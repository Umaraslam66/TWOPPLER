"""Follow-up vs new-topic classification of interviewer turns (Stage 2, D9).

**Pure standard library on purpose.** Like ``adaptive_render.py``, this exact
file is rsynced to the compute node next to the classifier driver, so the node
and any local re-analysis build prompts from one shared implementation and
cannot drift apart. Do not add third-party imports here.

What this file is for: every host turn in a test interview has to be tagged
FOLLOW-UP (it works on what the guest just said) or NEW-TOPIC (it brings in
something else). A local LLM does the tagging with one frozen rubric prompt;
this module builds that prompt and parses the answer. No model calls happen
here, and nothing here touches disk or network.

The rubric is DRAFT until bar-lock (SPEC D9). :data:`RUBRIC_SHA256` is the
freeze marker: it is pinned in ``tests/test_followup_render.py``, so any edit
to the rubric text -- including a stray space -- fails the test suite and has
to be re-frozen on purpose.

Blocks of a rendered prompt, in order:

    {RUBRIC_V1}          <- task, definitions, hard-case rules, 4 examples

    NOW LABEL THIS CASE

    PREV: ...            <- last 60 words of the interviewer's previous turn
    GUEST: ...           <- last 120 words of the guest's answer to it
    TARGET: ...          <- first 120 words of the turn being labelled

    {OUTPUT_INSTRUCTION}

The three field names are the same ones the few-shot examples use, so the
model sees one vocabulary throughout.
"""

from __future__ import annotations

import hashlib
import re

FOLLOW_UP = "FOLLOW-UP"
NEW_TOPIC = "NEW-TOPIC"

#: The only two labels a classification may carry.
LABELS = (FOLLOW_UP, NEW_TOPIC)

#: Truncation budgets from SPEC D9, in words (whitespace tokens -- the pilot's
#: documented token proxy). PREV and GUEST keep their *last* words because what
#: matters is what the guest said most recently; TARGET keeps its *first* words
#: because an interviewer's turn declares its business up front.
PREV_HOST_WORDS = 60
GUEST_ANSWER_WORDS = 120
TARGET_HOST_WORDS = 120

#: Marks where truncation removed text, so neither the model nor a human
#: auditor mistakes a mid-sentence fragment for a whole turn.
TRUNCATION_MARK = "..."

#: Rendered in place of a field that is empty after normalisation. Never
#: produced by :func:`classifiable_turns`; it exists so a degenerate direct
#: call still yields a well-formed prompt rather than a dangling label.
EMPTY_FIELD = "(none)"

#: Two short lines of output; a small cap also discourages the model from
#: writing an essay that the strict parser would then reject.
MAX_OUTPUT_TOKENS = 80

#: The frozen rubric. Under 450 words so it fits comfortably in short-context
#: calls (checked by the tests). ASCII only -- this file is rsynced and the
#: digest must survive the trip byte for byte.
RUBRIC_V1 = """FOLLOW-UP OR NEW-TOPIC

Label one turn from a news interview. Each case gives three fields:

PREV: the interviewer's previous turn.
GUEST: what the guest said in reply to PREV.
TARGET: the interviewer turn you must label.

A field may be cut off mid-sentence; "..." marks removed text. Label the TARGET
only.

FOLLOW-UP means the TARGET references, quotes, probes, or challenges something
in GUEST. That includes minimal continuers that only ask for more of the same
answer ("Go on.", "Meaning what?", "Such as?"); asking the guest to explain,
define, or back up something they just said; and pushback that disputes it.

NEW-TOPIC means the TARGET brings in material that does not come from GUEST: a
prepared or agenda question, a change of subject, a segment transition, a
sign-off, or a question to someone else. Two turns that look like follow-ups
but are NEW-TOPIC: acknowledge-then-pivot ("Fascinating. Now, the budget
vote..."), and going back to the interviewer's own earlier line of questioning
as if GUEST had not happened.

HARD CASES
1. Compound turn (a comment or acknowledgment plus a question): label by the
question. Probes GUEST -> FOLLOW-UP. New material -> NEW-TOPIC.
2. Same topic is not enough: a question can share the subject and still be
NEW-TOPIC if it takes nothing from GUEST.
3. Re-asking something the guest dodged is FOLLOW-UP only if the TARGET names
the dodge or quotes the answer; a bare repeat is NEW-TOPIC.
4. Part taken from GUEST and part new -> FOLLOW-UP.
5. Judge the words, not the interviewer's intention.

EXAMPLES

PREV: Why did you resign that week?
GUEST: I asked for the audit three times and was told to wait. After the third refusal I quit.
TARGET: Go on.
LABEL: FOLLOW-UP
WHY: A bare prompt to keep talking asks for more of the same answer.

PREV: How bad is the shortage?
GUEST: We are down to one week of supply and have started rationing tests.
TARGET: That is alarming. Who decides which patients get tested?
LABEL: FOLLOW-UP
WHY: The comment is filler; the question digs into the rationing just described.

PREV: How bad is the shortage?
GUEST: We are down to one week of supply and have started rationing tests.
TARGET: Fascinating. Let me turn to the election - will you endorse the governor?
LABEL: NEW-TOPIC
WHY: The acknowledgment is followed by a pivot to unrelated material.

PREV: Do you think your party mishandled the vote?
GUEST: I would not put it that way. The vote was rushed, and members said so afterwards.
TARGET: Earlier I asked about the housing bill. Are you still voting for it?
LABEL: NEW-TOPIC
WHY: The interviewer returns to an earlier question and uses nothing from the answer."""

#: The header between the rubric and the case being labelled.
CASE_HEADER = "NOW LABEL THIS CASE"

#: The output contract from SPEC D9. The four examples above already show the
#: two lines filled in, so the placeholder form here cannot be copied blindly.
OUTPUT_INSTRUCTION = (
    "Reply with exactly two lines and nothing else:\n"
    "LABEL: <FOLLOW-UP or NEW-TOPIC>\n"
    "WHY: <one sentence, 25 words or fewer>"
)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


#: Freeze marker for the rubric; pinned in the tests.
RUBRIC_SHA256 = sha256(RUBRIC_V1)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def last_words(text: str, n: int) -> str:
    """The last ``n`` whitespace-separated words, marked if anything was cut.

    Also collapses every run of whitespace (including newlines) to one space,
    which is what keeps one turn on one line of the prompt.
    """
    words = (text or "").split()
    if len(words) <= n:
        return " ".join(words)
    return f"{TRUNCATION_MARK} " + " ".join(words[-n:])


def first_words(text: str, n: int) -> str:
    """The first ``n`` words, marked if anything was cut. See :func:`last_words`."""
    words = (text or "").split()
    if len(words) <= n:
        return " ".join(words)
    return " ".join(words[:n]) + f" {TRUNCATION_MARK}"


def case_block(prev_host: str, guest_answer: str, target_host: str) -> str:
    """The three context lines, truncated to the D9 budgets."""
    fields = (
        ("PREV", last_words(prev_host, PREV_HOST_WORDS)),
        ("GUEST", last_words(guest_answer, GUEST_ANSWER_WORDS)),
        ("TARGET", first_words(target_host, TARGET_HOST_WORDS)),
    )
    return "\n".join(f"{name}: {value or EMPTY_FIELD}" for name, value in fields)


def classify_prompt(prev_host: str, guest_answer: str, target_host: str) -> str:
    """Full classification prompt: rubric + the case + the output contract.

    Pure: the same three strings always give the same bytes, and inputs that
    differ only in whitespace give the same bytes too.
    """
    return (
        f"{RUBRIC_V1}\n\n"
        f"{CASE_HEADER}\n\n"
        f"{case_block(prev_host, guest_answer, target_host)}\n\n"
        f"{OUTPUT_INSTRUCTION}"
    )


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
#
# Tolerant about how the line is dressed -- leading spaces, list bullets, block
# quotes, headings, bold/italic/backtick markup, a trailing period -- and
# strict about the token itself: exactly FOLLOW-UP or NEW-TOPIC, hyphen
# included. Case is folded because "Follow-up" is the same decision, but
# "FOLLOWUP", "FOLLOW UP" and a bare label with no "LABEL:" prefix all fail.

_LABEL_RE = re.compile(
    r"^[ \t>#*_\-]*label[ \t*_]*:[ \t*_`\"']*(follow-up|new-topic)[*_`\"'.!]*[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)


def parse_label(completion: str | None) -> str | None:
    """``"FOLLOW-UP"``, ``"NEW-TOPIC"``, or ``None`` on parse failure.

    Exactly one LABEL line must be present. Zero lines is a failure; two or
    more is also a failure, even when they agree -- a model that states the
    label twice is either waffling or echoing the prompt, and neither should be
    scored. Callers may retry twice (SPEC D9).
    """
    if not completion:
        return None
    matches = _LABEL_RE.findall(completion.replace("\r\n", "\n").replace("\r", "\n"))
    if len(matches) != 1:
        return None
    return matches[0].upper()


# ---------------------------------------------------------------------------
# Turn selection
# ---------------------------------------------------------------------------


def classifiable_turns(turns: list) -> list:
    """Split a transcript's turns into rule-labelled and model-labelled hosts.

    ``turns`` is the SPEC D3 list -- ``{transcript_id, turn_idx, role,
    speaker_label, text}`` -- **in transcript order**. Returns one dict per
    host turn, in that same order, of one of two shapes:

    * ``{turn_idx, label: "NEW-TOPIC", source: "rule"}`` for the transcript's
      first host turn. It is NEW-TOPIC by definition (D9) and costs no model
      call. The rule wins even if a guest happened to speak before it.
    * ``{turn_idx, prev_host, guest_answer, target_host}`` for every later host
      turn that has a guest answer behind it. Feed the three texts straight to
      :func:`classify_prompt`.

    A host turn with no guest answer anywhere before it is skipped: there is
    nothing it could be following up on.

    How the three texts are chosen. ``guest_answer`` is the most recent run of
    consecutive guest turns before the target, joined with spaces; a host or
    "other" speaker ends a run (same rule as D4's answer assembly). Any role
    that is not "guest" or "host" counts as "other". ``prev_host`` is the host
    turn that came *before that run* -- the turn the guest was answering, not
    necessarily the turn immediately before the target. That matters when the
    interviewer speaks twice in a row: both of those turns get judged against
    the same guest answer and the same eliciting question, which is exactly
    what "did this turn go back to the interviewer's own agenda?" needs.
    """
    out: list = []
    first_host_done = False
    last_host_text = ""       # most recent host turn
    run: list = []            # guest turns since the last boundary
    run_prev_host = ""        # host turn that preceded the current run
    answer = None             # (prev_host, guest_answer) of the latest run

    for turn in turns:
        role = turn.get("role")
        text = (turn.get("text") or "").strip()
        if role == "guest":
            if not run:
                run_prev_host = last_host_text
            if text:
                run.append(text)
            continue
        # A host or "other" turn closes any run of guest turns.
        if run:
            answer = (run_prev_host, " ".join(run))
            run = []
        if role != "host":
            continue
        if not first_host_done:
            first_host_done = True
            out.append({"turn_idx": turn["turn_idx"], "label": NEW_TOPIC,
                        "source": "rule"})
        elif answer is not None:
            out.append({"turn_idx": turn["turn_idx"], "prev_host": answer[0],
                        "guest_answer": answer[1], "target_host": text})
        last_host_text = text
    return out
