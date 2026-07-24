"""Stage-1E adaptive-elicitation gym (PREREGISTRATION_AMENDMENT_1.md, A6).

Setting: demographics are given up front, then the 48 RIASEC interest items are
revealed one at a time with the person's true recorded answer. At checkpoints
k in {1,2,4,8,12,16,20} the v2 twin predicts all 10 held-out TIPI items. The
primary metric is TIPI MAE lift over the demographics-only baseline as a
function of k, plus the A1 imposter arm.

Five policies:

``baseline``   demographics only, 10 predictions per person (k = 0).
``random``     per-person seeded reveal order.
``fixed``      ONE global order from greedy forward selection on the training
               split's raw data (ridge regression, no LLM in the selection).
``adaptive``   before each reveal the twin states a 1-5 distribution for every
               remaining item; the max-entropy item is revealed (ties -> lowest
               canonical item index). Sequential, so it runs on the node.
``imposter``   mirrors ``random`` -- same reveal *positions* -- but the whole
               profile (demographics + revealed values) belongs to a different
               training-split person under a seeded derangement. The prediction
               targets stay the test person's TIPI answers.

Everything here is additive: no existing module is modified. Prompt text comes
from :mod:`doppler.adaptive_render`, which is also rsynced to the compute node.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import adaptive_render as R
from .data import (
    CATEGORICAL_DEMOGRAPHICS,
    RIASEC_ITEMS,
    TIPI_ITEMS,
    Codebook,
    sample_eval_persons,
)
from .gym import PILOT2_N, PILOT2_SEED, SAMPLE_SEED, TOTAL_N
from .prompts import _demographics_block, _format_anchors

# ---------------------------------------------------------------------------
# Frozen protocol constants
# ---------------------------------------------------------------------------

#: Training split for Stage 1E: 150 persons, disjoint from pilot1 (20),
#: pilot2 (50) and the gate (500). The confirm split is NOT defined here and is
#: not touched until the owner commits the bar-lock addendum.
TRAIN_N = 150
TRAIN_SEED = 44

#: Budget checkpoints (A6). Predictions happen after exactly this many reveals.
CHECKPOINTS: tuple[int, ...] = (1, 2, 4, 8, 12, 16, 20)
MAX_REVEALS = max(CHECKPOINTS)

RANDOM_ORDER_SEED = 45
IMPOSTER_SEED = 46

VARIANT = "v2"
POLICIES = ("baseline", "random", "fixed", "adaptive", "imposter")
#: Policies whose prompts are fully determined before any model call.
STATIC_POLICIES = ("baseline", "random", "fixed", "imposter")

#: Greedy forward selection settings (statistical, no LLM).
RIDGE_FOLDS = 5
RIDGE_CV_SEED = 47
RIDGE_LAMBDAS = (0.1, 1.0, 10.0, 100.0)


# ---------------------------------------------------------------------------
# Split
# ---------------------------------------------------------------------------


def train_ids(df: pd.DataFrame) -> list[int]:
    """150 persons drawn with rng(44) from everyone outside the 520 and pilot2.

    Built with the same seeded-draw machinery as the existing splits, so the
    result is deterministic and disjoint by construction: the 520-draw
    (seed 42) and the pilot2 draw (seed 43) are both reproduced and removed
    from the pool before sampling.
    """
    used = set(sample_eval_persons(df, n=TOTAL_N, seed=SAMPLE_SEED))
    remaining = np.array(
        [pid for pid in df["person_id"].tolist() if pid not in used], dtype=np.int64
    )
    rng2 = np.random.default_rng(PILOT2_SEED)
    used |= {int(x) for x in rng2.choice(remaining, size=PILOT2_N, replace=False)}

    pool = np.array(
        [pid for pid in df["person_id"].tolist() if pid not in used], dtype=np.int64
    )
    if TRAIN_N > pool.size:
        raise ValueError(
            f"Requested {TRAIN_N} training persons but only {pool.size} remain."
        )
    rng = np.random.default_rng(TRAIN_SEED)
    chosen = rng.choice(pool, size=TRAIN_N, replace=False)
    return [int(x) for x in chosen]


def person_ids_in_run_dir(run_dir: str | Path) -> set[int]:
    """Every ``person_id`` that appears in a run directory's records.jsonl."""
    path = Path(run_dir) / "records.jsonl"
    ids: set[int] = set()
    if not path.exists():
        return ids
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(int(json.loads(line)["person_id"]))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
    return ids


def scan_used_person_ids(results_dir: str | Path) -> dict[str, set[int]]:
    """``{run_dir_name: person_ids}`` for every run dir under ``results/``.

    Recurses one level so the per-arm subdirectories of an adaptive run are
    picked up too.
    """
    out: dict[str, set[int]] = {}
    root = Path(results_dir)
    for path in sorted(root.rglob("records.jsonl")):
        name = str(path.parent.relative_to(root))
        ids = person_ids_in_run_dir(path.parent)
        if ids:
            out[name] = ids
    return out


# ---------------------------------------------------------------------------
# Person pack (the only thing shipped to the compute node)
# ---------------------------------------------------------------------------


def build_person_pack(df: pd.DataFrame, codebook: Codebook,
                      ids: list[int]) -> list[dict]:
    """Per-person rendered demographics + item texts/answers, in ``ids`` order."""
    by_id = df.set_index("person_id", drop=False)
    pack: list[dict] = []
    for pid in ids:
        row = by_id.loc[pid]
        demo: dict[str, object] = {}
        for var in CATEGORICAL_DEMOGRAPHICS:
            codes = codebook.demographic_decoders.get(var, {})
            value = row[var]
            demo[var] = None if pd.isna(value) else codes.get(int(value))
        demo["age"] = None if pd.isna(row["age"]) else int(row["age"])
        demo["familysize"] = (
            None if pd.isna(row["familysize"]) else int(row["familysize"])
        )
        demo["country"] = None if pd.isna(row["country"]) else str(row["country"])
        demo["major"] = None if pd.isna(row["major"]) else str(row["major"])

        pack.append({
            "person_id": int(pid),
            "demographics_block": _demographics_block(demo),
            "interests": {
                c: {"text": codebook.riasec_items.get(c, ""), "answer": int(row[c])}
                for c in RIASEC_ITEMS
            },
            "tipi": {
                c: {"text": codebook.tipi_items.get(c, ""), "answer": int(row[c])}
                for c in TIPI_ITEMS
            },
        })
    return pack


def node_pack(pack: list[dict], codebook: Codebook) -> dict:
    """The pack as shipped to Leonardo: **TIPI answers are stripped**.

    The node never needs a TIPI answer -- predictions are scored locally
    against the local record -- so removing them makes the cross-domain
    hold-out a structural property of the transfer, not just a prompt-level
    check.
    """
    persons = []
    for p in pack:
        persons.append({
            "person_id": p["person_id"],
            "demographics_block": p["demographics_block"],
            "interests": p["interests"],
            "tipi_texts": {c: p["tipi"][c]["text"] for c in TIPI_ITEMS},
        })
    return {
        "meta": {
            "variant": VARIANT,
            "riasec_anchors": _format_anchors(codebook.scales["riasec"]["anchors"]),
            "tipi_anchors": _format_anchors(codebook.scales["tipi"]["anchors"]),
            "riasec_codes": list(RIASEC_ITEMS),
            "tipi_codes": list(TIPI_ITEMS),
            "checkpoints": list(CHECKPOINTS),
            "max_reveals": MAX_REVEALS,
            "max_output_tokens_tipi": R.MAX_OUTPUT_TOKENS_TIPI,
            "max_output_tokens_interest": R.MAX_OUTPUT_TOKENS_INTEREST,
        },
        "persons": persons,
    }


# ---------------------------------------------------------------------------
# Reveal orders
# ---------------------------------------------------------------------------


def random_order(person_id: int, seed: int = RANDOM_ORDER_SEED) -> list[str]:
    """A per-person seeded permutation of all 48 interest item codes."""
    rng = np.random.default_rng(seed * 1000003 + person_id)
    return [RIASEC_ITEMS[i] for i in rng.permutation(len(RIASEC_ITEMS))]


def imposter_pairs(ids: list[int], seed: int = IMPOSTER_SEED) -> dict[int, int]:
    """Deterministic derangement ``{person_id: donor_id}``; never self-paired.

    A seeded permutation is rotated by one position, which is a single cycle
    over all persons and therefore has no fixed point for n >= 2.
    """
    if len(ids) < 2:
        raise ValueError("need at least 2 persons to build a derangement")
    rng = np.random.default_rng(seed)
    order = [int(x) for x in rng.permutation(np.array(ids, dtype=np.int64))]
    pairs = {order[i]: order[(i + 1) % len(order)] for i in range(len(order))}
    if any(k == v for k, v in pairs.items()):
        raise AssertionError("imposter pairing produced a self-pair")
    return pairs


# ---------------------------------------------------------------------------
# Best fixed order: greedy forward selection with ridge regression (no LLM)
# ---------------------------------------------------------------------------


def _demographic_design(df_train: pd.DataFrame) -> np.ndarray:
    """Always-present covariates: age, family size, and categorical dummies.

    The twin always sees demographics, so the greedy selection measures each
    interest item's *incremental* predictive value on top of them. Free-text
    ``country``/``major`` are excluded (high cardinality, n=150).
    """
    cols: list[np.ndarray] = [
        df_train["age"].to_numpy(dtype=float),
        df_train["familysize"].to_numpy(dtype=float),
    ]
    for var in CATEGORICAL_DEMOGRAPHICS:
        values = df_train[var].to_numpy()
        levels = sorted({int(v) for v in values if not pd.isna(v)})
        for level in levels[1:]:  # drop-first to avoid exact collinearity
            cols.append((values == level).astype(float))
    return np.column_stack(cols)


def _folds(n: int, k: int, seed: int) -> list[np.ndarray]:
    idx = np.random.default_rng(seed).permutation(n)
    return [np.sort(part) for part in np.array_split(idx, k)]


def _ridge_oof_mae(X: np.ndarray, Y: np.ndarray, lam: float,
                   folds: list[np.ndarray]) -> float:
    """Mean out-of-fold absolute error over all targets (all folds pooled).

    Closed-form ridge on centred, train-fold-standardised features; the
    intercept is the train-fold target mean and is never penalised.
    """
    n = X.shape[0]
    errs: list[float] = []
    for test_idx in folds:
        mask = np.ones(n, dtype=bool)
        mask[test_idx] = False
        Xtr, Xte = X[mask], X[test_idx]
        Ytr, Yte = Y[mask], Y[test_idx]

        mu = Xtr.mean(axis=0)
        sd = Xtr.std(axis=0)
        sd[sd < 1e-12] = 1.0
        Ztr = (Xtr - mu) / sd
        Zte = (Xte - mu) / sd
        ybar = Ytr.mean(axis=0)

        gram = Ztr.T @ Ztr + lam * np.eye(Ztr.shape[1])
        W = np.linalg.solve(gram, Ztr.T @ (Ytr - ybar))
        pred = ybar + Zte @ W
        errs.append(float(np.abs(pred - Yte).mean()))
    return float(np.mean(errs))


def greedy_fixed_order(df: pd.DataFrame, ids: list[int],
                       n_items: int = MAX_REVEALS) -> dict:
    """Greedy forward selection of the global best fixed reveal order.

    At each step the item added is the one that most reduces 5-fold
    out-of-fold MAE for the 10 TIPI targets, given the demographics and the
    items already selected. Ties break to the lowest canonical item index.
    Returns the order plus the OOF-MAE trace and the frozen lambda.
    """
    train = df[df["person_id"].isin(ids)].sort_values("person_id").reset_index(drop=True)
    D = _demographic_design(train)
    items = np.column_stack([train[c].to_numpy(dtype=float) for c in RIASEC_ITEMS])
    Y = np.column_stack([train[c].to_numpy(dtype=float) for c in TIPI_ITEMS])
    folds = _folds(len(train), RIDGE_FOLDS, RIDGE_CV_SEED)

    base_scores = {lam: _ridge_oof_mae(D, Y, lam, folds) for lam in RIDGE_LAMBDAS}
    lam = min(RIDGE_LAMBDAS, key=lambda x: (base_scores[x], x))
    base_mae = base_scores[lam]

    selected: list[int] = []
    order: list[str] = []
    trace: list[dict] = []
    for _ in range(n_items):
        best_col, best_mae = None, None
        for col in range(len(RIASEC_ITEMS)):
            if col in selected:
                continue
            X = np.column_stack([D, items[:, selected + [col]]])
            mae = _ridge_oof_mae(X, Y, lam, folds)
            # Strict '<' with canonical iteration order = lowest-index tie-break.
            if best_mae is None or mae < best_mae:
                best_col, best_mae = col, mae
        selected.append(int(best_col))
        order.append(RIASEC_ITEMS[best_col])
        trace.append({"step": len(order), "item": RIASEC_ITEMS[best_col],
                      "oof_mae": round(float(best_mae), 6)})

    return {
        "order": order,
        "lambda": lam,
        "base_oof_mae": round(base_mae, 6),
        "base_oof_mae_by_lambda": {str(k): round(v, 6) for k, v in base_scores.items()},
        "trace": trace,
        "n_train": int(len(train)),
        "folds": RIDGE_FOLDS,
        "cv_seed": RIDGE_CV_SEED,
    }


# ---------------------------------------------------------------------------
# Leakage guards
# ---------------------------------------------------------------------------


def assert_prompt_clean(prompt: str, tipi_text: str, true_answer: int,
                        all_tipi_texts: list[str], revealed_pairs: list) -> None:
    """Guards every TIPI prediction prompt must pass before it is sent."""
    head = prompt.split("\n\nYOUR TASK")[0]
    for text in all_tipi_texts:
        if text and text in head:
            raise AssertionError(f"TIPI item text leaked into a profile: {text!r}")
    if "I see myself as" in head:
        raise AssertionError("TIPI framing leaked into a profile")
    if prompt.count(tipi_text) != 1:
        raise AssertionError("questioned TIPI text does not appear exactly once")
    if f"{tipi_text}: {true_answer}" in prompt:
        raise AssertionError("the questioned item's answer is attached to it")
    _assert_reveal_order(head, revealed_pairs)


def assert_uncertainty_prompt_clean(prompt: str, item_text: str,
                                    all_tipi_texts: list[str],
                                    revealed_pairs: list) -> None:
    """Guards every adaptive uncertainty prompt must pass before it is sent."""
    head = prompt.split("\n\nYOUR TASK")[0]
    for text in all_tipi_texts:
        if text and text in head:
            raise AssertionError(f"TIPI item text leaked into an uncertainty prompt")
    if "I see myself as" in head:
        raise AssertionError("TIPI framing leaked into an uncertainty prompt")
    if item_text in head:
        raise AssertionError("the queried item is already revealed in the profile")
    _assert_reveal_order(head, revealed_pairs)


def _assert_reveal_order(profile_head: str, revealed_pairs: list) -> None:
    """The revealed block must be exactly the policy's order, nothing extra."""
    lines = [ln for ln in profile_head.splitlines() if ln.startswith("- ")]
    if len(lines) != len(revealed_pairs):
        raise AssertionError(
            f"profile shows {len(lines)} revealed items, policy revealed "
            f"{len(revealed_pairs)}"
        )
    for line, (text, answer) in zip(lines, revealed_pairs):
        if line != f"- {text}: {answer}":
            raise AssertionError(f"revealed line out of policy order: {line!r}")


# ---------------------------------------------------------------------------
# Static-policy task construction
# ---------------------------------------------------------------------------


def _pairs(source: dict, codes: list[str]) -> list:
    return [(source["interests"][c]["text"], source["interests"][c]["answer"])
            for c in codes]


def build_static_tasks(pack: list[dict], meta: dict, fixed_order: list[str],
                       donors: dict[int, int]) -> list[dict]:
    """Every prompt for the four non-adaptive policies, in deterministic order.

    Order is policy -> person (split order) -> k (checkpoint order) -> TIPI item
    (canonical order), so ``idx`` is stable and reproducible from code alone.
    """
    by_id = {p["person_id"]: p for p in pack}
    tipi_texts = [meta["tipi_texts"][c] for c in TIPI_ITEMS]
    r_anchors = meta["riasec_anchors"]
    t_anchors = meta["tipi_anchors"]

    tasks: list[dict] = []
    for policy in STATIC_POLICIES:
        for person in pack:
            pid = person["person_id"]
            if policy == "baseline":
                schedule = [(0, person["demographics_block"], [])]
            elif policy == "random":
                order = random_order(pid)
                schedule = [(k, person["demographics_block"],
                             _pairs(person, order[:k])) for k in CHECKPOINTS]
            elif policy == "fixed":
                schedule = [(k, person["demographics_block"],
                             _pairs(person, fixed_order[:k])) for k in CHECKPOINTS]
            else:  # imposter: test person's reveal positions, donor's content
                donor = by_id[donors[pid]]
                if donor["person_id"] == pid:
                    raise AssertionError("imposter donor is the person themselves")
                order = random_order(pid)
                schedule = [(k, donor["demographics_block"],
                             _pairs(donor, order[:k])) for k in CHECKPOINTS]

            for k, demo_block, revealed in schedule:
                for code in TIPI_ITEMS:
                    text = meta["tipi_texts"][code]
                    prompt = R.tipi_prompt(demo_block, revealed, r_anchors,
                                           text, t_anchors)
                    true = person["tipi"][code]["answer"]
                    assert_prompt_clean(prompt, text, true, tipi_texts, revealed)
                    tasks.append({
                        "idx": len(tasks),
                        "prompt": prompt,
                        "max_output_tokens": R.MAX_OUTPUT_TOKENS_TIPI,
                        "person_id": pid,
                        "policy": policy,
                        "arm": "baseline" if policy == "baseline" else "twin",
                        "k": k,
                        "item": code,
                        "variant": VARIANT,
                        "donor_id": donors[pid] if policy == "imposter" else None,
                    })
    return tasks


def static_meta(pack: list[dict], codebook: Codebook) -> dict:
    return {
        "riasec_anchors": _format_anchors(codebook.scales["riasec"]["anchors"]),
        "tipi_anchors": _format_anchors(codebook.scales["tipi"]["anchors"]),
        "tipi_texts": {c: pack[0]["tipi"][c]["text"] for c in TIPI_ITEMS},
    }


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


def record_from_completion(task: dict, text: str | None, tokens_in: int,
                           tokens_out: int, true_answer: int,
                           error: str | None = None) -> dict:
    """Assemble one record with the same field set as the batch-file runner.

    Field names and semantics match ``experiments/run_replay.py``'s records, so
    ``doppler.scoring.summarize`` ingests these unchanged; ``k``, ``policy`` and
    ``donor_id`` are the only additions.
    """
    from .scoring import parse_response

    if error is not None:
        pr = parse_response("", VARIANT)
        raw = f"<no completion: {error}>"
    else:
        pr = parse_response(text, VARIANT)
        raw = text
    disc = pr["prediction_argmax"]
    mae_pt = pr["mae_point"]
    return {
        "person_id": task["person_id"],
        "arm": task["arm"],
        "item": task["item"],
        "variant": VARIANT,
        "policy": task["policy"],
        "k": task["k"],
        "donor_id": task.get("donor_id"),
        "prompt": task["prompt"],
        "raw_response": raw,
        "parsed": pr["parsed"],
        "prediction_ev": pr["prediction_ev"],
        "prediction_argmax": pr["prediction_argmax"],
        "renorm_offset": pr["renorm_offset"],
        "true_answer": true_answer,
        "correct": None if disc is None else (disc == true_answer),
        "within1": None if disc is None else (abs(disc - true_answer) <= 1),
        "abs_error": None if mae_pt is None else abs(mae_pt - true_answer),
        "parse_failure": pr["parse_failure"],
        "parse_retry": False,
        "tokens_in": int(tokens_in),
        "tokens_out": int(tokens_out),
    }


# ---------------------------------------------------------------------------
# Cost projection
# ---------------------------------------------------------------------------


def call_counts(n_persons: int = TRAIN_N) -> dict[str, int]:
    """Planned completions per policy (uncertainty calls counted separately)."""
    n_ck = len(CHECKPOINTS)
    n_items = len(RIASEC_ITEMS)
    per_person_uncertainty = sum(n_items - r for r in range(MAX_REVEALS))
    return {
        "baseline": n_persons * len(TIPI_ITEMS),
        "random": n_persons * n_ck * len(TIPI_ITEMS),
        "fixed": n_persons * n_ck * len(TIPI_ITEMS),
        "imposter": n_persons * n_ck * len(TIPI_ITEMS),
        "adaptive_predictions": n_persons * n_ck * len(TIPI_ITEMS),
        "adaptive_uncertainty": n_persons * per_person_uncertainty,
    }


def project_node_hours(n_persons: int = TRAIN_N,
                       output_tokens_per_second: float = 2016.6,
                       mean_output_tokens: float = 49.0,
                       engine_init_seconds: float = 185.0,
                       n_jobs: int = 2) -> dict:
    """Project GPU node-hours from the gate run's measured throughput.

    Defaults are the gate's own numbers (results/leonardo_gate/
    completions_v2.jsonl.summary.json): 2016.6 output tok/s at ~49 output
    tokens per completion, 181.5 s engine init, Gemma-4-31B-it TP=4.
    """
    counts = call_counts(n_persons)
    total = sum(counts.values())
    gen_seconds = total * mean_output_tokens / output_tokens_per_second
    init_seconds = engine_init_seconds * n_jobs
    seconds = gen_seconds + init_seconds
    return {
        "counts": counts,
        "total_completions": total,
        "assumed_output_tokens_per_second": output_tokens_per_second,
        "assumed_mean_output_tokens": mean_output_tokens,
        "generation_hours": round(gen_seconds / 3600, 4),
        "engine_init_hours": round(init_seconds / 3600, 4),
        "projected_node_hours": round(seconds / 3600, 4),
    }
