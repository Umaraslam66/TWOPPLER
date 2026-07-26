"""DIAGNOSTIC prompt shapes for Stage 2 pilot round 2. NOT arms.

Nothing in this module is a SPEC D8 arm, nothing here may appear in a fidelity
table, and no result measured with it clears or fails a bar. It exists to
decompose ONE observation: after the same-subject redesign, the
zero-information arm still solved 10 of 10 candidate items with margins of
+0.80 to +1.00 (pilot round 2, phase 1).

Two things could carry that:

- **the option texts themselves** — dated names and events mark which answer
  belongs to the test interview's era. D2 makes the test interview the latest by
  construction, so every distractor is systematically older (measured mean gap
  5.0 years on this set). A4.2's entity-stripped variant already exists to blunt
  this, and needs no new template: it is the frozen renderer called with the
  stripped option texts.
- **responsiveness to the shown question** — a real answer replies to the
  question it was asked, so among real answers to OTHER questions it is the only
  one that fits. This one has no existing instrument, which is why this module
  exists.

:func:`render_question_blind` removes the question and asks the same forced
choice. If accuracy stays high without the question, the tell is in the options;
if it collapses, the tell is responsiveness.

**The frozen D8 templates are not touched.** This module composes new constants
and reuses ``stage2_render``'s option renderer and answer-format instruction, so
option formatting and the parse contract stay byte-identical to the arms and the
same parser reads both.
"""

from __future__ import annotations

import hashlib

from doppler import stage2_render as R

#: D8's ZEROINFO_PREAMBLE first sentence, verbatim. The second sentence of the
#: D8 constant ("The person is called GUEST in the question below.") is dropped
#: because there is no question below -- keeping it would describe a prompt the
#: model is not being shown.
QB_PREAMBLE = (
    "A person was interviewed on American broadcast news. Predict which "
    "answer they gave."
)

#: D8's CHOICE_LINE with ``who`` = "the person", plus "in this interview".
#: The clause is required, not cosmetic: with the question removed, "these
#: replies" has no referent and the forced choice reads as ungrounded.
QB_CHOICE_LINE = "Which of these replies did the person give in this interview?"

#: Freeze marker for this module's own strings, so a silent edit is detectable
#: the same way TEMPLATE_SHA256 makes one detectable in the frozen renderer.
QB_TEMPLATE_TEXT = "\n".join([QB_PREAMBLE, QB_CHOICE_LINE])
QB_TEMPLATE_SHA256 = hashlib.sha256(
    QB_TEMPLATE_TEXT.encode("utf-8")).hexdigest()

#: Names the artifacts use for the two diagnostics.
DIAG_STRIPPED = "gate_stripped"
DIAG_QUESTION_BLIND = "gate_qblind"

DIAG_RULES = {
    DIAG_STRIPPED:
        "DIAGNOSTIC A. The frozen zeroinfo_redacted template, standard "
        "renderer, called with A4.2's entity-stripped option texts. No new "
        "template. Isolates how much of the solve rides on named entities and "
        "numbers.",
    DIAG_QUESTION_BLIND:
        "DIAGNOSTIC B. Zero-information, standard option texts, HOST QUESTION "
        "REMOVED. Isolates how much of the solve rides on the true answer "
        "being responsive to the question shown, versus cues intrinsic to the "
        "options (era, style, dates).",
}


def render_question_blind(options) -> str:
    """DIAGNOSTIC B. A zero-information forced choice with no question.

    Same option rendering and same answer-format instruction as every D8 arm,
    so the frozen parser reads the reply unchanged and only one thing has moved
    relative to ``zeroinfo_redacted``: the question is gone.
    """
    blocks = [
        QB_PREAMBLE,
        f"{QB_CHOICE_LINE}\n{R.render_options(options)}",
        R.distribution_instruction(len(options)),
    ]
    return "\n\n".join(blocks)


def assert_question_blind(rendered: str, question: str) -> None:
    """The question must not have survived into a question-blind prompt.

    Checked on a normalised copy of a long run of the question's own words, so
    an accidental re-introduction of the question (or of the HOST: line the D8
    arms carry) is a loud failure rather than a silently weaker diagnostic.
    """
    if f"{R.HOST_LABEL}:" in rendered:
        raise ValueError("question-blind prompt carries a HOST: line")
    if R.EXCERPTS_HEADER in rendered or "[Interview," in rendered:
        raise ValueError("question-blind prompt carries excerpts")
    leak = R.find_answer_leak(rendered, question, n=6)
    if leak is not None:
        raise ValueError(
            f"question-blind prompt still contains the question: {leak!r}")


__all__ = [
    "QB_PREAMBLE", "QB_CHOICE_LINE", "QB_TEMPLATE_TEXT", "QB_TEMPLATE_SHA256",
    "DIAG_STRIPPED", "DIAG_QUESTION_BLIND", "DIAG_RULES",
    "render_question_blind", "assert_question_blind",
]
