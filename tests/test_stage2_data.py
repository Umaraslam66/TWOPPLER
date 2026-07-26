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


def test_registry_same_person_two_spellings_is_not_ambiguous():
    reg = S.surname_registry(["RICHARD ROTH, CNN ANCHOR", "Mr. Richard Roth"])
    assert reg["roth"] == "RICHARD ROTH, CNN ANCHOR"   # first spelling wins


def test_resolution_does_not_touch_labels_that_carry_a_role():
    """'HARRIS, host' is already a complete label; it is never rewritten."""
    row = subject("NPR-1|2001-01-01|P|cl1|S", name="Ann Lee")
    rec = record("NPR-1", ["ANN LEE", "HARRIS, host"], ["a", "b"])
    turns = S.extract_turns(rec, row)
    assert [t["role"] for t in turns] == ["guest", "host"]
    assert turns[1]["resolved_label"] is None


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
