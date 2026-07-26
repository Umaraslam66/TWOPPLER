"""Tests for the round-2 DIAGNOSTIC prompt shapes (src/doppler/diagnostics_v2.py).

Deterministic, offline. The point of these tests is that a diagnostic stays a
diagnostic: it must not become a sixth arm, it must not edit the frozen D8
templates, and its reply must be readable by the same frozen parser as every
arm -- otherwise its numbers cannot be compared with the gate's.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from doppler import diagnostics_v2 as DG  # noqa: E402
from doppler import stage2_render as R  # noqa: E402

OPTIONS = ["First reply here about the vote.",
           "Second reply here about the harvest.",
           "Third reply here about the ledger.",
           "Fourth reply here about the treaty."]
QUESTION = "Why did the vote fail so badly in the end?"


def test_the_question_blind_prompt_contains_no_question_and_no_host_line():
    got = DG.render_question_blind(OPTIONS)
    assert "HOST:" not in got
    assert QUESTION not in got
    DG.assert_question_blind(got, QUESTION)


def test_the_question_blind_prompt_carries_no_excerpts():
    got = DG.render_question_blind(OPTIONS)
    assert R.EXCERPTS_HEADER not in got
    assert "[Interview," not in got


def test_every_option_survives_into_the_question_blind_prompt():
    got = DG.render_question_blind(OPTIONS)
    for label, option in zip("ABCD", OPTIONS):
        assert f"{label}. {option}" in got


def test_the_question_blind_prompt_ends_on_the_frozen_answer_format():
    got = DG.render_question_blind(OPTIONS)
    assert got.endswith(R.distribution_instruction(4))


def test_the_frozen_parser_reads_a_question_blind_reply_unchanged():
    # If this drifts, the diagnostic's numbers stop being comparable with the
    # gate's, which is the whole reason the instruction is reused verbatim.
    assert R.parse_distribution("A: 0.1 B: 0.7 C: 0.1 D: 0.1", 4) == \
        pytest.approx([0.1, 0.7, 0.1, 0.1])


def test_the_guard_catches_a_question_that_leaked_back_in():
    bad = DG.render_question_blind(OPTIONS) + "\n\n" + QUESTION
    with pytest.raises(ValueError, match="still contains the question"):
        DG.assert_question_blind(bad, QUESTION)


def test_the_guard_catches_a_host_line():
    bad = f"HOST: {QUESTION}\n\n" + DG.render_question_blind(OPTIONS)
    with pytest.raises(ValueError, match="HOST: line"):
        DG.assert_question_blind(bad, QUESTION)


def test_the_guard_catches_smuggled_excerpts():
    bad = DG.render_question_blind(OPTIONS) + f"\n{R.EXCERPTS_HEADER}\nstuff"
    with pytest.raises(ValueError, match="carries excerpts"):
        DG.assert_question_blind(bad, QUESTION)


def test_the_diagnostic_preamble_is_d8s_own_first_sentence():
    # Minimal deviation is the point: only the GUEST clause is dropped, because
    # there is no question below for GUEST to appear in.
    assert R.ZEROINFO_PREAMBLE.startswith(DG.QB_PREAMBLE)
    assert "GUEST" not in DG.QB_PREAMBLE


def test_the_diagnostic_has_its_own_freeze_marker_separate_from_d8s():
    # QB_PREAMBLE is DELIBERATELY a substring of the frozen text -- it is D8's
    # own first sentence, reused verbatim. What must be new is the choice line,
    # and what must be separate is the freeze marker, so editing one cannot
    # silently re-freeze the other.
    assert DG.QB_TEMPLATE_SHA256 != R.TEMPLATE_SHA256
    assert DG.QB_PREAMBLE in R.TEMPLATE_TEXT
    assert DG.QB_CHOICE_LINE not in R.TEMPLATE_TEXT


def test_the_diagnostic_template_is_frozen_by_digest():
    # Re-freeze on purpose if this fails; a silent edit changes what the
    # diagnostic measured and invalidates comparison with the gate.
    assert DG.QB_TEMPLATE_SHA256 == (
        "d275f7a7cc0d7476eaa9290a74aea280fa46f11da5d7a9c5ec0b5de276bcba80")


def test_a_diagnostic_name_is_never_one_of_the_five_arms():
    for name in (DG.DIAG_STRIPPED, DG.DIAG_QUESTION_BLIND):
        assert name not in R.ARMS
        assert "DIAGNOSTIC" in DG.DIAG_RULES[name]


def test_rendering_needs_at_least_two_options():
    with pytest.raises(ValueError):
        DG.render_question_blind(["only one"])
