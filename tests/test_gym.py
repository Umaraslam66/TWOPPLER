"""Gym tests: leakage guards, arm symmetry, and the pilot/gate split."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from doppler.data import RIASEC_ITEMS, TIPI_ITEMS
from doppler.gym import (
    GATE_N,
    PILOT2_N,
    PILOT_N,
    build_tasks,
    pilot2_ids,
    pilot_and_gate_ids,
)


# --- leakage --------------------------------------------------------------


def test_twin_prompts_have_no_tipi_leak(synthetic_record, fake_codebook):
    tasks = build_tasks(synthetic_record, fake_codebook, "twin")
    assert len(tasks) == 10
    for task in tasks:
        profile = task.prompt.split("\n\nYOUR TASK")[0]
        # no TIPI item text (any of the 10) appears in the profile
        for code in TIPI_ITEMS:
            assert fake_codebook.tipi_items[code] not in profile
        assert "I see myself as" not in profile
        # the questioned statement appears exactly once (only in YOUR TASK)
        assert task.prompt.count(task.tipi_text) == 1
        # the questioned item's answer is never attached to it
        assert f"{task.tipi_text}: {task.true_answer}" not in task.prompt


def test_baseline_prompts_have_no_interest_leak(synthetic_record, fake_codebook):
    tasks = build_tasks(synthetic_record, fake_codebook, "baseline")
    for task in tasks:
        assert "HOW I RATED" not in task.prompt
        for code in RIASEC_ITEMS:
            assert synthetic_record["interests"][code]["text"] not in task.prompt


def test_true_answers_are_carried_from_record(synthetic_record, fake_codebook):
    tasks = build_tasks(synthetic_record, fake_codebook, "twin")
    by_code = {t.tipi_code: t for t in tasks}
    for code in TIPI_ITEMS:
        assert by_code[code].true_answer == synthetic_record["tipi"][code]["answer"]


def test_leak_guard_fires_when_tipi_text_in_demographics(record_factory, fake_codebook):
    # Force a leak: put a TIPI item text into a demographic value.
    demo = {"gender": "Male", "age": 30, "country": "US",
            "major": fake_codebook.tipi_items["TIPI1"]}
    rec = record_factory(1, demo)
    with pytest.raises(AssertionError):
        build_tasks(rec, fake_codebook, "twin")


# --- pilot / gate split ---------------------------------------------------


@pytest.fixture
def big_df():
    return pd.DataFrame({"person_id": np.arange(2000, dtype=np.int64)})


def test_pilot_gate_sizes_and_disjoint(big_df):
    pilot, gate = pilot_and_gate_ids(big_df)
    assert len(pilot) == PILOT_N == 20
    assert len(gate) == GATE_N == 500
    assert set(pilot).isdisjoint(set(gate))
    assert len(set(pilot) | set(gate)) == 520


def test_pilot_gate_deterministic(big_df):
    p1, g1 = pilot_and_gate_ids(big_df)
    p2, g2 = pilot_and_gate_ids(big_df)
    assert p1 == p2
    assert g1 == g2


def test_pilot2_size_disjoint_deterministic(big_df):
    pilot, gate = pilot_and_gate_ids(big_df)
    p2a = pilot2_ids(big_df)
    p2b = pilot2_ids(big_df)
    assert len(p2a) == PILOT2_N == 50
    assert len(set(p2a)) == 50
    assert set(p2a).isdisjoint(set(pilot))
    assert set(p2a).isdisjoint(set(gate))
    assert p2a == p2b  # deterministic


def test_build_tasks_variant_threads_into_prompt(synthetic_record, fake_codebook):
    for variant, needle in [
        ("v0", "Respond with a single integer from 1 to 7 and nothing else."),
        ("v1", "Then on a new line write only the integer (1-7)."),
        ("v2", "1:0.05 2:0.10 3:0.15 4:0.30 5:0.20 6:0.15 7:0.05"),
    ]:
        tasks = build_tasks(synthetic_record, fake_codebook, "twin", variant=variant)
        assert all(needle in t.prompt for t in tasks)
