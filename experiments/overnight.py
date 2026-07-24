"""Overnight Stage-1E batch (EXP1..EXP5): bootstrap, export, ingest, report.

TRAINING and DERIVATION splits only. The confirm split does not exist, is not
drawn here, and must not be drawn until the owner commits the bar-lock
addendum. Nothing in this file locks a bar.

The five experiments
--------------------
EXP1  tie-break. Three adaptive variants, all with a SEEDED RANDOM tie-break
      instead of the pilot's lowest-item-index rule (which decided 51.5% of the
      pilot's questions and is biased towards R-items):
      (a) entropy scorer, run out to k=48 -- doubles as EXP4's adaptive arm;
      (b) EV-variance scorer, to k=20;
      (c) entropy scorer with the 0.05-grid elicitation wording, to k=20.
EXP2  best fixed order, derived on a fresh 2,000-person derivation split
      (no LLM, ridge greedy) and then applied to train-150. The pilot's fixed
      order was picked on the same 150 people it was scored on; this one is
      the honest version.
EXP3  selection ladder: does target-aware expected-information-gain beat
      self-uncertainty? Go/no-go evidence for future RL policy work.
EXP4  budget curve: where does the adaptive edge peak, and where does
      everything saturate towards the all-48 gate reference?
EXP5  imposter gradient: does a MORE similar wrong person mislead less, or
      more? Rehearses Stage 2's same-domain imposter.

Reuse policy: an arm that is unchanged from the pilot is never re-bought. The
random arm reuses the pilot's k in {1,2,4,8,12,16,20} and buys only
{3,5,28,36,48}; the random-imposter, baseline and own-profile arms at k=12/20
are reused verbatim.

Subcommands
-----------
``plan``       print the per-job node-hour projection and the budget check.
``bootstrap``  create the five run dirs, their config.json, their sbatch files
               and the manifest. No model calls.
``export``     build the EXP2+EXP4+EXP5 static prompt file and the EXP3 pack.
``ingest``     join returned completions back into per-arm records + summaries.
``report``     write the per-experiment result tables.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from doppler import adaptive as A  # noqa: E402
from doppler import adaptive_render as R  # noqa: E402
from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402
from doppler.data import (  # noqa: E402
    TIPI_ITEMS,
    clean_riasec,
    load_codebook,
    load_riasec,
)
from doppler.scoring import summarize  # noqa: E402

DATA_DIR = _ROOT / "data"
RESULTS_DIR = _ROOT / "results"
MANIFEST = RESULTS_DIR / "overnight_manifest.json"

#: Hard budget rules for tonight (owner's directive).
PER_JOB_CAP = 4.0
BATCH_CAP = 12.0
EXP3_CAP = 3.0

REMOTE = "leonardo"
NODE_ROOT = "/leonardo_work/AIFAC_P02_548/DOPPLER"
NODE_RUNS = f"{NODE_ROOT}/runs/overnight"
NODE_JOBS = f"{NODE_ROOT}/jobs"
ACCOUNT = "AIFAC_P02_548"
MODEL = f"{NODE_ROOT}/models/Gemma-4-31B-it"

#: The pilot run whose completions are reused wherever an arm is unchanged.
PILOT_RUN = "adaptive_train_20260724-210916"


# ---------------------------------------------------------------------------
# Experiment definitions
# ---------------------------------------------------------------------------


def experiments() -> dict:
    """Per-experiment config: what it runs, what it reuses, what it costs."""
    proj = A.project_overnight()["jobs"]
    return {
        "overnight_exp1a": {
            "experiment": "EXP1a",
            "title": "adaptive, entropy scorer, seeded random tie-break, k to 48",
            "kind": "adaptive",
            "split": "train150",
            "n_persons": A.TRAIN_N,
            "scorer": "entropy",
            "tiebreak": "random",
            "tiebreak_seed": A.TIEBREAK_SEED,
            "interest_grid": "standard",
            "max_reveals": 48,
            "checkpoints": list(A.CHECKPOINTS_EXT),
            "walltime": "02:30:00",
            "doubles_as": "EXP4 adaptive arm",
            "compare_against": f"pilot adaptive arm in results/{PILOT_RUN}",
            "reuses": [],
            "projection": proj["exp1a_entropy_random_k48"],
        },
        "overnight_exp1b": {
            "experiment": "EXP1b",
            "title": "adaptive, EV-variance scorer, seeded random tie-break, k to 20",
            "kind": "adaptive",
            "split": "train150",
            "n_persons": A.TRAIN_N,
            "scorer": "ev_variance",
            "tiebreak": "random",
            "tiebreak_seed": A.TIEBREAK_SEED,
            "interest_grid": "standard",
            "max_reveals": 20,
            "checkpoints": list(A.CHECKPOINTS_K20),
            "walltime": "01:30:00",
            "compare_against": f"pilot adaptive arm in results/{PILOT_RUN}",
            "reuses": [],
            "projection": proj["exp1b_evvariance_k20"],
        },
        "overnight_exp1c": {
            "experiment": "EXP1c",
            "title": "adaptive, entropy scorer, random tie-break, 0.05 probability grid, k to 20",
            "kind": "adaptive",
            "split": "train150",
            "n_persons": A.TRAIN_N,
            "scorer": "entropy",
            "tiebreak": "random",
            "tiebreak_seed": A.TIEBREAK_SEED,
            "interest_grid": "fine",
            "max_reveals": 20,
            "checkpoints": list(A.CHECKPOINTS_K20),
            "walltime": "01:30:00",
            "compare_against": f"pilot adaptive arm in results/{PILOT_RUN}",
            "reuses": [],
            "projection": proj["exp1c_finegrid_k20"],
        },
        "overnight_exp245": {
            "experiment": "EXP2 + EXP4 + EXP5 (shared static job)",
            "title": "frozen derivation order, extended random checkpoints, "
                     "nearest-neighbour imposter",
            "kind": "static",
            "split": "train150",
            "n_persons": A.TRAIN_N,
            "arms": {
                "fixed_deriv": {
                    "experiment": "EXP2",
                    "checkpoints": list(A.CHECKPOINTS_EXT),
                    "order_from": "results/overnight_exp2/fixed_order_derivation.json",
                    "note": "order frozen on the 2,000-person derivation split; "
                            "these 150 people had no say in picking it",
                },
                "random_ext": {
                    "experiment": "EXP4",
                    "checkpoints": list(A.CHECKPOINTS_RANDOM_NEW),
                    "note": "continues each person's pilot permutation past "
                            "k=20; pilot k in {1,2,4,8,12,16,20} reused verbatim",
                },
                "nn_imposter": {
                    "experiment": "EXP5",
                    "checkpoints": list(A.CHECKPOINTS_IMPOSTER),
                    "note": "profile of the most cosine-similar OTHER person in "
                            "train-150, on the 48 interest ratings; reveal "
                            "positions mirror the random arm",
                },
            },
            "walltime": "01:00:00",
            "reuses": [
                f"results/{PILOT_RUN}/baseline (k=0)",
                f"results/{PILOT_RUN}/random (k in 1,2,4,8,12,16,20)",
                f"results/{PILOT_RUN}/imposter (random imposter, k=12,20)",
            ],
            "projection": proj["exp245_static"],
        },
        "overnight_exp3": {
            "experiment": "EXP3",
            "title": "selection ladder: expected information gain on TIPI "
                     "targets vs self-uncertainty",
            "kind": "eig",
            "split": "train150 subset",
            "n_persons": A.EXP3_N,
            "max_reveals": 20,
            "checkpoints": list(A.CHECKPOINTS_K20),
            "top_n": 5,
            "hypotheticals": [1, 3, 5],
            "tiebreak": "random",
            "tiebreak_seed": A.TIEBREAK_SEED,
            "walltime": "03:30:00",
            "budget_cap_node_hours": EXP3_CAP,
            "ladder": {
                "a": "greedy self-uncertainty -- NOT rerun; restrict EXP1a/EXP1b "
                     "curves onto these 100 persons",
                "b": "greedy expected information gain on the 10 TIPI targets",
                "c": "one-step lookahead of (b) -- only if budget allows after (b)",
            },
            "reuses": ["EXP1a and EXP1b curves restricted to the first 100 "
                       "persons of the train split"],
            "projection": proj["exp3_eig_ladder"],
        },
    }


# ---------------------------------------------------------------------------
# Budget gate
# ---------------------------------------------------------------------------


def check_budget(cfgs: dict) -> bool:
    """Print the projection and refuse anything over the caps."""
    ok = True
    total = 0.0
    print("=== projected node-hours ===")
    for name, cfg in cfgs.items():
        hours = cfg["projection"]["projected_node_hours"]
        total += hours
        flag = ""
        if hours > PER_JOB_CAP:
            flag, ok = "  <-- OVER PER-JOB CAP, ABORT", False
        if cfg["kind"] == "eig" and hours > EXP3_CAP:
            flag, ok = f"  <-- OVER EXP3 CAP {EXP3_CAP}, ABORT", False
        print(f"  {name:20s} {hours:6.3f}  "
              f"({cfg['projection']['total_calls']:,} calls){flag}")
    print(f"  {'BATCH TOTAL':20s} {total:6.3f}  "
          f"(per-job cap {PER_JOB_CAP}, batch cap {BATCH_CAP})")
    if total > BATCH_CAP:
        print("[fatal] batch exceeds the total cap.", file=sys.stderr)
        ok = False
    return ok


def cmd_plan(_args) -> int:
    return 0 if check_budget(experiments()) else 3


# ---------------------------------------------------------------------------
# sbatch generation
# ---------------------------------------------------------------------------


HEADER = """#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --partition=boost_usr_prod
#SBATCH --account={account}
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time={walltime}
#SBATCH --output={node_root}/logs/%x-%j.out
#
# {title}
# Projected {hours:.3f} node-hours (per-job cap {cap}).
set -euo pipefail
D={node_root}
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
echo "[{name}] node=$(hostname) start=$(date -u +%FT%TZ)"
"""

FOOTER = '\necho "[{name}] DONE $(date -u +%FT%TZ)"\n'


def sbatch_text(name: str, cfg: dict) -> str:
    head = HEADER.format(job_name=f"dop-{name.replace('overnight_', '')}",
                         account=ACCOUNT, walltime=cfg["walltime"],
                         node_root=NODE_ROOT, title=cfg["title"],
                         hours=cfg["projection"]["projected_node_hours"],
                         cap=PER_JOB_CAP, name=name)
    out = f"{NODE_RUNS}/{name}"
    if cfg["kind"] == "adaptive":
        body = (
            f'python jobs/adaptive_node_driver.py \\\n'
            f'    --pack "$D/runs/adaptive_train/pack_node.json" \\\n'
            f'    --outdir "{out}" \\\n'
            f'    --model-dir "{MODEL}" --tp 4 --max-model-len 2048 \\\n'
            f'    --gpu-mem-util 0.92 --temperature 0.0 \\\n'
            f'    --scorer {cfg["scorer"]} --tiebreak {cfg["tiebreak"]} \\\n'
            f'    --tiebreak-seed {cfg["tiebreak_seed"]} \\\n'
            f'    --interest-grid {cfg["interest_grid"]} \\\n'
            f'    --max-reveals {cfg["max_reveals"]} \\\n'
            f'    --checkpoints {",".join(str(k) for k in cfg["checkpoints"])}\n')
    elif cfg["kind"] == "static":
        body = (
            f'python jobs/batch_generate.py \\\n'
            f'    --model-dir "{MODEL}" --tp 4 --max-model-len 2048 \\\n'
            f'    --gpu-mem-util 0.92 --temperature 0.0 \\\n'
            f'    --prompts "{out}/prompts_static.jsonl" \\\n'
            f'    --out "{out}/completions_static.jsonl"\n')
    else:  # eig
        body = (
            f'python jobs/eig_node_driver.py \\\n'
            f'    --pack "{out}/pack_node_exp3.json" \\\n'
            f'    --outdir "{out}" \\\n'
            f'    --model-dir "{MODEL}" --tp 4 --max-model-len 3072 \\\n'
            f'    --gpu-mem-util 0.92 --temperature 0.0 \\\n'
            f'    --max-reveals {cfg["max_reveals"]} \\\n'
            f'    --checkpoints {",".join(str(k) for k in cfg["checkpoints"])} \\\n'
            f'    --top-n {cfg["top_n"]} \\\n'
            f'    --hypotheticals {",".join(str(a) for a in cfg["hypotheticals"])} \\\n'
            f'    --tiebreak-seed {cfg["tiebreak_seed"]} \\\n'
            f'    --smoke-n 200 --min-parse-rate 0.95 --fallback-persons 40\n')
    return head + body + FOOTER.format(name=name)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"created_utc": now(), "batch": "Stage-1E overnight EXP1..EXP5",
            "caps": {"per_job_node_hours": PER_JOB_CAP,
                     "batch_node_hours": BATCH_CAP,
                     "exp3_node_hours": EXP3_CAP},
            "socket_lost_at": None, "experiments": {}, "notes": []}


def save_manifest(man: dict) -> None:
    man["updated_utc"] = now()
    MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")


def cmd_bootstrap(_args) -> int:
    cfgs = experiments()
    if not check_budget(cfgs):
        print("[fatal] budget check failed; nothing written.", file=sys.stderr)
        return 3

    man = load_manifest()
    for name, cfg in cfgs.items():
        rundir = RESULTS_DIR / name
        rundir.mkdir(parents=True, exist_ok=True)
        cfg_out = dict(cfg, run_dir=f"results/{name}",
                       node_outdir=f"{NODE_RUNS}/{name}",
                       model="Gemma-4-31B-it", variant=A.VARIANT,
                       temperature=0.0, tp=4, generated_utc=now())
        (rundir / "config.json").write_text(json.dumps(cfg_out, indent=2),
                                            encoding="utf-8")
        sb = rundir / f"{name}.sbatch"
        sb.write_text(sbatch_text(name, cfg), encoding="utf-8")

        entry = man["experiments"].get(name, {})
        entry.update({
            "experiment": cfg["experiment"],
            "title": cfg["title"],
            "kind": cfg["kind"],
            "status": entry.get("status", "bootstrapped"),
            "run_dir": f"results/{name}",
            "config": f"results/{name}/config.json",
            "sbatch_local": f"results/{name}/{name}.sbatch",
            "sbatch_node": f"{NODE_JOBS}/{name}.sbatch",
            "node_outdir": f"{NODE_RUNS}/{name}",
            "slurm_job_ids": entry.get("slurm_job_ids", []),
            "projected_node_hours": cfg["projection"]["projected_node_hours"],
            "actual_node_hours": entry.get("actual_node_hours"),
            "reuses": cfg["reuses"],
        })
        man["experiments"][name] = entry
        print(f"[bootstrap] {name}: config + sbatch written to {rundir}")
    save_manifest(man)
    print(f"[bootstrap] manifest -> {MANIFEST}")
    return 0


# ---------------------------------------------------------------------------
# Export: the EXP2/4/5 static prompts and the EXP3 pack
# ---------------------------------------------------------------------------


def _pilot_split_ids() -> list[int]:
    """The train-150 ids in the exact order the pilot used them."""
    split = json.loads((RESULTS_DIR / PILOT_RUN / "split.json").read_text())
    return [int(x) for x in split["person_ids"]]


def cmd_export(_args) -> int:
    df = clean_riasec(load_riasec(DATA_DIR))
    codebook = load_codebook(DATA_DIR)
    ids = _pilot_split_ids()
    if ids != A.train_ids(df):
        raise SystemExit("[fatal] the pilot split does not reproduce; refusing "
                         "to build prompts against a different set of people.")
    pack = A.build_person_pack(df, codebook, ids)
    meta = A.static_meta(pack, codebook)

    # ---- EXP2/4/5 static prompt file -------------------------------------
    order_path = RESULTS_DIR / "overnight_exp2" / "fixed_order_derivation.json"
    deriv = json.loads(order_path.read_text(encoding="utf-8"))["order"]
    nn = A.nn_imposter_pairs(df, ids)
    tasks = A.build_overnight_static_tasks(pack, meta, deriv, nn["pairs"])

    # How much MORE similar the nearest neighbour is than the pilot's random
    # stranger -- EXP5 is only interesting if this gap is real.
    import numpy as np  # noqa: PLC0415

    by = df.set_index("person_id")
    vec = {p: by.loc[p, list(A.RIASEC_ITEMS)].to_numpy(dtype=float) for p in ids}

    def _cos(a, b):
        return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

    rnd_pairs = A.imposter_pairs(ids)
    rnd_cos = [_cos(vec[p], vec[d]) for p, d in rnd_pairs.items()]

    out245 = RESULTS_DIR / "overnight_exp245"
    out245.mkdir(parents=True, exist_ok=True)
    with (out245 / "prompts_static.jsonl").open("w", encoding="utf-8") as fh:
        for t in tasks:
            fh.write(json.dumps({"idx": t["idx"], "prompt": t["prompt"],
                                 "max_output_tokens": t["max_output_tokens"]})
                     + "\n")
    with (out245 / "tasks_static.jsonl").open("w", encoding="utf-8") as fh:
        for t in tasks:
            fh.write(json.dumps(t) + "\n")
    (out245 / "nn_imposter_pairs.json").write_text(json.dumps({
        "pairs": {str(k): v for k, v in nn["pairs"].items()},
        "similarity": {str(k): round(v, 6) for k, v in nn["similarity"].items()},
        "mean_similarity": nn["mean_similarity"],
        "min_similarity": nn["min_similarity"],
        "random_imposter_mean_similarity": float(np.mean(rnd_cos)),
        "random_imposter_min_similarity": float(np.min(rnd_cos)),
        "similarity_gap": float(np.mean(list(nn["similarity"].values()))
                                - np.mean(rnd_cos)),
        "n_distinct_donors": len(set(nn["pairs"].values())),
        "metric": "cosine on the 48 raw interest ratings, within train150, "
                  "never self, ties to lowest person_id",
    }, indent=2), encoding="utf-8")
    (out245 / "derivation_order_used.json").write_text(
        json.dumps({"order": deriv, "source": str(order_path.relative_to(_ROOT))},
                   indent=2), encoding="utf-8")
    (out245 / "pack_local.json").write_text(json.dumps(pack), encoding="utf-8")
    print(f"[export] EXP2/4/5: {len(tasks):,} static prompts -> {out245}")
    print(f"[export] nn imposter mean cosine {nn['mean_similarity']:.4f} "
          f"(min {nn['min_similarity']:.4f})")

    # ---- EXP3 pack (first 100 persons, TIPI answers stripped) -------------
    out3 = RESULTS_DIR / "overnight_exp3"
    out3.mkdir(parents=True, exist_ok=True)
    sub_ids = ids[: A.EXP3_N]
    sub_pack = [p for p in pack if p["person_id"] in set(sub_ids)]
    sub_pack.sort(key=lambda p: sub_ids.index(p["person_id"]))
    node = A.node_pack(sub_pack, codebook)
    node["meta"]["checkpoints"] = list(A.CHECKPOINTS_K20)
    node["meta"]["max_reveals"] = 20
    (out3 / "pack_node_exp3.json").write_text(json.dumps(node), encoding="utf-8")
    (out3 / "pack_local.json").write_text(json.dumps(sub_pack), encoding="utf-8")
    (out3 / "person_ids.json").write_text(json.dumps({
        "person_ids": sub_ids, "n": len(sub_ids),
        "note": "first 100 of the train-150 split, in split order, so EXP1a/b "
                "curves restrict onto exactly these people",
    }, indent=2), encoding="utf-8")
    blob = json.dumps(node)
    for code in TIPI_ITEMS:
        assert f'"{code}": {{"text"' not in blob or "answer" not in blob
    print(f"[export] EXP3: pack of {len(sub_pack)} persons -> {out3}")
    return 0


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _node_hours(summary: dict | None) -> float | None:
    """Node-hours actually burned, from a driver's own timing record."""
    if not summary:
        return None
    secs = (summary.get("engine_init_seconds", 0.0)
            + summary.get("generation_wall_seconds", 0.0))
    return round(secs / 3600, 4) if secs else None


def _log_cost(name: str, records: list[dict], extra: dict,
              n_persons: int) -> float | None:
    """One cost-log line per experiment, and the actual node-hours back.

    Every side call the experiment made (uncertainty probes, information-gain
    probes, the parse smoke test) is counted in ``n_calls`` alongside the
    scored predictions, so the ledger reflects what the GPU actually did rather
    than only what ended up in a table.
    """
    node_summary = extra.get("node_summary") or {}
    hours = _node_hours(node_summary)
    # Key names differ slightly between the two drivers; sum whatever is there.
    side_calls = sum(node_summary.get(k, 0) for k in
                     ("n_uncertainty_calls",   # both drivers
                      "n_shift_calls",         # EXP3: reference + hypotheticals
                      "smoke_n"))              # EXP3: the parse gate
    append_cost_log(build_cost_entry(
        run_id=name, model="leonardo-gemma4-31b-it", split="train150",
        variant=A.VARIANT, n_persons=n_persons,
        n_calls=len(records) + side_calls, n_retries=0,
        n_parse_failures=sum(1 for r in records if r["parse_failure"]),
        tokens_in=node_summary.get("total_tokens_in",
                                   sum(r["tokens_in"] for r in records)),
        tokens_out=node_summary.get("total_tokens_out",
                                    sum(r["tokens_out"] for r in records)),
        backend="leonardo-batch", node_hours=hours,
    ), RESULTS_DIR / "cost_log.jsonl")

    man = load_manifest()
    entry = man["experiments"].setdefault(name, {})
    entry["status"] = "ingested"
    entry["actual_node_hours"] = hours
    entry["n_scored_predictions"] = len(records)
    entry["n_side_calls"] = side_calls
    save_manifest(man)
    print(f"[cost] {name}: {hours if hours is not None else '?'} node-hours, "
          f"{len(records) + side_calls:,} calls "
          f"(projected {entry.get('projected_node_hours')})")
    return hours


def _write_arm(outdir: Path, policy: str, records: list[dict],
               extra: dict | None = None) -> dict:
    armdir = outdir / policy
    armdir.mkdir(parents=True, exist_ok=True)
    with (armdir / "records.jsonl").open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    per_k = {}
    for k in sorted({r["k"] for r in records}):
        per_k[str(k)] = summarize([r for r in records if r["k"] == k])
    summary = {
        "config": {"policy": policy, "split": "train150", "variant": A.VARIANT,
                   "model": "leonardo-gemma4-31b-it", "backend": "leonardo-batch"},
        "totals": {
            "n_records": len(records),
            "n_parse_failures": sum(1 for r in records if r["parse_failure"]),
            "tokens_in": sum(r["tokens_in"] for r in records),
            "tokens_out": sum(r["tokens_out"] for r in records),
            "n_persons": len({r["person_id"] for r in records}),
        },
        "per_k_scoring": per_k,
        "extra": extra or {},
    }
    (armdir / "summary.json").write_text(json.dumps(summary, indent=2),
                                         encoding="utf-8")
    return summary


def _tie_diagnostic(unc: list[dict]) -> dict:
    """Residual tie rate under whatever tie-break and scorer were used.

    Reads ``score`` (new) and falls back to ``entropy`` (pilot files), so the
    pilot and tonight's runs go through one code path.
    """
    by_round: dict[tuple, list[float]] = {}
    for row in unc:
        val = row.get("score", row.get("entropy"))
        by_round.setdefault((row["person_id"], row["round"]), []).append(float(val))
    tied, spreads, tops, n_tied = 0, [], [], []
    for ents in by_round.values():
        top = max(ents)
        count = sum(1 for e in ents if e == top)
        tied += int(count > 1)
        n_tied.append(count)
        tops.append(top)
        spreads.append(top - min(ents))
    n = max(len(by_round), 1)
    return {
        "n_decisions": len(by_round),
        "n_decisions_with_tie_at_top": tied,
        "pct_rounds_with_tie": round(100.0 * tied / n, 2),
        "mean_tied_at_top": round(sum(n_tied) / n, 3),
        "max_tied_at_top": max(n_tied) if n_tied else 0,
        "mean_top_score": round(sum(tops) / n, 4),
        "mean_score_spread": round(sum(spreads) / n, 4),
    }


def _ingest_sequential(name: str, nodedir: Path, pack_dir: str,
                       completions: str, arm: str,
                       score_file: str | None = None) -> int:
    """Ingest any sequential (on-node driver) arm: EXP1a/b/c or EXP3.

    Both driver families write the same prediction row shape, so one path
    handles them. Every prompt is rebuilt locally from the reveal order and
    compared byte-for-byte with what the node actually sent -- a mismatch
    would mean the node and the ingester disagree about the interview, which
    is the one failure that would quietly corrupt every number downstream.
    """
    outdir = RESULTS_DIR / name
    pack = json.loads((RESULTS_DIR / pack_dir
                       / "pack_local.json").read_text(encoding="utf-8"))
    by_id = {p["person_id"]: p for p in pack}
    codebook = load_codebook(DATA_DIR)
    meta = A.static_meta(pack, codebook)
    tipi_texts = [meta["tipi_texts"][c] for c in TIPI_ITEMS]

    reveal = {int(k): v for k, v in json.loads(
        (nodedir / "reveal_orders.json").read_text()).items()}
    (outdir / "reveal_orders.json").write_text(
        json.dumps({str(k): v for k, v in reveal.items()}, indent=2),
        encoding="utf-8")

    records, mismatch = [], 0
    for comp in _read_jsonl(nodedir / completions):
        pid, k, code = int(comp["person_id"]), int(comp["k"]), comp["item"]
        person = by_id[pid]
        pairs = [(person["interests"][c]["text"],
                  person["interests"][c]["answer"]) for c in reveal[pid][:k]]
        rebuilt = R.tipi_prompt(person["demographics_block"], pairs,
                                meta["riasec_anchors"], meta["tipi_texts"][code],
                                meta["tipi_anchors"])
        if rebuilt != comp["prompt"]:
            mismatch += 1
        true = person["tipi"][code]["answer"]
        A.assert_prompt_clean(comp["prompt"], meta["tipi_texts"][code], true,
                              tipi_texts, pairs)
        task = {"person_id": pid, "arm": "twin", "item": code,
                "policy": name, "k": k, "donor_id": None,
                "prompt": comp["prompt"]}
        records.append(A.record_from_completion(
            task, comp.get("text"), comp.get("tokens_in", 0),
            comp.get("tokens_out", 0), true))

    extra = {"n_prompt_rebuild_mismatches": mismatch}
    node_summary_path = nodedir / "node_summary.json"
    if node_summary_path.exists():
        extra["node_summary"] = json.loads(node_summary_path.read_text())

    # EXP1's headline diagnostic comes from the full uncertainty log; EXP3
    # logs only its shortlist, so the tie stats come from the scores file.
    ties = None
    if score_file and (nodedir / score_file).exists():
        rows = _read_jsonl(nodedir / score_file)
        if score_file == "uncertainty.jsonl":
            ties = _tie_diagnostic(rows)
            extra["n_uncertainty_calls"] = len(rows)
            extra["n_uncertainty_parse_failures"] = sum(
                1 for r in rows if r.get("parse_failure"))
        else:  # EXP3: shortlist scores, one selected row per person-round
            sel = [r for r in rows if r.get("selected")]
            tied = [r for r in sel if (r.get("n_tied") or 1) > 1]
            ties = {"n_decisions": len(sel),
                    "n_decisions_with_tie_at_top": len(tied),
                    "pct_rounds_with_tie": round(
                        100.0 * len(tied) / max(len(sel), 1), 2),
                    "n_shortlist_rows": len(rows),
                    "n_score_parse_failures": sum(
                        int(bool(r.get("parse_failures"))) for r in rows)}
            extra["eig_scores"] = ties
        if ties:
            extra["tie_diagnostic"] = ties
            (outdir / "tie_diagnostic.json").write_text(
                json.dumps(ties, indent=2), encoding="utf-8")

    smoke = nodedir / "multi_target_smoke.json"
    if smoke.exists():
        extra["multi_target_smoke"] = json.loads(smoke.read_text())
        (outdir / "multi_target_smoke.json").write_text(smoke.read_text(),
                                                        encoding="utf-8")

    _write_arm(outdir, arm, records, extra)
    _log_cost(name, records, extra, len({r["person_id"] for r in records}))
    tie_txt = (f", tie rate {ties['pct_rounds_with_tie']}%" if ties else "")
    print(f"[ingest] {name}: {len(records):,} predictions, "
          f"{mismatch} prompt mismatches{tie_txt}")
    if mismatch:
        print(f"[warn] {mismatch} prompts did not rebuild byte-identically -- "
              "the node and the ingester disagree about the interview.",
              file=sys.stderr)
    return 0


def _ingest_static(nodedir: Path) -> int:
    """EXP2+EXP4+EXP5: split the one completion file back into three arms."""
    outdir = RESULTS_DIR / "overnight_exp245"
    tasks = _read_jsonl(outdir / "tasks_static.jsonl")
    pack = json.loads((outdir / "pack_local.json").read_text(encoding="utf-8"))
    by_id = {p["person_id"]: p for p in pack}
    comps = {int(r["idx"]): r for r in
             _read_jsonl(nodedir / "completions_static.jsonl")}

    by_policy: dict[str, list[dict]] = {p: [] for p in A.OVERNIGHT_STATIC_POLICIES}
    missing = 0
    for task in tasks:
        comp = comps.get(task["idx"])
        true = by_id[task["person_id"]]["tipi"][task["item"]]["answer"]
        if comp is None:
            missing += 1
            rec = A.record_from_completion(task, None, 0, 0, true,
                                           error=f"missing idx {task['idx']}")
        else:
            rec = A.record_from_completion(task, comp.get("text"),
                                           comp.get("tokens_in", 0),
                                           comp.get("tokens_out", 0), true)
        by_policy[task["policy"]].append(rec)
    side = nodedir / "completions_static.jsonl.summary.json"
    node_summary = json.loads(side.read_text()) if side.exists() else {}
    all_records: list[dict] = []
    for policy, records in by_policy.items():
        _write_arm(outdir, policy, records, {
            "n_missing_completions": missing,
            "node_summary": node_summary,
            "experiment": {"fixed_deriv": "EXP2", "random_ext": "EXP4",
                           "nn_imposter": "EXP5"}[policy],
        })
        all_records += records
        print(f"[ingest] {policy}: {len(records):,} records "
              f"({missing} missing overall)")
    # One job, one cost line -- the three arms shared a single engine init.
    _log_cost("overnight_exp245", all_records, {"node_summary": node_summary},
              len({r["person_id"] for r in all_records}))
    if missing:
        print(f"[warn] {missing} completions missing from the static job.",
              file=sys.stderr)
    return 0


def cmd_ingest(args) -> int:
    name = args.name
    nodedir = Path(args.nodedir)
    if name == "overnight_exp245":
        return _ingest_static(nodedir)
    if name.startswith("overnight_exp1"):
        # EXP1 variants all run on the full train-150, so they share the
        # EXP2/4/5 pack (same people, same order).
        return _ingest_sequential(name, nodedir, "overnight_exp245",
                                  "completions_adaptive.jsonl", "adaptive",
                                  score_file="uncertainty.jsonl")
    if name == "overnight_exp3":
        return _ingest_sequential(name, nodedir, "overnight_exp3",
                                  "completions_eig.jsonl", "eig",
                                  score_file="eig_scores.jsonl")
    print(f"[fatal] no ingest path for {name}", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _relabel(records: list[dict], arm: str) -> list[dict]:
    return [dict(r, arm=arm) for r in records]


def _contrast(better: list[dict], worse: list[dict]) -> dict | None:
    """MAE lift of ``better`` over ``worse`` through the shared scoring path."""
    if not better or not worse:
        return None
    return summarize(_relabel(better, "twin") + _relabel(worse, "baseline"))


def _fmt(block: dict | None) -> str:
    if block is None:
        return "n/a"
    lift = block["mae"]["lift"]
    p = block["mae"]["tests"]["t_p"]
    return (f"{lift['mean']:+.3f} [{lift['ci_low']:+.3f}, {lift['ci_high']:+.3f}] "
            f"p={p:.2g}")


def _load(path: Path) -> list[dict]:
    return _read_jsonl(path) if path.exists() else []


def _arms() -> dict:
    """Every arm available for the report, pilot and overnight together."""
    pilot = RESULTS_DIR / PILOT_RUN
    out = {
        "baseline": _load(pilot / "baseline" / "records.jsonl"),
        "pilot_random": _load(pilot / "random" / "records.jsonl"),
        "pilot_fixed": _load(pilot / "fixed" / "records.jsonl"),
        "pilot_adaptive": _load(pilot / "adaptive" / "records.jsonl"),
        "rand_imposter": _load(pilot / "imposter" / "records.jsonl"),
        "exp1a": _load(RESULTS_DIR / "overnight_exp1a" / "adaptive"
                       / "records.jsonl"),
        "exp1b": _load(RESULTS_DIR / "overnight_exp1b" / "adaptive"
                       / "records.jsonl"),
        "exp1c": _load(RESULTS_DIR / "overnight_exp1c" / "adaptive"
                       / "records.jsonl"),
        "fixed_deriv": _load(RESULTS_DIR / "overnight_exp245" / "fixed_deriv"
                             / "records.jsonl"),
        "random_ext": _load(RESULTS_DIR / "overnight_exp245" / "random_ext"
                            / "records.jsonl"),
        "nn_imposter": _load(RESULTS_DIR / "overnight_exp245" / "nn_imposter"
                             / "records.jsonl"),
        "exp3_eig": _load(RESULTS_DIR / "overnight_exp3" / "eig"
                          / "records.jsonl"),
    }
    # EXP4's random curve is the pilot's checkpoints plus tonight's extension.
    out["random_full"] = out["pilot_random"] + out["random_ext"]
    return out


def _at(records: list[dict], k: int, ids: set[int] | None = None) -> list[dict]:
    rows = [r for r in records if r["k"] == k]
    if ids is not None:
        rows = [r for r in rows if r["person_id"] in ids]
    return rows


def _curve(arms: dict, arm: str, ks, ids=None) -> list[str]:
    base = arms["baseline"]
    return [_fmt(_contrast(_at(arms[arm], k, ids), _at(base, 0, ids)))
            for k in ks]


def _tie_rate(name: str) -> dict | None:
    path = RESULTS_DIR / name / "tie_diagnostic.json"
    return json.loads(path.read_text()) if path.exists() else None


def cmd_report(_args) -> int:
    arms = _arms()
    have = {k: bool(v) for k, v in arms.items()}
    man = load_manifest()
    L: list[str] = []

    L += [
        "# Stage 1E overnight batch (EXP1-EXP5) — TRAINING-SPLIT RESULTS",
        "",
        "**Label: TRAINING/DERIVATION SPLIT ONLY — for bar-setting and "
        "go/no-go judgement. No confirmatory claims. The confirm split has not "
        "been built or touched.**",
        "",
        f"Date: {datetime.now().strftime('%Y-%m-%d')}. Spec: "
        "PREREGISTRATION_AMENDMENT_1.md A6, extending "
        "results/adaptive_pilot_train.md. Model: Gemma-4-31B-it (vLLM, TP=4, "
        "temperature 0), twin variant v2, same parser and scoring as the "
        "Stage 1 gate.",
        "",
        "Lift = demographics-only baseline MAE − arm MAE, averaged over "
        "persons, 95% t interval and paired t-test. Higher is better.",
        "",
        "## What was run, and what was reused",
        "",
        "| experiment | status | reused from the pilot |",
        "|---|---|---|",
    ]
    for name, e in man["experiments"].items():
        L.append(f"| {e.get('experiment', name)} | {e.get('status', '?')} | "
                 + ("; ".join(e.get("reuses") or []) or "nothing") + " |")

    ks20 = list(A.CHECKPOINTS_K20)
    ks48 = list(A.CHECKPOINTS_EXT)
    pilot_ks = list(A.CHECKPOINTS)

    # ---- EXP1 -------------------------------------------------------------
    L += ["", "## EXP1 — tie-break, scorer and elicitation grid", "",
          "All three variants replace the pilot's lowest-item-index tie-break "
          "with a seeded random one. The pilot's tie-break was deciding 51.5% "
          "of reveals, and lowest-index is biased towards R-items.", "",
          "### Residual tie rate", "",
          "| variant | decisions | tied at top | mean tied | max tied |",
          "|---|---|---|---|---|"]
    pilot_ties = RESULTS_DIR / PILOT_RUN / "entropy_diagnostic.json"
    if pilot_ties.exists():
        t = json.loads(pilot_ties.read_text())
        L.append(f"| pilot (entropy, index tie-break) | {t['n_decisions']:,} | "
                 f"{t['pct_rounds_with_tie']:.1f}% | {t['mean_tied_at_top']:.1f} "
                 f"| {t['max_tied_at_top']} |")
    for label, name in (("EXP1a entropy + random", "overnight_exp1a"),
                        ("EXP1b EV-variance + random", "overnight_exp1b"),
                        ("EXP1c entropy + random + 0.05 grid",
                         "overnight_exp1c")):
        t = _tie_rate(name)
        if t:
            L.append(f"| {label} | {t['n_decisions']:,} | "
                     f"{t['pct_rounds_with_tie']:.1f}% | "
                     f"{t['mean_tied_at_top']:.1f} | {t['max_tied_at_top']} |")
        else:
            L.append(f"| {label} | not ingested | | | |")

    L += ["", "### Lift over baseline, by variant", "",
          "| k | pilot adaptive | EXP1a entropy+rand | EXP1b EV-var | "
          "EXP1c fine grid |", "|---|---|---|---|---|"]
    for k in ks20:
        cells = []
        for arm in ("pilot_adaptive", "exp1a", "exp1b", "exp1c"):
            cells.append(_fmt(_contrast(_at(arms[arm], k), _at(arms["baseline"], 0)))
                         if have[arm] else "not ingested")
        L.append(f"| {k} | " + " | ".join(cells) + " |")

    L += ["", "### Delta vs the pilot adaptive curve at matched k", "",
          "Positive = the change helped.", "",
          "| k | EXP1a − pilot | EXP1b − pilot | EXP1c − pilot |",
          "|---|---|---|---|"]
    for k in pilot_ks:
        cells = []
        for arm in ("exp1a", "exp1b", "exp1c"):
            cells.append(_fmt(_contrast(_at(arms[arm], k),
                                        _at(arms["pilot_adaptive"], k)))
                         if have[arm] and have["pilot_adaptive"] else "n/a")
        L.append(f"| {k} | " + " | ".join(cells) + " |")

    # ---- EXP2 -------------------------------------------------------------
    L += ["", "## EXP2 — best fixed order, derived on a disjoint split", ""]
    dpath = RESULTS_DIR / "overnight_exp2"
    if (dpath / "fixed_order_derivation.json").exists():
        fo = json.loads((dpath / "fixed_order_derivation.json").read_text())
        st = json.loads((dpath / "stability_derivation.json").read_text())
        ids_meta = json.loads((dpath / "derivation_ids.json").read_text())
        L += [
            f"Derived on {fo.get('n_train', 'n/a')} persons (seed "
            f"{A.DERIV_SEED}), disjoint from all {ids_meta.get('n_excluded', '?')} "
            "previously used people. Ridge greedy forward selection, no model "
            "involved.", "",
            "Frozen order (first 20): `" + " ".join(fo["order"][:20]) + "`", "",
            "Full 48: `" + " ".join(fo["order"]) + "`", "",
            "### Stability", "",
            "| statistic | value | chance baseline |", "|---|---|---|",
        ]
        for key, label, chance in (
                ("overlap_at_k20", "split-half overlap at k=20 (1000/1000)",
                 st.get("expected_overlap_if_random", 8.33)),
                ("spearman_between_halves", "rank correlation over 48 items",
                 0.0)):
            if key in st:
                L.append(f"| {label} | {st[key]} | {chance} |")
        for key, label in (("pilot_overlap_at_k20",
                            "pilot n=150 split-half overlap at k=20"),):
            if key in st:
                L.append(f"| {label} | {st[key]} | 8.33 |")
    L += ["", "### Frozen order applied to train-150", "",
          "These 150 people had no say in picking this order, so this column "
          "is not inflated the way the pilot's `fixed` arm was.", "",
          "| k | fixed_deriv lift | pilot fixed (selection-biased) |",
          "|---|---|---|"]
    for k in ks48:
        a = (_fmt(_contrast(_at(arms["fixed_deriv"], k), _at(arms["baseline"], 0)))
             if have["fixed_deriv"] else "not ingested")
        b = (_fmt(_contrast(_at(arms["pilot_fixed"], k), _at(arms["baseline"], 0)))
             if have["pilot_fixed"] and k in pilot_ks else "—")
        L.append(f"| {k} | {a} | {b} |")

    # ---- EXP3 -------------------------------------------------------------
    L += ["", "## EXP3 — selection ladder: does target-aware selection beat "
          "self-uncertainty?", "",
          f"n={A.EXP3_N} (first {A.EXP3_N} of the train split). Ladder rung "
          "(a) is EXP1's self-uncertainty policy restricted to these people — "
          "not rerun. Rung (b) scores each shortlisted item by how much the "
          "10 TIPI target distributions are expected to move.", ""]
    smoke = RESULTS_DIR / "overnight_exp3" / "multi_target_smoke.json"
    if smoke.exists():
        s = json.loads(smoke.read_text())
        verdict = ("PASSED" if s.get("passed") else
                   "FAILED — fell back to per-target calls on fewer persons")
        L += [f"Node-side parse check before committing the run: "
              f"{s.get('n_parsed', '?')}/{s.get('n', '?')} multi-target "
              f"completions parsed ({100 * s.get('parse_rate', 0):.1f}%), "
              f"bar was 95% — {verdict}.", ""]
    ids3 = None
    p3 = RESULTS_DIR / "overnight_exp3" / "person_ids.json"
    if p3.exists():
        ids3 = set(json.loads(p3.read_text())["person_ids"])
    L += ["| k | (a) self-uncertainty (EXP1a) | (b) expected info gain | "
          "(b) − (a) |", "|---|---|---|---|"]
    for k in ks20:
        a = (_fmt(_contrast(_at(arms["exp1a"], k, ids3), _at(arms["baseline"], 0, ids3)))
             if have["exp1a"] else "not ingested")
        b = (_fmt(_contrast(_at(arms["exp3_eig"], k), _at(arms["baseline"], 0, ids3)))
             if have["exp3_eig"] else "not ingested")
        d = (_fmt(_contrast(_at(arms["exp3_eig"], k), _at(arms["exp1a"], k, ids3)))
             if have["exp3_eig"] and have["exp1a"] else "n/a")
        L.append(f"| {k} | {a} | {b} | {d} |")
    L += ["", "Rung (c), one-step lookahead, was **not run**: it multiplies "
          "rung (b)'s cost by the shortlist size again and does not fit inside "
          f"EXP3's {EXP3_CAP} node-hour cap alongside (b)."]

    # ---- EXP4 -------------------------------------------------------------
    L += ["", "## EXP4 — budget curve: where does the edge peak, where does it "
          "saturate?", "",
          "The random arm reuses the pilot's completions at k in "
          f"{{{', '.join(str(k) for k in pilot_ks)}}} and buys only "
          f"{{{', '.join(str(k) for k in A.CHECKPOINTS_RANDOM_NEW)}}}. The "
          "adaptive side is EXP1a.", "",
          "| k | random | adaptive (EXP1a) | adaptive − random |",
          "|---|---|---|---|"]
    for k in ks48:
        r = (_fmt(_contrast(_at(arms["random_full"], k), _at(arms["baseline"], 0)))
             if _at(arms["random_full"], k) else "not ingested")
        a = (_fmt(_contrast(_at(arms["exp1a"], k), _at(arms["baseline"], 0)))
             if have["exp1a"] else "not ingested")
        d = (_fmt(_contrast(_at(arms["exp1a"], k), _at(arms["random_full"], k)))
             if have["exp1a"] and _at(arms["random_full"], k) else "n/a")
        L.append(f"| {k} | {r} | {a} | {d} |")
    L += ["", "Reference: the Stage 1 gate's all-48-item lift on 500 people "
          "was +0.095."]

    # ---- EXP5 -------------------------------------------------------------
    L += ["", "## EXP5 — imposter gradient: does a MORE similar wrong person "
          "mislead less, or more?", ""]
    nnp = RESULTS_DIR / "overnight_exp245" / "nn_imposter_pairs.json"
    if nnp.exists():
        nn = json.loads(nnp.read_text())
        L += [f"Nearest-neighbour donors are drawn inside train-150 by cosine "
              f"similarity on the 48 interest ratings (mean "
              f"{nn['mean_similarity']:.4f}, min {nn['min_similarity']:.4f}), "
              "never self-paired. Reveal positions mirror the random arm, "
              "exactly like the pilot's random imposter.", ""]
        if "random_imposter_mean_similarity" in nn:
            L += [f"The gradient is real: the random imposter's mean cosine is "
                  f"{nn['random_imposter_mean_similarity']:.4f}, so the "
                  f"nearest neighbour is {nn['similarity_gap']:+.4f} more "
                  f"similar. {nn['n_distinct_donors']} distinct people serve as "
                  f"NN donors for the 150.", ""]
    L += ["| k | own (random arm) | NN imposter | random imposter | "
          "own − NN | own − random imp | NN − random imp |",
          "|---|---|---|---|---|---|---|"]
    for k in A.CHECKPOINTS_IMPOSTER:
        own = _at(arms["random_full"], k)
        nnr = _at(arms["nn_imposter"], k)
        rnd = _at(arms["rand_imposter"], k)
        base0 = _at(arms["baseline"], 0)
        L.append(
            f"| {k} | {_fmt(_contrast(own, base0)) if own else 'n/a'} "
            f"| {_fmt(_contrast(nnr, base0)) if nnr else 'not ingested'} "
            f"| {_fmt(_contrast(rnd, base0)) if rnd else 'n/a'} "
            f"| {_fmt(_contrast(own, nnr)) if own and nnr else 'n/a'} "
            f"| {_fmt(_contrast(own, rnd)) if own and rnd else 'n/a'} "
            f"| {_fmt(_contrast(nnr, rnd)) if nnr and rnd else 'n/a'} |")
    L += ["", "Read: the pilot found a random stranger's profile is *worse "
          "than knowing nothing* (lift −0.04 to −0.055 over baseline). If the "
          "nearest neighbour is less harmful, similarity buys back some "
          "generic signal; if it is more harmful, a plausible-but-wrong "
          "profile is the more dangerous failure — which is the case Stage 2's "
          "same-domain imposter has to survive."]

    # ---- ledger -----------------------------------------------------------
    L += ["", "## Cost ledger", "",
          "| experiment | projected node-hours | actual | slurm job(s) | status |",
          "|---|---|---|---|---|"]
    tot_p = tot_a = 0.0
    for name, e in man["experiments"].items():
        p = e.get("projected_node_hours") or 0.0
        a = e.get("actual_node_hours")
        tot_p += p
        tot_a += a or 0.0
        L.append(f"| {name} | {p:.3f} | "
                 f"{f'{a:.3f}' if a is not None else '—'} | "
                 f"{', '.join(e.get('slurm_job_ids', [])) or '—'} | "
                 f"{e.get('status', '?')} |")
    L.append(f"| **TOTAL** | **{tot_p:.3f}** | **{tot_a:.3f}** | | "
             f"caps: {PER_JOB_CAP}/job, {BATCH_CAP}/batch |")

    L += ["", "## Provenance", "",
          "Per-experiment run directories under `results/overnight_exp*/` — "
          "each with `config.json`, its `.sbatch`, per-arm `records.jsonl` "
          "(full prompts and raw responses) and `summary.json`. Job ids, node "
          "paths and the exact ingestion commands are in "
          "`results/overnight_manifest.json`.", ""]

    dest = RESULTS_DIR / "overnight_stage1e.md"
    dest.write_text("\n".join(L), encoding="utf-8")
    print(f"[report] wrote {dest}")
    missing = [k for k, v in have.items() if not v]
    if missing:
        print(f"[report] arms not yet ingested: {', '.join(missing)}")
    return 0


#: Node-side files each job kind produces, and therefore what must be pulled
#: back before ingestion can run.
NODE_OUTPUTS = {
    "adaptive": ["completions_adaptive.jsonl", "uncertainty.jsonl",
                 "reveal_orders.json", "node_summary.json", "node_runs.jsonl"],
    "static": ["completions_static.jsonl",
               "completions_static.jsonl.summary.json"],
    "eig": ["completions_eig.jsonl", "eig_scores.jsonl", "reveal_orders.json",
            "multi_target_smoke.json", "node_summary.json", "node_runs.jsonl"],
}


def cmd_record(args) -> int:
    """Write a job id and its exact ingestion recipe into the manifest.

    Everything the morning needs is written here at submission time, so a dead
    socket costs nothing but the wait.
    """
    man = load_manifest()
    entry = man["experiments"].setdefault(args.name, {})
    if args.job_id:
        ids = entry.setdefault("slurm_job_ids", [])
        if args.job_id not in ids:
            ids.append(args.job_id)
    if args.status:
        entry["status"] = args.status
    if args.note:
        entry.setdefault("notes", []).append(f"{now()}: {args.note}")

    kind = entry.get("kind") or experiments()[args.name]["kind"]
    node_out = entry.get("node_outdir", f"{NODE_RUNS}/{args.name}")
    local = f"results/{args.name}/node_output"
    entry["node_output_files"] = [f"{node_out}/{f}" for f in NODE_OUTPUTS[kind]]
    entry["ingestion"] = {
        "step_1_check_job": f"ssh {REMOTE} 'sacct -j {','.join(entry.get('slurm_job_ids', [])) or '<jobid>'} "
                            f"-X --format=JobID,JobName,State,Elapsed,ExitCode'",
        "step_2_pull": f"mkdir -p {local} && rsync -az "
                       f"{REMOTE}:{node_out}/ {local}/",
        "step_3_ingest": f"uv run python experiments/overnight.py ingest "
                         f"--name {args.name} --nodedir {local}",
        "step_4_report": "uv run python experiments/overnight.py report",
        "node_log": f"{NODE_ROOT}/logs/dop-"
                    f"{args.name.replace('overnight_', '')}-<jobid>.out",
    }
    save_manifest(man)
    print(f"[record] {args.name}: job(s) {entry.get('slurm_job_ids')} "
          f"status={entry.get('status')}")
    return 0


def cmd_status(_args) -> int:
    man = load_manifest()
    print(f"socket_lost_at: {man.get('socket_lost_at')}")
    for name, e in man["experiments"].items():
        print(f"  {name:20s} {e.get('status','?'):12s} "
              f"jobs={e.get('slurm_job_ids')} "
              f"proj={e.get('projected_node_hours')} "
              f"actual={e.get('actual_node_hours')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    sub.add_parser("bootstrap")
    sub.add_parser("export")
    sub.add_parser("status")
    sub.add_parser("report")
    p_rec = sub.add_parser("record")
    p_rec.add_argument("--name", required=True)
    p_rec.add_argument("--job-id", default=None)
    p_rec.add_argument("--status", default=None)
    p_rec.add_argument("--note", default=None)
    p_in = sub.add_parser("ingest")
    p_in.add_argument("--name", required=True)
    p_in.add_argument("--nodedir", required=True,
                      help="local copy of the node output directory")
    args = ap.parse_args()
    return {"plan": cmd_plan, "bootstrap": cmd_bootstrap, "export": cmd_export,
            "ingest": cmd_ingest, "record": cmd_record, "report": cmd_report,
            "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
