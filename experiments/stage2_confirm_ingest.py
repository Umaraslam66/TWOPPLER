#!/usr/bin/env python3
"""Confirmatory Stage 2 -- ingest the Gemma completions off Leonardo.

This is the local, offline half of the primary-model generation step. The node
runs ``stage2_confirm_gen.sbatch`` (one job per prompt chunk, four GPUs, whole
node); this driver pulls what has landed, joins it back to the render rows, and
bills the GPU time. **No API call, no GPU, no job control.**

What this driver will not do, by construction
---------------------------------------------
It never submits and never cancels. ``_ssh`` refuses any remote command
containing ``sbatch``/``scancel``/``srun``/``sbcast``/``scontrol update``, so a
future edit cannot quietly turn an ingest into job control. The only remote
verbs used are ``ls``, ``sha256sum``, ``grep``, ``sacct`` and a read-only
``scontrol show job``.

The join key is ``prompt_sha256``, never ``idx``
------------------------------------------------
``idx`` is a position in a rendered file. The full-89 D7 donor re-fit moved 30
``imposter_redacted`` rows inside chunks 01-02 after generation had started, so
a position is not an identity and has been historically wrong for exactly those
rows. ``prompt_sha256`` is globally unique across all 1,911 confirmatory
prompts and names the prompt that was actually answered.

The node's own output format is ``{idx, text, tokens_in, tokens_out}`` -- it
carries no hash. So the bridge is built like this, and every step is verified:

1. The node prompt file ``chunk_NN.prompts.jsonl`` is the exact file the job
   read. Its sha256 on the node is compared to ``render_manifest.json``'s
   ``node_prompts_sha256`` **and** to the committed local copy. All three must
   agree or the chunk is refused.
2. Inside that verified file, ``idx -> prompt text`` is read, and the prompt
   text is hashed. That is the only place ``idx`` is used, and it is used
   within one internally consistent file, not across files.
3. ``sha256(prompt) -> render row`` comes from the join sidecar
   ``node/chunk_NN.meta.jsonl``, whose ``prompt_sha256`` values are checked to
   be a bijection with the prompt file's hashes.

A completion whose hash is absent from the current prompt file is stale: it is
reported and dropped, never joined by position.

Billing
-------
Leonardo bills whole nodes. ``sacct -X --name=dop-s2confirm-gen`` is the source
of truth for elapsed time, **every attempt included** -- a job that ran for
forty minutes and then failed cost the same as one that succeeded. Jobs are
attributed to chunks by reading the ``chunk=`` line the sbatch echoes into its
own log; anything unattributable with non-zero elapsed time is a hard stop, not
a rounding-down. One cost-log line per completed chunk, ``backend`` =
``leonardo-batch``, ``node_hours`` filled, against the run's 8 node-hour cap.

Usage::

    .venv/bin/python experiments/stage2_confirm_ingest.py --status
    .venv/bin/python experiments/stage2_confirm_ingest.py
    .venv/bin/python experiments/stage2_confirm_ingest.py --chunks chunk_01
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import stage2_oe1 as OE1  # noqa: E402  (the machinery this run reuses)

from doppler import counterfactuals as CF  # noqa: E402
from doppler import oe_render as OE  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402
from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402

RESULTS_DIR = _ROOT / "results"
CONFIRM_DIR = RESULTS_DIR / "stage2_confirm"
COST_LOG = RESULTS_DIR / "cost_log.jsonl"

#: Raw node output lands here. Regenerable (it is a copy of what is on the
#: node), large, and deliberately NOT part of the committed record -- the
#: joined completions and the summaries are.
NODE_OUT_DIR = CONFIRM_DIR / "node_out"
#: The joined rows, one file per chunk, same layout as the flash-lite half.
GEN_DIR = CONFIRM_DIR / "gen" / "gemma"

RUN_ID = "stage2_confirm/gen_gemma"
SPLIT = "stage2_confirm_openended"

#: Pinned in code. The node runs this model and nothing else.
MODEL = "Gemma-4-31B-it"

#: Frozen open-ended generation parameters (Addendum A parameter 4).
TEMPERATURE = 0.0
MAX_OUTPUT_TOKENS = OE.MAX_OUTPUT_TOKENS   # 256
MAX_ANSWER_WORDS = OE.MAX_ANSWER_WORDS     # 150

CHUNK_ALLOWLIST = ("chunk_01", "chunk_02", "chunk_03", "chunk_04", "chunk_05")

#: Launch plan: 8 node-hours total for the confirmatory generation run.
NODE_HOUR_BUDGET = 8.0

REMOTE_HOST = "leonardo"
REMOTE_BASE = "/leonardo_work/AIFAC_P02_548/DOPPLER"
REMOTE_RUN_DIR = f"{REMOTE_BASE}/runs/stage2_confirm"
REMOTE_LOG_DIR = f"{REMOTE_BASE}/logs"
JOB_NAME = "dop-s2confirm-gen"

#: How far back to ask sacct. Without this sacct only reports today's jobs.
SACCT_STARTTIME = "now-14days"

SSH_OPTS = ("-o", "ConnectTimeout=30", "-o", "BatchMode=yes")
SSH_TIMEOUT_S = 180
RSYNC_TIMEOUT_S = 1800

#: Any remote command invoking one of these is refused. This driver reads; it
#: does not run, stop, or reshape jobs, and it does not write on the node.
#: Matched as whole words at a command position, never as a substring -- a
#: plain ``in`` test fires on "stage2_confi**rm** " and would block every path
#: this driver legitimately reads.
_FORBIDDEN_RE = re.compile(
    r"(?:^|[\s;|&(`])(?:sbatch|scancel|srun|sbcast|salloc|rm|mv|cp|tee|"
    r"truncate|dd|mkdir|touch|chmod|chown)\b"
    r"|(?:^|[\s;|&(`])scontrol\s+(?:update|requeue|hold|release|suspend|"
    r"resume|delete|write|create)\b",
    re.IGNORECASE)

#: The only redirections a read-only command needs. Anything else writes.
_ALLOWED_REDIRECT_RE = re.compile(r"\d?>\s*/dev/null")

#: The marker ``batch_generate.py`` writes when it has finished a file. A
#: completions file without it is a job still writing, and is not ingested.
DONE_SUFFIX = ".summary.json"

_CHUNK_LINE_RE = re.compile(r"chunk=(chunk_\d\d)\b")
_JOBID_FROM_LOG_RE = re.compile(rf"{JOB_NAME}-(\d+)\.out")


def now() -> str:
    return OE1.now()


def rel(path: Path) -> str:
    return OE1.rel(path)


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


# ---------------------------------------------------------------------------
# Remote access (read-only)
# ---------------------------------------------------------------------------


def _ssh(command: str, *, timeout: int = SSH_TIMEOUT_S,
         check: bool = True) -> str:
    """Run one read-only command on Leonardo over the shared socket.

    The forbidden-verb check is the guard that keeps this file an ingest tool.
    It is deliberately crude and deliberately loud.
    """
    hit = _FORBIDDEN_RE.search(command)
    if hit:
        raise fatal(f"remote command invokes {hit.group(0).strip()!r}; this "
                    "driver is read-only and never controls jobs or writes on "
                    "the node")
    if _ALLOWED_REDIRECT_RE.sub("", command).count(">"):
        raise fatal("remote command redirects output to a file; this driver "
                    "never writes on the node")
    proc = subprocess.run(("ssh", *SSH_OPTS, REMOTE_HOST, command),
                          capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise fatal(f"ssh {REMOTE_HOST} failed ({proc.returncode}) for "
                    f"{command!r}: {proc.stderr.strip()[:400]}")
    return proc.stdout


def _pull(remote_path: str, local_path: Path) -> None:
    """Copy one file down. rsync when available, ssh+cat as the fallback."""
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("rsync"):
        proc = subprocess.run(
            ("rsync", "-az", "--partial",
             "-e", "ssh " + " ".join(SSH_OPTS),
             f"{REMOTE_HOST}:{remote_path}", str(local_path)),
            capture_output=True, text=True, timeout=RSYNC_TIMEOUT_S)
        if proc.returncode == 0:
            return
        print(f"[ingest] rsync failed ({proc.returncode}), falling back to "
              f"ssh cat: {proc.stderr.strip()[:200]}", file=sys.stderr)
    proc = subprocess.run(("ssh", *SSH_OPTS, REMOTE_HOST,
                           f"cat {remote_path}"),
                          capture_output=True, timeout=RSYNC_TIMEOUT_S)
    if proc.returncode != 0:
        raise fatal(f"could not pull {remote_path}: "
                    f"{proc.stderr.decode('utf-8', 'replace')[:400]}")
    local_path.write_bytes(proc.stdout)


def remote_listing() -> dict[str, dict]:
    """What exists in the node run dir right now, per chunk."""
    out = _ssh(f"ls -1 {REMOTE_RUN_DIR} 2>/dev/null || true")
    names = {line.strip() for line in out.splitlines() if line.strip()}
    state = {}
    for chunk in CHUNK_ALLOWLIST:
        comp = f"completions_{chunk}.jsonl"
        state[chunk] = {
            "completions_present": comp in names,
            "done_marker_present": (comp + DONE_SUFFIX) in names,
            "prompts_present": f"{chunk}.prompts.jsonl" in names,
        }
    return state


def remote_sha256(remote_path: str) -> str | None:
    out = _ssh(f"sha256sum {remote_path} 2>/dev/null || true").strip()
    return out.split()[0] if out else None


# ---------------------------------------------------------------------------
# GPU accounting
# ---------------------------------------------------------------------------


SACCT_FIELDS = ("JobID", "JobName", "State", "ElapsedRaw", "NNodes",
                "Submit", "Start", "End")


def sacct_jobs() -> list[dict]:
    """Every attempt of the confirmatory generation job, failures included.

    ``-X`` keeps this to allocations rather than job steps, which is what a
    whole-node billing model cares about. No state filter: a CANCELLED or
    FAILED attempt held the node just as hard as a COMPLETED one.
    """
    cmd = (f"sacct -X --name={JOB_NAME} --starttime={SACCT_STARTTIME} "
           f"--format={','.join(SACCT_FIELDS)} -P --noheader")
    rows = []
    for line in _ssh(cmd).splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) != len(SACCT_FIELDS):
            continue
        row = dict(zip(SACCT_FIELDS, parts))
        row["job_id"] = row["JobID"].split(".")[0]
        try:
            row["elapsed_raw"] = int(row["ElapsedRaw"] or 0)
        except ValueError:
            row["elapsed_raw"] = 0
        try:
            row["n_nodes"] = int(row["NNodes"] or 1)
        except ValueError:
            row["n_nodes"] = 1
        rows.append(row)
    return rows


def job_chunk_map(job_ids: list[str]) -> dict[str, str]:
    """job id -> chunk, read out of each job's own log line.

    ``stage2_confirm_gen.sbatch`` echoes ``[s2confirm-gen] chunk=chunk_NN ...``
    as its first act, so the log is the job's own statement of what it ran.
    """
    mapping: dict[str, str] = {}
    out = _ssh(f"grep -l . {REMOTE_LOG_DIR}/{JOB_NAME}-*.out 2>/dev/null "
               f"| head -200 || true")
    logs = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if logs:
        joined = " ".join(logs)
        grep = _ssh(f"grep -H 'chunk=' {joined} 2>/dev/null || true")
        for line in grep.splitlines():
            path, _, rest = line.partition(":")
            job = _JOBID_FROM_LOG_RE.search(path)
            chunk = _CHUNK_LINE_RE.search(rest)
            if job and chunk:
                mapping.setdefault(job.group(1), chunk.group(1))
    # Fallback for a job whose log has not been flushed yet: slurm still knows
    # the command line it was submitted with. Read-only.
    for job_id in job_ids:
        if job_id in mapping:
            continue
        text = _ssh(f"scontrol show job {job_id} 2>/dev/null || true",
                    check=False)
        chunk = _CHUNK_LINE_RE.search(text) or re.search(r"(chunk_\d\d)", text)
        if chunk:
            mapping[job_id] = chunk.group(1)
    return mapping


def node_hours_by_chunk(jobs: list[dict], mapping: dict[str, str],
                        allow_unattributed: bool) -> tuple[dict, dict]:
    """Per-chunk node-hours, plus the attempts behind each number."""
    per_chunk: dict[str, dict] = {c: {"node_seconds": 0, "attempts": []}
                                  for c in CHUNK_ALLOWLIST}
    unattributed = {"node_seconds": 0, "attempts": []}
    for job in jobs:
        chunk = mapping.get(job["job_id"])
        seconds = job["elapsed_raw"] * max(job["n_nodes"], 1)
        record = {"job_id": job["job_id"], "state": job["State"],
                  "elapsed_raw": job["elapsed_raw"],
                  "n_nodes": job["n_nodes"],
                  "start": job["Start"], "end": job["End"]}
        if chunk in per_chunk:
            per_chunk[chunk]["node_seconds"] += seconds
            per_chunk[chunk]["attempts"].append(record)
        else:
            unattributed["node_seconds"] += seconds
            unattributed["attempts"].append(record)
    if unattributed["node_seconds"] > 0 and not allow_unattributed:
        ids = ", ".join(a["job_id"] for a in unattributed["attempts"])
        raise fatal(
            f"{unattributed['node_seconds']}s of node time on job(s) {ids} "
            "could not be attributed to a chunk. Billing them to nobody would "
            "under-report the run's GPU cost. Re-run with "
            "--allow-unattributed once you have checked what those jobs were.")
    for chunk, rec in per_chunk.items():
        rec["node_hours"] = round(rec["node_seconds"] / 3600.0, 4)
        rec["n_attempts"] = len(rec["attempts"])
        rec["n_failed_attempts"] = sum(
            1 for a in rec["attempts"]
            if not str(a["state"]).upper().startswith("COMPLETED"))
    unattributed["node_hours"] = round(unattributed["node_seconds"] / 3600.0, 4)
    return per_chunk, unattributed


def logged_node_hours(cost_log: Path) -> tuple[float, set[str]]:
    """Node-hours already billed to this run, and the chunks already billed."""
    if not cost_log.exists():
        return 0.0, set()
    total, chunks = 0.0, set()
    with cost_log.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("run_id") != RUN_ID:
                continue
            total += float(entry.get("node_hours") or 0.0)
            if entry.get("variant"):
                chunks.add(str(entry["variant"]))
    return round(total, 4), chunks


# ---------------------------------------------------------------------------
# The join
# ---------------------------------------------------------------------------


def load_manifest() -> dict:
    path = CONFIRM_DIR / "render_manifest.json"
    if not path.exists():
        raise fatal(f"{rel(path)} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_chunk(manifest: dict, chunk: str) -> dict:
    for rec in manifest.get("chunking", {}).get("chunks", []):
        if rec.get("chunk") == chunk:
            return rec
    raise fatal(f"{chunk} is not in render_manifest.json chunking")


def load_items() -> dict:
    path = CONFIRM_DIR / "items_confirm.jsonl"
    if not path.exists():
        raise fatal(f"{rel(path)} not found")
    return {r["item_id"]: r for r in S.read_jsonl(path)}


def verified_prompt_bridge(chunk: str, manifest: dict,
                           *, check_remote: bool) -> tuple[dict, dict]:
    """``(idx -> sha, sha -> meta row)``, with every link checked.

    Refuses the chunk unless the node's prompt file, the committed local copy
    and the manifest's recorded sha256 are the same three bytes, and unless the
    prompt hashes are a bijection with the meta sidecar's ``prompt_sha256``.
    """
    spec = manifest_chunk(manifest, chunk)
    local_prompts = _ROOT / spec["node_prompts_file"]
    local_meta = _ROOT / spec["node_meta_file"]
    for path in (local_prompts, local_meta):
        if not path.exists():
            raise fatal(f"{rel(path)} not found")

    local_sha = R.sha256(local_prompts.read_text(encoding="utf-8"))
    if local_sha != spec["node_prompts_sha256"]:
        raise fatal(f"{rel(local_prompts)} hashes to {local_sha}, manifest "
                    f"records {spec['node_prompts_sha256']}; the committed "
                    "prompt file has been edited")
    meta_sha = R.sha256(local_meta.read_text(encoding="utf-8"))
    if meta_sha != spec["node_meta_sha256"]:
        raise fatal(f"{rel(local_meta)} hashes to {meta_sha}, manifest records "
                    f"{spec['node_meta_sha256']}")
    if check_remote:
        got = remote_sha256(f"{REMOTE_RUN_DIR}/{chunk}.prompts.jsonl")
        if got != spec["node_prompts_sha256"]:
            raise fatal(
                f"{chunk}: the prompt file ON THE NODE hashes to {got}, the "
                f"manifest records {spec['node_prompts_sha256']}. The job "
                "answered prompts that are not the committed ones -- refusing "
                "to join.")

    idx_to_sha, sha_seen = {}, set()
    for row in S.read_jsonl(local_prompts):
        idx = int(row["idx"])
        if idx in idx_to_sha:
            raise fatal(f"{rel(local_prompts)}: duplicate idx {idx}")
        sha = R.sha256(row["prompt"])
        if sha in sha_seen:
            raise fatal(f"{rel(local_prompts)}: prompt_sha256 {sha} appears "
                        "twice; the hash cannot be the join key")
        sha_seen.add(sha)
        idx_to_sha[idx] = sha

    by_sha = {}
    for row in S.read_jsonl(local_meta):
        sha = row["prompt_sha256"]
        if sha in by_sha:
            raise fatal(f"{rel(local_meta)}: duplicate prompt_sha256 {sha}")
        by_sha[sha] = row
    if set(by_sha) != sha_seen:
        raise fatal(
            f"{chunk}: the meta sidecar and the prompt file disagree "
            f"({len(sha_seen - set(by_sha))} prompts with no meta row, "
            f"{len(set(by_sha) - sha_seen)} meta rows with no prompt)")
    return idx_to_sha, by_sha


def build_row(chunk: str, meta: dict, item: dict, got: dict) -> dict:
    """One completion row, in the OE-1 ``cmd_ingest_gemma`` schema.

    ``chunk``, ``idx``, ``h7_bin``, ``cutoff_date``, ``delta_days`` and
    ``item_type`` ride along on top of it: the confirmatory run is chunked and
    carries the H7 arms, and dropping those fields here would force the report
    to re-join against the sidecar for no reason.
    """
    text = (got.get("text") or "").strip()
    tout = int(got.get("tokens_out") or got.get("n_tokens_out") or 0)
    words = R.word_count(text)
    return {
        "chunk": chunk,
        "idx": int(meta["idx"]),
        "item_id": meta["item_id"],
        "canonical_id": meta["canonical_id"],
        "arm": meta["arm"],
        "h7_bin": meta.get("h7_bin"),
        "cutoff_date": meta.get("cutoff_date"),
        "delta_days": meta.get("delta_days"),
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
        "ingested_utc": now(),
    }


def per_arm_stats(rows: list[dict]) -> dict:
    out = {}
    for arm in sorted({r["arm"] for r in rows}):
        sub = [r for r in rows if r["arm"] == arm]
        n_trunc = sum(1 for r in sub if r["truncated"])
        out[arm] = {
            "n": len(sub),
            "n_truncated": n_trunc,
            "truncation_rate": round(n_trunc / len(sub), 4),
            "n_era_violations": sum(1 for r in sub if r["era_violations"]),
            "n_over_word_cap": sum(1 for r in sub if r["over_word_cap"]),
            "n_empty": sum(1 for r in sub if not r["text"]),
            "tokens_in": sum(int(r["tokens_in"]) for r in sub),
            "tokens_out": sum(int(r["tokens_out"]) for r in sub),
        }
    return out


def ingest_chunk(chunk: str, manifest: dict, items: dict, billing: dict,
                 args) -> dict:
    """Pull, join and bill one chunk. Returns its summary dict."""
    t0 = time.time()
    idx_to_sha, by_sha = verified_prompt_bridge(
        chunk, manifest, check_remote=not args.no_remote_hash_check)

    raw_path = NODE_OUT_DIR / f"completions_{chunk}.jsonl"
    marker_path = NODE_OUT_DIR / f"completions_{chunk}.jsonl{DONE_SUFFIX}"
    if not args.no_pull:
        print(f"[ingest] {chunk}: pulling completions from the node")
        _pull(f"{REMOTE_RUN_DIR}/completions_{chunk}.jsonl", raw_path)
        _pull(f"{REMOTE_RUN_DIR}/completions_{chunk}.jsonl{DONE_SUFFIX}",
              marker_path)
    if not raw_path.exists():
        raise fatal(f"{rel(raw_path)} not present after the pull")

    node_rows = S.read_jsonl(raw_path)
    joined, stale, missing = [], [], []
    seen_sha = set()
    for row in node_rows:
        if "idx" not in row:
            raise fatal(f"{rel(raw_path)}: a completion row has no idx; the "
                        "node output format is not what this driver expects")
        sha = idx_to_sha.get(int(row["idx"]))
        if sha is None or sha in seen_sha:
            stale.append(row)
            continue
        seen_sha.add(sha)
        meta = by_sha[sha]
        item = items.get(meta["item_id"])
        if item is None:
            raise fatal(f"item {meta['item_id']} is not in items_confirm.jsonl")
        joined.append(build_row(chunk, meta, item, row))
    for sha, meta in by_sha.items():
        if sha not in seen_sha:
            missing.append(meta["prompt_sha256"])

    if stale:
        print(f"[ingest] {chunk}: {len(stale)} node row(s) do not map to a "
              "prompt in the committed prompt file; dropped, not joined by "
              "position")
    if missing and not args.allow_partial:
        raise fatal(
            f"{chunk}: {len(missing)} of {len(by_sha)} prompts have no "
            "completion. The chunk is not finished (or the job died mid-file). "
            "Re-run when it is, or pass --allow-partial to ingest what exists "
            "-- partial chunks are NOT billed and NOT marked complete.")

    joined.sort(key=lambda r: r["idx"])
    out_path = GEN_DIR / f"completions_{chunk}.jsonl"
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    S.write_jsonl(out_path, joined)

    complete = not missing
    stats = per_arm_stats(joined) if joined else {}
    bill = billing["per_chunk"][chunk]
    summary = {
        "banner": "CONFIRMATORY. Primary-model generations, ingested from "
                  "Leonardo. No scoring and no verdict in this file.",
        "run_id": RUN_ID, "chunk": chunk, "model": MODEL,
        "temperature": TEMPERATURE, "max_output_tokens": MAX_OUTPUT_TOKENS,
        "max_answer_words": MAX_ANSWER_WORDS,
        "join_key": "prompt_sha256",
        "join_note": "idx is used only inside the sha-verified node prompt "
                     "file to recover each completion's prompt text; every "
                     "cross-file link is by hash.",
        "node_prompts_sha256": manifest_chunk(manifest, chunk)[
            "node_prompts_sha256"],
        "node_prompts_sha256_verified_on_node":
            not args.no_remote_hash_check,
        "n_prompts_expected": len(by_sha),
        "n_rows": len(joined),
        "n_missing_completions": len(missing),
        "n_stale_node_rows_dropped": len(stale),
        "complete": complete,
        "tokens_in": sum(int(r["tokens_in"]) for r in joined),
        "tokens_out": sum(int(r["tokens_out"]) for r in joined),
        "n_truncated": sum(1 for r in joined if r["truncated"]),
        "n_era_violations": sum(1 for r in joined if r["era_violations"]),
        "n_over_word_cap": sum(1 for r in joined if r["over_word_cap"]),
        "n_empty": sum(1 for r in joined if not r["text"]),
        "per_arm": stats,
        "node_hours_this_chunk": bill["node_hours"],
        "node_hours_attempts": bill["attempts"],
        "runtime_secs": round(time.time() - t0, 1),
        "ingested_utc": now(),
    }

    if complete and chunk not in billing["already_billed"] and not args.skip_cost:
        prior = billing["logged_node_hours"] + billing["billed_this_run"]
        total = round(prior + bill["node_hours"], 4)
        if total > NODE_HOUR_BUDGET:
            raise fatal(
                f"billing {chunk} at {bill['node_hours']} node-hours would "
                f"take the run to {total}, over the {NODE_HOUR_BUDGET} cap "
                f"({prior} already logged). Stopping without writing the cost "
                "line; this needs an owner decision.")
        entry = build_cost_entry(
            run_id=RUN_ID, model=MODEL, split=SPLIT, variant=chunk,
            n_persons=len({r["canonical_id"] for r in joined}),
            n_calls=len(joined),
            n_retries=bill["n_failed_attempts"],
            n_parse_failures=summary["n_empty"],
            tokens_in=summary["tokens_in"], tokens_out=summary["tokens_out"],
            backend="leonardo-batch", node_hours=bill["node_hours"])
        append_cost_log(entry, COST_LOG)
        billing["billed_this_run"] = round(
            billing["billed_this_run"] + bill["node_hours"], 4)
        billing["already_billed"].add(chunk)
        summary["cost_logged"] = True
        summary["node_hours_after_this_chunk"] = total
        print(f"[ingest] {chunk}: billed {bill['node_hours']} node-hours "
              f"({bill['n_attempts']} attempt(s), "
              f"{bill['n_failed_attempts']} failed); run total {total} of "
              f"{NODE_HOUR_BUDGET}")
    else:
        summary["cost_logged"] = False
        summary["cost_skip_reason"] = (
            "already billed" if chunk in billing["already_billed"]
            else "--skip-cost" if args.skip_cost
            else "chunk incomplete")

    S.write_json(GEN_DIR / f"ingest_summary_{chunk}.json", summary)
    print(f"[ingest] {chunk}: {len(joined)}/{len(by_sha)} rows, "
          f"{summary['n_truncated']} truncated, "
          f"{summary['n_era_violations']} era violations, "
          f"{summary['n_empty']} empty")
    return summary


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def print_status(listing: dict, billing: dict) -> None:
    print("\n=== node state (read-only) ===")
    print(f"{'chunk':10s} {'completions':>12s} {'done marker':>12s} "
          f"{'node-hours':>11s} {'attempts':>9s} {'billed':>7s}")
    for chunk in CHUNK_ALLOWLIST:
        st = listing.get(chunk, {})
        bill = billing["per_chunk"][chunk]
        print(f"{chunk:10s} "
              f"{'yes' if st.get('completions_present') else 'no':>12s} "
              f"{'yes' if st.get('done_marker_present') else 'no':>12s} "
              f"{bill['node_hours']:>11.4f} {bill['n_attempts']:>9d} "
              f"{'yes' if chunk in billing['already_billed'] else 'no':>7s}")
    print(f"node-hours already in the cost log for {RUN_ID}: "
          f"{billing['logged_node_hours']} of {NODE_HOUR_BUDGET}")
    if billing["unattributed"]["node_seconds"]:
        print(f"UNATTRIBUTED node time: "
              f"{billing['unattributed']['node_hours']} node-hours on job(s) "
              + ", ".join(a["job_id"]
                          for a in billing["unattributed"]["attempts"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chunks", nargs="*", default=None,
                    help="chunks to ingest (default: every complete chunk)")
    ap.add_argument("--status", action="store_true",
                    help="report node and billing state, ingest nothing")
    ap.add_argument("--no-pull", action="store_true",
                    help="join whatever is already staged in node_out/")
    ap.add_argument("--no-remote-hash-check", action="store_true",
                    help="skip re-hashing the prompt file on the node")
    ap.add_argument("--allow-partial", action="store_true",
                    help="join a chunk that is still missing completions "
                         "(never billed, never marked complete)")
    ap.add_argument("--allow-unattributed", action="store_true",
                    help="proceed when some node time maps to no chunk")
    ap.add_argument("--skip-cost", action="store_true",
                    help="do not append cost-log lines")
    ap.add_argument("--force", action="store_true",
                    help="re-ingest chunks that already have joined output")
    args = ap.parse_args(argv)

    for chunk in args.chunks or ():
        if chunk not in CHUNK_ALLOWLIST:
            raise fatal(f"{chunk!r} is not in the chunk allowlist "
                        f"{CHUNK_ALLOWLIST}")

    manifest = load_manifest()
    listing = remote_listing()
    jobs = sacct_jobs()
    mapping = job_chunk_map([j["job_id"] for j in jobs])
    per_chunk, unattributed = node_hours_by_chunk(
        jobs, mapping, args.allow_unattributed)
    logged, billed_chunks = logged_node_hours(COST_LOG)
    billing = {"per_chunk": per_chunk, "unattributed": unattributed,
               "logged_node_hours": logged,
               "already_billed": set(billed_chunks),
               "billed_this_run": 0.0}

    # The full accounting trail, written every run: every attempt sacct knows
    # about, including the zero-elapsed cancelled ones, so the billed numbers
    # can be re-derived without another sacct query.
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    S.write_json(GEN_DIR / "node_hours_accounting.json", {
        "banner": "CONFIRMATORY. GPU accounting for the primary-model "
                  "generation jobs. Whole-node billing; every attempt counted.",
        "run_id": RUN_ID, "job_name": JOB_NAME,
        "sacct_query": f"sacct -X --name={JOB_NAME} "
                       f"--starttime={SACCT_STARTTIME} ElapsedRaw",
        "node_hour_budget": NODE_HOUR_BUDGET,
        "attempts": [{"job_id": j["job_id"], "state": j["State"],
                      "elapsed_raw_s": j["elapsed_raw"],
                      "n_nodes": j["n_nodes"],
                      "chunk": mapping.get(j["job_id"]),
                      "node_hours": round(
                          j["elapsed_raw"] * max(j["n_nodes"], 1) / 3600.0, 4),
                      "submit": j["Submit"], "start": j["Start"],
                      "end": j["End"]} for j in jobs],
        "per_chunk_node_hours": {c: per_chunk[c]["node_hours"]
                                 for c in CHUNK_ALLOWLIST},
        "total_node_hours": round(
            sum(j["elapsed_raw"] * max(j["n_nodes"], 1) for j in jobs) / 3600.0,
            4),
        "unattributed_node_hours": unattributed["node_hours"],
        "node_hours_already_logged": logged,
        "recorded_utc": now(),
    })

    print_status(listing, billing)
    if args.status:
        return 0

    ready = [c for c in CHUNK_ALLOWLIST
             if listing[c]["completions_present"]
             and (listing[c]["done_marker_present"] or args.allow_partial)]
    wanted = args.chunks or ready
    todo = []
    for chunk in wanted:
        if chunk not in ready and not args.no_pull:
            print(f"[ingest] {chunk}: not finished on the node yet, skipping")
            continue
        out_path = GEN_DIR / f"completions_{chunk}.jsonl"
        sidecar = GEN_DIR / f"ingest_summary_{chunk}.json"
        if out_path.exists() and sidecar.exists() and not args.force:
            prev = json.loads(sidecar.read_text(encoding="utf-8"))
            if prev.get("complete"):
                print(f"[ingest] {chunk}: already ingested "
                      f"({prev.get('n_rows')} rows), skipping")
                continue
        todo.append(chunk)

    if not todo:
        print("[ingest] nothing to ingest right now.")
        return 0

    items = load_items()
    summaries = [ingest_chunk(c, manifest, items, billing, args) for c in todo]

    print("\n=== ingested ===")
    for s in summaries:
        print(f"{s['chunk']}: {s['n_rows']} rows, complete={s['complete']}, "
              f"node_hours={s['node_hours_this_chunk']}, "
              f"cost_logged={s['cost_logged']}")
    print(f"node-hours logged for {RUN_ID} after this run: "
          f"{round(billing['logged_node_hours'] + billing['billed_this_run'], 4)}"
          f" of {NODE_HOUR_BUDGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
