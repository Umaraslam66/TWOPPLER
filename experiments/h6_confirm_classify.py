#!/usr/bin/env python3
"""Run the frozen H6 follow-up classifier over the confirmatory survivors.

Amendment 2 B2.1 freezes the classifier as **Gemma-4-31B-it under RUBRIC_V1**
(`src/doppler/followup_render.py`, rubric sha256
``053b96cba42ebf03d966db3c22fce2acde3a685d5b4cca9badd556ee248a24da``). This
driver is the confirmatory twin of the dev pass that produced
``results/stage2_pilot/records/classify.jsonl``: same rubric text, same prompt
builder, same rule shortcut, same deterministic decode settings.

Scope, stated so it cannot drift
--------------------------------
* **Grounding side only.** Every case comes from a subject's
  ``grounding_turns.jsonl``. The test interview is never read, never
  classified, never printed. ``test_turns.jsonl`` is not opened anywhere in
  this file.
* **The 89 confirmatory survivors** (``build_full140.json``, ``survived ==
  true``). Dev subjects are asserted absent.
* **No Gemini call, ever.** The only model is the local Gemma on Leonardo.

The rule shortcut (SPEC D9, unchanged from dev)
-----------------------------------------------
A host turn with no guest answer anywhere behind it is NEW-TOPIC by definition
-- nothing exists for it to follow up on -- so it is labelled by rule and costs
no model call. ``followup_render.classifiable_turns`` makes that split; this
driver only writes down what it returns.

Join key
--------
One prompt file, one meta sidecar, joined on per-file 0-based ``idx`` exactly
as the dev pass did. 17 prompts in the confirmatory set are byte-identical to
another prompt (19 duplicate rows in all), so a content hash is **not** a
bijection here and cannot be the join key. The safety the hash still buys is
kept: the prompt file's whole-file sha256 is recorded at build time and
re-checked on the node before any completion is joined, so ``idx`` is only ever
read inside a file proven not to have moved.

Retries (Amendment 2 B4.3)
--------------------------
Up to 2 retry passes over the turns that failed to parse. Decode settings are
identical on every pass (temperature 0.0, seed 0) -- so a retry recovers a
*missing* completion (truncation, engine hiccup, a chunk that never landed) but
reproduces a genuinely unparseable answer byte for byte. That is the honest
reading of the rule and it is recorded rather than papered over with a seed
change the frozen text does not authorise. Turns still unlabelled after pass 3
are dropped from H6 selection and counted, per B4.3.

Usage::

    .venv/bin/python experiments/h6_confirm_classify.py build
    .venv/bin/python experiments/h6_confirm_classify.py push  --pass 1
    .venv/bin/python experiments/h6_confirm_classify.py status
    .venv/bin/python experiments/h6_confirm_classify.py ingest --pass 1
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

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from doppler import followup_render as F  # noqa: E402
from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

RUBRIC_SHA256_EXPECTED = (
    "053b96cba42ebf03d966db3c22fce2acde3a685d5b4cca9badd556ee248a24da")

CONFIRM_DIR = REPO / "results/stage2_confirm"
BUILD_JSON = CONFIRM_DIR / "build_full140.json"
SUBJECTS_DIR = CONFIRM_DIR / "subjects"
DEV_SUBJECTS = REPO / "results/stage2_pilot/dev_subjects.json"

OUT_DIR = CONFIRM_DIR / "h6_classify"
EXPORT_DIR = OUT_DIR / "exports"
NODE_OUT_DIR = OUT_DIR / "node_out"
RECORDS_DIR = OUT_DIR / "records"
MANIFEST = OUT_DIR / "manifest.json"
STATS = OUT_DIR / "stats.json"
COST_LOG = REPO / "results/cost_log.jsonl"

REMOTE_HOST = "leonardo"
REMOTE_ROOT = "/leonardo_work/AIFAC_P02_548/DOPPLER"
REMOTE_RUN = f"{REMOTE_ROOT}/runs/stage2_confirm_h6"
JOB_NAME = "dop-h6-classify"
SSH_OPTS = ("-o", "BatchMode=yes", "-o", "ConnectTimeout=25")

RUN_ID = "stage2_confirm/h6_classify"
#: Phase cap from the closeout plan: 3 node-hours across H6 classify + H6
#: generation. This driver refuses to bill past it.
PHASE_NODE_HOUR_CAP = 3.0
#: Task 1a's own projection gate. Refuse to push if the build projects above it.
PROJECTION_GATE_NODE_HOURS = 1.5

#: Flagged-turn threshold, H6/B3 appendix section 4.3(a), APPROVED 2026-07-28.
#: A subject above this drop rate is *analyzed separately*, never excluded.
FLAGGED_DROP_RATE = 0.05

MAX_PASSES = 3          # pass 1 + 2 retries (B4.3)

META_FIELDS = ("canonical_id", "transcript_id", "turn_idx", "target_host",
               "prompt_sha256", "prompt_words")


def fatal(msg: str) -> SystemExit:
    return SystemExit(f"FATAL: {msg}")


def read_jsonl(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def write_json(path: Path, doc: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_rubric() -> None:
    if F.RUBRIC_SHA256 != RUBRIC_SHA256_EXPECTED:
        raise fatal(
            "RUBRIC_V1 has moved: "
            f"{F.RUBRIC_SHA256} != {RUBRIC_SHA256_EXPECTED}. The classifier is "
            "frozen by Amendment 2 B2.1; stop and re-freeze on purpose.")


# --------------------------------------------------------------------------
# Subjects
# --------------------------------------------------------------------------


def survivors() -> list[dict]:
    doc = json.loads(BUILD_JSON.read_text())
    rows = [s for s in doc["subjects"] if s.get("survived")]
    if len(rows) != doc["n_survived"]:
        raise fatal(f"survivor count disagrees with build: {len(rows)} vs "
                    f"{doc['n_survived']}")
    dev = json.loads(DEV_SUBJECTS.read_text())
    dev_ids = {s["canonical_id"] for s in dev["subjects"]}
    overlap = sorted({s["canonical_id"] for s in rows} & dev_ids)
    if overlap:
        raise fatal(f"dev subjects leaked into the confirmatory set: {overlap}")
    return sorted(rows, key=lambda s: s["canonical_id"])


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------


def build() -> dict:
    """Every classifier case over the 89 survivors' grounding transcripts."""
    check_rubric()
    subjects = survivors()
    cases: list[dict] = []
    rule_labels: list[dict] = []
    per_subject: dict[str, dict] = {}

    for subject in subjects:
        cid = subject["canonical_id"]
        sdir = SUBJECTS_DIR / cid
        # Guard: the test interview is off-limits. Assert the file we read is
        # the grounding one and that its transcripts are the split's grounding
        # clusters, never the test cluster.
        split = json.loads((sdir / "split.json").read_text())
        test_tid = split["test"]["transcript_id"] if isinstance(
            split.get("test"), dict) else None
        turns = read_jsonl(sdir / "grounding_turns.jsonl")
        by_tid: dict[str, list[dict]] = {}
        for turn in turns:
            by_tid.setdefault(turn["transcript_id"], []).append(turn)
        if test_tid is not None and test_tid in by_tid:
            raise fatal(f"{cid}: the test transcript {test_tid} appears in "
                        "grounding_turns.jsonl")

        n_model = n_rule = 0
        for tid in sorted(by_tid):
            ordered = sorted(by_tid[tid], key=lambda t: t["turn_idx"])
            for case in F.classifiable_turns(ordered):
                if case.get("source") == "rule":
                    rule_labels.append({
                        "canonical_id": cid, "transcript_id": tid,
                        "turn_idx": case["turn_idx"], "label": case["label"],
                        "source": "rule",
                    })
                    n_rule += 1
                    continue
                prompt = F.classify_prompt(
                    prev_host=case["prev_host"],
                    guest_answer=case["guest_answer"],
                    target_host=case["target_host"])
                cases.append({
                    "canonical_id": cid,
                    "transcript_id": tid,
                    "turn_idx": case["turn_idx"],
                    "target_host": case["target_host"][:240],
                    "prompt": prompt,
                    "prompt_sha256": F.sha256(prompt),
                    "prompt_words": len(prompt.split()),
                    "max_output_tokens": F.MAX_OUTPUT_TOKENS,
                })
                n_model += 1
        per_subject[cid] = {
            "canonical_id": cid,
            "canonical_name": subject.get("canonical_name"),
            "stratum": subject.get("stratum"),
            "n_transcripts": len(by_tid),
            "n_model_cases": n_model,
            "n_rule_labels": n_rule,
            "n_host_turns": n_model + n_rule,
        }

    # Every prompt must open on the frozen rubric; cheap and catches a bad edit.
    for case in cases:
        if not case["prompt"].startswith(F.RUBRIC_V1):
            raise fatal(f"{case['canonical_id']}/{case['transcript_id']} turn "
                        f"{case['turn_idx']}: prompt does not open on RUBRIC_V1")

    prompts_path = EXPORT_DIR / "prompts_classify.jsonl"
    meta_path = EXPORT_DIR / "meta_classify.jsonl"
    rule_path = EXPORT_DIR / "labels_rule.jsonl"
    write_jsonl(prompts_path, [
        {"idx": i, "prompt": c["prompt"],
         "max_output_tokens": c["max_output_tokens"]}
        for i, c in enumerate(cases)])
    write_jsonl(meta_path, [
        dict({"idx": i}, **{f: c.get(f) for f in META_FIELDS})
        for i, c in enumerate(cases)])
    write_jsonl(rule_path, rule_labels)

    words = sorted(c["prompt_words"] for c in cases)
    n_unique = len({c["prompt_sha256"] for c in cases})
    doc = {
        "run_id": RUN_ID,
        "purpose": "H6 follow-up/new-topic classification of the 89 "
                   "confirmatory survivors' GROUNDING host turns "
                   "(Amendment 2 B2.1). Grounding only; no test interview is "
                   "read or classified.",
        "model": "Gemma-4-31B-it",
        "rubric_sha256": F.RUBRIC_SHA256,
        "followup_render_file_sha256": sha256_file(
            REPO / "src/doppler/followup_render.py"),
        "decode": {"temperature": 0.0, "seed": 0, "tp": 4,
                   "max_model_len": 8192, "gpu_mem_util": 0.92,
                   "max_output_tokens": F.MAX_OUTPUT_TOKENS},
        "n_subjects": len(subjects),
        "n_host_turns": len(cases) + len(rule_labels),
        "n_model_cases": len(cases),
        "n_rule_labels": len(rule_labels),
        "n_unique_prompts": n_unique,
        "n_duplicate_prompt_rows": len(cases) - n_unique,
        "prompt_words": {
            "max": words[-1], "median": words[len(words) // 2],
            "mean": round(sum(words) / len(words), 2)},
        "files": {
            "prompts": {"path": str(prompts_path.relative_to(REPO)),
                        "sha256": sha256_file(prompts_path),
                        "n_rows": len(cases)},
            "meta": {"path": str(meta_path.relative_to(REPO)),
                     "sha256": sha256_file(meta_path), "n_rows": len(cases)},
            "labels_rule": {"path": str(rule_path.relative_to(REPO)),
                            "sha256": sha256_file(rule_path),
                            "n_rows": len(rule_labels)},
        },
        "per_subject": per_subject,
        "projection": projection(len(cases)),
        "max_passes": MAX_PASSES,
    }
    write_json(MANIFEST, doc)
    return doc


def projection(n_prompts: int) -> dict:
    """Node-hours projected from the dev classifier pass, not from the gen run.

    The dev classify slice is the right yardstick: same rubric, same 80-token
    cap, same engine. It ran 469 prompts in 10.14 s of generation after a
    201.57 s engine init (``results/stage2_pilot/node/
    completions_classify.jsonl.summary.json``). The confirmatory *generation*
    run (1,911 prompts, 0.6028 node-hours) is a poor comparator -- its prompts
    are ~10x longer and its outputs ~30x longer -- so it is quoted only as an
    upper bound sanity check.
    """
    dev_prompts, dev_gen_s, dev_init_s = 469, 10.14, 201.57
    gen_s = dev_gen_s / dev_prompts * n_prompts
    init_s = 230.0                     # worst engine init seen on this stack
    slurm_overhead_s = 120.0           # prologue/epilogue/teardown, generous
    wall_s = init_s + gen_s + slurm_overhead_s
    return {
        "basis": "results/stage2_pilot/node/completions_classify.jsonl.summary.json",
        "dev_prompts": dev_prompts,
        "dev_generation_seconds": dev_gen_s,
        "n_prompts": n_prompts,
        "projected_generation_seconds": round(gen_s, 1),
        "assumed_engine_init_seconds": init_s,
        "assumed_slurm_overhead_seconds": slurm_overhead_s,
        "projected_wall_seconds_pass1": round(wall_s, 1),
        "projected_node_hours_pass1": round(wall_s / 3600.0, 4),
        "projected_node_hours_worst_case_3_passes": round(
            (wall_s + 2 * (init_s + slurm_overhead_s + 5)) / 3600.0, 4),
        "gate_node_hours": PROJECTION_GATE_NODE_HOURS,
    }


# --------------------------------------------------------------------------
# Node I/O
# --------------------------------------------------------------------------


def _ssh(command: str, *, timeout: int = 180, check: bool = True) -> str:
    proc = subprocess.run(("ssh", *SSH_OPTS, REMOTE_HOST, command),
                          capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise fatal(f"ssh failed ({proc.returncode}) for {command!r}: "
                    f"{proc.stderr.strip()[:400]}")
    return proc.stdout


def _push_file(local: Path, remote: str) -> None:
    if shutil.which("rsync"):
        proc = subprocess.run(
            ("rsync", "-az", "-e", "ssh " + " ".join(SSH_OPTS),
             str(local), f"{REMOTE_HOST}:{remote}"),
            capture_output=True, text=True, timeout=900)
        if proc.returncode == 0:
            return
        print(f"[push] rsync failed ({proc.returncode}), falling back to scp",
              file=sys.stderr)
    proc = subprocess.run(("scp", *SSH_OPTS, str(local),
                           f"{REMOTE_HOST}:{remote}"),
                          capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        raise fatal(f"scp failed: {proc.stderr.strip()[:400]}")


def _pull_file(remote: str, local: Path) -> bool:
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


def pass_name(n: int) -> str:
    return f"pass{n}"


def push(pass_no: int) -> None:
    """Stage one pass's prompt file (and the sbatch) on the node."""
    doc = json.loads(MANIFEST.read_text())
    proj = doc["projection"]["projected_node_hours_worst_case_3_passes"]
    if proj > PROJECTION_GATE_NODE_HOURS:
        raise fatal(f"projection {proj} node-hours exceeds the "
                    f"{PROJECTION_GATE_NODE_HOURS} gate; stop and report")
    name = pass_name(pass_no)
    local = (EXPORT_DIR / "prompts_classify.jsonl" if pass_no == 1
             else EXPORT_DIR / f"prompts_{name}.jsonl")
    if not local.exists():
        raise fatal(f"{local} does not exist; build the pass first")
    _ssh(f"mkdir -p {REMOTE_RUN}")
    _push_file(local, f"{REMOTE_RUN}/{name}.prompts.jsonl")
    _push_file(REPO / "experiments/h6_classify_gen.sbatch",
               f"{REMOTE_ROOT}/jobs/h6_classify_gen.sbatch")
    remote_sha = _ssh(
        f"sha256sum {REMOTE_RUN}/{name}.prompts.jsonl").split()[0]
    local_sha = sha256_file(local)
    if remote_sha != local_sha:
        raise fatal(f"{name}: prompt file sha differs after push "
                    f"({remote_sha} != {local_sha})")
    print(f"[push] {name}: {sum(1 for _ in local.open())} prompts, "
          f"sha {local_sha[:16]}... verified on node")
    print(f"[push] submit with: ssh {REMOTE_HOST} "
          f"'cd {REMOTE_ROOT} && sbatch jobs/h6_classify_gen.sbatch {name}'")


# --------------------------------------------------------------------------
# Billing
# --------------------------------------------------------------------------


def sacct_node_hours() -> dict:
    """Every attempt of this job name, billed at elapsed x allocated nodes."""
    out = _ssh(f"sacct -X --name={JOB_NAME} --starttime=2026-07-01 "
               "--format=JobID,JobName,State,Elapsed,NNodes,Start,End "
               "--parsable2 --noheader")
    jobs = []
    total_s = 0.0
    for line in out.splitlines():
        if not line.strip():
            continue
        jobid, jobname, state, elapsed, nnodes, start, end = line.split("|")[:7]
        secs = _elapsed_seconds(elapsed) * int(nnodes or 1)
        total_s += secs
        jobs.append({"job_id": jobid, "state": state, "elapsed": elapsed,
                     "nnodes": int(nnodes or 1),
                     "node_seconds": round(secs, 1),
                     "start": start, "end": end})
    return {"jobs": jobs, "n_attempts": len(jobs),
            "node_seconds_all_attempts": round(total_s, 1),
            "node_hours_all_attempts": round(total_s / 3600.0, 4)}


def _elapsed_seconds(text: str) -> float:
    m = re.match(r"^(?:(\d+)-)?(\d+):(\d+):(\d+(?:\.\d+)?)$", text.strip())
    if not m:
        return 0.0
    days, hh, mm, ss = m.groups()
    return (int(days or 0) * 86400 + int(hh) * 3600 + int(mm) * 60 + float(ss))


def logged_node_hours() -> float:
    if not COST_LOG.exists():
        return 0.0
    total = 0.0
    for line in COST_LOG.read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("run_id") == RUN_ID:
            total += float(entry.get("node_hours") or 0.0)
    return round(total, 4)


# --------------------------------------------------------------------------
# Ingest
# --------------------------------------------------------------------------


def parse_why(text: str | None) -> str | None:
    if not text:
        return None
    for line in text.splitlines():
        stripped = line.strip().lstrip(">#*_- ")
        if stripped.upper().startswith("WHY:"):
            return stripped[4:].strip().strip("*_`\"'")
    return None


def ingest(pass_no: int, *, skip_cost: bool = False) -> dict:
    """Pull one pass's completions, label what parsed, stage the next retry."""
    check_rubric()
    doc = json.loads(MANIFEST.read_text())
    name = pass_name(pass_no)

    remote_out = f"{REMOTE_RUN}/completions_{name}.jsonl"
    local_out = NODE_OUT_DIR / f"completions_{name}.jsonl"
    ok = _pull_file(remote_out, local_out)
    if not ok:
        raise fatal(f"{name}: no completions on the node at {remote_out}")
    _pull_file(remote_out + ".summary.json", Path(str(local_out) + ".summary.json"))

    # The node must have read the file we built. Re-check its sha before any
    # idx is trusted.
    prompts_local = (EXPORT_DIR / "prompts_classify.jsonl" if pass_no == 1
                     else EXPORT_DIR / f"prompts_{name}.jsonl")
    remote_sha = _ssh(f"sha256sum {REMOTE_RUN}/{name}.prompts.jsonl").split()[0]
    if remote_sha != sha256_file(prompts_local):
        raise fatal(f"{name}: the node's prompt file is not the one we built; "
                    "refusing to join by idx")

    metas = read_jsonl(EXPORT_DIR / ("meta_classify.jsonl" if pass_no == 1
                                     else f"meta_{name}.jsonl"))
    comps = {int(r["idx"]): r for r in read_jsonl(local_out)}

    rows = []
    for meta in metas:
        comp = comps.get(int(meta["idx"]))
        text = comp.get("text") if comp else None
        label = F.parse_label(text)
        rows.append({
            "canonical_id": meta["canonical_id"],
            "transcript_id": meta["transcript_id"],
            "turn_idx": meta["turn_idx"],
            "target_host": meta.get("target_host"),
            "prompt_sha256": meta["prompt_sha256"],
            "label": label,
            "source": "model",
            "why": parse_why(text),
            "parse_failure": label is None,
            "missing_completion": comp is None,
            "raw_response": (text or "")[:600],
            "tokens_in": int((comp or {}).get("tokens_in", 0) or 0),
            "tokens_out": int((comp or {}).get("tokens_out", 0) or 0),
            "pass": pass_no,
        })
    write_jsonl(RECORDS_DIR / f"model_{name}.jsonl", rows)

    failed = [r for r in rows if r["parse_failure"]]
    print(f"[ingest] {name}: {len(rows)} model rows, {len(failed)} unlabelled "
          f"({sum(1 for r in rows if r['missing_completion'])} missing "
          "completions)")

    # Stage the next retry pass, if B4.3 still allows one.
    if failed and pass_no < MAX_PASSES:
        nxt = pass_name(pass_no + 1)
        keys = {(r["canonical_id"], r["transcript_id"], r["turn_idx"])
                for r in failed}
        src_meta = read_jsonl(EXPORT_DIR / "meta_classify.jsonl")
        src_prompts = {r["idx"]: r for r in read_jsonl(
            EXPORT_DIR / "prompts_classify.jsonl")}
        keep = [m for m in src_meta
                if (m["canonical_id"], m["transcript_id"], m["turn_idx"]) in keys]
        write_jsonl(EXPORT_DIR / f"prompts_{nxt}.jsonl", [
            {"idx": i, "prompt": src_prompts[m["idx"]]["prompt"],
             "max_output_tokens": src_prompts[m["idx"]]["max_output_tokens"]}
            for i, m in enumerate(keep)])
        write_jsonl(EXPORT_DIR / f"meta_{nxt}.jsonl", [
            dict(m, idx=i) for i, m in enumerate(keep)])
        print(f"[ingest] staged {len(keep)} prompts for {nxt} "
              f"(push --pass {pass_no + 1})")

    bill = sacct_node_hours()
    already = logged_node_hours()
    summary = {"pass": pass_no, "n_model_rows": len(rows),
               "n_unlabelled": len(failed), "billing": bill,
               "node_hours_already_logged": already}

    if not skip_cost:
        delta = round(bill["node_hours_all_attempts"] - already, 4)
        if delta <= 0:
            print(f"[cost] nothing new to bill (sacct {bill['node_hours_all_attempts']}"
                  f" vs logged {already})")
        else:
            total = round(already + delta, 4)
            if total > PHASE_NODE_HOUR_CAP:
                raise fatal(f"billing {delta} node-hours would take the run to "
                            f"{total}, past the {PHASE_NODE_HOUR_CAP} phase cap")
            entry = build_cost_entry(
                run_id=RUN_ID, model="Gemma-4-31B-it",
                split="stage2_confirm_h6_classify", n_persons=doc["n_subjects"],
                n_calls=len(rows),
                n_retries=(pass_no - 1),
                n_parse_failures=len(failed),
                tokens_in=sum(r["tokens_in"] for r in rows),
                tokens_out=sum(r["tokens_out"] for r in rows),
                variant=name, backend="leonardo-batch", node_hours=delta)
            append_cost_log(entry, COST_LOG)
            summary["cost_logged"] = delta
            print(f"[cost] logged {delta} node-hours for {name} "
                  f"(run total {total}, cap {PHASE_NODE_HOUR_CAP})")
    return summary


# --------------------------------------------------------------------------
# Finalise
# --------------------------------------------------------------------------


def finalise() -> dict:
    """Merge every pass into one records file and compute the B4.3 stats."""
    check_rubric()
    doc = json.loads(MANIFEST.read_text())
    best: dict[tuple, dict] = {}
    passes = []
    for n in range(1, MAX_PASSES + 1):
        path = RECORDS_DIR / f"model_{pass_name(n)}.jsonl"
        if not path.exists():
            continue
        passes.append(n)
        for row in read_jsonl(path):
            key = (row["canonical_id"], row["transcript_id"], row["turn_idx"])
            prior = best.get(key)
            # A later pass only ever replaces an unlabelled row.
            if prior is None or (prior["parse_failure"] and not row["parse_failure"]):
                best[key] = row
    model_rows = [best[k] for k in sorted(best)]
    rule_rows = read_jsonl(EXPORT_DIR / "labels_rule.jsonl")
    if len(model_rows) != doc["n_model_cases"]:
        raise fatal(f"records cover {len(model_rows)} of "
                    f"{doc['n_model_cases']} model cases")
    write_jsonl(RECORDS_DIR / "classify.jsonl", model_rows + rule_rows)

    per_subject: dict[str, dict] = {}
    for row in model_rows:
        e = per_subject.setdefault(row["canonical_id"], {
            "FOLLOW-UP": 0, "NEW-TOPIC": 0, "dropped": 0, "rule": 0,
            "n_model_cases": 0})
        e["n_model_cases"] += 1
        if row["label"] is None:
            e["dropped"] += 1
        else:
            e[row["label"]] += 1
    for row in rule_rows:
        e = per_subject.setdefault(row["canonical_id"], {
            "FOLLOW-UP": 0, "NEW-TOPIC": 0, "dropped": 0, "rule": 0,
            "n_model_cases": 0})
        e["rule"] += 1
    for cid, e in per_subject.items():
        e["drop_rate"] = (round(e["dropped"] / e["n_model_cases"], 6)
                          if e["n_model_cases"] else 0.0)
        e["flagged_analyzed_separately"] = e["drop_rate"] > FLAGGED_DROP_RATE

    dropped = [r for r in model_rows if r["label"] is None]
    out = {
        "run_id": RUN_ID,
        "model": "Gemma-4-31B-it",
        "rubric_sha256": F.RUBRIC_SHA256,
        "passes_run": passes,
        "n_subjects": doc["n_subjects"],
        "n_host_turns": doc["n_host_turns"],
        "n_rule_labels": len(rule_rows),
        "n_model_cases": len(model_rows),
        "n_labelled_by_model": sum(1 for r in model_rows if r["label"]),
        "n_dropped_after_retries": len(dropped),
        "corpus_drop_rate": round(len(dropped) / len(model_rows), 6),
        "label_counts": {
            "FOLLOW-UP": sum(1 for r in model_rows if r["label"] == "FOLLOW-UP"),
            "NEW-TOPIC": sum(1 for r in model_rows if r["label"] == "NEW-TOPIC"),
            "rule_NEW-TOPIC": len(rule_rows),
        },
        "flagged_turn_threshold": FLAGGED_DROP_RATE,
        "flagged_subjects": sorted(
            cid for cid, e in per_subject.items()
            if e["flagged_analyzed_separately"]),
        "dropped_turns": [
            {k: r[k] for k in ("canonical_id", "transcript_id", "turn_idx",
                               "missing_completion", "pass")}
            for r in dropped],
        "per_subject": dict(sorted(per_subject.items())),
        "node_hours_logged": logged_node_hours(),
        "records": str((RECORDS_DIR / "classify.jsonl").relative_to(REPO)),
    }
    write_json(STATS, out)
    print(f"[final] {out['n_host_turns']} host turns = "
          f"{out['n_model_cases']} model + {out['n_rule_labels']} rule")
    print(f"[final] labels: {out['label_counts']}")
    print(f"[final] dropped after retries: {out['n_dropped_after_retries']}")
    print(f"[final] flagged subjects (> {FLAGGED_DROP_RATE:.0%} drop rate): "
          f"{out['flagged_subjects'] or 'none'}")
    print(f"[final] node-hours logged: {out['node_hours_logged']}")
    return out


def status() -> None:
    print(_ssh(f"squeue -u $USER -o '%.12i %.20j %.10T %.10M %.6D' ; "
               f"echo '--- sacct ---' ; sacct -X --name={JOB_NAME} "
               "--starttime=2026-07-01 "
               "--format=JobID,JobName,State,Elapsed,NNodes,Start,End"))
    print(_ssh(f"ls -la {REMOTE_RUN} 2>/dev/null || echo '(no run dir yet)'"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command",
                    choices=("build", "push", "status", "ingest", "finalise"))
    ap.add_argument("--pass", dest="pass_no", type=int, default=1)
    ap.add_argument("--skip-cost", action="store_true")
    args = ap.parse_args()

    if args.command == "build":
        doc = build()
        p = doc["projection"]
        print(f"[build] {doc['n_subjects']} subjects, {doc['n_host_turns']} "
              f"host turns: {doc['n_model_cases']} model + "
              f"{doc['n_rule_labels']} rule")
        print(f"[build] prompts: {doc['n_unique_prompts']} unique of "
              f"{doc['n_model_cases']} (max {doc['prompt_words']['max']} words)")
        print(f"[build] projected {p['projected_node_hours_pass1']} node-hours "
              f"pass 1, {p['projected_node_hours_worst_case_3_passes']} worst "
              f"case over 3 passes (gate {PROJECTION_GATE_NODE_HOURS})")
        if p["projected_node_hours_worst_case_3_passes"] > PROJECTION_GATE_NODE_HOURS:
            raise fatal("projection exceeds the gate; stop and report")
    elif args.command == "push":
        push(args.pass_no)
    elif args.command == "status":
        status()
    elif args.command == "ingest":
        ingest(args.pass_no, skip_cost=args.skip_cost)
    elif args.command == "finalise":
        finalise()


if __name__ == "__main__":
    main()
