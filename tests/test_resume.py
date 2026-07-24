"""Resume skip-logic tests for the runner. Mocked client -> zero API calls."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "experiments"))
sys.path.insert(0, str(_ROOT / "src"))

import run_replay  # noqa: E402
from doppler.backends import GeminiBackend  # noqa: E402
from doppler.gym import build_tasks  # noqa: E402
from doppler.prompts import VARIANT_MAX_OUTPUT_TOKENS, VARIANT_RETRY_REMINDER  # noqa: E402
from doppler.scoring import summarize  # noqa: E402


class _FakeClient:
    """Stand-in for GeminiClient: no network, records how many calls it took."""

    def __init__(self, answer: str = "4"):
        self.answer = answer
        self.n_calls = 0
        self.n_retries = 0

    def generate(self, prompt: str):
        self.n_calls += 1
        return self.answer, 10, 1


def _run(fake, task, variant="v0"):
    return run_replay._run_one(
        GeminiBackend(fake), task, variant,
        VARIANT_RETRY_REMINDER[variant], VARIANT_MAX_OUTPUT_TOKENS[variant],
    )


def _write(records_path, records):
    fh, sink = run_replay._record_sink(records_path)
    try:
        for r in records:
            sink(r)
    finally:
        fh.close()


def _all_tasks(fake_codebook, record_factory, full_demographics):
    tasks = []
    for pid in (1, 2):
        rec = record_factory(pid, dict(full_demographics))
        tasks += build_tasks(rec, fake_codebook, "twin")
        tasks += build_tasks(rec, fake_codebook, "baseline")
    return tasks


def test_filter_missing_returns_only_the_gap(
    tmp_path, fake_codebook, record_factory, full_demographics
):
    tasks = _all_tasks(fake_codebook, record_factory, full_demographics)
    assert len(tasks) == 40  # 2 persons x 10 items x 2 arms

    fake = _FakeClient("5")
    records_path = tmp_path / "records.jsonl"
    _write(records_path, [_run(fake, t) for t in tasks[:15]])

    done = run_replay.completed_keys(records_path)
    assert len(done) == 15

    missing = run_replay.filter_missing(tasks, done)
    assert len(missing) == 25

    missing_keys = {(t.person_id, t.arm, t.tipi_code) for t in missing}
    all_keys = {(t.person_id, t.arm, t.tipi_code) for t in tasks}
    assert missing_keys.isdisjoint(done)
    assert missing_keys | done == all_keys


def test_resume_appends_and_scores(
    tmp_path, fake_codebook, record_factory, full_demographics
):
    tasks = _all_tasks(fake_codebook, record_factory, full_demographics)
    fake = _FakeClient("4")
    records_path = tmp_path / "records.jsonl"

    # Partial run: first 15 tasks completed and written.
    _write(records_path, [_run(fake, t) for t in tasks[:15]])

    # Resume: plan the missing tasks, run them, append to the SAME file.
    done = run_replay.completed_keys(records_path)
    missing = run_replay.filter_missing(tasks, done)
    _write(records_path, [_run(fake, t) for t in missing])

    all_records = run_replay.read_records(records_path)
    assert len(all_records) == 40

    # No (person, arm, item) is duplicated across the appended file.
    keys = [(r["person_id"], r["arm"], r["item"]) for r in all_records]
    assert len(keys) == len(set(keys)) == 40

    # The completed file scores cleanly: both persons have both arms.
    out = summarize(all_records)
    assert out["n_persons"] == 2

    # The fake client only ever ran total-task-count calls (no re-doing done work).
    assert fake.n_calls == 40


def test_resume_config_recovers_variant_from_run_id(tmp_path):
    # No summary.json -> split/k/variant recovered from the directory name.
    run_dir = tmp_path / "pilot2_v2_k48_20260101-000000"
    run_dir.mkdir()
    split, k, seed, variant = run_replay._resume_config(run_dir, run_dir.name)
    assert (split, k, seed, variant) == ("pilot2", 48, run_replay.DEFAULT_SEED, "v2")


def test_resume_config_legacy_v0_name(tmp_path):
    run_dir = tmp_path / "gate_k12_20260101-000000"
    run_dir.mkdir()
    split, k, seed, variant = run_replay._resume_config(run_dir, run_dir.name)
    assert (split, k, seed, variant) == ("gate", 12, run_replay.DEFAULT_SEED, "v0")
