"""Tests for gate_report: verdict logic, calibration math, ECE, cost ledger."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "experiments"))
sys.path.insert(0, str(_ROOT / "src"))

import gate_report as gr  # noqa: E402


# --- verdict truth table --------------------------------------------------


def _summ(mean, p):
    block = lambda m: {"lift": {"mean": m, "ci_low": None if m is None else m - 0.05,
                                "ci_high": None if m is None else m + 0.05},
                       "tests": {"t_stat": 2.0, "t_p": p,
                                 "wilcoxon_stat": 1.0, "wilcoxon_p": p}}
    return {"scoring": {"mae": block(mean), "within1": block(0.0),
                        "exact": block(0.0), "n_excluded_pairs": 0,
                        "histograms": {}, "per_item": []},
            "totals": {"n_parse_failures": 0}}


@pytest.mark.parametrize("mean,p,expected", [
    (0.10, 0.01, True),     # positive + significant
    (0.10, 0.049, True),
    (0.10, 0.05, False),    # p not < .05
    (0.10, 0.06, False),
    (-0.10, 0.01, False),   # not positive
    (0.0, 0.01, False),     # zero is not positive
    (0.10, None, False),    # missing p
    (None, 0.01, False),    # missing lift
])
def test_gate_and_promotion_truth_table(mean, p, expected):
    s = _summ(mean, p)
    assert gr.gate_pass(s) is expected
    assert gr.promotion_pass(s) is expected  # identical rule on the secondary


# --- calibration / ECE ----------------------------------------------------


def test_calibration_hand_fixture():
    # A: 0.8 on option 1 (wrong, true=2), 0.2 on option 2 (right).
    # B: 0.8 on option 1 (right, true=1), 0.2 on option 2 (wrong).
    a = ({1: 0.8, 2: 0.2, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0}, 2)
    b = ({1: 0.8, 2: 0.2, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0}, 1)
    cal = gr.calibration([a, b])

    assert cal["n_records"] == 2 and cal["n_pairs"] == 14
    # ECE = (2/14)|0.2-0.5| + (2/14)|0.8-0.5| = (4/14)*0.3
    assert cal["ece"] == pytest.approx(4 / 14 * 0.3)
    assert cal["mean_true_prob"] == pytest.approx(0.5)  # (0.2 + 0.8) / 2
    assert cal["uniform"] == pytest.approx(1 / 7)

    bins = {round(b["lo"], 1): b for b in cal["bins"]}
    assert bins[0.0]["n"] == 10
    assert bins[0.0]["mean_conf"] == pytest.approx(0.0)
    assert bins[0.0]["freq"] == pytest.approx(0.0)
    assert bins[0.2]["n"] == 2
    assert bins[0.2]["mean_conf"] == pytest.approx(0.2)
    assert bins[0.2]["freq"] == pytest.approx(0.5)
    assert bins[0.8]["n"] == 2
    assert bins[0.8]["mean_conf"] == pytest.approx(0.8)
    assert bins[0.8]["freq"] == pytest.approx(0.5)


def test_calibration_perfect_has_zero_ece():
    p1 = ({1: 1.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0}, 1)
    p2 = ({1: 0.0, 2: 0.0, 3: 1.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0}, 3)
    cal = gr.calibration([p1, p2])
    assert cal["ece"] == pytest.approx(0.0)
    assert cal["mean_true_prob"] == pytest.approx(1.0)


def test_v2_calibration_pairs_filters():
    dist = "1:0.7 2:0.05 3:0.05 4:0.05 5:0.05 6:0.05 7:0.05"
    recs = [
        {"arm": "twin", "variant": "v2", "parse_failure": False,
         "raw_response": dist, "true_answer": 1},
        {"arm": "baseline", "variant": "v2", "parse_failure": False,
         "raw_response": dist, "true_answer": 1},         # baseline -> excluded
        {"arm": "twin", "variant": "v2", "parse_failure": True,
         "raw_response": "junk", "true_answer": 2},        # failure -> excluded
        {"arm": "twin", "variant": "v2", "parse_failure": False,
         "raw_response": "not a distribution", "true_answer": 2},  # unparseable
    ]
    pairs = gr.v2_calibration_pairs(recs)
    assert len(pairs) == 1
    probs, true = pairs[0]
    assert true == 1
    assert sum(probs.values()) == pytest.approx(1.0)


# --- cost ledger ----------------------------------------------------------


def test_cost_ledger():
    lines = [
        {"run_id": "gate_A", "backend": "gemini", "n_calls": 10000,
         "cost_usd": 3.0, "node_hours": None},
        {"run_id": "gate_A_leonardo-batch", "backend": "leonardo-batch",
         "n_calls": 0, "cost_usd": None, "node_hours": 0.4},
        {"run_id": "pilot_x", "backend": "gemini", "n_calls": 400,
         "cost_usd": 0.06, "node_hours": None},
    ]
    led = gr.cost_ledger(lines, {"gate_A", "gate_A_leonardo-batch"})
    assert len(led["gate_lines"]) == 2
    assert led["totals"]["gemini_calls"] == 10400
    assert led["totals"]["usd"] == pytest.approx(3.06)
    assert led["totals"]["node_hours"] == pytest.approx(0.4)


# --- end-to-end render ----------------------------------------------------


def _full_summary(mean, p, *, variant="v2", backend=None):
    block = lambda m: {"lift": {"mean": m, "ci_low": m - 0.05, "ci_high": m + 0.05},
                       "tests": {"t_stat": 3.0, "t_p": p,
                                 "wilcoxon_stat": 2.0, "wilcoxon_p": p}}
    hist = {arm: {"predicted": {str(i): 1 for i in range(1, 8)},
                  "true": {str(i): 1 for i in range(1, 8)}}
            for arm in ("twin", "baseline")}
    per_item = [{"item": f"TIPI{j}", "twin_mae": 1.0, "baseline_mae": 1.1,
                 "mae_lift": 0.1} for j in range(1, 11)]
    cfg = {"variant": variant, "n_persons": 500}
    if backend:
        cfg["backend"] = backend
    return {"config": cfg,
            "totals": {"n_parse_failures": 0, "n_records": 10000},
            "scoring": {"mae": block(mean), "within1": block(0.0),
                        "exact": block(0.02), "n_persons": 500,
                        "n_excluded_pairs": 0, "histograms": hist,
                        "per_item": per_item}}


def _write_run(base, name, summary, records=None):
    d = base / name
    d.mkdir()
    (d / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    if records is not None:
        with (d / "records.jsonl").open("w") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
    return d


def test_build_report_pass_and_not_promoted(tmp_path):
    dist = "1:0.6 2:0.1 3:0.1 4:0.05 5:0.05 6:0.05 7:0.05"
    recs = [{"arm": "twin", "variant": "v2", "parse_failure": False,
             "raw_response": dist, "true_answer": 1} for _ in range(3)]
    pri = _write_run(tmp_path, "gate_v2_k48_20260724-181226",
                     _full_summary(0.12, 0.001), records=recs)
    sec = _write_run(tmp_path, "gate_v2_k48_20260724-181226_leonardo-batch",
                     _full_summary(0.05, 0.4, backend="leonardo-batch"))
    cost = tmp_path / "cost_log.jsonl"
    cost.write_text(json.dumps({"run_id": pri.name, "backend": "gemini",
                                "n_calls": 10000, "cost_usd": 3.0,
                                "node_hours": None}) + "\n", encoding="utf-8")

    report = gr.build_report(pri, sec, cost)
    assert "GATE: PASS" in report
    assert "NOT PROMOTED: Gemini stays primary" in report
    assert "EXPLORATORY" in report
    assert "ECE" in report
    assert "total Gemini calls: 10000" in report
    # pre-commitment quoted verbatim.
    assert "becomes the primary" in report


def test_build_report_fail_and_promoted(tmp_path):
    pri = _write_run(tmp_path, "gate_v2_k48_x", _full_summary(-0.01, 0.9))
    sec = _write_run(tmp_path, "gate_v2_k48_x_leonardo-batch",
                     _full_summary(0.09, 0.002, backend="leonardo-batch"))
    cost = tmp_path / "cost_log.jsonl"
    cost.write_text("", encoding="utf-8")

    report = gr.build_report(pri, sec, cost)
    assert "GATE: FAIL" in report
    assert "PROMOTED: Gemma-4+v2 primary for future stages" in report
    # No primary records -> calibration N/A, not a crash.
    assert "Calibration N/A" in report
