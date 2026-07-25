"""Stage 1E CONFIRM run (PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md, section A).

CONFIRMATORY. This is the one run whose numbers answer the frozen bars C1/C2/C3.
Every design choice here is quoted from Addendum A and is not a knob:

  split         n=1,000, seed 46, read from results/stage1e_confirm/confirm_ids.json
                (drawn and committed in 4860bb4; this file NEVER re-draws it)
  model         Gemma-4-31B-it, twin variant v2, temperature 0, TP=4
  checkpoints   k in {1, 2, 4, 8, 12, 16, 20}
  arms (5)      baseline   demographics only
                random     per-person seeded reveal order
                fixed      the frozen derivation order (greedy ridge, n=2,000,
                           seed 45) -- first 20 items quoted in Addendum A
                adaptive   EV-variance scorer + seeded random tie-break, i.e.
                           exactly the EXP1b configuration, wording unchanged
                imposter   random-person donor profile mirroring the random
                           arm's reveal positions (Amendment A1)

Job layout. The four static arms are one pre-determined prompt file, so they
share a single engine init. The adaptive arm is sequential (round r+1 depends on
round r) and is split into 4 shards of 250 persons. Sharding is free of
scientific consequence: every person's trajectory is independent, the tie-break
is seeded per (person_id, round), and temperature is 0 -- shards only buy
wall-clock and failure isolation. Everything is resumable: the static job skips
chunks that already have output, the adaptive driver recovers complete reveal
rounds and complete checkpoints from a killed job's partial files.

Subcommands
-----------
``plan``       node-hour projection from measured throughput.
``verify``     re-prove the split: n, seed, and disjointness from every
               previously used person and from the 2,000 derivation ids.
``bootstrap``  run dir, config.json, the sbatch files, the manifest.
``export``     build the static prompt chunks and the 4 adaptive shard packs.
``record``     write a job id / status into the manifest.
``ingest``     join returned completions back into per-arm records, per-arm
               summaries and per-arm cost-log lines.
``analyse``    apply the frozen bars mechanically, under BOTH decodings, and
               dump every number the report needs to results/stage1e_confirm/
               analysis.json.
"""

from __future__ import annotations

import argparse
import hashlib
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
CONFIRM_DIR = RESULTS_DIR / "stage1e_confirm"
IDS_FILE = CONFIRM_DIR / "confirm_ids.json"
DERIVATION_IDS = RESULTS_DIR / "overnight_exp2" / "derivation_ids.json"
ORDER_FILE = RESULTS_DIR / "overnight_exp2" / "fixed_order_derivation.json"
MANIFEST = CONFIRM_DIR / "manifest.json"
ANALYSIS = CONFIRM_DIR / "analysis.json"

REMOTE = "leonardo"
NODE_ROOT = "/leonardo_work/AIFAC_P02_548/DOPPLER"
NODE_RUN = f"{NODE_ROOT}/runs/stage1e_confirm"
NODE_JOBS = f"{NODE_ROOT}/jobs"
ACCOUNT = "AIFAC_P02_548"
MODEL = f"{NODE_ROOT}/models/Gemma-4-31B-it"
MODEL_LABEL = "leonardo-gemma4-31b-it"
SPLIT_LABEL = "stage1e_confirm"

#: Frozen by Addendum A section A.
CONFIRM_N = 1000
CONFIRM_SEED = 46
CHECKPOINTS = A.CHECKPOINTS            # (1, 2, 4, 8, 12, 16, 20)
MAX_REVEALS = 20
SCORER = "ev_variance"
TIEBREAK = "random"
TIEBREAK_SEED = A.TIEBREAK_SEED         # 71
INTEREST_GRID = "standard"
ARMS = ("baseline", "random", "fixed", "adaptive", "imposter")

#: The first 20 items of the frozen order, quoted verbatim in Addendum A. The
#: order file on disk must agree with the addendum, or one of the two is wrong.
ADDENDUM_ORDER_20 = ("A3 E5 S5 A5 A2 C1 C2 S7 E7 A6 A7 I1 I8 S6 E1 S2 I2 S4 "
                     "R2 C4").split()

#: Adaptive shards (250 persons each) and static prompt chunks.
N_ADAPTIVE_SHARDS = 4
N_STATIC_CHUNKS = 4

#: Bars that need a paired test, as (label, better_arm, worse_arm, k, tier).
FROZEN_CONTRASTS = (
    ("C1_primary_adaptive_vs_random_k12", "adaptive", "random", 12, "PRIMARY"),
    ("C1_secondary_adaptive_vs_random_k20", "adaptive", "random", 20, "SECONDARY"),
    ("C2_adaptive_vs_fixed_k12", "adaptive", "fixed", 12, "SECONDARY"),
    ("C2_adaptive_vs_fixed_k20", "adaptive", "fixed", 20, "SECONDARY"),
    ("C3_own_vs_baseline_k20", "random", "baseline", 20, "CONFIRMATORY"),
    ("C3_own_vs_imposter_k20", "random", "imposter", 20, "CONFIRMATORY"),
)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Split verification -- run before anything is built, and again at export
# ---------------------------------------------------------------------------


def confirm_ids() -> list[int]:
    """The committed confirm split. Read, never re-drawn."""
    doc = json.loads(IDS_FILE.read_text(encoding="utf-8"))
    ids = [int(x) for x in doc["person_ids"]]
    if doc["n"] != CONFIRM_N or len(ids) != CONFIRM_N:
        raise SystemExit(f"[fatal] confirm split has {len(ids)} ids, expected "
                         f"{CONFIRM_N}")
    if doc["seed"] != CONFIRM_SEED:
        raise SystemExit(f"[fatal] confirm split seed is {doc['seed']}, expected "
                         f"{CONFIRM_SEED}")
    if len(set(ids)) != len(ids):
        raise SystemExit("[fatal] confirm split contains duplicates")
    return ids


def verify_split(verbose: bool = True) -> dict:
    """Re-prove disjointness against both exclusion sets, from scratch.

    The derivation ids have no records.jsonl, so the automatic run-dir scan
    cannot see them -- they are loaded explicitly, exactly as the draw script
    warned. This check is cheap and is repeated at export time, because a
    contaminated confirm split would silently invalidate every bar.
    """
    ids = confirm_ids()
    ids_set = set(ids)

    per_run = A.scan_used_person_ids(RESULTS_DIR)
    # This run's own arms would otherwise look like "previously used" people.
    per_run = {name: v for name, v in per_run.items()
               if not name.startswith("stage1e_confirm")}
    used = set().union(*per_run.values()) if per_run else set()

    deriv = {int(x) for x in json.loads(
        DERIVATION_IDS.read_text(encoding="utf-8"))["person_ids"]}

    df = clean_riasec(load_riasec(DATA_DIR))
    pool = set(df["person_id"].tolist())

    bad_used = sorted(ids_set & used)
    bad_deriv = sorted(ids_set & deriv)
    not_in_pool = sorted(ids_set - pool)

    out = {
        "n": len(ids), "seed": CONFIRM_SEED,
        "n_run_dirs_scanned": len(per_run),
        "n_excluded_run_scan": len(used),
        "n_excluded_derivation": len(deriv),
        "cleaned_pool": len(pool),
        "overlap_with_used": len(bad_used),
        "overlap_with_derivation": len(bad_deriv),
        "ids_missing_from_cleaned_pool": len(not_in_pool),
        "checked_utc": now(),
    }
    if verbose:
        print(f"[verify] n={len(ids)} seed={CONFIRM_SEED}")
        print(f"[verify] run-dir scan: {len(per_run)} dirs, {len(used)} persons "
              f"excluded")
        print(f"[verify] derivation file: {len(deriv)} persons excluded")
        print(f"[verify] cleaned pool: {len(pool)}")
        print(f"[verify] overlap with used: {len(bad_used)}; with derivation: "
              f"{len(bad_deriv)}; outside cleaned pool: {len(not_in_pool)}")
    if bad_used or bad_deriv or not_in_pool:
        raise SystemExit("[fatal] confirm split is CONTAMINATED -- stop and "
                         f"tell the owner. used={bad_used[:10]} "
                         f"deriv={bad_deriv[:10]} outside={not_in_pool[:10]}")
    if verbose:
        print("[verify] OK: confirm split is disjoint from everything used "
              "before and from the derivation split.")
    return out


def fixed_order() -> list[str]:
    """The frozen derivation order, cross-checked against Addendum A's text."""
    doc = json.loads(ORDER_FILE.read_text(encoding="utf-8"))
    order = list(doc["order"])
    if len(set(order)) != len(order):
        raise SystemExit("[fatal] derivation order repeats an item")
    if order[:20] != ADDENDUM_ORDER_20:
        raise SystemExit("[fatal] the order file disagrees with the first 20 "
                         "items quoted in Addendum A:\n"
                         f"  file:     {' '.join(order[:20])}\n"
                         f"  addendum: {' '.join(ADDENDUM_ORDER_20)}")
    if doc.get("n_train") != A.DERIV_N:
        raise SystemExit(f"[fatal] order was derived on {doc.get('n_train')} "
                         f"persons, expected {A.DERIV_N}")
    return order


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def static_counts() -> dict:
    per_person = (1                                   # baseline, k=0
                  + 3 * len(CHECKPOINTS)) * len(TIPI_ITEMS)
    return {
        "baseline": CONFIRM_N * len(TIPI_ITEMS),
        "random": CONFIRM_N * len(CHECKPOINTS) * len(TIPI_ITEMS),
        "fixed": CONFIRM_N * len(CHECKPOINTS) * len(TIPI_ITEMS),
        "imposter": CONFIRM_N * len(CHECKPOINTS) * len(TIPI_ITEMS),
        "per_person": per_person,
        "TOTAL": CONFIRM_N * per_person,
    }


def projection() -> dict:
    """Node-hours from the pilot's *measured* throughput, per job."""
    static = A.project_job(n_tipi=static_counts()["TOTAL"])
    shard_n = CONFIRM_N // N_ADAPTIVE_SHARDS
    unc, pred = A.adaptive_call_counts(shard_n, MAX_REVEALS, CHECKPOINTS)
    shard = A.project_job(n_interest=unc, n_tipi=pred)
    jobs = {"confirm_static": static}
    for s in range(N_ADAPTIVE_SHARDS):
        jobs[f"confirm_adaptive_s{s}"] = shard
    total = round(sum(j["projected_node_hours"] for j in jobs.values()), 4)
    return {
        "jobs": jobs,
        "n_persons": CONFIRM_N,
        "adaptive_shards": N_ADAPTIVE_SHARDS,
        "persons_per_shard": shard_n,
        "total_projected_node_hours": total,
        "addendum_estimate_node_hours": [11, 14],
        "note": "Addendum A estimated 11-14 node-hours by scaling the pilot's "
                "per-person cost. This projection uses the pilot's measured "
                "tokens-per-second and comes in lower; the addendum figure is "
                "an estimate, not a cap. Actuals are logged per arm.",
    }


def cmd_plan(_args) -> int:
    proj = projection()
    counts = static_counts()
    print("=== Stage 1E confirm run: projection ===")
    print(f"  persons                {CONFIRM_N}")
    print(f"  checkpoints            {list(CHECKPOINTS)}")
    print(f"  static completions     {counts['TOTAL']:,} "
          f"({counts['per_person']} per person)")
    shard_n = proj["persons_per_shard"]
    unc, pred = A.adaptive_call_counts(shard_n, MAX_REVEALS, CHECKPOINTS)
    print(f"  adaptive per shard     {unc:,} uncertainty + {pred:,} predictions "
          f"({shard_n} persons)")
    print(f"  adaptive total         {unc * N_ADAPTIVE_SHARDS:,} uncertainty + "
          f"{pred * N_ADAPTIVE_SHARDS:,} predictions")
    print("  --- node-hours ---")
    for name, job in proj["jobs"].items():
        print(f"  {name:24s} {job['projected_node_hours']:6.3f}  "
              f"({job['total_calls']:,} calls)")
    print(f"  {'TOTAL':24s} {proj['total_projected_node_hours']:6.3f}  "
          f"(Addendum A estimate 11-14)")
    return 0


def cmd_verify(_args) -> int:
    verify_split()
    order = fixed_order()
    print(f"[verify] fixed order OK, matches Addendum A's first 20: "
          f"{' '.join(order[:20])}")
    return 0


# ---------------------------------------------------------------------------
# sbatch
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
# Stage 1E CONFIRM run -- {title}
# Frozen by PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md section A.
# Production queue (boost_usr_prod), NOT the debug QOS.
# Projected {hours:.3f} node-hours. Resumable: resubmitting continues.
set -euo pipefail
D={node_root}
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
mkdir -p "{out}"
echo "[{name}] node=$(hostname) start=$(date -u +%FT%TZ)"
"""

FOOTER = '\necho "[{name}] DONE $(date -u +%FT%TZ)"\n'


def static_sbatch(walltime: str, hours: float) -> str:
    """One engine init, N chunk files, and chunks already done are skipped.

    batch_generate.py takes repeated --prompts/--out pairs through a single
    engine. The bash loop below drops any chunk whose output summary already
    exists, so a walltime cut or a resubmit only pays for what is missing.
    """
    out = NODE_RUN
    head = HEADER.format(job_name="dop-confirm-static", account=ACCOUNT,
                         walltime=walltime, node_root=NODE_ROOT,
                         title="static arms (baseline, random, fixed, imposter)",
                         hours=hours, name="confirm_static", out=out)
    body = f"""
ARGS=()
for c in $(seq 0 {N_STATIC_CHUNKS - 1}); do
  P="{out}/prompts_static_$c.jsonl"
  O="{out}/completions_static_$c.jsonl"
  if [[ -f "$O.summary.json" ]]; then
    echo "[confirm_static] chunk $c already complete, skipping"
  else
    ARGS+=(--prompts "$P" --out "$O")
  fi
done
if [[ ${{#ARGS[@]}} -eq 0 ]]; then
  echo "[confirm_static] all chunks complete; nothing to do."
  exit 0
fi
python jobs/batch_generate.py \\
    --model-dir "{MODEL}" --tp 4 --max-model-len 2048 \\
    --gpu-mem-util 0.92 --temperature 0.0 \\
    "${{ARGS[@]}}"
"""
    return head + body + FOOTER.format(name="confirm_static")


def adaptive_sbatch(shard: int, walltime: str, hours: float) -> str:
    name = f"confirm_adaptive_s{shard}"
    out = f"{NODE_RUN}/adaptive_s{shard}"
    head = HEADER.format(job_name=f"dop-confirm-ad{shard}", account=ACCOUNT,
                         walltime=walltime, node_root=NODE_ROOT,
                         title=f"adaptive arm, shard {shard} of "
                               f"{N_ADAPTIVE_SHARDS} (EV-variance scorer)",
                         hours=hours, name=name, out=out)
    body = (
        f'python jobs/adaptive_node_driver.py \\\n'
        f'    --pack "{NODE_RUN}/pack_node_s{shard}.json" \\\n'
        f'    --outdir "{out}" \\\n'
        f'    --model-dir "{MODEL}" --tp 4 --max-model-len 2048 \\\n'
        f'    --gpu-mem-util 0.92 --temperature 0.0 \\\n'
        f'    --scorer {SCORER} --tiebreak {TIEBREAK} \\\n'
        f'    --tiebreak-seed {TIEBREAK_SEED} \\\n'
        f'    --interest-grid {INTEREST_GRID} \\\n'
        f'    --max-reveals {MAX_REVEALS} \\\n'
        f'    --checkpoints {",".join(str(k) for k in CHECKPOINTS)}\n')
    return head + body + FOOTER.format(name=name)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {
        "created_utc": now(),
        "run": "Stage 1E confirm (Addendum A section A)",
        "confirmatory": True,
        "contract": "PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md (commit 3b8dd57)",
        "jobs": {}, "anomalies": [], "notes": [],
    }


def save_manifest(man: dict) -> None:
    man["updated_utc"] = now()
    CONFIRM_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")


def cmd_bootstrap(_args) -> int:
    verify_split()
    order = fixed_order()
    proj = projection()
    CONFIRM_DIR.mkdir(parents=True, exist_ok=True)

    config = {
        "run": "stage1e_confirm",
        "confirmatory": True,
        "contract": "PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md section A "
                    "(commit 3b8dd57)",
        "split": {"name": SPLIT_LABEL, "n": CONFIRM_N, "seed": CONFIRM_SEED,
                  "ids_file": str(IDS_FILE.relative_to(_ROOT))},
        "model": "Gemma-4-31B-it", "model_label": MODEL_LABEL,
        "variant": A.VARIANT, "temperature": 0.0, "tp": 4,
        "max_model_len": 2048,
        "checkpoints": list(CHECKPOINTS),
        "arms": {
            "baseline": {"policy": "baseline", "k": [0],
                         "note": "demographics only"},
            "random": {"policy": "random", "k": list(CHECKPOINTS),
                       "seed": A.RANDOM_ORDER_SEED,
                       "note": "per-person seeded reveal order"},
            "fixed": {"policy": "fixed", "k": list(CHECKPOINTS),
                      "order_source": str(ORDER_FILE.relative_to(_ROOT)),
                      "order_first_20": order[:20],
                      "note": "frozen derivation order (greedy ridge, n=2,000, "
                              "seed 45); no LLM in the selection"},
            "adaptive": {"policy": "adaptive", "k": list(CHECKPOINTS),
                         "scorer": SCORER, "tiebreak": TIEBREAK,
                         "tiebreak_seed": TIEBREAK_SEED,
                         "interest_grid": INTEREST_GRID,
                         "max_reveals": MAX_REVEALS,
                         "shards": N_ADAPTIVE_SHARDS,
                         "note": "exactly the EXP1b configuration; elicitation "
                                 "wording unchanged from the pilot"},
            "imposter": {"policy": "imposter", "k": list(CHECKPOINTS),
                         "seed": A.IMPOSTER_SEED,
                         "note": "random-person donor mirroring the random "
                                 "arm's reveal positions (Amendment A1); "
                                 "measures generic-profile harm, NOT Stage 2's "
                                 "same-domain imposter"},
        },
        "frozen_contrasts": [
            {"label": lab, "better": b, "worse": w, "k": k, "tier": tier}
            for lab, b, w, k, tier in FROZEN_CONTRASTS
        ],
        "decoding": {"primary": "expected_value",
                     "robustness": "argmax",
                     "rule": "every confirmatory contrast must hold in "
                             "direction under argmax decoding of the same "
                             "distributions (Addendum A section B)"},
        "projection": proj,
        "generated_utc": now(),
    }
    (CONFIRM_DIR / "config.json").write_text(json.dumps(config, indent=2),
                                             encoding="utf-8")

    jobs = {
        "confirm_static": {
            "kind": "static", "arms": ["baseline", "random", "fixed", "imposter"],
            "walltime": "04:00:00", "chunks": N_STATIC_CHUNKS,
            "node_outdir": NODE_RUN,
            "text": static_sbatch(
                "04:00:00",
                proj["jobs"]["confirm_static"]["projected_node_hours"]),
        },
    }
    for s in range(N_ADAPTIVE_SHARDS):
        name = f"confirm_adaptive_s{s}"
        jobs[name] = {
            "kind": "adaptive", "arms": ["adaptive"], "shard": s,
            "walltime": "03:30:00", "node_outdir": f"{NODE_RUN}/adaptive_s{s}",
            "text": adaptive_sbatch(
                s, "03:30:00", proj["jobs"][name]["projected_node_hours"]),
        }

    man = load_manifest()
    for name, spec in jobs.items():
        path = CONFIRM_DIR / f"{name}.sbatch"
        path.write_text(spec.pop("text"), encoding="utf-8")
        entry = man["jobs"].get(name, {})
        entry.update({
            "kind": spec["kind"], "arms": spec["arms"],
            "walltime": spec["walltime"],
            "sbatch_local": str(path.relative_to(_ROOT)),
            "sbatch_node": f"{NODE_JOBS}/{name}.sbatch",
            "node_outdir": spec["node_outdir"],
            "projected_node_hours":
                proj["jobs"][name]["projected_node_hours"],
            "status": entry.get("status", "bootstrapped"),
            "slurm_job_ids": entry.get("slurm_job_ids", []),
            "actual_node_hours": entry.get("actual_node_hours"),
        })
        if "shard" in spec:
            entry["shard"] = spec["shard"]
        if "chunks" in spec:
            entry["chunks"] = spec["chunks"]
        man["jobs"][name] = entry
        print(f"[bootstrap] {name}: sbatch -> {path.relative_to(_ROOT)}")
    save_manifest(man)
    print(f"[bootstrap] config -> {CONFIRM_DIR / 'config.json'}")
    print(f"[bootstrap] manifest -> {MANIFEST}")
    return 0


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def cmd_export(_args) -> int:
    verify_split()
    order = fixed_order()
    ids = confirm_ids()

    df = clean_riasec(load_riasec(DATA_DIR))
    codebook = load_codebook(DATA_DIR)
    pack = A.build_person_pack(df, codebook, ids)
    meta = A.static_meta(pack, codebook)
    donors = A.imposter_pairs(ids, seed=A.IMPOSTER_SEED)
    if any(p == d for p, d in donors.items()):
        raise SystemExit("[fatal] imposter pairing produced a self-pair")
    if set(donors) != set(ids):
        raise SystemExit("[fatal] imposter pairing does not cover the split")

    # ---- static arms: baseline + random + fixed + imposter ------------------
    # build_static_tasks IS the frozen 4-arm design: STATIC_POLICIES over
    # CHECKPOINTS. It runs assert_prompt_clean on every prompt it builds, so a
    # leaked TIPI answer or an out-of-order reveal block aborts the export.
    tasks = A.build_static_tasks(pack, meta, order, donors)
    expected = static_counts()["TOTAL"]
    if len(tasks) != expected:
        raise SystemExit(f"[fatal] built {len(tasks):,} static prompts, "
                         f"expected {expected:,}")
    per_policy: dict[str, int] = {}
    for t in tasks:
        per_policy[t["policy"]] = per_policy.get(t["policy"], 0) + 1

    with (CONFIRM_DIR / "tasks_static.jsonl").open("w", encoding="utf-8") as fh:
        for t in tasks:
            fh.write(json.dumps(t) + "\n")

    chunk_size = -(-len(tasks) // N_STATIC_CHUNKS)
    chunk_info = []
    for c in range(N_STATIC_CHUNKS):
        part = tasks[c * chunk_size:(c + 1) * chunk_size]
        path = CONFIRM_DIR / f"prompts_static_{c}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for t in part:
                fh.write(json.dumps({"idx": t["idx"], "prompt": t["prompt"],
                                     "max_output_tokens": t["max_output_tokens"]})
                         + "\n")
        chunk_info.append({"chunk": c, "n_prompts": len(part),
                           "idx_low": part[0]["idx"], "idx_high": part[-1]["idx"],
                           "sha256": _sha256_file(path)})
        print(f"[export] static chunk {c}: {len(part):,} prompts -> "
              f"{path.name}")
    if sum(ci["n_prompts"] for ci in chunk_info) != len(tasks):
        raise SystemExit("[fatal] static chunks do not sum to the task count")

    (CONFIRM_DIR / "pack_local.json").write_text(json.dumps(pack),
                                                 encoding="utf-8")
    (CONFIRM_DIR / "imposter_pairs.json").write_text(json.dumps({
        "pairs": {str(k): v for k, v in donors.items()},
        "seed": A.IMPOSTER_SEED,
        "method": "seeded permutation rotated by one position (single cycle, "
                  "no fixed point); donor drawn from the confirm split itself",
        "scope_note": "This random-person imposter measures generic-profile "
                      "harm. Stage 2's same-domain imposter is a different "
                      "construct; results must not be conflated.",
    }, indent=2), encoding="utf-8")

    # ---- adaptive arm: 4 shard packs, TIPI answers stripped -----------------
    shard_n = CONFIRM_N // N_ADAPTIVE_SHARDS
    shard_info = []
    for s in range(N_ADAPTIVE_SHARDS):
        sub_ids = ids[s * shard_n:(s + 1) * shard_n]
        sub_pack = [p for p in pack if p["person_id"] in set(sub_ids)]
        sub_pack.sort(key=lambda p: sub_ids.index(p["person_id"]))
        node = A.node_pack(sub_pack, codebook)
        node["meta"]["checkpoints"] = list(CHECKPOINTS)
        node["meta"]["max_reveals"] = MAX_REVEALS
        blob = json.dumps(node)
        # Structural hold-out check: no TIPI answer may reach the node.
        for person in node["persons"]:
            if "tipi" in person:
                raise SystemExit("[fatal] shard pack carries a tipi answer block")
        for code in TIPI_ITEMS:
            if f'"{code}": {{"text"' in blob and '"answer"' in blob:
                raise SystemExit(f"[fatal] TIPI answer for {code} reached the "
                                 "node pack")
        path = CONFIRM_DIR / f"pack_node_s{s}.json"
        path.write_text(blob, encoding="utf-8")
        shard_info.append({"shard": s, "n_persons": len(sub_pack),
                           "person_ids": sub_ids, "sha256": _sha256_file(path)})
        print(f"[export] adaptive shard {s}: {len(sub_pack)} persons -> "
              f"{path.name}")
    covered = [pid for si in shard_info for pid in si["person_ids"]]
    if covered != ids:
        raise SystemExit("[fatal] adaptive shards do not reproduce the split "
                         "exactly once, in order")

    (CONFIRM_DIR / "export_manifest.json").write_text(json.dumps({
        "n_persons": CONFIRM_N,
        "static_prompts_total": len(tasks),
        "static_prompts_per_policy": per_policy,
        "static_chunks": chunk_info,
        "adaptive_shards": [{k: v for k, v in si.items() if k != "person_ids"}
                            for si in shard_info],
        "adaptive_shard_person_ids": {str(si["shard"]): si["person_ids"]
                                      for si in shard_info},
        "fixed_order_first_20": order[:20],
        "exported_utc": now(),
    }, indent=2), encoding="utf-8")
    print(f"[export] total static prompts {len(tasks):,} {per_policy}")
    print(f"[export] manifest -> {CONFIRM_DIR / 'export_manifest.json'}")
    return 0


# ---------------------------------------------------------------------------
# Record job state
# ---------------------------------------------------------------------------


def cmd_record(args) -> int:
    man = load_manifest()
    if args.anomaly:
        man["anomalies"].append({"utc": now(), "job": args.name,
                                 "note": args.anomaly})
        print(f"[record] anomaly logged for {args.name}")
    entry = man["jobs"].setdefault(args.name, {})
    if args.job_id:
        entry.setdefault("slurm_job_ids", []).append(args.job_id)
    if args.status:
        entry["status"] = args.status
    if args.note:
        entry.setdefault("notes", []).append({"utc": now(), "note": args.note})
    save_manifest(man)
    print(f"[record] {args.name}: {entry.get('status')} "
          f"jobs={entry.get('slurm_job_ids')}")
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
    if not summary:
        return None
    secs = (summary.get("engine_init_seconds", 0.0)
            + summary.get("generation_wall_seconds", 0.0))
    return round(secs / 3600, 4) if secs else None


def _write_arm(arm: str, records: list[dict], extra: dict) -> dict:
    armdir = CONFIRM_DIR / "arms" / arm
    armdir.mkdir(parents=True, exist_ok=True)
    with (armdir / "records.jsonl").open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    per_k = {str(k): summarize([r for r in records if r["k"] == k])
             for k in sorted({r["k"] for r in records})}
    # Addendum A section E rule 3: keep example raw completions beside the
    # parse rate, so truncation is distinguishable from format failure.
    fails = [r for r in records if r["parse_failure"]]
    examples = {
        "n_parse_failures": len(fails),
        "failed_examples": [{"person_id": r["person_id"], "k": r["k"],
                             "item": r["item"],
                             "raw_response": (r["raw_response"] or "")[:400]}
                            for r in fails[:10]],
        "ok_examples": [{"person_id": r["person_id"], "k": r["k"],
                         "item": r["item"],
                         "raw_response": (r["raw_response"] or "")[:400]}
                        for r in records[:3]],
    }
    (armdir / "parse_examples.json").write_text(json.dumps(examples, indent=2),
                                                encoding="utf-8")
    summary = {
        "config": {"policy": arm, "split": SPLIT_LABEL, "variant": A.VARIANT,
                   "model": MODEL_LABEL, "backend": "leonardo-batch",
                   "temperature": 0.0},
        "totals": {
            "n_records": len(records),
            "n_parse_failures": len(fails),
            "parse_rate": round(1.0 - len(fails) / max(len(records), 1), 6),
            "tokens_in": sum(r["tokens_in"] for r in records),
            "tokens_out": sum(r["tokens_out"] for r in records),
            "n_persons": len({r["person_id"] for r in records}),
            "checkpoints": sorted({r["k"] for r in records}),
        },
        "per_k_scoring": per_k,
        "extra": extra,
    }
    (armdir / "summary.json").write_text(json.dumps(summary, indent=2),
                                         encoding="utf-8")
    return summary


def _log_arm_cost(arm: str, records: list[dict], node_hours: float | None,
                  side_calls: int, note: str) -> None:
    """One cost-log line per ARM, as Addendum A section A requires."""
    append_cost_log(build_cost_entry(
        run_id=f"stage1e_confirm/{arm}", model=MODEL_LABEL, split=SPLIT_LABEL,
        variant=A.VARIANT, n_persons=len({r["person_id"] for r in records}),
        n_calls=len(records) + side_calls, n_retries=0,
        n_parse_failures=sum(1 for r in records if r["parse_failure"]),
        tokens_in=sum(r["tokens_in"] for r in records),
        tokens_out=sum(r["tokens_out"] for r in records),
        backend="leonardo-batch", node_hours=node_hours,
    ), RESULTS_DIR / "cost_log.jsonl")
    print(f"[cost] {arm}: {node_hours if node_hours is not None else '?'} "
          f"node-hours, {len(records) + side_calls:,} calls ({note})")


def _ingest_static(nodedir: Path) -> tuple[dict, int]:
    """Split the chunked static completions back into the four static arms."""
    tasks = _read_jsonl(CONFIRM_DIR / "tasks_static.jsonl")
    pack = json.loads((CONFIRM_DIR / "pack_local.json").read_text(
        encoding="utf-8"))
    by_id = {p["person_id"]: p for p in pack}

    comps: dict[int, dict] = {}
    job_summaries = []
    for c in range(N_STATIC_CHUNKS):
        path = nodedir / f"completions_static_{c}.jsonl"
        if not path.exists():
            print(f"[warn] static chunk {c} has no completions file",
                  file=sys.stderr)
            continue
        for row in _read_jsonl(path):
            comps[int(row["idx"])] = row
        side = nodedir / f"completions_static_{c}.jsonl.summary.json"
        if side.exists():
            job_summaries.append(json.loads(side.read_text()))

    by_policy: dict[str, list[dict]] = {p: [] for p in A.STATIC_POLICIES}
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

    # The four arms shared one engine init. Apportion the job's node-hours by
    # each arm's share of output tokens, and keep the job total visible.
    init_s = max((s.get("engine_init_seconds", 0.0) for s in job_summaries),
                 default=0.0)
    gen_s = sum(s.get("generation_wall_seconds", 0.0) for s in job_summaries)
    job_hours = round((init_s + gen_s) / 3600, 4) if (init_s or gen_s) else None
    total_out = sum(sum(r["tokens_out"] for r in recs)
                    for recs in by_policy.values()) or 1

    summaries = {}
    for policy, records in by_policy.items():
        share = sum(r["tokens_out"] for r in records) / total_out
        hours = round(job_hours * share, 4) if job_hours is not None else None
        summaries[policy] = _write_arm(policy, records, {
            "n_missing_completions": missing,
            "job": "confirm_static",
            "job_node_hours_total": job_hours,
            "node_hours_apportioned_by": "share of output tokens in the shared "
                                         "static job",
            "chunk_summaries": job_summaries,
        })
        _log_arm_cost(policy, records, hours, 0,
                      f"{share:.1%} of the shared static job")
        print(f"[ingest] {policy}: {len(records):,} records, parse rate "
              f"{summaries[policy]['totals']['parse_rate']:.4f}")
    return summaries, missing


def _ingest_adaptive(nodedir: Path) -> tuple[dict, int]:
    """Join the 4 adaptive shards into one arm, rebuilding every prompt.

    Every prompt is rebuilt locally from the reveal order and compared with
    what the node actually sent. A mismatch means the node and the ingester
    disagree about the interview -- the one failure that would quietly corrupt
    every downstream number.
    """
    pack = json.loads((CONFIRM_DIR / "pack_local.json").read_text(
        encoding="utf-8"))
    by_id = {p["person_id"]: p for p in pack}
    codebook = load_codebook(DATA_DIR)
    meta = A.static_meta(pack, codebook)
    tipi_texts = [meta["tipi_texts"][c] for c in TIPI_ITEMS]

    records: list[dict] = []
    mismatch = 0
    reveal_all: dict[int, list[str]] = {}
    unc_rows: list[dict] = []
    shard_summaries = []
    seen_shards = []
    for s in range(N_ADAPTIVE_SHARDS):
        sdir = nodedir / f"adaptive_s{s}"
        comp_path = sdir / "completions_adaptive.jsonl"
        if not comp_path.exists():
            print(f"[warn] adaptive shard {s} has no completions",
                  file=sys.stderr)
            continue
        seen_shards.append(s)
        reveal = {int(k): v for k, v in json.loads(
            (sdir / "reveal_orders.json").read_text()).items()}
        reveal_all.update(reveal)
        for comp in _read_jsonl(comp_path):
            pid, k, code = int(comp["person_id"]), int(comp["k"]), comp["item"]
            person = by_id[pid]
            pairs = [(person["interests"][c]["text"],
                      person["interests"][c]["answer"])
                     for c in reveal[pid][:k]]
            rebuilt = R.tipi_prompt(person["demographics_block"], pairs,
                                    meta["riasec_anchors"],
                                    meta["tipi_texts"][code],
                                    meta["tipi_anchors"])
            if rebuilt != comp["prompt"]:
                mismatch += 1
            true = person["tipi"][code]["answer"]
            A.assert_prompt_clean(comp["prompt"], meta["tipi_texts"][code],
                                  true, tipi_texts, pairs)
            task = {"person_id": pid, "arm": "twin", "item": code,
                    "policy": "adaptive", "k": k, "donor_id": None,
                    "prompt": comp["prompt"]}
            records.append(A.record_from_completion(
                task, comp.get("text"), comp.get("tokens_in", 0),
                comp.get("tokens_out", 0), true))
        upath = sdir / "uncertainty.jsonl"
        if upath.exists():
            unc_rows += _read_jsonl(upath)
        npath = sdir / "node_summary.json"
        if npath.exists():
            shard_summaries.append(dict(json.loads(npath.read_text()),
                                        shard=s))

    (CONFIRM_DIR / "reveal_orders.json").write_text(
        json.dumps({str(k): v for k, v in reveal_all.items()}, indent=2),
        encoding="utf-8")

    ties = _tie_diagnostic(unc_rows) if unc_rows else None
    if ties:
        (CONFIRM_DIR / "tie_diagnostic.json").write_text(
            json.dumps(ties, indent=2), encoding="utf-8")

    hours = sum(h for h in (_node_hours(s) for s in shard_summaries)
                if h is not None) or None
    extra = {
        "job": [f"confirm_adaptive_s{s}" for s in seen_shards],
        "shards_ingested": seen_shards,
        "n_prompt_rebuild_mismatches": mismatch,
        "n_uncertainty_calls": len(unc_rows),
        "n_uncertainty_parse_failures": sum(
            1 for r in unc_rows if r.get("parse_failure")),
        "tie_diagnostic": ties,
        "shard_summaries": shard_summaries,
        "node_hours_total": hours,
    }
    summary = _write_arm("adaptive", records, extra)
    _log_arm_cost("adaptive", records, hours, len(unc_rows),
                  f"{len(unc_rows):,} uncertainty calls included")
    tie_txt = f", tie rate {ties['pct_rounds_with_tie']}%" if ties else ""
    print(f"[ingest] adaptive: {len(records):,} predictions from "
          f"{len(seen_shards)} shards, {mismatch} prompt mismatches{tie_txt}")
    if mismatch:
        print(f"[warn] {mismatch} prompts did not rebuild byte-identically.",
              file=sys.stderr)
    return {"adaptive": summary}, mismatch


def _tie_diagnostic(unc: list[dict]) -> dict:
    by_round: dict[tuple, list[float]] = {}
    for row in unc:
        val = row.get("score", row.get("entropy"))
        by_round.setdefault((row["person_id"], row["round"]), []).append(
            float(val))
    tied, spreads, tops, n_tied = 0, [], [], []
    for scores in by_round.values():
        top = max(scores)
        count = sum(1 for e in scores if e == top)
        tied += int(count > 1)
        n_tied.append(count)
        tops.append(top)
        spreads.append(top - min(scores))
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


def cmd_ingest(args) -> int:
    nodedir = Path(args.nodedir)
    man = load_manifest()
    if args.which in ("static", "all"):
        _, missing = _ingest_static(nodedir)
        man["jobs"].setdefault("confirm_static", {})["status"] = "ingested"
        if missing:
            man["anomalies"].append({
                "utc": now(), "job": "confirm_static",
                "note": f"{missing} completions missing from the static job"})
            print(f"[warn] {missing} static completions missing.",
                  file=sys.stderr)
    if args.which in ("adaptive", "all"):
        _, mismatch = _ingest_adaptive(nodedir)
        for s in range(N_ADAPTIVE_SHARDS):
            man["jobs"].setdefault(f"confirm_adaptive_s{s}",
                                   {})["status"] = "ingested"
        if mismatch:
            man["anomalies"].append({
                "utc": now(), "job": "confirm_adaptive",
                "note": f"{mismatch} prompts did not rebuild byte-identically"})
    save_manifest(man)
    return 0


# ---------------------------------------------------------------------------
# Analysis: the frozen bars, applied mechanically, under both decodings
# ---------------------------------------------------------------------------


def _load_arm(arm: str) -> list[dict]:
    path = CONFIRM_DIR / "arms" / arm / "records.jsonl"
    return _read_jsonl(path) if path.exists() else []


def _as_decoding(records: list[dict], decoding: str) -> list[dict]:
    """Force a decoding. ``argmax`` drops the EV point so scoring falls back
    to the parsed argmax digit -- same distributions, different read-off."""
    if decoding == "expected_value":
        return records
    if decoding != "argmax":
        raise ValueError(decoding)
    return [dict(r, prediction_ev=None) for r in records]


def _relabel(records: list[dict], arm: str) -> list[dict]:
    return [dict(r, arm=arm) for r in records]


def _at(records: list[dict], k: int) -> list[dict]:
    return [r for r in records if r["k"] == k]


def _contrast(better: list[dict], worse: list[dict],
              decoding: str) -> dict | None:
    """Paired MAE lift of ``better`` over ``worse`` through the shared path."""
    if not better or not worse:
        return None
    b = _relabel(_as_decoding(better, decoding), "twin")
    w = _relabel(_as_decoding(worse, decoding), "baseline")
    block = summarize(b + w)["mae"]
    return {
        "lift_mean": block["lift"]["mean"],
        "ci_low": block["lift"]["ci_low"],
        "ci_high": block["lift"]["ci_high"],
        "t_p": block["tests"]["t_p"],
        "better_mae": block["twin"]["mean"],
        "worse_mae": block["baseline"]["mean"],
        "n_persons": block["lift"].get("n"),
    }


def cmd_analyse(_args) -> int:
    arms = {a: _load_arm(a) for a in ARMS}
    have = {a: bool(v) for a, v in arms.items()}
    print(f"[analyse] arms present: "
          f"{', '.join(a for a in ARMS if have[a]) or 'none'}")
    missing = [a for a in ARMS if not have[a]]
    if missing:
        print(f"[analyse] NOT YET INGESTED: {', '.join(missing)}",
              file=sys.stderr)

    out: dict = {
        "run": "stage1e_confirm", "confirmatory": True,
        "contract": "PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md section B",
        "arms_present": [a for a in ARMS if have[a]],
        "arms_missing": missing,
        "generated_utc": now(),
        "raw_mae": {}, "lift_over_baseline": {}, "frozen_contrasts": {},
        "integrity": {},
    }

    # ---- raw MAEs, every arm, every checkpoint, both decodings -------------
    # Addendum A section E rule 1: lifts never appear without both arms' raw
    # MAEs, under both decodings.
    for decoding in ("expected_value", "argmax"):
        out["raw_mae"][decoding] = {}
        for arm in ARMS:
            if not have[arm]:
                continue
            ks = sorted({r["k"] for r in arms[arm]})
            per_k = {}
            for k in ks:
                rows = _as_decoding(_at(arms[arm], k), decoding)
                s = summarize(_relabel(rows, "twin") + _relabel(rows, "baseline"))
                per_k[str(k)] = s["mae"]["twin"]["mean"]
            out["raw_mae"][decoding][arm] = per_k

    # ---- lift over the demographics-only baseline (the curve) --------------
    if have["baseline"]:
        base = _at(arms["baseline"], 0)
        for decoding in ("expected_value", "argmax"):
            out["lift_over_baseline"][decoding] = {}
            for arm in ARMS:
                if arm == "baseline" or not have[arm]:
                    continue
                out["lift_over_baseline"][decoding][arm] = {
                    str(k): _contrast(_at(arms[arm], k), base, decoding)
                    for k in sorted({r["k"] for r in arms[arm]})
                }

    # ---- the frozen contrasts, both decodings ------------------------------
    for label, better, worse, k, tier in FROZEN_CONTRASTS:
        if not (have[better] and have[worse]):
            continue
        wk = 0 if worse == "baseline" else k
        entry = {"tier": tier, "better_arm": better, "worse_arm": worse, "k": k}
        for decoding in ("expected_value", "argmax"):
            entry[decoding] = _contrast(_at(arms[better], k),
                                        _at(arms[worse], wk), decoding)
        ev, am = entry["expected_value"], entry["argmax"]
        if ev and am:
            # The binding robustness rule: direction must agree.
            entry["direction_agrees"] = (
                (ev["lift_mean"] > 0) == (am["lift_mean"] > 0))
            entry["ev_significant"] = ev["t_p"] < 0.05
            entry["argmax_significant"] = am["t_p"] < 0.05
        out["frozen_contrasts"][label] = entry

    # ---- integrity ---------------------------------------------------------
    for arm in ARMS:
        if not have[arm]:
            continue
        recs = arms[arm]
        spath = CONFIRM_DIR / "arms" / arm / "summary.json"
        extra = json.loads(spath.read_text())["extra"] if spath.exists() else {}
        out["integrity"][arm] = {
            "n_records": len(recs),
            "n_persons": len({r["person_id"] for r in recs}),
            "checkpoints": sorted({r["k"] for r in recs}),
            "n_parse_failures": sum(1 for r in recs if r["parse_failure"]),
            "parse_rate": round(
                1.0 - sum(1 for r in recs if r["parse_failure"])
                / max(len(recs), 1), 6),
            "n_prompt_rebuild_mismatches": extra.get(
                "n_prompt_rebuild_mismatches"),
            "n_missing_completions": extra.get("n_missing_completions"),
            "node_hours": extra.get("node_hours_total")
                          or extra.get("job_node_hours_total"),
        }
    if (CONFIRM_DIR / "tie_diagnostic.json").exists():
        out["tie_diagnostic"] = json.loads(
            (CONFIRM_DIR / "tie_diagnostic.json").read_text())

    ANALYSIS.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[analyse] -> {ANALYSIS.relative_to(_ROOT)}")
    for label, entry in out["frozen_contrasts"].items():
        ev = entry.get("expected_value")
        am = entry.get("argmax")
        if not ev:
            continue
        print(f"  {entry['tier']:12s} {label}: EV {ev['lift_mean']:+.4f} "
              f"[{ev['ci_low']:+.4f}, {ev['ci_high']:+.4f}] p={ev['t_p']:.3g}"
              + (f" | argmax {am['lift_mean']:+.4f} p={am['t_p']:.3g}"
                 if am else ""))
    return 0


# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan").set_defaults(fn=cmd_plan)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    sub.add_parser("bootstrap").set_defaults(fn=cmd_bootstrap)
    sub.add_parser("export").set_defaults(fn=cmd_export)

    p_rec = sub.add_parser("record")
    p_rec.add_argument("--name", required=True)
    p_rec.add_argument("--job-id", default=None)
    p_rec.add_argument("--status", default=None)
    p_rec.add_argument("--note", default=None)
    p_rec.add_argument("--anomaly", default=None,
                       help="log an anomaly for the owner to review")
    p_rec.set_defaults(fn=cmd_record)

    p_in = sub.add_parser("ingest")
    p_in.add_argument("--nodedir", required=True,
                      help="local copy of the node run dir")
    p_in.add_argument("--which", default="all",
                      choices=("all", "static", "adaptive"))
    p_in.set_defaults(fn=cmd_ingest)

    sub.add_parser("analyse").set_defaults(fn=cmd_analyse)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
