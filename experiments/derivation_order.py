"""EXP2: draw a large derivation split and freeze the best fixed item order.

Why this exists
---------------
In the training-split pilot (results/adaptive_pilot_train.md) the "fixed" item
order was picked using the same 150 people it was then scored on, so its
advantage was inflated by an unknown amount. Worse, re-deriving that order on
two halves of 75 people gave orders sharing only 10 of 20 items, when pure
chance alone would give 8.3. In other words, at n=150 the order was mostly
noise.

This script fixes that. It draws 2000 fresh people who have never been used by
any run, derives the full 48-item order on them, and measures how reproducible
that order is. The frozen order is then applied later, unchanged, to the
training-split people who had no say in picking it. That is the honest test.

What this script does NOT do
----------------------------
No model is called here. This is plain ridge regression on the raw recorded
answers, running on the local CPU. Scoring the frozen order with the twin is a
separate static job on Leonardo. The confirm split is not drawn, named, or
touched anywhere in this file.

Run with:
    cd /Users/umaraslam/Projects/DOPPLER && uv run python experiments/derivation_order.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from doppler import adaptive as A  # noqa: E402
from doppler.data import RIASEC_ITEMS, clean_riasec, load_riasec  # noqa: E402

DATA_DIR = _ROOT / "data"
RESULTS_DIR = _ROOT / "results"
OUTDIR = RESULTS_DIR / "overnight_exp2"

EXPERIMENT_NAME = "overnight_exp2"

#: The derivation split: 2000 people, drawn with rng(45) from everyone who has
#: never appeared in a run directory and is not in the 150-person train split.
DERIVATION_N = 2000
DERIVATION_SEED = 45

#: Seed for cutting the 2000 into two halves of 1000 for the stability check.
#: A different number from the pilot's 4242 so the two checks are independent.
HALF_SPLIT_SEED = 4243

#: Reveal budgets this order will later be evaluated at.
CHECKPOINTS = [1, 2, 3, 4, 5, 8, 12, 16, 20, 28, 36, 48]

N_ITEMS = len(RIASEC_ITEMS)  # 48
TOP_K = 20  # the budget the overlap statistic is reported at

#: The pilot's own split-half check, for the "n=2000 vs n=150" comparison.
PILOT_STABILITY_PATH = (
    RESULTS_DIR / "adaptive_train_20260724-210916" / "fixed_order_stability.json"
)

#: How long we are willing to wait for the three greedy selections.
TIME_BUDGET_SECONDS = 15 * 60


def log(msg: str) -> None:
    """Print with a timestamp so a long step is visibly alive."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Step 1: draw the derivation split and prove it touches nobody used before
# ---------------------------------------------------------------------------


def draw_derivation_split(df) -> dict:
    """Pick 2000 people nobody has used yet, and check that claim mechanically.

    Two exclusion sources are combined:

    1. every person_id found in any records.jsonl under results/ (everyone any
       run has ever scored), and
    2. the 150-person training split.

    The training-split people already appear in source 1 because the pilot ran
    on them, so the union is smaller than the sum. Both are removed anyway, so
    the result does not depend on that overlap.
    """
    used_by_dir = A.scan_used_person_ids(RESULTS_DIR)
    used_in_runs: set[int] = set()
    for pids in used_by_dir.values():
        used_in_runs |= pids
    train = set(A.train_ids(df))
    excluded = used_in_runs | train

    all_ids = df["person_id"].tolist()
    pool = np.array([pid for pid in all_ids if pid not in excluded], dtype=np.int64)
    if DERIVATION_N > pool.size:
        raise SystemExit(
            f"[fatal] wanted {DERIVATION_N} people but only {pool.size} are free."
        )

    rng = np.random.default_rng(DERIVATION_SEED)
    ids = sorted(int(x) for x in rng.choice(pool, size=DERIVATION_N, replace=False))

    chosen = set(ids)
    overlap_runs = sorted(chosen & used_in_runs)
    overlap_train = sorted(chosen & train)
    per_dir = {
        name: sorted(chosen & pids)
        for name, pids in used_by_dir.items()
        if chosen & pids
    }

    return {
        "split": "derivation2000",
        "n": len(ids),
        "n_unique": len(chosen),
        "seed": DERIVATION_SEED,
        "person_ids": ids,
        "n_cleaned_persons": int(len(df)),
        "pool_size_after_exclusions": int(pool.size),
        "exclusion_sources": {
            "existing_run_directories": {
                "n_dirs": len(used_by_dir),
                "n_persons": len(used_in_runs),
                "dirs": sorted(used_by_dir),
            },
            "train150_split": {
                "n_persons": len(train),
                "seed": A.TRAIN_SEED,
            },
        },
        "n_persons_in_runs_outside_train150": len(used_in_runs - train),
        "n_excluded_total_union": len(excluded),
        "overlap_with_existing_runs": len(overlap_runs),
        "overlap_with_train150": len(overlap_train),
        "overlap_by_run_dir": per_dir,
        "disjoint": not overlap_runs and not overlap_train and len(chosen) == len(ids),
    }


def check_split_or_die(split: dict) -> None:
    """Print the disjointness proof; stop the whole script if anything overlaps."""
    src = split["exclusion_sources"]
    log(f"cleaned RIASEC respondents: {split['n_cleaned_persons']:,}")
    log(f"excluded: {src['existing_run_directories']['n_persons']} people across "
        f"{src['existing_run_directories']['n_dirs']} run directories "
        f"(of which {split['n_persons_in_runs_outside_train150']} are outside the "
        f"train-150 split), plus the {src['train150_split']['n_persons']}-person "
        f"train split -> {split['n_excluded_total_union']} distinct people excluded")
    log(f"free pool: {split['pool_size_after_exclusions']:,} people")
    log(f"drawn: {split['n']} with seed {split['seed']} "
        f"({split['n_unique']} of them distinct)")
    log(f"overlap with existing runs: {split['overlap_with_existing_runs']}")
    log(f"overlap with train-150:     {split['overlap_with_train150']}")
    log(f"disjoint: {split['disjoint']}")
    if not split["disjoint"]:
        print("[fatal] the derivation split touches people who were already used. "
              "Nothing was written. Stopping.", file=sys.stderr)
        raise SystemExit(2)


# ---------------------------------------------------------------------------
# Step 2: how long will the greedy selection take?
# ---------------------------------------------------------------------------


def _work_units(n_steps: int, n_demo_cols: int) -> float:
    """Rough cost of a greedy run: one unit per candidate ridge fit, size-weighted.

    At step s the code tries the (48 - s) items it has not picked yet, and each
    trial solves a ridge system with (demographics + s + 1) columns. Solve cost
    grows with the square of the column count, so that is the weight.
    """
    return float(sum((N_ITEMS - s) * (n_demo_cols + s + 1) ** 2
                     for s in range(n_steps)))


def project_runtime(df, ids: list[int], probe_steps: int = 4) -> float:
    """Time a few greedy steps, then project the full 48-item run from them."""
    frame = df[df["person_id"].isin(ids)]
    n_demo = A._demographic_design(frame).shape[1]
    t0 = time.perf_counter()
    A.greedy_fixed_order(df, ids, n_items=probe_steps)
    probe_seconds = time.perf_counter() - t0
    ratio = _work_units(N_ITEMS, n_demo) / _work_units(probe_steps, n_demo)
    projected = probe_seconds * ratio
    log(f"timing probe: {probe_steps} of {N_ITEMS} items on {len(ids)} people took "
        f"{probe_seconds:.1f}s ({n_demo} demographic columns) -> the full order "
        f"should take about {projected:.0f}s")
    return projected


# ---------------------------------------------------------------------------
# Step 3: stability
# ---------------------------------------------------------------------------


def rank_correlation(order_a: list[str], order_b: list[str]) -> float:
    """Spearman correlation between two orders, computed with numpy only.

    Each item gets its position in the order as its rank (1 = picked first).
    Positions are unique, so there are no tied ranks, and Spearman is then
    exactly Pearson on those ranks. No scipy needed.
    """
    if sorted(order_a) != sorted(order_b):
        raise ValueError("the two orders do not cover the same items")
    rank_a = {item: i + 1 for i, item in enumerate(order_a)}
    rank_b = {item: i + 1 for i, item in enumerate(order_b)}
    items = sorted(rank_a)
    a = np.array([rank_a[i] for i in items], dtype=float)
    b = np.array([rank_b[i] for i in items], dtype=float)
    a -= a.mean()
    b -= b.mean()
    denom = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / denom)


def load_pilot_stability() -> dict:
    """The pilot's n=150 split-half numbers, read from disk (never recomputed)."""
    if not PILOT_STABILITY_PATH.exists():
        return {"available": False, "path": str(PILOT_STABILITY_PATH)}
    old = json.loads(PILOT_STABILITY_PATH.read_text(encoding="utf-8"))
    n_selected = len(old["full_order"])
    return {
        "available": True,
        "path": str(PILOT_STABILITY_PATH),
        "n_per_half": old["n_per_half"],
        "n_items_selected": n_selected,
        "overlap_between_halves": old["overlap_top20_between_halves"],
        "expected_overlap_if_random": old["expected_overlap_if_random"],
        "first_item_agrees": old["first_item_agrees"],
        "half_a_matches_full": old["half_a_matches_full"],
        "half_b_matches_full": old["half_b_matches_full"],
        "note": (
            "The pilot only ever derived 20 items, so there is no 48-item rank "
            "correlation to compare against. The overlap statistic is the same "
            "one: how many of the top 20 two independently derived orders share."
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    log("EXP2: derivation split + frozen best fixed order (CPU only, no model calls)")

    # -- Step 1 ------------------------------------------------------------
    log("loading and cleaning the RIASEC data...")
    df = clean_riasec(load_riasec(DATA_DIR))
    log("drawing the derivation split...")
    split = draw_derivation_split(df)
    check_split_or_die(split)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    ids = split["person_ids"]

    ids_record = dict(split)
    ids_record["generated_utc"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds")
    ids_record["what_this_is"] = (
        "The 2000 people used to derive project DOPPLER's frozen 48-item reveal "
        "order for Stage 1E. Their recorded answers were fed to a ridge "
        "regression to choose the order. No model saw them."
    )
    ids_record["how_to_reproduce"] = (
        "Clean the RIASEC frame, remove every person_id that appears in any "
        "records.jsonl under results/ and every id returned by "
        "doppler.adaptive.train_ids, then draw 2000 with "
        "numpy.random.default_rng(45).choice(pool, size=2000, replace=False). "
        "The list here is sorted ascending; the draw order is not meaningful."
    )
    ids_record["WARNING_FUTURE_CONFIRM_DRAWS_MUST_EXCLUDE_THESE_IDS"] = (
        "These 2000 people are BURNED. The frozen item order was fitted to their "
        "answers, so scoring any twin on them would be scoring a model on its own "
        "training data. This directory contains no records.jsonl, which means "
        "doppler.adaptive.scan_used_person_ids WILL NOT find these ids "
        "automatically. Any future split -- confirm or otherwise -- must load "
        "this file and subtract these ids from its pool by hand."
    )
    ids_record["only_field_that_changes_between_reruns"] = "generated_utc"
    ids_path = OUTDIR / "derivation_ids.json"
    ids_path.write_text(json.dumps(ids_record, indent=2), encoding="utf-8")
    log(f"wrote {ids_path}")

    # -- Step 2 ------------------------------------------------------------
    log("checking how long the greedy selection will take...")
    projected = project_runtime(df, ids)
    # Three full selections: the 2000, and each half of 1000. The halves are
    # cheaper than the full run, so 3x the full-run estimate is conservative.
    if projected * 3 > TIME_BUDGET_SECONDS:
        print(f"[fatal] projected {projected * 3 / 60:.1f} minutes for the three "
              f"selections, over the {TIME_BUDGET_SECONDS / 60:.0f}-minute budget. "
              "Stopping rather than changing adaptive.py.", file=sys.stderr)
        return 3

    log(f"deriving the full {N_ITEMS}-item order on all {len(ids)} people "
        f"(greedy forward selection, ridge regression, no model calls)...")
    t0 = time.perf_counter()
    fixed = A.greedy_fixed_order(df, ids, n_items=N_ITEMS)
    seconds_full = time.perf_counter() - t0
    log(f"done in {seconds_full:.1f}s")

    order = fixed["order"]
    trace = fixed["trace"]
    log(f"ridge lambda {fixed['lambda']}, {fixed['folds']}-fold out-of-fold MAE: "
        f"{fixed['base_oof_mae']:.4f} with demographics only")
    print("\n  step  item   out-of-fold MAE", flush=True)
    for row in trace:
        print(f"  {row['step']:>4}  {row['item']:<5}  {row['oof_mae']:.4f}", flush=True)
    print(f"\n  frozen order: {' '.join(order)}\n", flush=True)

    # Deliberately no wall-clock field here: this file must be byte-identical
    # across reruns. Timing is printed instead.
    fixed_out = dict(fixed)
    fixed_out["split"] = "derivation2000"
    fixed_out["oof_mae_at_k"] = {
        "0": fixed["base_oof_mae"],
        **{str(row["step"]): row["oof_mae"] for row in trace
           if row["step"] in CHECKPOINTS},
    }
    fixed_path = OUTDIR / "fixed_order_derivation.json"
    fixed_path.write_text(json.dumps(fixed_out, indent=2), encoding="utf-8")
    log(f"wrote {fixed_path}")

    # -- Step 3 ------------------------------------------------------------
    log("stability check: cutting the 2000 into two halves of 1000 and deriving "
        "the order separately on each...")
    rng = np.random.default_rng(HALF_SPLIT_SEED)
    perm = [ids[i] for i in rng.permutation(len(ids))]
    half_a = sorted(perm[: len(ids) // 2])
    half_b = sorted(perm[len(ids) // 2:])
    if set(half_a) & set(half_b):
        raise SystemExit("[fatal] the two halves are not disjoint.")

    log(f"half A: {len(half_a)} people, deriving...")
    t0 = time.perf_counter()
    res_a = A.greedy_fixed_order(df, half_a, n_items=N_ITEMS)
    log(f"half A done in {time.perf_counter() - t0:.1f}s")
    log(f"half B: {len(half_b)} people, deriving...")
    t0 = time.perf_counter()
    res_b = A.greedy_fixed_order(df, half_b, n_items=N_ITEMS)
    log(f"half B done in {time.perf_counter() - t0:.1f}s")

    order_a, order_b = res_a["order"], res_b["order"]
    overlap_ab = len(set(order_a[:TOP_K]) & set(order_b[:TOP_K]))
    chance = TOP_K * TOP_K / N_ITEMS
    rho = rank_correlation(order_a, order_b)

    stability = {
        "experiment": EXPERIMENT_NAME,
        "what_this_measures": (
            "Whether the frozen item order is a real signal or a coincidence of "
            "one sample. Two independent halves are given the same job; if they "
            "agree far more than chance, the order means something."
        ),
        "derivation_n": len(ids),
        "half_split_seed": HALF_SPLIT_SEED,
        "n_per_half": len(half_a),
        "top_k": TOP_K,
        "n_items_total": N_ITEMS,

        "overlap_top20_between_halves": overlap_ab,
        "overlap_top20_chance_baseline": round(chance, 4),
        "overlap_top20_excess_over_chance": round(overlap_ab - chance, 4),
        "overlap_top20_pct_of_k": round(100.0 * overlap_ab / TOP_K, 1),

        "rank_correlation_all48_between_halves": round(rho, 4),
        "rank_correlation_chance_baseline": 0.0,
        "rank_correlation_chance_sd": round(1.0 / np.sqrt(N_ITEMS - 1), 4),
        "rank_correlation_z_vs_chance": round(rho * np.sqrt(N_ITEMS - 1), 3),

        "overlap_top20_half_a_vs_full": len(set(order_a[:TOP_K]) & set(order[:TOP_K])),
        "overlap_top20_half_b_vs_full": len(set(order_b[:TOP_K]) & set(order[:TOP_K])),
        "rank_correlation_all48_half_a_vs_full": round(
            rank_correlation(order_a, order), 4),
        "rank_correlation_all48_half_b_vs_full": round(
            rank_correlation(order_b, order), 4),

        "first_item_full": order[0],
        "first_item_half_a": order_a[0],
        "first_item_half_b": order_b[0],
        "first_item_halves_agree": order_a[0] == order_b[0],
        "first_item_half_a_agrees_with_full": order_a[0] == order[0],
        "first_item_half_b_agrees_with_full": order_b[0] == order[0],
        "first_item_chance_agreement": round(1.0 / N_ITEMS, 4),

        "full_order": order,
        "half_a_order": order_a,
        "half_b_order": order_b,
        "half_a_base_oof_mae": res_a["base_oof_mae"],
        "half_b_base_oof_mae": res_b["base_oof_mae"],
        "half_a_lambda": res_a["lambda"],
        "half_b_lambda": res_b["lambda"],

        "pilot_train150_for_comparison": load_pilot_stability(),
    }
    stability_path = OUTDIR / "stability_derivation.json"
    stability_path.write_text(json.dumps(stability, indent=2), encoding="utf-8")
    log(f"wrote {stability_path}")

    # -- config ------------------------------------------------------------
    config = {
        "name": EXPERIMENT_NAME,
        "one_line": (
            "Derive project DOPPLER's frozen 48-item reveal order on 2000 fresh "
            "people, so the order is never scored on the people who chose it."
        ),
        "split": {
            "name": "derivation2000",
            "n": DERIVATION_N,
            "seed": DERIVATION_SEED,
            "drawn_from": "cleaned RIASEC respondents",
            "excludes": [
                "every person_id in any records.jsonl under results/",
                "the 150-person train split (doppler.adaptive.train_ids, seed 44)",
            ],
            "ids_file": str(ids_path),
        },
        "seeds": {
            "derivation_draw": DERIVATION_SEED,
            "half_split": HALF_SPLIT_SEED,
            "ridge_cv": A.RIDGE_CV_SEED,
            "train150_draw": A.TRAIN_SEED,
        },
        "selection_method": {
            "algorithm": "greedy forward selection, one item at a time",
            "criterion": "5-fold out-of-fold mean absolute error on the 10 TIPI items",
            "model": "ridge regression on raw answers plus demographics",
            "lambda_grid": list(A.RIDGE_LAMBDAS),
            "folds": A.RIDGE_FOLDS,
            "tie_break": "lowest canonical item index",
            "code": "doppler.adaptive.greedy_fixed_order (imported, not copied)",
        },
        "checkpoints": CHECKPOINTS,
        "derives": [
            "the derivation split's person ids",
            "the frozen 48-item reveal order",
            "how stable that order is (split-half overlap and rank correlation)",
        ],
        "does_not_do": [
            "no model calls of any kind -- this is CPU ridge regression",
            "no GPU, no Leonardo, no network",
            "does not score the frozen order; a separate static Leonardo job "
            "evaluates it on the train-150 people",
            "does not draw, name, or reserve a confirm split",
        ],
        "outputs": {
            "derivation_ids": str(ids_path),
            "fixed_order": str(fixed_path),
            "stability": str(stability_path),
            "config": str(OUTDIR / "config.json"),
        },
        "determinism": (
            "Every seed is explicit and the code has no wall-clock dependence, so "
            "reruns produce identical files apart from the 'generated_utc' "
            "timestamp in derivation_ids.json. One caveat: the exclusion set is "
            "read live from results/, so if a new run directory appears the free "
            "pool changes and the draw would change with it. The ids file is the "
            "record of what was actually drawn."
        ),
    }
    config_path = OUTDIR / "config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    log(f"wrote {config_path}")

    # -- Step 5: summary ---------------------------------------------------
    by_step = {row["step"]: row["oof_mae"] for row in trace}
    pilot = stability["pilot_train150_for_comparison"]
    print("\n" + "=" * 72, flush=True)
    print("SUMMARY", flush=True)
    print("=" * 72, flush=True)
    print(f"First {TOP_K} items of the frozen order:", flush=True)
    print("  " + " ".join(order[:TOP_K]), flush=True)
    print(f"\nSplit-half agreement at k={TOP_K} (1000 people per half):", flush=True)
    print(f"  {overlap_ab}/{TOP_K} shared, against {chance:.2f} expected by pure "
          f"chance ({overlap_ab - chance:+.2f})", flush=True)
    if pilot["available"]:
        print(f"  pilot at n=150 (75 per half): "
              f"{pilot['overlap_between_halves']}/{pilot['n_items_selected']} shared, "
              f"chance {pilot['expected_overlap_if_random']}", flush=True)
    print(f"\nRank agreement over all {N_ITEMS} items between halves "
          f"(Spearman, 0 = chance):", flush=True)
    print(f"  {rho:+.3f}  (chance spread is about "
          f"{stability['rank_correlation_chance_sd']:.3f}, so this is "
          f"{stability['rank_correlation_z_vs_chance']:+.1f} sd from chance)",
          flush=True)
    print(f"\nOut-of-fold TIPI MAE on the derivation split:", flush=True)
    print(f"  k=0  (demographics only) {fixed['base_oof_mae']:.4f}", flush=True)
    print(f"  k=20                     {by_step[20]:.4f}", flush=True)
    print(f"  k=48 (all items)         {by_step[48]:.4f}", flush=True)
    print(f"\nGreedy selection on the full 2000 took {seconds_full:.1f}s.", flush=True)
    print(f"Files written under {OUTDIR}", flush=True)
    print("=" * 72, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
