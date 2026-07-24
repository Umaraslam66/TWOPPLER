"""Scoring tests: strict parser + the per-person lift statistics."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from doppler.scoring import parse_answer, score, summarize


# --- parser ---------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("5", 5),
        (" 5 ", 5),
        ("5.", 5),
        ("Answer: 5", 5),
        ("1", 1),
        ("7", 7),
    ],
)
def test_parser_happy(text, expected):
    assert parse_answer(text) == expected


@pytest.mark.parametrize(
    "text",
    ["57", "I'd say 5 or 6", "", "0", "8", "10", None, "no answer", "3.5"],
)
def test_parser_rejects(text):
    assert parse_answer(text) is None


def test_score_parse_failure_is_incorrect():
    sc = score(None, 5)
    assert sc == {"correct": False, "within1": False, "abs_error": None}


def test_score_exact_and_within1():
    assert score(5, 5) == {"correct": True, "within1": True, "abs_error": 0}
    assert score(4, 5) == {"correct": False, "within1": True, "abs_error": 1}
    assert score(2, 5) == {"correct": False, "within1": False, "abs_error": 3}


# --- aggregate statistics -------------------------------------------------


def _person_records(pid, arm, n_correct, n_within1):
    """10 item records for one (person, arm); correct subset of within1."""
    assert n_correct <= n_within1 <= 10
    recs = []
    for i in range(10):
        correct = i < n_correct
        within1 = i < n_within1
        recs.append({"person_id": pid, "arm": arm,
                     "correct": correct, "within1": within1})
    return recs


def test_summarize_known_lift_and_ci():
    twin_correct = [6, 7, 8, 5, 9]
    base_correct = [5, 5, 5, 5, 5]
    records = []
    for pid, (tc, bc) in enumerate(zip(twin_correct, base_correct)):
        records += _person_records(pid, "twin", tc, tc)       # within1 == correct here
        records += _person_records(pid, "baseline", bc, bc)

    out = summarize(records)
    assert out["n_persons"] == 5

    ex = out["exact"]
    assert ex["twin_accuracy"]["mean"] == pytest.approx(0.70)
    assert ex["baseline_accuracy"]["mean"] == pytest.approx(0.50)
    assert ex["lift"]["mean"] == pytest.approx(0.20)

    # CI matches an independent scipy computation on the lift vector.
    lift = np.array([0.1, 0.2, 0.3, 0.0, 0.4])
    lo, hi = stats.t.interval(0.95, df=4, loc=lift.mean(), scale=stats.sem(lift))
    assert ex["lift"]["ci_low"] == pytest.approx(lo)
    assert ex["lift"]["ci_high"] == pytest.approx(hi)

    # paired t-test matches scipy on the raw twin/baseline vectors.
    tw = np.array([0.6, 0.7, 0.8, 0.5, 0.9])
    bs = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
    _, p = stats.ttest_rel(tw, bs)
    assert ex["tests"]["t_p"] == pytest.approx(p)


def test_summarize_only_pairs_complete_persons():
    # person 0 has both arms; person 1 has only twin -> excluded from pairing.
    records = _person_records(0, "twin", 8, 9) + _person_records(0, "baseline", 5, 6)
    records += _person_records(1, "twin", 10, 10)
    out = summarize(records)
    assert out["n_persons"] == 1
