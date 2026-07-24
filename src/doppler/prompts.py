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
    if _has(demo.get("familysize")):
        frags.append(
            f"Number of children my parents had, including me: {demo['familysize']}."
        )
    if _has(demo.get("voted")):
        frags.append(f"Voted in a national election in the past year: {demo['voted']}.")
    if _has(demo.get("major")):
        frags.append(f"College major: {demo['major']}.")

    return "MY PROFILE\n" + " ".join(frags)


def _interests_block(record: dict, codebook: Codebook, k: int, seed: int) -> str:
    """The 'HOW I RATED...' block, only ever present in the twin arm."""
    anchors = _format_anchors(codebook.scales["riasec"]["anchors"])
    lines = [
        "HOW I RATED MY INTEREST IN VARIOUS ACTIVITIES",
        f"(Scale: {anchors})",
    ]
    for code in select_interest_items(record["person_id"], k, seed):
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
) -> str:
    """Build a person's profile text. Single function shared by both arms."""
    demo = _demographics_block(record["demographics"])
    if not include_interests:
        return demo
    return demo + "\n\n" + _interests_block(record, codebook, k, seed)


def build_prompt(profile: str, tipi_code: str, codebook: Codebook) -> str:
    """Wrap a profile with the intro line and the held-out TIPI question."""
    tipi_text = codebook.tipi_items[tipi_code]
    tipi_anchors = _format_anchors(codebook.scales["tipi"]["anchors"])
    task = (
        "YOUR TASK\n"
        f'The survey asked this person to rate the statement "I see myself as: '
        f'{tipi_text}" on this scale: {tipi_anchors}.\n\n'
        "Answer as this person would. Respond with a single integer from 1 to 7 "
        "and nothing else."
    )
    return f"{INTRO}\n\n{profile}\n\n{task}"
