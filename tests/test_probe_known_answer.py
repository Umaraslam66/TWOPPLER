"""Known-answer probe: fold construction and leakage guards.

The probe (PREREGISTRATION_AMENDMENT_1.md A7) deliberately puts five of a
person's own TIPI answers into the prompt, so the gym's blanket "no TIPI in a
profile" guard cannot apply. These tests pin down what must still hold:

  * a predicted item is NEVER in its own seed set,
  * the two fold directions together predict each item exactly once,
  * every predicted item's same-trait partner IS in the seed,
  * no interest item ever enters a probe prompt,
  * the baseline arm is demographics-only (so gate baseline records are reusable).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "experiments"))

from doppler.data import RIASEC_ITEMS, TIPI_ITEMS  # noqa: E402

from probe_known_answer import (  # noqa: E402
    FOLDS,
    TIPI_PAIRS,
    assert_folds_wellformed,
    assert_no_self_leak,
    build_probe_tasks,
    build_seed_block,
    fold_spec,
)


# --- fold construction ----------------------------------------------------


def test_folds_are_wellformed():
    assert_folds_wellformed()


def test_fold_directions_are_five_five_and_disjoint():
    for fold in ("A2B", "B2A"):
        seed, predict = fold_spec(fold)
        assert len(seed) == 5 and len(predict) == 5
        assert not (set(seed) & set(predict))
        assert set(seed) | set(predict) == set(TIPI_ITEMS)


def test_both_directions_cover_each_item_exactly_once():
    predicted = [code for _, predict in FOLDS.values() for code in predict]
    assert sorted(predicted) == sorted(TIPI_ITEMS)
    assert len(predicted) == len(set(predicted)) == 10


def test_every_predicted_item_has_its_trait_pair_in_the_seed():
    partner = {}
    for a, b in TIPI_PAIRS:
        partner[a] = b
        partner[b] = a
    for _, (seed, predict) in FOLDS.items():
        for code in predict:
            assert partner[code] in seed


def test_tipi_pairs_are_the_five_trait_pairs():
    assert TIPI_PAIRS == (
        ("TIPI1", "TIPI6"), ("TIPI2", "TIPI7"), ("TIPI3", "TIPI8"),
        ("TIPI4", "TIPI9"), ("TIPI5", "TIPI10"),
    )


def test_unknown_fold_rejected():
    with pytest.raises(ValueError):
        fold_spec("C2D")


# --- task shape -----------------------------------------------------------


def test_ten_twin_tasks_per_person_one_per_item(synthetic_record, fake_codebook):
    tasks = build_probe_tasks(synthetic_record, fake_codebook, arm="twin")
    assert len(tasks) == 10
    assert sorted(t.tipi_code for t in tasks) == sorted(TIPI_ITEMS)
    assert {t.fold for t in tasks} == {"A2B", "B2A"}
    assert sum(1 for t in tasks if t.fold == "A2B") == 5


def test_true_answers_come_from_the_record(synthetic_record, fake_codebook):
    tasks = build_probe_tasks(synthetic_record, fake_codebook, arm="twin")
    for task in tasks:
        assert task.true_answer == synthetic_record["tipi"][task.tipi_code]["answer"]


# --- leakage --------------------------------------------------------------


def test_predicted_item_never_in_its_own_seed(synthetic_record, fake_codebook):
    tasks = build_probe_tasks(synthetic_record, fake_codebook, arm="twin")
    for task in tasks:
        assert task.tipi_code not in task.seed_codes
        assert fake_codebook.tipi_items[task.tipi_code] not in build_seed_block(
            synthetic_record, fake_codebook, task.seed_codes)


def test_predicted_text_appears_exactly_once_and_answer_not_attached(
    synthetic_record, fake_codebook
):
    tasks = build_probe_tasks(synthetic_record, fake_codebook, arm="twin")
    for task in tasks:
        assert task.prompt.count(task.tipi_text) == 1
        assert f"{task.tipi_text}\" -> {task.true_answer}" not in task.prompt


def test_seed_answers_are_present_and_correct(synthetic_record, fake_codebook):
    tasks = build_probe_tasks(synthetic_record, fake_codebook, arm="twin")
    for task in tasks:
        for code in task.seed_codes:
            text = fake_codebook.tipi_items[code]
            answer = synthetic_record["tipi"][code]["answer"]
            assert f'"I see myself as: {text}" -> {answer}' in task.prompt


def test_no_interest_content_in_probe_prompts(synthetic_record, fake_codebook):
    for arm in ("twin", "baseline"):
        for task in build_probe_tasks(synthetic_record, fake_codebook, arm=arm):
            assert "HOW I RATED MY INTEREST" not in task.prompt
            assert "HOW I FEEL ABOUT" not in task.prompt
            for code in RIASEC_ITEMS:
                assert synthetic_record["interests"][code]["text"] not in task.prompt


def test_baseline_arm_is_demographics_only(synthetic_record, fake_codebook):
    tasks = build_probe_tasks(synthetic_record, fake_codebook, arm="baseline")
    assert len(tasks) == 10
    for task in tasks:
        profile = task.prompt.split("\n\nYOUR TASK")[0]
        assert "HOW I RATED MYSELF" not in profile
        assert "I see myself as" not in profile
        for code in TIPI_ITEMS:
            assert fake_codebook.tipi_items[code] not in profile


def test_baseline_prompts_match_the_gym_baseline_byte_for_byte(
    synthetic_record, fake_codebook
):
    """The reuse argument in one test: our baseline == the gym's baseline arm."""
    from doppler.gym import build_tasks

    gym_tasks = {t.tipi_code: t.prompt
                 for t in build_tasks(synthetic_record, fake_codebook, "baseline",
                                      variant="v2")}
    probe_tasks = build_probe_tasks(synthetic_record, fake_codebook, arm="baseline")
    for task in probe_tasks:
        assert task.prompt == gym_tasks[task.tipi_code]


# --- the guard itself fails loudly ---------------------------------------


def test_self_leak_guard_rejects_item_in_its_own_seed(fake_codebook):
    text = fake_codebook.tipi_items["TIPI3"]
    with pytest.raises(AssertionError):
        assert_no_self_leak(f"...{text}...", ("TIPI3", "TIPI4"), "TIPI3",
                            text, 5, fake_codebook)


def test_self_leak_guard_rejects_repeated_predicted_text(fake_codebook):
    text = fake_codebook.tipi_items["TIPI3"]
    with pytest.raises(AssertionError):
        assert_no_self_leak(f"{text} ... {text}", ("TIPI8",), "TIPI3",
                            text, 5, fake_codebook)


def test_self_leak_guard_rejects_attached_answer(fake_codebook):
    text = fake_codebook.tipi_items["TIPI3"]
    with pytest.raises(AssertionError):
        assert_no_self_leak(f"{text} -> 5", ("TIPI8",), "TIPI3", text, 5,
                            fake_codebook)
