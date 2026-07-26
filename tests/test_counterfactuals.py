"""Tests for Amendment 2 B10's generated counterfactuals (counterfactuals.py).

Deterministic, offline, no API. Everything here is the part of B10 that must be
auditable without replaying a non-reproducible API run: the prompt builders, the
strict parsers, and every deterministic guard.

The properties being defended: a generated option must never smuggle in a later
era, never name the subject, never quote the twin's own context, and never be a
restatement of the true answer; and a truncated model reply must be recognised
as truncated rather than scored as an answer.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from doppler import counterfactuals as CF  # noqa: E402
from doppler import stage2_render as R  # noqa: E402

TRUE = ("I think anyone who considers himself a Syrian nationalist would find "
        "it very difficult to sign up with that group.")


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def test_the_generation_prompt_carries_question_answer_era_and_targets():
    got = CF.gen_prompt("Why did it fail?", TRUE, "2016-12-14")
    assert "Why did it fail?" in got
    assert TRUE in got
    assert "2016-12-14" in got
    assert "<<<1>>>" in got and "<<<4>>>" in got
    assert "GENUINELY CONFLICTS" in got


def test_the_generation_prompt_sizes_length_on_the_answer_it_is_given():
    short = CF.gen_prompt("Q?", "one two three four five six seven eight",
                          "2016-12-14")
    assert "about 8 words" in short


def test_the_generation_prompt_states_an_entity_target():
    # The trial failure this exists for: an entity-dense true answer against
    # three entity-free alternatives is the tell "pick the one with the names".
    dense = "Egypt and Syria both blamed Bashar al-Assad for the 2011 collapse."
    got = CF.gen_prompt("Q?", dense, "2016-12-14")
    assert "SPECIFICITY" in got
    assert f"about {CF.entity_tokens(dense)} specific named things" in got


def test_entity_tokens_counts_names_and_numbers():
    assert CF.entity_tokens("nothing here at all today") == 0
    # D5 counts mid-sentence capitalised spans and 2+ digit numbers. A
    # SENTENCE-INITIAL single capital is excluded by design (the capital says
    # "new sentence", not "name"), which is why "Bashar" does not count here
    # and only "Syria" does. That limitation is already on record as the NER
    # bar-lock item; this test pins the behaviour rather than the wish.
    assert CF.entity_tokens("Bashar al-Assad ruled Syria") == 1
    assert CF.entity_tokens("It cost 1500 dollars in Egypt") == 2


def test_the_paraphrase_prompt_is_identical_whatever_the_text_is():
    # One-factor style neutralisation: the paraphraser must not be able to tell
    # a real answer from a generated one, so only {text} may differ.
    a = CF.para_prompt("first text")
    b = CF.para_prompt("second text")
    assert a.replace("first text", "X") == b.replace("second text", "X")


def test_the_check_prompts_name_their_allowed_verdicts():
    assert "VERDICT: SAME" in CF.position_prompt("a", "b")
    assert "VERDICT: CONFLICT" in CF.contra_prompt("q", "a", "b")
    assert "VERDICT: UNRELATED" in CF.contra_prompt("q", "a", "b")


def test_the_templates_are_frozen_by_digest():
    # Re-freeze deliberately if this fails: the templates ARE the procedure
    # B10.9 freezes, and an unnoticed edit changes what was generated.
    assert CF.TEMPLATE_SHA256 == (
        "adb6fd3b42a5c67ce32cae7a7f20c48756dca8b92e36b2c6cdaf6a873b299e19")


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def test_generated_blocks_are_parsed_in_order():
    got = CF.parse_generated("<<<1>>>\nfirst\n<<<2>>>\nsecond\n<<<3>>>\nthird")
    assert got == ["first", "second", "third"]


def test_prose_before_the_first_block_is_ignored():
    got = CF.parse_generated("Here you go:\n<<<1>>>\nfirst\n<<<2>>>\nsecond")
    assert got == ["first", "second"]


def test_a_reply_with_no_blocks_parses_to_nothing():
    assert CF.parse_generated("I cannot help with that.") == []
    assert CF.parse_generated("") == []
    assert CF.parse_generated(None) == []


def test_a_repeated_block_number_keeps_the_first():
    got = CF.parse_generated("<<<1>>>\nfirst\n<<<1>>>\nagain\n<<<2>>>\nsecond")
    assert got == ["first", "second"]


def test_generated_blocks_are_whitespace_normalised():
    assert CF.parse_generated("<<<1>>>\n  a\n  b  \n") == ["a b"]


def test_a_verdict_line_is_parsed_with_its_reason():
    v, why = CF.parse_verdict("VERDICT: CONFLICT\nWHY: they disagree.",
                              ("CONFLICT", "AGREE", "UNRELATED"))
    assert v == "CONFLICT"
    assert why == "they disagree."


def test_a_verdict_survives_markdown_dressing():
    v, _ = CF.parse_verdict("**VERDICT:** SAME\n**WHY:** same claims",
                            ("SAME", "CHANGED"))
    assert v == "SAME"


def test_a_verdict_outside_the_allowed_set_is_a_parse_failure():
    v, _ = CF.parse_verdict("VERDICT: MAYBE\nWHY: unsure", ("SAME", "CHANGED"))
    assert v is None


def test_an_unparseable_check_reply_is_never_guessed():
    assert CF.parse_verdict("I think they conflict.", ("CONFLICT",)) == (None, None)


def test_a_paraphrase_reply_is_stripped_of_labels_and_quotes():
    assert CF.parse_paraphrase('ANSWER: "I disagree."') == "I disagree."
    assert CF.parse_paraphrase("  spread   out  ") == "spread out"


# ---------------------------------------------------------------------------
# Deterministic guards
# ---------------------------------------------------------------------------


def test_a_year_after_the_test_date_is_an_era_violation():
    assert CF.era_violations("Everything changed in 2019.", "2016-12-14") == ["2019"]


def test_a_year_before_or_during_the_test_year_is_fine():
    assert CF.era_violations("Back in 2011 and again in 2016.", "2016-12-14") == []


def test_a_non_year_number_is_not_an_era_reference():
    assert CF.era_violations("We had 1500 people and 12 buses.", "2016-12-14") == []


def test_an_unusable_test_date_disables_the_era_guard_rather_than_crashing():
    assert CF.era_violations("in 2019", None) == []
    assert CF.era_violations("in 2019", "") == []


def test_an_option_that_restates_the_true_answer_is_a_copy():
    assert CF.copies_true(TRUE, TRUE)
    assert not CF.copies_true("The opposite is obviously the case here.", TRUE)


def test_an_option_quoting_the_grounding_is_caught():
    shared = " ".join(f"w{i}" for i in range(12))
    grounding = "HOST: q\nGUEST: " + shared
    assert CF.quotes_grounding(shared, [grounding])
    assert CF.quotes_grounding("nothing in common at all", [grounding]) is None


def test_the_grounding_guard_tolerates_an_empty_block():
    assert CF.quotes_grounding("some text", ["", None]) is None


def test_an_option_naming_the_subject_is_caught():
    assert CF.names_subject("Well, Kroenig disagrees.", ["Matthew Kroenig"])
    assert CF.names_subject("Nobody in particular.", ["Matthew Kroenig"]) == []


def test_a_reply_that_stops_mid_sentence_is_truncated():
    assert CF.looks_truncated("I think the answer is clearly som")
    assert CF.looks_truncated("")
    assert CF.looks_truncated(None)
    assert not CF.looks_truncated("I think the answer is clear.")
    assert not CF.looks_truncated('He said "yes."')


# ---------------------------------------------------------------------------
# Option-set matching
# ---------------------------------------------------------------------------


def _words(n, tag="w"):
    return " ".join(f"{tag}{i}" for i in range(n))


def test_a_well_matched_set_sits_at_rung_zero():
    true = _words(40)
    assert CF.match_rung(true, [_words(40, "a"), _words(38, "b"),
                                _words(42, "c")]) == 0


def test_a_length_mismatch_pushes_the_set_up_the_ladder():
    true = _words(40)
    # 52 words is outside +-20% (32..48) but inside +-30% (28..52).
    assert CF.match_rung(true, [_words(52, "a"), _words(40, "b"),
                                _words(40, "c")]) == 1


def test_a_set_nothing_can_match_returns_none():
    assert CF.match_rung(_words(40), [_words(400, "a")]) is None


def test_the_shuffle_seed_is_the_frozen_d6_one():
    from doppler.distractors import shuffle_seed as d6_seed
    assert CF.shuffle_seed("C1:T:3") == d6_seed("C1:T:3")


def test_the_renderer_reads_a_generated_option_set_unchanged():
    # The generated options must flow through the FROZEN D8 renderer with no
    # special-casing, or round 3 is not comparable with rounds 1 and 2.
    got = R.render_prompt("zeroinfo_redacted", "Why?",
                          ["first", "second", "third", "fourth"])
    assert "A. first" in got and "D. fourth" in got
