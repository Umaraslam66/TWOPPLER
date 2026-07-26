"""Tests for the pilot-3 driver (experiments/stage2_pilot3.py).

Deterministic, offline, NO API. The generator is replaced by a scripted fake
client, so the whole build pipeline — paraphrase, position check, generation,
guards, contradiction check, ladder, shuffle — is exercised without spending a
call or depending on a non-reproducible model.

What these defend: B10.3 separation, B10.4's one-factor paraphrase, B10.5's
rejections, the era/leak guards, and the B10.8 sheet never revealing its key.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from doppler import counterfactuals as CF  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P3 = _load("stage2_pilot3_under_test", ROOT / "experiments/stage2_pilot3.py")


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


# Fixture texts must end in sentence-final punctuation: the driver refuses a
# paraphrase that does not, because that is how a thinking-token truncation
# shows up in the real pipeline.
WORDS = " ".join(f"w{i}" for i in range(40)) + "."
TRUE_ANSWER = "I believe the council acted correctly. " + WORDS


def _alt(k):
    return (f"I believe the council acted wrongly in case {k}. "
            + " ".join(f"z{k}x{i}" for i in range(34)) + ".")


class FakeClient:
    """A scripted generator. Returns canned text by pipeline step.

    ``script`` maps a step keyword to a list of replies consumed in order;
    anything missing falls back to a sensible default, so a test only has to
    say what it is actually about.
    """

    def __init__(self, script=None, n_generated=4):
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.n_generated = n_generated
        self.prompts: list[str] = []
        self.n_calls = 0
        self.n_retries = 0
        self.model_name = P3.GENERATOR
        self.temperature = 0.0
        self.max_output_tokens = 512
        self._config = None

    def _take(self, key, default):
        if self.script.get(key):
            return self.script[key].pop(0)
        return default

    def generate(self, prompt):
        self.prompts.append(prompt)
        self.n_calls += 1
        if "ALTERNATIVE answers" in prompt:
            blocks = "\n".join(f"<<<{i+1}>>>\n{_alt(i)}"
                               for i in range(self.n_generated))
            return self._take("generate", blocks), 10, 10
        if prompt.startswith("Rewrite the interview answer"):
            body = prompt.split("ANSWER\n", 1)[1].strip()
            if not body.endswith("."):
                body += "."
            return self._take("paraphrase", body), 10, 10
        if "VERDICT: SAME" in prompt:
            return self._take("position", "VERDICT: SAME\nWHY: same claims."), 5, 5
        if "VERDICT: CONFLICT" in prompt:
            return self._take("contradiction",
                              "VERDICT: CONFLICT\nWHY: opposite."), 5, 5
        raise AssertionError(f"unscripted prompt: {prompt[:80]}")


ITEM = {"item_id": "C1:T:3", "canonical_id": "C1", "transcript_id": "T",
        "q_turn_idx": 3, "question": "Did the council act correctly?",
        "answer": TRUE_ANSWER, "answer_words": len(TRUE_ANSWER.split()),
        "flags": []}
CTX = {"variants": ["Zorvath Quilliman"], "canonical_name": "Zorvath Quilliman",
       "grounding_raw": "HOST: earlier\nGUEST: " + " ".join(f"g{i}" for i in range(30)),
       "grounding_redacted": "HOST: earlier\nGUEST: " + " ".join(f"g{i}" for i in range(30)),
       "test_date": "2016-12-14"}


def _log(tmp_path):
    return P3.GenLog(tmp_path / "genlog" / "item.jsonl")


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


def test_a_clean_item_builds_four_options_with_one_true(tmp_path):
    rec = P3.build_item(FakeClient(), ITEM, CTX, _log(tmp_path))
    assert rec["built"] is True
    assert len(rec["options"]) == 4
    kinds = [o["kind"] for o in rec["options"]]
    assert kinds.count("true") == 1 and kinds.count("distractor") == 3
    assert rec["options"][rec["correct_index"]]["kind"] == "true"


def test_the_true_option_is_the_paraphrase_not_the_verbatim_answer(tmp_path):
    client = FakeClient(script={"paraphrase": ["Neutralised true answer. " + WORDS]})
    rec = P3.build_item(client, ITEM, CTX, _log(tmp_path))
    true = rec["options"][rec["correct_index"]]["text"]
    assert true == rec["true_answer_paraphrased"]
    assert true != ITEM["answer"]


def test_every_option_including_the_true_one_is_paraphrased(tmp_path):
    # B10.4 is one-factor only if the real answer goes through the same step.
    client = FakeClient()
    P3.build_item(client, ITEM, CTX, _log(tmp_path))
    para = [p for p in client.prompts
            if p.startswith("Rewrite the interview answer")]
    assert len(para) == 1 + CF.N_GENERATED


def test_the_paraphrase_template_is_byte_identical_for_real_and_generated(
        tmp_path):
    client = FakeClient()
    P3.build_item(client, ITEM, CTX, _log(tmp_path))
    para = [p for p in client.prompts
            if p.startswith("Rewrite the interview answer")]
    skeletons = {p.split("ANSWER\n", 1)[0] for p in para}
    assert len(skeletons) == 1


def test_generation_is_conditioned_on_the_paraphrased_true_answer(tmp_path):
    client = FakeClient(script={"paraphrase": ["SHORTER TRUE TEXT HERE."]})
    P3.build_item(client, ITEM, CTX, _log(tmp_path))
    gen = next(p for p in client.prompts if "ALTERNATIVE answers" in p)
    assert "SHORTER TRUE TEXT HERE." in gen
    assert ITEM["answer"] not in gen


def test_the_option_order_is_seeded_by_item_id(tmp_path):
    a = P3.build_item(FakeClient(), ITEM, CTX, _log(tmp_path))
    b = P3.build_item(FakeClient(), ITEM, CTX, _log(tmp_path))
    assert [o["text"] for o in a["options"]] == [o["text"] for o in b["options"]]
    assert a["correct_index"] == b["correct_index"]


def test_every_call_is_written_to_the_genlog(tmp_path):
    log = _log(tmp_path)
    client = FakeClient()
    P3.build_item(client, ITEM, CTX, log)
    log.flush()
    rows = [json.loads(l) for l in log.path.read_text().splitlines()]
    assert len(rows) == client.n_calls
    assert {r["model"] for r in rows} == {P3.GENERATOR}
    for row in rows:
        assert row["prompt"] and row["completion"] is not None


# ---------------------------------------------------------------------------
# Rejections and drops
# ---------------------------------------------------------------------------


def test_a_changed_position_drops_the_item_after_one_retry(tmp_path):
    client = FakeClient(script={"position": ["VERDICT: CHANGED\nWHY: lost a claim.",
                                             "VERDICT: CHANGED\nWHY: still lost."]})
    rec = P3.build_item(client, ITEM, CTX, _log(tmp_path))
    assert rec["built"] is False
    assert "did not preserve" in rec["reason"]
    assert rec["position_check"]["retried"] is True


def test_a_position_check_that_passes_on_retry_keeps_the_item(tmp_path):
    client = FakeClient(script={"position": ["VERDICT: CHANGED\nWHY: truncated.",
                                             "VERDICT: SAME\nWHY: fine."]})
    rec = P3.build_item(client, ITEM, CTX, _log(tmp_path))
    assert rec["built"] is True
    assert rec["position_check"]["retried"] is True


def test_a_truncated_true_paraphrase_is_refused_not_scored(tmp_path):
    client = FakeClient(script={"paraphrase": ["I think the answer is clearly som",
                                               "A complete sentence this time."]})
    rec = P3.build_item(client, ITEM, CTX, _log(tmp_path))
    # The first paraphrase is refused as truncated and retried, not passed to
    # the position check where it would look like a changed position.
    assert rec["built"] is True
    assert rec["true_answer_paraphrased"] == "A complete sentence this time."


def test_a_distractor_that_agrees_is_rejected_and_counted(tmp_path):
    client = FakeClient(script={"contradiction": [
        "VERDICT: AGREE\nWHY: same position.",
        "VERDICT: CONFLICT\nWHY: opposite.",
        "VERDICT: CONFLICT\nWHY: opposite.",
        "VERDICT: CONFLICT\nWHY: opposite."]})
    rec = P3.build_item(client, ITEM, CTX, _log(tmp_path))
    assert rec["built"] is True
    reasons = [r["reason"] for rej in rec["rejections"]
               for r in rej.get("reasons", [])]
    assert "contradiction_agree" in reasons


def test_an_unrelated_distractor_is_rejected_too(tmp_path):
    # UNRELATED does not answer the question, which is exactly the round-2
    # responsiveness tell coming back in.
    client = FakeClient(script={"contradiction": [
        "VERDICT: UNRELATED\nWHY: answers something else.",
        "VERDICT: CONFLICT\nWHY: opposite.",
        "VERDICT: CONFLICT\nWHY: opposite.",
        "VERDICT: CONFLICT\nWHY: opposite."]})
    rec = P3.build_item(client, ITEM, CTX, _log(tmp_path))
    reasons = [r["reason"] for rej in rec["rejections"]
               for r in rej.get("reasons", [])]
    assert "contradiction_unrelated" in reasons


def test_too_few_surviving_distractors_drops_the_item(tmp_path):
    client = FakeClient(script={"contradiction": ["VERDICT: AGREE\nWHY: same."] * 4})
    rec = P3.build_item(client, ITEM, CTX, _log(tmp_path))
    assert rec["built"] is False
    assert "survived the checks" in rec["reason"]


def test_a_generator_returning_too_few_blocks_drops_the_item(tmp_path):
    client = FakeClient(script={"generate": ["<<<1>>>\nonly one alternative."]})
    rec = P3.build_item(client, ITEM, CTX, _log(tmp_path))
    assert rec["built"] is False
    assert "returned 1 blocks" in rec["reason"]


def test_an_era_violation_is_rejected_offline(tmp_path):
    bad = ("In 2019 everything changed completely and totally. "
           + " ".join(f"q{i}" for i in range(32)) + ".")
    blocks = "\n".join([f"<<<1>>>\n{bad}"] +
                       [f"<<<{i+2}>>>\n{_alt(i)}" for i in range(3)])
    client = FakeClient(script={"generate": [blocks]})
    rec = P3.build_item(client, ITEM, CTX, _log(tmp_path))
    reasons = [r["reason"] for rej in rec["rejections"]
               for r in rej.get("reasons", [])]
    assert "era_violation" in reasons


def test_an_option_naming_the_subject_is_rejected_offline(tmp_path):
    bad = ("Well Quilliman would never agree with that at all. "
           + " ".join(f"q{i}" for i in range(32)) + ".")
    blocks = "\n".join([f"<<<1>>>\n{bad}"] +
                       [f"<<<{i+2}>>>\n{_alt(i)}" for i in range(3)])
    client = FakeClient(script={"generate": [blocks]})
    rec = P3.build_item(client, ITEM, CTX, _log(tmp_path))
    reasons = [r["reason"] for rej in rec["rejections"]
               for r in rej.get("reasons", [])]
    assert "names_subject" in reasons


def test_an_option_quoting_the_grounding_is_rejected_offline(tmp_path):
    quote = " ".join(f"g{i}" for i in range(30)) + "."
    blocks = "\n".join([f"<<<1>>>\n{quote}"] +
                       [f"<<<{i+2}>>>\n{_alt(i)}" for i in range(3)])
    client = FakeClient(script={"generate": [blocks]})
    rec = P3.build_item(client, ITEM, CTX, _log(tmp_path))
    reasons = [r["reason"] for rej in rec["rejections"]
               for r in rej.get("reasons", [])]
    assert "quotes_grounding" in reasons


def test_an_option_copying_the_true_answer_is_rejected_offline(tmp_path):
    blocks = "\n".join([f"<<<1>>>\n{TRUE_ANSWER}"] +
                       [f"<<<{i+2}>>>\n{_alt(i)}" for i in range(3)])
    client = FakeClient(script={"generate": [blocks]})
    rec = P3.build_item(client, ITEM, CTX, _log(tmp_path))
    reasons = [r["reason"] for rej in rec["rejections"]
               for r in rej.get("reasons", [])]
    assert "copies_true_answer" in reasons


def test_the_ladder_rung_is_recorded(tmp_path):
    rec = P3.build_item(FakeClient(), ITEM, CTX, _log(tmp_path))
    assert rec["relax_rung"] is not None
    assert rec["flags"] == [f"relax_rung_{rec['relax_rung']}"]


# ---------------------------------------------------------------------------
# B10.3 separation and the reframing
# ---------------------------------------------------------------------------


def test_the_generator_is_never_the_robustness_scorer():
    assert P3.GENERATOR != P3.ROBUSTNESS_SCORER


def test_a_build_refuses_to_run_on_the_robustness_scorer(tmp_path, monkeypatch):
    client = FakeClient()
    client.model_name = P3.ROBUSTNESS_SCORER
    with pytest.raises(SystemExit, match="B10.3 violation"):
        P3.cmd_build(Args(pilot1_dir=ROOT / "results/stage2_pilot",
                          out_dir=tmp_path, client=client, force=False,
                          call_cap=10, skip_cost=True))


def test_the_scored_claim_is_carried_on_every_built_item(tmp_path):
    rec = P3.build_item(FakeClient(), ITEM, CTX, _log(tmp_path))
    assert "POSITION" in rec["scored_claim"]
    assert "NOT that it picks a verbatim" in rec["scored_claim"]


# ---------------------------------------------------------------------------
# The B10.8 detectability sheet
# ---------------------------------------------------------------------------


def _fake_built(out_dir, n=12):
    items_dir = out_dir / "items"
    items_dir.mkdir(parents=True, exist_ok=True)
    for k in range(n):
        item_id = f"C{k % 3}:T:{k}"
        opts = [{"text": f"real answer {k}", "kind": "true",
                 "origin": "paraphrased_real"}]
        opts += [{"text": f"generated {k}-{j}", "kind": "distractor",
                  "origin": "generated"} for j in range(3)]
        (items_dir / f"{P3.safe_id(item_id)}.json").write_text(json.dumps({
            "item_id": item_id, "canonical_id": f"C{k % 3}", "built": True,
            "question": f"Question number {k}?", "options": opts,
            "options_stripped": [o["text"] for o in opts],
            "correct_index": 0, "relax_rung": 0, "flags": ["relax_rung_0"],
            "true_answer_paraphrased": f"real answer {k}",
            "spare_generated": [f"spare {k}"], "generator": P3.GENERATOR}),
            encoding="utf-8")


def test_the_sheet_has_twenty_entries_split_ten_and_ten(tmp_path):
    _fake_built(tmp_path)
    P3.cmd_sheet(Args(out_dir=tmp_path))
    plan = json.loads((tmp_path / "detectability_plan.json").read_text())
    assert plan["n_entries"] == 20
    assert plan["n_real"] == 10 and plan["n_control"] == 10


def test_the_sheet_never_marks_an_answer(tmp_path):
    _fake_built(tmp_path)
    P3.cmd_sheet(Args(out_dir=tmp_path))
    sheet = (tmp_path / "DETECTABILITY_SHEET.md").read_text()
    for banned in ("TRUE ANSWER", "correct", "real answer is", "KEY:",
                   "kind: real", "control"):
        assert banned not in sheet
    assert "**A.**" in sheet and "Your answer:" in sheet


def test_the_key_names_the_answer_for_every_entry(tmp_path):
    _fake_built(tmp_path)
    P3.cmd_sheet(Args(out_dir=tmp_path))
    key = (tmp_path / "DETECTABILITY_KEY.md").read_text()
    assert key.count("| real |") == 10
    assert key.count("| control |") == 10
    assert "**none**" in key


def test_a_control_entry_contains_no_real_answer(tmp_path):
    _fake_built(tmp_path)
    P3.cmd_sheet(Args(out_dir=tmp_path))
    plan = json.loads((tmp_path / "detectability_plan.json").read_text())
    records = {r["item_id"]: r for r in P3.load_records(tmp_path)}
    sheet = (tmp_path / "DETECTABILITY_SHEET.md").read_text()
    controls = [e for e in plan["entries"] if e["kind"] == "control"]
    assert controls
    for entry in controls:
        assert entry["correct_index"] is None
        real = records[entry["item_id"]]["true_answer_paraphrased"]
        # the real text may still appear via another entry, so check the block
        block = sheet.split(f"## {entry['n']}.")[1].split("---")[0]
        assert real not in block


def test_control_options_are_four_generated_texts(tmp_path):
    _fake_built(tmp_path)
    rec = P3.load_records(tmp_path)[0]
    opts = P3.control_options(rec)
    assert len(opts) == 4
    assert rec["true_answer_paraphrased"] not in opts


def test_an_item_with_no_spare_cannot_be_a_control(tmp_path):
    _fake_built(tmp_path, n=1)
    rec = P3.load_records(tmp_path)[0]
    rec["spare_generated"] = []
    assert P3.control_options(rec) is None


def test_the_sheet_is_stable_for_a_fixed_seed(tmp_path):
    _fake_built(tmp_path)
    P3.cmd_sheet(Args(out_dir=tmp_path))
    first = (tmp_path / "DETECTABILITY_SHEET.md").read_text()
    P3.cmd_sheet(Args(out_dir=tmp_path))
    assert (tmp_path / "DETECTABILITY_SHEET.md").read_text() == first
