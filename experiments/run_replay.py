"""Stage-1 replay gym runner.

Predicts each of a person's 10 held-out TIPI items from (a) demographics +
interests (twin) and (b) demographics only (baseline), one API call per
(person, item, arm). A run-level ``variant`` (v0/v1/v2) changes only the final
instruction and the answer format; it is applied identically to both arms.

Records are appended to records.jsonl as each call completes, so a hard kill
loses at most the in-flight call and the run can be resumed.

Usage:
    uv run python experiments/run_replay.py --split pilot2 --variant v1
    uv run python experiments/run_replay.py --split pilot2 --variant v2 --dry-run
    uv run python experiments/run_replay.py --resume results/<run_id>

Writes to ``results/<run_id>/`` where ``run_id`` is
``{split}_k{k}_{ts}`` for v0 pilot/gate, else ``{split}_{variant}_k{k}_{ts}``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from doppler.backends import BatchFileBackend, GeminiBackend  # noqa: E402
from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402
from doppler.data import (  # noqa: E402
    clean_riasec,
    load_codebook,
    load_riasec,
    person_record,
)
from doppler.gemini import CallCapExceeded, GeminiClient  # noqa: E402
from doppler.gym import build_tasks, pilot2_ids, pilot_and_gate_ids  # noqa: E402
from doppler.prompts import (  # noqa: E402
    VARIANT_MAX_OUTPUT_TOKENS,
    VARIANT_RETRY_REMINDER,
    VARIANTS,
)
from doppler.scoring import parse_response, summarize  # noqa: E402

DATA_DIR = _ROOT / "data"
RESULTS_DIR = _ROOT / "results"
# One worker: the key is on a ~15 requests/minute free tier, so throughput is
# gated entirely by the client's request pacer. Extra threads only cause 429s.
MAX_WORKERS = 1
DEFAULT_SEED = 42
# Retry headroom above the number of planned calls, for the self-sizing cap used
# by standalone runs (the pilot2 driver passes its own shared budget instead).
DEFAULT_HEADROOM = 400


def _default_cap(n_planned: int) -> int:
    """A hard call cap that comfortably covers ``n_planned`` calls plus retries."""
    return n_planned + max(DEFAULT_HEADROOM, n_planned // 2)


@dataclass
class RunOutcome:
    """Result of a fresh or resumed run, for the driver to sequence on."""

    exit_code: int          # 0 ok, 2 fatal setup, 3 aborted (quota/cap/error)
    run_dir: Path | None
    n_calls: int
    complete: bool          # all tasks attempted (no abort)


# ---------------------------------------------------------------------------
# Setup / run-id
# ---------------------------------------------------------------------------


def make_run_id(split: str, k: int, variant: str, timestamp: str) -> str:
    """v0 pilot/gate keep the legacy name; everything else carries the variant."""
    if split != "pilot2" and variant == "v0":
        return f"{split}_k{k}_{timestamp}"
    return f"{split}_{variant}_k{k}_{timestamp}"


def _person_ids(df, split: str) -> list[int]:
    pilot_ids, gate_ids = pilot_and_gate_ids(df)
    if split == "pilot":
        return pilot_ids
    if split == "gate":
        return gate_ids
    if split == "pilot2":
        return pilot2_ids(df)
    raise ValueError(f"unknown split {split!r}")


def _build_all_tasks(split: str, k: int, seed: int, variant: str):
    """Load data and build both-arm tasks for every person in the split."""
    df = clean_riasec(load_riasec(DATA_DIR))
    codebook = load_codebook(DATA_DIR)
    ids = _person_ids(df, split)

    by_id = df.set_index("person_id", drop=False)
    tasks = []
    for pid in ids:
        record = person_record(by_id.loc[pid], codebook)
        tasks.extend(build_tasks(record, codebook, "twin", k=k, seed=seed,
                                 variant=variant))
        tasks.extend(build_tasks(record, codebook, "baseline", k=k, seed=seed,
                                 variant=variant))
    return tasks, ids, codebook


# ---------------------------------------------------------------------------
# Records I/O
# ---------------------------------------------------------------------------


def read_records(records_path: Path) -> list[dict]:
    """Load every JSON-line record from a run's records.jsonl (order preserved)."""
    records: list[dict] = []
    with Path(records_path).open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def completed_keys(records_path: Path) -> set[tuple[int, str, str]]:
    """The set of (person_id, arm, item) already present in records.jsonl."""
    return {
        (int(r["person_id"]), r["arm"], r["item"])
        for r in read_records(records_path)
    }


def filter_missing(tasks, completed: set[tuple[int, str, str]]) -> list:
    """Tasks whose (person_id, arm, item) is not yet in ``completed``."""
    return [t for t in tasks if (t.person_id, t.arm, t.tipi_code) not in completed]


def _resume_config(outdir: Path, run_id: str) -> tuple[str, int, int, str]:
    """Recover (split, k, seed, variant) for a resume, from summary.json then run_id."""
    summary_path = outdir / "summary.json"
    if summary_path.exists():
        try:
            cfg = json.loads(summary_path.read_text(encoding="utf-8")).get("config", {})
            if (cfg.get("split") and cfg.get("k") is not None
                    and cfg.get("seed") is not None):
                return (cfg["split"], int(cfg["k"]), int(cfg["seed"]),
                        cfg.get("variant", "v0"))
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            pass
    m = re.match(r"(pilot2|pilot|gate)_(?:(v\d)_)?k(\d+)_", run_id)
    if not m:
        raise SystemExit(
            f"[fatal] cannot infer split/k from run_id {run_id!r} and no usable "
            "summary.json; cannot resume."
        )
    return m.group(1), int(m.group(3)), DEFAULT_SEED, (m.group(2) or "v0")


def _write_example_prompts(outdir: Path, tasks) -> None:
    """One full twin prompt and one full baseline prompt, verbatim as sent."""
    twin = next(t for t in tasks if t.arm == "twin")
    baseline = next(
        t for t in tasks if t.arm == "baseline" and t.person_id == twin.person_id
        and t.tipi_code == twin.tipi_code
    )
    (outdir / "example_prompt_twin.txt").write_text(twin.prompt, encoding="utf-8")
    (outdir / "example_prompt_baseline.txt").write_text(baseline.prompt, encoding="utf-8")


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _record_from_parse(task, variant, prompt, raw, pr, parse_retry,
                        t_in, t_out) -> dict:
    """Assemble one record dict from a parse result (shared by live/ingest)."""
    true = task.true_answer
    disc = pr["prediction_argmax"]
    mae_pt = pr["mae_point"]
    return {
        "person_id": task.person_id,
        "arm": task.arm,
        "item": task.tipi_code,
        "variant": variant,
        "prompt": prompt,
        "raw_response": raw,
        "parsed": pr["parsed"],
        "prediction_ev": pr["prediction_ev"],
        "prediction_argmax": pr["prediction_argmax"],
        "renorm_offset": pr["renorm_offset"],
        "true_answer": true,
        "correct": None if disc is None else (disc == true),
        "within1": None if disc is None else (abs(disc - true) <= 1),
        "abs_error": None if mae_pt is None else abs(mae_pt - true),
        "parse_failure": pr["parse_failure"],
        "parse_retry": parse_retry,
        "tokens_in": t_in,
        "tokens_out": t_out,
    }


def _run_one(backend, task, variant: str, retry_reminder: str,
             max_output_tokens: int) -> dict:
    """One prediction: generate, parse per variant, one parse-retry if needed.

    Routed through ``backend.batch_generate`` (single-prompt batches). For the
    Gemini backend this is exactly the previous two-``generate`` sequence, so
    the produced record is byte-identical.
    """
    res = backend.batch_generate([task.prompt], max_output_tokens=max_output_tokens)[0]
    text, t_in, t_out = res.text, res.tokens_in, res.tokens_out
    pr = parse_response(text, variant)
    raw = text
    parse_retry = False

    if pr["parse_failure"]:
        parse_retry = True
        retry_prompt = task.prompt + "\n\n" + retry_reminder
        res2 = backend.batch_generate([retry_prompt],
                                      max_output_tokens=max_output_tokens)[0]
        t_in += res2.tokens_in
        t_out += res2.tokens_out
        raw = res2.text
        pr = parse_response(res2.text, variant)

    return _record_from_parse(task, variant, task.prompt, raw, pr, parse_retry,
                              t_in, t_out)


def _score_from_completion(task, variant: str, res) -> dict:
    """Build a record from a pre-computed completion (ingest path, no retry)."""
    if res.error is not None:
        pr = parse_response("", variant)  # -> parse_failure
        raw = f"<no completion: {res.error}>"
    else:
        pr = parse_response(res.text, variant)
        raw = res.text
    return _record_from_parse(task, variant, task.prompt, raw, pr, False,
                              res.tokens_in, res.tokens_out)


def _execute(backend, tasks, variant: str, sink) -> tuple[list[dict], str | None]:
    """Run tasks; ``sink(record)`` is called (and durably persists) per result."""
    reminder = VARIANT_RETRY_REMINDER[variant]
    max_tok = VARIANT_MAX_OUTPUT_TOKENS[variant]
    records: list[dict] = []
    abort_reason: str | None = None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_run_one, backend, t, variant, reminder, max_tok): t
                   for t in tasks}
        try:
            for fut in tqdm(as_completed(futures), total=len(futures), desc="calls"):
                rec = fut.result()
                records.append(rec)
                sink(rec)
        except CallCapExceeded as exc:
            abort_reason = f"CallCapExceeded: {exc}"
        except Exception as exc:  # noqa: BLE001 - fatal API error; stop cleanly
            abort_reason = f"{type(exc).__name__}: {_redact(str(exc))}"
        finally:
            if abort_reason is not None:
                for fut in futures:
                    fut.cancel()

    return records, abort_reason


def _record_sink(records_path: Path):
    """Return (file_handle, sink) that appends+flushes each record durably."""
    fh = Path(records_path).open("a", encoding="utf-8")
    lock = threading.Lock()

    def sink(rec: dict) -> None:
        with lock:
            fh.write(json.dumps(rec) + "\n")
            fh.flush()

    return fh, sink


def _redact(message: str) -> str:
    """Strip the API key from any message before it is printed/written."""
    key = os.environ.get("GOOGLE_AI_STUDIO")
    if key and key in message:
        message = message.replace(key, "<REDACTED_API_KEY>")
    return message


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _write_human_review(outdir: Path, records: list[dict], codebook) -> None:
    """10 distinct persons, twin arm: profile, question, prediction, true, baseline."""
    lookup = {(r["person_id"], r["arm"], r["item"]): r for r in records}
    seen: dict[int, dict] = {}
    for r in records:
        if r["arm"] == "twin":
            seen.setdefault(r["person_id"], r)
    examples = list(seen.values())[:10]

    lines = ["# Human review - 10 twin-arm examples", ""]
    for i, r in enumerate(examples, 1):
        pid, item = r["person_id"], r["item"]
        base = lookup.get((pid, "baseline", item))
        tipi_text = codebook.tipi_items.get(item, item)
        profile = r["prompt"].split("\n\nYOUR TASK")[0]
        ev = r.get("prediction_ev")
        ev_str = f" (EV {ev:.2f})" if ev is not None else ""
        lines += [
            f"## Example {i} - person {pid}, item {item} (variant {r.get('variant','v0')})",
            "",
            "**Seed profile (twin):**",
            "",
            "```",
            profile,
            "```",
            "",
            f'**Held-out question:** "I see myself as: {tipi_text}"',
            "",
            f"- Twin prediction: {r['parsed']}{ev_str}"
            + (" (parse failure)" if r["parse_failure"] else ""),
            f"- True answer: {r['true_answer']}",
            f"- Baseline prediction for same item: "
            f"{base['parsed'] if base else 'n/a'}",
            "",
        ]
    (outdir / "human_review.md").write_text("\n".join(lines), encoding="utf-8")


def _write_summary(outdir: Path, records: list[dict], config: dict,
                   process_totals: dict, abort_reason: str | None) -> dict:
    """Score ALL ``records`` and write summary.json (scoring over the full file)."""
    totals = {
        "n_records": len(records),
        "n_parse_failures": sum(1 for r in records if r["parse_failure"]),
        "tokens_in": sum(r["tokens_in"] for r in records),
        "tokens_out": sum(r["tokens_out"] for r in records),
    }
    totals.update(process_totals)
    summary = {
        "config": config,
        "scoring": summarize(records),
        "totals": totals,
        "aborted": abort_reason,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2),
                                         encoding="utf-8")
    return summary


def _print_scores(prefix: str, run_id: str, summary: dict, n_calls: int) -> None:
    sc = summary["scoring"]
    mae, w1, ex = sc["mae"], sc["within1"], sc["exact"]
    print(f"{prefix} {run_id}: {n_calls} calls, "
          f"{summary['totals']['n_parse_failures']} parse failures, "
          f"{sc['n_excluded_pairs']} excluded pairs")
    print(f"{prefix} MAE twin={mae['twin']['mean']:.3f} "
          f"base={mae['baseline']['mean']:.3f} "
          f"MAE-lift={mae['lift']['mean']:+.3f} (t p={mae['tests']['t_p']:.4g})")
    print(f"{prefix} within1-lift={w1['lift']['mean']:+.3f} "
          f"exact-lift={ex['lift']['mean']:+.3f}")


# ---------------------------------------------------------------------------
# Fresh / resume runs
# ---------------------------------------------------------------------------


def _make_client(max_calls: int, variant: str) -> GeminiClient:
    return GeminiClient(max_calls=max_calls,
                        max_output_tokens=VARIANT_MAX_OUTPUT_TOKENS[variant])


def run_fresh(split: str, k: int, seed: int, variant: str,
              dry_run: bool = False, max_calls: int | None = None) -> RunOutcome:
    """Start a brand-new run for (split, k, seed, variant).

    ``max_calls`` caps total API requests; when None it self-sizes to the
    planned call count plus retry headroom. The driver passes its shared budget.
    """
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}, got {variant!r}")

    tasks, ids, codebook = _build_all_tasks(split, k, seed, variant)
    cap = max_calls if max_calls is not None else _default_cap(len(tasks))
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = make_run_id(split, k, variant, timestamp)
    outdir = RESULTS_DIR / run_id
    outdir.mkdir(parents=True, exist_ok=True)

    _write_example_prompts(outdir, tasks)
    mean_chars = sum(len(t.prompt) for t in tasks) / len(tasks)
    config = {"split": split, "k": k, "seed": seed, "variant": variant,
              "n_persons": len(ids), "model": None}

    if dry_run:
        manifest = {"run_id": run_id, "split": split, "k": k, "seed": seed,
                    "variant": variant, "n_persons": len(ids),
                    "planned_calls": len(tasks),
                    "mean_prompt_chars": round(mean_chars, 1)}
        (outdir / "dry_run_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"[dry-run] {run_id}: {len(tasks)} planned calls, "
              f"mean prompt {mean_chars:.0f} chars. No API calls made.")
        print(f"[dry-run] wrote example prompts + manifest to {outdir}")
        return RunOutcome(0, outdir, 0, True)

    try:
        client = _make_client(cap, variant)
    except Exception as exc:  # noqa: BLE001
        print(f"[fatal] could not init client: {type(exc).__name__}: "
              f"{_redact(str(exc))}", file=sys.stderr)
        return RunOutcome(2, outdir, 0, False)

    config["model"] = client.model_name
    print(f"[run] {run_id}: {len(tasks)} planned calls (cap {cap}), "
          f"model={client.model_name}, variant={variant}, workers={MAX_WORKERS}")

    fh, sink = _record_sink(outdir / "records.jsonl")
    try:
        records, abort_reason = _execute(GeminiBackend(client), tasks, variant, sink)
    finally:
        fh.close()

    all_records = read_records(outdir / "records.jsonl")
    n_parse_retries = sum(1 for r in records if r["parse_retry"])
    process_totals = {
        "n_calls": client.n_calls,
        "n_backoff_retries": client.n_retries,
        "n_parse_retries": n_parse_retries,
        "n_retries_total": client.n_retries + n_parse_retries,
    }
    summary = _write_summary(outdir, all_records, config, process_totals, abort_reason)
    _write_human_review(outdir, all_records, codebook)

    append_cost_log(build_cost_entry(
        run_id=run_id, model=client.model_name, split=split, variant=variant,
        n_persons=len(ids), n_calls=client.n_calls,
        n_retries=process_totals["n_retries_total"],
        n_parse_failures=summary["totals"]["n_parse_failures"],
        tokens_in=summary["totals"]["tokens_in"],
        tokens_out=summary["totals"]["tokens_out"],
    ), RESULTS_DIR / "cost_log.jsonl")

    if abort_reason:
        print(f"[aborted] {abort_reason}", file=sys.stderr)
        print(f"[aborted] partial results ({len(all_records)} records) in {outdir}",
              file=sys.stderr)
        return RunOutcome(3, outdir, client.n_calls, False)

    _print_scores("[done]", run_id, summary, client.n_calls)
    print(f"[done] results in {outdir}")
    return RunOutcome(0, outdir, client.n_calls, True)


def run_resume(resume_dir: str, max_calls: int | None = None) -> RunOutcome:
    """Finish an existing run: execute only the missing (person, arm, item) calls."""
    outdir = Path(resume_dir).resolve()
    records_path = outdir / "records.jsonl"
    run_id = outdir.name
    if not records_path.exists():
        print(f"[fatal] no records.jsonl in {outdir}; nothing to resume.",
              file=sys.stderr)
        return RunOutcome(2, outdir, 0, False)

    split, k, seed, variant = _resume_config(outdir, run_id)
    tasks, ids, codebook = _build_all_tasks(split, k, seed, variant)
    done = completed_keys(records_path)
    missing = filter_missing(tasks, done)
    print(f"[resume] {run_id}: split={split} k={k} seed={seed} variant={variant} | "
          f"{len(tasks)} total, {len(done)} done, {len(missing)} missing")

    config = {"split": split, "k": k, "seed": seed, "variant": variant,
              "n_persons": len(ids), "model": None}

    if not missing:
        all_records = read_records(records_path)
        _write_summary(outdir, all_records, config,
                       {"resumed": True, "resume_n_calls": 0}, None)
        _write_human_review(outdir, all_records, codebook)
        print("[resume] already complete; regenerated summary + human_review.")
        return RunOutcome(0, outdir, 0, True)

    cap = max_calls if max_calls is not None else _default_cap(len(missing))
    try:
        client = _make_client(cap, variant)
    except Exception as exc:  # noqa: BLE001
        print(f"[fatal] could not init client: {type(exc).__name__}: "
              f"{_redact(str(exc))}", file=sys.stderr)
        return RunOutcome(2, outdir, 0, False)

    config["model"] = client.model_name
    print(f"[resume] running {len(missing)} calls (cap {cap}), "
          f"model={client.model_name}, variant={variant}, workers={MAX_WORKERS}")

    fh, sink = _record_sink(records_path)
    try:
        new_records, abort_reason = _execute(GeminiBackend(client), missing,
                                             variant, sink)
    finally:
        fh.close()

    all_records = read_records(records_path)
    n_parse_retries = sum(1 for r in new_records if r["parse_retry"])
    process_totals = {
        "resumed": True,
        "resume_n_new_records": len(new_records),
        "resume_n_calls": client.n_calls,
        "resume_n_backoff_retries": client.n_retries,
        "resume_n_parse_retries": n_parse_retries,
        "resume_n_retries_total": client.n_retries + n_parse_retries,
    }
    summary = _write_summary(outdir, all_records, config, process_totals, abort_reason)
    _write_human_review(outdir, all_records, codebook)

    append_cost_log(build_cost_entry(
        run_id=run_id, model=client.model_name, split=split, variant=variant,
        n_persons=len(ids), n_calls=client.n_calls,
        n_retries=client.n_retries + n_parse_retries,
        n_parse_failures=sum(1 for r in new_records if r["parse_failure"]),
        tokens_in=sum(r["tokens_in"] for r in new_records),
        tokens_out=sum(r["tokens_out"] for r in new_records),
        resumed=True,
    ), RESULTS_DIR / "cost_log.jsonl")

    if abort_reason:
        print(f"[aborted] {abort_reason}", file=sys.stderr)
        print(f"[aborted] appended {len(new_records)} records; "
              f"{len(all_records)} total now in {records_path}", file=sys.stderr)
        return RunOutcome(3, outdir, client.n_calls, False)

    _print_scores("[done]", run_id, summary, client.n_calls)
    print(f"[done] appended {len(new_records)} records; {len(all_records)} total "
          f"in {outdir}")
    return RunOutcome(0, outdir, client.n_calls, True)


# ---------------------------------------------------------------------------
# Batch-file backend: export prompts / ingest completions
# ---------------------------------------------------------------------------


def run_export(split: str, k: int, seed: int, variant: str,
               out_path: str) -> RunOutcome:
    """Export the deterministic prompt set to prompts.jsonl + a manifest. No API."""
    tasks, ids, _ = _build_all_tasks(split, k, seed, variant)
    out = Path(out_path)
    n = BatchFileBackend.export(tasks, variant, VARIANT_MAX_OUTPUT_TOKENS[variant], out)
    manifest = {
        "split": split, "k": k, "seed": seed, "variant": variant,
        "backend": "batchfile", "n_prompts": n, "n_persons": len(ids),
        "max_output_tokens": VARIANT_MAX_OUTPUT_TOKENS[variant],
        "prompts_file": str(out),
    }
    (out.parent / "export_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[export] wrote {n} prompts to {out} (+ export_manifest.json). "
          f"split={split} k={k} seed={seed} variant={variant}. No API calls.")
    return RunOutcome(0, out.parent, 0, True)


def run_ingest(split: str, k: int, seed: int, variant: str,
               completions_path: str, node_hours: float | None = None,
               backend_name: str = "batchfile") -> RunOutcome:
    """Score an exported run from a completions.jsonl. No API calls.

    ``backend_name`` labels the generation backend in the summary config and the
    cost log (e.g. "leonardo-batch" for the Qwen HPC batch job); it also names
    the run directory suffix so gemini and batch runs are easy to tell apart.
    """
    tasks, ids, codebook = _build_all_tasks(split, k, seed, variant)
    backend = BatchFileBackend.from_completions(completions_path)
    results = backend.batch_generate([t.prompt for t in tasks],
                                     max_output_tokens=VARIANT_MAX_OUTPUT_TOKENS[variant])

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{make_run_id(split, k, variant, timestamp)}_{backend_name}"
    outdir = RESULTS_DIR / run_id
    outdir.mkdir(parents=True, exist_ok=True)
    _write_example_prompts(outdir, tasks)

    fh, sink = _record_sink(outdir / "records.jsonl")
    try:
        for task, res in zip(tasks, results):
            sink(_score_from_completion(task, variant, res))
    finally:
        fh.close()

    all_records = read_records(outdir / "records.jsonl")
    n_missing = sum(1 for r in results if r.error is not None)
    config = {"split": split, "k": k, "seed": seed, "variant": variant,
              "n_persons": len(ids), "model": backend_name, "backend": backend_name}
    process_totals = {"backend": backend_name, "n_completions": len(results),
                      "n_missing_completions": n_missing, "node_hours": node_hours}
    summary = _write_summary(outdir, all_records, config, process_totals, None)
    _write_human_review(outdir, all_records, codebook)

    append_cost_log(build_cost_entry(
        run_id=run_id, model=backend_name, split=split, variant=variant,
        n_persons=len(ids), n_calls=0, n_retries=0,
        n_parse_failures=summary["totals"]["n_parse_failures"],
        tokens_in=summary["totals"]["tokens_in"],
        tokens_out=summary["totals"]["tokens_out"],
        backend=backend_name, node_hours=node_hours,
    ), RESULTS_DIR / "cost_log.jsonl")

    _print_scores("[ingest]", run_id, summary, 0)
    print(f"[ingest] {len(all_records)} records ({n_missing} missing completions) "
          f"in {outdir}")
    return RunOutcome(0, outdir, 0, True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="DOPPLER Stage-1 replay gym runner.")
    ap.add_argument("--split", choices=["pilot", "gate", "pilot2"], default="pilot")
    ap.add_argument("--k", type=int, default=48, help="interest items per twin (<=48)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--variant", choices=list(VARIANTS), default="v0")
    ap.add_argument("--backend", choices=["gemini", "batchfile"], default="gemini")
    ap.add_argument("--dry-run", action="store_true", help="build prompts, no API calls")
    ap.add_argument("--resume", metavar="RUN_DIR", default=None,
                    help="finish an existing run dir: run only its missing calls")
    ap.add_argument("--export-prompts", metavar="PATH", default=None,
                    help="batchfile: write prompts.jsonl + manifest and exit")
    ap.add_argument("--ingest-completions", metavar="PATH", default=None,
                    help="batchfile: score an exported run from a completions file")
    ap.add_argument("--node-hours", type=float, default=None,
                    help="batchfile ingest: GPU node-hours to record in the cost log")
    ap.add_argument("--backend-name", default="batchfile",
                    help="batchfile ingest: backend label for summary/cost log "
                         "(e.g. leonardo-batch)")
    ap.add_argument("--manifest", metavar="PATH", default=None,
                    help="batchfile ingest: read split/k/seed/variant from an "
                         "export manifest instead of the CLI flags")
    args = ap.parse_args()

    if args.backend == "batchfile":
        split, k, seed, variant = args.split, args.k, args.seed, args.variant
        if args.manifest:
            m = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
            split = m.get("split", split)
            k = int(m.get("k", k))
            seed = int(m.get("seed", seed))
            variant = m.get("variant", variant)
        if args.export_prompts:
            return run_export(split, k, seed, variant,
                              args.export_prompts).exit_code
        if args.ingest_completions:
            return run_ingest(split, k, seed, variant, args.ingest_completions,
                              args.node_hours, args.backend_name).exit_code
        ap.error("--backend batchfile requires --export-prompts or "
                 "--ingest-completions")

    if args.resume:
        return run_resume(args.resume).exit_code
    return run_fresh(args.split, args.k, args.seed, args.variant,
                     dry_run=args.dry_run).exit_code


if __name__ == "__main__":
    raise SystemExit(main())
