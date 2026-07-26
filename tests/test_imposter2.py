"""Tests for src/doppler/imposter2.py (SPEC D7 same-domain imposter).

All fixtures are synthetic: no corpus, no network, no committed artifact is
read. The one file-backed test writes its own miniature news_dialogue.json into
tmp_path.
"""

from __future__ import annotations

import json
import math
import random

import pytest

from doppler.imposter2 import (
    NAME_RATIO,
    WORD_FLOOR,
    collect_donor_texts,
    cosine,
    donor_sample,
    donor_splits,
    grounding_text,
    guest_text,
    match_donors,
    name_conflict,
    name_tokens,
    sample_sha256,
    tfidf_vectors,
    tokenize,
)
from doppler.stage2_data import word_count, write_jsonl

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_row(cid, name, variants=(), transcripts=None, qualifies=True,
             clean=True, ambiguous=False):
    return {
        "canonical_id": cid,
        "canonical_name": name,
        "variants": list(variants),
        "qualifies": qualifies,
        "clean": clean,
        "ambiguous_identity": ambiguous,
        "transcripts": list(transcripts or []),
    }


def tr(tid, date, cluster, program="Program", substantive=True):
    return {"transcript_id": tid, "date": date, "program": program,
            "cluster_id": cluster, "substantive": substantive}


def text_of(vocab, n_words):
    """A document of exactly n_words words drawn cyclically from vocab."""
    return " ".join(vocab[i % len(vocab)] for i in range(n_words))


SYRIA = ["damascus", "border", "ceasefire", "refugees", "diplomacy"]
BASEBALL = ["pitcher", "innings", "bullpen", "shortstop", "dugout"]


# ---------------------------------------------------------------------------
# donor_sample — the derivation T2 must agree with
# ---------------------------------------------------------------------------


def big_pool(n=60):
    rows = [make_row(f"C{i:05d}", f"Person {i}") for i in range(n)]
    rows.append(make_row("C09001", "Not Qualified", qualifies=False))
    rows.append(make_row("C09002", "Not Clean", clean=False))
    rows.append(make_row("C09003", "Ambiguous", ambiguous=True))
    return rows


def test_donor_sample_is_deterministic():
    pool = big_pool()
    a = donor_sample(pool, ["C00000", "C00001"], seed=48, n=10)
    b = donor_sample(pool, ["C00000", "C00001"], seed=48, n=10)
    assert a == b
    assert len(a) == 10 and len(set(a)) == 10


def test_donor_sample_matches_the_documented_derivation():
    """random.Random(seed).sample over sorted eligible ids minus dev ids."""
    pool = big_pool()
    dev = ["C00003", "C00007"]
    ids = sorted(r["canonical_id"] for r in pool
                 if r["qualifies"] and r["clean"] and not r["ambiguous_identity"]
                 and r["canonical_id"] not in set(dev))
    assert donor_sample(pool, dev, seed=48, n=10) == random.Random(48).sample(ids, 10)


def test_donor_sample_excludes_dev_and_ineligible_ids():
    pool = big_pool()
    dev = ["C00000", "C00001", "C00002", "C00003", "C00004", "C00005"]
    got = donor_sample(pool, dev, seed=48, n=40)
    assert not set(got) & set(dev)
    assert not {"C09001", "C09002", "C09003"} & set(got)


def test_donor_sample_seed_changes_the_draw():
    pool = big_pool()
    assert donor_sample(pool, [], seed=48, n=20) != donor_sample(pool, [], seed=49, n=20)


def test_donor_sample_refuses_when_the_pool_is_too_small():
    with pytest.raises(ValueError, match="only"):
        donor_sample(big_pool(n=12), [], seed=48, n=200)


def test_sample_sha256_is_order_independent():
    ids = ["C3", "C1", "C2"]
    assert sample_sha256(ids) == sample_sha256(reversed(ids))
    assert sample_sha256(ids) != sample_sha256(["C1", "C2"])


# ---------------------------------------------------------------------------
# TF-IDF and cosine
# ---------------------------------------------------------------------------


def test_tokenize_drops_single_characters_and_lowercases():
    assert tokenize("A Big Cat, 42 x9!") == ["big", "cat", "42", "x9"]


def test_tfidf_matches_the_hand_computed_values():
    rows = tfidf_vectors(["a bb cc", "bb dd"])
    idf_rare = math.log(3 / 2) + 1.0          # df = 1, n = 2, smoothed
    norm = math.sqrt(1.0 + idf_rare ** 2)
    assert set(rows[0]) == {"bb", "cc"}       # "a" is below the token pattern
    assert rows[0]["bb"] == pytest.approx(1.0 / norm)
    assert rows[0]["cc"] == pytest.approx(idf_rare / norm)
    assert cosine(rows[0], rows[1]) == pytest.approx((1.0 / norm) ** 2)


def test_cosine_endpoints():
    same = tfidf_vectors(["alpha beta gamma", "alpha beta gamma"])
    assert cosine(same[0], same[1]) == pytest.approx(1.0)
    apart = tfidf_vectors(["alpha beta", "gamma delta"])
    assert cosine(apart[0], apart[1]) == 0.0


def test_tfidf_parity_with_sklearn_when_available():
    sk = pytest.importorskip("sklearn.feature_extraction.text")
    docs = [text_of(SYRIA, 40), text_of(BASEBALL, 55),
            text_of(SYRIA + BASEBALL, 30), "damascus damascus bullpen"]
    mine = tfidf_vectors(docs)
    theirs = sk.TfidfVectorizer().fit_transform(docs)
    for i in range(len(docs)):
        for j in range(len(docs)):
            assert cosine(mine[i], mine[j]) == pytest.approx(
                float((theirs[i] @ theirs[j].T).toarray()[0][0]), abs=1e-9)


# ---------------------------------------------------------------------------
# Name-similarity exclusion
# ---------------------------------------------------------------------------


def test_name_tokens_drop_particles_and_initials():
    row = make_row("C1", "Juan de la Cruz Jr.")
    assert name_tokens(row) == {"juan", "cruz"}


def test_shared_surname_is_a_conflict():
    hit, why = name_conflict(make_row("C1", "Robert Harris"),
                             make_row("C2", "Nina Harris"))
    assert hit and "harris" in why


def test_spelling_drift_is_a_conflict_without_a_shared_token():
    a, b = make_row("C1", "Frederic Hof"), make_row("C2", "Frederick Hoff")
    assert not name_tokens(a) & name_tokens(b)
    hit, why = name_conflict(a, b)
    assert hit and "difflib" in why


def test_a_variant_can_trigger_the_conflict():
    a = make_row("C1", "Samer Shehata", variants=["Samer Shehata", "S. Shehata"])
    b = make_row("C2", "Mona Shehata")
    assert name_conflict(a, b)[0]


def test_unrelated_names_sharing_only_particles_are_not_a_conflict():
    assert not name_conflict(make_row("C1", "Juan de la Cruz"),
                             make_row("C2", "Ana de la Vega"))[0]


def test_honorifics_do_not_hide_a_conflict():
    assert name_conflict(make_row("C1", "Dr. Robert Sampson"),
                         make_row("C2", "Mr. Peter Sampson"))[0]


# ---------------------------------------------------------------------------
# Grounding text
# ---------------------------------------------------------------------------


def test_guest_text_keeps_only_guest_turns_in_order():
    turns = [
        {"role": "host", "text": "question one"},
        {"role": "guest", "text": "answer one"},
        {"role": "other", "text": "third party"},
        {"role": "guest", "text": "answer two"},
        {"role": "guest", "text": "   "},
    ]
    assert guest_text(turns) == "answer one\nanswer two"


def test_grounding_text_reads_the_committed_turn_file(tmp_path):
    rows = [
        {"transcript_id": "NPR-1", "turn_idx": 0, "role": "host",
         "speaker_label": "HOST", "resolved_label": None, "text": "hello"},
        {"transcript_id": "NPR-1", "turn_idx": 1, "role": "guest",
         "speaker_label": "JANE DOE", "resolved_label": None, "text": "my answer"},
    ]
    write_jsonl(tmp_path / "subjects" / "C1" / "grounding_turns.jsonl", rows)
    assert grounding_text("C1", pilot_dir=tmp_path) == "my answer"


def donor_record(tid, guest_label, guest_lines, host="ANCHOR, CNN ANCHOR"):
    utt, spk = [], []
    for line in guest_lines:
        utt.append("host asks")
        spk.append(host)
        utt.append(line)
        spk.append(guest_label)
    return {"id": tid, "program": "Program", "date": "2010-01-01",
            "title": "T", "summary": "", "utt": utt, "speaker": spk}


def test_grounding_text_for_a_donor_excludes_the_test_cluster():
    row = make_row("C1", "Jane Doe", transcripts=[
        tr("NPR-1", "2010-01-01", "cl1"),
        tr("NPR-2", "2011-01-01", "cl2"),
        tr("NPR-3", "2012-01-01", "cl3"),      # latest = test, must not appear
    ])
    records = {
        "NPR-1": donor_record("NPR-1", "JANE DOE", ["early words"]),
        "NPR-2": donor_record("NPR-2", "JANE DOE", ["middle words"]),
        "NPR-3": donor_record("NPR-3", "JANE DOE", ["FORBIDDEN"]),
    }
    got = grounding_text("C1", pool=[row], records=records)
    assert got == "early words\n\nmiddle words"
    assert "FORBIDDEN" not in got


def test_donor_splits_report_donors_with_no_grounding_side():
    one = make_row("C1", "Only Once", transcripts=[tr("NPR-1", "2010-01-01", "cl1")])
    two = make_row("C2", "Twice Over", transcripts=[
        tr("NPR-2", "2010-01-01", "cl1"), tr("NPR-3", "2011-01-01", "cl2")])
    splits, skipped = donor_splits(["C1", "C2"], [one, two], guest_words={})
    assert set(splits) == {"C2"}
    assert "C1" in skipped


def test_collect_donor_texts_streams_one_pass(tmp_path):
    rows = [
        make_row("C1", "Jane Doe", transcripts=[
            tr("NPR-1", "2010-01-01", "cl1"), tr("NPR-9", "2015-01-01", "cl9")]),
        make_row("C2", "John Roe", transcripts=[
            tr("NPR-1", "2010-01-01", "cl1"), tr("NPR-8", "2015-01-01", "cl8")]),
    ]
    shared = {"id": "NPR-1", "utt": ["q", "jane says", "john says"],
              "speaker": ["ANCHOR, CNN ANCHOR", "JANE DOE", "JOHN ROE"]}
    corpus = [shared,
              donor_record("NPR-9", "JANE DOE", ["later jane"]),
              donor_record("NPR-8", "JOHN ROE", ["later john"])]
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(corpus), encoding="utf-8")

    texts, meta = collect_donor_texts(["C1", "C2"], rows, raw_path=path,
                                      guest_words={"C1": {}, "C2": {}},
                                      keep_turns=["C1"])
    # One transcript serves two donors; the later cluster is each donor's test.
    assert texts == {"C1": "jane says", "C2": "john says"}
    assert meta["n_transcripts_wanted"] == 1 and meta["n_transcripts_read"] == 1
    assert meta["missing_transcripts"] == [] and meta["malformed"] == {}
    assert [t["role"] for t in meta["turns"]["C1"]["NPR-1"]] == \
        ["host", "guest", "other"]
    assert "C2" not in meta["turns"]


# ---------------------------------------------------------------------------
# match_donors — the D7 rule
# ---------------------------------------------------------------------------


def matching_fixture(donor_specs, subject_name="Frederic Hof",
                     subject_vocab=SYRIA):
    """(dev_subjects, pool, subject_texts, donor_texts) for one subject."""
    pool = [make_row("C00001", subject_name)]
    donor_texts = {}
    for cid, name, vocab, n_words in donor_specs:
        pool.append(make_row(cid, name))
        donor_texts[cid] = text_of(vocab, n_words)
    subject_texts = {"C00001": text_of(subject_vocab, 1200)}
    return [{"canonical_id": "C00001"}], pool, subject_texts, donor_texts


def test_match_picks_the_most_similar_eligible_donor():
    dev, pool, st, dt = matching_fixture([
        ("C00100", "Alice Adams", SYRIA, 3000),
        ("C00200", "Bob Brown", BASEBALL, 3000),
    ])
    doc = match_donors(dev, pool, st, dt)
    assert doc["pairs"] == {"C00001": "C00100"}
    assert doc["similarity"]["C00001"] == pytest.approx(1.0)
    assert doc["runner_up_top5"]["C00001"][0][0] == "C00200"
    assert doc["n_eligible_donors"] == 2


def test_match_is_deterministic():
    dev, pool, st, dt = matching_fixture([
        ("C00100", "Alice Adams", SYRIA, 3000),
        ("C00200", "Bob Brown", SYRIA + BASEBALL, 4000),
        ("C00300", "Carol Cook", BASEBALL, 3000),
    ])
    assert match_donors(dev, pool, st, dt) == match_donors(dev, pool, st, dt)


def test_word_floor_excludes_a_short_donor():
    dev, pool, st, dt = matching_fixture([
        ("C00100", "Alice Adams", SYRIA, WORD_FLOOR - 1),   # best match, too short
        ("C00200", "Bob Brown", BASEBALL, WORD_FLOOR),
    ])
    doc = match_donors(dev, pool, st, dt)
    assert doc["pairs"] == {"C00001": "C00200"}
    assert doc["n_eligible_donors"] == 1
    assert "C00100" not in doc["donor_words"]


def test_word_floor_is_inclusive():
    dev, pool, st, dt = matching_fixture([("C00100", "Alice Adams", SYRIA,
                                           WORD_FLOOR)])
    assert match_donors(dev, pool, st, dt)["pairs"] == {"C00001": "C00100"}


def test_name_conflict_excludes_the_best_donor():
    dev, pool, st, dt = matching_fixture([
        ("C00100", "Rachel Hof", SYRIA, 3000),       # shares the subject surname
        ("C00200", "Bob Brown", SYRIA, 3000),
    ])
    doc = match_donors(dev, pool, st, dt)
    assert doc["pairs"] == {"C00001": "C00200"}
    assert doc["excluded_by_name"]["C00001"][0]["donor"] == "C00100"
    assert "C00100" not in [d for d, _ in doc["runner_up_top5"]["C00001"]]


def test_fuzzy_name_conflict_excludes_a_near_spelling():
    dev, pool, st, dt = matching_fixture([
        ("C00100", "Frederick Hoff", SYRIA, 3000),
        ("C00200", "Bob Brown", SYRIA, 3000),
    ])
    doc = match_donors(dev, pool, st, dt)
    assert doc["pairs"] == {"C00001": "C00200"}
    assert "difflib" in doc["excluded_by_name"]["C00001"][0]["reason"]


def test_ties_break_on_lexicographic_canonical_id():
    dev, pool, st, dt = matching_fixture([
        ("C00300", "Zoe Zane", SYRIA, 3000),
        ("C00200", "Bob Brown", SYRIA, 3000),        # identical text, smaller id
    ])
    doc = match_donors(dev, pool, st, dt)
    assert doc["similarity"]["C00001"] == pytest.approx(1.0)
    assert doc["pairs"] == {"C00001": "C00200"}
    assert doc["runner_up_top5"]["C00001"] == [["C00300", 1.0]]


def test_runner_up_list_is_capped_and_excludes_the_winner():
    specs = [(f"C0{100 * i:04d}", f"Person {i}", SYRIA + [f"topic{i}"], 3000)
             for i in range(1, 9)]
    dev, pool, st, dt = matching_fixture(specs)
    doc = match_donors(dev, pool, st, dt)
    runners = doc["runner_up_top5"]["C00001"]
    assert len(runners) == 5
    assert doc["pairs"]["C00001"] not in [d for d, _ in runners]
    sims = [s for _, s in runners]
    assert sims == sorted(sims, reverse=True)
    assert doc["similarity"]["C00001"] >= sims[0]


def test_a_dev_subject_in_the_donor_pool_is_fatal():
    dev, pool, st, dt = matching_fixture([("C00100", "Alice Adams", SYRIA, 3000)])
    dt["C00001"] = text_of(SYRIA, 3000)
    with pytest.raises(ValueError, match="dev subjects in the donor pool"):
        match_donors(dev, pool, st, dt)


def test_every_dev_subject_gets_a_pair_including_a_burned_one():
    dev = [{"canonical_id": "C00001"},
           {"canonical_id": "C00002", "burned_for_qa": True}]
    pool = [make_row("C00001", "Frederic Hof"), make_row("C00002", "Bassir Pour"),
            make_row("C00100", "Alice Adams"), make_row("C00200", "Bob Brown")]
    st = {"C00001": text_of(SYRIA, 1200), "C00002": text_of(BASEBALL, 1200)}
    dt = {"C00100": text_of(SYRIA, 3000), "C00200": text_of(BASEBALL, 3000)}
    doc = match_donors(dev, pool, st, dt)
    assert doc["pairs"] == {"C00001": "C00100", "C00002": "C00200"}
    assert doc["subject_words"] == {"C00001": 1200, "C00002": 1200}


def test_no_eligible_donor_is_an_error():
    dev, pool, st, dt = matching_fixture([("C00100", "Alice Adams", SYRIA, 10)])
    with pytest.raises(ValueError, match="grounding floor"):
        match_donors(dev, pool, st, dt)


def test_all_donors_blocked_by_name_is_an_error():
    dev, pool, st, dt = matching_fixture([("C00100", "Rachel Hof", SYRIA, 3000)])
    with pytest.raises(ValueError, match="excluded by name"):
        match_donors(dev, pool, st, dt)


def test_recorded_word_counts_use_the_whitespace_proxy():
    dev, pool, st, dt = matching_fixture([("C00100", "Alice Adams", SYRIA, 3000)])
    doc = match_donors(dev, pool, st, dt)
    assert doc["donor_words"]["C00100"] == word_count(dt["C00100"]) == 3000
    assert doc["name_ratio"] == NAME_RATIO and doc["word_floor"] == WORD_FLOOR
