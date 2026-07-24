"""Idempotent driver: run variants v0, v1, v2 over the pilot2 split.

For each variant, in order:
  * if a COMPLETE run dir already exists (1000 records) -> skip it;
  * else if a PARTIAL run dir exists -> resume it;
  * else -> start it fresh.

Re-invoking the driver picks up exactly where it left off. If a run aborts from
exhausted retries (e.g. a dead daily quota) or the shared call budget, the
driver prints a line starting ``[quota-or-fatal]`` and EXITS without starting
the next variant (which would only burn retries on a dead quota).

One shared in-code call budget of 3500 covers the whole driver invocation.

Usage:
    uv run python experiments/run_pilot2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import run_replay  # noqa: E402
from run_replay import (  # noqa: E402
    DEFAULT_SEED,
    RESULTS_DIR,
    completed_keys,
    run_fresh,
    run_resume,
)

VARIANTS = ("v0", "v1", "v2")
SPLIT = "pilot2"
K = 48
EXPECTED_RECORDS = 1000  # 50 persons x 10 items x 2 arms
BUDGET = 3500            # in-code call cap for this driver invocation


def _existing_run(variant: str) -> tuple[Path | None, int]:
    """The most-progressed existing run dir for this variant, and its record count."""
    dirs = sorted(RESULTS_DIR.glob(f"{SPLIT}_{variant}_k{K}_*"))
    candidates = [
        (len(completed_keys(d / "records.jsonl")), d)
        for d in dirs
        if (d / "records.jsonl").exists()
    ]
    if not candidates:
        return None, 0
    candidates.sort()
    count, best = candidates[-1]
    return best, count


def main() -> int:
    used = 0
    for variant in VARIANTS:
        run_dir, count = _existing_run(variant)

        if run_dir is not None and count >= EXPECTED_RECORDS:
            print(f"[skip] {variant}: already complete ({count} records) at {run_dir}")
            continue

        remaining = BUDGET - used
        if remaining <= 0:
            print(f"[quota-or-fatal] {variant}: driver call budget of {BUDGET} "
                  "exhausted before starting; stopping.")
            return 1

        if run_dir is not None:
            print(f"[driver] {variant}: resuming {run_dir} ({count}/{EXPECTED_RECORDS} "
                  f"done), budget left {remaining}")
            outcome = run_resume(str(run_dir), max_calls=remaining)
        else:
            print(f"[driver] {variant}: starting fresh, budget left {remaining}")
            outcome = run_fresh(SPLIT, K, DEFAULT_SEED, variant, max_calls=remaining)

        used += outcome.n_calls

        if outcome.exit_code != 0 or not outcome.complete:
            print(f"[quota-or-fatal] {variant}: run did not complete "
                  f"(exit={outcome.exit_code}); {used} calls used this invocation. "
                  "Not starting the next variant. Re-run the driver to resume.")
            return 1

        print(f"[driver] {variant}: complete ({used} calls used so far).")

    print(f"[driver] all variants complete ({used} calls this invocation).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
