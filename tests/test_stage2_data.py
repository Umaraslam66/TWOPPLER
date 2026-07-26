"""Tests for the Stage 2 data foundation (SPEC D1/D2/D3).

Everything here is synthetic: tiny fake pool rows written to tmp CSVs and tiny
fake MediaSum records. No network, no read of the 4.45 GB corpus, no read of
the real candidate pool. The one file outside tmp that is touched is
experiments/mediasum_index.py, loaded by file path so the vendored
classify_speaker can be checked against its origin.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys

import pytest

from doppler import stage2_data as S


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

POOL_COLUMNS = [
    "canonical_id", "canonical_name", "clean", "qualifies", "wiki_status",
    "ambiguous_identity", "variants", "transcripts",
]


def pool_row(cid, name, wiki="has-page", clean=True, qualifies=True,
             ambiguous=False, variants="", transcripts=""):
    return {
        "canonical_id": cid,
        "canonical_name": name,
        "clean": str(clean),
        "qualifies": str(qualifies),
        "wiki_status": wiki,
        "ambiguous_identity": str(ambiguous),
        "variants": variants,
        "transcripts": transcripts,
    }


def write_pool(tmp_path, rows):
    path = tmp_path / "pool.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=POOL_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def big_pool(n=40):
    """A pool with both strata, deliberately not in draw order."""
    rows = []
    for i in range(n):
        wiki = "long-tail" if i % 3 == 0 else ("has-page-fuzzy" if i % 7 == 0
                                               else "has-page")
        rows.append(pool_row(f"C{i:05d}", f"Person {i}", wiki=wiki,
                             variants=f"Person {i}"))
    return rows


def record(tid, speakers, utts, program="Talk of the Nation",
           date="2011-01-01", title="A Title"):
    return {"id": tid, "program": program, "date": date, "title": title,
            "summary": "s", "utt": list(utts), "speaker": list(speakers)}


# ---------------------------------------------------------------------------
# transcripts-column parsing
# ---------------------------------------------------------------------------

def test_parse_transcripts_basic():
    cell = ("NPR-7092|2004-11-23|Day To Day|cl12|S;"
            "CNN-27211|2001-03-15|Burden of Proof|cl1|-")
    items = S.parse_transcripts(cell)
    assert items == [
        {"transcript_id": "NPR-7092", "date": "2004-11-23",
         "program": "Day To Day", "cluster_id": "cl12", "substantive": True},
        {"transcript_id": "CNN-27211", "date": "2001-03-15",
         "program": "Burden of Proof", "cluster_id": "cl1",
         "substantive": False},
    ]


def test_parse_transcripts_program_containing_semicolon():
    """Five real MediaSum programs contain ';' ("Q&A; WITH JIM CLANCY")."""
    cell = ("CNN-48032|2002-01-25|Q&A; WITH JIM CLANCY|cl5|-;"
            "CNN-5666|2000-04-02|CNN&Time;|cl71|S")
    items = S.parse_transcripts(cell)
    assert [i["program"] for i in items] == ["Q&A; WITH JIM CLANCY", "CNN&Time;"]
    assert [i["substantive"] for i in items] == [False, True]


def test_parse_transcripts_empty_and_malformed():
    assert S.parse_transcripts("") == []
    assert S.parse_transcripts(None) == []
    with pytest.raises(ValueError):
        S.parse_transcripts("NPR-1|2004-11-23|Day To Day|cl1")   # no flag
    with pytest.raises(ValueError):
        S.parse_transcripts("NPR-1|2004-11-23|Day To Day|cl1|X")  # bad flag


def test_load_pool_types(tmp_path):
    rows = [pool_row("C00001", "Ann Lee", clean=True, qualifies=False,
                     ambiguous=True, variants="Ann Lee;A. Lee",
                     transcripts="NPR-1|2004-01-01|Day To Day|cl1|S")]
    pool = S.load_pool(write_pool(tmp_path, rows))
    assert pool[0]["clean"] is True
    assert pool[0]["qualifies"] is False
    assert pool[0]["ambiguous_identity"] is True
    assert pool[0]["variants"] == ["Ann Lee", "A. Lee"]
    assert pool[0]["transcripts"][0]["transcript_id"] == "NPR-1"
    assert pool[0]["canonical_name"] == "Ann Lee"     # untouched columns survive


def test_eligible_subjects_filters(tmp_path):
    rows = [
        pool_row("C1", "Keep Me"),
        pool_row("C2", "Not Clean", clean=False),
        pool_row("C3", "Not Qualifying", qualifies=False),
        pool_row("C4", "Ambiguous", ambiguous=True),
    ]
    pool = S.load_pool(write_pool(tmp_path, rows))
    assert [r["canonical_id"] for r in S.eligible_subjects(pool)] == ["C1"]


# ---------------------------------------------------------------------------
# D1 — the draw
# ---------------------------------------------------------------------------

def test_draw_is_deterministic_and_stratified(tmp_path):
    pool = S.load_pool(write_pool(tmp_path, big_pool()))
    a = S.draw_dev_subjects(pool, drawn_at="2026-07-26")
    b = S.draw_dev_subjects(pool, drawn_at="2026-07-26")
    assert a == b
    ids = [s["canonical_id"] for s in a["subjects"]]
    assert len(ids) == len(set(ids)) == 5
    strata = [s["wiki_status"] for s in a["subjects"]]
    assert sum(1 for s in strata if s == "long-tail") == 2
    assert sum(1 for s in strata if s != "long-tail") == 3
    assert a["seed"] == 47


def test_draw_changes_with_seed(tmp_path):
    pool = S.load_pool(write_pool(tmp_path, big_pool()))
    a = S.draw_dev_subjects(pool, seed=47, drawn_at="x")
    c = S.draw_dev_subjects(pool, seed=48, drawn_at="x")
    assert [s["canonical_id"] for s in a["subjects"]] != \
           [s["canonical_id"] for s in c["subjects"]]


def test_draw_shuffle_pos_matches_the_frozen_order(tmp_path):
    pool = S.load_pool(write_pool(tmp_path, big_pool()))
    order = S.shuffled_eligible_ids(pool)
    doc = S.draw_dev_subjects(pool, drawn_at="x")
    for s in doc["subjects"]:
        assert order[s["shuffle_pos"]] == s["canonical_id"]
    # Picks are the earliest of their stratum in that order.
    first_lt = next(i for i, cid in enumerate(order)
                    if next(r for r in pool if r["canonical_id"] == cid)["wiki_status"]
                    == "long-tail")
    assert min(s["shuffle_pos"] for s in doc["subjects"]
               if s["wiki_status"] == "long-tail") == first_lt


def test_draw_ignores_ineligible_rows(tmp_path):
    rows = big_pool()
    rows.append(pool_row("C99999", "Dirty", wiki="long-tail", clean=False))
    pool = S.load_pool(write_pool(tmp_path, rows))
    doc = S.draw_dev_subjects(pool, drawn_at="x")
    assert "C99999" not in [s["canonical_id"] for s in doc["subjects"]]


def test_burned_subject_is_replaced_by_next_of_same_stratum(tmp_path):
    pool = S.load_pool(write_pool(tmp_path, big_pool()))
    base = S.draw_dev_subjects(pool, drawn_at="x")
    victim = next(s for s in base["subjects"] if s["wiki_status"] == "long-tail")

    doc = S.draw_dev_subjects(pool, burned=[victim["canonical_id"]], drawn_at="x")
    ids = [s["canonical_id"] for s in doc["subjects"]]
    assert victim["canonical_id"] not in ids
    assert doc["burned"] == [victim["canonical_id"]]
    assert len(doc["replacements"]) == 1
    rep = doc["replacements"][0]
    assert rep["stratum"] == "long-tail"
    assert rep["burned_shuffle_pos"] == victim["shuffle_pos"]
    # The replacement is the next long-tail id further along the same order.
    order = S.shuffled_eligible_ids(pool)
    replacement = next(s for s in doc["subjects"]
                       if s["wiki_status"] == "long-tail"
                       and s["canonical_id"] not in
                       [b["canonical_id"] for b in base["subjects"]])
    assert rep["replaced_by"] == replacement["canonical_id"]
    assert order.index(replacement["canonical_id"]) > victim["shuffle_pos"]
    # The other stratum is untouched.
    assert [s["canonical_id"] for s in doc["subjects"] if s["wiki_status"] != "long-tail"] \
        == [s["canonical_id"] for s in base["subjects"] if s["wiki_status"] != "long-tail"]


def test_two_burns_in_one_stratum(tmp_path):
    pool = S.load_pool(write_pool(tmp_path, big_pool()))
    base = S.draw_dev_subjects(pool, drawn_at="x")
    victims = [s["canonical_id"] for s in base["subjects"]
               if s["wiki_status"] == "long-tail"]
    doc = S.draw_dev_subjects(pool, burned=victims, drawn_at="x")
    ids = [s["canonical_id"] for s in doc["subjects"]]
    assert not set(victims) & set(ids)
    reps = [r for r in doc["replacements"] if r["stratum"] == "long-tail"]
    assert len(reps) == 2
    assert [r["replaced_by"] for r in reps] == \
        [s["canonical_id"] for s in doc["subjects"] if s["wiki_status"] == "long-tail"]


def test_burned_for_qa_keeps_the_subject_and_adds_one(tmp_path):
    """Retire-in-place: the subject stays, its stratum's quota goes up by one."""
    pool = S.load_pool(write_pool(tmp_path, big_pool()))
    base = S.draw_dev_subjects(pool, drawn_at="x")
    victim = next(s for s in base["subjects"] if s["wiki_status"] == "long-tail")

    doc = S.draw_dev_subjects(pool, burned_for_qa=[victim["canonical_id"]],
                              drawn_at="x")
    ids = [s["canonical_id"] for s in doc["subjects"]]
    assert len(ids) == 6
    # Every original pick survives, in the same relative order, at the same
    # shuffle position. Subjects are listed in shuffled order, so the added one
    # slots in where it falls rather than at the end.
    base_ids = [s["canonical_id"] for s in base["subjects"]]
    assert [c for c in ids if c in base_ids] == base_ids
    was_pos = {s["canonical_id"]: s["shuffle_pos"] for s in base["subjects"]}
    for s in doc["subjects"]:
        if s["canonical_id"] in was_pos:
            assert s["shuffle_pos"] == was_pos[s["canonical_id"]]
    assert [s["shuffle_pos"] for s in doc["subjects"]] == \
        sorted(s["shuffle_pos"] for s in doc["subjects"])
    assert sum(1 for s in doc["subjects"] if s["wiki_status"] == "long-tail") == 3
    assert sum(1 for s in doc["subjects"] if s["wiki_status"] != "long-tail") == 3

    kept = next(s for s in doc["subjects"]
                if s["canonical_id"] == victim["canonical_id"])
    assert kept["burned_for_qa"] is True
    assert all("burned_for_qa" not in s for s in doc["subjects"]
               if s["canonical_id"] != victim["canonical_id"])
    assert doc["burned_for_qa"] == [victim["canonical_id"]]
    assert doc["burned"] == []

    rep = doc["replacements"][0]
    assert rep["mode"] == "retained_in_place"
    assert rep["burned_canonical_id"] == victim["canonical_id"]
    assert rep["stratum"] == "long-tail"
    # The added subject is the next long-tail id further along the same order.
    added = next(c for c in ids if c not in base_ids)
    assert rep["replaced_by"] == added
    order = S.shuffled_eligible_ids(pool)
    assert order.index(added) > victim["shuffle_pos"]
    added_row = next(s for s in doc["subjects"] if s["canonical_id"] == added)
    assert added_row["wiki_status"] == "long-tail"
    # ...and it is the FIRST such id, i.e. nothing long-tail was skipped.
    lt_after = [c for c in order[victim["shuffle_pos"] + 1:]
                if c not in base_ids
                and next(r for r in pool if r["canonical_id"] == c)["wiki_status"]
                == "long-tail"]
    assert added == lt_after[0]


def test_burned_for_qa_accepts_a_reason_mapping(tmp_path):
    pool = S.load_pool(write_pool(tmp_path, big_pool()))
    base = S.draw_dev_subjects(pool, drawn_at="x")
    victim = next(s for s in base["subjects"] if s["wiki_status"] != "long-tail")
    doc = S.draw_dev_subjects(pool, burned_for_qa={victim["canonical_id"]: "why"},
                              drawn_at="x")
    assert len(doc["subjects"]) == 6
    assert sum(1 for s in doc["subjects"] if s["wiki_status"] != "long-tail") == 4
    assert doc["replacements"][0]["reason"] == "why"


def test_burned_for_qa_is_deterministic(tmp_path):
    pool = S.load_pool(write_pool(tmp_path, big_pool()))
    cid = S.draw_dev_subjects(pool, drawn_at="x")["subjects"][0]["canonical_id"]
    a = S.draw_dev_subjects(pool, burned_for_qa=[cid], drawn_at="x")
    b = S.draw_dev_subjects(pool, burned_for_qa=[cid], drawn_at="x")
    assert a == b


def test_a_subject_cannot_be_both_dropped_and_retained(tmp_path):
    pool = S.load_pool(write_pool(tmp_path, big_pool()))
    cid = S.draw_dev_subjects(pool, drawn_at="x")["subjects"][0]["canonical_id"]
    with pytest.raises(ValueError, match="both dropped and retained"):
        S.draw_dev_subjects(pool, burned=[cid], burned_for_qa=[cid], drawn_at="x")


def test_burned_for_qa_rejects_an_ineligible_id(tmp_path):
    pool = S.load_pool(write_pool(tmp_path, big_pool()))
    with pytest.raises(ValueError, match="not an eligible subject"):
        S.draw_dev_subjects(pool, burned_for_qa=["C99999"], drawn_at="x")


def test_burned_rejects_an_unknown_id(tmp_path):
    """A typo in the burn list must not silently burn nothing."""
    pool = S.load_pool(write_pool(tmp_path, big_pool()))
    with pytest.raises(ValueError, match="not an eligible subject"):
        S.draw_dev_subjects(pool, burned=["C99999"], drawn_at="x")
    with pytest.raises(ValueError, match="not an eligible subject"):
        S.draw_dev_subjects(pool, burned=["c00000"], drawn_at="x")   # wrong case


def test_drop_and_retain_together(tmp_path):
    """One stratum losing a subject and another gaining one do not interfere."""
    pool = S.load_pool(write_pool(tmp_path, big_pool()))
    base = S.draw_dev_subjects(pool, drawn_at="x")
    dropped = next(s for s in base["subjects"] if s["wiki_status"] == "long-tail")
    retained = next(s for s in base["subjects"] if s["wiki_status"] != "long-tail")
    doc = S.draw_dev_subjects(pool, burned=[dropped["canonical_id"]],
                              burned_for_qa=[retained["canonical_id"]],
                              drawn_at="x")
    ids = [s["canonical_id"] for s in doc["subjects"]]
    assert dropped["canonical_id"] not in ids
    assert retained["canonical_id"] in ids
    assert len(ids) == 6
    assert sum(1 for s in doc["subjects"] if s["wiki_status"] == "long-tail") == 2
    assert sum(1 for s in doc["subjects"] if s["wiki_status"] != "long-tail") == 4
    modes = {r["burned_canonical_id"]: r["mode"] for r in doc["replacements"]}
    assert modes == {dropped["canonical_id"]: "dropped",
                     retained["canonical_id"]: "retained_in_place"}
    for rep in doc["replacements"]:
        assert rep["replaced_by"] in ids
        assert rep["replaced_by"] != rep["burned_canonical_id"]


def test_load_dev_subjects_accepts_the_extra_subject(tmp_path):
    doc = {"seed": 47, "drawn_at": "x", "subjects": [
        {"canonical_id": f"C{i}", "wiki_status": "has-page"} for i in range(5)]}
    S.write_json(tmp_path / "dev_subjects.json", doc)
    assert len(S.load_dev_subjects(tmp_path)["subjects"]) == 5

    doc["subjects"].append({"canonical_id": "C9", "wiki_status": "long-tail"})
    S.write_json(tmp_path / "dev_subjects.json", doc)
    with pytest.raises(SystemExit):            # 6 with nothing retired
        S.load_dev_subjects(tmp_path)

    doc["subjects"][0]["burned_for_qa"] = True
    S.write_json(tmp_path / "dev_subjects.json", doc)
    assert len(S.load_dev_subjects(tmp_path)["subjects"]) == 6


def test_draw_raises_when_a_stratum_is_exhausted(tmp_path):
    rows = [pool_row(f"C{i:05d}", f"P{i}", wiki="has-page") for i in range(10)]
    pool = S.load_pool(write_pool(tmp_path, rows))
    with pytest.raises(ValueError, match="pool exhausted"):
        S.draw_dev_subjects(pool, drawn_at="x")


# ---------------------------------------------------------------------------
# D2 — chronological split
# ---------------------------------------------------------------------------

def subject(transcripts, cid="C00001", name="Ann Lee", variants=None):
    return {
        "canonical_id": cid,
        "canonical_name": name,
        "variants": variants if variants is not None else [name],
        "transcripts": S.parse_transcripts(transcripts),
    }


def test_split_basic_latest_is_test():
    row = subject(
        "NPR-1|2001-01-01|Prog A|cl1|S;"
        "NPR-2|2002-02-02|Prog B|cl2|S;"
        "NPR-3|2003-03-03|Prog C|cl3|S")
    split = S.chronological_split(row)
    assert split["test"]["transcript_id"] == "NPR-3"
    assert [g["transcript_id"] for g in split["grounding"]] == ["NPR-1", "NPR-2"]
    assert split["excluded_same_date"] == []
    assert split["grounding"][0]["date"] < split["grounding"][1]["date"] \
        < split["test"]["date"]


def test_split_ignores_non_substantive_transcripts():
    row = subject(
        "NPR-1|2001-01-01|Prog A|cl1|S;"
        "NPR-2|2002-02-02|Prog B|cl2|S;"
        "NPR-9|2009-09-09|Prog Z|cl9|-")      # latest date, but not substantive
    split = S.chronological_split(row)
    assert split["test"]["transcript_id"] == "NPR-2"
    assert "NPR-9" not in [g["transcript_id"] for g in split["grounding"]]


def test_split_same_date_cluster_is_excluded_entirely():
    """A second interview event on the test date is dropped, not grounded."""
    row = subject(
        "NPR-1|2001-01-01|Prog A|cl1|S;"
        "NPR-5|2005-05-05|Prog B|cl2|S;"
        "NPR-7|2005-05-05|Prog C|cl3|S")
    split = S.chronological_split(row)
    assert split["test"]["transcript_id"] == "NPR-7"           # largest id wins
    assert [e["transcript_id"] for e in split["excluded_same_date"]] == ["NPR-5"]
    ground = [g["transcript_id"] for g in split["grounding"]]
    assert ground == ["NPR-1"]
    assert "NPR-5" not in ground                                # the leak guard


def test_split_tie_break_is_largest_representative_id():
    row = subject(
        "NPR-1|2001-01-01|Prog A|cl1|S;"
        "NPR-30|2005-05-05|Prog B|cl2|S;"
        "NPR-4|2005-05-05|Prog C|cl3|S")
    split = S.chronological_split(row)
    # Lexicographic, not numeric: "NPR-4" > "NPR-30".
    assert split["test"]["transcript_id"] == "NPR-4"
    assert [e["transcript_id"] for e in split["excluded_same_date"]] == ["NPR-30"]


def test_split_cluster_representative_is_most_guest_words():
    row = subject(
        "NPR-1|2001-01-01|Prog A|cl1|S;"
        "NPR-2|2002-02-02|Prog B|cl2|S;"       # re-airing pair, same cluster
        "NPR-3|2002-02-03|Prog B rerun|cl2|S")
    split = S.chronological_split(row, guest_words={"NPR-2": 100, "NPR-3": 900})
    assert split["test"]["transcript_id"] == "NPR-3"
    assert split["test"]["date"] == "2002-02-02"     # cluster date = earliest
    assert split["test"]["n_transcripts_in_cluster"] == 2

    other = S.chronological_split(row, guest_words={"NPR-2": 900, "NPR-3": 100})
    assert other["test"]["transcript_id"] == "NPR-2"


def test_split_representative_tie_is_smallest_transcript_id():
    row = subject(
        "NPR-1|2001-01-01|Prog A|cl1|S;"
        "NPR-8|2002-02-02|Prog B|cl2|S;"
        "NPR-7|2002-02-02|Prog B rerun|cl2|S")
    split = S.chronological_split(row, guest_words={"NPR-8": 50, "NPR-7": 50})
    assert split["test"]["transcript_id"] == "NPR-7"


def test_split_titles_are_filled_when_supplied():
    row = subject("NPR-1|2001-01-01|Prog A|cl1|S;NPR-2|2002-02-02|Prog B|cl2|S")
    split = S.chronological_split(row, titles={"NPR-2": "The Last One"})
    assert split["test"]["title"] == "The Last One"
    assert split["grounding"][0]["title"] == ""


def test_split_excludes_a_cluster_with_any_member_on_or_after_the_test_date():
    """SPEC D2 hardening v1.2: test every member date, not the cluster minimum.

    cl2's cluster date is 2002-02-02, safely early, but one of its re-airings
    went out on the test date itself — that is the same-event leak the guard
    exists for.
    """
    row = subject(
        "NPR-1|2001-01-01|Prog A|cl1|S;"
        "NPR-2|2002-02-02|Prog B|cl2|S;"
        "NPR-3|2005-05-05|Prog B rerun|cl2|S;"
        "NPR-9|2005-05-05|Prog C|cl3|S")
    split = S.chronological_split(row, guest_words={"NPR-2": 90, "NPR-3": 10})
    assert split["test"]["transcript_id"] == "NPR-9"
    assert [g["cluster_id"] for g in split["grounding"]] == ["cl1"]
    assert "cl2" in [e["cluster_id"] for e in split["excluded_same_date"]]


def test_split_excludes_a_cluster_with_a_member_after_the_test_date():
    row = subject(
        "NPR-1|2001-01-01|Prog A|cl1|S;"
        "NPR-2|2002-02-02|Prog B|cl2|S;"
        "NPR-3|2009-09-09|Prog B rerun|cl2|S;"
        "NPR-9|2005-05-05|Prog C|cl3|S")
    split = S.chronological_split(row, guest_words={"NPR-2": 90, "NPR-3": 10})
    assert split["test"]["transcript_id"] == "NPR-9"
    assert [g["cluster_id"] for g in split["grounding"]] == ["cl1"]
    assert [e["cluster_id"] for e in split["excluded_same_date"]] == ["cl2"]


def test_split_records_member_dates():
    row = subject(
        "NPR-1|2001-01-01|Prog A|cl1|S;"
        "NPR-2|2002-02-02|Prog B|cl2|S;"
        "NPR-3|2002-02-05|Prog B rerun|cl2|S;"
        "NPR-9|2005-05-05|Prog C|cl3|S")
    split = S.chronological_split(row, guest_words={"NPR-2": 90, "NPR-3": 10})
    cl2 = next(g for g in split["grounding"] if g["cluster_id"] == "cl2")
    assert cl2["member_dates"] == ["2002-02-02", "2002-02-05"]
    assert cl2["date"] == "2002-02-02"


def test_split_requires_grounding():
    row = subject("NPR-1|2001-01-01|Prog A|cl1|S;NPR-2|2001-01-01|Prog B|cl2|S")
    with pytest.raises(ValueError, match="no grounding"):
        S.chronological_split(row)


def test_split_requires_substantive_transcripts():
    row = subject("NPR-1|2001-01-01|Prog A|cl1|-")
    with pytest.raises(ValueError, match="no substantive"):
        S.chronological_split(row)


# ---------------------------------------------------------------------------
# D3 — turn extraction
# ---------------------------------------------------------------------------

def test_extract_turns_roles():
    row = subject("NPR-1|2001-01-01|P|cl1|S", name="Ann Lee")
    rec = record("NPR-1",
                 speakers=["NEAL CONAN, host", "Ms. ANN LEE (Author)",
                           "UNIDENTIFIED WOMAN", "Mr. BOB SMITH (Analyst)"],
                 utts=["welcome", "thanks", "(noise)", "my view"])
    turns = S.extract_turns(rec, row)
    assert [t["role"] for t in turns] == ["host", "guest", "other", "other"]
    assert [t["turn_idx"] for t in turns] == [0, 1, 2, 3]
    assert all(t["transcript_id"] == "NPR-1" for t in turns)
    assert turns[1]["speaker_label"] == "Ms. ANN LEE (Author)"
    assert turns[1]["text"] == "thanks"


@pytest.mark.parametrize("label", [
    "ANN LEE", "ann lee", "Ann Lee", "Ms. ANN LEE", "MS. Ann Lee",
    "Dr. Ann Lee", "Professor ANN LEE", "Ambassador Ann Lee",
    "Ms. ANN LEE (Author, Something Institute)",
    "ANN LEE, Author", "Ann Lee - Author", "ANN LEE:",
])
def test_guest_matching_is_case_insensitive_and_honorific_tolerant(label):
    row = subject("NPR-1|2001-01-01|P|cl1|S", name="Ann Lee")
    turns = S.extract_turns(record("NPR-1", [label], ["hello"]), row)
    assert turns[0]["role"] == "guest", label


def test_guest_matching_uses_variants():
    row = subject("NPR-1|2001-01-01|P|cl1|S", name="Robert Harris",
                  variants=["Robert Harris", "R. Harris"])
    turns = S.extract_turns(
        record("NPR-1", ["Mr. R. HARRIS", "ROBERT HARRIS", "Mr. RALPH HARRIS"],
               ["a", "b", "c"]), row)
    assert [t["role"] for t in turns] == ["guest", "guest", "other"]


def test_same_named_host_is_host_not_guest():
    """A staff marker beats the name match: that is an identity collision."""
    row = subject("NPR-1|2001-01-01|P|cl1|S", name="Robert Harris")
    turns = S.extract_turns(
        record("NPR-1", ["ROBERT HARRIS, host"], ["and now the news"]), row)
    assert turns[0]["role"] == "host"


# ---------------------------------------------------------------------------
# D3.1 — within-transcript bare-surname resolution
# ---------------------------------------------------------------------------

def test_bare_surname_host_resolves():
    """The real C00292 failure: CNN names the anchor once, then uses 'ROTH'."""
    row = subject("CNN-1|2004-12-31|P|cl1|S", name="Bassir Pour")
    rec = record("CNN-1",
                 speakers=["RICHARD ROTH, CNN ANCHOR", "BASSIR POUR", "ROTH",
                           "BASSIR POUR", "ROTH"],
                 utts=["intro", "answer", "follow up", "more", "and then"])
    turns = S.extract_turns(rec, row)
    assert [t["role"] for t in turns] == \
        ["host", "guest", "host", "guest", "host"]
    assert turns[2]["speaker_label"] == "ROTH"           # raw label preserved
    assert turns[2]["resolved_label"] == "RICHARD ROTH, CNN ANCHOR"
    assert turns[0]["resolved_label"] is None            # full labels untouched


def test_bare_surname_guest_resolves():
    row = subject("NPR-1|2001-01-01|P|cl1|S", name="Robert Sampson")
    rec = record("NPR-1",
                 speakers=["NEAL CONAN, HOST", "ROBERT SAMPSON", "CONAN",
                           "SAMPSON"],
                 utts=["q1", "a1", "q2", "a2"])
    turns = S.extract_turns(rec, row)
    assert [t["role"] for t in turns] == ["host", "guest", "host", "guest"]
    assert turns[3]["resolved_label"] == "ROBERT SAMPSON"


def test_ambiguous_surname_stays_other():
    """Two Harrises in the room: a bare 'HARRIS' resolves to neither."""
    row = subject("NPR-1|2001-01-01|P|cl1|S", name="Robert Harris")
    rec = record("NPR-1",
                 speakers=["ROBERT HARRIS", "Ms. JANE HARRIS (Analyst)",
                           "HARRIS"],
                 utts=["a", "b", "c"])
    turns = S.extract_turns(rec, row)
    assert [t["role"] for t in turns] == ["guest", "other", "other"]
    assert turns[2]["resolved_label"] is None


def test_ambiguous_surname_does_not_block_an_unambiguous_one():
    row = subject("NPR-1|2001-01-01|P|cl1|S", name="Ann Lee")
    rec = record("NPR-1",
                 speakers=["ANN LEE", "JOHN LEE", "NEAL CONAN, HOST", "LEE",
                           "CONAN"],
                 utts=["a", "b", "c", "d", "e"])
    turns = S.extract_turns(rec, row)
    assert turns[3]["role"] == "other"      # LEE is ambiguous
    assert turns[4]["role"] == "host"       # CONAN is not


def test_resolution_never_crosses_transcripts():
    """A name introduced in one interview says nothing about another."""
    row = subject("CNN-1|2004-01-01|P|cl1|S;CNN-2|2005-01-01|P|cl2|S",
                  name="Bassir Pour")
    intro = record("CNN-1", ["RICHARD ROTH, CNN ANCHOR", "ROTH"], ["a", "b"])
    later = record("CNN-2", ["ROTH", "BASSIR POUR"], ["c", "d"])
    assert [t["role"] for t in S.extract_turns(intro, row)] == ["host", "host"]
    # CNN-2 never introduces Roth, so its bare 'ROTH' must stay unresolved.
    turns = S.extract_turns(later, row)
    assert [t["role"] for t in turns] == ["other", "guest"]
    assert turns[0]["resolved_label"] is None


def test_registry_registers_role_descriptors_and_multi_token_names():
    reg = S.surname_registry([
        "RICHARD ROTH, CNN ANCHOR",       # role descriptor
        "ANN LEE",                        # multi-token name
        "Ms. JANE DOE (Author)",          # parenthetical affiliation
        "SMITH",                          # bare surname: never registered
        "UNIDENTIFIED MAN",               # anonymous: never registered
        "MALE VOICE",                     # generic: never registered
    ])
    assert set(reg) == {"roth", "lee", "doe"}
    assert reg["roth"] == "RICHARD ROTH, CNN ANCHOR"


def test_registry_single_token_with_role_descriptor_registers():
    reg = S.surname_registry(["ROTH, CNN ANCHOR"])
    assert reg == {"roth": "ROTH, CNN ANCHOR"}


def test_registry_the_real_cnn_roth_collision():
    """The corpus shapes that broke D3.1-r1, taken from CNN-3812 verbatim.

    "ROTH (voice-over)" is a stage direction, "UNMOVIC. ROTH" and
    "UN. GREENSTOCK" are fused fragments of the previous line. None of them is
    a person, and r1 counted all of them as one, which poisoned the surname
    and left every bare "ROTH" unresolved.
    """
    labels = [
        "RICHARD ROTH, DIPLOMATIC LICENSE", "ROTH", "ROTH (voice-over)",
        "ROTH (on camera)", "UNMOVIC. ROTH", "UN. ROTH",
        "JEREMY GREENSTOCK, BRITISH AMB. TO UN", "UN. GREENSTOCK",
        "GREENSTOCK", "UNMOVIC. (voice-over)",
        "DIPLOMATIC LICENSE. (voice-over)",
    ]
    reg = S.surname_registry(labels)
    assert reg["roth"] == "RICHARD ROTH, DIPLOMATIC LICENSE"
    assert reg["greenstock"] == "JEREMY GREENSTOCK, BRITISH AMB. TO UN"
    # The noise never invents a person.
    assert "unmovic" not in reg and "un" not in reg and "license" not in reg
    assert "diplomatic" not in reg


def test_stage_directions_and_fused_fragments_all_resolve():
    row = subject("CNN-1|2000-03-04|P|cl1|S", name="Bassir Pour")
    rec = record("CNN-1",
                 speakers=["RICHARD ROTH, DIPLOMATIC LICENSE", "ROTH",
                           "ROTH (voice-over)", "UNMOVIC. ROTH", "UN. ROTH"],
                 utts=["a", "b", "c", "d", "e"])
    turns = S.extract_turns(rec, row)
    assert all(t["resolved_label"] == "RICHARD ROTH, DIPLOMATIC LICENSE"
               for t in turns[1:]), [t["resolved_label"] for t in turns]
    assert turns[0]["resolved_label"] is None


def test_name_part_drops_noise_dot_tokens_but_keeps_titles_and_initials():
    assert S.label_tokens("UNMOVIC. ROTH") == ["roth"]
    assert S.label_tokens("UN. GREENSTOCK") == ["greenstock"]
    assert S.label_tokens("AIDS. BASSIR POUR") == ["bassir", "pour"]
    assert S.label_tokens("DIPLOMATIC LICENSE. (voice-over)") == ["diplomatic"]
    # Honorifics survive the noise drop (and are then stripped as honorifics).
    assert S.label_tokens("MR. BOB MEADOWS") == ["bob", "meadows"]
    assert S.label_tokens("MS. ANN LEE") == ["ann", "lee"]
    assert S.label_tokens("DR. FREDERIC HOF") == ["frederic", "hof"]
    assert S.label_tokens("AMB. ABDALLAH BAALI") == ["abdallah", "baali"]
    # A single-letter initial is name material, not noise.
    assert S.label_tokens("R. Harris") == ["r", "harris"]


def test_punctuation_shape_alone_never_registers():
    """SPEC D3.1-r2(b): "(", "," and dashes are not role descriptors."""
    assert S.surname_registry(["ROTH (voice-over)"]) == {}
    assert S.surname_registry(["ROTH, LE MONDE"]) == {}
    assert S.surname_registry(["ROTH - CNN"]) == {}
    # An explicit role word does register a single-token name.
    assert S.surname_registry(["ROTH, CNN ANCHOR"]) == {"roth": "ROTH, CNN ANCHOR"}


def test_single_token_registration_merges_into_the_multi_token_one():
    """SPEC D3.1-r2(c): same surname, one person, not an ambiguity."""
    reg = S.surname_registry(["ROTH, CNN ANCHOR", "RICHARD ROTH, DIPLOMATIC LICENSE"])
    assert reg["roth"] == "ROTH, CNN ANCHOR"      # the role-bearing label wins


def test_registry_prefers_the_role_bearing_spelling():
    reg = S.surname_registry(["RICHARD ROTH, DIPLOMATIC LICENSE",
                              "RICHARD ROTH, CNN ANCHOR"])
    assert reg["roth"] == "RICHARD ROTH, CNN ANCHOR"


def test_two_different_multi_token_names_are_a_real_ambiguity():
    reg = S.surname_registry(["ROBERT HARRIS", "JANE HARRIS, CNN ANCHOR"])
    assert "harris" not in reg


def test_resolution_does_not_touch_labels_that_carry_a_role():
    """'HARRIS, host' is already a complete label; it is never rewritten."""
    row = subject("NPR-1|2001-01-01|P|cl1|S", name="Ann Lee")
    rec = record("NPR-1", ["ANN LEE", "HARRIS, host"], ["a", "b"])
    turns = S.extract_turns(rec, row)
    assert [t["role"] for t in turns] == ["guest", "host"]
    assert turns[1]["resolved_label"] is None


# ---------------------------------------------------------------------------
# D3.1-r2(d) — guest matching by token containment
# ---------------------------------------------------------------------------

def test_guest_matching_is_token_containment():
    """The corpus writes the full name on the intro line and the short one
    everywhere else; canonical "Bassir Pour" must match both."""
    row = subject("CNN-1|2000-03-04|P|cl1|S", name="Bassir Pour")
    rec = record("CNN-1",
                 speakers=['AFSANE BASSIR POUR, "LE MONDE"', "BASSIR POUR",
                           "UN. BASSIR POUR", "AIDS. BASSIR POUR",
                           "I. BASSIR POUR", "JAMES BONE, TIMES OF LONDON"],
                 utts=["a", "b", "c", "d", "e", "f"])
    turns = S.extract_turns(rec, row)
    assert [t["role"] for t in turns] == \
        ["guest", "guest", "guest", "guest", "guest", "other"]


def test_containment_needs_two_shared_tokens():
    row = subject("NPR-1|2001-01-01|P|cl1|S", name="Ann Lee")
    rec = record("NPR-1", ["JOHN LEE", "ANN LEE", "LEE HARVEY OSWALD"],
                 ["a", "b", "c"])
    assert [t["role"] for t in S.extract_turns(rec, row)] == \
        ["other", "guest", "other"]


def test_containment_matches_in_both_directions():
    subj = [["bassir", "pour"]]
    assert S.name_matches_subject(["afsane", "bassir", "pour"], subj)
    assert S.name_matches_subject(["bassir", "pour"], subj)
    assert not S.name_matches_subject(["pour"], subj)
    assert not S.name_matches_subject(["bassir", "smith"], subj)
    # Longer canonical, shorter label: containment the other way round.
    assert S.name_matches_subject(["bassir", "pour"],
                                  [["afsane", "bassir", "pour"]])
    # Non-contiguous is not a match.
    assert not S.name_matches_subject(["bassir", "x", "pour"], subj)


def test_one_token_canonical_still_matches_exactly():
    row = subject("NPR-1|2001-01-01|P|cl1|S", name="Madonna", variants=["Madonna"])
    rec = record("NPR-1", ["MADONNA", "MADONNA CICCONE"], ["a", "b"])
    assert [t["role"] for t in S.extract_turns(rec, row)] == ["guest", "other"]


def test_extract_turns_rejects_misaligned_records():
    row = subject("NPR-1|2001-01-01|P|cl1|S")
    with pytest.raises(ValueError):
        S.extract_turns(record("NPR-1", ["A", "B"], ["only one"]), row)


def test_name_key_normalizes():
    assert S.name_key("Ms. ANN LEE (Author)") == S.name_key("ann lee")
    assert S.name_key("R. Harris") == S.name_key("R HARRIS")
    assert S.name_key("") == ""


def test_word_count():
    assert S.word_count("  one   two three ") == 3
    assert S.word_count("") == 0
    assert S.word_count(None) == 0


# ---------------------------------------------------------------------------
# Vendored classify_speaker must not drift from its origin
# ---------------------------------------------------------------------------

def _origin_classify_speaker():
    path = S.ROOT / "experiments/mediasum_index.py"
    if not path.exists():                                   # pragma: no cover
        pytest.skip("experiments/mediasum_index.py not present")
    spec = importlib.util.spec_from_file_location("_ms_index_origin", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ms_index_origin"] = mod
    spec.loader.exec_module(mod)                            # no side effects
    return mod.classify_speaker


def test_vendored_classify_speaker_matches_origin():
    origin = _origin_classify_speaker()
    labels = [
        "", None, "NEAL CONAN, host", "FARAI CHIDEYA, host",
        "UNIDENTIFIED MAN", "UNIDENTIFIED WOMAN #2", "SOUNDBITE",
        "Mr. BOB MEADOWS (Writer, People Magazine)", "Ms. ANN LEE (Author)",
        "Dr. Frederic Hof", "Professor MATTHEW KROENIG",
        "Sen. JOHN McCAIN (Republican, Arizona)", "VICE PRESIDENT AL GORE",
        "PRIME MINISTER Tony Blair", "Gen. DAVID PETRAEUS",
        "R. Harris", "ROBERT HARRIS", "AUDIENCE MEMBER", "CALLER",
        "JOHN SMITH - CNN CORRESPONDENT", "Rev. Dr. MARTIN LUTHER KING",
        "MALE VOICE", "Mr. JEFF OBAFEMI CARR (Actor, Playwright)",
        "BASSIR POUR", "Ms. Bassir Pour, United Nations",
        "STATE SENATOR Jane Doe", "chief justice john roberts",
        "unidentified reporter", "Mr. X", "...", "  ",
    ]
    for label in labels:
        assert S.classify_speaker(label) == origin(label), label


# ---------------------------------------------------------------------------
# One-pass corpus fetch (synthetic corpus file, never the real 4.45 GB one)
# ---------------------------------------------------------------------------

def fake_corpus(tmp_path, records, name="corpus.json"):
    """Serialize exactly like news_dialogue.json: one array, ': ' separators."""
    path = tmp_path / name
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    assert path.read_bytes().count(b'{"id": "') == len(records)
    return path


def test_fetch_records_pulls_only_what_was_asked_for(tmp_path):
    recs = [record(f"NPR-{i}", ["HOST, host", "Ms. ANN LEE"],
                   [f"q{i}", f"a{i} with braces {{\"id\": \"NPR-999\"}} inside"])
            for i in range(1, 12)]
    path = fake_corpus(tmp_path, recs)
    got = S.fetch_records(["NPR-3", "NPR-11"], path)
    assert set(got) == {"NPR-3", "NPR-11"}
    assert got["NPR-3"]["utt"][0] == "q3"
    assert got["NPR-11"]["title"] == "A Title"


@pytest.mark.parametrize("chunk", [1, 7, 8, 9, 64, 1000, 10 ** 6])
def test_fetch_records_is_chunk_size_independent(tmp_path, chunk):
    recs = [record(f"NPR-{i}", ["HOST, host"], [f"utterance number {i}"])
            for i in range(1, 21)]
    path = fake_corpus(tmp_path, recs)
    wanted = {"NPR-1", "NPR-9", "NPR-20"}
    got = {rid: json.JSONDecoder().raw_decode(raw.decode("utf-8"))[0]
           for rid, raw in S.iter_wanted_raw(path, wanted, chunk_bytes=chunk)}
    assert set(got) == wanted
    assert got["NPR-20"]["utt"] == ["utterance number 20"]
    assert got["NPR-1"]["utt"] == ["utterance number 1"]


def test_fetch_records_missing_id_raises(tmp_path):
    path = fake_corpus(tmp_path, [record("NPR-1", ["A"], ["x"])])
    with pytest.raises(KeyError):
        S.fetch_records(["NPR-1", "NPR-404"], path)


def test_fetch_records_empty_request(tmp_path):
    path = fake_corpus(tmp_path, [record("NPR-1", ["A"], ["x"])])
    assert S.fetch_records([], path) == {}


def test_fetch_records_handles_unicode_payloads(tmp_path):
    recs = [record("NPR-1", ["Mr. ANDRÉ MÜLLER"], ["café — naïve “quotes”"]),
            record("NPR-2", ["HOST, host"], ["plain"])]
    path = fake_corpus(tmp_path, recs)
    got = S.fetch_records(["NPR-1"], path, )
    assert got["NPR-1"]["utt"] == ["café — naïve “quotes”"]


# ---------------------------------------------------------------------------
# Scan-cache readers (synthetic pickle, never the real 82 MB cache)
# ---------------------------------------------------------------------------

def fake_cache(tmp_path, stats=None, tid_info=None):
    import pickle
    path = tmp_path / "cache.pkl"
    with path.open("wb") as fh:
        pickle.dump({"stats": stats or {}, "tid_info": tid_info or {}}, fh)
    return path


def test_load_guest_words_does_not_double_count_the_canonical_name(tmp_path):
    """The pool's `variants` column repeats canonical_name; summing it twice
    would double every word count and silently inflate the split."""
    row = subject("NPR-1|2001-01-01|P|cl1|S;NPR-2|2002-02-02|P|cl2|S",
                  name="Robert Harris", variants=["R. Harris", "Robert Harris"])
    cache = fake_cache(tmp_path, stats={
        ("Robert Harris", "NPR-1"): [100, 4],
        ("R. Harris", "NPR-1"): [7, 1],
        ("Robert Harris", "NPR-2"): [50, 2],
    })
    got = S.load_guest_words([row], cache)
    assert got["C00001"] == {"NPR-1": 107, "NPR-2": 50}


def test_load_titles(tmp_path):
    cache = fake_cache(tmp_path, tid_info={"NPR-1": ("Prog", "The Title", 12)})
    assert S.load_titles(["NPR-1", "NPR-2"], cache) == \
        {"NPR-1": "The Title", "NPR-2": ""}


# ---------------------------------------------------------------------------
# The driver's guard functions (imported by path; experiments/ is not a package)
# ---------------------------------------------------------------------------

def _driver():
    path = S.ROOT / "experiments/stage2_draw_dev.py"
    if not path.exists():                                   # pragma: no cover
        pytest.skip("experiments/stage2_draw_dev.py not present")
    spec = importlib.util.spec_from_file_location("_stage2_draw_dev", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_stage2_draw_dev"] = mod
    spec.loader.exec_module(mod)                            # no side effects
    return mod


def _draw_doc(entries, **extra):
    """entries: (canonical_id, wiki_status, shuffle_pos) in list order."""
    subjects = [{"canonical_id": cid, "canonical_name": cid,
                 "wiki_status": ws, "shuffle_pos": pos}
                for cid, ws, pos in entries]
    return {"seed": 47, "drawn_at": "x", "subjects": subjects, **extra}


# Positions are the real thing the guard protects, so they are explicit here
# and a newly added subject slots in at its own position without moving them.
FIVE = [("C1", "long-tail", 0), ("C2", "long-tail", 1), ("C3", "has-page", 2),
        ("C4", "has-page", 5), ("C5", "has-page", 6)]
ADDED = ("C9", "long-tail", 3)


def test_guard_refuses_an_existing_draw(tmp_path):
    drv = _driver()
    drv.guard(force=False, pilot_dir=tmp_path)              # nothing there yet
    S.write_json(tmp_path / "dev_subjects.json", {"seed": 47})
    with pytest.raises(SystemExit, match="refused"):
        drv.guard(force=False, pilot_dir=tmp_path)
    drv.guard(force=True, pilot_dir=tmp_path)               # --force overrides


def test_check_extension_accepts_a_real_extension():
    drv = _driver()
    old = _draw_doc(FIVE)
    new = _draw_doc(FIVE[:3] + [ADDED] + FIVE[3:])
    assert drv.check_extension(old, new) == ["C9"]


def test_check_extension_rejects_a_dropped_subject():
    drv = _driver()
    with pytest.raises(SystemExit, match="would drop committed"):
        drv.check_extension(_draw_doc(FIVE), _draw_doc(FIVE[1:]))


def test_check_extension_rejects_a_moved_shuffle_position():
    drv = _driver()
    new = _draw_doc(FIVE[:3] + [ADDED] + FIVE[3:])
    new["subjects"][2]["shuffle_pos"] = 99
    with pytest.raises(SystemExit, match="moved from shuffle position"):
        drv.check_extension(_draw_doc(FIVE), new)


def test_check_extension_rejects_a_reorder():
    drv = _driver()
    swapped = [FIVE[1], FIVE[0]] + FIVE[2:] + [ADDED]
    with pytest.raises(SystemExit, match="relative order"):
        drv.check_extension(_draw_doc(FIVE), _draw_doc(swapped))


def test_check_extension_refuses_a_no_op():
    drv = _driver()
    with pytest.raises(SystemExit, match="nothing to add"):
        drv.check_extension(_draw_doc(FIVE), _draw_doc(FIVE))


def test_split_identity_ignores_guest_words_but_not_the_split():
    drv = _driver()
    row = subject("NPR-1|2001-01-01|P|cl1|S;NPR-2|2002-02-02|P|cl2|S")
    a = S.chronological_split(row)
    b = S.chronological_split(row)
    b["grounding"][0]["guest_words"] = 12345
    assert drv.split_identity(a) == drv.split_identity(b)
    b["grounding"][0]["transcript_id"] = "NPR-77"
    assert drv.split_identity(a) != drv.split_identity(b)


# ---------------------------------------------------------------------------
# End-to-end on synthetic data: draw -> split -> turns
# ---------------------------------------------------------------------------

def test_pipeline_on_synthetic_subject(tmp_path):
    row = subject(
        "NPR-1|2001-01-01|Prog A|cl1|S;"
        "NPR-2|2002-02-02|Prog B|cl2|S;"
        "NPR-3|2003-03-03|Prog C|cl3|S", name="Ann Lee")
    split = S.chronological_split(row)
    recs = [record("NPR-1", ["HOST, host", "Ms. ANN LEE"], ["q1", "a1 a1"]),
            record("NPR-2", ["HOST, host", "ANN LEE"], ["q2", "a2 a2 a2"]),
            record("NPR-3", ["HOST, host", "Ann Lee"], ["q3", "a3"])]
    path = fake_corpus(tmp_path, recs)
    tids = [g["transcript_id"] for g in split["grounding"]] + \
           [split["test"]["transcript_id"]]
    fetched = S.fetch_records(tids, path)

    ground = [t for g in split["grounding"]
              for t in S.extract_turns(fetched[g["transcript_id"]], row)]
    test = S.extract_turns(fetched[split["test"]["transcript_id"]], row)
    assert {t["transcript_id"] for t in ground} == {"NPR-1", "NPR-2"}
    assert all(t["transcript_id"] == "NPR-3" for t in test)
    assert sum(S.word_count(t["text"]) for t in ground if t["role"] == "guest") == 5

    out = tmp_path / "subjects" / "C00001"
    assert S.write_jsonl(out / "grounding_turns.jsonl", ground) == 4
    assert S.read_jsonl(out / "grounding_turns.jsonl") == ground
    S.write_json(out / "split.json", split)
    assert json.loads((out / "split.json").read_text())["test"]["transcript_id"] \
        == "NPR-3"
