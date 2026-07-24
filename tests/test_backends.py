"""Backend tests: export determinism, ingest join, round-trip, and proof that
the refactored GeminiBackend path yields byte-identical records. Zero API."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "experiments"))
sys.path.insert(0, str(_ROOT / "src"))
_DATA = _ROOT / "data" / "riasec" / "data.csv"

import run_replay  # noqa: E402
from doppler.backends import (  # noqa: E402
    BackendResult,
    BatchFileBackend,
    GeminiBackend,
)
from doppler.gym import build_tasks  # noqa: E402
from doppler.prompts import VARIANT_MAX_OUTPUT_TOKENS, VARIANT_RETRY_REMINDER  # noqa: E402
from doppler.scoring import parse_response, summarize  # noqa: E402


class _ScriptClient:
    """Returns scripted (text, tokens_in, tokens_out) tuples in order."""

    def __init__(self, script):
        self._script = list(script)
        self.n_calls = 0

    def generate(self, prompt):
        self.n_calls += 1
        return self._script.pop(0)


def _tasks(fake_codebook, record_factory, full_demographics, variant="v0"):
    tasks = []
    for pid in (1, 2):
        rec = record_factory(pid, dict(full_demographics))
        tasks += build_tasks(rec, fake_codebook, "twin", variant=variant)
        tasks += build_tasks(rec, fake_codebook, "baseline", variant=variant)
    return tasks


# --- GeminiBackend is a transparent pass-through --------------------------


def test_gemini_backend_passthrough_and_propagates():
    client = _ScriptClient([("5", 700, 1), ("6", 710, 1)])
    backend = GeminiBackend(client)
    out = backend.batch_generate(["a", "b"], max_output_tokens=16)
    assert out == [BackendResult("5", 700, 1, None), BackendResult("6", 710, 1, None)]

    class _Boom(RuntimeError):
        pass

    class _Raiser:
        def generate(self, prompt):
            raise _Boom("fatal")

    try:
        GeminiBackend(_Raiser()).batch_generate(["x"], max_output_tokens=16)
        assert False, "should have propagated"
    except _Boom:
        pass  # errors propagate unchanged so the runner's abort path still fires


# --- refactored path produces byte-identical records ----------------------


def _reference_run_one(client, task, variant, reminder):
    """Pre-refactor _run_one logic, verbatim, calling client.generate directly."""
    text, t_in, t_out = client.generate(task.prompt)
    pr = parse_response(text, variant)
    raw = text
    parse_retry = False
    if pr["parse_failure"]:
        parse_retry = True
        text2, t_in2, t_out2 = client.generate(task.prompt + "\n\n" + reminder)
        t_in += t_in2
        t_out += t_out2
        raw = text2
        pr = parse_response(text2, variant)
    true = task.true_answer
    disc = pr["prediction_argmax"]
    mae_pt = pr["mae_point"]
    return {
        "person_id": task.person_id, "arm": task.arm, "item": task.tipi_code,
        "variant": variant, "prompt": task.prompt, "raw_response": raw,
        "parsed": pr["parsed"], "prediction_ev": pr["prediction_ev"],
        "prediction_argmax": pr["prediction_argmax"],
        "renorm_offset": pr["renorm_offset"], "true_answer": true,
        "correct": None if disc is None else (disc == true),
        "within1": None if disc is None else (abs(disc - true) <= 1),
        "abs_error": None if mae_pt is None else abs(mae_pt - true),
        "parse_failure": pr["parse_failure"], "parse_retry": parse_retry,
        "tokens_in": t_in, "tokens_out": t_out,
    }


def test_gemini_backend_record_identical_to_prerefactor(
    fake_codebook, record_factory, full_demographics
):
    task = _tasks(fake_codebook, record_factory, full_demographics)[0]
    reminder = VARIANT_RETRY_REMINDER["v0"]
    mot = VARIANT_MAX_OUTPUT_TOKENS["v0"]

    # Happy path.
    ref = _reference_run_one(_ScriptClient([("5", 700, 1)]), task, "v0", reminder)
    new = run_replay._run_one(GeminiBackend(_ScriptClient([("5", 700, 1)])),
                              task, "v0", reminder, mot)
    assert new == ref

    # Parse-failure -> retry path (two generate calls).
    script = [("nope", 700, 3), ("5", 720, 1)]
    ref2 = _reference_run_one(_ScriptClient(list(script)), task, "v0", reminder)
    new2 = run_replay._run_one(GeminiBackend(_ScriptClient(list(script))),
                               task, "v0", reminder, mot)
    assert new2 == ref2
    assert new2["parse_retry"] is True
    assert new2["tokens_in"] == 1420 and new2["parsed"] == 5


# --- BatchFileBackend export / ingest -------------------------------------


def test_export_is_deterministic(tmp_path, fake_codebook, record_factory,
                                 full_demographics):
    tasks = _tasks(fake_codebook, record_factory, full_demographics)
    p1, p2 = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    n1 = BatchFileBackend.export(tasks, "v0", 16, p1)
    n2 = BatchFileBackend.export(tasks, "v0", 16, p2)
    assert n1 == n2 == len(tasks)
    assert p1.read_bytes() == p2.read_bytes()  # byte-identical

    lines = [json.loads(x) for x in p1.read_text().splitlines()]
    assert [ln["idx"] for ln in lines] == list(range(len(tasks)))
    # metadata joins back to the task order
    for ln, t in zip(lines, tasks):
        assert (ln["person_id"], ln["arm"], ln["item"]) == (t.person_id, t.arm,
                                                             t.tipi_code)
        assert ln["prompt"] == t.prompt
        assert ln["variant"] == "v0" and ln["max_output_tokens"] == 16


def test_ingest_join_by_idx(tmp_path, fake_codebook, record_factory,
                            full_demographics):
    tasks = _tasks(fake_codebook, record_factory, full_demographics)
    prompts_path = tmp_path / "prompts.jsonl"
    BatchFileBackend.export(tasks, "v0", 16, prompts_path)

    # Fake completions in SHUFFLED order (join must be by idx, not file order).
    comp_path = tmp_path / "completions.jsonl"
    lines = [{"idx": i, "text": str((i % 7) + 1),
              "gen_meta": {"tokens_in": 100 + i, "tokens_out": 1}}
             for i in range(len(tasks))]
    with comp_path.open("w") as fh:
        for ln in reversed(lines):  # reversed on disk
            fh.write(json.dumps(ln) + "\n")

    backend = BatchFileBackend.from_completions(comp_path)
    results = backend.batch_generate([t.prompt for t in tasks], max_output_tokens=16)
    assert len(results) == len(tasks)
    for i, res in enumerate(results):
        assert res.text == str((i % 7) + 1)
        assert res.tokens_in == 100 + i
        assert res.error is None


def test_ingest_missing_completion_is_error(tmp_path, fake_codebook,
                                            record_factory, full_demographics):
    tasks = _tasks(fake_codebook, record_factory, full_demographics)
    comp_path = tmp_path / "completions.jsonl"
    # Provide completions for all but idx 3.
    with comp_path.open("w") as fh:
        for i in range(len(tasks)):
            if i == 3:
                continue
            fh.write(json.dumps({"idx": i, "text": "4"}) + "\n")

    backend = BatchFileBackend.from_completions(comp_path)
    results = backend.batch_generate([t.prompt for t in tasks], max_output_tokens=16)
    assert results[3].error is not None and results[3].text == ""

    # And the runner's ingest scorer turns that into a parse failure.
    rec = run_replay._score_from_completion(tasks[3], "v0", results[3])
    assert rec["parse_failure"] is True and rec["parsed"] is None
    ok = run_replay._score_from_completion(tasks[0], "v0", results[0])
    assert ok["parse_failure"] is False and ok["parsed"] == 4


@pytest.mark.skipif(not _DATA.exists(), reason="RIASEC data.csv not present")
def test_run_ingest_end_to_end(tmp_path, monkeypatch):
    # Redirect RESULTS_DIR so this never touches the live results/ or cost_log.
    monkeypatch.setattr(run_replay, "RESULTS_DIR", tmp_path)
    tasks, _ids, _cb = run_replay._build_all_tasks("pilot", 48, 42, "v0")

    comp = tmp_path / "completions.jsonl"
    with comp.open("w") as fh:
        for i in range(len(tasks)):
            fh.write(json.dumps({"idx": i, "text": "4",
                                 "gen_meta": {"tokens_in": 50, "tokens_out": 1}}) + "\n")

    outcome = run_replay.run_ingest("pilot", 48, 42, "v0", str(comp), node_hours=2.5)
    assert outcome.exit_code == 0 and outcome.n_calls == 0

    recs = run_replay.read_records(outcome.run_dir / "records.jsonl")
    assert len(recs) == len(tasks)

    summ = json.loads((outcome.run_dir / "summary.json").read_text())
    assert summ["config"]["backend"] == "batchfile"

    cost = (tmp_path / "cost_log.jsonl").read_text().strip().splitlines()
    entry = json.loads(cost[-1])
    assert entry["backend"] == "batchfile"
    assert entry["node_hours"] == 2.5
    assert entry["n_calls"] == 0
    assert entry["cost_usd"] is None  # batch model has no token price


class _FixedBackend:
    """Order-preserving fake backend that answers every prompt with '4'."""

    def batch_generate(self, prompts, *, max_output_tokens):
        return [BackendResult("4", 5, 1, None) for _ in prompts]


def test_execute_concurrent_resume_flow_order_independent(
    tmp_path, fake_codebook, record_factory, full_demographics
):
    tasks = _tasks(fake_codebook, record_factory, full_demographics)  # 40 tasks
    backend = _FixedBackend()
    records_path = tmp_path / "records.jsonl"

    # Partial run across several workers (records land in completion order).
    fh, sink = run_replay._record_sink(records_path)
    try:
        _recs, abort = run_replay._execute(backend, tasks[:15], "v0", sink, workers=4)
    finally:
        fh.close()
    assert abort is None

    # Resume the remainder concurrently; keying is on (person, arm, item).
    done = run_replay.completed_keys(records_path)
    missing = run_replay.filter_missing(tasks, done)
    assert len(missing) == 25
    fh, sink = run_replay._record_sink(records_path)
    try:
        _recs2, abort2 = run_replay._execute(backend, missing, "v0", sink, workers=8)
    finally:
        fh.close()
    assert abort2 is None

    all_records = run_replay.read_records(records_path)
    keys = [(r["person_id"], r["arm"], r["item"]) for r in all_records]
    assert len(keys) == len(set(keys)) == 40
    assert set(keys) == {(t.person_id, t.arm, t.tipi_code) for t in tasks}
    # Completed file scores cleanly regardless of the (completion) order.
    assert summarize(all_records)["n_persons"] == 2


# Variant-distinguishing completion text: each parses under its OWN variant
# parser but NOT (to the same answer) under the others, proving variant-correct
# parsing is applied. idx 0 is deliberately malformed to exercise the exclusion.
_INGEST_TEXT = {
    "v0": ("4", ""),                                   # single int / fail
    "v1": ("Around 3 or 4, so 5", "no digit here"),    # last standalone -> 5
    "v2": ("1:0.0 2:0.0 3:0.0 4:1.0 5:0.0 6:0.0 7:0.0", "garbage"),  # argmax 4
}
_INGEST_EXPECT = {"v0": 4, "v1": 5, "v2": 4}


@pytest.mark.skipif(not _DATA.exists(), reason="RIASEC data.csv not present")
@pytest.mark.parametrize("variant", ["v0", "v1", "v2"])
def test_run_ingest_pilot2_variant_end_to_end(tmp_path, monkeypatch, variant):
    monkeypatch.setattr(run_replay, "RESULTS_DIR", tmp_path)
    tasks, _ids, _cb = run_replay._build_all_tasks("pilot2", 48, 42, variant)
    assert len(tasks) == 1000

    good, bad = _INGEST_TEXT[variant]
    comp = tmp_path / "completions.jsonl"
    with comp.open("w") as fh:
        for i in range(len(tasks)):
            fh.write(json.dumps({"idx": i, "text": bad if i == 0 else good}) + "\n")

    outcome = run_replay.run_ingest("pilot2", 48, 42, variant, str(comp),
                                    node_hours=3.0, backend_name="leonardo-batch")
    assert outcome.exit_code == 0 and outcome.n_calls == 0

    recs = run_replay.read_records(outcome.run_dir / "records.jsonl")
    assert len(recs) == 1000

    # Variant-correct parsing on a well-formed record (idx 1).
    r1 = next(r for r in recs if r["prompt"] == tasks[1].prompt)
    assert r1["parsed"] == _INGEST_EXPECT[variant]
    if variant == "v2":
        assert r1["prediction_ev"] is not None
        assert r1["prediction_argmax"] == r1["parsed"]

    summ = json.loads((outcome.run_dir / "summary.json").read_text())
    assert summ["config"]["backend"] == "leonardo-batch"
    sc = summ["scoring"]
    assert list(k for k in sc if k in ("mae", "within1", "exact", "spearman")) == \
        ["mae", "within1", "exact", "spearman"]
    assert "histograms" in sc and "per_item" in sc
    # idx 0 malformed -> that (person, item) pair excluded from both arms.
    assert summ["totals"]["n_parse_failures"] == 1
    assert sc["n_excluded_pairs"] == 1

    entry = json.loads((tmp_path / "cost_log.jsonl").read_text().strip().splitlines()[-1])
    assert entry["backend"] == "leonardo-batch"
    assert entry["node_hours"] == 3.0
    assert entry["variant"] == variant
