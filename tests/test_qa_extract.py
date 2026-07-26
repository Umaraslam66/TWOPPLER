"""SPEC D4 — Q-A extraction. All fixtures synthetic, no corpus, no network."""

from __future__ import annotations

import pytest

from doppler.qa_extract import (
    MAX_ITEMS,
    extract_qa,
    extract_qa_verbose,
    first_word,
    has_interrogative_cue,
    is_question,
    jaccard,
    qa_candidates,
    truncate_answer,
    word_count,
    word_set,
)

TID = "SYN-1"


def turns(*spec, transcript_id: str = TID) -> list[dict]:
    """(role, text) pairs -> D3-shaped turn records."""
    return [{"transcript_id": transcript_id, "turn_idx": i, "role": role,
             "speaker_label": role.upper(), "resolved_label": None, "text": text}
            for i, (role, text) in enumerate(spec)]


def filler(n: int, word: str = "alpha") -> str:
    return " ".join([word] * n)


def reasons(drops) -> dict:
    from collections import Counter
    return dict(Counter(d["reason"] for d in drops))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def test_first_word_strips_stage_directions_then_takes_the_literal_first_word():
    """SPEC D4 as clarified by v1.7."""
    assert first_word("(LAUGHTER) What did you make of that?") == "what"
    assert first_word("[APPLAUSE] Why now?") == "why"
    assert first_word("(LAUGHTER) (APPLAUSE) Tell me more") == "tell"
    assert first_word("  \"What about it?") == "what"
    assert first_word("...Why now?") == "why"          # punctuation, not a word
    assert first_word("") == ""
    assert first_word("!!! ???") == ""
    assert first_word("(LAUGHTER)") == ""


def test_first_word_never_skips_a_token_to_find_a_cue():
    """The v1.7 fix. Nothing is stepped over to reach a nicer-looking word."""
    assert first_word("1-800-989-8255 is our number. What is interesting") == \
        "1-800-989-8255"
    assert first_word("2016 was a year, no?") == "2016"
    assert first_word("Well, what do you make of it") == "well"


def test_a_phone_number_opening_is_not_a_question():
    """The bank row v1.7 removes: a cue word sat behind a phone number."""
    q = "1-800-989-8255 is our number. What is interesting is that it is sad"
    assert not has_interrogative_cue(q)
    assert not is_question(q)


def test_a_stage_direction_does_not_hide_a_real_cue():
    assert has_interrogative_cue("(LAUGHTER) What did you make of that")
    assert is_question("(LAUGHTER) What did you make of that")


def test_interrogative_cue_is_first_word_only_and_case_insensitive():
    assert has_interrogative_cue("How did that feel to you")
    assert has_interrogative_cue("HOW did that feel to you")
    assert has_interrogative_cue("Tell me about the meeting")
    # "how" is present but not first -- the cue rule is about the opening word.
    assert not has_interrogative_cue("And so how did that feel to you")
    assert not has_interrogative_cue("Well that is quite something")


def test_is_question_accepts_either_route():
    assert is_question("So that was quite a week for you?")      # "?" only
    assert is_question("Describe the room for me")               # cue only
    assert not is_question("So that was quite a week for you")


def test_word_set_normalises_case_and_punctuation():
    assert word_set("Why, Bob?  why BOB") == {"why", "bob"}
    assert word_set("") == set()


def test_jaccard_edges():
    assert jaccard(set(), set()) == 1.0
    assert jaccard({"a"}, {"a"}) == 1.0
    assert jaccard({"a"}, {"b"}) == 0.0
    assert jaccard({"a", "b", "c", "d"}, {"a", "b", "c", "e"}) == pytest.approx(3 / 5)


def test_word_count_is_whitespace_tokens():
    assert word_count("one  two\tthree\nfour") == 4
    assert word_count("") == 0
    assert word_count(None) == 0


# ---------------------------------------------------------------------------
# pairing
# ---------------------------------------------------------------------------

def test_answer_is_the_run_of_consecutive_guest_turns():
    rows = turns(("guest", "hello"),
                 ("host", "What happened next in the negotiation"),
                 ("guest", "first part"), ("guest", "second part"),
                 ("other", "applause"), ("guest", "not part of it"))
    cand = qa_candidates(rows)
    assert len(cand) == 1
    assert cand[0]["answer"] == "first part second part"
    assert cand[0]["n_answer_turns"] == 2


def test_host_turn_not_immediately_followed_by_guest_is_not_a_candidate():
    rows = turns(("guest", "hi"),
                 ("host", "What happened next in the negotiation"),
                 ("other", "a third party speaks"),
                 ("guest", "the subject answers late"))
    assert qa_candidates(rows) == []


def test_turns_are_read_in_turn_idx_order_not_list_order():
    rows = turns(("guest", "hi"),
                 ("host", "What happened next in the negotiation"),
                 ("guest", filler(40)))
    shuffled = [rows[2], rows[0], rows[1]]
    items = extract_qa(shuffled, "C1", TID)
    assert [it["q_turn_idx"] for it in items] == [1]


def test_duplicate_turn_idx_is_an_error():
    rows = turns(("host", "What happened next here"), ("guest", filler(40)))
    rows[1]["turn_idx"] = 0
    with pytest.raises(ValueError, match="duplicate turn_idx"):
        extract_qa(rows, "C1", TID)


def test_turns_from_another_transcript_are_refused():
    """A grounding turn must never be able to answer a test question."""
    rows = turns(("guest", "hi"), ("host", "What happened next here"),
                 ("guest", filler(40)))
    rows[2]["transcript_id"] = "SYN-OTHER"
    with pytest.raises(ValueError, match="SYN-OTHER"):
        extract_qa(rows, "C1", TID)


def test_qa_candidates_refuses_mixed_transcripts_too():
    """The guard is on every path into the pairing logic, not just the named one."""
    rows = turns(("guest", "hi"), ("host", "What happened next here"),
                 ("guest", filler(40)))
    rows[2]["transcript_id"] = "SYN-OTHER"
    with pytest.raises(ValueError, match="multiple transcripts"):
        qa_candidates(rows)


# ---------------------------------------------------------------------------
# D4 filters
# ---------------------------------------------------------------------------

def test_intro_host_turn_is_dropped_when_the_guest_has_not_spoken():
    rows = turns(("host", "Tonight we are joined by a very special guest"),
                 ("guest", filler(40)))
    items, drops = extract_qa_verbose(rows, "C1", TID)
    assert items == []
    assert reasons(drops) == {"intro_host_turn": 1}


def test_first_host_turn_is_kept_when_the_guest_spoke_first():
    rows = turns(("guest", "thanks for having me"),
                 ("host", "Tell me how the whole thing started"),
                 ("guest", filler(40)))
    items, drops = extract_qa_verbose(rows, "C1", TID)
    assert len(items) == 1
    assert drops == []


def test_only_the_first_host_turn_gets_the_intro_exemption():
    """A later host turn is judged on its own merits, never as an intro."""
    rows = turns(("host", "Tonight we are joined by a very special guest"),
                 ("other", "a clip plays"),
                 ("host", "What did you make of that clip"),
                 ("guest", filler(40)))
    items, drops = extract_qa_verbose(rows, "C1", TID)
    assert [it["q_turn_idx"] for it in items] == [2]
    assert drops == []


def test_question_shorter_than_five_words_is_dropped():
    rows = turns(("guest", "hi"), ("host", "What now"), ("guest", filler(40)))
    items, drops = extract_qa_verbose(rows, "C1", TID)
    assert items == []
    assert reasons(drops) == {"question_too_short": 1}


def test_question_of_exactly_five_words_is_kept():
    rows = turns(("guest", "hi"), ("host", "With a much shorter timeline?"),
                 ("guest", filler(40)))
    assert len(extract_qa(rows, "C1", TID)) == 1


def test_statement_without_question_mark_or_cue_is_dropped():
    rows = turns(("guest", "hi"),
                 ("host", "Well, you know, the taxpayers want to give more."),
                 ("guest", filler(40)))
    items, drops = extract_qa_verbose(rows, "C1", TID)
    assert items == []
    assert reasons(drops) == {"not_interrogative": 1}


def test_statement_with_a_question_mark_is_kept():
    rows = turns(("guest", "hi"),
                 ("host", "And you were there the whole time, right?"),
                 ("guest", filler(40)))
    assert len(extract_qa(rows, "C1", TID)) == 1


def test_answer_below_the_thirty_word_floor_is_dropped():
    rows = turns(("guest", "hi"), ("host", "What happened next in the room"),
                 ("guest", filler(29)))
    items, drops = extract_qa_verbose(rows, "C1", TID)
    assert items == []
    assert reasons(drops) == {"answer_too_short": 1}


def test_answer_of_exactly_thirty_words_is_kept():
    rows = turns(("guest", "hi"), ("host", "What happened next in the room"),
                 ("guest", filler(30)))
    items = extract_qa(rows, "C1", TID)
    assert len(items) == 1
    assert items[0]["answer_words"] == 30
    assert items[0]["flags"] == []


def test_answer_of_exactly_four_hundred_words_is_not_truncated():
    rows = turns(("guest", "hi"), ("host", "What happened next in the room"),
                 ("guest", filler(400)))
    items = extract_qa(rows, "C1", TID)
    assert items[0]["answer_words"] == 400
    assert items[0]["flags"] == []


def test_long_answer_is_truncated_at_the_sentence_boundary_nearest_300():
    sentences = [filler(50) + f" end{i}." for i in range(10)]      # 510 words
    rows = turns(("guest", "hi"), ("host", "What happened next in the room"),
                 ("guest", " ".join(sentences)))
    items = extract_qa(rows, "C1", TID)
    assert items[0]["flags"] == ["truncated"]
    # Boundaries land at 51, 102, ... 306 is nearer 300 than 255 or 357.
    assert items[0]["answer_words"] == 306
    assert items[0]["answer"].endswith("end5.")


def test_truncate_answer_falls_back_to_a_hard_cut_with_no_sentence_boundary():
    text = filler(500)
    out, was = truncate_answer(text)
    assert was is True
    assert word_count(out) == 300


def test_truncated_output_is_never_longer_than_the_400_word_bound():
    """A boundary past 400 words must not be honoured.

    900 words, first sentence end at word 500. Cutting there would respect
    "nearest boundary to 300" and still leave a 500-word option towering over
    its three ~100-word distractors, which is the length cue the A4 control
    exists to remove. The hard cut wins.
    """
    text = filler(500) + ". " + filler(400)
    assert word_count(text) == 900
    out, was = truncate_answer(text)
    assert was is True
    assert word_count(out) == 300
    assert word_count(out) <= 400


def test_truncate_answer_leaves_short_text_alone():
    out, was = truncate_answer("a short answer.")
    assert (out, was) == ("a short answer.", False)


# ---------------------------------------------------------------------------
# near-duplicates and the cap
# ---------------------------------------------------------------------------

def test_near_duplicate_question_keeps_the_first_only():
    q = "What did you make of the vote in the assembly?"
    near = "What did you make of that vote in the assembly?"   # Jaccard 9/11 >= .8
    rows = turns(("guest", "hi"), ("host", q), ("guest", filler(40)),
                 ("host", near), ("guest", filler(40)))
    items, drops = extract_qa_verbose(rows, "C1", TID)
    assert [it["q_turn_idx"] for it in items] == [1]
    assert reasons(drops) == {"near_duplicate_question": 1}


def test_similar_but_not_near_duplicate_questions_both_survive():
    rows = turns(("guest", "hi"),
                 ("host", "What did you make of the vote in the assembly?"),
                 ("guest", filler(40)),
                 ("host", "Why does the outcome matter to ordinary voters?"),
                 ("guest", filler(40)))
    items = extract_qa(rows, "C1", TID)
    assert [it["q_turn_idx"] for it in items] == [1, 3]


def test_near_duplicate_is_measured_against_kept_items_not_dropped_ones():
    """A question dropped by an earlier filter cannot suppress a later one."""
    q = "What did you make of the vote in the assembly?"
    rows = turns(("guest", "hi"),
                 ("host", q), ("guest", filler(10)),      # answer too short
                 ("host", q), ("guest", filler(40)))      # must survive
    items, drops = extract_qa_verbose(rows, "C1", TID)
    assert [it["q_turn_idx"] for it in items] == [3]
    assert reasons(drops) == {"answer_too_short": 1}


def test_item_cap_is_twenty_in_turn_order():
    spec = [("guest", "hi")]
    for i in range(MAX_ITEMS + 5):
        spec.append(("host", f"What happened in the year of {i} exactly?"))
        spec.append(("guest", filler(40)))
    items, drops = extract_qa_verbose(turns(*spec), "C1", TID)
    assert len(items) == MAX_ITEMS
    assert [it["q_turn_idx"] for it in items] == list(range(1, 2 * MAX_ITEMS, 2))
    assert reasons(drops) == {"over_item_cap": 5}


# ---------------------------------------------------------------------------
# emitted shape
# ---------------------------------------------------------------------------

def test_item_shape_and_id():
    rows = turns(("guest", "hi"), ("host", "What happened next in the room?"),
                 ("guest", filler(40)), transcript_id="NPR-999")
    item = extract_qa(rows, "C00792", "NPR-999")[0]
    assert item == {
        "item_id": "C00792:NPR-999:1",
        "canonical_id": "C00792",
        "transcript_id": "NPR-999",
        "q_turn_idx": 1,
        "question": "What happened next in the room?",
        "answer": filler(40),
        "answer_words": 40,
        "flags": [],
    }


def test_question_and_answer_are_stripped_of_surrounding_whitespace():
    rows = turns(("guest", "hi"), ("host", "  What happened next in the room? "),
                 ("guest", "  " + filler(40) + "\n"))
    item = extract_qa(rows, "C1", TID)[0]
    assert item["question"] == "What happened next in the room?"
    assert item["answer"] == filler(40)


def test_empty_turn_list_yields_nothing():
    assert extract_qa([], "C1", TID) == []
