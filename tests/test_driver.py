"""Driver planning tests for run_pilot2: skip complete, resume partial, start
fresh, and stop on abort. run_fresh/run_resume are mocked -> zero API calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "experiments"))
sys.path.insert(0, str(_ROOT / "src"))

import run_pilot2  # noqa: E402
from run_replay import RunOutcome  # noqa: E402


def _write_dir(base: Path, name: str, n_records: int) -> Path:
    d = base / name
    d.mkdir(parents=True)
    recs = [
        {"person_id": i // 2, "arm": "twin" if i % 2 else "baseline",
         "item": f"TIPI{i}"}
        for i in range(n_records)
    ]
    (d / "records.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8"
    )
    return d


def test_existing_run_picks_most_progressed(tmp_path, monkeypatch):
    monkeypatch.setattr(run_pilot2, "RESULTS_DIR", tmp_path)
    _write_dir(tmp_path, "pilot2_v0_k48_20260101-000000", 2)
    best = _write_dir(tmp_path, "pilot2_v0_k48_20260102-000000", 3)
    run_dir, count = run_pilot2._existing_run("v0")
    assert run_dir == best
    assert count == 3


def test_existing_run_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(run_pilot2, "RESULTS_DIR", tmp_path)
    run_dir, count = run_pilot2._existing_run("v1")
    assert run_dir is None and count == 0


def _add_summary(d, config):
    (d / "summary.json").write_text(json.dumps({"config": config}), encoding="utf-8")


def test_existing_run_ignores_batch_ingest_decoy(tmp_path, monkeypatch):
    # A COMPLETE leonardo-batch ingest dir matches the variant glob but is NOT a
    # Gemini run, so it must not be mistaken for "Gemini v2 already complete".
    monkeypatch.setattr(run_pilot2, "RESULTS_DIR", tmp_path)
    decoy = _write_dir(tmp_path, "pilot2_v2_k48_20260101-000000_leonardo-batch", 4)
    _add_summary(decoy, {"backend": "leonardo-batch", "model_label": None})
    run_dir, count = run_pilot2._existing_run("v2")
    assert run_dir is None and count == 0


def test_existing_run_prefers_gemini_over_batch(tmp_path, monkeypatch):
    monkeypatch.setattr(run_pilot2, "RESULTS_DIR", tmp_path)
    gem = _write_dir(tmp_path, "pilot2_v2_k48_20260101-000001", 4)
    _add_summary(gem, {"backend": None, "model_label": None})
    batch = _write_dir(tmp_path, "pilot2_v2_k48_20260101-000002_leonardo-batch", 4)
    _add_summary(batch, {"backend": "leonardo-batch"})
    run_dir, count = run_pilot2._existing_run("v2")
    assert run_dir == gem and count == 4


def test_driver_skips_complete_resumes_partial_starts_fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(run_pilot2, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(run_pilot2, "EXPECTED_RECORDS", 4)

    _write_dir(tmp_path, "pilot2_v0_k48_20260101-000000", 4)   # complete -> skip
    v1_dir = _write_dir(tmp_path, "pilot2_v1_k48_20260101-000000", 2)  # partial -> resume

    calls = []

    def fake_fresh(split, k, seed, variant, max_calls):
        calls.append(("fresh", variant, max_calls))
        return RunOutcome(0, tmp_path / f"pilot2_{variant}_k48_new", 100, True)

    def fake_resume(run_dir, max_calls):
        calls.append(("resume", Path(run_dir).name, max_calls))
        return RunOutcome(0, Path(run_dir), 50, True)

    monkeypatch.setattr(run_pilot2, "run_fresh", fake_fresh)
    monkeypatch.setattr(run_pilot2, "run_resume", fake_resume)

    rc = run_pilot2.main()
    assert rc == 0
    assert calls[0] == ("resume", v1_dir.name, run_pilot2.BUDGET)         # v1 partial
    assert calls[1][0] == "fresh" and calls[1][1] == "v2"                 # v2 fresh
    # v0 was skipped (never invoked); budget decremented across the two runs.
    assert calls[1][2] == run_pilot2.BUDGET - 50


def test_driver_stops_on_abort(tmp_path, monkeypatch):
    monkeypatch.setattr(run_pilot2, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(run_pilot2, "EXPECTED_RECORDS", 4)

    calls = []

    def fake_fresh(split, k, seed, variant, max_calls):
        calls.append(variant)
        # v0 aborts (e.g. dead quota): incomplete.
        return RunOutcome(3, tmp_path / "d", 30, False)

    monkeypatch.setattr(run_pilot2, "run_fresh", fake_fresh)
    monkeypatch.setattr(run_pilot2, "run_resume", fake_fresh)

    rc = run_pilot2.main()
    assert rc == 1
    assert calls == ["v0"]  # stopped; did not start v1/v2
