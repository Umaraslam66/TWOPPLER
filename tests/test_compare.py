"""Tests for compare_pilot2: label/alias resolution and N-model rendering."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "experiments"))

import compare_pilot2 as cmp  # noqa: E402


# --- label / alias resolution ---------------------------------------------


def test_label_of_gemini():
    assert cmp.label_of({"config": {"backend": None}}) == "gemini"
    assert cmp.label_of({"config": {"backend": "gemini"}}) == "gemini"
    assert cmp.label_of({"config": {}}) == "gemini"


def test_label_of_alias_and_override():
    # Legacy backend name maps through the alias table.
    assert cmp.label_of({"config": {"backend": "leonardo-batch"}}) \
        == "leonardo-qwen3.6-27b"
    # An explicit model_label always wins over the alias.
    assert cmp.label_of(
        {"config": {"backend": "leonardo-batch", "model_label": "leonardo-llama70b"}}
    ) == "leonardo-llama70b"
    # Unknown backend with no alias passes through unchanged.
    assert cmp.label_of({"config": {"backend": "leonardo-gemma27b"}}) \
        == "leonardo-gemma27b"


# --- N-model discovery + rendering ----------------------------------------


def _hist():
    return {arm: {"predicted": {str(i): 1 for i in range(1, 8)},
                  "true": {str(i): 1 for i in range(1, 8)}}
            for arm in ("twin", "baseline")}


def _summary(backend, variant, *, model_label=None, n=1000, mae_lift=0.1):
    block = lambda m: {"lift": {"mean": m, "ci_low": m - 0.05, "ci_high": m + 0.05},
                       "tests": {"t_p": 0.04, "wilcoxon_p": 0.05}}
    return {
        "config": {"split": "pilot2", "k": 48, "seed": 42, "variant": variant,
                   "backend": backend, "model_label": model_label},
        "totals": {"n_records": n, "n_parse_failures": 0},
        "scoring": {
            "mae": block(mae_lift), "within1": block(0.02), "exact": block(0.01),
            "n_excluded_pairs": 0, "histograms": _hist(),
            "per_item": [{"item": f"TIPI{j}", "mae_lift": 0.01 * j}
                         for j in range(1, 11)],
        },
    }


def _make(base: Path, name: str, summary: dict) -> Path:
    d = base / name
    d.mkdir(parents=True)
    (d / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return d


def test_discover_three_models(tmp_path, monkeypatch):
    monkeypatch.setattr(cmp, "RESULTS", tmp_path)
    _make(tmp_path, "pilot2_v0_k48_20260101-000000",
          _summary(None, "v0", mae_lift=0.07))
    _make(tmp_path, "pilot2_v0_k48_20260101-000001_leonardo-batch",
          _summary("leonardo-batch", "v0", mae_lift=-0.09))
    _make(tmp_path, "pilot2_v0_k48_20260101-000002_leonardo-batch",
          _summary("leonardo-batch", "v0", model_label="leonardo-llama70b",
                   mae_lift=0.05))
    _make(tmp_path, "pilot2_v1_k48_20260101-000003",
          _summary("gemini", "v1", n=500))

    runs = cmp.discover()
    assert set(runs) == {
        ("v0", "gemini"), ("v0", "leonardo-qwen3.6-27b"),
        ("v0", "leonardo-llama70b"), ("v1", "gemini"),
    }


def test_build_report_n_models(tmp_path, monkeypatch):
    monkeypatch.setattr(cmp, "RESULTS", tmp_path)
    _make(tmp_path, "pilot2_v0_k48_20260101-000000", _summary(None, "v0"))
    _make(tmp_path, "pilot2_v0_k48_20260101-000001_leonardo-batch",
          _summary("leonardo-batch", "v0"))
    _make(tmp_path, "pilot2_v0_k48_20260101-000002_leonardo-batch",
          _summary("leonardo-batch", "v0", model_label="leonardo-llama70b"))
    _make(tmp_path, "pilot2_v1_k48_20260101-000003", _summary("gemini", "v1", n=500))

    report = cmp.build_report(cmp.discover())

    # gemini first, then the two batch labels; all three variants per model.
    for model in ("gemini", "leonardo-qwen3.6-27b", "leonardo-llama70b"):
        assert f"| {model} | v0 |" in report
        assert f"| {model} | v2 |" in report  # missing -> row still present
    # Missing runs are marked PENDING (e.g. llama v1/v2, gemini v2).
    assert "| leonardo-llama70b | v1 | PENDING" in report
    assert "| gemini | v2 | PENDING" in report
    # Partial gemini v1 is flagged, not called complete.
    assert "partial 500/1000" in report
    # Wide per-item table: a column per present model x variant (gemini first,
    # then the other labels alphabetically; every run with a per-item table).
    assert ("| item | gemini v0 | gemini v1 | leonardo-llama70b v0 | "
            "leonardo-qwen3.6-27b v0 |") in report
    assert "| TIPI1 |" in report
