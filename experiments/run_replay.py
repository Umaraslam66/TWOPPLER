"""Stage-1 replay gym runner.

Predicts each of a person's 10 held-out TIPI items from (a) demographics +
interests (twin) and (b) demographics only (baseline), one API call per
(person, item, arm), then scores lift = twin - baseline per person.

Usage:
    uv run python experiments/run_replay.py --split pilot            # real pilot
    uv run python experiments/run_replay.py --split pilot --dry-run  # zero calls

Writes everything to ``results/<run_id>/`` where
``run_id = {split}_k{k}_{YYYYMMDD-HHMMSS}``.
"""

from __future__ import annotations

import argparse
import json
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
    client: GeminiClient,
    n_parse_retries: int,
    abort_reason: str | None,
) -> dict:
    stats = summarize(records)
    tokens_in = sum(r["tokens_in"] for r in records)
    tokens_out = sum(r["tokens_out"] for r in records)
    n_parse_failures = sum(1 for r in records if r["parse_failure"])
    n_retries = client.n_retries + n_parse_retries

    summary = {
        "config": config,
        "scoring": stats,
        "totals": {
            "n_records": len(records),
            "n_calls": client.n_calls,
            "n_retries_total": n_retries,
            "n_backoff_retries": client.n_retries,
            "n_parse_retries": n_parse_retries,
            "n_parse_failures": n_parse_failures,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        },
        "aborted": abort_reason,
    }
    (outdir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="DOPPLER Stage-1 replay gym runner.")
    ap.add_argument("--split", choices=["pilot", "gate"], default="pilot")
    ap.add_argument("--k", type=int, default=48, help="interest items per twin (<=48)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true", help="build prompts, no API calls")
    args = ap.parse_args()

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
    summary = _write_summary(
        outdir, records, config, client, n_parse_retries, abort_reason
    )

    entry = build_cost_entry(
        run_id=run_id,
        model=client.model_name,
        split=args.split,
        n_persons=len(ids),
        n_calls=client.n_calls,
        n_retries=summary["totals"]["n_retries_total"],
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
