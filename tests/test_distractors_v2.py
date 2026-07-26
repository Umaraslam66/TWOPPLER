"""Tests for SPEC v1.8 D6-v2 (src/doppler/distractors_v2.py).

Deterministic, offline, synthetic fixtures only. Nothing here reads the corpus,
the candidate pool or any committed artifact.

The property every test is really defending: a v2 option set must be four
answers from ONE person, none of them from the test interview, none of them
quotable from the context the twin arm is given, and none of them a second
copy of the true answer. Everything else is bookkeeping.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from doppler import distractors_v2 as D2  # noqa: E402
from doppler import stage2_render as R  # noqa: E402

FILLER = " ".join(f"w{i}" for i in range(40))
OTHER_FILLER = " ".join(f"q{i}" for i in range(40))


def mk_pool_row(tid, q_idx, question, answer, *, substantive=True, cid="C1"):
    return D2.pool_row(
        {"item_id": f"{cid}:{tid}:{q_idx}", "canonical_id": cid,
         "transcript_id": tid, "q_turn_idx": q_idx, "question": question,
         "answer": answer, "answer_words": len(answer.split()), "flags": []},
        substantive=substantive, cluster_id="cl1", date="2011-01-01",
        program="PROG")


def mk_item(item_id, question, answer, cid="C1", tid="C1-TEST"):
    return {"item_id": item_id, "canonical_id": cid, "transcript_id": tid,
            "q_turn_idx": 3, "question": question, "answer": answer,
            "answer_words": len(answer.split()), "flags": []}


# ---------------------------------------------------------------------------
# 1. The pool
# ---------------------------------------------------------------------------


def _subject_row(tids_clusters):
    return {"canonical_id": "C1", "canonical_name": "Zorvath Quilliman",
            "variants": ["Zorvath Quilliman"],
            "transcripts": [
                {"transcript_id": tid, "cluster_id": cl, "date": "2011-01-01",
                 "program": "PROG", "substantive": sub}
                for tid, cl, sub in tids_clusters]}


def test_pool_sources_drop_the_blocked_clusters_and_sort_by_transcript_id():
    row = _subject_row([("T3", "cl3", True), ("T1", "cl1", True),
                        ("T2", "cl2", False)])
    got = D2.pool_sources(row, ["cl3"])
    assert [t["transcript_id"] for t in got] == ["T1", "T2"]


def test_non_substantive_transcripts_are_eligible_pool_sources():
    row = _subject_row([("T1", "cl1", False)])
    assert [t["transcript_id"] for t in D2.pool_sources(row, [])] == ["T1"]


def _record(tid, pairs):
    # D4 drops a transcript's first host turn when the guest has not spoken
    # yet, so the fixture opens on a guest greeting; without it every
    # single-pair transcript would yield nothing for the wrong reason.
    speakers, utts = ["ZORVATH QUILLIMAN"], ["Thanks for having me."]
    for host, guest in pairs:
        speakers.append("ANCHOR, host")
        utts.append(host)
        speakers.append("ZORVATH QUILLIMAN")
        utts.append(guest)
    return {"id": tid, "program": "PROG", "date": "2011-01-01",
            "speaker": speakers, "utt": utts}


def test_harvest_runs_d4_per_transcript_and_tags_the_source():
    row = _subject_row([("T1", "cl1", True), ("T2", "cl2", False)])
    records = {
        "T1": _record("T1", [("Why did the vote fail so badly?",
                              "Because of the audit. " + FILLER)]),
        "T2": _record("T2", [("How would you describe the mood there?",
                              "It was tense throughout. " + OTHER_FILLER)]),
    }
    pool = D2.harvest_answer_pool(row, records, [])
    assert len(pool) == 2
    by_tid = {p["source_transcript_id"]: p for p in pool}
    assert by_tid["T1"]["source_substantive"] is True
    assert by_tid["T2"]["source_substantive"] is False
    assert by_tid["T1"]["source_canonical_id"] == "C1"
    assert by_tid["T1"]["bucket"] in ("Z", "L", "H")


def test_harvest_reports_a_transcript_it_could_not_fetch():
    row = _subject_row([("T1", "cl1", True)])
    seen = []
    pool = D2.harvest_answer_pool(row, {}, [], on_transcript=lambda *a: seen.append(a))
    assert pool == []
    assert seen[0][0] == "T1" and seen[0][3] == "record not fetched"


def test_harvest_never_touches_a_blocked_cluster():
    row = _subject_row([("T1", "cl1", True), ("TEST", "clT", True)])
    records = {"T1": _record("T1", [("Why did the vote fail so badly?",
                                     "Because of the audit. " + FILLER)]),
               "TEST": _record("TEST", [("What happened at the hearing then?",
                                         "Everything collapsed. " + FILLER)])}
    pool = D2.harvest_answer_pool(row, records, ["clT"])
    assert {p["source_transcript_id"] for p in pool} == {"T1"}


# ---------------------------------------------------------------------------
# 2. Dedup + anti-leak + ambiguity
# ---------------------------------------------------------------------------


def test_dedupe_drops_a_reaired_copy_and_keeps_the_first_by_source_order():
    answer = "Because of the audit. " + FILLER
    pool = [mk_pool_row("T2", 1, "Q one here now please?", answer),
            mk_pool_row("T1", 1, "Q one here now please?", answer)]
    kept, dropped = D2.dedupe_pool(pool)
    assert len(kept) == 1 and len(dropped) == 1
    assert kept[0]["source_transcript_id"] == "T1"      # sorted, not list order
    assert dropped[0]["duplicate_of"] == "T1:1"


def test_dedupe_keeps_two_genuinely_different_answers():
    pool = [mk_pool_row("T1", 1, "Q?", "First answer. " + FILLER),
            mk_pool_row("T2", 1, "Q?", "Second answer. " + OTHER_FILLER)]
    kept, dropped = D2.dedupe_pool(pool)
    assert len(kept) == 2 and dropped == []


def test_anti_leak_excludes_an_answer_quotable_from_the_rendered_grounding():
    answer = "Because of the audit. " + FILLER
    grounding = "HOST: earlier\nGUEST: " + answer
    pool = [mk_pool_row("T1", 1, "Q?", answer),
            mk_pool_row("T2", 1, "Q?", "Nothing in common. " + OTHER_FILLER)]
    keep, excluded = D2.anti_leak_split(pool, grounding, grounding, ["Nobody"])
    assert [k["source_transcript_id"] for k in keep] == ["T2"]
    assert excluded[0]["leak_side"] == "raw"
    assert excluded[0]["leak_shingle"]


def test_anti_leak_also_catches_the_leak_that_only_shows_after_redaction():
    # The raw grounding says the name; the pool answer says the name too. Both
    # sides become "guest" once redacted, so the shared run only appears in the
    # redacted comparison when the surrounding words differ in the raw text.
    variants = ["Zorvath Quilliman"]
    answer = "Zorvath Quilliman said " + " ".join(f"z{i}" for i in range(20))
    raw_grounding = "HOST: q\nGUEST: Quilliman said " + \
        " ".join(f"z{i}" for i in range(20))
    redacted_grounding = R.redact(raw_grounding, variants)
    pool = [mk_pool_row("T1", 1, "Q?", answer)]
    keep, excluded = D2.anti_leak_split(pool, "unrelated text entirely",
                                        redacted_grounding, variants)
    assert keep == []
    assert excluded[0]["leak_side"] == "redacted"


def test_an_answer_the_grounding_does_not_contain_survives():
    pool = [mk_pool_row("T1", 1, "Q?", "Nothing in common. " + OTHER_FILLER)]
    keep, excluded = D2.anti_leak_split(pool, "HOST: a\nGUEST: " + FILLER,
                                        "HOST: a\nGUEST: " + FILLER, ["Nobody"])
    assert len(keep) == 1 and excluded == []


def test_a_near_copy_of_the_true_answer_is_too_close():
    true = "Because of the audit and nothing else. " + FILLER
    assert D2.too_close_to_true(true, true)
    assert not D2.too_close_to_true("Utterly different. " + OTHER_FILLER, true)


# ---------------------------------------------------------------------------
# 3. Question similarity
# ---------------------------------------------------------------------------


def test_identical_questions_score_one_and_unrelated_ones_score_lower():
    sim = D2.QuestionSimilarity([
        "why did the vote fail so badly",
        "how is the harvest going this year",
        "what did the auditor find in the ledger"])
    got = sim.cosines("why did the vote fail so badly",
                      ["why did the vote fail so badly",
                       "how is the harvest going this year"])
    assert got[0] == pytest.approx(1.0, abs=1e-9)
    assert got[1] < got[0]


def test_the_corpus_is_deduplicated_sorted_and_digested_stably():
    a = D2.QuestionSimilarity(["b question", "a question", "b question"])
    b = D2.QuestionSimilarity(["a question", "b question"])
    assert a.corpus == ["a question", "b question"]
    assert a.corpus_sha256 == b.corpus_sha256


def test_an_empty_corpus_is_refused():
    with pytest.raises(ValueError):
        D2.QuestionSimilarity(["", "   "])


def test_cosines_of_no_questions_is_an_empty_list():
    sim = D2.QuestionSimilarity(["a question"])
    assert sim.cosines("a question", []) == []


# ---------------------------------------------------------------------------
# 4. Selection
# ---------------------------------------------------------------------------


def _uniform_pool(n, words=40, cid="C1"):
    """``n`` pool rows of the same length and the same (Z) density bucket."""
    out = []
    for k in range(n):
        answer = " ".join(f"p{k}x{i}" for i in range(words))
        out.append(mk_pool_row(f"T{k}", k, f"pool question number {k} here",
                               answer, cid=cid))
    return out


def _true_item(words=40):
    answer = " ".join(f"t{i}" for i in range(words))
    return mk_item("C1:C1-TEST:3", "the test question about the vote", answer)


def test_a_full_pool_builds_four_options_all_from_the_subject():
    pool = _uniform_pool(6)
    item = _true_item()
    res = D2.select_same_subject(item, pool, [0.1] * len(pool))
    assert res["built"] is True
    assert len(res["options"]) == 4
    assert {o["source_canonical_id"] for o in res["options"]} == {"C1"}
    assert res["options"][res["correct_index"]]["kind"] == "true"
    assert res["options"][res["correct_index"]]["text"] == item["answer"]
    assert len(res["options_stripped"]) == 4


def test_no_distractor_may_come_from_the_test_interview():
    pool = _uniform_pool(6)
    item = _true_item()
    res = D2.select_same_subject(item, pool, [0.1] * len(pool))
    for opt in res["options"]:
        if opt["kind"] == "distractor":
            assert opt["source_transcript_id"] != item["transcript_id"]


def test_a_pool_with_fewer_than_three_usable_rows_does_not_build_the_item():
    pool = _uniform_pool(2)
    res = D2.select_same_subject(_true_item(), pool, [0.1, 0.1])
    assert res["built"] is False
    assert "no cross-person fallback" in res["reason"]
    assert res["best_rung_candidates"] == 2
    assert "options" not in res


def test_an_empty_pool_does_not_build_the_item():
    res = D2.select_same_subject(_true_item(), [], [])
    assert res["built"] is False


def test_the_highest_similarity_candidates_are_the_ones_chosen():
    pool = _uniform_pool(5)
    sims = [0.01, 0.90, 0.02, 0.80, 0.70]
    res = D2.select_same_subject(_true_item(), pool, sims)
    chosen = sorted(o["question_similarity"] for o in res["options"]
                    if o["kind"] == "distractor")
    assert chosen == [0.7, 0.8, 0.9]


def test_ties_are_broken_by_source_position_not_by_list_order():
    pool = _uniform_pool(4)
    res = D2.select_same_subject(_true_item(), pool, [0.5] * 4)
    keys = sorted((o["source_transcript_id"], o["source_q_turn_idx"])
                  for o in res["options"] if o["kind"] == "distractor")
    assert keys == [("T0", 0), ("T1", 1), ("T2", 2)]


def test_a_floor_removes_candidates_below_it_and_counts_them():
    pool = _uniform_pool(6)
    sims = [0.01, 0.01, 0.01, 0.30, 0.30, 0.30]
    res = D2.select_same_subject(_true_item(), pool, sims, floor=0.10)
    assert res["built"] is True
    assert res["pool_excluded_below_floor"] == 3
    assert all(o["question_similarity"] >= 0.10 for o in res["options"]
               if o["kind"] == "distractor")


def test_a_floor_that_starves_the_pool_leaves_the_item_unbuilt():
    pool = _uniform_pool(6)
    res = D2.select_same_subject(_true_item(), pool, [0.01] * 6, floor=0.50)
    assert res["built"] is False
    assert res["pool_excluded_below_floor"] == 6


def test_a_candidate_that_duplicates_the_true_answer_is_excluded_and_counted():
    item = _true_item()
    pool = _uniform_pool(3) + [mk_pool_row("TD", 9, "another question here",
                                           item["answer"])]
    res = D2.select_same_subject(item, pool, [0.1] * 4)
    assert res["pool_excluded_duplicate_of_true"] == 1
    assert item["answer"] not in [o["text"] for o in res["options"]
                                  if o["kind"] == "distractor"]


def test_the_relaxation_rung_used_is_recorded_and_rung_zero_is_preferred():
    pool = _uniform_pool(6)
    res = D2.select_same_subject(_true_item(), pool, [0.1] * 6)
    assert res["relax_rung"] == 0
    assert res["flags"] == ["relax_rung_0"]


def test_a_length_mismatch_forces_the_ladder_up_a_rung():
    # 40-word true answer; the pool sits at 50 words, which is outside +-20%
    # (32..48) but inside +-30% (28..52).
    pool = _uniform_pool(4, words=50)
    res = D2.select_same_subject(_true_item(words=40), pool, [0.1] * 4)
    assert res["built"] is True
    assert res["relax_rung"] == 1


def test_option_order_is_seeded_by_item_id_and_therefore_reproducible():
    pool = _uniform_pool(6)
    item = _true_item()
    first = D2.select_same_subject(item, pool, [0.1] * 6)
    second = D2.select_same_subject(item, pool, [0.1] * 6)
    assert first["correct_index"] == second["correct_index"]
    assert [o["text"] for o in first["options"]] == \
           [o["text"] for o in second["options"]]


def test_an_option_from_another_person_is_a_loud_failure_not_a_silent_one():
    pool = _uniform_pool(2) + [mk_pool_row("X1", 0, "foreign question here",
                                           " ".join(f"f{i}" for i in range(40)),
                                           cid="C9")]
    with pytest.raises(AssertionError, match="must come from the subject"):
        D2.select_same_subject(_true_item(), pool, [0.1] * 3)


# ---------------------------------------------------------------------------
# 5. The floor sweep
# ---------------------------------------------------------------------------


def test_the_sweep_reports_every_floor_and_never_rises_with_the_floor():
    pool = _uniform_pool(6)
    item = _true_item()
    sims = [0.00, 0.03, 0.06, 0.12, 0.18, 0.25]
    sweep = D2.similarity_floor_sweep({"C1": [item]}, {"C1": pool},
                                      {item["item_id"]: sims})
    assert sweep["floors"] == ["0.00", "0.02", "0.05", "0.10", "0.15", "0.20"]
    counts = [sweep["total"][f] for f in sweep["floors"]]
    assert counts == sorted(counts, reverse=True)
    assert sweep["per_subject"]["C1"]["0.00"] == 1
    assert sweep["per_subject"]["C1"]["0.20"] == 0    # only 2 rows clear 0.20
