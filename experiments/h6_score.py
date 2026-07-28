#!/usr/bin/env python3
"""Run the FROZEN confirmatory scoring drivers against the H6 directory.

H6 scores on exactly the instrument H1 scored on. Rather than copy three
drivers and let them drift, this file IMPORTS them and re-points three or four
module constants at ``results/stage2_confirm/h6/``:

  * ``experiments/stage2_confirm_gen_flashlite.py`` -- robustness generations
  * ``experiments/stage2_confirm_embed.py``        -- channel 1, pinned mpnet
  * ``experiments/stage2_confirm_judge.py``        -- channel 2, r2 stance judge

Nothing else about them is touched: the model pins, the temperature, the
rubric hash, the canary rule, the resume-by-hash logic, the per-chunk cost
lines and every stop condition are the code that produced the H1 numbers,
executed unchanged. What is overridden, and why, is listed per subcommand
below and printed at run time so the substitution is never silent.

**Budget.** Two caps are enforced at once:

  * the Stage-2 confirmatory cap of $15 across every ``stage2_confirm*`` run,
    which the drivers already enforce; and
  * H6's own sub-cap of **$6.00**, enforced here by setting each driver's
    budget to (non-H6 Stage-2 spend) + $6.00, so the driver's own mid-chunk
    guard stops at exactly the H6 limit.

**Chunk scope.** ``chunk_01`` carries the four arms both models generate;
``chunk_02`` carries the two root-excluded sensitivity arms, which run on the
PRIMARY model only. The subcommands default to the right chunks per model, so
the sensitivity arm cannot be sent to the API by accident.

Run::

    .venv/bin/python experiments/h6_score.py genlite --dry-run
    .venv/bin/python experiments/h6_score.py genlite
    .venv/bin/python experiments/h6_score.py embed
    .venv/bin/python experiments/h6_score.py judge --canary-only
    .venv/bin/python experiments/h6_score.py judge --go
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
H6_DIR = CONFIRM_DIR / "h6"
COST_LOG = RESULTS_DIR / "cost_log.jsonl"

#: H6's own API sub-cap. The Stage-2 $15 cap still applies on top.
H6_API_CAP_USD = 6.00
STAGE2_API_CAP_USD = 15.00
H6_RUN_PREFIX = "stage2_confirm/h6"
STAGE2_RUN_PREFIX = "stage2_confirm"

#: chunk_01 = the four arms both models generate. chunk_02 = the two
#: root-excluded sensitivity arms, primary model only.
SHARED_CHUNKS = ["chunk_01"]
PRIMARY_ONLY_CHUNKS = ["chunk_02"]
ALL_CHUNKS = SHARED_CHUNKS + PRIMARY_ONLY_CHUNKS


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
    return total


def budget_for_driver() -> tuple[float, float, float]:
    """(driver budget, H6 spend so far, all-Stage-2 spend so far).

    The driver's guard compares (all Stage-2 spend) against one number, so the
    number that makes it stop at H6's own $6 is the non-H6 Stage-2 spend plus
    $6. Returned rather than hidden, and printed before anything is spent.
    """
    h6 = spend(H6_RUN_PREFIX)
    all2 = spend(STAGE2_RUN_PREFIX)
    return round(all2 - h6 + H6_API_CAP_USD, 6), round(h6, 6), round(all2, 6)


def announce(name: str, overrides: dict) -> None:
    print(f"[h6-score] running the frozen {name} driver against the H6 "
          f"directory. Overridden constants:")
    for k, v in overrides.items():
        print(f"[h6-score]   {k} = {v}")


# ---------------------------------------------------------------------------
# Channel 0: robustness generations
# ---------------------------------------------------------------------------


def cmd_genlite(rest: list[str]) -> int:
    import stage2_confirm_gen_flashlite as F

    driver_budget, h6_spent, all_spent = budget_for_driver()
    F.RUN_ID = "stage2_confirm/h6_gen_flashlite"
    F.SPLIT = "stage2_confirm_h6"
    F.CHUNK_ALLOWLIST = tuple(SHARED_CHUNKS)
    announce("gen_flashlite", {
        "RUN_ID": F.RUN_ID, "SPLIT": F.SPLIT,
        "CHUNK_ALLOWLIST": F.CHUNK_ALLOWLIST,
        "out-dir": str(H6_DIR),
        "budget-usd": f"{driver_budget} (= Stage-2 non-H6 spend "
                      f"${all_spent - h6_spent:.4f} + H6 cap "
                      f"${H6_API_CAP_USD:.2f})"})
    if all_spent > STAGE2_API_CAP_USD:
        raise fatal(f"Stage-2 API spend ${all_spent} already exceeds the "
                    f"${STAGE2_API_CAP_USD} cap")
    argv = ["--out-dir", str(H6_DIR), "--budget-usd", str(driver_budget),
            "--chunks", *SHARED_CHUNKS, *rest]
    return F.main(argv)


# ---------------------------------------------------------------------------
# Channel 1: embeddings
# ---------------------------------------------------------------------------


def cmd_embed(rest: list[str]) -> int:
    import stage2_confirm_embed as E

    E.CONFIRM_DIR = H6_DIR
    E.GEN_ROOT = H6_DIR / "gen"
    E.EMBED_DIR = H6_DIR / "embed"
    E.CHUNK_ALLOWLIST = tuple(ALL_CHUNKS)
    announce("embed", {"CONFIRM_DIR": str(E.CONFIRM_DIR),
                       "GEN_ROOT": str(E.GEN_ROOT),
                       "EMBED_DIR": str(E.EMBED_DIR),
                       "CHUNK_ALLOWLIST": E.CHUNK_ALLOWLIST})
    return E.main(list(rest))


# ---------------------------------------------------------------------------
# Channel 2: the stance judge
# ---------------------------------------------------------------------------


def cmd_judge(rest: list[str]) -> int:
    import stage2_confirm_judge as J

    driver_budget, h6_spent, all_spent = budget_for_driver()
    J.CONFIRM_DIR = H6_DIR
    J.JUDGE_DIR = H6_DIR / "judge"
    J.RUN_ID = "stage2_confirm/h6_judge_r2"
    J.CANARY_RUN_ID = "stage2_confirm/h6_judge_r2_canary"
    J.SPLIT = "stage2_confirm_h6"
    J.CHUNK_ALLOWLIST = tuple(ALL_CHUNKS)
    # ``budget_usd`` is a default argument bound when the class was defined,
    # so re-binding the module constant alone would not reach it. Rebinding
    # the default is the whole override; the guard's arithmetic is untouched.
    J.CONFIRM_API_BUDGET_USD = driver_budget
    J.SpendGuard.__init__.__defaults__ = (driver_budget,)
    announce("judge", {"CONFIRM_DIR": str(J.CONFIRM_DIR),
                       "JUDGE_DIR": str(J.JUDGE_DIR),
                       "RUN_ID": J.RUN_ID,
                       "CANARY_RUN_ID": J.CANARY_RUN_ID,
                       "CHUNK_ALLOWLIST": J.CHUNK_ALLOWLIST,
                       "budget_usd": f"{driver_budget} (= Stage-2 non-H6 "
                                     f"spend ${all_spent - h6_spent:.4f} + H6 "
                                     f"cap ${H6_API_CAP_USD:.2f})"})
    if all_spent > STAGE2_API_CAP_USD:
        raise fatal(f"Stage-2 API spend ${all_spent} already exceeds the "
                    f"${STAGE2_API_CAP_USD} cap")
    return J.main(list(rest))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("genlite", "embed", "judge"))
    args, rest = ap.parse_known_args(argv)
    return {"genlite": cmd_genlite, "embed": cmd_embed,
            "judge": cmd_judge}[args.command](rest)


if __name__ == "__main__":
    raise SystemExit(main())
