#!/usr/bin/env python3
"""Ingest and score the EXPLORATORY H6 D_min = 3 arm.

Same discipline as ``experiments/h6_score.py``: the frozen drivers are
IMPORTED and a handful of module constants are re-pointed at
``results/stage2_confirm/h6_d3/``. Nothing about the join, the model pins, the
rubric hash, the canary rule or the spend guards is re-implemented — the code
that produced the registered H6 numbers is executed unchanged, and every
substitution is printed before it takes effect.

Three subcommands:

``ingest``  pull the Gemma completions off Leonardo, verify by prompt hash that
            the node read the file we built, join, and bill ``sacct``. This arm
            has its OWN job name (``dop-h6d3-gen``) so sacct bills it apart
            from the registered H6 generation.
``embed``   channel 1, the pinned mpnet revision, local CPU, $0.
``judge``   channel 2, gemini-3.5-flash on rubric r2, thinking budget 0, canary
            first, halt on any flip.

There is no ``genlite``: this arm runs on the PRIMARY model only, consistent
with the root-excluded sensitivity arm's precedent.

**Caps.** GPU: 0.2 additional node-hours for this exploratory arm, on top of
the 3.0-node-hour closeout phase cap which the prior H6 runs already drew
0.4112 from. API: this arm's own $0.75 sub-cap, inside H6's $6.00 sub-cap,
inside Stage 2's $15.00 cap. All three are enforced, the tightest one wins, and
the arithmetic is printed before the first call.

Run::

    .venv/bin/python experiments/h6_d3_score.py ingest --status
    .venv/bin/python experiments/h6_d3_score.py ingest
    .venv/bin/python experiments/h6_d3_score.py embed
    .venv/bin/python experiments/h6_d3_score.py judge --canary-only
    .venv/bin/python experiments/h6_d3_score.py judge --go
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

RESULTS_DIR = _ROOT / "results"
CONFIRM_DIR = RESULTS_DIR / "stage2_confirm"
D3_DIR = CONFIRM_DIR / "h6_d3"
COST_LOG = RESULTS_DIR / "cost_log.jsonl"

CHUNK = "chunk_01"
JOB_NAME = "dop-h6d3-gen"
REMOTE_RUN = "/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage2_confirm_h6d3_gen"
GEN_RUN_ID = "stage2_confirm/h6_d3_gen_gemma"
JUDGE_RUN_ID = "stage2_confirm/h6_d3_judge_r2"
CANARY_RUN_ID = "stage2_confirm/h6_d3_judge_r2_canary"
SPLIT = "stage2_confirm_h6_d3"

#: This exploratory arm's own caps.
D3_NODE_HOUR_CAP = 0.2
D3_API_CAP_USD = 0.75
#: The caps it sits inside.
H6_API_CAP_USD = 6.00
STAGE2_API_CAP_USD = 15.00
PHASE_NODE_HOUR_CAP = 3.0
#: GPU already billed to H6 before this arm, from ``results/cost_log.jsonl``.
PRIOR_H6_GPU_RUN_IDS = ("stage2_confirm/h6_classify",
                        "stage2_confirm/h6_gen_gemma")

D3_RUN_PREFIX = "stage2_confirm/h6_d3"
H6_RUN_PREFIX = "stage2_confirm/h6"
STAGE2_RUN_PREFIX = "stage2_confirm"


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


def spend(prefix: str) -> float:
    if not COST_LOG.exists():
        return 0.0
    total = 0.0
    for line in COST_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if str(entry.get("run_id", "")).startswith(prefix):
            total += float(entry.get("cost_usd") or 0.0)
    return round(total, 6)


def announce(name: str, overrides: dict) -> None:
    print(f"[h6-d3] running the frozen {name} driver against "
          f"{D3_DIR.relative_to(_ROOT)}. Overridden constants:")
    for k, v in overrides.items():
        print(f"[h6-d3]   {k} = {v}")


def budget_for_driver() -> tuple[float, dict]:
    """The driver's stop number = the tightest of the three caps.

    Each driver compares TOTAL Stage-2 spend against one budget number, so a
    sub-cap is expressed as (spend outside the sub-cap) + (the sub-cap).
    """
    d3 = spend(D3_RUN_PREFIX)
    h6 = spend(H6_RUN_PREFIX)
    all2 = spend(STAGE2_RUN_PREFIX)
    by_d3 = round(all2 - d3 + D3_API_CAP_USD, 6)
    by_h6 = round(all2 - h6 + H6_API_CAP_USD, 6)
    by_stage2 = STAGE2_API_CAP_USD
    budget = min(by_d3, by_h6, by_stage2)
    detail = {"spend_d3": d3, "spend_h6": h6, "spend_stage2": all2,
              "stop_at_d3_cap": by_d3, "stop_at_h6_cap": by_h6,
              "stop_at_stage2_cap": by_stage2, "binding": budget}
    if all2 > STAGE2_API_CAP_USD:
        raise fatal(f"Stage-2 API spend ${all2} already exceeds the "
                    f"${STAGE2_API_CAP_USD} cap")
    return budget, detail


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


def cmd_ingest(rest: list[str]) -> int:
    import h6_ingest as I

    from doppler import stage2_data as S
    from doppler.costlog import append_cost_log, build_cost_entry

    ap = argparse.ArgumentParser(prog="h6_d3_score.py ingest")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--skip-cost", action="store_true")
    args = ap.parse_args(rest)

    I.H6_DIR = D3_DIR
    I.GEN_DIR = D3_DIR / "gen" / "gemma"
    I.NODE_OUT = D3_DIR / "node_out"
    I.REMOTE_RUN = REMOTE_RUN
    I.JOB_NAME = JOB_NAME
    I.RUN_ID = GEN_RUN_ID
    I.SPLIT = SPLIT
    announce("h6_ingest", {"H6_DIR": str(I.H6_DIR), "GEN_DIR": str(I.GEN_DIR),
                           "NODE_OUT": str(I.NODE_OUT),
                           "REMOTE_RUN": I.REMOTE_RUN,
                           "JOB_NAME": I.JOB_NAME, "RUN_ID": I.RUN_ID,
                           "SPLIT": I.SPLIT})

    bill = I.sacct_node_hours()
    already = I.logged(GEN_RUN_ID)
    prior = round(sum(I.logged(r) for r in PRIOR_H6_GPU_RUN_IDS), 4)
    delta = round(bill["node_hours_all_attempts"] - already, 4)
    print(f"[bill] {bill['n_attempts']} attempt(s) of {JOB_NAME}, "
          f"{bill['node_hours_all_attempts']} node-hours from sacct "
          f"(already logged: {already}, new: {delta})")
    for job in bill["jobs"]:
        print(f"  {job['job_id']} {job['state']:12s} {job['elapsed']} "
              f"x{job['nnodes']}")
    print(f"[bill] this arm's cap {D3_NODE_HOUR_CAP} node-hours; closeout "
          f"phase: prior H6 GPU {prior} + this arm "
          f"{bill['node_hours_all_attempts']} = "
          f"{round(prior + bill['node_hours_all_attempts'], 4)} of "
          f"{PHASE_NODE_HOUR_CAP}")
    if args.status:
        return 0

    if bill["node_hours_all_attempts"] > D3_NODE_HOUR_CAP:
        raise fatal(f"this arm billed {bill['node_hours_all_attempts']} "
                    f"node-hours, past its {D3_NODE_HOUR_CAP} cap; stop and "
                    "report the arithmetic")
    if prior + bill["node_hours_all_attempts"] > PHASE_NODE_HOUR_CAP:
        raise fatal(f"the closeout phase would reach "
                    f"{prior + bill['node_hours_all_attempts']} node-hours, "
                    f"past the {PHASE_NODE_HOUR_CAP} cap")

    items = {r["item_id"]: r
             for r in S.read_jsonl(D3_DIR / "items_confirm.jsonl")}
    summary = I.ingest_chunk(CHUNK, items)

    if delta > 0 and not args.skip_cost:
        entry = build_cost_entry(
            run_id=GEN_RUN_ID, model=I.MODEL, split=SPLIT,
            n_persons=len({r["canonical_id"] for r in S.read_jsonl(
                I.GEN_DIR / f"completions_{CHUNK}.jsonl")}),
            n_calls=summary["n_rows"], n_retries=0,
            n_parse_failures=summary["n_empty"],
            tokens_in=summary["tokens_in"], tokens_out=summary["tokens_out"],
            backend="leonardo-batch", node_hours=delta)
        append_cost_log(entry, COST_LOG)
        print(f"[cost] logged {delta} node-hours for {GEN_RUN_ID}")
    S.write_json(I.GEN_DIR / "node_hours_accounting.json",
                 {"run_id": GEN_RUN_ID, "billing": bill,
                  "prior_h6_node_hours": prior,
                  "phase_cap": PHASE_NODE_HOUR_CAP,
                  "arm_cap": D3_NODE_HOUR_CAP, "billed_this_run": delta})
    return 0


# ---------------------------------------------------------------------------
# Channel 1
# ---------------------------------------------------------------------------


def cmd_embed(rest: list[str]) -> int:
    import stage2_confirm_embed as E

    E.CONFIRM_DIR = D3_DIR
    E.GEN_ROOT = D3_DIR / "gen"
    E.EMBED_DIR = D3_DIR / "embed"
    E.CHUNK_ALLOWLIST = (CHUNK,)
    announce("embed", {"CONFIRM_DIR": str(E.CONFIRM_DIR),
                       "GEN_ROOT": str(E.GEN_ROOT),
                       "EMBED_DIR": str(E.EMBED_DIR),
                       "CHUNK_ALLOWLIST": E.CHUNK_ALLOWLIST,
                       "models": "gemma (primary model only)"})
    return E.main(["--models", "gemma", *rest])


# ---------------------------------------------------------------------------
# Channel 2
# ---------------------------------------------------------------------------


def cmd_judge(rest: list[str]) -> int:
    import stage2_confirm_judge as J

    budget, detail = budget_for_driver()
    J.CONFIRM_DIR = D3_DIR
    J.JUDGE_DIR = D3_DIR / "judge"
    J.RUN_ID = JUDGE_RUN_ID
    J.CANARY_RUN_ID = CANARY_RUN_ID
    J.SPLIT = SPLIT
    J.CHUNK_ALLOWLIST = (CHUNK,)
    # ``budget_usd`` is a default argument bound when the class was defined, so
    # re-binding the module constant alone would not reach it. Rebinding the
    # default is the whole override; the guard's arithmetic is untouched.
    J.CONFIRM_API_BUDGET_USD = budget
    J.SpendGuard.__init__.__defaults__ = (budget,)
    announce("judge", {"CONFIRM_DIR": str(J.CONFIRM_DIR),
                       "JUDGE_DIR": str(J.JUDGE_DIR),
                       "RUN_ID": J.RUN_ID, "CANARY_RUN_ID": J.CANARY_RUN_ID,
                       "CHUNK_ALLOWLIST": J.CHUNK_ALLOWLIST,
                       "budget_usd": f"{budget} {detail}"})
    return J.main(["--models", "gemma", *rest])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("ingest", "embed", "judge"))
    args, rest = ap.parse_known_args(argv)
    return {"ingest": cmd_ingest, "embed": cmd_embed,
            "judge": cmd_judge}[args.command](rest)


if __name__ == "__main__":
    raise SystemExit(main())
