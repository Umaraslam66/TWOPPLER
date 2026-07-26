"""Tests for the Stage 2 pilot driver (experiments/stage2_pilot.py).

Deterministic, offline, no GPU, no corpus read. The ssh/rsync/sacct layer is
exercised through its argv builders and a monkeypatched ``run``; nothing here
opens a socket. The end-to-end export/verify test builds a complete synthetic
pilot directory in ``tmp_path`` -- six subjects, one of them burned for Q-A --
so the C00292 exclusion is tested on a subject that HAS a full option set on
disk, which is the situation that actually exists in the repo.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from doppler import followup_render as F  # noqa: E402
from doppler import stage2_render as R  # noqa: E402


def _load_driver():
    spec = importlib.util.spec_from_file_location(
        "stage2_pilot_under_test", ROOT / "experiments/stage2_pilot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = _load_driver()


# ---------------------------------------------------------------------------
# Exchange building
# ---------------------------------------------------------------------------


def turn(idx, role, text, tid="T1", label="X"):
    return {"transcript_id": tid, "turn_idx": idx, "role": role,
            "speaker_label": label, "text": text, "resolved_label": None,
            "d32_program_host": None}


def test_exchange_pairs_host_with_the_guest_reply_it_drew():
    turns = [turn(0, "host", "Why now?"), turn(1, "guest", "Because of the audit.")]
    assert P.build_exchanges(turns) == [
        {"host_text": "Why now?", "guest_text": "Because of the audit."}]


def test_consecutive_guest_turns_join_into_one_exchange():
    turns = [turn(0, "host", "Why now?"),
             turn(1, "guest", "Because of the audit."),
             turn(2, "guest", "And nobody listened."),
             turn(3, "host", "Next question.")]
    out = P.build_exchanges(turns)
    assert len(out) == 1
    assert out[0]["guest_text"] == "Because of the audit. And nobody listened."


def test_an_other_speaker_breaks_a_guest_run_into_two_exchanges():
    turns = [turn(0, "host", "Why now?"),
             turn(1, "guest", "First half."),
             turn(2, "other", "A third party interjects."),
             turn(3, "guest", "Second half.")]
    out = P.build_exchanges(turns)
    assert len(out) == 2
    assert out[0] == {"host_text": "Why now?", "guest_text": "First half."}
    # The turn immediately before the second run is "other", so the host side
    # is empty and the exchange renders one line (SPEC D8 / T4).
    assert out[1] == {"host_text": "", "guest_text": "Second half."}


def test_host_side_is_empty_when_the_preceding_turn_is_not_a_host():
    turns = [turn(0, "other", "Announcer copy."), turn(1, "guest", "My answer.")]
    assert P.build_exchanges(turns) == [
        {"host_text": "", "guest_text": "My answer."}]


def test_a_guest_run_with_no_text_is_dropped_entirely():
    turns = [turn(0, "host", "Why now?"), turn(1, "guest", "   "),
             turn(2, "host", "Still there?"), turn(3, "guest", "Yes.")]
    out = P.build_exchanges(turns)
    assert out == [{"host_text": "Still there?", "guest_text": "Yes."}]


def test_a_trailing_guest_run_at_the_end_of_a_transcript_is_kept():
    turns = [turn(0, "host", "Last word?"), turn(1, "guest", "Goodbye.")]
    assert len(P.build_exchanges(turns)) == 1


def test_exchanges_are_built_in_turn_idx_order_not_list_order():
    turns = [turn(3, "guest", "second"), turn(2, "host", "q2"),
             turn(1, "guest", "first"), turn(0, "host", "q1")]
    out = P.build_exchanges(turns)
    assert [e["guest_text"] for e in out] == ["first", "second"]


def test_empty_turn_list_yields_no_exchanges():
    assert P.build_exchanges([]) == []


def test_segments_carry_date_and_program_and_sort_deterministically():
    turns = [turn(0, "host", "q", tid="B"), turn(1, "guest", "a", tid="B"),
             turn(0, "host", "q", tid="A"), turn(1, "guest", "a", tid="A")]
    split = {"grounding": [
        {"transcript_id": "B", "date": "2010-01-01", "program": "PROG B"},
        {"transcript_id": "A", "date": "2012-01-01", "program": "PROG A"}],
        "test": {"transcript_id": "Z"}}
    segs = P.build_segments(turns, split)
    assert [s["transcript_id"] for s in segs] == ["B", "A"]   # by date
    assert segs[0]["program"] == "PROG B"


def test_a_test_transcript_inside_the_grounding_turn_file_is_fatal():
    turns = [turn(0, "host", "q", tid="Z"), turn(1, "guest", "a", tid="Z")]
    split = {"grounding": [{"transcript_id": "Z", "date": "2010-01-01",
                            "program": "P"}],
             "test": {"transcript_id": "Z"}}
    with pytest.raises(SystemExit, match="must never enter grounding"):
        P.build_segments(turns, split)


# ---------------------------------------------------------------------------
# Sidecar idx joins
# ---------------------------------------------------------------------------


def test_join_by_idx_pairs_prompts_with_their_sidecar_rows():
    prompts = [{"idx": 0, "prompt": "p0"}, {"idx": 1, "prompt": "p1"}]
    metas = [{"idx": 1, "item_id": "b"}, {"idx": 0, "item_id": "a"}]
    out = P.join_by_idx(prompts, metas)
    assert [(r["idx"], r["prompt"], r["item_id"]) for r in out] == [
        (0, "p0", "a"), (1, "p1", "b")]


def test_join_by_idx_refuses_a_prompt_with_no_sidecar_row():
    with pytest.raises(SystemExit, match="no sidecar row"):
        P.join_by_idx([{"idx": 0, "prompt": "p"}], [])


def test_join_by_idx_refuses_a_sidecar_row_with_no_prompt():
    with pytest.raises(SystemExit, match="no prompt"):
        P.join_by_idx([], [{"idx": 7, "item_id": "x"}])


def test_join_by_idx_refuses_a_duplicated_sidecar_idx():
    with pytest.raises(SystemExit, match="duplicate idx"):
        P.join_by_idx([{"idx": 0, "prompt": "p"}],
                      [{"idx": 0, "a": 1}, {"idx": 0, "a": 2}])


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


GROUNDING = ("[Interview, 2011-03-02, MORNING EDITION]\n"
             "HOST: GUEST, why then?\n"
             "GUEST: Because the audit was buried and nobody would sign it.")

ITEM = {
    "item_id": "C99999:T1:2",
    "question": "Looking back, what did that episode teach you?",
    "answer": "You learn that paperwork is the only friend you have in this "
              "business and I kept copies of every single page after that.",
    "options": {
        "standard": [
            "You learn that paperwork is the only friend you have in this "
            "business and I kept copies of every single page after that.",
            "Honestly I would do it all again the same way.",
            "It taught me the press gets there first.",
            "Nothing really, these things happen everywhere."],
        "stripped": [
            "You learn that paperwork is the only friend you have in this "
            "business and I kept copies of every single page after that.",
            "Honestly I would do it all again the same way.",
            "It taught me the press gets there first.",
            "Nothing really, these things happen everywhere."],
    },
    "correct_index": 0,
}


def test_a_clean_twin_prompt_passes_both_guards():
    built = P.render_and_guard(
        "twin_redacted", "standard", ITEM, subject_name="Jane Smith",
        subject_variants=["Jane Smith"], grounding_block=GROUNDING)
    assert built["prompt_sha256"] == R.sha256(built["prompt"])
    assert "Smith" not in built["prompt"]


def test_the_question_is_redacted_not_only_the_excerpts():
    """Six of the eighteen real questions say the subject's name out loud."""
    leaky = dict(ITEM, question="Ms. Smith, what did that episode teach you?")
    built = P.render_and_guard("twin_redacted", "standard", leaky,
                               subject_name="Jane Smith",
                               subject_variants=["Jane Smith"],
                               grounding_block=GROUNDING)
    assert "Smith" not in built["prompt"]
    assert "GUEST, what did that episode teach you?" in built["prompt"]


def test_the_options_are_redacted_too():
    leaky = dict(ITEM)
    leaky["options"] = {
        "standard": ["Smith said the audit was fine."]
        + ITEM["options"]["standard"][1:],
        "stripped": ITEM["options"]["stripped"],
    }
    built = P.render_and_guard("twin_redacted", "standard", leaky,
                               subject_name="Jane Smith",
                               subject_variants=["Jane Smith"],
                               grounding_block=GROUNDING)
    assert "Smith" not in built["prompt"]


def test_the_guard_refuses_a_leaking_prompt_when_the_scrubber_is_bypassed(
        monkeypatch):
    """The guard is wired in, not decorative: disable the scrubber and it fires.

    Redaction and the guard use the same matcher, so a leak the scrubber could
    have removed can only be demonstrated by removing the scrubber. This is the
    test that would fail if someone deleted the ``assert_redacted`` call.
    """
    monkeypatch.setattr(P.R, "redact",
                        lambda text, variants, *a, **kw: text)
    leaky = dict(ITEM, question="Ms. Smith, what did that episode teach you?")
    with pytest.raises(ValueError, match="redaction failed"):
        P.render_and_guard("twin_redacted", "standard", leaky,
                           subject_name="Jane Smith",
                           subject_variants=["Jane Smith"],
                           grounding_block=GROUNDING)


def test_export_refuses_when_the_true_answer_leaks_into_the_grounding():
    leaking_block = (
        "[Interview, 2011-03-02, MORNING EDITION]\n"
        "HOST: And what did you learn?\n"
        "GUEST: You learn that paperwork is the only friend you have in this "
        "business and I kept copies of every single page after that.")
    with pytest.raises(ValueError, match="leaked into the grounding"):
        P.render_and_guard("twin_redacted", "standard", ITEM,
                           subject_name="Jane Smith",
                           subject_variants=["Jane Smith"],
                           grounding_block=leaking_block)


def test_the_imposter_arm_asserts_the_subject_list_as_well_as_the_donor_list(
        monkeypatch):
    """Asserting only the donor's name is the dangerous half-measure.

    The excerpts here are clean of the donor's name, so the donor assertion
    passes; only the subject assertion can catch the subject's name sitting in
    the question, which is the leak that makes an imposter prompt read as a twin.
    """
    monkeypatch.setattr(P.R, "redact",
                        lambda text, variants, *a, **kw: text)
    leaky = dict(ITEM, question="Ms. Smith, what did that teach you?")
    with pytest.raises(ValueError, match="redaction failed"):
        P.render_and_guard("imposter_redacted", "standard", leaky,
                           subject_name="Jane Smith",
                           subject_variants=["Jane Smith"],
                           grounding_block=GROUNDING,
                           donor_variants=["Chidi Okonkwo"])


def test_the_imposter_arm_asserts_the_donor_list_too():
    donor_block = GROUNDING.replace("GUEST, why then?", "Okonkwo, why then?")
    with pytest.raises(ValueError, match="redaction failed"):
        P.render_and_guard("imposter_redacted", "standard", ITEM,
                           subject_name="Jane Smith",
                           subject_variants=["Jane Smith"],
                           grounding_block=donor_block,
                           donor_variants=["Chidi Okonkwo"])


def test_a_named_arm_differs_from_its_redacted_twin_by_exactly_the_name_line():
    named = P.render_and_guard(
        "twin_named", "standard", ITEM, subject_name="Jane Smith",
        subject_variants=["Jane Smith"], grounding_block=GROUNDING)
    plain = P.render_and_guard(
        "twin_redacted", "standard", ITEM, subject_name="Jane Smith",
        subject_variants=["Jane Smith"], grounding_block=GROUNDING)
    line = R.TWIN_NAME_LINE.format(name="Jane Smith")
    assert named["prompt"].replace(f"{line}\n\n", "", 1) == plain["prompt"]


def test_zeroinfo_arms_carry_no_excerpts():
    built = P.render_and_guard(
        "zeroinfo_redacted", "standard", ITEM, subject_name="Jane Smith",
        subject_variants=["Jane Smith"], grounding_block=None)
    assert R.EXCERPTS_HEADER not in built["prompt"]
    assert "[Interview," not in built["prompt"]


def test_excerpt_block_extracts_only_the_past_interviews_section():
    built = P.render_and_guard(
        "twin_redacted", "standard", ITEM, subject_name="Jane Smith",
        subject_variants=["Jane Smith"], grounding_block=GROUNDING)
    block = P.excerpt_block(built["prompt"])
    assert block.startswith("[Interview,")
    assert R.LATER_HEADER not in block
    assert ITEM["options"]["standard"][1] not in block


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def meta(item_id="i1", cid="C1", arm="twin_redacted", variant="standard",
         correct=0):
    return {"item_id": item_id, "canonical_id": cid, "arm": arm,
            "variant": variant, "correct_index": correct, "n_options": 4,
            "donor_id": None}


def test_score_record_reads_argmax_and_probability_mass():
    rec = P.score_record(meta(correct=1), "A: 0.1 B: 0.6 C: 0.2 D: 0.1")
    assert rec["parse_failure"] is False
    assert rec["argmax_index"] == 1
    assert rec["argmax_correct"] is True
    assert rec["prob_mass_correct"] == pytest.approx(0.6)


def test_score_record_marks_a_wrong_argmax_but_still_reports_the_mass():
    rec = P.score_record(meta(correct=0), "A: 0.2 B: 0.6 C: 0.1 D: 0.1")
    assert rec["argmax_correct"] is False
    assert rec["prob_mass_correct"] == pytest.approx(0.2)


def test_score_record_records_a_parse_failure_without_a_retry():
    rec = P.score_record(meta(), "I am not going to answer that.")
    assert rec["parse_failure"] is True
    assert rec["argmax_correct"] is None
    assert rec["prob_mass_correct"] is None


def test_score_record_treats_a_missing_completion_as_a_parse_failure():
    assert P.score_record(meta(), None)["parse_failure"] is True


def test_accuracy_excludes_parse_failures_from_both_denominators():
    recs = [P.score_record(meta(correct=0), "A: 0.7 B: 0.1 C: 0.1 D: 0.1"),
            P.score_record(meta(correct=0), "A: 0.1 B: 0.7 C: 0.1 D: 0.1"),
            P.score_record(meta(correct=0), "garbage")]
    acc = P.accuracy(recs)
    assert acc["n_attempted"] == 3
    assert acc["n"] == 2
    assert acc["n_parse_failures"] == 1
    assert acc["argmax_accuracy"] == pytest.approx(0.5)
    assert acc["prob_mass_correct"] == pytest.approx(0.4)


def test_accuracy_of_nothing_is_none_not_zero():
    acc = P.accuracy([])
    assert acc["n"] == 0
    assert acc["argmax_accuracy"] is None
    assert acc["prob_mass_correct"] is None


# ---------------------------------------------------------------------------
# Adversarial filter (A4.3)
# ---------------------------------------------------------------------------


def test_adversarial_filter_drops_items_the_zero_information_arm_solved():
    recs = [
        P.score_record(meta("i1", arm="zeroinfo_redacted", correct=0),
                       "A: 0.7 B: 0.1 C: 0.1 D: 0.1"),   # solved -> dropped
        P.score_record(meta("i2", arm="zeroinfo_redacted", correct=0),
                       "A: 0.1 B: 0.7 C: 0.1 D: 0.1"),   # missed -> kept
        P.score_record(meta("i1", arm="twin_redacted", correct=0),
                       "A: 0.7 B: 0.1 C: 0.1 D: 0.1"),
        P.score_record(meta("i2", arm="twin_redacted", correct=0),
                       "A: 0.7 B: 0.1 C: 0.1 D: 0.1"),
    ]
    assert P.adversarial_keep(recs, "standard") == {"i2"}


def test_adversarial_filter_keeps_an_item_the_floor_arm_failed_to_parse():
    recs = [
        P.score_record(meta("i1", arm="zeroinfo_redacted", correct=0), "junk"),
        P.score_record(meta("i1", arm="twin_redacted", correct=0),
                       "A: 0.7 B: 0.1 C: 0.1 D: 0.1"),
    ]
    assert P.adversarial_keep(recs, "standard") == {"i1"}


def test_adversarial_filter_is_computed_within_one_option_variant():
    recs = [
        P.score_record(meta("i1", arm="zeroinfo_redacted", variant="standard",
                            correct=0), "A: 0.7 B: 0.1 C: 0.1 D: 0.1"),
        P.score_record(meta("i1", arm="zeroinfo_redacted", variant="stripped",
                            correct=0), "A: 0.1 B: 0.7 C: 0.1 D: 0.1"),
    ]
    assert P.adversarial_keep(recs, "standard") == set()
    assert P.adversarial_keep(recs, "stripped") == {"i1"}


# ---------------------------------------------------------------------------
# Contamination meter + paired lift
# ---------------------------------------------------------------------------


def test_contamination_meter_is_named_minus_redacted_per_subject():
    recs = [
        P.score_record(meta("i1", "C1", "zeroinfo_named", correct=0),
                       "A: 0.8 B: 0.1 C: 0.05 D: 0.05"),
        P.score_record(meta("i1", "C1", "zeroinfo_redacted", correct=0),
                       "A: 0.3 B: 0.4 C: 0.2 D: 0.1"),
    ]
    meter = P.contamination_meter(recs)["C1"]["standard"]
    assert meter["delta_argmax"] == pytest.approx(1.0)      # 1.0 - 0.0
    assert meter["delta_prob_mass"] == pytest.approx(0.5)   # 0.8 - 0.3


def test_contamination_meter_is_none_when_one_side_did_not_parse():
    recs = [
        P.score_record(meta("i1", "C1", "zeroinfo_named", correct=0),
                       "A: 0.8 B: 0.1 C: 0.05 D: 0.05"),
        P.score_record(meta("i1", "C1", "zeroinfo_redacted", correct=0), "junk"),
    ]
    meter = P.contamination_meter(recs)["C1"]["standard"]
    assert meter["delta_argmax"] is None


def test_paired_lift_averages_over_subjects_and_reports_no_p_value():
    recs = []
    for cid, twin_ok in (("C1", True), ("C2", False)):
        recs.append(P.score_record(
            meta("i" + cid, cid, "twin_redacted", correct=0),
            "A: 0.7 B: 0.1 C: 0.1 D: 0.1" if twin_ok
            else "A: 0.1 B: 0.7 C: 0.1 D: 0.1"))
        recs.append(P.score_record(
            meta("i" + cid, cid, "zeroinfo_redacted", correct=0),
            "A: 0.1 B: 0.7 C: 0.1 D: 0.1"))
    lift = P.paired_lift(recs, "twin_redacted", "zeroinfo_redacted", "standard")
    assert lift["n_subjects"] == 2
    assert lift["mean_argmax_delta"] == pytest.approx(0.5)   # (1-0 + 0-0)/2
    assert "p" not in lift and "t_p" not in lift
    assert "not powered" in lift["note"]


def test_paired_lift_honours_the_adversarial_keep_set():
    recs = [
        P.score_record(meta("keep", "C1", "twin_redacted", correct=0),
                       "A: 0.7 B: 0.1 C: 0.1 D: 0.1"),
        P.score_record(meta("keep", "C1", "zeroinfo_redacted", correct=0),
                       "A: 0.1 B: 0.7 C: 0.1 D: 0.1"),
        P.score_record(meta("drop", "C1", "twin_redacted", correct=0),
                       "A: 0.1 B: 0.7 C: 0.1 D: 0.1"),
        P.score_record(meta("drop", "C1", "zeroinfo_redacted", correct=0),
                       "A: 0.7 B: 0.1 C: 0.1 D: 0.1"),
    ]
    full = P.paired_lift(recs, "twin_redacted", "zeroinfo_redacted", "standard")
    kept = P.paired_lift(recs, "twin_redacted", "zeroinfo_redacted", "standard",
                         {"keep"})
    assert full["mean_argmax_delta"] == pytest.approx(0.0)
    assert kept["mean_argmax_delta"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Cost entries
# ---------------------------------------------------------------------------


def test_cost_entries_are_written_only_when_node_time_was_spent(tmp_path,
                                                                monkeypatch):
    written = []
    monkeypatch.setattr(P, "append_cost_log",
                        lambda entry, path: written.append((entry, path)))
    pred = [dict(P.score_record(meta(), "A: 0.7 B: 0.1 C: 0.1 D: 0.1"),
                 tokens_in=1000, tokens_out=40)]
    clf = [{"canonical_id": "C1", "parse_failure": False,
            "tokens_in": 500, "tokens_out": 10}]
    P._log_cost(pred, clf, 0.25)
    assert len(written) == 2
    entry = written[0][0]
    assert entry["run_id"] == "stage2_pilot/prediction"
    assert entry["backend"] == "leonardo-batch"
    assert entry["cost_usd"] is None          # no price for a batch model
    assert entry["node_hours"] == pytest.approx(0.25 * 40 / 50)
    assert entry["n_calls"] == 1
    assert sum(e["node_hours"] for e, _ in written) == pytest.approx(0.25)


def test_sum_node_hours_counts_one_engine_init_and_every_generation_window():
    summaries = [{"engine_init_seconds": 200.0, "generation_wall_seconds": 100.0},
                 {"engine_init_seconds": 200.0, "generation_wall_seconds": 260.0}]
    assert P._sum_node_hours(summaries) == round(560 / 3600, 4)


def test_sum_node_hours_is_none_when_the_job_never_ran():
    assert P._sum_node_hours([]) is None


# ---------------------------------------------------------------------------
# The ssh / rsync / sacct layer (mocked)
# ---------------------------------------------------------------------------


def test_ssh_argv_uses_batchmode_so_it_can_never_prompt():
    assert P.ssh_argv("echo ok") == ["ssh", "-o", "BatchMode=yes", "leonardo",
                                     "echo ok"]


def test_rsync_argv_targets_the_node_run_directory():
    argv = P.rsync_argv(Path("/local/prompts.jsonl"), f"{P.NODE_RUN}/")
    assert argv[0] == "rsync"
    assert argv[-1] == f"leonardo:{P.NODE_RUN}/"


def test_ssh_ok_is_true_only_on_the_ok_handshake(monkeypatch):
    monkeypatch.setattr(P, "run", lambda argv, check=True: "ok\n")
    assert P.ssh_ok() is True
    monkeypatch.setattr(P, "run", lambda argv, check=True: "")
    assert P.ssh_ok() is False


def test_parse_sacct_converts_elapsed_and_node_count_to_node_hours():
    out = P.parse_sacct("123456|COMPLETED|00:12:30|1|0:0\n")
    assert out["job_id"] == "123456"
    assert out["state"] == "COMPLETED"
    assert out["node_hours"] == round(750 / 3600, 4)


def test_parse_sacct_handles_days_and_multiple_nodes():
    out = P.parse_sacct("9|COMPLETED|1-00:00:00|2|0:0")
    assert out["node_hours"] == pytest.approx(48.0)


def test_parse_sacct_returns_none_on_empty_output():
    assert P.parse_sacct("") is None


# ---------------------------------------------------------------------------
# End to end on a synthetic pilot directory
# ---------------------------------------------------------------------------


#: Three disjoint filler vocabularies. Guard (a) refuses a grounding block that
#: shares a 10-word run with the true answer, so the fixture's grounding, its
#: true answers and its distractors must not share long runs by accident.
GROUND_FILLER = " ".join(f"gx{i}" for i in range(40))
ANSWER_FILLER = " ".join(f"ay{i}" for i in range(40))
DISTRACTOR_FILLER = " ".join(f"dz{i}" for i in range(40))


def _mk_turns(tid, n_pairs, who):
    rows = []
    for k in range(n_pairs):
        rows.append({"transcript_id": tid, "turn_idx": 2 * k, "role": "host",
                     "speaker_label": "ANCHOR, host", "resolved_label": None,
                     "d32_program_host": None,
                     "text": f"Host question {k} on {tid}?"})
        rows.append({"transcript_id": tid, "turn_idx": 2 * k + 1,
                     "role": "guest", "speaker_label": who.upper(),
                     "resolved_label": None, "d32_program_host": None,
                     "text": f"Guest reply {k} from {tid}. {GROUND_FILLER}"})
    return rows


def _write_person(base: Path, cid: str, name: str, n_items: int):
    """One subject tree: split.json, grounding turns, items, option sets."""
    base.mkdir(parents=True, exist_ok=True)
    grounding = _mk_turns(f"{cid}-G1", 4, name) + _mk_turns(f"{cid}-G2", 4, name)
    (base / "grounding_turns.jsonl").write_text(
        "\n".join(json.dumps(r) for r in grounding) + "\n", encoding="utf-8")
    split = {
        "canonical_id": cid, "canonical_name": name, "rule": "synthetic",
        "grounding": [
            {"cluster_id": "c1", "transcript_id": f"{cid}-G1",
             "date": "2011-01-01", "program": "PROG ONE", "title": "t1"},
            {"cluster_id": "c2", "transcript_id": f"{cid}-G2",
             "date": "2012-01-01", "program": "PROG TWO", "title": "t2"}],
        "test": {"cluster_id": "c3", "transcript_id": f"{cid}-T",
                 "date": "2013-01-01", "program": "PROG THREE", "title": "t3"},
        "excluded_same_date": [],
    }
    (base / "split.json").write_text(json.dumps(split), encoding="utf-8")

    items, options = [], []
    for k in range(n_items):
        item_id = f"{cid}:{cid}-T:{k}"
        answer = f"True answer {k} for {cid}. {ANSWER_FILLER}"
        items.append({"item_id": item_id, "canonical_id": cid,
                      "transcript_id": f"{cid}-T", "q_turn_idx": k,
                      # The question names the subject on purpose: six of the
                      # real eighteen do, and redaction has to remove it.
                      "question": f"{name}, what did you make of item {k}?",
                      "answer": answer, "answer_words": len(answer.split()),
                      "flags": []})
        opts = [{"text": answer, "kind": "true", "source_canonical_id": cid,
                 "source_transcript_id": f"{cid}-T", "answer_words": 40,
                 "entity_density": 0.01, "question_similarity": None}]
        for d in range(3):
            opts.append({"text": f"Distractor {d} for item {k}. {DISTRACTOR_FILLER}",
                         "kind": "distractor", "source_canonical_id": "C09999",
                         "source_transcript_id": "D-1", "answer_words": 40,
                         "entity_density": 0.01, "question_similarity": 0.05})
        options.append({"item_id": item_id, "options": opts,
                        "correct_index": 0, "relax_rung": 0,
                        "options_stripped": [o["text"] for o in opts]})
    (base / "qa_items.jsonl").write_text(
        "\n".join(json.dumps(r) for r in items) + ("\n" if items else ""),
        encoding="utf-8")
    (base / "distractors.jsonl").write_text(
        "\n".join(json.dumps(r) for r in options) + ("\n" if options else ""),
        encoding="utf-8")


#: Invented names, deliberately made of nonsense tokens. T4's redactor expands
#: every variant to its bare name tokens, so a synthetic surname that is also an
#: ordinary English word ("One") would be scrubbed out of the template's own
#: prose and the guard would trip on the fixture rather than on the code.
SUBJECTS = [
    ("C10001", "Zorvath Quilliman", "long-tail", 0, False),
    ("C10002", "Brastock Venneby", "long-tail", 1, True),      # burned for Q-A
    ("C10003", "Chalmot Drexworth", "has-page", 2, False),
    ("C10004", "Dornith Falquay", "long-tail", 3, False),
    ("C10005", "Ekwith Grumbold", "has-page", 4, False),
    ("C10006", "Fanther Holvist", "has-page", 5, False),
]
DONORS = {"C10001": "C20001", "C10002": "C20002", "C10003": "C20003",
          "C10004": "C20004", "C10005": "C20005", "C10006": "C20006"}
DONOR_NAMES = {
    "C20001": "Ilvaro Jantwick", "C20002": "Kesmir Lundhaven",
    "C20003": "Morvath Nexbury", "C20004": "Orlaith Pruvane",
    "C20005": "Quenlow Rathmar", "C20006": "Suvrith Tolquist",
}


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    root = tmp_path / "stage2_pilot"
    root.mkdir()
    (root / "dev_subjects.json").write_text(json.dumps({
        "seed": 47, "rule": "synthetic", "drawn_at": "2026-07-26",
        "n_eligible": 6,
        "subjects": [
            dict({"canonical_id": cid, "canonical_name": name,
                  "wiki_status": wiki, "shuffle_pos": pos},
                 **({"burned_for_qa": True} if burned else {}))
            for cid, name, wiki, pos, burned in SUBJECTS],
        "burned": [], "burned_for_qa": ["C10002"],
        "replacements": [{"burned_canonical_id": "C10002",
                          "burned_shuffle_pos": 1, "stratum": "long-tail",
                          "mode": "retained_in_place", "reason": "synthetic",
                          "replaced_by": "C10004"}],
    }), encoding="utf-8")
    for cid, name, _wiki, _pos, burned in SUBJECTS:
        # The burned subject has a full option set on disk -- exactly the
        # situation C00292 is in -- so the exclusion has something to exclude.
        _write_person(root / "subjects" / cid, cid, name, 2)
    for cid, donor in DONORS.items():
        _write_person(root / "donors" / donor, donor, DONOR_NAMES[donor], 0)
    (root / "imposter_pairs.json").write_text(
        json.dumps({"method": "synthetic", "pairs": DONORS}), encoding="utf-8")

    rows = {cid: {"canonical_id": cid, "canonical_name": name,
                  "variants": [name]}
            for cid, name, _w, _p, _b in SUBJECTS}
    rows.update({d: {"canonical_id": d, "canonical_name": n, "variants": [n]}
                 for d, n in DONOR_NAMES.items()})
    monkeypatch.setattr(P, "pool_rows", lambda: rows)
    return root


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_export_then_verify_round_trips_on_a_synthetic_pilot(pilot, capsys):
    assert P.cmd_export(Args(pilot_dir=pilot, force=False)) == 0
    assert P.cmd_verify(Args(pilot_dir=pilot)) == 0
    doc = json.loads((pilot / "exports/export_manifest.json").read_text())
    # 5 Q-A subjects x 2 items = 10 items; x 5 arms x 2 variants = 100 prompts.
    assert doc["n_qa_subjects"] == 5
    assert doc["n_items"] == 10
    assert doc["prediction_prompts_total"] == 100
    for arm in P.ARMS:
        for variant in P.VARIANTS:
            assert doc["files"][P.set_name(arm, variant)]["n_prompts"] == 10


def test_the_burned_subject_is_in_no_prediction_set_but_is_in_the_classifier(
        pilot):
    P.cmd_export(Args(pilot_dir=pilot, force=False))
    export = pilot / "exports"
    for arm in P.ARMS:
        for variant in P.VARIANTS:
            metas = json.loads("[" + ",".join(
                (export / f"meta_{P.set_name(arm, variant)}.jsonl")
                .read_text().strip().splitlines()) + "]")
            assert all(m["canonical_id"] != "C10002" for m in metas)
    clf = (export / "meta_classify.jsonl").read_text()
    assert '"C10002"' in clf


def test_export_refuses_to_overwrite_without_force(pilot):
    P.cmd_export(Args(pilot_dir=pilot, force=False))
    with pytest.raises(SystemExit, match="already exists"):
        P.cmd_export(Args(pilot_dir=pilot, force=False))
    assert P.cmd_export(Args(pilot_dir=pilot, force=True)) == 0


def test_verify_catches_a_tampered_prompt_file(pilot):
    P.cmd_export(Args(pilot_dir=pilot, force=False))
    path = pilot / "exports/prompts_pred_twin_redacted_standard.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["prompt"] = rows[0]["prompt"] + "\nZorvath Quilliman was here."
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                    encoding="utf-8")
    with pytest.raises(SystemExit, match="sha256"):
        P.cmd_verify(Args(pilot_dir=pilot))


def test_verify_catches_a_name_leak_even_when_the_digests_are_reconciled(pilot):
    P.cmd_export(Args(pilot_dir=pilot, force=False))
    export = pilot / "exports"
    path = export / "prompts_pred_twin_redacted_standard.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["prompt"] += "\nZorvath Quilliman said so."
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                    encoding="utf-8")
    # Re-point the sidecar digest and the manifest so only the guard can fail.
    mpath = export / "meta_pred_twin_redacted_standard.jsonl"
    metas = [json.loads(line) for line in mpath.read_text().splitlines()]
    metas[0]["prompt_sha256"] = R.sha256(rows[0]["prompt"])
    mpath.write_text("\n".join(json.dumps(m) for m in metas) + "\n",
                     encoding="utf-8")
    doc = json.loads((export / "export_manifest.json").read_text())
    doc["files"]["pred_twin_redacted_standard"]["prompts_sha256"] = \
        P.sha256_file(path)
    doc["files"]["pred_twin_redacted_standard"]["meta_sha256"] = \
        P.sha256_file(mpath)
    (export / "export_manifest.json").write_text(json.dumps(doc),
                                                 encoding="utf-8")
    with pytest.raises(ValueError, match="redaction failed"):
        P.cmd_verify(Args(pilot_dir=pilot))


def test_plan_projects_and_stays_inside_the_abort_threshold(pilot, capsys):
    assert P.cmd_plan(Args(pilot_dir=pilot)) == 0
    out = capsys.readouterr().out
    assert "PILOT" in out
    assert "burned_for_qa C10002 excluded" in out


def test_projection_is_deterministic_and_counts_output_tokens_at_the_cap(pilot):
    build = P.build_all(pilot)
    a, b = P.projection(build), P.projection(build)
    assert a["jobs"] == b["jobs"]
    pred_rows = [r for rows in build["prediction"]["sets"].values() for r in rows]
    assert a["prediction"]["tokens_out_cap"] == \
        len(pred_rows) * R.MAX_OUTPUT_TOKENS
    assert a["classifier"]["tokens_out_cap"] == \
        len(build["classifier"]["cases"]) * F.MAX_OUTPUT_TOKENS


def test_context_check_refuses_a_prompt_that_would_not_fit(pilot, monkeypatch):
    build = P.build_all(pilot)
    monkeypatch.setattr(P, "MAX_MODEL_LEN", 128)
    with pytest.raises(SystemExit, match="does not fit MAX_MODEL_LEN"):
        P.context_check(build)


def test_the_smoke_slice_spans_every_prompt_set(pilot):
    build = P.build_all(pilot)
    rows = P.smoke_slice(build)
    sets = {r["source_set"] for r in rows}
    assert sets == {P.set_name(a, v) for a in P.ARMS for v in P.VARIANTS} | \
        {"classify"}
    assert len(rows) == len(P.ARMS) * len(P.VARIANTS) * P.SMOKE_PER_SET \
        + P.SMOKE_CLASSIFY


def test_bootstrap_writes_two_sbatch_files_with_the_right_qos(pilot):
    P.cmd_export(Args(pilot_dir=pilot, force=False))
    assert P.cmd_bootstrap(Args(pilot_dir=pilot)) == 0
    smoke = (pilot / "stage2_pilot_smoke.sbatch").read_text()
    full = (pilot / "stage2_pilot_full.sbatch").read_text()
    assert f"--qos={P.SMOKE_QOS}" in smoke
    assert "--qos=" not in full
    for text in (smoke, full):
        assert "--gpus-per-node=4" in text
        assert f"--tp {P.TP}" in text
        assert f"--max-model-len {P.MAX_MODEL_LEN}" in text
        assert "--temperature 0.0" in text
    # One engine init: a single batch_generate.py invocation per job.
    assert full.count("python jobs/batch_generate.py") == 1
    assert all(f'"{n}"' in full for n in P.full_set_names())


def test_bootstrap_refuses_when_the_projection_is_over_the_threshold(pilot,
                                                                     monkeypatch):
    P.cmd_export(Args(pilot_dir=pilot, force=False))
    doc = json.loads((pilot / "exports/export_manifest.json").read_text())
    doc["projection"]["total_projected_node_hours"] = 99.0
    (pilot / "exports/export_manifest.json").write_text(json.dumps(doc),
                                                        encoding="utf-8")
    with pytest.raises(SystemExit, match="exceeds"):
        P.cmd_bootstrap(Args(pilot_dir=pilot))


def test_ingest_scores_completions_and_writes_analysis(pilot, monkeypatch):
    P.cmd_export(Args(pilot_dir=pilot, force=False))
    nodedir = pilot / "node"
    nodedir.mkdir()
    export = pilot / "exports"
    for arm in P.ARMS:
        for variant in P.VARIANTS:
            name = P.set_name(arm, variant)
            metas = [json.loads(line) for line in
                     (export / f"meta_{name}.jsonl").read_text().splitlines()]
            rows = [{"idx": m["idx"],
                     "text": "A: 0.7 B: 0.1 C: 0.1 D: 0.1",
                     "tokens_in": 100, "tokens_out": 20} for m in metas]
            (nodedir / f"completions_{name}.jsonl").write_text(
                "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    metas = [json.loads(line) for line in
             (export / "meta_classify.jsonl").read_text().splitlines()]
    (nodedir / "completions_classify.jsonl").write_text(
        "\n".join(json.dumps({"idx": m["idx"],
                              "text": "LABEL: FOLLOW-UP\nWHY: it probes.",
                              "tokens_in": 60, "tokens_out": 9})
                  for m in metas) + "\n", encoding="utf-8")
    (nodedir / "completions_classify.jsonl.summary.json").write_text(
        json.dumps({"engine_init_seconds": 200.0,
                    "generation_wall_seconds": 160.0}), encoding="utf-8")
    logged = []
    monkeypatch.setattr(P, "append_cost_log",
                        lambda entry, path: logged.append(entry))

    assert P.cmd_ingest(Args(pilot_dir=pilot, nodedir=str(nodedir))) == 0
    analysis = json.loads((pilot / "analysis.json").read_text())
    # Every option set puts the true answer at index 0 and every completion
    # picks A, so everything is correct and the lift is exactly zero.
    block = analysis["accuracy"]["standard"]["unfiltered"]
    assert block["twin_redacted"]["argmax_accuracy"] == pytest.approx(1.0)
    assert block["twin_redacted"]["prob_mass_correct"] == pytest.approx(0.7)
    assert analysis["accuracy"]["standard"]["adversarial_filter"][
        "n_items_kept"] == 0
    assert analysis["classifier"]["parse_failure_rate"] == 0.0
    assert analysis["total_cost"]["cost_usd"] == 0.0
    assert analysis["total_cost"]["api_calls"] == 0
    assert len(logged) == 2
    assert P.cmd_report(Args(pilot_dir=pilot)) == 0
    report = (pilot / "PILOT_REPORT.md").read_text()
    assert P.PILOT_BANNER in report
    assert "no significance test" in report.lower() or "not powered" in report


def test_ingest_records_a_parse_failure_rather_than_re_asking(pilot,
                                                             monkeypatch):
    """batch_generate.py has no re-ask hook, so a bad reply is just recorded."""
    P.cmd_export(Args(pilot_dir=pilot, force=False))
    nodedir = pilot / "node"
    nodedir.mkdir()
    export = pilot / "exports"
    name = P.set_name("twin_redacted", "standard")
    metas = [json.loads(line) for line in
             (export / f"meta_{name}.jsonl").read_text().splitlines()]
    (nodedir / f"completions_{name}.jsonl").write_text(
        "\n".join(json.dumps({"idx": m["idx"], "text": "no idea",
                              "tokens_in": 10, "tokens_out": 3})
                  for m in metas) + "\n", encoding="utf-8")
    monkeypatch.setattr(P, "append_cost_log", lambda entry, path: None)
    P.cmd_ingest(Args(pilot_dir=pilot, nodedir=str(nodedir)))
    rows = [json.loads(line) for line in
            (pilot / "records" / f"{name}.jsonl").read_text().splitlines()]
    assert all(r["parse_failure"] for r in rows)
    # No duplicated idx: a retry would have shown up as a second row.
    assert len({r["idx"] for r in rows}) == len(rows)


# ---------------------------------------------------------------------------
# The real committed artifacts
# ---------------------------------------------------------------------------


def test_the_real_draw_has_six_subjects_and_exactly_one_burned_for_qa():
    subjects = P.dev_subjects()
    assert len(subjects) == 6
    burned = [s["canonical_id"] for s in subjects if s.get("burned_for_qa")]
    assert burned == [P.BURNED_FOR_QA]
    assert len(P.prediction_subjects(subjects)) == 5
    assert len(P.classifier_subjects(subjects)) == 6


def test_prediction_subjects_refuses_a_draw_with_nothing_burned():
    with pytest.raises(SystemExit, match="burned_for_qa"):
        P.prediction_subjects([{"canonical_id": "C1"}])
