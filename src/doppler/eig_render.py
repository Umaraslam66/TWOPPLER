"""Prompt rendering + maths for the Stage-1E EXP3 information-gain policy.

**Pure standard library on purpose.** Like ``adaptive_render.py``, this exact
file is rsynced to the Leonardo compute node next to the EIG driver, so the
driver and any local re-analysis build prompts from one shared implementation
and cannot drift apart. Do not add third-party imports here.

What the EXP3 policy needs that the plain adaptive arm does not:

* a way to ask the model for **all 10 TIPI distributions in one call**. The
  policy has to look at what a hypothetical answer would do to the targets, and
  doing that one target at a time costs 10x. So we add a multi-target prompt,
  used ONLY inside the policy -- never as an outcome. Checkpoint predictions
  still go through ``adaptive_render.tipi_prompt``, single target, identical to
  every other arm, so the ladder stays comparable.
* a distance between two sets of target distributions. We use total variation,
  averaged over the 10 targets: "how far did the model's belief about this
  person's personality move when I told it one more thing about them".
* the weights that turn "how far would it move" into an expectation: the
  candidate item's own stated probability of each hypothetical answer.

Nothing here scores a held-out answer. The node pack carries no TIPI answers,
so none of these prompts can contain one even in principle.
"""

from __future__ import annotations

import re

try:  # on the node: adaptive_render.py sits next to this file
    import adaptive_render as R
except ImportError:  # locally (tests, analysis): it lives in the package
    from doppler import adaptive_render as R  # noqa: F401


#: The multi-target answer-format instruction. Deliberately as close to
#: :data:`adaptive_render.TIPI_INSTRUCTION` (the frozen v2 wording) as a
#: 10-line answer allows: same opening sentence, same "probability for each of
#: the 7 answers" phrasing, same worked example on the right-hand side. What is
#: added is the per-line code prefix and the line-count contract, because those
#: are the two things a model gets wrong when asked for a block of answers.
#:
#: The example uses ``TIPI1`` because that is always the first real target code;
#: :func:`multi_tipi_task` also lists every code explicitly above this text, so
#: the model never has to guess a code.
MULTI_TIPI_INSTRUCTION = (
    "Answer as this person would. Output one line for each of the 10 "
    "statements above, in the order they are listed, starting with that "
    "statement's code. On each line, output a probability for each of the 7 "
    "answers, in exactly this format:\n"
    "TIPI1: 1:0.05 2:0.10 3:0.15 4:0.30 5:0.20 6:0.15 7:0.05\n"
    "Output exactly 10 lines, one per code, each with all 7 probabilities. "
    "No other text."
)

#: Output-token budget for a 10-line answer. One line of the required shape is
#: about 35 tokens, so 10 lines is ~350; 420 leaves room for a stray newline or
#: a slightly chatty code prefix without paying for a runaway generation.
MAX_OUTPUT_TOKENS_MULTI_TIPI = 420

#: A ``key:prob`` pair. Same shape as ``doppler.scoring._PAIR`` so the 7-point
#: rules here and in the shipped v2 scorer cannot diverge.
_PAIR = re.compile(r"(-?\d+)\s*:\s*(-?\d*\.?\d+)")

#: A leading ordered-list marker, e.g. ``3.`` or ``3)``.
_ORDERED = re.compile(r"^\d+[.)]\s*")


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------


def multi_tipi_task(tipi_codes: list, tipi_texts: dict,
                    tipi_anchors: str) -> str:
    """The 'rate all 10 statements' task block.

    Wording tracks :func:`adaptive_render.tipi_task` as closely as a 10-item
    question can: same ``I see myself as: {text}`` framing per statement, same
    ``on this scale: {anchors}`` sentence, then the answer-format instruction.
    Each statement is prefixed with its code so the model has nothing to invent
    when it writes the code column.
    """
    lines = [
        "YOUR TASK",
        f"The survey asked this person to rate each of these "
        f"{len(tipi_codes)} statements on this scale: {tipi_anchors}.",
        "",
    ]
    for code in tipi_codes:
        lines.append(f'{code}: "I see myself as: {tipi_texts[code]}"')
    lines.append("")
    lines.append(MULTI_TIPI_INSTRUCTION)
    return "\n".join(lines)


def multi_tipi_prompt(demographics_block: str, pairs: list,
                      riasec_anchors: str, tipi_codes: list, tipi_texts: dict,
                      tipi_anchors: str) -> str:
    """Full multi-target prompt for a person at some reveal depth.

    ``pairs`` is the ordered ``(item_text, answer)`` list in reveal order,
    **including** any hypothetical pair the caller appended. The profile head is
    built by the shared renderer, so a hypothetical profile is byte-identical to
    a real one of the same depth -- which is the point: the policy is asking
    "what would I believe if this were true".
    """
    return R.assemble(
        R.profile(demographics_block, pairs, riasec_anchors),
        multi_tipi_task(tipi_codes, tipi_texts, tipi_anchors),
    )


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_tipi_distribution(text: str | None) -> dict | None:
    """Parse ``1:p ... 7:p`` -> normalized ``{1..7: prob}``, or ``None``.

    Exactly the rules ``doppler.scoring.v2_probabilities`` uses -- every key 1-7
    present exactly once, no extra keys, no negatives, positive total, then
    normalize. Duplicated here only because this file must stay dependency-free
    for the compute node; tests/test_eig.py checks the two agree.
    """
    if not text:
        return None
    probs: dict[int, float] = {}
    for key_str, val_str in _PAIR.findall(text):
        key = int(key_str)
        if key in probs:  # duplicate key -> ambiguous
            return None
        probs[key] = float(val_str)
    if set(probs) != set(range(1, 8)):
        return None
    if any(p < 0 for p in probs.values()):
        return None
    total = sum(probs.values())
    if total <= 0:
        return None
    return {k: probs[k] / total for k in range(1, 8)}


def _strip_decoration(line: str) -> str:
    """Remove the markdown a chat model sprinkles on a list line.

    Handles ``**TIPI1**``, backticks, ``- `` bullets, ``* `` bullets and
    ``3.`` numbering. We only need the *front* of the line to be clean enough to
    match a code against; the probability pairs behind it survive untouched
    because none of the removed characters can appear inside ``d:p``.
    """
    s = line.replace("*", "").replace("`", "").replace("_", "").strip()
    while s and s[0] in "-–—•+>#":
        s = s[1:].lstrip()
    s = _ORDERED.sub("", s)
    return s.strip()


def parse_multi_tipi(text: str | None, tipi_codes: list) -> dict | None:
    """Parse a 10-line multi-target answer -> ``{code: {1..7: prob}}``.

    Returns ``None`` if **any** required code is missing, duplicated, or carries
    a malformed distribution. All-or-nothing on purpose: a partial answer would
    quietly shrink the averaged distance and make one candidate look calmer than
    another for a reason that has nothing to do with the person.

    Tolerated (models do all of these): prose before or after the block, blank
    lines, markdown bullets and bold, ``TIPI1 -`` instead of ``TIPI1:``, lines in
    any order, arbitrary whitespace.

    Judgement call: a line that starts with a code but contains **no** ``d:p``
    pair at all is treated as prose and skipped, not as a malformed answer.
    That is what lets a preamble like ``TIPI1 through TIPI10 are below:`` pass
    through. A line that starts with a code and *does* contain pairs is a real
    answer attempt, so anything wrong with it (6 probabilities, a negative, an
    all-zero line) fails the whole parse.
    """
    if not text:
        return None
    codes = list(tipi_codes)
    # Longest code first so ``TIPI10`` is never eaten by ``TIPI1``.
    by_length = sorted(codes, key=len, reverse=True)
    upper = {code: code.upper() for code in codes}

    out: dict[str, dict] = {}
    for raw in text.splitlines():
        s = _strip_decoration(raw)
        if not s:
            continue
        su = s.upper()
        matched = None
        for code in by_length:
            u = upper[code]
            if su.startswith(u) and (len(s) == len(u) or not s[len(u)].isdigit()):
                matched = code
                break
        if matched is None:
            continue
        rest = s[len(matched):].lstrip()
        while rest and rest[0] in ":-–—=)|.":
            rest = rest[1:].lstrip()
        if not _PAIR.search(rest):
            continue  # prose that happens to start with a code
        if matched in out:
            return None  # the same target answered twice -> ambiguous
        dist = parse_tipi_distribution(rest)
        if dist is None:
            return None
        out[matched] = dist

    if set(out) != set(codes):
        return None
    return out


# ---------------------------------------------------------------------------
# Information-gain maths
# ---------------------------------------------------------------------------


def total_variation(p: dict | None, q: dict | None) -> float:
    """Total-variation distance: ``0.5 * sum |p_v - q_v|``.

    0 means "the two beliefs are the same", 1 means "they have no overlap at
    all". Missing keys count as zero mass, so distributions on different
    supports still compare cleanly.
    """
    if not p or not q:
        return 0.0
    total = 0.0
    for v in set(p) | set(q):
        total += abs(p.get(v, 0.0) - q.get(v, 0.0))
    return 0.5 * total


def mean_tv_shift(dists_a: dict | None, dists_0: dict | None,
                  tipi_codes: list) -> float:
    """Average, over the 10 targets, of how far the belief moved.

    ``dists_a`` is what the model believes after the hypothetical answer,
    ``dists_0`` is what it believes now. Either side being ``None`` (an
    unparseable completion) returns 0.0 -- "no evidence of movement" -- so a
    parse failure can never *win* a candidate the reveal. A target missing from
    one side contributes 0.0 for the same reason.
    """
    if dists_a is None or dists_0 is None:
        return 0.0
    codes = list(tipi_codes)
    if not codes:
        return 0.0
    total = 0.0
    for code in codes:
        total += total_variation(dists_a.get(code), dists_0.get(code))
    return total / len(codes)


def hypothetical_weights(q: dict | None, answers=(1, 3, 5)) -> dict:
    """How likely each hypothetical answer is, per the item's own answer.

    ``q`` is the candidate item's parsed 1-5 self-uncertainty distribution. We
    only ever simulate the three anchor answers, so their probabilities are
    renormalized to sum to 1. If ``q`` is unparseable, or it put no mass at all
    on the three anchors, we fall back to uniform -- guessing evenly is honest,
    and it keeps a parse failure here from silently zeroing the candidate.
    """
    keys = tuple(answers)
    if not keys:
        return {}
    uniform = {a: 1.0 / len(keys) for a in keys}
    if not q:
        return uniform
    vals = {}
    mass = 0.0
    for a in keys:
        p = q.get(a, 0.0)
        if p is None or p < 0:
            p = 0.0
        vals[a] = float(p)
        mass += float(p)
    if mass <= 0:
        return uniform
    return {a: vals[a] / mass for a in keys}


def info_gain_score(shift_by_answer: dict, weights: dict) -> float:
    """Expected movement: ``sum_a weight(a) * shift(a)``.

    Higher means "asking this item is more likely to change what I believe
    about this person's personality", which is what the EXP3 policy maximizes.
    """
    return sum(w * float(shift_by_answer.get(a, 0.0))
               for a, w in weights.items())
