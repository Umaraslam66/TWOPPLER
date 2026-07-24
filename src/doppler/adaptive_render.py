"""Prompt rendering for the Stage-1E adaptive-elicitation gym.

**Pure standard library on purpose.** This exact file is rsynced to the Leonardo
compute node next to the adaptive driver, so the driver and the local
export/ingest code build prompts from one shared implementation and cannot
drift apart. Do not add third-party imports here.

Format contract with the gate (results/stage1_gate_report.md): a TIPI
prediction prompt built here with all 48 items revealed is byte-identical to
the gate's v2 twin prompt for that person **except** for the order of the
revealed-item lines. The gate renders items in canonical R1..C8 order; the gym
renders them in the order the policy revealed them, which is the honest
representation of an interview and is what the leakage guard checks.

Blocks, in order:

    {INTRO}

    MY PROFILE
    ...one line of demographic fragments...

    HOW I RATED MY INTEREST IN VARIOUS ACTIVITIES     <- omitted when k == 0
    (Scale: 1=Dislike, 3=Neutral, 5=Enjoy)
    - <item text>: <1-5>

    YOUR TASK
    ...the held-out question + the answer-format instruction...
"""

from __future__ import annotations

import hashlib

# Byte-identical to doppler.prompts.INTRO (checked by tests/test_adaptive.py).
INTRO = (
    "You are simulating a specific, real survey respondent. Answer exactly as "
    "this person would, based on their profile below."
)

# Byte-identical to doppler.prompts.VARIANT_FINAL_INSTRUCTION["v2"] (checked).
TIPI_INSTRUCTION = (
    "Answer as this person would. Output a probability for each of the 7 "
    "answers on a single line, in exactly this format:\n"
    "1:0.05 2:0.10 3:0.15 4:0.30 5:0.20 6:0.15 7:0.05"
)

#: The same v2 idea on the 1-5 interest scale: used only by the adaptive
#: policy's uncertainty calls, never scored as an outcome.
INTEREST_INSTRUCTION = (
    "Answer as this person would. Output a probability for each of the 5 "
    "answers on a single line, in exactly this format:\n"
    "1:0.20 2:0.20 3:0.20 4:0.20 5:0.20"
)

INTERESTS_HEADER = "HOW I RATED MY INTEREST IN VARIOUS ACTIVITIES"

#: Output-token budgets. TIPI matches the gate exactly (120); the 5-way
#: interest distribution is shorter so it gets a smaller cap.
MAX_OUTPUT_TOKENS_TIPI = 120
MAX_OUTPUT_TOKENS_INTEREST = 100


def interests_block(pairs: list, anchors: str) -> str | None:
    """Render the revealed-items block, or ``None`` when nothing is revealed.

    ``pairs`` is an ordered list of ``(item_text, answer)`` in **reveal order**.
    Returning ``None`` for the empty case makes a 0-reveal profile
    byte-identical to the demographics-only baseline profile.
    """
    if not pairs:
        return None
    lines = [INTERESTS_HEADER, f"(Scale: {anchors})"]
    for text, answer in pairs:
        lines.append(f"- {text}: {answer}")
    return "\n".join(lines)


def profile(demographics_block: str, pairs: list, anchors: str) -> str:
    """Demographics block plus the revealed-items block (when non-empty)."""
    block = interests_block(pairs, anchors)
    if block is None:
        return demographics_block
    return demographics_block + "\n\n" + block


def tipi_task(tipi_text: str, tipi_anchors: str) -> str:
    """The held-out TIPI question + the v2 answer-format instruction."""
    return (
        "YOUR TASK\n"
        f'The survey asked this person to rate the statement "I see myself as: '
        f'{tipi_text}" on this scale: {tipi_anchors}.\n\n'
        f"{TIPI_INSTRUCTION}"
    )


def interest_task(item_text: str, riasec_anchors: str) -> str:
    """The 'how would you rate this activity' question for an unrevealed item."""
    return (
        "YOUR TASK\n"
        f"The survey asked this person to rate how much they would enjoy this "
        f'activity: "{item_text}" on this scale: {riasec_anchors}.\n\n'
        f"{INTEREST_INSTRUCTION}"
    )


def assemble(profile_text: str, task_text: str) -> str:
    return f"{INTRO}\n\n{profile_text}\n\n{task_text}"


def tipi_prompt(demographics_block: str, pairs: list, riasec_anchors: str,
                tipi_text: str, tipi_anchors: str) -> str:
    """Full TIPI prediction prompt for a person at some reveal depth."""
    return assemble(profile(demographics_block, pairs, riasec_anchors),
                    tipi_task(tipi_text, tipi_anchors))


def interest_prompt(demographics_block: str, pairs: list, riasec_anchors: str,
                    item_text: str) -> str:
    """Full uncertainty prompt: ask about one item that is NOT yet revealed."""
    return assemble(profile(demographics_block, pairs, riasec_anchors),
                    interest_task(item_text, riasec_anchors))


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Distribution parsing (1-5) + entropy. Mirrors doppler.scoring.v2_probabilities
# for the 7-point case; duplicated here only because this file must stay
# dependency-free for the compute node. tests/test_adaptive.py checks the two
# agree on shared inputs.
# ---------------------------------------------------------------------------

#: Sentinel entropy for an unparseable uncertainty answer. Strictly below the
#: real minimum (0.0), so a parse failure is never *rewarded* with selection;
#: it is chosen only if every remaining candidate also failed, and the
#: lowest-index tie-break then applies.
PARSE_FAILURE_ENTROPY = -1.0


def parse_interest_distribution(text: str | None) -> dict | None:
    """Parse ``1:p 2:p 3:p 4:p 5:p`` -> normalized ``{1..5: prob}``.

    Same validation rules as the v2 TIPI parser: every key 1-5 present exactly
    once, no extra keys, no negatives, positive total. Reordering and arbitrary
    whitespace are tolerated. Malformed input returns ``None``.
    """
    if not text:
        return None
    probs: dict[int, float] = {}
    i = 0
    n = len(text)
    while i < n:
        # Scan for "<int> : <float>" without regex-heavy machinery.
        if not (text[i].isdigit() or (text[i] == "-" and i + 1 < n
                                      and text[i + 1].isdigit())):
            i += 1
            continue
        j = i
        if text[j] == "-":
            j += 1
        while j < n and text[j].isdigit():
            j += 1
        key_str = text[i:j]
        m = j
        while m < n and text[m] in " \t":
            m += 1
        if m >= n or text[m] != ":":
            i = j
            continue
        m += 1
        while m < n and text[m] in " \t":
            m += 1
        v = m
        if v < n and text[v] == "-":
            v += 1
        seen_digit = False
        while v < n and (text[v].isdigit() or text[v] == "."):
            if text[v].isdigit():
                seen_digit = True
            v += 1
        if not seen_digit:
            i = j
            continue
        try:
            key = int(key_str)
            val = float(text[m:v])
        except ValueError:
            i = j
            continue
        if key in probs:
            return None  # duplicate key -> ambiguous
        probs[key] = val
        i = v
    if set(probs) != set(range(1, 6)):
        return None
    if any(p < 0 for p in probs.values()):
        return None
    total = sum(probs.values())
    if total <= 0:
        return None
    return {k: probs[k] / total for k in range(1, 6)}


def entropy(dist: dict | None) -> float:
    """Shannon entropy in nats, or :data:`PARSE_FAILURE_ENTROPY` for ``None``."""
    if dist is None:
        return PARSE_FAILURE_ENTROPY
    import math

    total = 0.0
    for p in dist.values():
        if p > 0:
            total -= p * math.log(p)
    return total
