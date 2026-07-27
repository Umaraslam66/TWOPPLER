"""Tests for round 4's additions to the B10 instrument (counterfactuals4.py).

Deterministic, offline, no API. Round 3's zero-information arm solved 15 of 15,
and the gate's own completions named three mechanisms: the generated options
read like op-eds, the true position was simply right about the world, and the
paraphrased true answer still carried the host's first name. This file defends
the round-4 answer to each one.

The properties being defended: the generator is shown how the guest actually
talks and is told to hedge; a plausibility verdict is parsed strictly or not at
all; interviewer address is removed from ALL FOUR options or from none of them,
never from some; a question with no evidence on either side is reported as
unclear rather than quietly filed as factual; and round 3 keeps its own digest.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from doppler import counterfactuals as CF  # noqa: E402
from doppler import counterfactuals4 as C4  # noqa: E402

#: A paraphrased true answer, entity-dense enough that the +-2 entity band has
#: room on both sides (a 0-entity answer makes lo_e and hi_e uninformative).
TRUE = ("Egypt and Syria both blamed Bashar al-Assad for the 2011 collapse in "
        "Aleppo and Homs.")

#: Real answers by the same guest, from other interviews. Style only.
EXEMPLARS = [
    "I think it depends a great deal on what you count, honestly.",
    "The evidence is mixed, and I would not want to overstate it.",
]

#: What a MediaSum host label looks like before any cleaning.
HOST_LABELS = ["ROBERT SIEGEL, HOST"]
HOST_FORMS = C4.host_name_forms(HOST_LABELS)


# ---------------------------------------------------------------------------
# The v4 generation prompt
# ---------------------------------------------------------------------------


def test_the_v4_prompt_shows_the_guests_own_answers_as_style_exemplars():
    """The +0.96 item was lost on register, and register cannot be described in
    the abstract -- the generator has to see how this guest actually talks."""
    got = C4.gen_prompt_v4("Why did it fail?", TRUE, "2016-12-14", EXEMPLARS)
    assert "STYLE EXAMPLE 1" in got and "STYLE EXAMPLE 2" in got
    for exemplar in EXEMPLARS:
        assert exemplar in got
    assert "STYLE EXAMPLE 3" not in got


def test_the_v4_prompt_demands_hedged_interview_register_not_advocacy():
    """The scorer picked the option that "reflects the typical speaking style of
    a social science professor". Confident advocacy is the tell, so the rule
    that removes it has to be in the prompt, not just in the exemplars."""
    got = C4.gen_prompt_v4("Why did it fail?", TRUE, "2016-12-14", EXEMPLARS)
    assert "REGISTER" in got
    assert "the evidence is mixed" in got
    assert "op-ed advocacy" in got


def test_the_v4_prompt_requires_positions_someone_could_actually_have_held():
    """B10.5 forces every distractor to conflict with the truth, so when the
    truth is simply right about the world every distractor is wrong about it and
    the test measures general knowledge instead of this person's view."""
    got = C4.gen_prompt_v4("Why did it fail?", TRUE, "2016-12-14", EXEMPLARS)
    assert "PLAUSIBILITY" in got
    assert "factually false, invented, or fringe" in got
    assert "general knowledge" in got


def test_the_v4_prompt_forbids_addressing_the_interviewer():
    """Deixis is stripped after generation, but an option written without a
    vocative in the first place never has to be repaired."""
    got = C4.gen_prompt_v4("Why did it fail?", TRUE, "2016-12-14", EXEMPLARS)
    assert "Never address the interviewer." in got
    assert "vocative" in got


def test_the_v4_prompt_sizes_the_length_window_on_the_answer_it_is_given():
    """Options outside the length ladder are rejected after the API call has
    been paid for, so the window has to be stated to the generator up front."""
    answer = "one two three four five six seven eight nine ten"
    got = C4.gen_prompt_v4("Q?", answer, "2016-12-14", EXEMPLARS)
    assert "about 10 words each (between 8 and 11 words)" in got


def test_the_v4_prompt_states_the_entity_target_as_a_plus_or_minus_two_band():
    """An entity-dense true answer against entity-free alternatives hands the
    scorer "pick the option with the names", which A4.1 matching forbids."""
    ents = CF.entity_tokens(TRUE)
    got = C4.gen_prompt_v4("Q?", TRUE, "2016-12-14", EXEMPLARS)
    assert f"about {ents} specific named things" in got
    assert f"roughly {ents - 2} to {ents + 2}" in got


def test_a_guest_with_no_usable_style_examples_gets_an_explicit_absence():
    """Some guests appear once in the corpus. A missing exemplar block would
    leave a dangling header and an unexplained gap where a rule should be; the
    fallback tells the generator what to match instead."""
    empty = C4.format_exemplars([])
    assert "No style examples were available" in empty
    assert "STYLE EXAMPLE" not in empty
    assert empty == C4.format_exemplars(["", "   "])
    assert empty in C4.gen_prompt_v4("Q?", TRUE, "2016-12-14", [])


def test_style_exemplars_are_whitespace_normalised_like_every_other_text():
    """Transcript text arrives wrapped. Every length and overlap measure in the
    instrument is defined on whitespace tokens, so the prompt uses them too."""
    got = C4.format_exemplars(["a\n  b   c"])
    assert "a b c" in got


def test_the_v4_templates_are_frozen_by_their_own_digest():
    """Round 3's artifacts must stay verifiable against the digest they were
    built with, which is exactly why round 4 does not extend TEMPLATE_SHA256."""
    assert C4.TEMPLATE_SHA256_V4 == hashlib.sha256(
        C4.TEMPLATE_TEXT_V4.encode("utf-8")).hexdigest()
    assert C4.TEMPLATE_SHA256_V4 != CF.TEMPLATE_SHA256
    assert C4.TEMPLATE_SHA256_V3_REUSED == CF.TEMPLATE_SHA256


# ---------------------------------------------------------------------------
# The plausibility check
# ---------------------------------------------------------------------------


def test_the_plausibility_prompt_offers_exactly_the_verdicts_the_parser_takes():
    """A verdict the prompt invites but the parser rejects is a silent loss of
    every reply that uses it."""
    got = C4.plausibility_prompt("Why did it fail?", TRUE, "2016-12-14")
    for verdict in C4.PLAUSIBILITY_VERDICTS:
        assert f"VERDICT: {verdict}" in got
    assert "2016-12-14" in got


def test_a_plausibility_verdict_is_parsed_with_its_reason():
    """The reason is what a reader uses to overrule one rejection instead of
    distrusting the whole check."""
    v, why = C4.parse_plausibility(
        "VERDICT: PLAUSIBLE\nWHY: a minority view, but a serious one.")
    assert v == "PLAUSIBLE"
    assert why == "a minority view, but a serious one."


def test_the_false_and_fringe_verdicts_are_kept_apart():
    """They reject an option for different reasons -- wrong about the world
    versus nobody serious held it -- and the report counts them separately."""
    assert C4.parse_plausibility("VERDICT: FALSE\nWHY: no such vote.")[0] == "FALSE"
    assert C4.parse_plausibility("VERDICT: FRINGE\nWHY: conspiracy.")[0] == "FRINGE"


def test_a_plausibility_verdict_survives_markdown_dressing():
    """The checker is a chat model that decorates its output; losing a
    well-formed verdict to bold markers would be a fake rejection rate."""
    v, _ = C4.parse_plausibility("**VERDICT:** FRINGE\n**WHY:** a crank reading")
    assert v == "FRINGE"


def test_a_verdict_outside_the_plausibility_vocabulary_is_a_parse_failure():
    """Guessing at a verdict would let an unchecked option into the item set
    while the log says it was checked."""
    assert C4.parse_plausibility("VERDICT: MAYBE\nWHY: unsure")[0] is None
    assert C4.parse_plausibility("VERDICT: SAME\nWHY: wrong template")[0] is None


def test_an_unparseable_plausibility_reply_is_never_guessed():
    """Same rule as every other check in B10: no verdict means no verdict."""
    assert C4.parse_plausibility("I think that's defensible.") == (None, None)
    assert C4.parse_plausibility("") == (None, None)
    assert C4.parse_plausibility(None) == (None, None)


# ---------------------------------------------------------------------------
# D6-v4.2 Deixis: host names
# ---------------------------------------------------------------------------


def test_a_host_label_yields_the_full_name_and_each_name_token_longest_first():
    """The label says ROBERT SIEGEL and the transcript says "Robert", so both
    have to be strippable; longest first so the full name goes before its parts
    and a two-word name is never left half-removed."""
    forms = C4.host_name_forms(HOST_LABELS)
    assert forms[0] == "ROBERT SIEGEL"
    assert set(forms) == {"ROBERT SIEGEL", "ROBERT", "SIEGEL"}
    assert [len(f) for f in forms] == sorted((len(f) for f in forms), reverse=True)


def test_short_tokens_survive_in_the_full_name_but_not_as_standalone_forms():
    """A half-removed name is worse than none: it mangles the text AND leaves
    the tell.

    Dropping short tokens everywhere built the "full name" from the survivors
    only, so "AL SHARPTON, HOST" produced just ["SHARPTON"] and "Al Sharpton is
    wrong" stripped to "Al is wrong". Short tokens are still excluded as
    STANDALONE forms, because stripping every "al" out of an option would do
    real damage.
    """
    forms = C4.host_name_forms(["AL SHARPTON, HOST"])
    assert "AL SHARPTON" in forms          # the full name strips cleanly
    assert "SHARPTON" in forms             # the surname alone still strips
    assert "AL" not in forms               # but "al" is never stripped alone

    initials = C4.host_name_forms(["J. K. ROWLING, HOST"])
    assert "J. K. ROWLING" in initials
    assert "ROWLING" in initials
    assert "J." not in initials


def test_stripping_prefers_the_longest_matching_name_form():
    """Forms are applied longest-first so the full name goes before the surname
    and never leaves a stranded first name behind."""
    forms = C4.host_name_forms(["AL SHARPTON, HOST"])
    assert forms == sorted(forms, key=len, reverse=True)
    out, removed = C4.strip_deixis("Al Sharpton is wrong about this.", forms)
    assert "Sharpton" not in out and "Al " not in out
    assert removed


def test_a_label_with_no_usable_name_yields_nothing_to_strip():
    """Corpus labels are not clean. A missing or unusable host label must leave
    the options alone rather than crash the build."""
    assert C4.host_name_forms([]) == []
    assert C4.host_name_forms(None) == []
    assert C4.host_name_forms([""]) == []
    assert C4.host_name_forms(["123, HOST"]) == []


# ---------------------------------------------------------------------------
# D6-v4.2 Deixis: stripping one option
# ---------------------------------------------------------------------------


def test_a_leading_vocative_is_removed_and_the_answer_recapitalised():
    """This is the round-3 failure verbatim: the scorer solved the tightest item
    by noticing the true answer called the host Robert."""
    out, removed = C4.strip_deixis(
        "Robert, regarding the budget, I think it's fine.", HOST_FORMS)
    assert out == "Regarding the budget, I think it's fine."
    assert removed == ["ROBERT"]


def test_a_trailing_vocative_is_removed_too():
    """The name is a tell wherever it sits, and guests put it at the end as
    often as at the front."""
    out, removed = C4.strip_deixis("I think it's fine, Robert.", HOST_FORMS)
    assert "Robert" not in out
    assert removed == ["ROBERT"]


def test_nested_openers_are_peeled_until_the_answer_starts():
    """Real speech stacks the packaging -- "Well, you know, Robert," is one
    tell, not three -- and stopping after the first would leave the rest."""
    out, removed = C4.strip_deixis(
        "Well, you know, Robert, regarding the budget, we don't really know yet.",
        HOST_FORMS)
    assert out == "Regarding the budget, we don't really know yet."
    assert removed == ["ROBERT", "well", "you know"]


def test_second_person_address_inside_the_sentence_is_removed():
    """"As you said" points at the interviewer from the middle of a sentence,
    where the opener rule cannot reach it."""
    out, removed = C4.strip_deixis(
        "The situation, as you said, is worrying now.", HOST_FORMS)
    assert "as you said" not in out.lower()
    assert "worrying" in out
    assert removed and removed[0].lower().startswith("as you said")


def test_a_topical_you_survives_the_strip_intact():
    """Load-bearing. A guest saying "you can't fix this with policing" is
    talking about the world, not to the host; deleting that "you" would damage
    the option's meaning far more than the tell it removes, and a mangled option
    is a new tell of its own."""
    text = "You can't fix this with policing alone, and that is the real problem."
    out, removed = C4.strip_deixis(text, HOST_FORMS)
    assert out == text
    assert removed == []


def test_an_option_with_nothing_to_strip_comes_back_unchanged():
    """Most generated options carry no deixis at all; the rule must be a no-op
    on them so a strip is evidence of a real tell."""
    text = "It depends a great deal on what you count, honestly."
    assert C4.strip_deixis(text, HOST_FORMS) == (text, [])
    assert C4.strip_deixis(text, []) == (text, [])


# ---------------------------------------------------------------------------
# D6-v4.2 Deixis: the all-or-nothing rule
# ---------------------------------------------------------------------------

#: Four options in the register round 4 asks for. Two carry interviewer
#: address; two do not. That asymmetry is the thing under test.
OPTIONS = [
    "Robert, the evidence on this is mixed and I would not want to overstate "
    "it at all.",
    "Well, you know, I think the picture is more complicated than most people "
    "allow here.",
    "It depends a great deal on what you count, and the data are honestly not "
    "settled yet.",
    "To some extent the effect is real, though I would say the size of it is "
    "unclear.",
]


def test_when_every_option_strips_cleanly_the_whole_set_is_stripped():
    """Uniformity is the rule. Stripping only the options that happen to carry a
    vocative would leave exactly the asymmetry the strip exists to remove."""
    texts, record = C4.apply_deixis_rule(OPTIONS, HOST_FORMS)
    assert record["mode"] == "stripped"
    assert not any("Robert" in t for t in texts)
    assert texts[0].startswith("The evidence")
    assert texts[1].startswith("I think the picture")
    # The two options that had nothing to strip are untouched, not rewritten.
    assert texts[2] == OPTIONS[2] and texts[3] == OPTIONS[3]


def test_a_stripped_set_records_what_came_off_each_option():
    """The per-item record is what lets a reader check the strip did not eat an
    answer, without re-running the generation it cannot reproduce."""
    _, record = C4.apply_deixis_rule(OPTIONS, HOST_FORMS)
    assert record["removed_per_option"] == [["ROBERT"], ["well", "you know"],
                                            [], []]
    assert record["n_options_changed"] == 2
    assert record["min_retain_ratio"] == C4.MIN_RETAIN_RATIO


def test_one_option_that_would_lose_its_answer_retains_the_whole_set():
    """THE rule. "Robert, I disagree." is three words, two of which survive, so
    stripping it changes what the option says. Round 4 would rather every option
    keep its packaging than have one option shortened relative to the rest."""
    options = list(OPTIONS)
    options[2] = "Robert, I disagree."
    texts, record = C4.apply_deixis_rule(options, HOST_FORMS)
    assert record["mode"] == "retained"
    assert texts == options
    assert "Robert" in texts[0] and "Robert" in texts[2]


def test_a_retained_set_records_no_removals_and_says_which_option_forced_it():
    """A retained set still carries the round-3 tell, so the artifact has to say
    so out loud -- an unexplained retention reads like a bug."""
    options = list(OPTIONS)
    options[2] = "Robert, I disagree."
    _, record = C4.apply_deixis_rule(options, HOST_FORMS)
    assert record["removed_per_option"] == [[], [], [], []]
    assert record["n_options_changed"] == 0
    assert "[2]" in record["reason"]
    assert "30%" in record["reason"]


def test_the_retain_ratio_is_a_knob_the_caller_can_tighten():
    """The 0.70 default was chosen on round-3 lengths; a future round with
    longer options may need a different one, and the record states which was
    used, so the threshold must actually be honoured."""
    options = list(OPTIONS)
    options[2] = "Robert, I disagree."
    _, loose = C4.apply_deixis_rule(options, HOST_FORMS, min_retain_ratio=0.5)
    assert loose["mode"] == "stripped"
    _, strict = C4.apply_deixis_rule(OPTIONS, HOST_FORMS, min_retain_ratio=0.99)
    assert strict["mode"] == "retained"


# ---------------------------------------------------------------------------
# D6-v4.4 Item-type classification
# ---------------------------------------------------------------------------


def test_a_question_asking_for_the_guests_own_view_is_subjective():
    """The subjective-leaning subset is what round 4 builds first, because
    round 3's widest margins all sat on the other kind."""
    got = C4.classify_question("Do you think the policy worked?")
    assert got["kind"] == "subjective"
    assert "do you think" in got["subjective_cues"]
    assert got["no_cue_fired"] is False


def test_a_question_asking_what_happened_is_a_factual_explanation():
    """These are the items where B10.5 turns every distractor into a wrong claim
    about the world, so they have to be identifiable to be deprioritised."""
    got = C4.classify_question("Walk us through what happened at the plant.")
    assert got["kind"] == "factual_explanation"
    assert set(got["factual_cues"]) == {"walk us through", "what happened"}
    assert got["tie_broken_to_factual"] is False


def test_a_question_with_no_cue_on_either_side_is_unclear_and_not_factual():
    """The real bug. An earlier version broke 0-0 ties toward factual and
    mislabelled nine of round 3's fifteen questions. Zero evidence on both sides
    is the rule admitting it has nothing to say, not a verdict."""
    got = C4.classify_question("Where does the pipeline end?")
    assert got["kind"] == "unclear"
    assert got["score_subjective"] == 0 and got["score_factual"] == 0
    assert got["no_cue_fired"] is True
    assert got["tie_broken_to_factual"] is False


def test_an_evaluative_frame_is_subjective_even_without_the_word_you():
    """"Is there an opportunity to change course in Syria?" asks for an
    assessment. Nothing in it names the guest's view, and the earlier rule sent
    every question like it to the factual pile."""
    got = C4.classify_question(
        "Is there an opportunity to change course in Syria?")
    assert got["kind"] == "subjective"
    assert got["evaluative_cues"] == ["is there an opportunity"]
    assert got["subjective_cues"] == []


def test_a_prediction_modal_alone_is_enough_to_tip_a_question_subjective():
    """A question about what might happen cannot be answered from the record, so
    the answer to it is a judgement whatever else is in the sentence."""
    got = C4.classify_question("Could the talks collapse before the spring?")
    assert got["kind"] == "subjective"
    assert got["subjective_modals"] == ["could"]
    assert got["no_cue_fired"] is False


def test_a_tie_with_cues_on_both_sides_resolves_to_factual_explanation():
    """Different from a 0-0 tie on purpose: calling an item subjective is what
    buys it a place in the build, so a genuinely mixed question does not get in
    on a coin flip."""
    got = C4.classify_question("In your view, what happened?")
    assert got["kind"] == "factual_explanation"
    assert got["score_subjective"] == got["score_factual"] == 1
    assert got["tie_broken_to_factual"] is True
    assert got["no_cue_fired"] is False


def test_every_matched_cue_is_recorded_so_a_single_call_can_be_overruled():
    """15 questions do not justify an unauditable judgement. A reader who
    disagrees with one classification should be able to see the exact phrase it
    turned on rather than distrust the whole split."""
    got = C4.classify_question("What is the evidence on this?")
    assert set(got["factual_cues"]) == {"what is the", "the evidence"}
    assert got["score_factual"] == len(got["factual_cues"])
    assert got["score_subjective"] == 0


def test_an_empty_question_is_unclear_rather_than_an_error():
    """The classifier runs over whatever the extractor produced, and one blank
    field must not stop a build."""
    for question in ("", None, "   "):
        got = C4.classify_question(question)
        assert got["kind"] == "unclear"
        assert got["no_cue_fired"] is True


# ---------------------------------------------------------------------------
# Guards against the style exemplars leaking into the options
# ---------------------------------------------------------------------------


def test_an_option_that_restates_a_style_exemplar_is_caught():
    """The exemplars are real speech by the subject. A model shown three real
    answers can reach for their content as well as their rhythm, and an option
    that does is a real answer sitting in a generated slot."""
    assert C4.copies_any(EXEMPLARS[0], EXEMPLARS)
    assert not C4.copies_any("The opposite is obviously the case here.",
                             EXEMPLARS)


def test_an_option_sharing_a_long_run_with_an_exemplar_is_caught():
    """Same frozen shingle test the D8 answer-leak guard uses: a reproduced run
    is the D6-v3.7 grounding-quote failure arriving by a new route."""
    shared = " ".join(f"w{i}" for i in range(12))
    assert C4.quotes_any(shared, ["I said this once: " + shared])
    assert C4.quotes_any("nothing in common at all", ["prefix " + shared]) is None


def test_the_exemplar_guards_tolerate_a_guest_with_no_exemplars():
    """Guests who appear once in the corpus have none, and the guard must
    return "no leak" rather than fail the item."""
    assert C4.quotes_any("some text", []) is None
    assert C4.quotes_any("some text", ["", None]) is None
    assert not C4.copies_any("some text", [])
    assert not C4.copies_any("some text", ["", None])


# ---------------------------------------------------------------------------
# Punctuation repair after a mid-sentence removal
# ---------------------------------------------------------------------------


def test_a_trailing_vocative_does_not_leave_dangling_punctuation():
    """A stray " , ." in one option and not the others is a NEW formatting tell.

    Removing a vocative that is not at the front strands its commas, and the
    result goes straight into an option the scorer reads. The retain-ratio
    guard cannot catch it either, because the word count barely moves -- which
    is exactly why it has to be repaired here.
    """
    out, removed = C4.strip_deixis("I think it's fine, Robert.", ["ROBERT"])
    assert removed
    assert out == "I think it's fine."
    assert " ," not in out and ", ." not in out


def test_a_mid_sentence_address_does_not_leave_a_doubled_comma():
    out, removed = C4.strip_deixis(
        "The situation, as you said, is worrying now.", [])
    assert removed
    assert ", ," not in out and " ," not in out
    assert out.endswith("worrying now.")


def test_no_stripped_option_ends_with_orphaned_punctuation():
    """Across a spread of shapes, never leave punctuation the generator would
    not have produced."""
    cases = [
        "Well, Robert, the answer is complicated.",
        "The answer is complicated, Robert.",
        "You know, Robert, as you said, it is complicated.",
        "It is complicated, Robert, and it always was.",
    ]
    for text in cases:
        out, _ = C4.strip_deixis(text, ["ROBERT"])
        assert "Robert" not in out, text
        assert " ," not in out and ", ." not in out and ",," not in out, text
        assert not out.startswith(","), text


def test_the_retained_mode_records_what_it_would_have_removed():
    """A reader auditing the decision should not have to re-run the stripper."""
    texts = ["Well, Robert, you know.",
             "A perfectly ordinary alternative answer that survives stripping.",
             "Another ordinary alternative answer that survives stripping too.",
             "A third ordinary alternative answer that also survives it fine."]
    out, record = C4.apply_deixis_rule(texts, ["ROBERT"])
    assert record["mode"] == "retained"
    assert out == texts
    assert record["forced_by_option_index"] == [0]
    assert any(record["would_have_removed_per_option"])
    assert record["would_have_produced"][0] != texts[0]


def test_a_none_exemplar_never_reaches_the_prompt_as_the_word_none():
    """str(None) is the literal "None", which would have put
    `STYLE EXAMPLE 1: None` in front of the generator."""
    assert "None" not in C4.format_exemplars([None, None])
    block = C4.format_exemplars([None, "A real answer with hedging in it."])
    assert "None" not in block
    assert "STYLE EXAMPLE 1" in block and "STYLE EXAMPLE 2" not in block


def test_an_overlapping_cue_is_counted_once():
    """"do you think" contains "you think"; one phrase must not score twice,
    because the subjective/factual comparison is a raw count."""
    got = C4.classify_question("Do you think the council acted correctly?")
    assert got["subjective_cues"] == ["do you think"]
    assert got["score_subjective"] == 1
