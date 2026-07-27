"""Tests for the Stage 2 OPEN-ENDED prompt renderer (OE-1).

All fixtures are synthetic. No network, no data files, no API, nothing random.

What these defend, in the order the pilot spec puts them:
  * the instruction tail is ONE frozen string and is byte-identical in all five
    arms — the whole open-ended instrument rests on that;
  * no option line, no choice line and no distribution instruction survives
    anywhere in an open-ended prompt;
  * the 2,000-word grounding budget still binds;
  * a zero-information prompt carries no excerpts, no program and no date;
  * every subject name variant is still replaced by GUEST, and a named arm is
    still its redacted counterpart plus exactly one name line;
  * S1 affiliation redaction is the scope that was priced, not a new one.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from doppler import oe_render as OE
from doppler import stage2_render as R

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SEGMENTS = [
    {
        "date": "2011-03-02",
        "program": "MORNING EDITION",
        "exchanges": [
            {"host_text": "You left the ministry in 2009. Why then?",
             "guest_text": "Because the audit was buried."},
            {"host_text": "And nobody backed you?",
             "guest_text": "Two colleagues did, quietly."},
        ],
    },
    {
        "date": "2013-04-29",
        "program": "ALL THINGS CONSIDERED",
        "exchanges": [
            {"host_text": "What would you tell a young official?",
             "guest_text": "Keep your own copy of everything."},
        ],
    },
]

QUESTION = "So what did you learn from all of that?"
NAME = "Jane Smith"
VARIANTS = ["Jane Smith"]
OPTIONS = ["First reply text.", "Second reply text.", "Third reply text.",
           "Fourth reply text."]


def _grounding(budget=OE.GROUNDING_BUDGET_WORDS):
    return R.render_grounding(SEGMENTS, budget_words=budget)


def _render(arm, **kw):
    grounded = arm in OE.GROUNDED_ARMS
    named = arm in OE.NAMED_ARMS
    return OE.render_open_prompt(
        arm, kw.pop("question", QUESTION),
        grounding_block=_grounding() if grounded else None,
        name=NAME if named else None, **kw)


def _all_five():
    return {arm: _render(arm) for arm in OE.ARMS}


# ---------------------------------------------------------------------------
# The frozen tail
# ---------------------------------------------------------------------------


def test_instruction_text_is_the_spec_string_verbatim():
    """PILOT_SPEC section 2, word for word. Re-freeze on purpose or not at all."""
    assert OE.OPEN_ANSWER_INSTRUCTION == (
        "Now answer the interviewer's next question as this person would, "
        "speaking in their voice, in the first person. Give one spoken reply "
        "of at most 150 words. No lists, no stage directions, no commentary "
        "about this task."
    )


def test_instruction_and_template_digests_are_frozen():
    assert OE.INSTRUCTION_SHA256 == (
        "d8758204009e71b482d36fb7133641f3077b7414df87e5a055f3949cb2ef3d3b")
    assert OE.TEMPLATE_SHA256 == (
        "4c4f9e0bdca11ce79ec669a0719d7a71894d587f4e61b54ddda4848f7bb1b785")
    assert OE.INSTRUCTION_SHA256 == R.sha256(OE.OPEN_ANSWER_INSTRUCTION)
    assert OE.TEMPLATE_SHA256 == R.sha256(OE.TEMPLATE_TEXT)


def test_instruction_is_a_single_line_with_no_stray_whitespace():
    text = OE.OPEN_ANSWER_INSTRUCTION
    assert "\n" not in text
    assert text == text.strip()
    assert "  " not in text


def test_the_tail_is_byte_identical_across_all_five_arms():
    tails = {arm: OE.tail_of(p) for arm, p in _all_five().items()}
    assert set(tails.values()) == {OE.OPEN_ANSWER_INSTRUCTION}
    assert len({R.sha256(t) for t in tails.values()}) == 1


def test_every_arm_ends_with_the_instruction_block():
    for arm, prompt in _all_five().items():
        assert OE.has_instruction_tail(prompt), arm
        assert prompt.endswith(OE.OPEN_ANSWER_INSTRUCTION)


def test_the_instruction_appears_exactly_once():
    for arm, prompt in _all_five().items():
        assert prompt.count(OE.OPEN_ANSWER_INSTRUCTION) == 1, arm


def test_generation_caps_match_the_spec():
    assert OE.MAX_ANSWER_WORDS == 150
    assert OE.MAX_OUTPUT_TOKENS == 256
    assert OE.TEMPERATURE == 0.0
    assert "at most 150 words" in OE.OPEN_ANSWER_INSTRUCTION


# ---------------------------------------------------------------------------
# No forced-choice material survives
# ---------------------------------------------------------------------------


def test_no_options_and_no_distribution_line_in_any_arm():
    for arm, prompt in _all_five().items():
        assert OE.forced_choice_residue(prompt) == [], arm
        assert "Which of these replies did" not in prompt
        assert "Give a probability for each option" not in prompt
        for label in "ABCD":
            assert f"\n{label}. " not in prompt.rsplit("\n\n", 1)[-1]


def test_assert_open_ended_rejects_a_forced_choice_prompt():
    forced = R.render_prompt("zeroinfo_redacted", QUESTION, OPTIONS)
    with pytest.raises(ValueError):
        OE.assert_open_ended(forced)


def test_assert_open_ended_rejects_a_prompt_with_a_trailing_block():
    prompt = _render("zeroinfo_redacted") + "\n\nPick one of A, B, C or D."
    with pytest.raises(ValueError, match="frozen instruction"):
        OE.assert_open_ended(prompt)


def test_open_ended_prompt_is_shorter_than_its_forced_choice_twin():
    """Same item, same arm: dropping four options must remove text, not add it."""
    open_ended = _render("zeroinfo_redacted")
    forced = R.render_prompt("zeroinfo_redacted", QUESTION, OPTIONS)
    assert R.word_count(open_ended) < R.word_count(forced) + 40


# ---------------------------------------------------------------------------
# Grounding budget
# ---------------------------------------------------------------------------


def test_grounding_speech_words_matches_the_budget_accounting():
    block = _grounding()
    expected = sum(R.word_count(e["host_text"]) + R.word_count(e["guest_text"])
                   for seg in SEGMENTS for e in seg["exchanges"])
    assert OE.grounding_speech_words(block) == expected


def test_grounding_headers_do_not_count_against_the_budget():
    block = _grounding()
    assert "[Interview," in block
    assert OE.grounding_speech_words(block) < R.word_count(block)


def test_a_small_budget_drops_exchanges_and_stays_under_it():
    block = R.render_grounding(SEGMENTS, budget_words=12)
    assert OE.grounding_speech_words(block) <= 12
    assert OE.grounding_speech_words(block) < OE.grounding_speech_words(
        _grounding())


def test_rendered_twin_prompt_respects_the_two_thousand_word_budget():
    prompt = _render("twin_redacted")
    excerpts = OE.excerpt_block_of(prompt)
    assert OE.grounding_speech_words(excerpts) <= OE.GROUNDING_BUDGET_WORDS
    assert OE.GROUNDING_BUDGET_WORDS == R.GROUNDING_BUDGET_WORDS == 2000


def test_excerpt_block_of_returns_nothing_for_a_zero_information_prompt():
    assert OE.excerpt_block_of(_render("zeroinfo_named")) == ""
    assert OE.grounding_speech_words("") == 0


# ---------------------------------------------------------------------------
# Zero-information emptiness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("arm", ["zeroinfo_redacted", "zeroinfo_named"])
def test_zero_information_arms_carry_no_excerpts_program_or_date(arm):
    prompt = _render(arm)
    assert not OE.carries_excerpts(prompt)
    assert R.EXCERPTS_HEADER not in prompt
    assert "[Interview," not in prompt
    assert "MORNING EDITION" not in prompt
    assert "2011-03-02" not in prompt


@pytest.mark.parametrize("arm", ["zeroinfo_redacted", "zeroinfo_named"])
def test_a_grounding_block_handed_to_a_zero_information_arm_raises(arm):
    with pytest.raises(ValueError, match="zero-information arm"):
        OE.render_open_prompt(arm, QUESTION, grounding_block=_grounding(),
                              name=NAME if arm in OE.NAMED_ARMS else None)


@pytest.mark.parametrize("arm", ["twin_redacted", "twin_named",
                                 "imposter_redacted"])
def test_a_grounded_arm_without_excerpts_raises(arm):
    with pytest.raises(ValueError, match="needs a grounding block"):
        OE.render_open_prompt(arm, QUESTION,
                              name=NAME if arm in OE.NAMED_ARMS else None)


def test_zero_information_prompt_is_only_preamble_question_and_tail():
    blocks = _render("zeroinfo_redacted").split("\n\n")
    assert len(blocks) == 3
    assert blocks[0] == R.ZEROINFO_PREAMBLE
    assert blocks[1].startswith(f"{R.HOST_LABEL}: ")
    assert blocks[2] == OE.OPEN_ANSWER_INSTRUCTION


# ---------------------------------------------------------------------------
# GUEST replacement and the one-factor invariant
# ---------------------------------------------------------------------------


def test_the_subject_name_is_replaced_by_guest_everywhere():
    raw_q = "Jane Smith, do you regret the audit, Ms. Smith?"
    block = R.redact(
        R.render_grounding(
            [{"date": "2012-01-01", "program": "WEEKEND EDITION",
              "exchanges": [{"host_text": "Jane Smith joins us.",
                             "guest_text": "Smith here, thanks."}]}],
            budget_words=OE.GROUNDING_BUDGET_WORDS),
        VARIANTS)
    prompt = OE.render_open_prompt(
        "twin_redacted", R.redact(raw_q, VARIANTS), grounding_block=block)
    assert "Jane" not in prompt
    assert "Smith" not in prompt
    assert R.PLACEHOLDER in prompt
    R.assert_redacted(prompt, VARIANTS)


def test_a_name_handed_to_a_redacted_arm_raises():
    with pytest.raises(ValueError, match="redacted arm"):
        OE.render_open_prompt("twin_redacted", QUESTION,
                              grounding_block=_grounding(), name=NAME)


def test_a_named_arm_without_a_name_raises():
    with pytest.raises(ValueError, match="needs the subject's name"):
        OE.render_open_prompt("twin_named", QUESTION,
                              grounding_block=_grounding())


@pytest.mark.parametrize("named,redacted,line", [
    ("twin_named", "twin_redacted", R.TWIN_NAME_LINE),
    ("zeroinfo_named", "zeroinfo_redacted", R.ZEROINFO_NAME_LINE),
])
def test_a_named_arm_is_its_redacted_twin_plus_exactly_one_name_line(
        named, redacted, line):
    got = _render(named)
    base = _render(redacted)
    assert got.replace(line.format(name=NAME) + "\n\n", "", 1) == base


def test_twin_and_imposter_share_one_template_byte_for_byte():
    """Only the provenance of the excerpts differs; the prompt never says so."""
    block = _grounding()
    twin = OE.render_open_prompt("twin_redacted", QUESTION,
                                 grounding_block=block)
    imposter = OE.render_open_prompt("imposter_redacted", QUESTION,
                                     grounding_block=block)
    assert twin == imposter


def test_an_unknown_arm_raises():
    with pytest.raises(ValueError, match="arm must be one of"):
        OE.render_open_prompt("twin_open", QUESTION,
                              grounding_block=_grounding())


def test_an_empty_question_raises():
    with pytest.raises(ValueError, match="question is empty"):
        OE.render_open_prompt("zeroinfo_redacted", "   ")


# ---------------------------------------------------------------------------
# Preambles and headers are the frozen v1.10 strings, reused not restated
# ---------------------------------------------------------------------------


def test_preambles_are_the_forced_choice_ones_unchanged():
    assert _render("twin_redacted").startswith(R.TWIN_PREAMBLE)
    assert _render("zeroinfo_redacted").startswith(R.ZEROINFO_PREAMBLE)


def test_arm_names_and_groupings_come_from_the_frozen_renderer():
    assert OE.ARMS == R.ARMS
    assert OE.GROUNDED_ARMS == R.GROUNDED_ARMS
    assert OE.NAMED_ARMS == R.NAMED_ARMS
    assert OE.PLACEHOLDER == R.PLACEHOLDER == "GUEST"


# ---------------------------------------------------------------------------
# S1 affiliation redaction
# ---------------------------------------------------------------------------


def _barlock():
    path = ROOT / "experiments/barlock_affiliation.py"
    spec = importlib.util.spec_from_file_location("barlock_affiliation_ut", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["barlock_affiliation_ut"] = module
    spec.loader.exec_module(module)
    return module


def test_inlined_s1_matches_the_origin_module():
    """No drift from experiments/barlock_affiliation, which priced this scope."""
    origin = _barlock()
    assert OE.ROLE_WORDS == origin.ROLE_WORDS
    assert OE._APPOS_RE.pattern == origin._APPOS_RE.pattern
    sample = "GUEST, as a former State Department official, can you reflect?"
    assert OE.apply_s1(sample) == origin.apply_s1(sample)


def test_s1_removes_the_host_intro_clause():
    line = "HOST: GUEST, as a former State Department official, can you reflect?"
    out, n = OE.apply_s1_scope(line)
    assert n == 1
    assert OE.S1_PLACEHOLDER in out
    assert "State Department official" not in out


def test_s1_leaves_a_clause_without_a_role_word_alone():
    line = "HOST: GUEST, who was in Aleppo last week, what did you see?"
    out, n = OE.apply_s1_scope(line)
    assert (out, n) == (line, 0)


def test_s1_only_touches_speech_lines():
    prompt = "\n".join([
        R.TWIN_PREAMBLE,
        "",
        "GUEST is a professor of history.",          # the NAME line's shape
        "",
        "HOST: GUEST is a professor of history. Welcome.",
    ])
    out, n = OE.apply_s1_scope(prompt)
    assert n == 1
    assert out.splitlines()[2] == "GUEST is a professor of history."
    assert OE.S1_PLACEHOLDER in out.splitlines()[4]


def test_s1_is_on_by_default_and_can_be_turned_off():
    question = "GUEST, a senior fellow at the institute, what now?"
    on = OE.render_open_prompt("zeroinfo_redacted", question)
    off = OE.render_open_prompt("zeroinfo_redacted", question, s1=False)
    assert OE.S1_PLACEHOLDER in on
    assert OE.S1_PLACEHOLDER not in off
    assert "senior fellow at the institute" in off


def test_s1_does_not_disturb_the_instruction_tail():
    question = "GUEST, a former ambassador, was that a mistake?"
    prompt = OE.render_open_prompt("zeroinfo_redacted", question)
    assert OE.has_instruction_tail(prompt)
    assert OE.tail_of(prompt) == OE.OPEN_ANSWER_INSTRUCTION
