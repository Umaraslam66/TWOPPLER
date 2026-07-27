"""Tests for the OE-1 driver (experiments/stage2_oe1.py).

Deterministic, offline, NO API and NO GPU. Every fixture is synthetic.

What these defend:
  * the judge rubric is lifted VERBATIM out of the spec's fenced block and its
    sha256 is the hash of the text that would actually be sent;
  * a judge call carries one candidate, three GUEST-redacted texts, and no arm
    or model label anywhere;
  * the LABEL:/WHY: parser accepts the required format and refuses everything
    else, so a malformed reply is retried rather than silently scored;
  * the build QA fails loudly — it is the thing standing between a broken
    prompt set and a node-hour;
  * the H7 delta bins are the four frozen ones.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from doppler import oe_render as OE  # noqa: E402
from doppler import stage2_render as R  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


OE1 = _load("stage2_oe1_under_test", ROOT / "experiments/stage2_oe1.py")

VARIANTS = ["Jane Smith"]


# ---------------------------------------------------------------------------
# Rubric extraction
# ---------------------------------------------------------------------------


def test_rubric_is_extracted_verbatim_from_the_spec():
    got = OE1.extract_rubric(OE1.SPEC_PATH)
    raw = OE1.SPEC_PATH.read_text(encoding="utf-8")
    assert got["text"] in raw            # verbatim: a substring of the spec
    assert got["text"].startswith("STANCE JUDGE RUBRIC")
    assert got["text"].rstrip().endswith(
        "WHY: <one sentence quoting the decisive phrase of each answer>")
    assert "```" not in got["text"]
    assert got["sha256"] == R.sha256(got["text"])
    assert got["version"] == "r1"


def test_rubric_carries_the_three_labels_and_the_seven_boundary_rules():
    text = OE1.extract_rubric(OE1.SPEC_PATH)["text"]
    for label in OE1.LABELS:
        assert f"\n{label} " in text or f"{label} —" in text or label in text
    assert "LABEL: <SAME|DIFFERENT|UNCLEAR>" in text
    for n in range(1, 8):
        assert f"\n{n}. " in text


def test_a_spec_without_the_fenced_rubric_fails_loudly(tmp_path):
    path = tmp_path / "SPEC.md"
    path.write_text("# no rubric here\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        OE1.extract_rubric(path)


# ---------------------------------------------------------------------------
# The judge call
# ---------------------------------------------------------------------------


def test_judge_input_redacts_the_name_in_all_three_texts():
    got = OE1.judge_input(
        "RUBRIC", "Jane Smith, was the audit buried?",
        "Smith here — yes, it was buried.",
        "I think Jane Smith would say it was buried.", VARIANTS)
    assert "Jane" not in got
    assert "Smith" not in got
    assert got.count("GUEST") >= 3


def test_judge_input_names_no_arm_and_no_model():
    got = OE1.judge_input("RUBRIC", "q?", "real", "candidate", VARIANTS)
    for arm in OE.ARMS:
        assert arm not in got
    for token in ("Gemma", "gemini", "flash", "imposter", "twin", "zeroinfo"):
        assert token not in got
    assert got.count("CANDIDATE ANSWER:") == 1


def test_judge_input_carries_exactly_the_three_labelled_texts():
    got = OE1.judge_input("RUBRIC", "q?", "real answer", "candidate answer",
                          VARIANTS)
    assert got.index("QUESTION:") < got.index("REAL ANSWER:") \
        < got.index("CANDIDATE ANSWER:")
    assert got.startswith("RUBRIC")


@pytest.mark.parametrize("label", ["SAME", "DIFFERENT", "UNCLEAR"])
def test_parse_judge_reads_the_required_format(label):
    got = OE1.parse_judge(f"LABEL: {label}\nWHY: because 'x' and 'y'.")
    assert got == (label, "because 'x' and 'y'.")


def test_parse_judge_is_case_insensitive_and_tolerates_a_preamble():
    label, why = OE1.parse_judge("Here you go.\nlabel: same\nwhy: both say yes.")
    assert (label, why) == ("SAME", "both say yes.")


@pytest.mark.parametrize("bad", ["", None, "SAME", "LABEL: MAYBE\nWHY: no.",
                                 "The answers agree."])
def test_parse_judge_refuses_everything_else(bad):
    assert OE1.parse_judge(bad) == (None, None)


def test_a_judge_call_is_twin_free_by_construction():
    """One candidate per call, so a question is never in front of it twice."""
    call = {"item_id": "C1:T:1"}
    got = OE1.assert_no_cross_visible_twins({"judge_call_0": [call]})
    assert got["ok"] is True
    with pytest.raises(SystemExit):
        OE1.assert_no_cross_visible_twins({"bad": [call, dict(call)]})


def test_judge_order_seed_is_fixed_and_recorded():
    assert isinstance(OE1.JUDGE_ORDER_SEED, int)
    assert OE1.JUDGE_TEMPERATURE == 0.0


def test_the_judge_is_not_a_scored_model_and_not_the_robustness_version():
    assert OE1.JUDGE_MODEL not in OE1.SCORED_MODELS
    assert OE1.JUDGE_MODEL != OE1.ROBUSTNESS_MODEL


# ---------------------------------------------------------------------------
# Generation settings and caps
# ---------------------------------------------------------------------------


def test_generation_settings_are_the_spec_values_everywhere():
    assert OE1.GEN_TEMPERATURE == 0.0
    assert OE1.GEN_MAX_OUTPUT_TOKENS == 256 == OE.MAX_OUTPUT_TOKENS
    assert OE1.API_BUDGET_USD == 0.40
    assert OE1.NODE_HOUR_BUDGET == 0.25


def test_truncation_is_flagged_at_the_cap_and_mid_sentence():
    assert OE1.looks_truncated("a finished sentence.", 10) is False
    assert OE1.looks_truncated("a finished sentence.", OE.MAX_OUTPUT_TOKENS) is True


# ---------------------------------------------------------------------------
# H7 delta bins (spec section 9 smoke check)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("days,expected", [
    (10, "<6m"), (183, "6-12m"), (364, "6-12m"), (365, "1-2y"),
    (729, "1-2y"), (730, "2-3y"), (1094, "2-3y"), (1095, ">3y"), (4000, ">3y"),
    (None, None),
])
def test_delta_bins_are_the_four_frozen_ones(days, expected):
    assert OE1.delta_bin(days) == expected


# ---------------------------------------------------------------------------
# Build QA
# ---------------------------------------------------------------------------

SEGMENTS = [{"date": "2012-01-01", "program": "WEEKEND EDITION",
             "exchanges": [{"host_text": "You joined us before.",
                            "guest_text": "I did, and I said the same then."}]}]
DONOR_SEGMENTS = [{"date": "2012-06-01", "program": "MORNING EDITION",
                   "exchanges": [{"host_text": "Different person entirely.",
                                  "guest_text": "Quite a different view."}]}]


def _fixture_build():
    twin = R.render_grounding(SEGMENTS)
    donor = R.render_grounding(DONOR_SEGMENTS)
    ctx = {"C1": {"canonical_id": "C1", "canonical_name": "Jane Smith",
                  "variants": VARIANTS, "twin_block": twin,
                  "donor_id": "D9", "donor_variants": ["Bob Jones"],
                  "donor_block": donor}}
    item = {"item_id": "C1:T:1", "canonical_id": "C1",
            "question": "So what did you learn?",
            "answer": "Nothing that anybody wanted to hear about it, honestly."}
    sets = {}
    for arm in OE.ARMS:
        if arm == "imposter_redacted":
            block, donor_variants = donor, ctx["C1"]["donor_variants"]
        elif arm in OE.GROUNDED_ARMS:
            block, donor_variants = twin, None
        else:
            block, donor_variants = None, None
        row = OE1.render_and_guard_open(
            arm, item, subject_name="Jane Smith", subject_variants=VARIANTS,
            grounding_block=block, donor_variants=donor_variants)
        row.update({"item_id": item["item_id"], "canonical_id": "C1",
                    "arm": arm, "item_type": "subjective",
                    "donor_id": "D9" if arm == "imposter_redacted" else None,
                    "delta_bin": "1-2y"})
        sets[arm] = [row]
    return {"sets": sets, "n_items": 1}, ctx


def test_build_qa_passes_on_a_clean_set():
    build, ctx = _fixture_build()
    qa = OE1.build_qa(build, ctx)
    assert qa["instruction_tail_byte_identical"] is True
    assert qa["instruction_tail_sha256"] == OE.INSTRUCTION_SHA256
    assert qa["per_arm_prompt_counts"] == {arm: 1 for arm in OE.ARMS}
    assert qa["n_grounded_prompts_over_budget"] == 0
    assert qa["zeroinfo_prompts_with_excerpts"] == 0
    assert qa["surviving_name_variants_in_redacted_arms"] == 0
    assert qa["twin_free_check"]["ok"] is True


def test_build_qa_catches_a_drifted_instruction_tail():
    build, ctx = _fixture_build()
    row = build["sets"]["twin_named"][0]
    row["prompt"] = row["prompt"] + " Please be brief."
    row["instruction_tail_sha256"] = R.sha256(OE.tail_of(row["prompt"]))
    with pytest.raises(SystemExit, match="byte-identical"):
        OE1.build_qa(build, ctx)


def test_build_qa_catches_a_forced_choice_tail():
    build, ctx = _fixture_build()
    row = build["sets"]["zeroinfo_redacted"][0]
    row["prompt"] = (row["prompt"].rsplit("\n\n", 1)[0]
                     + "\n\nA. one\nB. two\n\n" + OE.OPEN_ANSWER_INSTRUCTION)
    with pytest.raises(SystemExit):
        OE1.build_qa(build, ctx)


def test_build_qa_catches_an_excerpt_in_a_zero_information_prompt():
    build, ctx = _fixture_build()
    row = build["sets"]["zeroinfo_named"][0]
    head, tail = row["prompt"].rsplit("\n\n", 1)
    row["prompt"] = f"{head}\n\n{R.EXCERPTS_HEADER}\nHOST: leak\n\n{tail}"
    with pytest.raises(SystemExit, match="carry excerpts"):
        OE1.build_qa(build, ctx)


def test_build_qa_catches_a_surviving_subject_name():
    build, ctx = _fixture_build()
    row = build["sets"]["twin_redacted"][0]
    row["prompt"] = row["prompt"].replace("HOST:", "HOST: Jane Smith,", 1)
    with pytest.raises(SystemExit, match="name variants survive"):
        OE1.build_qa(build, ctx)


def test_build_qa_catches_an_over_budget_grounding():
    build, ctx = _fixture_build()
    build["sets"]["twin_redacted"][0]["grounding_speech_words"] = 2001
    with pytest.raises(SystemExit, match="grounding budget"):
        OE1.build_qa(build, ctx)


def test_build_qa_catches_uneven_per_arm_counts():
    build, ctx = _fixture_build()
    build["sets"]["twin_named"] = []
    with pytest.raises(SystemExit):
        OE1.build_qa(build, ctx)


def test_render_and_guard_open_rejects_an_answer_quoted_in_the_grounding():
    twin = R.render_grounding(SEGMENTS)
    item = {"item_id": "C1:T:1", "canonical_id": "C1",
            "question": "So what did you learn?",
            "answer": "I did, and I said the same then."}
    with pytest.raises(ValueError, match="leaked"):
        OE1.render_and_guard_open("twin_redacted", item,
                                  subject_name="Jane Smith",
                                  subject_variants=VARIANTS,
                                  grounding_block=twin)


def test_render_and_guard_open_reports_the_open_ended_metadata():
    build, _ = _fixture_build()
    row = build["sets"]["twin_redacted"][0]
    assert row["max_output_tokens"] == OE.MAX_OUTPUT_TOKENS
    assert row["instruction_tail_sha256"] == OE.INSTRUCTION_SHA256
    assert row["prompt_sha256"] == R.sha256(row["prompt"])
    assert row["grounding_speech_words"] > 0
    assert build["sets"]["zeroinfo_redacted"][0]["grounding_speech_words"] == 0


# ---------------------------------------------------------------------------
# Embedding candidates
# ---------------------------------------------------------------------------


def test_embedding_candidates_fall_back_to_the_spec_list(tmp_path):
    got = OE1.embed_candidates(tmp_path)
    assert [c["name"] for c in got] == [c["name"] for c in OE1.EMBED_CANDIDATES]
    assert len(got) == 4


def test_embedding_candidates_prefer_housekeeping_when_it_exists(tmp_path):
    (tmp_path / "housekeeping.json").write_text(
        '{"embedding_candidates": ["a/b", "c/d"]}', encoding="utf-8")
    assert [c["name"] for c in OE1.embed_candidates(tmp_path)] == ["a/b", "c/d"]


def test_embedding_candidates_read_the_housekeeping_models_key_with_revisions(
        tmp_path):
    """housekeeping.json records the pinned HF revision; it must survive."""
    (tmp_path / "housekeeping.json").write_text(
        '{"models": [{"name": "a/b", "revision": "deadbeef"}]}',
        encoding="utf-8")
    got = OE1.embed_candidates(tmp_path)
    assert got == [{"name": "a/b", "revision": "deadbeef"}]


def test_the_real_housekeeping_file_pins_all_four_candidates():
    got = OE1.embed_candidates(OE1.OE_DIR)
    assert len(got) == 4
    assert [c["name"] for c in got] == [c["name"] for c in OE1.EMBED_CANDIDATES]
    assert all(c.get("revision") for c in got)


def test_e5_prefixes_are_asymmetric_and_pinned():
    assert OE1.E5_QUERY_PREFIX == "query: "
    assert OE1.E5_PASSAGE_PREFIX == "passage: "
    assert OE1.E5_QUERY_PREFIX != OE1.E5_PASSAGE_PREFIX


def test_no_scored_model_is_ever_an_embedding_candidate():
    names = [c["name"] for c in OE1.EMBED_CANDIDATES]
    for model in OE1.SCORED_MODELS + (OE1.JUDGE_MODEL,):
        assert model not in names
