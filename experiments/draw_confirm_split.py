"""Draw the frozen Stage 1E confirm split (Addendum A, section A).

n=1,000, seed 46, from the cleaned RIASEC pool after excluding
(i) every person_id appearing in any run dir under results/ (automatic scan)
and (ii) the 2,000 derivation-split ids, which have no records.jsonl and are
therefore invisible to the scan — they MUST be loaded from
results/overnight_exp2/derivation_ids.json, per the warning in that file.

Prints both exclusion counts, their overlap, the remaining pool size, and
verifies the drawn split is disjoint from everything excluded.

Run: uv run python experiments/draw_confirm_split.py
"""

import json
from pathlib import Path

import numpy as np

from doppler.adaptive import scan_used_person_ids
from doppler.data import clean_riasec, load_riasec

CONFIRM_N = 1000
CONFIRM_SEED = 46
DERIVATION_FILE = Path("results/overnight_exp2/derivation_ids.json")
OUT_DIR = Path("results/stage1e_confirm")

df = clean_riasec(load_riasec("data/riasec"))
all_ids = df["person_id"].tolist()

per_run = scan_used_person_ids("results")
used_runs: set[int] = set().union(*per_run.values()) if per_run else set()

deriv_doc = json.loads(DERIVATION_FILE.read_text())
deriv = {int(x) for x in deriv_doc["person_ids"]}

overlap = used_runs & deriv
pool = np.array([pid for pid in all_ids if pid not in used_runs and pid not in deriv],
                dtype=np.int64)

print(f"excluded from run-dir scan ({len(per_run)} run dirs): {len(used_runs)}")
print(f"excluded from derivation file (seed {deriv_doc['seed']}): {len(deriv)}")
print(f"overlap between the two exclusion sets: {len(overlap)}")
print(f"cleaned pool: {len(all_ids)}; remaining after exclusions: {pool.size}")

if len(deriv) != 2000:
    raise SystemExit(f"derivation file has {len(deriv)} ids, expected 2000 — stop.")

rng = np.random.default_rng(CONFIRM_SEED)
chosen = sorted(int(x) for x in rng.choice(pool, size=CONFIRM_N, replace=False))

assert len(set(chosen)) == CONFIRM_N
assert not (set(chosen) & used_runs) and not (set(chosen) & deriv)
print(f"drawn: {len(chosen)} persons, seed {CONFIRM_SEED}; "
      "disjointness vs both exclusion sets verified")

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "confirm_ids.json").write_text(json.dumps({
    "split": "stage1e_confirm",
    "n": CONFIRM_N,
    "seed": CONFIRM_SEED,
    "excluded_run_scan": len(used_runs),
    "excluded_derivation": len(deriv),
    "provenance": "Addendum A section A; drawn 2026-07-25",
    "person_ids": chosen,
}, indent=1))
print(f"written: {OUT_DIR / 'confirm_ids.json'}")
