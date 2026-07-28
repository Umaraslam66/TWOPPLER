#!/usr/bin/env python3
"""Pull the H6 primary-model completions off Leonardo and bill the node-hours.

The node half of the H6 generation step. ``experiments/h6_gen.sbatch`` runs
Gemma-4-31B-it over the prompt chunks ``experiments/h6_arms.py`` rendered; this
driver pulls the completions back, joins them to the meta sidecar BY PROMPT
HASH (never by position), writes them in the same completion schema the
confirmatory H1 run used -- so the frozen embed and judge drivers read them
unchanged -- and appends one cost line per chunk billed from ``sacct``.

Every attempt is billed, cancelled ones included, at elapsed x allocated nodes.
The phase cap is 3 node-hours across H6 classify + H6 generation; the classify
pass already spent 0.1581, so this driver refuses to bill past the remainder.

Run::

    .venv/bin/python experiments/h6_ingest.py --status
    .venv/bin/python experiments/h6_ingest.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import stage2_oe1 as OE1  # noqa: E402

from doppler import counterfactuals as CF  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402
from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402

RESULTS_DIR = _ROOT / "results"
CONFIRM_DIR = RESULTS_DIR / "stage2_confirm"
H6_DIR = CONFIRM_DIR / "h6"
GEN_DIR = H6_DIR / "gen" / "gemma"
NODE_OUT = H6_DIR / "node_out"
COST_LOG = RESULTS_DIR / "cost_log.jsonl"

REMOTE_HOST = "leonardo"
REMOTE_ROOT = "/leonardo_work/AIFAC_P02_548/DOPPLER"
REMOTE_RUN = f"{REMOTE_ROOT}/runs/stage2_confirm_h6_gen"
JOB_NAME = "dop-h6-gen"
SSH_OPTS = ("-o", "BatchMode=yes", "-o", "ConnectTimeout=25")

RUN_ID = "stage2_confirm/h6_gen_gemma"
SPLIT = "stage2_confirm_h6"
MODEL = OE1.PRIMARY_MODEL
TEMPERATURE = OE1.GEN_TEMPERATURE
MAX_OUTPUT_TOKENS = 256
MAX_ANSWER_WORDS = 150

CHUNKS = ("chunk_01", "chunk_02")

#: Closeout GPU phase cap, shared with the classifier pass.
PHASE_NODE_HOUR_CAP = 3.0
#: What the classifier pass already billed against it.
CLASSIFY_RUN_ID = "stage2_confirm/h6_classify"
#: This task's own additional-GPU limit.
TASK_NODE_HOUR_LIMIT = 2.0


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


def _ssh(command: str, *, timeout: int = 180) -> str:
    proc = subprocess.run(("ssh", *SSH_OPTS, REMOTE_HOST, command),
                          capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise fatal(f"ssh failed ({proc.returncode}) for {command!r}: "
                    f"{proc.stderr.strip()[:400]}")
    return proc.stdout


def _pull(remote: str, local: Path) -> bool:
    local.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("rsync"):
        proc = subprocess.run(
            ("rsync", "-az", "-e", "ssh " + " ".join(SSH_OPTS),
             f"{REMOTE_HOST}:{remote}", str(local)),
            capture_output=True, text=True, timeout=900)
        return proc.returncode == 0
    proc = subprocess.run(("scp", *SSH_OPTS, f"{REMOTE_HOST}:{remote}",
                           str(local)), capture_output=True, text=True,
                          timeout=900)
    return proc.returncode == 0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _elapsed_seconds(text: str) -> float:
    m = re.match(r"^(?:(\d+)-)?(\d+):(\d+):(\d+(?:\.\d+)?)$", text.strip())
    if not m:
        return 0.0
    days, hh, mm, ss = m.groups()
    return (int(days or 0) * 86400 + int(hh) * 3600 + int(mm) * 60 + float(ss))


def sacct_node_hours() -> dict:
    """Every attempt of this job name, billed at elapsed x allocated nodes."""
    out = _ssh(f"sacct -X --name={JOB_NAME} --starttime=2026-07-01 "
               "--format=JobID,JobName,State,Elapsed,NNodes,Start,End "
               "--parsable2 --noheader")
    jobs, total = [], 0.0
    for line in out.splitlines():
        if not line.strip():
            continue
        jobid, _name, state, elapsed, nnodes, start, end = line.split("|")[:7]
        secs = _elapsed_seconds(elapsed) * int(nnodes or 1)
        total += secs
        jobs.append({"job_id": jobid, "state": state, "elapsed": elapsed,
                     "nnodes": int(nnodes or 1),
                     "node_seconds": round(secs, 1), "start": start,
                     "end": end})
    return {"jobs": jobs, "n_attempts": len(jobs),
            "node_hours_all_attempts": round(total / 3600.0, 4)}


def logged(run_id: str) -> float:
    if not COST_LOG.exists():
        return 0.0
    total = 0.0
    for line in COST_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("run_id") == run_id:
            total += float(entry.get("node_hours") or 0.0)
    return round(total, 4)


def build_row(chunk: str, meta: dict, item: dict, got: dict) -> dict:
    """One completion row, in the confirmatory run's completion schema."""
    text = (got.get("text") or "").strip()
    tout = int(got.get("tokens_out") or got.get("n_tokens_out") or 0)
    words = R.word_count(text)
    return {
        "chunk": chunk,
        "idx": int(meta["idx"]),
        "item_id": meta["item_id"],
        "canonical_id": meta["canonical_id"],
        "arm": meta["arm"],
        "h6_kind": meta.get("h6_kind"),
        "h6_budget": meta.get("h6_budget"),
        "h7_bin": None,
        "cutoff_date": None,
        "delta_days": None,
        "item_type": meta.get("item_type"),
        "model": MODEL,
        "temperature": TEMPERATURE,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "prompt_sha256": meta["prompt_sha256"],
        "text": text,
        "answer_words": words,
        "over_word_cap": words > MAX_ANSWER_WORDS,
        "truncated": OE1.looks_truncated(text, tout),
        "era_violations": CF.era_violations(text, item["test_date"]),
        "tokens_in": int(got.get("tokens_in") or 0),
        "tokens_out": tout,
        "ingested_utc": OE1.now(),
    }


def ingest_chunk(chunk: str, items: dict) -> dict:
    """Pull one chunk, verify the node read OUR prompts, join, write."""
    local_out = NODE_OUT / f"completions_{chunk}.jsonl"
    if not _pull(f"{REMOTE_RUN}/completions_{chunk}.jsonl", local_out):
        raise fatal(f"{chunk}: no completions on the node")
    _pull(f"{REMOTE_RUN}/completions_{chunk}.jsonl.summary.json",
          Path(str(local_out) + ".summary.json"))

    # The node must have read the file we built. Checked before any join.
    local_prompts = H6_DIR / "node" / f"{chunk}.prompts.jsonl"
    remote_sha = _ssh(
        f"sha256sum {REMOTE_RUN}/{chunk}.prompts.jsonl").split()[0]
    if remote_sha != sha256_file(local_prompts):
        raise fatal(f"{chunk}: the node's prompt file is not the one we "
                    "built; refusing to join")

    metas = S.read_jsonl(H6_DIR / "node" / f"{chunk}.meta.jsonl")
    prompts = {int(r["idx"]): r for r in S.read_jsonl(local_prompts)}
    comps = {int(r["idx"]): r for r in S.read_jsonl(local_out)}

    joined = []
    for meta in metas:
        idx = int(meta["idx"])
        got = comps.get(idx)
        if got is None:
            raise fatal(f"{chunk}: no completion for idx {idx}")
        # Position is not identity. Re-derive the hash of the prompt that was
        # actually on the node at this index and check it against the sidecar.
        if R.sha256(prompts[idx]["prompt"]) != meta["prompt_sha256"]:
            raise fatal(f"{chunk} idx {idx}: prompt file and meta sidecar "
                        "disagree on the prompt hash")
        item = items.get(meta["item_id"])
        if item is None:
            raise fatal(f"{chunk}: item {meta['item_id']} not in the H6 "
                        "item file")
        joined.append(build_row(chunk, meta, item, got))

    GEN_DIR.mkdir(parents=True, exist_ok=True)
    S.write_jsonl(GEN_DIR / f"completions_{chunk}.jsonl", joined)

    per_arm = {}
    for arm in sorted({r["arm"] for r in joined}):
        sub = [r for r in joined if r["arm"] == arm]
        per_arm[arm] = {
            "n": len(sub),
            "n_truncated": sum(1 for r in sub if r["truncated"]),
            "n_over_word_cap": sum(1 for r in sub if r["over_word_cap"]),
            "n_era_violations": sum(1 for r in sub if r["era_violations"]),
            "n_empty": sum(1 for r in sub if not r["text"]),
        }
    summary = {
        "chunk": chunk, "model": MODEL, "n_rows": len(joined),
        "temperature": TEMPERATURE, "max_output_tokens": MAX_OUTPUT_TOKENS,
        "tokens_in": sum(r["tokens_in"] for r in joined),
        "tokens_out": sum(r["tokens_out"] for r in joined),
        "n_truncated": sum(1 for r in joined if r["truncated"]),
        "n_over_word_cap": sum(1 for r in joined if r["over_word_cap"]),
        "n_era_violations": sum(1 for r in joined if r["era_violations"]),
        "n_empty": sum(1 for r in joined if not r["text"]),
        "per_arm": per_arm, "ingested_utc": OE1.now(),
    }
    S.write_json(GEN_DIR / f"gen_summary_{chunk}.json", summary)
    print(f"[ingest] {chunk}: {len(joined)} rows, "
          f"{summary['n_truncated']} truncated, "
          f"{summary['n_era_violations']} era violations, "
          f"{summary['n_empty']} empty")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--chunks", nargs="*", default=list(CHUNKS))
    ap.add_argument("--skip-cost", action="store_true")
    args = ap.parse_args(argv)

    listing = _ssh(f"ls -la {REMOTE_RUN} 2>/dev/null || echo '(no run dir)'")
    bill = sacct_node_hours()
    already = logged(RUN_ID)
    classify = logged(CLASSIFY_RUN_ID)
    print(listing)
    print(f"[bill] {bill['n_attempts']} attempt(s), "
          f"{bill['node_hours_all_attempts']} node-hours from sacct "
          f"(already logged for this run: {already})")
    for job in bill["jobs"]:
        print(f"  {job['job_id']} {job['state']:12s} {job['elapsed']} "
              f"x{job['nnodes']}")
    print(f"[bill] closeout phase: classify {classify} + this run "
          f"{bill['node_hours_all_attempts']} = "
          f"{round(classify + bill['node_hours_all_attempts'], 4)} of "
          f"{PHASE_NODE_HOUR_CAP}; this task's own limit is "
          f"{TASK_NODE_HOUR_LIMIT} additional node-hours")
    if args.status:
        return 0

    items = {r["item_id"]: r for r in
             S.read_jsonl(H6_DIR / "items_confirm.jsonl")}
    summaries = [ingest_chunk(c, items) for c in args.chunks]

    delta = round(bill["node_hours_all_attempts"] - already, 4)
    if delta > TASK_NODE_HOUR_LIMIT:
        raise fatal(f"this run billed {delta} node-hours, past the "
                    f"{TASK_NODE_HOUR_LIMIT} additional-GPU limit; stop and "
                    "report the arithmetic")
    if classify + bill["node_hours_all_attempts"] > PHASE_NODE_HOUR_CAP:
        raise fatal(f"the closeout phase would reach "
                    f"{classify + bill['node_hours_all_attempts']} node-hours, "
                    f"past the {PHASE_NODE_HOUR_CAP} cap")
    if delta > 0 and not args.skip_cost:
        entry = build_cost_entry(
            run_id=RUN_ID, model=MODEL, split=SPLIT,
            n_persons=len({r["canonical_id"] for c in args.chunks
                           for r in S.read_jsonl(
                               GEN_DIR / f"completions_{c}.jsonl")}),
            n_calls=sum(s["n_rows"] for s in summaries),
            n_retries=0,
            n_parse_failures=sum(s["n_empty"] for s in summaries),
            tokens_in=sum(s["tokens_in"] for s in summaries),
            tokens_out=sum(s["tokens_out"] for s in summaries),
            backend="leonardo-batch", node_hours=delta)
        append_cost_log(entry, COST_LOG)
        print(f"[cost] logged {delta} node-hours for {RUN_ID}")
    S.write_json(GEN_DIR / "node_hours_accounting.json",
                 {"run_id": RUN_ID, "billing": bill,
                  "classify_node_hours": classify,
                  "phase_cap": PHASE_NODE_HOUR_CAP,
                  "task_limit": TASK_NODE_HOUR_LIMIT,
                  "billed_this_run": delta})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
