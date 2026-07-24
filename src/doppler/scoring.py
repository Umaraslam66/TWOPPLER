"""Parsing, scoring, and the paired lift statistics.

Primary metric (v2 of the metric design) is **MAE lift** =
``baseline_MAE - twin_MAE`` per person (positive = twin better). Within-1 lift
is secondary; exact-match lift is still computed but demoted to last. A
per-person Spearman correlation (prediction vs truth) is a diagnostic.

Parse-failure rule (all variants): if either arm fails to parse for a
(person, item), that pair is EXCLUDED from both arms for every metric and
counted in ``n_excluded_pairs``. No default answer is ever substituted.

Three answer formats are parsed by variant:
  * v0 - a single integer 1-7.
  * v1 - a sentence then the integer; take the LAST standalone digit 1-7.
  * v2 - seven ``d:p`` probability pairs; expected value drives MAE, argmax
    drives exact/within-1/histograms.
"""

from __future__ import annotations

import re
import warnings
from statistics import mean

import numpy as np
from scipy import stats

_DIGIT = re.compile(r"\d")
# A standalone digit 1-7 (not part of a longer number).
_STANDALONE_1_7 = re.compile(r"(?<!\d)([1-7])(?!\d)")
# A "key:prob" pair; key is any integer, prob may be signed / bare-decimal.
_PAIR = re.compile(r"(-?\d+)\s*:\s*(-?\d*\.?\d+)")


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def parse_answer(text: str | None) -> int | None:
    """v0 strict parse: exactly one digit in 1..7 present, no other digits."""
    if not text:
        return None
    digits = _DIGIT.findall(text)
    if len(digits) != 1:
        return None
    value = int(digits[0])
    return value if 1 <= value <= 7 else None


def parse_v1(text: str | None) -> int | None:
    """v1 parse: the LAST standalone digit 1-7 in the response (the answer line)."""
    if not text:
        return None
    matches = _STANDALONE_1_7.findall(text)
    if not matches:
        return None
    return int(matches[-1])


def parse_v2(text: str | None) -> dict | None:
    """v2 parse: seven ``d:p`` pairs -> expected value + argmax.

    Returns ``{"ev": float, "argmax": int, "renorm_offset": float}`` on success,
    or ``None`` if malformed (missing/duplicate/extra keys, negative prob, or a
    non-positive sum). Reordering and arbitrary whitespace are tolerated.
    """
    if not text:
        return None
    probs: dict[int, float] = {}
    for key_str, val_str in _PAIR.findall(text):
        key = int(key_str)
        if key in probs:  # duplicate key -> ambiguous
            return None
        probs[key] = float(val_str)
    if set(probs) != set(range(1, 8)):  # missing or extra digits
        return None
    if any(p < 0 for p in probs.values()):  # negative probability
        return None
    total = sum(probs.values())
    if total <= 0:  # non-positive mass
        return None
    renorm_offset = abs(total - 1.0)
    norm = {k: probs[k] / total for k in probs}
    ev = float(sum(k * norm[k] for k in range(1, 8)))
    argmax = int(max(range(1, 8), key=lambda k: probs[k]))
    return {"ev": ev, "argmax": argmax, "renorm_offset": renorm_offset}


def v2_probabilities(text: str | None) -> dict[int, float] | None:
    """Return the normalized ``{1..7: prob}`` vector from a v2 distribution string.

    Same validation as :func:`parse_v2` (malformed -> None). Used for the
    exploratory calibration diagnostic, which needs the full probability vector
    rather than just the expected value / argmax.
    """
    if not text:
        return None
    probs: dict[int, float] = {}
    for key_str, val_str in _PAIR.findall(text):
        key = int(key_str)
        if key in probs:
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


def parse_response(text: str | None, variant: str) -> dict:
    """Unified parse -> discrete prediction, MAE point, EV, argmax, failure flag.

    Keys: ``parsed`` (discrete answer used for exact/within-1/histograms;
    the argmax for v2), ``prediction_ev`` (v2 float / None), ``prediction_argmax``
    (== parsed on success / None on failure), ``mae_point`` (EV for v2 else the
    discrete answer, as float), ``renorm_offset`` (v2 / None), ``parse_failure``.
    """
    fail = {
        "parsed": None,
        "prediction_ev": None,
        "prediction_argmax": None,
        "mae_point": None,
        "renorm_offset": None,
        "parse_failure": True,
    }

    if variant in ("v0", "v3"):
        d = parse_answer(text)
    elif variant == "v1":
        d = parse_v1(text)
    elif variant == "v2":
        parsed = parse_v2(text)
        if parsed is None:
            return fail
        return {
            "parsed": parsed["argmax"],
            "prediction_ev": parsed["ev"],
            "prediction_argmax": parsed["argmax"],
            "mae_point": parsed["ev"],
            "renorm_offset": parsed["renorm_offset"],
            "parse_failure": False,
        }
    else:
        raise ValueError(f"unknown variant {variant!r}")

    if d is None:
        return fail
    return {
        "parsed": d,
        "prediction_ev": None,
        "prediction_argmax": d,
        "mae_point": float(d),
        "renorm_offset": None,
        "parse_failure": False,
    }


def score(pred: int | None, true: int) -> dict:
    """v0 per-item scores (kept for convenience/back-compat)."""
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


def paired_tests(better, worse) -> dict:
    """Paired t-test and Wilcoxon of ``better`` vs ``worse``.

    Pass the arrays so that ``better - worse`` equals the lift being tested.
    """
    a = np.asarray(list(better), dtype=float)
    b = np.asarray(list(worse), dtype=float)
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


def _spearman(pred, true) -> float | None:
    """Spearman rho, or None for constant input (undefined correlation)."""
    if len(pred) < 2:
        return None
    with warnings.catch_warnings():
        # Constant input (e.g. all predictions equal) -> undefined; handled below.
        warnings.simplefilter("ignore")
        rho = stats.spearmanr(pred, true).correlation
    if rho is None or (isinstance(rho, float) and np.isnan(rho)):
        return None
    return float(rho)


# ---------------------------------------------------------------------------
# Record helpers
# ---------------------------------------------------------------------------


def _disc_point(rec: dict):
    """Discrete prediction for exact/within-1/histogram (argmax for v2)."""
    a = rec.get("prediction_argmax")
    if a is not None:
        return int(a)
    p = rec.get("parsed")
    return None if p is None else int(p)


def _mae_point(rec: dict):
    """Continuous point for MAE / Spearman (EV for v2, else the digit)."""
    ev = rec.get("prediction_ev")
    if ev is not None:
        return float(ev)
    p = rec.get("parsed")
    return None if p is None else float(p)


def _metric_block(twin_vals, base_vals, lift_vals, better, worse) -> dict:
    return {
        "twin": mean_ci(twin_vals),
        "baseline": mean_ci(base_vals),
        "lift": mean_ci(lift_vals),
        "tests": paired_tests(better, worse),
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def summarize(records: list[dict]) -> dict:
    """Full per-person summary with the parse-failure exclusion rule applied.

    A (person, item) pair contributes only when BOTH arms are present and
    NEITHER arm is a parse failure. Metric-block order: mae, within1, exact,
    spearman; then histograms and the per-item table.
    """
    by_key: dict[tuple, dict] = {}
    persons: set[int] = set()
    items_by_person: dict[int, set[str]] = {}
    for r in records:
        pid = int(r["person_id"])
        item = r["item"]
        by_key[(pid, r["arm"], item)] = r
        persons.add(pid)
        items_by_person.setdefault(pid, set()).add(item)

    twin_mae, base_mae = [], []
    twin_w1, base_w1 = [], []
    twin_ex, base_ex = [], []
    twin_rho, base_rho = [], []
    n_excluded_pairs = 0
    paired_persons = 0

    # Pooled containers for histograms and the per-item table.
    hist = {arm: {"predicted": {i: 0 for i in range(1, 8)},
                  "true": {i: 0 for i in range(1, 8)}}
            for arm in ("twin", "baseline")}
    per_item_acc: dict[str, dict] = {}

    for pid in sorted(persons):
        inc_true, inc_twin_mae, inc_base_mae = [], [], []
        inc_twin_w1, inc_base_w1, inc_twin_ex, inc_base_ex = [], [], [], []
        inc_twin_pt, inc_base_pt = [], []

        for item in items_by_person[pid]:
            t = by_key.get((pid, "twin", item))
            b = by_key.get((pid, "baseline", item))
            if t is None or b is None:
                continue  # incomplete pair (e.g. partial run) - not scored
            if t.get("parse_failure") or b.get("parse_failure"):
                n_excluded_pairs += 1
                continue

            true = int(t["true_answer"])
            t_disc, b_disc = _disc_point(t), _disc_point(b)
            t_pt, b_pt = _mae_point(t), _mae_point(b)

            inc_true.append(true)
            inc_twin_mae.append(abs(t_pt - true))
            inc_base_mae.append(abs(b_pt - true))
            inc_twin_w1.append(abs(t_disc - true) <= 1)
            inc_base_w1.append(abs(b_disc - true) <= 1)
            inc_twin_ex.append(t_disc == true)
            inc_base_ex.append(b_disc == true)
            inc_twin_pt.append(t_pt)
            inc_base_pt.append(b_pt)

            # Pooled histograms (predicted uses the discrete/argmax answer).
            hist["twin"]["predicted"][t_disc] += 1
            hist["baseline"]["predicted"][b_disc] += 1
            hist["twin"]["true"][true] += 1
            hist["baseline"]["true"][true] += 1

            # Pooled per-item accumulation.
            acc = per_item_acc.setdefault(
                item, {"twin_ae": [], "base_ae": [], "twin_w1": [], "base_w1": []}
            )
            acc["twin_ae"].append(abs(t_pt - true))
            acc["base_ae"].append(abs(b_pt - true))
            acc["twin_w1"].append(abs(t_disc - true) <= 1)
            acc["base_w1"].append(abs(b_disc - true) <= 1)

        if not inc_true:
            continue  # every pair excluded -> person drops out
        paired_persons += 1
        twin_mae.append(mean(inc_twin_mae))
        base_mae.append(mean(inc_base_mae))
        twin_w1.append(mean(inc_twin_w1))
        base_w1.append(mean(inc_base_w1))
        twin_ex.append(mean(inc_twin_ex))
        base_ex.append(mean(inc_base_ex))
        twin_rho.append(_spearman(inc_twin_pt, inc_true))
        base_rho.append(_spearman(inc_base_pt, inc_true))

    lift_mae = [b - t for t, b in zip(twin_mae, base_mae)]     # + = twin better
    lift_w1 = [t - b for t, b in zip(twin_w1, base_w1)]        # + = twin better
    lift_ex = [t - b for t, b in zip(twin_ex, base_ex)]        # + = twin better

    tw_rho = [r for r in twin_rho if r is not None]
    bs_rho = [r for r in base_rho if r is not None]

    per_item = []
    for item in sorted(per_item_acc):
        a = per_item_acc[item]
        tw_mae = mean(a["twin_ae"])
        bs_mae = mean(a["base_ae"])
        per_item.append({
            "item": item,
            "n": len(a["twin_ae"]),
            "twin_mae": tw_mae,
            "baseline_mae": bs_mae,
            "mae_lift": bs_mae - tw_mae,
            "within1_lift": mean(a["twin_w1"]) - mean(a["base_w1"]),
        })

    return {
        "n_persons": paired_persons,
        "n_excluded_pairs": n_excluded_pairs,
        "mae": _metric_block(twin_mae, base_mae, lift_mae, base_mae, twin_mae),
        "within1": _metric_block(twin_w1, base_w1, lift_w1, twin_w1, base_w1),
        "exact": _metric_block(twin_ex, base_ex, lift_ex, twin_ex, base_ex),
        "spearman": {
            "twin_mean": float(mean(tw_rho)) if tw_rho else None,
            "baseline_mean": float(mean(bs_rho)) if bs_rho else None,
            "twin_n_valid": len(tw_rho),
            "baseline_n_valid": len(bs_rho),
            "twin_n_none": sum(1 for r in twin_rho if r is None),
            "baseline_n_none": sum(1 for r in base_rho if r is None),
        },
        "histograms": hist,
        "per_item": per_item,
    }
