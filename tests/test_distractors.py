"""SPEC D5 (entity heuristic) + D6 (bank, matching, shuffle). All synthetic.

No corpus read, no network. ``build_bank`` is exercised with an injected
``fetch_fn`` so the 4.45 GB file is never touched.
"""

from __future__ import annotations

import hashlib
from collections import Counter

import pytest

from doppler.distractors import (
    ADJACENT_BUCKETS,
    BANK_SEED,
    RELAX_LADDER,
    bank_row,
    bank_stats,
    build_bank,
    bucket_of,
    density_bucket,
    entity_density,
    is_abbreviation,
    latest_cluster,
    sample_donor_ids,
    select_distractors,
    shuffle_seed,
    strip_entities,
)

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def answer_with(n_words: int, n_entities: int, filler: str = "topic") -> str:
    """`n_words` whitespace tokens of which exactly `n_entities` are entities.

    Entities sit on odd positions so no two are adjacent (each is its own span)
    and none is sentence-initial (position 0 is filler, and there is no
    sentence-ending punctuation anywhere).
    """
    assert n_entities * 2 <= n_words
    toks, placed = [], 0
    for i in range(n_words):
        if i % 2 == 1 and placed < n_entities:
            toks.append("Zurich")
            placed += 1
        else:
            toks.append(filler)
    assert placed == n_entities
    return " ".join(toks)


def mk_row(subject: str, question: str, words: int, entities: int,
           tid: str | None = None) -> dict:
    text = answer_with(words, entities)
    density = entity_density(text)
    return {
        "question": question,
        "answer": text,
        "answer_words": words,
        "entity_density": density,
        "bucket": density_bucket(density),
        "source_canonical_id": subject,
        "source_transcript_id": tid or f"T-{subject}",
    }


def mk_item(subject: str = "C0DEV", words: int = 100, entities: int = 5,
            question: str = "what did you make of the vote in the assembly",
            tid: str = "T-DEV", turn: int = 3) -> dict:
    text = answer_with(words, entities)
    return {
        "item_id": f"{subject}:{tid}:{turn}",
        "canonical_id": subject,
        "transcript_id": tid,
        "q_turn_idx": turn,
        "question": question,
        "answer": text,
        "answer_words": words,
        "flags": [],
    }


def big_bank(n: int = 30, words: int = 100, entities: int = 5,
             prefix: str = "D") -> list[dict]:
    return [mk_row(f"{prefix}{i:03d}", f"what about topic number {i} today",
                   words, entities) for i in range(n)]


# ---------------------------------------------------------------------------
# D5 — density
# ---------------------------------------------------------------------------

def test_density_is_entity_tokens_over_whitespace_tokens():
    assert entity_density(answer_with(100, 5)) == pytest.approx(0.05)
    assert entity_density(answer_with(20, 0)) == 0.0
    assert entity_density("") == 0.0


def test_a_lone_sentence_initial_capital_is_not_an_entity():
    assert entity_density("The dog barked at the cat") == 0.0
    assert entity_density("the dog barked. The cat ran") == 0.0


def test_a_mid_sentence_capital_is_an_entity():
    d = entity_density("the dog barked at Rex")
    assert d == pytest.approx(1 / 5)


def test_a_multi_token_span_counts_even_at_a_sentence_start():
    """"not SOLELY sentence-initial" -- the second capital is unexplained."""
    d = entity_density("New York is big")
    assert d == pytest.approx(2 / 4)


def test_maximal_span_counts_every_token_in_it():
    d = entity_density("he met Angela Dorothea Merkel today")
    assert d == pytest.approx(3 / 6)


def test_numbers_need_two_digits_but_money_and_percent_need_one():
    assert entity_density("we lost 5 games") == 0.0
    assert entity_density("we lost 15 games") == pytest.approx(1 / 4)
    assert entity_density("it cost $5 today") == pytest.approx(1 / 4)
    assert entity_density("it rose 5% today") == pytest.approx(1 / 4)
    assert entity_density("about 1,300 people came") == pytest.approx(1 / 4)


def test_punctuation_around_a_name_does_not_hide_it():
    assert entity_density('he said "Berlin" loudly') == pytest.approx(1 / 4)
    assert entity_density("he went to Berlin, then home") == pytest.approx(1 / 6)


def test_bucket_edges():
    assert density_bucket(0.0) == "Z"
    assert density_bucket(0.02) == "Z"
    assert density_bucket(0.0201) == "L"
    assert density_bucket(0.08) == "L"
    assert density_bucket(0.0801) == "H"
    assert density_bucket(1.0) == "H"


def test_bucket_of_returns_literal_buckets_at_the_boundaries():
    """Text-to-bucket end to end, against literal expected values.

    Densities are exact by construction: answer_with(1000, k) puts exactly k
    entity tokens in 1000 words, so k/1000 IS the density. Nothing here is
    computed by the code under test.
    """
    assert entity_density(answer_with(1000, 19)) == 0.019
    assert bucket_of(answer_with(1000, 19)) == "Z"      # below the Z/L edge
    assert entity_density(answer_with(1000, 20)) == 0.020
    assert bucket_of(answer_with(1000, 20)) == "Z"      # ON the edge: Z wins
    assert entity_density(answer_with(1000, 21)) == 0.021
    assert bucket_of(answer_with(1000, 21)) == "L"      # just over
    assert entity_density(answer_with(1000, 80)) == 0.080
    assert bucket_of(answer_with(1000, 80)) == "L"      # ON the edge: L wins
    assert entity_density(answer_with(1000, 81)) == 0.081
    assert bucket_of(answer_with(1000, 81)) == "H"      # just over
    assert bucket_of(answer_with(1000, 0)) == "Z"
    assert bucket_of(answer_with(1000, 500)) == "H"


def test_adjacency_is_symmetric_and_z_is_not_adjacent_to_h():
    for a, neighbours in ADJACENT_BUCKETS.items():
        for b in neighbours:
            assert a in ADJACENT_BUCKETS[b]
    assert "H" not in ADJACENT_BUCKETS["Z"]
    assert "Z" not in ADJACENT_BUCKETS["H"]


# ---------------------------------------------------------------------------
# D5-r2 (SPEC v1.4) — the pronoun family, and spans breaking at sentences
# ---------------------------------------------------------------------------

def test_the_pronoun_i_is_never_an_entity():
    assert entity_density("that's why I referred to it") == 0.0
    assert entity_density("I told them so") == 0.0


def test_the_i_contraction_family_is_never_an_entity():
    for form in ("I'm", "I've", "I'd", "I'll"):
        assert entity_density(f"and {form} sure about that") == 0.0, form
    # Same word however the transcriber typed the apostrophe.
    for form in ("I’m", "I’ve", "I’d", "I’ll"):
        assert entity_density(f"and {form} sure about that") == 0.0, form


def test_i_forms_are_case_exact_so_real_names_still_count():
    """"I" is the pronoun; "Ian" and "Id" are not."""
    assert entity_density("he met Ian today") == pytest.approx(1 / 4)
    assert entity_density("he met Ivan today") == pytest.approx(1 / 4)
    assert entity_density("he read the Id chapter") == pytest.approx(1 / 5)


def test_the_pronoun_does_not_hold_a_span_together():
    """Only "Rex" is a name here -- the pronoun must not glue on "think"."""
    assert entity_density("he met Rex I think") == pytest.approx(1 / 5)
    assert strip_entities("he met Rex I think") == "he met [NAME] I think"


def test_a_capitalised_span_breaks_at_a_sentence_boundary():
    """The case that motivated D5-r2(b): two sentences, not one name."""
    text = "Absolutely. He should have returned immediately."
    assert entity_density(text) == 0.0
    assert strip_entities(text) == text


def test_a_multi_token_name_after_a_sentence_boundary_still_counts():
    assert entity_density("he left. New York was cold") == pytest.approx(2 / 6)
    assert strip_entities("he left. New York was cold") == "he left. [NAME] was cold"


def test_an_i_heavy_passage_no_longer_mis_buckets():
    """Under the first D5 reading this scored 5/35 = 0.143 and bucketed H.

    The five "entity" tokens it found were "I", "I", "Later I've" and "I'd".
    There is not a single name in the passage, so H was simply wrong; both
    D5-r2 fixes are needed to get it to Z (the pronouns, and the span that
    glued a sentence opening to the pronoun after it).
    """
    text = ("I went along to the meeting and I listened for a while. "
            "I'm not sure I agreed with any of it. "
            "Later I've thought about it a lot and I'd say it went badly here.")
    assert len(text.split()) == 35
    assert entity_density(text) == 0.0
    assert density_bucket(entity_density(text)) == "Z"
    assert strip_entities(text) == " ".join(text.split())


# ---------------------------------------------------------------------------
# D5-r3 (SPEC v1.6) — an abbreviation's dot does not end a sentence
# ---------------------------------------------------------------------------

def test_is_abbreviation_covers_exactly_the_three_spec_cases():
    assert is_abbreviation("Mr")                # honorific
    assert is_abbreviation("Gen")
    assert is_abbreviation("U.S")               # internal dot
    assert is_abbreviation("R")                 # single initial
    assert not is_abbreviation("reasons")
    assert not is_abbreviation("St")            # see the dedicated test below
    assert not is_abbreviation("")


def test_an_honorific_dot_no_longer_splits_a_name():
    """The case D5-r3 exists for: A4.2's stripped variant must lose "Morsi"."""
    assert entity_density("opposed to Mr. Morsi before then") == \
        pytest.approx(2 / 6)
    assert strip_entities("opposed to Mr. Morsi before then") == \
        "opposed to [NAME] before then"


def test_an_internal_dot_no_longer_splits_a_name():
    assert strip_entities("the U.S. Government said so") == \
        "the [NAME] said so"


def test_a_military_honorific_no_longer_splits_a_name():
    assert strip_entities("he served under Gen. Petraeus in Iraq") == \
        "he served under [NAME] in [NAME]"


def test_a_single_initial_no_longer_splits_a_name():
    assert strip_entities("signed by R. Harris yesterday") == \
        "signed by [NAME] yesterday"


def test_bang_and_question_mark_still_end_a_sentence_after_an_abbreviation():
    """Only "." is ambiguous. "!" and "?" are not, whatever precedes them."""
    assert entity_density("ask Mr? Morsi was there") == pytest.approx(1 / 5)
    assert entity_density("ask Mr! Morsi was there") == pytest.approx(1 / 5)


def test_d5_r2_sentence_breaking_still_works_after_r3():
    assert entity_density("Absolutely. He should have returned") == 0.0
    assert strip_entities("he left. New York was cold") == \
        "he left. [NAME] was cold"


def test_the_price_of_r3_a_real_sentence_end_after_an_initial_like_word():
    """PINS THE APPROVED TRADE-OFF, not desirable behaviour in itself.

    A "." after an abbreviation-shaped token is read as an abbreviation even
    when it really did end the sentence, so the next sentence's opening word
    is swallowed into the span. The orchestrator accepted this on the record:
    density noise is cheaper than leaving a real surname in the stripped
    variant, which is a pre-registered control (A4.2).
    """
    assert strip_entities("he got an A. The result was fine") == \
        "he got an [NAME] result was fine"
    assert strip_entities("it happened in the U.S. Nobody noticed") == \
        "it happened in the [NAME] noticed"


def test_known_d5_r3_limit_a_spelled_out_title_reads_as_an_abbreviation():
    """PINS A KNOWN MISFIRE, not desirable behaviour.

    HONORIFIC holds titles spelled out in full (PRESIDENT, GENERAL, JUSTICE,
    FATHER, SIR) as well as abbreviations, and 58 of its 83 entries are
    ordinary English words. A spelled-out title never carries an abbreviation
    dot -- the abbreviation is "Pres." -- so "became president. And of course"
    really is a sentence end, but D5-r3 as v1.6 writes it reads the dot as an
    abbreviation and glues "And" into the span.

    Measured: 15 of 653 bank rows (2%); fixing it would move 4 bank rows and
    0 items between buckets. Reported to the orchestrator; the fix is to
    narrow the clause to a curated abbreviation list, which is a new rule.
    """
    assert is_abbreviation("president")          # the misfire, at its root
    assert is_abbreviation("general")
    assert is_abbreviation("sir")
    assert strip_entities("he became president. And of course it was") == \
        "he became president. [NAME] of course it was"


def test_honorific_set_has_not_drifted_under_d5_r3():
    """D5-r3's semantics are a function of stage2_data.HONORIFIC, which is
    T1's file. If an edit there adds or removes an entry, which dots count as
    abbreviations changes silently and the bank's buckets move with it.

    This pins the set. A deliberate change to HONORIFIC should update this
    hash AND trigger a bank rebuild; an accidental one fails here first.
    """
    import hashlib

    from doppler.stage2_data import HONORIFIC

    digest = hashlib.sha256(
        "\n".join(sorted(HONORIFIC)).encode("utf-8")).hexdigest()[:16]
    assert len(HONORIFIC) == 83, f"HONORIFIC size changed to {len(HONORIFIC)}"
    assert digest == "4a42d8725c6eaa72", (
        "stage2_data.HONORIFIC changed. D5-r3 reads it to decide which "
        "trailing dots are abbreviations, so the entity buckets and the "
        "distractor bank move with it. Review, then update this hash and "
        "rebuild the bank.")
    # The entries D5-r3 actually leans on, named so a removal is legible.
    for abbrev in ("MR", "MRS", "DR", "GEN", "COL", "SEN", "REV", "CAPT"):
        assert abbrev in HONORIFIC, abbrev


def test_d5_r3_does_not_cover_st_because_v1_6_does_not_say_so():
    """PINS A GAP. "ST" is not in HONORIFIC, has no internal dot and is not a
    single initial, so "St. Petersburg" still splits and "Petersburg" still
    survives into the stripped text. Covering it means extending HONORIFIC or
    adding a fourth case; neither is in v1.6. Reported, not patched.
    """
    assert strip_entities("in St. Petersburg this week") == \
        "in [NAME]. Petersburg this week"


# ---------------------------------------------------------------------------
# D5 — stripping
# ---------------------------------------------------------------------------

def test_strip_replaces_names_and_numbers_and_keeps_the_rest():
    assert strip_entities("he met Rex in 1997 and paid $5") == \
        "he met [NAME] in [NUMBER] and paid [NUMBER]"


def test_strip_leaves_a_sentence_initial_capital_alone():
    assert strip_entities("The dog barked. The cat ran") == \
        "The dog barked. The cat ran"


def test_strip_collapses_a_whole_span_into_one_placeholder():
    assert strip_entities("he met Angela Dorothea Merkel today") == \
        "he met [NAME] today"


def test_strip_preserves_surrounding_punctuation():
    assert strip_entities('he went to "Berlin", then home') == \
        'he went to "[NAME]", then home'


def test_strip_is_idempotent_on_already_stripped_text():
    once = strip_entities("he met Rex in 1997")
    assert strip_entities(once) == once


def test_strip_of_empty_text_is_empty():
    assert strip_entities("") == ""
    assert strip_entities(None) == ""


# ---------------------------------------------------------------------------
# D6 — donor sample
# ---------------------------------------------------------------------------

def fake_pool(n: int = 40) -> list[dict]:
    """Synthetic donors. Names must be real-looking: "Person 3" classifies as
    anonymous (GENERIC_TOKENS), so its turns would never be role "guest"."""
    rows = []
    for i in range(n):
        rows.append({
            "canonical_id": f"C{i:05d}",
            "canonical_name": f"Dana Krell{i}",
            "variants": [f"Dana Krell{i}"],
            "wiki_status": "long-tail" if i % 2 else "has-page",
            "clean": True, "qualifies": True, "ambiguous_identity": False,
            "transcripts": [
                {"transcript_id": f"T-{i}-a", "date": "2001-01-01",
                 "program": "Show", "cluster_id": "cl1", "substantive": True},
                {"transcript_id": f"T-{i}-b", "date": "2009-09-09",
                 "program": "Show", "cluster_id": "cl2", "substantive": True},
            ],
        })
    return rows


def test_donor_sample_is_deterministic_and_excludes_every_dev_subject():
    pool = fake_pool()
    dev = ["C00000", "C00001", "C00002", "C00003", "C00004", "C00005"]
    a = sample_donor_ids(pool, dev, seed=BANK_SEED, n_donors=10)
    b = sample_donor_ids(pool, dev, seed=BANK_SEED, n_donors=10)
    assert a == b
    assert len(a) == len(set(a)) == 10
    assert not set(a) & set(dev)


def test_donor_sample_changes_with_the_seed():
    pool = fake_pool()
    assert sample_donor_ids(pool, [], seed=48, n_donors=10) != \
        sample_donor_ids(pool, [], seed=49, n_donors=10)


def test_donor_sample_ignores_ineligible_rows():
    pool = fake_pool(12)
    pool[0]["clean"] = False
    pool[1]["qualifies"] = False
    pool[2]["ambiguous_identity"] = True
    got = sample_donor_ids(pool, [], n_donors=9)
    assert set(got).isdisjoint({"C00000", "C00001", "C00002"})


def test_donor_sample_refuses_to_run_short():
    with pytest.raises(ValueError, match="need 50"):
        sample_donor_ids(fake_pool(10), [], n_donors=50)


# ---------------------------------------------------------------------------
# D6 — latest cluster and bank build
# ---------------------------------------------------------------------------

def test_latest_cluster_takes_the_latest_date():
    row = fake_pool(1)[0]
    assert latest_cluster(row)["transcript_id"] == "T-0-b"


def test_latest_cluster_ignores_non_substantive_transcripts():
    row = fake_pool(1)[0]
    row["transcripts"][1]["substantive"] = False
    assert latest_cluster(row)["transcript_id"] == "T-0-a"


def test_latest_cluster_needs_no_grounding_unlike_the_dev_split():
    """A one-interview donor is still a perfectly good distractor source."""
    row = fake_pool(1)[0]
    row["transcripts"] = row["transcripts"][:1]
    assert latest_cluster(row)["transcript_id"] == "T-0-a"


def test_latest_cluster_is_none_when_nothing_is_substantive():
    row = fake_pool(1)[0]
    for e in row["transcripts"]:
        e["substantive"] = False
    assert latest_cluster(row) is None


def test_latest_cluster_representative_is_the_most_guest_words():
    row = fake_pool(1)[0]
    row["transcripts"].append({"transcript_id": "T-0-c", "date": "2009-09-09",
                               "program": "Show", "cluster_id": "cl2",
                               "substantive": True})
    assert latest_cluster(row, {"T-0-b": 10, "T-0-c": 99})["transcript_id"] == "T-0-c"


#: Deliberately unalike, so D4's near-duplicate rule does not eat them.
DONOR_QUESTIONS = [
    "What did you make of the vote in the assembly last night?",
    "How would you describe the mood among ordinary voters now?",
    "Why has the currency moved so sharply in the past fortnight?",
]


def donor_record(tid: str, name: str, n_pairs: int = 2) -> dict:
    speaker = ["ANNE SMITH, HOST", name]
    utt = ["Welcome to the show tonight, we have a special guest with us.",
           "Thanks for having me on the programme this evening."]
    for k in range(n_pairs):
        speaker += ["ANNE SMITH, HOST", name]
        utt += [DONOR_QUESTIONS[k % len(DONOR_QUESTIONS)], answer_with(60, 3)]
    return {"id": tid, "speaker": speaker, "utt": utt}


def fetch_from(pool):
    """A fetch_fn over synthetic records, so no corpus file is ever opened."""
    names = {e["transcript_id"]: r["canonical_name"]
             for r in pool for e in r["transcripts"]}

    def fetch(ids):
        return {t: donor_record(t, names[t]) for t in ids}
    return fetch


def test_build_bank_uses_only_the_latest_transcript_of_each_donor():
    pool = fake_pool(12)
    dev = ["C00000"]
    fetched: list[list[str]] = []
    inner = fetch_from(pool)

    def fetch(ids):
        fetched.append(list(ids))
        return inner(ids)

    bank = build_bank(pool, dev, n_donors=6, fetch_fn=fetch, guest_words={})
    assert len(fetched) == 1                       # one pass, not one per donor
    assert all(t.endswith("-b") for t in fetched[0])
    assert {r["source_transcript_id"] for r in bank} <= set(fetched[0])
    assert len(bank) == 6 * 2
    assert all(r["source_canonical_id"] != "C00000" for r in bank)


def test_build_bank_rows_carry_the_d6_schema():
    pool = fake_pool(12)
    bank = build_bank(pool, [], n_donors=3, fetch_fn=fetch_from(pool),
                      guest_words={})
    assert set(bank[0]) == {"question", "answer", "answer_words",
                            "entity_density", "bucket", "source_canonical_id",
                            "source_transcript_id"}


def test_build_bank_reports_donors_with_no_substantive_transcript():
    pool = fake_pool(12)
    for e in pool[11]["transcripts"]:
        e["substantive"] = False
    seen = []
    build_bank(pool, [], n_donors=12, fetch_fn=fetch_from(pool), guest_words={},
               on_donor=lambda cid, tid, items, note: seen.append((cid, note)))
    assert ("C00011", "no substantive transcript") in seen


def test_build_bank_is_deterministic():
    pool = fake_pool(20)
    fetch = fetch_from(pool)
    a = build_bank(pool, ["C00000"], n_donors=8, fetch_fn=fetch, guest_words={})
    b = build_bank(pool, ["C00000"], n_donors=8, fetch_fn=fetch, guest_words={})
    assert a == b


def test_bank_row_matches_entity_density_of_its_answer():
    item = mk_item(words=100, entities=12)
    row = bank_row(item)
    assert row["entity_density"] == entity_density(item["answer"])
    assert row["bucket"] == density_bucket(row["entity_density"])


def test_bank_stats_counts_what_it_says():
    bank = big_bank(10)
    stats = bank_stats(bank)
    assert stats["n_rows"] == 10
    assert stats["n_donor_subjects_with_items"] == 10
    assert sum(stats["buckets"].values()) == 10


# ---------------------------------------------------------------------------
# D6 — matching and the relaxation ladder
# ---------------------------------------------------------------------------

def test_rung_zero_when_the_control_is_satisfiable():
    item = mk_item(words=100, entities=5)             # density .05 -> L
    bank = big_bank(20, words=100, entities=5)
    out = select_distractors(item, bank)
    assert out["relax_rung"] == 0
    assert out["flags"] == ["relax_rung_0"]
    assert len(out["options"]) == 4


def test_length_control_holds_at_rung_zero():
    item = mk_item(words=100, entities=5)
    bank = ([mk_row(f"A{i}", f"what about topic {i}", 100, 5) for i in range(3)]
            + [mk_row(f"B{i}", f"what about topic {i}", 160, 8) for i in range(20)])
    out = select_distractors(item, bank)
    assert out["relax_rung"] == 0
    for opt in out["options"]:
        assert 80 <= opt["answer_words"] <= 120


def test_rung_one_widens_the_length_window_only():
    item = mk_item(words=100, entities=5)
    # Nothing within +-20%; three rows at 128 words (+28%), same L bucket.
    bank = [mk_row(f"A{i}", f"what about topic {i}", 128, 7) for i in range(6)]
    assert all(r["bucket"] == "L" for r in bank)
    out = select_distractors(item, bank)
    assert out["relax_rung"] == 1
    assert {o["answer_words"] for o in out["options"] if o["kind"] == "distractor"} \
        == {128}


def test_rung_two_opens_the_adjacent_bucket():
    item = mk_item(words=100, entities=5)             # L
    bank = [mk_row(f"A{i}", f"what about topic {i}", 110, 15) for i in range(6)]
    assert all(r["bucket"] == "H" for r in bank)      # adjacent to L
    out = select_distractors(item, bank)
    assert out["relax_rung"] == 2


def test_rung_three_widens_the_length_window_again():
    item = mk_item(words=100, entities=5)             # L
    bank = [mk_row(f"A{i}", f"what about topic {i}", 145, 22) for i in range(6)]
    assert all(r["bucket"] == "H" for r in bank)      # +45%, adjacent bucket
    out = select_distractors(item, bank)
    assert out["relax_rung"] == 3


def test_the_ladder_stops_at_the_first_rung_that_works():
    item = mk_item(words=100, entities=5)
    bank = ([mk_row(f"A{i}", f"what about topic {i}", 100, 5) for i in range(3)]
            + [mk_row(f"B{i}", f"what about topic {i}", 145, 22) for i in range(9)])
    out = select_distractors(item, bank)
    assert out["relax_rung"] == 0


def test_an_unreachable_item_is_flagged_not_silently_shortened():
    item = mk_item(words=100, entities=0)             # Z bucket
    bank = [mk_row("A0", "what about topic zero", 100, 0)]
    out = select_distractors(item, bank)
    assert out["relax_rung"] == len(RELAX_LADDER) - 1
    assert "insufficient_candidates" in out["flags"]
    assert len(out["options"]) == 2


def test_z_and_h_never_substitute_for_each_other_even_at_the_last_rung():
    item = mk_item(words=100, entities=0)             # Z
    bank = [mk_row(f"A{i}", f"what about topic {i}", 100, 30) for i in range(9)]
    assert all(r["bucket"] == "H" for r in bank)
    out = select_distractors(item, bank)
    assert "insufficient_candidates" in out["flags"]
    assert len(out["options"]) == 1


# ---------------------------------------------------------------------------
# D6-r2 (SPEC v1.7) — three distinct donors
# ---------------------------------------------------------------------------

def test_the_three_distractors_come_from_three_different_people():
    """Even when one donor owns the three most similar questions."""
    item = mk_item(question="the vote in the assembly")
    bank = [
        mk_row("HOG", "the vote in the assembly", 100, 5, tid="T-HOG-1"),
        mk_row("HOG", "the vote in the assembly today", 100, 5, tid="T-HOG-2"),
        mk_row("HOG", "the vote in the assembly again", 100, 5, tid="T-HOG-3"),
        mk_row("D1", "the vote was close", 100, 5),
        mk_row("D2", "an entirely different matter", 100, 5),
        mk_row("D3", "another unrelated question here", 100, 5),
    ]
    out = select_distractors(item, bank)
    donors = [o["source_canonical_id"] for o in out["options"]
              if o["kind"] == "distractor"]
    assert len(donors) == 3
    assert len(set(donors)) == 3
    assert donors.count("HOG") == 1          # its best row, and only that one
    assert "duplicate_donor" not in out["flags"]


def test_the_ladder_is_walked_before_a_duplicate_donor_is_allowed():
    """Rung 0 has 3 rows but only 2 donors; rung 1 has 3 donors. Rung 1 wins."""
    item = mk_item(words=100, entities=5)
    bank = [
        mk_row("A1", "what about the vote", 100, 5, tid="T-A1-a"),
        mk_row("A1", "what about the vote later", 100, 5, tid="T-A1-b"),
        mk_row("A2", "what about the vote again", 100, 5),
        # +28%: out of reach at rung 0, in reach at rung 1, same L bucket.
        mk_row("B1", "what about the vote once more", 128, 7),
        mk_row("B2", "what about the vote finally", 128, 7),
        mk_row("B3", "what about the vote at last", 128, 7),
    ]
    out = select_distractors(item, bank)
    assert out["relax_rung"] == 1
    donors = [o["source_canonical_id"] for o in out["options"]
              if o["kind"] == "distractor"]
    assert len(set(donors)) == 3
    assert "duplicate_donor" not in out["flags"]


def test_a_duplicate_donor_is_permitted_only_at_the_final_rung_and_flagged():
    """One donor, three rows, nothing else in the bank at any tolerance."""
    item = mk_item(words=100, entities=5)
    bank = [mk_row("ONLY", f"what about topic {i}", 100, 5, tid=f"T-ONLY-{i}")
            for i in range(3)]
    out = select_distractors(item, bank)
    assert out["relax_rung"] == len(RELAX_LADDER) - 1
    assert "duplicate_donor" in out["flags"]
    donors = [o["source_canonical_id"] for o in out["options"]
              if o["kind"] == "distractor"]
    assert donors == ["ONLY", "ONLY", "ONLY"]
    assert len(out["options"]) == 4


def test_a_duplicated_donor_never_repeats_the_same_bank_row():
    """A duplicate donor is still three different answers, not one thrice."""
    item = mk_item(words=100, entities=5)
    bank = [mk_row("ONLY", f"what about topic {i}", 100, 5, tid=f"T-ONLY-{i}")
            for i in range(3)]
    out = select_distractors(item, bank)
    texts = [o["source_transcript_id"] for o in out["options"]
             if o["kind"] == "distractor"]
    assert len(set(texts)) == 3


def test_distinct_donors_hold_across_every_pilot_shaped_item():
    item = mk_item()
    out = select_distractors(item, big_bank(20))
    donors = [o["source_canonical_id"] for o in out["options"]
              if o["kind"] == "distractor"]
    assert len(set(donors)) == 3


def test_a_distractor_never_comes_from_the_subject_itself():
    """The one rule the relaxation ladder may never touch."""
    item = mk_item(subject="C0DEV", words=100, entities=5)
    own = [mk_row("C0DEV", "what did you make of the vote in the assembly",
                  100, 5, tid=f"T-DEV-{i}") for i in range(20)]
    other = [mk_row("D999", "a totally unrelated matter entirely", 100, 5)]
    out = select_distractors(item, own + other)
    sources = {o["source_canonical_id"] for o in out["options"]
               if o["kind"] == "distractor"}
    assert sources == {"D999"}


def test_question_similarity_decides_which_candidates_win():
    item = mk_item(question="what did you make of the vote in the assembly")
    bank = [
        mk_row("A1", "what did you make of the vote in the assembly today", 100, 5),
        mk_row("A2", "what did you make of the vote in the assembly then", 100, 5),
        mk_row("A3", "what did you make of the vote in the assembly now", 100, 5),
        mk_row("B1", "how do you bake sourdough bread properly", 100, 5),
        mk_row("B2", "how do you bake rye bread properly", 100, 5),
        mk_row("B3", "how do you bake bread at altitude", 100, 5),
    ]
    out = select_distractors(item, bank)
    picked = {o["source_canonical_id"] for o in out["options"]
              if o["kind"] == "distractor"}
    assert picked == {"A1", "A2", "A3"}


def test_the_three_top_ranked_candidates_win_in_a_hand_computed_ranking():
    """Asserts the actual selection property against a ranking worked out by
    hand, not against whatever the code happened to produce.

    The query is "the vote in the assembly". Overlap with the query, in words:
    A1 shares all four content words, A2 three, A3 two, B1 one, B2/B3 none. So
    the ranking is A1 > A2 > A3 > B1 > {B2, B3}, and the three that must be
    picked are A1, A2, A3 — in that order, since selection order is recorded
    before the shuffle.
    """
    item = mk_item(question="the vote in the assembly")
    bank = [
        mk_row("A1", "the vote in the assembly", 100, 5),
        mk_row("A2", "the vote in the chamber", 100, 5),
        mk_row("A3", "the vote today", 100, 5),
        mk_row("B1", "the sourdough bread recipe", 100, 5),
        mk_row("B2", "baking rye at altitude", 100, 5),
        mk_row("B3", "planting onions in spring", 100, 5),
    ]
    out = select_distractors(item, bank)
    by_donor = {o["source_canonical_id"]: o for o in out["options"]
                if o["kind"] == "distractor"}
    assert set(by_donor) == {"A1", "A2", "A3"}
    assert by_donor["A1"]["question_similarity"] > \
        by_donor["A2"]["question_similarity"] > \
        by_donor["A3"]["question_similarity"] > 0.0


# ---------------------------------------------------------------------------
# D6 — shuffle, correct_index, stripped variant
# ---------------------------------------------------------------------------

def test_shuffle_seed_is_the_spec_formula():
    seed = shuffle_seed("C00792:NPR-1:7")
    assert seed == int(hashlib.sha256(b"C00792:NPR-1:7").hexdigest()[:8], 16)


def test_same_item_and_bank_give_the_same_options_in_the_same_order():
    item, bank = mk_item(), big_bank(20)
    a = select_distractors(item, bank)
    b = select_distractors(item, bank)
    assert a == b
    assert [o["text"] for o in a["options"]] == [o["text"] for o in b["options"]]
    assert a["correct_index"] == b["correct_index"]


def test_correct_index_points_at_the_true_answer_after_the_shuffle():
    bank = big_bank(20)
    for turn in range(40):
        item = mk_item(turn=turn)
        out = select_distractors(item, bank)
        opt = out["options"][out["correct_index"]]
        assert opt["kind"] == "true"
        assert opt["text"] == item["answer"]
        assert sum(1 for o in out["options"] if o["kind"] == "true") == 1


def test_the_true_answer_does_not_sit_in_one_position():
    """A constant seed would put it at the same index every time."""
    bank = big_bank(20)
    seen = Counter(select_distractors(mk_item(turn=t), bank)["correct_index"]
                   for t in range(60))
    assert set(seen) == {0, 1, 2, 3}


def test_options_stripped_holds_the_literal_stripped_text_in_the_same_order():
    """Literal expected strings, so this cannot mirror the implementation.

    Each option's text is known, so its stripped form is known; the test
    writes both out and checks the alignment survives the shuffle.
    """
    def row(donor: str, question: str, answer: str) -> dict:
        density = entity_density(answer)
        return {"question": question, "answer": answer,
                "answer_words": len(answer.split()),
                "entity_density": density, "bucket": density_bucket(density),
                "source_canonical_id": donor,
                "source_transcript_id": f"T-{donor}"}

    item = mk_item(question="what happened at the meeting")
    item["answer"] = "we met Rex in 1997 and paid $5"
    item["answer_words"] = 8
    bank = [
        row("D1", "what happened at the meeting", "she met Ada in 2001 and paid $9"),
        row("D2", "what happened at the hearing", "they met Bob in 1985 and paid $3"),
        row("D3", "what happened at the trial", "he met Cleo in 1972 and paid $7"),
    ]
    expected = {
        "we met Rex in 1997 and paid $5": "we met [NAME] in [NUMBER] and paid [NUMBER]",
        "she met Ada in 2001 and paid $9": "she met [NAME] in [NUMBER] and paid [NUMBER]",
        "they met Bob in 1985 and paid $3": "they met [NAME] in [NUMBER] and paid [NUMBER]",
        "he met Cleo in 1972 and paid $7": "he met [NAME] in [NUMBER] and paid [NUMBER]",
    }
    out = select_distractors(item, bank)
    assert len(out["options_stripped"]) == len(out["options"]) == 4
    for opt, stripped in zip(out["options"], out["options_stripped"]):
        assert stripped == expected[opt["text"]]
    assert out["options_stripped"][out["correct_index"]] == \
        "we met [NAME] in [NUMBER] and paid [NUMBER]"


def test_selection_output_carries_the_d6_keys():
    out = select_distractors(mk_item(), big_bank(20))
    assert set(out) == {"item_id", "options", "correct_index", "relax_rung",
                        "flags", "options_stripped"}
    assert set(out["options"][0]) >= {"text", "kind", "source_canonical_id",
                                      "source_transcript_id", "answer_words",
                                      "entity_density"}
