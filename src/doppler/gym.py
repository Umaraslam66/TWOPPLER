"""Replay gym: person/arm -> the 10 held-out TIPI prediction tasks.

The gym is where the cross-domain contract is enforced at runtime. Every
profile is checked before it can be turned into prompts:

  * no TIPI item text (any of the 10) appears in a profile,
  * a baseline profile carries no interest text or ratings,
  * the questioned item's recorded answer is never attached to it in the prompt.

These are cheap ``assert`` guards that fail loudly rather than let a leak reach
the model. The scoring only means anything if the twin never saw the answer.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .data import (
    RIASEC_ITEMS,
    TIPI_ITEMS,
    Codebook,
    sample_eval_persons,
)
from .prompts import build_profile, build_prompt

# Frozen person-sampling protocol (PREREGISTRATION + task spec).
PILOT_N = 20
GATE_N = 500
TOTAL_N = PILOT_N + GATE_N  # 520
SAMPLE_SEED = 42

ARMS = ("twin", "baseline")


def pilot_and_gate_ids(df: pd.DataFrame) -> tuple[list[int], list[int]]:
    """Return ``(pilot_ids, gate_ids)`` = first 20 / remaining 500.

    Drawn as one deterministic sample of 520 distinct persons, so the two sets
    are always disjoint and stable across calls.
    """
    ids = sample_eval_persons(df, n=TOTAL_N, seed=SAMPLE_SEED)
    return ids[:PILOT_N], ids[PILOT_N:]


@dataclass(frozen=True)
class Task:
    """One held-out prediction: this person, this arm, this TIPI item."""

    person_id: int
    arm: str
    tipi_code: str
    tipi_text: str
    true_answer: int
    prompt: str


# ---------------------------------------------------------------------------
# Leakage guards
# ---------------------------------------------------------------------------


def _assert_no_tipi_leak(profile: str, codebook: Codebook) -> None:
    for code in TIPI_ITEMS:
        text = codebook.tipi_items[code]
        if text and text in profile:
            raise AssertionError(f"TIPI item text for {code} leaked into a profile")
    if "I see myself as" in profile:
        raise AssertionError("TIPI framing 'I see myself as' leaked into a profile")


def _assert_no_interest_leak(profile: str, record: dict, codebook: Codebook) -> None:
    if "HOW I RATED" in profile:
        raise AssertionError("interest block present in a baseline profile")
    for code in RIASEC_ITEMS:
        text = record["interests"][code]["text"]
        if text and text in profile:
            raise AssertionError(f"interest text for {code} leaked into baseline profile")


def _assert_answer_not_leaked(prompt: str, tipi_text: str, true_answer: int) -> None:
    # The questioned statement appears exactly once (in YOUR TASK), never in the
    # profile, and its recorded answer is never attached to it.
    if prompt.count(tipi_text) != 1:
        raise AssertionError("questioned TIPI text does not appear exactly once")
    if f"{tipi_text}: {true_answer}" in prompt:
        raise AssertionError("questioned item's answer is attached to it in the prompt")


# ---------------------------------------------------------------------------
# Task construction
# ---------------------------------------------------------------------------


def build_tasks(
    record: dict,
    codebook: Codebook,
    arm: str,
    k: int = 48,
    seed: int = 42,
) -> list[Task]:
    """Build all 10 TIPI prediction tasks for one person under one arm."""
    if arm not in ARMS:
        raise ValueError(f"arm must be one of {ARMS}, got {arm!r}")

    include_interests = arm == "twin"
    profile = build_profile(record, codebook, include_interests, k=k, seed=seed)

    _assert_no_tipi_leak(profile, codebook)
    if arm == "baseline":
        _assert_no_interest_leak(profile, record, codebook)

    tasks: list[Task] = []
    for code in TIPI_ITEMS:
        prompt = build_prompt(profile, code, codebook)
        tipi_text = codebook.tipi_items[code]
        true_answer = int(record["tipi"][code]["answer"])
        _assert_answer_not_leaked(prompt, tipi_text, true_answer)
        tasks.append(
            Task(
                person_id=int(record["person_id"]),
                arm=arm,
                tipi_code=code,
                tipi_text=tipi_text,
                true_answer=true_answer,
                prompt=prompt,
            )
        )
    return tasks
