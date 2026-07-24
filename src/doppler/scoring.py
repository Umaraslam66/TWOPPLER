"""Parsing, scoring, and the paired lift statistics.

Primary metric is **lift** = twin accuracy - baseline accuracy, per person.
Raw twin/baseline accuracies are always carried alongside it. Everything is
computed per person first, then paired across persons (paired t-test + Wilcoxon
signed-rank, 95% t-CI), for both exact match and within-1.
"""

from __future__ import annotations

import re
from statistics import mean

import numpy as np
from scipy import stats

_DIGIT = re.compile(r"\d")


def parse_answer(text: str | None) -> int | None:
    """Strict parse: exactly one digit in 1..7 present, no other digits.

    Accepts "5", " 5 ", "5.", "Answer: 5". Rejects "57", "5 or 6", "", "0",
    "8", "10". Returns the int, or ``None`` if it cannot be parsed cleanly.
    """
    if not text:
        return None
    digits = _DIGIT.findall(text)
    if len(digits) != 1:
        return None
    value = int(digits[0])
    if 1 <= value <= 7:
        return value
    return None


def score(pred: int | None, true: int) -> dict:
    """Per-item scores. A failed parse (``pred is None``) scores as incorrect."""
    if pred is None:
        return {"correct": False, "within1": False, "abs_error": None}
    return {
        "correct": pred == true,
        "within1": abs(pred - true) <= 1,
        "abs_error": abs(pred - true),
    }


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------


def mean_ci(values, conf: float = 0.95) -> dict:
    """Mean and a two-sided t confidence interval."""
    x = np.asarray(list(values), dtype=float)
    n = int(x.size)
    if n == 0:
        return {"mean": float("nan"), "ci_low": float("nan"),
                "ci_high": float("nan"), "n": 0}
    m = float(x.mean())
    if n < 2:
        return {"mean": m, "ci_low": float("nan"), "ci_high": float("nan"), "n": n}
    sem = float(stats.sem(x))
    if sem == 0.0:
        return {"mean": m, "ci_low": m, "ci_high": m, "n": n}
    lo, hi = stats.t.interval(conf, df=n - 1, loc=m, scale=sem)
    return {"mean": m, "ci_low": float(lo), "ci_high": float(hi), "n": n}


def paired_tests(twin, baseline) -> dict:
    """Paired t-test and Wilcoxon signed-rank of twin vs baseline arrays."""
    a = np.asarray(list(twin), dtype=float)
    b = np.asarray(list(baseline), dtype=float)

    if a.size < 2:
        return {"t_stat": float("nan"), "t_p": float("nan"),
                "wilcoxon_stat": float("nan"), "wilcoxon_p": float("nan")}

    t_stat, t_p = stats.ttest_rel(a, b)

    diff = a - b
    if np.allclose(diff, 0.0):
        w_stat, w_p = float("nan"), float("nan")
    else:
        try:
            w_stat, w_p = stats.wilcoxon(a, b)
        except ValueError:
            w_stat, w_p = float("nan"), float("nan")

    return {
        "t_stat": float(t_stat),
        "t_p": float(t_p),
        "wilcoxon_stat": float(w_stat),
        "wilcoxon_p": float(w_p),
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _per_person(records: list[dict]) -> tuple[list[int], dict]:
    """Group records into per-person, per-arm accuracy lists.

    Each record needs: person_id, arm, correct (bool), within1 (bool).
    Returns ``(person_ids_sorted, per_person)`` where ``per_person[pid][arm]``
    is a dict of lists of the item-level correct/within1 flags.
    """
    grouped: dict[int, dict[str, dict[str, list]]] = {}
    for r in records:
        pid = int(r["person_id"])
        arm = r["arm"]
        slot = grouped.setdefault(pid, {})
        arm_slot = slot.setdefault(arm, {"correct": [], "within1": []})
        arm_slot["correct"].append(bool(r["correct"]))
        arm_slot["within1"].append(bool(r["within1"]))
    return sorted(grouped), grouped


def summarize(records: list[dict]) -> dict:
    """Full per-person lift summary for exact match and within-1.

    Only persons that have BOTH arms scored contribute to the paired stats.
    """
    person_ids, grouped = _per_person(records)

    twin_exact, base_exact = [], []
    twin_w1, base_w1 = [], []
    paired_ids = []

    for pid in person_ids:
        arms = grouped[pid]
        if "twin" not in arms or "baseline" not in arms:
            continue
        paired_ids.append(pid)
        twin_exact.append(mean(arms["twin"]["correct"]))
        base_exact.append(mean(arms["baseline"]["correct"]))
        twin_w1.append(mean(arms["twin"]["within1"]))
        base_w1.append(mean(arms["baseline"]["within1"]))

    lift_exact = [t - b for t, b in zip(twin_exact, base_exact)]
    lift_w1 = [t - b for t, b in zip(twin_w1, base_w1)]

    return {
        "n_persons": len(paired_ids),
        "exact": {
            "twin_accuracy": mean_ci(twin_exact),
            "baseline_accuracy": mean_ci(base_exact),
            "lift": mean_ci(lift_exact),
            "tests": paired_tests(twin_exact, base_exact),
        },
        "within1": {
            "twin_accuracy": mean_ci(twin_w1),
            "baseline_accuracy": mean_ci(base_w1),
            "lift": mean_ci(lift_w1),
            "tests": paired_tests(twin_w1, base_w1),
        },
    }
