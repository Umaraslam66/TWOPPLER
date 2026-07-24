"""Prompt construction for the Stage-1 replay gym.

ONE profile builder serves both arms. ``include_interests=True`` is the twin
arm (demographics + interest ratings); ``include_interests=False`` is the
zero-information baseline (demographics only). Building both arms from the same
code path is deliberate: the two prompts can only ever differ by the interests
block, so the arms cannot silently drift apart.

Scale anchors and every item text come from the parsed :class:`Codebook`,
never from hard-coded strings. The TIPI item under prediction is added by
:func:`build_prompt`; no TIPI content ever enters a profile.
"""

from __future__ import annotations

import numpy as np

from .data import RIASEC_ITEMS, Codebook

INTRO = (
    "You are simulating a specific, real survey respondent. Answer exactly as "
    "this person would, based on their profile below."
)

# ---------------------------------------------------------------------------
# Twin variants (applied identically to both arms). v0 = original behaviour.
# ---------------------------------------------------------------------------

VARIANTS = ("v0", "v1", "v2", "v3")

#: The final instruction line(s), chosen by variant. Everything above it (intro,
#: profile, question, scale) is identical across variants and across arms.
VARIANT_FINAL_INSTRUCTION = {
    "v0": (
        "Answer as this person would. Respond with a single integer from 1 to 7 "
        "and nothing else."
    ),
    "v1": (
        "Answer as this person would. First write one short sentence about how "
        "this person would answer. Then on a new line write only the integer "
        "(1-7)."
    ),
    "v2": (
        "Answer as this person would. Output a probability for each of the 7 "
        "answers on a single line, in exactly this format:\n"
        "1:0.05 2:0.10 3:0.15 4:0.30 5:0.20 6:0.15 7:0.05"
    ),
}

#: Output-token budget per variant (v1/v2 need room for a sentence / 7 pairs).
VARIANT_MAX_OUTPUT_TOKENS = {"v0": 16, "v1": 100, "v2": 120}

#: Extra reminder appended for the single parse-failure retry, per variant.
VARIANT_RETRY_REMINDER = {
    "v0": "Respond with only a single digit from 1 to 7.",
    "v1": "On the final line, write only a single integer from 1 to 7.",
    "v2": (
        "Reply with only the seven probabilities, one per answer, in exactly "
        "this format: 1:0.05 2:0.10 3:0.15 4:0.30 5:0.20 6:0.15 7:0.05"
    ),
}

# v3 = v0 with the scale-anchoring fix: the interests block renders WORDS instead
# of the raw 1-5 integers (see _interests_block), which stops a model from
# dragging its 1-7 TIPI answers toward the 1-5 interest digits. Everything else
# (final instruction, token budget, retry reminder, parser) is identical to v0.
VARIANT_FINAL_INSTRUCTION["v3"] = VARIANT_FINAL_INSTRUCTION["v0"]
VARIANT_MAX_OUTPUT_TOKENS["v3"] = VARIANT_MAX_OUTPUT_TOKENS["v0"]
VARIANT_RETRY_REMINDER["v3"] = VARIANT_RETRY_REMINDER["v0"]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _has(value) -> bool:
    """True if a demographic value is present (not None, not blank string)."""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def _format_anchors(anchors: dict[int, str]) -> str:
    """``{1:'Dislike',3:'Neutral',5:'Enjoy'}`` -> ``"1=Dislike, 3=Neutral, 5=Enjoy"``."""
    return ", ".join(f"{code}={anchors[code]}" for code in sorted(anchors))


# ---------------------------------------------------------------------------
# Deterministic per-person interest subsampling
# ---------------------------------------------------------------------------


def select_interest_items(person_id: int, k: int, seed: int) -> list[str]:
    """Return ``k`` interest item codes for this person, in canonical order.

    When ``k >= 48`` all items are used. When ``k < 48`` a deterministic subset
    is drawn with ``numpy.random.default_rng(seed * 1000003 + person_id)`` so
    the same person always sees the same items for a given ``(k, seed)``. The
    returned list is always in canonical R1..C8 order regardless of draw order.
    """
    n = len(RIASEC_ITEMS)
    if k >= n:
        return list(RIASEC_ITEMS)
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")
    rng = np.random.default_rng(seed * 1000003 + person_id)
    idx = rng.choice(n, size=k, replace=False)
    chosen = {RIASEC_ITEMS[i] for i in idx}
    return [code for code in RIASEC_ITEMS if code in chosen]


# ---------------------------------------------------------------------------
# Profile blocks
# ---------------------------------------------------------------------------


def _demographics_block(demo: dict) -> str:
    """The 'MY PROFILE' body: one line of sentence-fragments.

    Any fragment whose value is missing (None / blank) is omitted entirely, so
    the literal strings "None"/"nan" never reach the model.
    """
    frags: list[str] = []

    age = demo.get("age")
    gender = demo.get("gender")
    if _has(age) and _has(gender):
        frags.append(f"I am a {age}-year-old {gender.lower()}.")
    elif _has(age):
        frags.append(f"I am {age} years old.")
    elif _has(gender):
        frags.append(f"I am a {gender.lower()}.")

    if _has(demo.get("country")):
        frags.append(f"My country: {demo['country']}.")
    if _has(demo.get("urban")):
        frags.append(f"I grew up in a {demo['urban'].lower()} area.")
    if _has(demo.get("education")):
        frags.append(f"My education level: {demo['education']}.")
    if _has(demo.get("engnat")):
        frags.append(f"Native English speaker: {demo['engnat']}.")
    if _has(demo.get("religion")):
        frags.append(f"Religion: {demo['religion']}.")
    if _has(demo.get("orientation")):
        frags.append(f"Sexual orientation: {demo['orientation']}.")
    if _has(demo.get("race")):
        frags.append(f"Race: {demo['race']}.")
    if _has(demo.get("married")):
        frags.append(f"Marital status: {demo['married']}.")
    familysize = demo.get("familysize")
    if _has(familysize) and familysize >= 1:
        frags.append(
            f"Number of children my parents had, including me: {familysize}."
        )
    if _has(demo.get("voted")):
        frags.append(f"Voted in a national election in the past year: {demo['voted']}.")
    if _has(demo.get("major")):
        frags.append(f"College major: {demo['major']}.")

    return "MY PROFILE\n" + " ".join(frags)


def _interest_words(codebook: Codebook) -> dict[int, str]:
    """Map interest ratings 1-5 to WORDS with no digits (used by variant v3).

    The codebook only anchors 1/3/5 (Dislike/Neutral/Enjoy). 2 and 4 are
    INTERPOLATED deterministically as "Slightly <dislike>" / "Slightly <enjoy>"
    from those anchors, so the mapping is 1->Dislike, 2->Slightly dislike,
    3->Neutral, 4->Slightly enjoy, 5->Enjoy.
    """
    anchors = codebook.scales["riasec"]["anchors"]
    return {
        1: anchors[1],
        2: f"Slightly {anchors[1].lower()}",
        3: anchors[3],
        4: f"Slightly {anchors[5].lower()}",
        5: anchors[5],
    }


def _interests_block(
    record: dict, codebook: Codebook, k: int, seed: int, variant: str = "v0"
) -> str:
    """The interests block, only ever present in the twin arm.

    v0/v1/v2 render the numeric 1-5 ratings with a scale line. v3 renders WORDS
    with a digit-free header and no scale line, so nothing in the block is a
    number the model can anchor its 1-7 answer to.
    """
    codes = select_interest_items(record["person_id"], k, seed)
    if variant == "v3":
        words = _interest_words(codebook)
        lines = ["HOW I FEEL ABOUT VARIOUS ACTIVITIES"]
        for code in codes:
            entry = record["interests"][code]
            lines.append(f"- {entry['text']}: {words[entry['answer']]}")
        return "\n".join(lines)

    anchors = _format_anchors(codebook.scales["riasec"]["anchors"])
    lines = [
        "HOW I RATED MY INTEREST IN VARIOUS ACTIVITIES",
        f"(Scale: {anchors})",
    ]
    for code in codes:
        entry = record["interests"][code]
        lines.append(f"- {entry['text']}: {entry['answer']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------


def build_profile(
    record: dict,
    codebook: Codebook,
    include_interests: bool,
    k: int = 48,
    seed: int = 42,
    variant: str = "v0",
) -> str:
    """Build a person's profile text. Single function shared by both arms.

    ``variant`` only affects the interests block (v3 renders words, not digits);
    the demographics block is variant-independent, so a baseline profile
    (``include_interests=False``) is byte-identical across all variants.
    """
    demo = _demographics_block(record["demographics"])
    if not include_interests:
        return demo
    return demo + "\n\n" + _interests_block(record, codebook, k, seed, variant)


def build_prompt(
    profile: str, tipi_code: str, codebook: Codebook, variant: str = "v0"
) -> str:
    """Wrap a profile with the intro line and the held-out TIPI question.

    The only thing ``variant`` changes is the final instruction line; the intro,
    profile, question, and scale are identical across all variants and both arms.
    """
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}, got {variant!r}")
    tipi_text = codebook.tipi_items[tipi_code]
    tipi_anchors = _format_anchors(codebook.scales["tipi"]["anchors"])
    task = (
        "YOUR TASK\n"
        f'The survey asked this person to rate the statement "I see myself as: '
        f'{tipi_text}" on this scale: {tipi_anchors}.\n\n'
        f"{VARIANT_FINAL_INSTRUCTION[variant]}"
    )
    return f"{INTRO}\n\n{profile}\n\n{task}"
