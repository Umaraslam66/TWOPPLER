"""Tests for the pilot-4 driver (experiments/stage2_pilot4.py).

Deterministic, offline, NO API. The generator is a scripted fake client, so the
whole round-4 pipeline — register-conditioned generation, the plausibility
check, the deixis rule, the post-strip ladder — runs without spending a call.

What these defend, in the order round 3's report named the failures:
  * the generator is actually shown the subject's own answers as style
    exemplars, and cannot smuggle their content into an option;
  * a factually-false or fringe alternative is rejected, not accepted;
  * interviewer address is removed from ALL FOUR options or from NONE;
  * the ladder rung describes the options that were actually shipped;
  * the kill rule and the B10.7 non-adoption are pre-committed in code.
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
from doppler import counterfactuals4 as C4  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P4 = _load("stage2_pilot4_under_test", ROOT / "experiments/stage2_pilot4.py")


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


PAD = " ".join(f"w{i}" for i in range(34))
TRUE_ANSWER = f"Well, Robert, I think the council probably acted correctly. {PAD}."
EXEMPLARS = ["It depends, and the evidence is honestly mixed on that point.",
             "I would want to be careful here, because we do not really know yet."]


def _alt(k):
    return (f"I think the council probably acted wrongly in case {k}, though "
            f"it is a close call. " + " ".join(f"z{k}x{i}" for i in range(28))
            + ".")


class FakeClient:
    """Scripted generator. ``script`` maps a step keyword to replies in order."""

    def __init__(self, script=None, n_generated=4):
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.n_generated = n_generated
        self.prompts: list[str] = []
        self.n_calls = 0
        self.n_retries = 0
        self.model_name = P4.GENERATOR
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
            blocks = "\n".join(f"<<<{i + 1}>>>\n{_alt(i)}"
                               for i in range(self.n_generated))
            return self._take("generate", blocks), 10, 10
        if prompt.startswith("Rewrite the interview answer"):
            body = prompt.split("ANSWER\n", 1)[1].strip()
            if not body.endswith("."):
                body += "."
            return self._take("paraphrase", body), 10, 10
        if "VERDICT: SAME" in prompt:
            return self._take("position",
                              "VERDICT: SAME\nWHY: same claims."), 5, 5
        if "Classify the relationship" in prompt:
            return self._take("contradiction",
                              "VERDICT: CONFLICT\nWHY: opposite."), 5, 5
        if "Judge ONLY whether" in prompt:
            return self._take("plausibility",
                              "VERDICT: PLAUSIBLE\nWHY: defensible."), 5, 5
        raise AssertionError(f"unscripted prompt: {prompt[:80]}")


ITEM = {"item_id": "C1:T:3", "canonical_id": "C1", "transcript_id": "T",
        "q_turn_idx": 3, "question": "Did the council act correctly?",
        "answer": TRUE_ANSWER, "answer_words": len(TRUE_ANSWER.split()),
        "flags": []}

CTX = {"variants": ["Zorvath Quilliman"], "canonical_name": "Zorvath Quilliman",
       "grounding_raw": "HOST: earlier\nGUEST: " + " ".join(f"g{i}" for i in range(30)),
       "grounding_redacted": "HOST: earlier\nGUEST: " + " ".join(f"g{i}" for i in range(30)),
       "test_date": "2016-12-14",
       "host_forms": ["ROBERT SIEGEL", "SIEGEL", "ROBERT"]}

EXEMPLAR_BLOCK = {"texts": EXEMPLARS, "sources": ["answer_pool:T9", "answer_pool:T9"],
                  "n": 2, "shortfall": 1}


def _log(tmp_path):
    return P4.P3.GenLog(tmp_path / "genlog" / "item.jsonl")


def _build(client=None, item=None, ctx=None, exemplars=None, tmp_path=None):
    return P4.build_item_v4(client or FakeClient(), item or ITEM, ctx or CTX,
                            _log(tmp_path), exemplars or EXEMPLAR_BLOCK)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_a_clean_item_builds_four_options_with_exactly_one_true(tmp_path):
    rec = _build(tmp_path=tmp_path)
    assert rec["built"] is True
    kinds = [o["kind"] for o in rec["options"]]
    assert kinds.count("true") == 1 and kinds.count("distractor") == 3
    assert rec["options"][rec["correct_index"]]["kind"] == "true"


def test_the_true_option_is_the_post_deixis_paraphrase(tmp_path):
    """load_candidate_items asserts these are byte-identical downstream.

    If the record kept the pre-strip paraphrase as `true_answer_paraphrased`
    the export would refuse the item, so this is the join that makes the deixis
    rule survive into the prompts.
    """
    rec = _build(tmp_path=tmp_path)
    true = rec["options"][rec["correct_index"]]["text"]
    assert true == rec["true_answer_paraphrased"]
    assert rec["true_answer_paraphrased_pre_deixis"] != rec["true_answer_paraphrased"]


# ---------------------------------------------------------------------------
# D6-v4.1 register conditioning
# ---------------------------------------------------------------------------


def test_the_generator_is_shown_the_subjects_own_answers(tmp_path):
    """The whole point of round 4's register fix is few-shot conditioning."""
    client = FakeClient()
    _build(client=client, tmp_path=tmp_path)
    gen = [p for p in client.prompts if "ALTERNATIVE answers" in p]
    assert len(gen) == 1
    for exemplar in EXEMPLARS:
        assert exemplar in gen[0]
    assert "STYLE EXAMPLE 1" in gen[0]


def test_an_option_that_copies_a_style_exemplar_is_rejected(tmp_path):
    """A model handed three real answers can reach for content, not just rhythm.

    That would put real transcript speech into a slot the item calls generated.
    """
    leaked = EXEMPLARS[0]
    client = FakeClient(script={"generate": [
        "\n".join([f"<<<1>>>\n{leaked}"]
                  + [f"<<<{i}>>>\n{_alt(i)}" for i in (2, 3, 4)])]})
    rec = _build(client=client, tmp_path=tmp_path)
    reasons = [r["reason"] for rej in rec["rejections"]
               for r in rej.get("reasons", [])]
    assert any(x in reasons for x in
               ("copies_style_exemplar", "quotes_style_exemplar"))


# ---------------------------------------------------------------------------
# D6-v4.3 plausibility
# ---------------------------------------------------------------------------


def test_a_factually_false_alternative_is_rejected(tmp_path):
    """Round 3's report 2.2: if the alternatives are wrong about the world, the
    scorer wins on general knowledge and never models the person."""
    client = FakeClient(script={"plausibility": [
        "VERDICT: FALSE\nWHY: invents an event.",
        "VERDICT: PLAUSIBLE\nWHY: fine.",
        "VERDICT: PLAUSIBLE\nWHY: fine.",
        "VERDICT: PLAUSIBLE\nWHY: fine."]})
    rec = _build(client=client, tmp_path=tmp_path)
    reasons = [r["reason"] for rej in rec["rejections"]
               for r in rej.get("reasons", [])]
    assert "plausibility_false" in reasons
    assert rec["built"] is True          # the 4th generated option replaces it


def test_a_fringe_alternative_is_rejected(tmp_path):
    client = FakeClient(script={"plausibility": [
        "VERDICT: FRINGE\nWHY: nobody serious holds this.",
        "VERDICT: PLAUSIBLE\nWHY: fine.",
        "VERDICT: PLAUSIBLE\nWHY: fine.",
        "VERDICT: PLAUSIBLE\nWHY: fine."]})
    rec = _build(client=client, tmp_path=tmp_path)
    reasons = [r["reason"] for rej in rec["rejections"]
               for r in rej.get("reasons", [])]
    assert "plausibility_fringe" in reasons


def test_an_unparseable_plausibility_verdict_is_a_rejection_never_a_guess(tmp_path):
    client = FakeClient(script={"plausibility": ["I think it is probably fine."]})
    rec = _build(client=client, tmp_path=tmp_path)
    reasons = [r["reason"] for rej in rec["rejections"]
               for r in rej.get("reasons", [])]
    assert "plausibility_unparsed" in reasons


def test_plausibility_runs_only_on_options_that_already_conflict(tmp_path):
    """Order matters for cost: an AGREE option is dead already, so paying for a
    plausibility call on it is waste."""
    client = FakeClient(script={"contradiction": [
        "VERDICT: AGREE\nWHY: restates it.",
        "VERDICT: CONFLICT\nWHY: opposite.",
        "VERDICT: CONFLICT\nWHY: opposite.",
        "VERDICT: CONFLICT\nWHY: opposite."]})
    _build(client=client, tmp_path=tmp_path)
    n_contra = sum(1 for p in client.prompts if "Classify the relationship" in p)
    n_plaus = sum(1 for p in client.prompts if "Judge ONLY whether" in p)
    assert n_contra == 4 and n_plaus == 3


# ---------------------------------------------------------------------------
# D6-v4.2 deixis
# ---------------------------------------------------------------------------


def test_interviewer_address_is_removed_from_every_option(tmp_path):
    rec = _build(tmp_path=tmp_path)
    assert rec["deixis"]["mode"] == "stripped"
    for opt in rec["options"]:
        assert "Robert" not in opt["text"]
        assert not opt["text"].lower().startswith("well,")


def test_the_deixis_decision_is_recorded_on_the_item(tmp_path):
    rec = _build(tmp_path=tmp_path)
    assert f"deixis_{rec['deixis']['mode']}" in rec["flags"]
    assert "removed_per_option" in rec["deixis"]
    assert rec["deixis"]["n_options_changed"] >= 1


def test_the_whole_set_is_retained_when_stripping_would_gut_an_option(tmp_path):
    """Uniformity is the rule. Stripping only the options that happen to carry
    a vocative would leave exactly the asymmetry the strip exists to remove."""
    short = {**ITEM, "answer": "Well, Robert, you know."}
    client = FakeClient(script={"generate": [
        "\n".join(f"<<<{i}>>>\nA measured alternative reading number {i}."
                  for i in range(1, 5))]})
    rec = P4.build_item_v4(client, short, CTX, _log(tmp_path), EXEMPLAR_BLOCK)
    if rec["built"]:
        assert rec["deixis"]["mode"] == "retained"
        assert all(r == [] for r in rec["deixis"]["removed_per_option"])


def test_the_ladder_rung_is_measured_after_stripping(tmp_path):
    """A rung measured on pre-strip text describes an option set that no longer
    exists, because stripping changes word counts."""
    rec = _build(tmp_path=tmp_path)
    texts = [o["text"] for o in rec["options"] if o["kind"] == "distractor"]
    expected = CF.match_rung(rec["true_answer_paraphrased"], texts)
    assert rec["relax_rung"] == expected


# ---------------------------------------------------------------------------
# D6-v4.4 item type
# ---------------------------------------------------------------------------


def test_every_round_three_item_has_a_hand_classification_with_a_reason():
    """The build uses the hand call, so an unreasoned entry is a silent choice."""
    for item_id, (kind, why) in P4.HAND_ITEM_TYPE.items():
        assert kind in ("subjective", "factual_explanation"), item_id
        assert why and len(why) > 20, item_id


def test_subjective_items_are_built_before_factual_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(P4, "classify_candidates", lambda _d: {"items": [
        {"item_id": "C1:T:9", "kind": "factual_explanation"},
        {"item_id": "C1:T:3", "kind": "subjective"}]})
    monkeypatch.setattr(P4.P3, "all_items", lambda _d: [
        {"item_id": "C1:T:3", "canonical_id": "C1"},
        {"item_id": "C1:T:9", "canonical_id": "C1"}])
    order = [i["item_id"] for i in P4.items_in_build_order(
        tmp_path, tmp_path, include_factual=True, pilot1_dir=tmp_path)]
    assert order == ["C1:T:3", "C1:T:9"]


def test_factual_items_are_excluded_unless_supply_demands(tmp_path, monkeypatch):
    monkeypatch.setattr(P4, "classify_candidates", lambda _d: {"items": [
        {"item_id": "C1:T:9", "kind": "factual_explanation"},
        {"item_id": "C1:T:3", "kind": "subjective"}]})
    monkeypatch.setattr(P4.P3, "all_items", lambda _d: [
        {"item_id": "C1:T:3", "canonical_id": "C1"},
        {"item_id": "C1:T:9", "canonical_id": "C1"}])
    order = [i["item_id"] for i in P4.items_in_build_order(
        tmp_path, tmp_path, include_factual=False, pilot1_dir=tmp_path)]
    assert order == ["C1:T:3"]


# ---------------------------------------------------------------------------
# Pre-committed decisions
# ---------------------------------------------------------------------------


def test_the_kill_rule_is_pre_committed_in_code_at_zero_point_nine():
    """It only means something if it is written down before the data exists."""
    assert P4.KILL_RULE_THRESHOLD == 0.9
    assert "FALLBACK_OPENENDED_SKETCH.md" in P4.KILL_RULE
    assert "no round 5" in P4.KILL_RULE


def test_the_margin_relaxation_is_documented_as_not_adopted():
    """A kill rule means nothing if the bar moves in the same round."""
    text = P4.B10_7_MARGIN_CONSIDERATION
    assert "NOT adopted" in text
    assert "bar-lock" in text.lower()
    assert "gray zone" in text


def test_the_generator_is_still_never_a_scored_model():
    assert P4.GENERATOR not in P4.SCORED_MODELS


def test_the_round_three_overlap_declaration_is_carried_forward():
    assert P4.GENERATOR_IS_ROBUSTNESS_SCORER is True
    assert "INERT IN THIS PILOT" in P4.B10_3_OVERLAP_DECLARATION


def test_round_four_does_not_reuse_round_threes_template_digest():
    """Round 3's artifacts must stay verifiable against the digest they used."""
    assert C4.TEMPLATE_SHA256_V4 != CF.TEMPLATE_SHA256
    assert C4.TEMPLATE_SHA256_V3_REUSED == CF.TEMPLATE_SHA256


def test_the_scored_claim_reframing_is_carried_on_every_built_item(tmp_path):
    rec = _build(tmp_path=tmp_path)
    assert "POSITION" in rec["scored_claim"]


def test_a_build_refuses_to_run_on_a_scored_model(tmp_path):
    client = FakeClient()
    client.model_name = P4.SCORED_MODELS[0]
    with pytest.raises(SystemExit, match="B10.3 violation"):
        P4.cmd_build(Args(pilot1_dir=ROOT / "results/stage2_pilot",
                          pilot3_dir=ROOT / "results/stage2_pilot3",
                          out_dir=tmp_path, client=client, force=False,
                          call_cap=10, skip_cost=True, include_factual=False))
