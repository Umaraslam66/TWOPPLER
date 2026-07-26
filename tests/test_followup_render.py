"""Follow-up classifier tests: frozen rubric, byte-determinism, strict parser.

Everything here is offline and synthetic. The rubric digest is pinned, so an
accidental edit to the frozen text fails loudly instead of silently changing
what the node classifies.
"""

from __future__ import annotations

import pytest

from doppler import followup_render as F

# Pinned freeze marker for RUBRIC_V1 (SPEC D9). Changing the rubric text is
# allowed only as a deliberate re-freeze: update this digest in the same commit
# and say so in the commit message, because every classification made with the
# old text was made with a different instrument.
FROZEN_RUBRIC_SHA256 = (
    "053b96cba42ebf03d966db3c22fce2acde3a685d5b4cca9badd556ee248a24da"
)


# ---------------------------------------------------------------------------
# The frozen rubric
# ---------------------------------------------------------------------------


def test_rubric_digest_is_frozen():
    assert F.RUBRIC_SHA256 == F.sha256(F.RUBRIC_V1)
    assert F.RUBRIC_SHA256 == FROZEN_RUBRIC_SHA256


def test_rubric_fits_a_short_context():
    """Under 450 words so it is cheap to send on every turn (T5 brief)."""
    assert len(F.RUBRIC_V1.split()) < 450


def test_rubric_is_ascii():
    """The file is rsynced to the node; no smart quotes, no encoding surprises."""
    assert F.RUBRIC_V1.isascii()
    assert F.OUTPUT_INSTRUCTION.isascii()


def test_rubric_has_four_examples_two_per_label():
    assert F.RUBRIC_V1.count("LABEL: FOLLOW-UP") == 2
    assert F.RUBRIC_V1.count("LABEL: NEW-TOPIC") == 2
    assert F.RUBRIC_V1.count("\nWHY: ") == 4
    # 4 examples + the one line that defines the field name.
    assert F.RUBRIC_V1.count("\nPREV: ") == 5


def test_rubric_covers_every_required_decision_rule():
    """Each rule the human audit will be checked against is stated somewhere."""
    text = F.RUBRIC_V1.lower()
    for phrase in (
        "minimal continuers",       # "Go on."
        "acknowledge-then-pivot",   # acknowledgment then pivot
        "challenges",               # pushback on the prior answer
        "own earlier line",         # return to the interviewer's own agenda
        "compound turn",            # acknowledgment + follow-up question
    ):
        assert phrase in text, phrase


def test_every_rubric_example_parses_with_our_own_parser():
    """A human reading the examples and the parser agree on what output means."""
    blocks = F.RUBRIC_V1.split("EXAMPLES", 1)[1].strip().split("\n\n")
    assert len(blocks) == 4
    labels = [F.parse_label(block) for block in blocks]
    assert labels == [F.FOLLOW_UP, F.FOLLOW_UP, F.NEW_TOPIC, F.NEW_TOPIC]


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------


def test_prompt_is_byte_deterministic():
    args = ("Why did you resign?", "Because the audit was buried.", "Buried by whom?")
    first = F.classify_prompt(*args)
    assert first == F.classify_prompt(*args)
    assert F.sha256(first) == F.sha256(F.classify_prompt(*args))


def test_prompt_changes_when_any_field_changes():
    base = F.classify_prompt("a", "b", "c")
    variants = {
        F.sha256(base),
        F.sha256(F.classify_prompt("A", "b", "c")),
        F.sha256(F.classify_prompt("a", "B", "c")),
        F.sha256(F.classify_prompt("a", "b", "C")),
    }
    assert len(variants) == 4


def test_prompt_has_rubric_case_and_output_contract_in_order():
    prompt = F.classify_prompt("prev text", "guest text", "target text")
    assert prompt.startswith(F.RUBRIC_V1)
    assert prompt.endswith(F.OUTPUT_INSTRUCTION)
    assert prompt.index(F.CASE_HEADER) < prompt.index("PREV: prev text")
    assert "\nPREV: prev text\nGUEST: guest text\nTARGET: target text\n" in prompt


def test_whitespace_in_the_transcript_does_not_change_the_prompt():
    """Newlines and double spaces inside a turn collapse, so the layout holds."""
    messy = F.classify_prompt("a  b\nc", "d\n\ne", "  f g  ")
    clean = F.classify_prompt("a b c", "d e", "f g")
    assert messy == clean


def test_empty_field_renders_a_placeholder():
    prompt = F.classify_prompt("", "", "target")
    assert f"PREV: {F.EMPTY_FIELD}" in prompt
    assert f"GUEST: {F.EMPTY_FIELD}" in prompt


# ---------------------------------------------------------------------------
# Truncation boundaries
# ---------------------------------------------------------------------------


def _numbered(n: int) -> str:
    return " ".join(f"w{i}" for i in range(n))


@pytest.mark.parametrize("budget,func", [
    (F.PREV_HOST_WORDS, F.last_words),
    (F.GUEST_ANSWER_WORDS, F.last_words),
    (F.TARGET_HOST_WORDS, F.first_words),
])
def test_at_budget_nothing_is_cut(budget, func):
    text = _numbered(budget)
    assert func(text, budget) == text
    assert F.TRUNCATION_MARK not in func(text, budget)


def test_last_words_keeps_the_tail_one_word_over_budget():
    kept = F.last_words(_numbered(61), 60)
    assert kept.startswith(f"{F.TRUNCATION_MARK} w1 w2")
    assert kept.endswith("w60")
    assert "w0" not in kept.split()
    assert len(kept.split()) == 61  # 60 words + the marker


def test_first_words_keeps_the_head_one_word_over_budget():
    kept = F.first_words(_numbered(121), 120)
    assert kept.startswith("w0 w1")
    assert kept.endswith(f"w119 {F.TRUNCATION_MARK}")
    assert "w120" not in kept.split()
    assert len(kept.split()) == 121


def test_prompt_applies_the_three_d9_budgets():
    """Each field is one line, cut to its own budget: 60 / 120 / 120 words."""
    prompt = F.classify_prompt(_numbered(200), _numbered(200), _numbered(200))
    body = prompt.split(F.CASE_HEADER, 1)[1].split(F.OUTPUT_INSTRUCTION, 1)[0]
    prev, guest, target = [line for line in body.splitlines() if line.strip()]

    assert prev.startswith(f"PREV: {F.TRUNCATION_MARK} w140 ")
    assert guest.startswith(f"GUEST: {F.TRUNCATION_MARK} w80 ")
    assert prev.endswith("w199") and guest.endswith("w199")
    assert target.startswith("TARGET: w0 w1 ")
    assert target.endswith(f"w119 {F.TRUNCATION_MARK}")


def test_truncation_of_the_prev_turn_is_shorter_than_the_guest_answer():
    """PREV gets 60 words, GUEST 120 -- a swap would be silent otherwise."""
    assert F.PREV_HOST_WORDS == 60
    assert F.GUEST_ANSWER_WORDS == 120
    assert F.TARGET_HOST_WORDS == 120


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("completion,expected", [
    ("LABEL: FOLLOW-UP\nWHY: it probes the answer.", F.FOLLOW_UP),
    ("LABEL: NEW-TOPIC\nWHY: it pivots.", F.NEW_TOPIC),
    ("  LABEL: FOLLOW-UP  \nWHY: x.", F.FOLLOW_UP),
    ("\n\nLABEL:FOLLOW-UP\nWHY: x.", F.FOLLOW_UP),
    ("**LABEL:** NEW-TOPIC\nWHY: x.", F.NEW_TOPIC),
    ("LABEL: **FOLLOW-UP**\nWHY: x.", F.FOLLOW_UP),
    ("- LABEL: NEW-TOPIC\n- WHY: x.", F.NEW_TOPIC),
    ("> LABEL: FOLLOW-UP\n> WHY: x.", F.FOLLOW_UP),
    ("label: follow-up\nwhy: x.", F.FOLLOW_UP),
    ("Label: New-Topic.", F.NEW_TOPIC),
    ("Sure, here is my answer.\nLABEL: FOLLOW-UP\nWHY: x.", F.FOLLOW_UP),
    ("LABEL: FOLLOW-UP\r\nWHY: x.", F.FOLLOW_UP),
])
def test_parser_accepts_dressed_up_but_well_formed_labels(completion, expected):
    assert F.parse_label(completion) == expected


@pytest.mark.parametrize("completion", [
    "",
    None,
    "WHY: it probes the answer.",
    "FOLLOW-UP",                              # no LABEL: prefix
    "LABEL: FOLLOWUP",                        # missing hyphen
    "LABEL: FOLLOW UP",                       # space, not hyphen
    "LABEL: NEWTOPIC",
    "LABEL: NEW TOPIC",
    "LABEL: MAYBE",
    "LABEL: UNCLEAR\nWHY: cannot tell.",
    "LABEL: FOLLOW-UP or NEW-TOPIC",          # the instruction echoed back
    "LABEL: <FOLLOW-UP or NEW-TOPIC>",
    "LABEL: FOLLOW-UP because it probes",     # extra words on the label line
    "The label is FOLLOW-UP.",
    "I cannot classify this turn.",
])
def test_parser_rejects_garbage(completion):
    assert F.parse_label(completion) is None


@pytest.mark.parametrize("completion", [
    "LABEL: FOLLOW-UP\nLABEL: NEW-TOPIC\nWHY: x.",   # contradicts itself
    "LABEL: FOLLOW-UP\nWHY: x.\nLABEL: FOLLOW-UP",   # agrees, still ambiguous
    "LABEL: NEW-TOPIC\n\nLABEL: NEW-TOPIC",
])
def test_parser_rejects_double_labels(completion):
    assert F.parse_label(completion) is None


def test_parser_never_invents_a_third_label():
    assert F.parse_label("LABEL: FOLLOW-UP") in F.LABELS


# ---------------------------------------------------------------------------
# Turn selection
# ---------------------------------------------------------------------------


def _turns(*specs) -> list:
    """``("host", "text")`` pairs -> SPEC D3 turn dicts with running turn_idx."""
    return [{"transcript_id": "T1", "turn_idx": i, "role": role,
             "speaker_label": role.upper(), "text": text}
            for i, (role, text) in enumerate(specs)]


ALTERNATING = _turns(
    ("other", "Announcer intro."),
    ("host", "Welcome. Tell us about the audit."),          # 1: first host -> rule
    ("guest", "The audit was buried for three months."),
    ("host", "Buried by whom?"),                            # 3: follow-up case
    ("guest", "By the deputy director, I believe."),
    ("other", "Unrelated soundbite from a third party."),
    ("host", "Let me turn to the budget."),                 # 6: follow-up case
    ("host", "Do you support the new spending bill?"),      # 7: no new answer
)


def test_first_host_turn_is_rule_labelled_new_topic():
    items = F.classifiable_turns(ALTERNATING)
    first = items[0]
    assert first == {"turn_idx": 1, "label": F.NEW_TOPIC, "source": "rule"}
    assert "prev_host" not in first


def test_classifiable_items_carry_the_three_prompt_fields():
    items = F.classifiable_turns(ALTERNATING)
    assert [item["turn_idx"] for item in items] == [1, 3, 6, 7]
    case = items[1]
    assert set(case) == {"turn_idx", "prev_host", "guest_answer", "target_host"}
    assert case["prev_host"] == "Welcome. Tell us about the audit."
    assert case["guest_answer"] == "The audit was buried for three months."
    assert case["target_host"] == "Buried by whom?"


def test_other_speakers_do_not_become_context_or_targets():
    items = F.classifiable_turns(ALTERNATING)
    assert all(item["turn_idx"] not in (0, 2, 4, 5) for item in items)
    rendered = " ".join(item.get("guest_answer", "") + item.get("prev_host", "")
                        for item in items[1:])
    assert "third party" not in rendered
    assert "Announcer" not in rendered


def test_back_to_back_host_turns_share_the_last_guest_answer():
    """Turn 7 has no answer of its own, so it is judged against turn 4's."""
    items = {item["turn_idx"]: item for item in F.classifiable_turns(ALTERNATING)}
    assert items[6]["guest_answer"] == items[7]["guest_answer"]
    assert items[7]["guest_answer"] == "By the deputy director, I believe."
    # prev_host is the turn the guest was answering, not the turn just before.
    assert items[7]["prev_host"] == "Buried by whom?"


def test_consecutive_guest_turns_are_joined_into_one_answer():
    items = F.classifiable_turns(_turns(
        ("host", "Q1"),
        ("guest", "First part."),
        ("guest", "Second part."),
        ("host", "Q2"),
    ))
    assert items[1]["guest_answer"] == "First part. Second part."


def test_an_other_speaker_ends_the_guest_run():
    """D4's rule: an answer stops at the next non-guest turn."""
    items = F.classifiable_turns(_turns(
        ("host", "Q1"),
        ("guest", "Early part."),
        ("other", "Interruption."),
        ("guest", "Later part."),
        ("host", "Q2"),
    ))
    assert items[1]["guest_answer"] == "Later part."


def test_host_turns_before_any_guest_speaks_are_skipped():
    """Only the first one is emitted (by rule); the rest have nothing to follow."""
    items = F.classifiable_turns(_turns(
        ("host", "Welcome."),
        ("host", "Our guest joins us from Chicago."),
        ("other", "Station identification."),
        ("host", "Thanks for coming."),
        ("guest", "Happy to be here."),
        ("host", "Why now?"),
    ))
    assert [item["turn_idx"] for item in items] == [0, 5]
    assert items[0]["source"] == "rule"
    assert items[1]["prev_host"] == "Thanks for coming."


def test_the_rule_wins_when_the_guest_speaks_first():
    """A transcript that opens on the guest still rule-labels host turn one."""
    items = F.classifiable_turns(_turns(
        ("guest", "I never said that."),
        ("host", "You said it on this program last week."),
        ("guest", "That was a different claim."),
        ("host", "Which claim?"),
    ))
    assert items[0] == {"turn_idx": 1, "label": F.NEW_TOPIC, "source": "rule"}
    assert items[1]["turn_idx"] == 3
    assert items[1]["prev_host"] == "You said it on this program last week."


def test_empty_and_whitespace_turns_are_ignored():
    items = F.classifiable_turns(_turns(
        ("host", "Q1"),
        ("guest", "   "),
        ("host", "Q2"),          # no usable answer yet -> skipped
        ("guest", "A real answer."),
        ("host", "Q3"),
    ))
    assert [item["turn_idx"] for item in items] == [0, 4]
    assert items[1]["guest_answer"] == "A real answer."


def test_empty_transcript_and_guest_only_transcript():
    assert F.classifiable_turns([]) == []
    assert F.classifiable_turns(_turns(("guest", "Alone."))) == []


def test_items_feed_classify_prompt_directly():
    """The dict keys are the renderer's argument names -- checked, not assumed."""
    cases = [item for item in F.classifiable_turns(ALTERNATING)
             if "target_host" in item]
    for case in cases:
        fields = {k: v for k, v in case.items() if k != "turn_idx"}
        prompt = F.classify_prompt(**fields)
        assert prompt.startswith(F.RUBRIC_V1)
        assert case["target_host"] in prompt
