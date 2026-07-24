"""Stage-1 replay gym runner.

Predicts each of a person's 10 held-out TIPI items from (a) demographics +
interests (twin) and (b) demographics only (baseline), one API call per
(person, item, arm), then scores lift = twin - baseline per person.

Usage:
    uv run python experiments/run_replay.py --split pilot            # real pilot
    uv run python experiments/run_replay.py --split pilot --dry-run  # zero calls
    uv run python experiments/run_replay.py --resume results/<run_id>  # finish it

Writes everything to ``results/<run_id>/`` where
``run_id = {split}_k{k}_{YYYYMMDD-HHMMSS}``. ``--resume`` re-opens an existing
run directory, runs only the (person, arm, item) calls missing from its
records.jsonl, appends them, and regenerates the summary and human-review from
all records in the file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402
from doppler.data import (  # noqa: E402
    clean_riasec,
    load_codebook,
    load_riasec,
    person_record,
)
from doppler.gemini import CallCapExceeded, GeminiClient  # noqa: E402
from doppler.gym import build_tasks, pilot_and_gate_ids  # noqa: E402
from doppler.scoring import parse_answer, score, summarize  # noqa: E402

DATA_DIR = _ROOT / "data"
RESULTS_DIR = _ROOT / "results"
# One worker: the key is on a ~15 requests/minute free tier, so throughput is
# gated entirely by the client's request pacer. Extra threads would only race to
# hit the shared RPM cap and trigger 429 storms; they buy no speed.
MAX_CALLS = 600
MAX_WORKERS = 1
DEFAULT_SEED = 42
RETRY_SENTENCE = "Respond with only a single digit from 1 to 7."


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def _build_all_tasks(split: str, k: int, seed: int):
    """Load data and build both-arm tasks for every person in the split."""
    df = clean_riasec(load_riasec(DATA_DIR))
    codebook = load_codebook(DATA_DIR)
    pilot_ids, gate_ids = pilot_and_gate_ids(df)
    ids = pilot_ids if split == "pilot" else gate_ids

    by_id = df.set_index("person_id", drop=False)
    tasks = []
    for pid in ids:
        record = person_record(by_id.loc[pid], codebook)
        tasks.extend(build_tasks(record, codebook, "twin", k=k, seed=seed))
        tasks.extend(build_tasks(record, codebook, "baseline", k=k, seed=seed))
    return tasks, ids, codebook


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
    return [
        t for t in tasks
        if (t.person_id, t.arm, t.tipi_code) not in completed
    ]


def _append_records(records_path: Path, records: list[dict]) -> None:
    """Append records as JSON lines to an existing records.jsonl."""
    with Path(records_path).open("a", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _resume_config(outdir: Path, run_id: str) -> tuple[str, int, int]:
    """Recover (split, k, seed) for a resume, from summary.json then run_id."""
    summary_path = outdir / "summary.json"
    if summary_path.exists():
        try:
            cfg = json.loads(summary_path.read_text(encoding="utf-8")).get("config", {})
            if cfg.get("split") and cfg.get("k") is not None and cfg.get("seed") is not None:
                return cfg["split"], int(cfg["k"]), int(cfg["seed"])
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            pass
    m = re.match(r"(pilot|gate)_k(\d+)_", run_id)
    if not m:
        raise SystemExit(
            f"[fatal] cannot infer split/k from run_id {run_id!r} and no usable "
            "summary.json; cannot resume."
        )
    return m.group(1), int(m.group(2)), DEFAULT_SEED


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


def _run_one(client: GeminiClient, task) -> dict:
    """Execute one prediction task: generate, parse, one parse-retry if needed."""
    text, t_in, t_out = client.generate(task.prompt)
    parsed = parse_answer(text)
    raw = text
    parse_retry = False

    if parsed is None:
        parse_retry = True
        retry_prompt = task.prompt + "\n\n" + RETRY_SENTENCE
        text2, t_in2, t_out2 = client.generate(retry_prompt)
        t_in += t_in2
        t_out += t_out2
        raw = text2
        parsed = parse_answer(text2)

    parse_failure = parsed is None
    sc = score(parsed, task.true_answer)
    return {
        "person_id": task.person_id,
        "arm": task.arm,
        "item": task.tipi_code,
        "prompt": task.prompt,
        "raw_response": raw,
        "parsed": parsed,
        "true_answer": task.true_answer,
        "correct": sc["correct"],
        "abs_error": sc["abs_error"],
        "within1": sc["within1"],
        "parse_failure": parse_failure,
        "parse_retry": parse_retry,
        "tokens_in": t_in,
        "tokens_out": t_out,
    }


def _execute(client: GeminiClient, tasks) -> tuple[list[dict], str | None]:
    """Run all tasks in a small thread pool. Returns (records, abort_reason)."""
    records: list[dict] = []
    abort_reason: str | None = None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_run_one, client, t): t for t in tasks}
        try:
            for fut in tqdm(as_completed(futures), total=len(futures), desc="calls"):
                records.append(fut.result())
        except CallCapExceeded as exc:
            abort_reason = f"CallCapExceeded: {exc}"
        except Exception as exc:  # noqa: BLE001 - fatal API error; stop cleanly
            abort_reason = f"{type(exc).__name__}: {_redact(str(exc))}"
        finally:
            if abort_reason is not None:
                for fut in futures:
                    fut.cancel()

    return records, abort_reason


def _redact(message: str) -> str:
    """Strip the API key from any message before it is printed/written."""
    import os

    key = os.environ.get("GOOGLE_AI_STUDIO")
    if key and key in message:
        message = message.replace(key, "<REDACTED_API_KEY>")
    return message


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _write_records(outdir: Path, records: list[dict]) -> None:
    with (outdir / "records.jsonl").open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _write_human_review(outdir: Path, records: list[dict], codebook) -> None:
    """10 distinct persons, twin arm: profile, question, parsed, true, baseline."""
    lookup = {(r["person_id"], r["arm"], r["item"]): r for r in records}
    twins = [r for r in records if r["arm"] == "twin"]

    seen: dict[int, dict] = {}
    for r in twins:  # first record per person (records are unordered; that's fine)
        seen.setdefault(r["person_id"], r)
    examples = list(seen.values())[:10]

    lines = ["# Human review — 10 twin-arm examples", ""]
    for i, r in enumerate(examples, 1):
        pid, item = r["person_id"], r["item"]
        base = lookup.get((pid, "baseline", item))
        tipi_text = codebook.tipi_items.get(item, item)
        profile = r["prompt"].split("\n\nYOUR TASK")[0]
        lines += [
            f"## Example {i} — person {pid}, item {item}",
            "",
            "**Seed profile (twin):**",
            "",
            "```",
            profile,
            "```",
            "",
            f'**Held-out question:** "I see myself as: {tipi_text}"',
            "",
            f"- Twin parsed answer: {r['parsed']}"
            + (" (parse failure)" if r["parse_failure"] else ""),
            f"- True answer: {r['true_answer']}",
            f"- Baseline parsed answer for same item: "
            f"{base['parsed'] if base else 'n/a'}",
            "",
        ]
    (outdir / "human_review.md").write_text("\n".join(lines), encoding="utf-8")


def _write_summary(
    outdir: Path,
    records: list[dict],
    config: dict,
    process_totals: dict,
    abort_reason: str | None,
) -> dict:
    """Score ALL ``records`` and write summary.json.

    Content totals (records, tokens, parse failures) are cumulative over the
    file; ``process_totals`` carries the call/retry counts for the process that
    just ran (a fresh run, or the resuming process).
    """
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
    (outdir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_resume(resume_dir: str) -> int:
    """Finish an existing run: execute only the missing (person, arm, item) calls."""
    outdir = Path(resume_dir).resolve()
    records_path = outdir / "records.jsonl"
    run_id = outdir.name
    if not records_path.exists():
        print(f"[fatal] no records.jsonl in {outdir}; nothing to resume.",
              file=sys.stderr)
        return 2

    split, k, seed = _resume_config(outdir, run_id)
    tasks, ids, codebook = _build_all_tasks(split, k, seed)
    done = completed_keys(records_path)
    missing = filter_missing(tasks, done)

    print(f"[resume] {run_id}: split={split} k={k} seed={seed} | "
          f"{len(tasks)} total tasks, {len(done)} done, {len(missing)} missing")

    if not missing:
        # Nothing to call: just regenerate the derived files from all records.
        all_records = read_records(records_path)
        config = {"split": split, "k": k, "seed": seed, "n_persons": len(ids),
                  "model": None}
        _write_summary(outdir, all_records, config,
                       {"resumed": True, "resume_n_calls": 0}, None)
        _write_human_review(outdir, all_records, codebook)
        print("[resume] already complete; regenerated summary + human_review.")
        return 0

    try:
        client = GeminiClient(max_calls=MAX_CALLS)
    except Exception as exc:  # noqa: BLE001
        print(f"[fatal] could not init client: {type(exc).__name__}: "
              f"{_redact(str(exc))}", file=sys.stderr)
        return 2

    print(f"[resume] running {len(missing)} calls (cap {MAX_CALLS}), "
          f"model={client.model_name}, workers={MAX_WORKERS}")
    new_records, abort_reason = _execute(client, missing)
    _append_records(records_path, new_records)

    all_records = read_records(records_path)
    n_parse_retries = sum(1 for r in new_records if r["parse_retry"])
    config = {"split": split, "k": k, "seed": seed, "n_persons": len(ids),
              "model": client.model_name}
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

    # Cost log: a new line, resumed=True, counting only THIS process's spend.
    entry = build_cost_entry(
        run_id=run_id,
        model=client.model_name,
        split=split,
        n_persons=len(ids),
        n_calls=client.n_calls,
        n_retries=client.n_retries + n_parse_retries,
        n_parse_failures=sum(1 for r in new_records if r["parse_failure"]),
        tokens_in=sum(r["tokens_in"] for r in new_records),
        tokens_out=sum(r["tokens_out"] for r in new_records),
        resumed=True,
    )
    append_cost_log(entry, RESULTS_DIR / "cost_log.jsonl")

    if abort_reason:
        print(f"[aborted] {abort_reason}", file=sys.stderr)
        print(f"[aborted] appended {len(new_records)} records; "
              f"{len(all_records)} total now in {records_path}", file=sys.stderr)
        return 3

    ex = summary["scoring"]["exact"]
    print(f"[done] {run_id}: appended {len(new_records)} records "
          f"({client.n_calls} calls); {len(all_records)} total")
    print(f"[done] twin={ex['twin_accuracy']['mean']:.3f} "
          f"baseline={ex['baseline_accuracy']['mean']:.3f} "
          f"lift={ex['lift']['mean']:+.3f} (t p={ex['tests']['t_p']:.4g})")
    print(f"[done] results in {outdir}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="DOPPLER Stage-1 replay gym runner.")
    ap.add_argument("--split", choices=["pilot", "gate"], default="pilot")
    ap.add_argument("--k", type=int, default=48, help="interest items per twin (<=48)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true", help="build prompts, no API calls")
    ap.add_argument("--resume", metavar="RUN_DIR", default=None,
                    help="finish an existing run dir: run only its missing calls")
    args = ap.parse_args()

    if args.resume:
        return run_resume(args.resume)

    tasks, ids, codebook = _build_all_tasks(args.split, args.k, args.seed)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{args.split}_k{args.k}_{timestamp}"
    outdir = RESULTS_DIR / run_id
    outdir.mkdir(parents=True, exist_ok=True)

    _write_example_prompts(outdir, tasks)
    mean_chars = sum(len(t.prompt) for t in tasks) / len(tasks)

    config = {
        "split": args.split,
        "k": args.k,
        "seed": args.seed,
        "n_persons": len(ids),
        "model": None,  # filled below for real runs
    }

    if args.dry_run:
        manifest = {
            "run_id": run_id,
            "split": args.split,
            "k": args.k,
            "seed": args.seed,
            "n_persons": len(ids),
            "planned_calls": len(tasks),
            "mean_prompt_chars": round(mean_chars, 1),
        }
        (outdir / "dry_run_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        print(f"[dry-run] {run_id}: {len(tasks)} planned calls, "
              f"mean prompt {mean_chars:.0f} chars. No API calls made.")
        print(f"[dry-run] wrote example prompts + manifest to {outdir}")
        return 0

    # ---- real run --------------------------------------------------------
    try:
        client = GeminiClient(max_calls=MAX_CALLS)
    except Exception as exc:  # noqa: BLE001
        print(f"[fatal] could not init client: {type(exc).__name__}: "
              f"{_redact(str(exc))}", file=sys.stderr)
        return 2

    config["model"] = client.model_name
    print(f"[run] {run_id}: {len(tasks)} planned calls (cap {MAX_CALLS}), "
          f"model={client.model_name}, workers={MAX_WORKERS}")

    records, abort_reason = _execute(client, tasks)
    n_parse_retries = sum(1 for r in records if r["parse_retry"])

    _write_records(outdir, records)
    _write_human_review(outdir, records, codebook)
    process_totals = {
        "n_calls": client.n_calls,
        "n_backoff_retries": client.n_retries,
        "n_parse_retries": n_parse_retries,
        "n_retries_total": client.n_retries + n_parse_retries,
    }
    summary = _write_summary(outdir, records, config, process_totals, abort_reason)

    entry = build_cost_entry(
        run_id=run_id,
        model=client.model_name,
        split=args.split,
        n_persons=len(ids),
        n_calls=client.n_calls,
        n_retries=process_totals["n_retries_total"],
        n_parse_failures=summary["totals"]["n_parse_failures"],
        tokens_in=summary["totals"]["tokens_in"],
        tokens_out=summary["totals"]["tokens_out"],
    )
    append_cost_log(entry, RESULTS_DIR / "cost_log.jsonl")

    if abort_reason:
        print(f"[aborted] {abort_reason}", file=sys.stderr)
        print(f"[aborted] partial results ({len(records)} records) written to {outdir}",
              file=sys.stderr)
        return 3

    ex = summary["scoring"]["exact"]
    print(f"[done] {run_id}: {client.n_calls} calls, "
          f"{summary['totals']['n_parse_failures']} parse failures")
    print(f"[done] twin={ex['twin_accuracy']['mean']:.3f} "
          f"baseline={ex['baseline_accuracy']['mean']:.3f} "
          f"lift={ex['lift']['mean']:+.3f} "
          f"(t p={ex['tests']['t_p']:.4g})")
    print(f"[done] results in {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
