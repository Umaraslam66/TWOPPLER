#!/usr/bin/env python3
"""H5 (calibration) -- the SUBSTITUTED analysis, on existing Stage 2 records.

WHAT THIS IS NOT
----------------
This is **not** the registered H5 estimator. The registration says:

    "twin confidence (self-consistency sampling: k = 10 samples, agreement
     rate = confidence) is calibrated: ECE <= 0.10 on pooled predictions
     across Stages 2-3. Reliability diagrams reported regardless."
    -- PREREGISTRATION.md section 3, Stage 3 hypotheses

and Amendment 2 B9.b re-scopes the pooling to Stage 2 predictions only.

The registered estimator cannot be computed from the records that exist. Every
confirmatory generation was made at **temperature 0.0** (pinned, asserted in
``experiments/stage2_confirm_gen.sbatch`` and
``experiments/stage2_confirm_gen_flashlite.py``). Greedy decoding returns the
same string every time, so drawing k = 10 samples from the existing
configuration yields k identical answers and an agreement rate of exactly 1.0
for every item. The registered confidence is degenerate on this record -- it is
not "noisy" or "low-powered", it is constant. Running it properly means
re-generating at a temperature above zero, which is a fresh run, not a
re-analysis: see ``registered_projection()`` for the cost, which is what puts
it outside the cap the owner set.

WHAT THIS IS
------------
An owner-directed substitution, run at $0 on CPU over the records that do
exist: take a graded signal already attached to every generation, map it
monotonically to a [0, 1] confidence, and ask whether that confidence matches
the rate at which the generation is actually judged right.

- **Correctness** is the channel-2 stance label: SAME -> 1, DIFFERENT -> 0,
  UNCLEAR -> **excluded** (the frozen handling rule, Addendum A instrument
  parameter 6 adopting Amendment 3 C2.3). Every exclusion is counted and
  reported; nothing is imputed.

- **Signal A (owner-directed primary)** is the channel-1 embedding cosine
  between the generated answer and the real answer, pinned mpnet. Read the
  limitation in ``SIGNAL_A_LIMITATION`` before reading any number it produces:
  the cosine needs the real answer, so it is not a confidence a deployed twin
  could state. It is a cross-channel quantity -- does channel 1's graded score,
  mapped to a probability, predict channel 2's binary verdict at the right
  rate?

- **Signal B (secondary, exploratory, non-oracle)** is prompt-perturbation
  agreement: the cosine between the twin's ``twin_redacted`` answer and its own
  ``twin_named`` answer to the same item, both encoded by the same pinned
  model. Two generations of one item, differing only by whether the subject's
  name was shown. It is the closest thing on this record to the registered
  "agreement rate over k samples" -- k = 2 pseudo-samples produced by a prompt
  perturbation rather than by temperature -- and unlike signal A it needs no
  access to the real answer. It is still not the registered estimator.

MAPPING, AND THE HYGIENE ON IT
------------------------------
A cosine is not a probability. Two monotone maps are declared here, neither
inherited from any frozen text:

- ``platt``   -- p = sigmoid(a * x + b), fit by Newton on Platt's smoothed
                 targets. Monotone increasing when a > 0. PRIMARY MAP.
- ``isotonic`` -- pool-adjacent-violators, non-parametric monotone. SECONDARY.

A map fit and evaluated on the same rows reports its own fitting error as
calibration, so the headline never comes from that. Subjects are split in two
by a seeded shuffle (``SPLIT_SEED``); each half's map is fit on the other half
and every item is scored by a map that never saw its subject. That cross-fit
number is the headline. The fit-on-everything number is computed too and is
labelled NAIVE wherever it appears.

BINNING
-------
No binning was ever frozen for H5, so both are reported and neither is
privileged: equal-width (10 fixed bins on [0, 1]) and equal-mass (10 bins of
equal count). Said out loud rather than chosen quietly.

ECE IS GAMEABLE -- READ AUC BESIDE IT
-------------------------------------
A constant predictor that always states the base rate has an ECE near zero and
tells you nothing. Its ECE is computed here as ``constant_baserate_ece`` and
sits beside every headline, as does AUC, which measures whether the signal
separates right from wrong at all. A low ECE with an AUC near 0.5 is a
well-calibrated way of knowing nothing.

Usage::

    .venv/bin/python experiments/h5_calibration.py
    .venv/bin/python experiments/h5_calibration.py --compute-signal-b
    uv run --no-project --with matplotlib --with numpy \\
        python experiments/h5_calibration.py --figure

matplotlib is not a project dependency (see ``pyproject.toml``), so the PNGs
are written only under ``--figure``; the CSVs behind them are always written.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

RESULTS_DIR = _ROOT / "results"
CONFIRM_DIR = RESULTS_DIR / "stage2_confirm"
JUDGE_DIR = CONFIRM_DIR / "judge"
EMBED_DIR = CONFIRM_DIR / "embed"
GEN_ROOT = CONFIRM_DIR / "gen"
OUT_DIR = CONFIRM_DIR / "h5"

BANNER = ("SUBSTITUTED ANALYSIS, EXPLORATORY. Not the registered H5 estimator "
          "(k=10 self-consistency). No pass/fail verdict on registered H5 is "
          "produced by this script, by design.")

SIGNAL_A_LIMITATION = (
    "Signal A is cosine(generated answer, REAL answer). It cannot be computed "
    "without the real answer, so it is not a confidence a deployed twin could "
    "state, and calibrating it does not answer the deployment question H5 was "
    "written to ask. It is a cross-channel agreement measure: channel 1's "
    "graded score, mapped to a probability, against channel 2's binary "
    "verdict.")

#: The registered H5 text, quoted so the report and the code cannot drift.
REGISTERED_H5 = (
    "twin confidence (self-consistency sampling: k = 10 samples, agreement "
    "rate = confidence) is calibrated: ECE ≤ 0.10 on pooled predictions "
    "across Stages 2–3. Reliability diagrams reported regardless.")
REGISTERED_H5_BAR = "ECE ≤ 0.10"

#: Owner-set caps for this piece of work (2026-07-28 ruling, stop point iii).
CAP_API_USD = 0.50
CAP_NODE_HOURS = 0.2

#: Measured on the confirmatory run itself -- see
#: results/stage2_confirm/STAGE2_CONFIRM_REPORT.md section 7 and
#: results/stage2_confirm/gen/gemma/node_hours_accounting.json.
CONFIRM_GEMMA_GENERATIONS = 1911
CONFIRM_GEMMA_NODE_HOURS = 0.6028
CONFIRM_FLASHLITE_GENERATIONS = 1911
CONFIRM_FLASHLITE_USD = 1.676161
CONFIRM_JUDGE_CALLS = 3822
CONFIRM_JUDGE_USD = 4.851384

#: The registered estimator's k.
REGISTERED_K = 10

MODELS = ("Gemma-4-31B-it", "gemini-3.5-flash-lite")
PRIMARY_MODEL = "Gemma-4-31B-it"
GEN_DIR_OF = {"Gemma-4-31B-it": "gemma", "gemini-3.5-flash-lite": "flashlite"}

#: Stage-2 scope. The registered arm is the redacted own-twin; the rest are
#: secondary rows, reported but never the headline.
PRIMARY_ARM = "twin_redacted"
SECONDARY_ARMS = ("twin_named", "zeroinfo_redacted", "zeroinfo_named",
                  "imposter_redacted", "h7_twin_redacted")

#: Seeds. Fixed so a re-run reproduces every number bit for bit.
SPLIT_SEED = 20260728
BOOTSTRAP_SEED = 20260728
BOOTSTRAP_B = 10000

N_BINS = 10

#: Platt target smoothing (Platt 1999): guards against a separating fit.
PLATT_NEWTON_ITERS = 100
PLATT_TOL = 1e-10


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


def rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(_ROOT))
    except ValueError:
        return str(path)


def read_jsonl(path: Path):
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


# ---------------------------------------------------------------------------
# Step 1 -- what the registered estimator would cost
# ---------------------------------------------------------------------------


def registered_projection(n_items: int) -> dict:
    """Price the registered k=10 self-consistency estimator on this cohort.

    Unit costs are the confirmatory run's own measured throughput, not a
    vendor quote: node-hours per generation from the Gemma jobs, dollars per
    judge call from the judge ledger. The projection is deliberately the
    cheapest honest version -- primary model only, one judge call per sample,
    no retries, no canaries -- because a floor that already breaks the cap
    settles the question.
    """
    nh_per_gen = CONFIRM_GEMMA_NODE_HOURS / CONFIRM_GEMMA_GENERATIONS
    usd_per_judge = CONFIRM_JUDGE_USD / CONFIRM_JUDGE_CALLS
    usd_per_flashlite_gen = CONFIRM_FLASHLITE_USD / CONFIRM_FLASHLITE_GENERATIONS

    n_gen = n_items * REGISTERED_K
    primary_nh = n_gen * nh_per_gen
    judge_usd = n_gen * usd_per_judge

    # Full parity with the confirm run (robustness model generated and judged
    # too) -- the number the project would actually have to spend to keep the
    # two-model structure every other Stage 2 result carries.
    parity_usd = judge_usd + n_gen * usd_per_flashlite_gen + judge_usd

    return {
        "cohort_items": n_items,
        "k": REGISTERED_K,
        "generations_needed": n_gen,
        "unit_costs_measured_on_the_confirm_run": {
            "node_hours_per_gemma_generation": nh_per_gen,
            "source_node_hours": CONFIRM_GEMMA_NODE_HOURS,
            "source_generations": CONFIRM_GEMMA_GENERATIONS,
            "usd_per_judge_call": usd_per_judge,
            "source_judge_usd": CONFIRM_JUDGE_USD,
            "source_judge_calls": CONFIRM_JUDGE_CALLS,
            "usd_per_flashlite_generation": usd_per_flashlite_gen,
        },
        "primary_model_only": {
            "node_hours": primary_nh,
            "api_usd": judge_usd,
            "node_hours_cap": CAP_NODE_HOURS,
            "api_cap_usd": CAP_API_USD,
            "node_hours_over_cap_factor": primary_nh / CAP_NODE_HOURS,
            "api_over_cap_factor": judge_usd / CAP_API_USD,
            "breaches_node_hour_cap": primary_nh > CAP_NODE_HOURS,
            "breaches_api_cap": judge_usd > CAP_API_USD,
        },
        "both_models_full_parity": {
            "node_hours": primary_nh,
            "api_usd": parity_usd,
            "api_over_cap_factor": parity_usd / CAP_API_USD,
        },
        "note": ("Temperature is pinned at 0.0 on both generators, so the "
                 "registered estimator cannot reuse a single existing "
                 "generation: k identical greedy samples give agreement 1.0 "
                 "for every item. The projection is therefore for a full "
                 "re-generation, which is also why it cannot be trimmed by "
                 "reusing the confirmatory outputs."),
    }


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


def load_records() -> dict:
    """(model, prompt_sha256) -> merged judge + embed row.

    prompt_sha256 is the join key because it identifies the exact rendered
    prompt, which item_id alone does not (an item appears in several arms and,
    for H7, in several staleness bins).
    """
    judge_files = sorted(glob.glob(str(JUDGE_DIR / "judgements_*_chunk_*.jsonl")))
    embed_files = sorted(glob.glob(str(EMBED_DIR / "cosines_*_chunk_*.jsonl")))
    if not judge_files:
        raise fatal(f"no judge files under {rel(JUDGE_DIR)}")
    if not embed_files:
        raise fatal(f"no embed files under {rel(EMBED_DIR)}")

    judge = {}
    for path in judge_files:
        for r in read_jsonl(Path(path)):
            judge[(r["model"], r["prompt_sha256"])] = r
    embed = {}
    for path in embed_files:
        for r in read_jsonl(Path(path)):
            embed[(r["model"], r["prompt_sha256"])] = r

    missing = set(judge) - set(embed)
    if missing:
        raise fatal(f"{len(missing)} judged rows have no channel-1 cosine; "
                    "refusing to calibrate against a partial join")

    out = {}
    for key, j in judge.items():
        e = embed[key]
        if e["arm"] != j["arm"] or e["item_id"] != j["item_id"]:
            raise fatal(f"join mismatch on {key}: the two channels disagree "
                        "about which row this is")
        out[key] = {
            "model": j["model"],
            "arm": j["arm"],
            "item_id": j["item_id"],
            "canonical_id": j["canonical_id"],
            "prompt_sha256": j["prompt_sha256"],
            "h7_bin": j.get("h7_bin"),
            "item_type": j.get("item_type"),
            "label": j["label"],
            "cosine_to_real": float(e["cosine_to_real"]),
            "answer_words": e.get("answer_words"),
        }
    return out


def load_generation_texts(model: str) -> dict:
    """prompt_sha256 -> generated text, for the perturbation signal."""
    gen_dir = GEN_ROOT / GEN_DIR_OF[model]
    files = sorted(gen_dir.glob("completions_chunk_*.jsonl"))
    if not files:
        raise fatal(f"no completions under {rel(gen_dir)}")
    out = {}
    for path in files:
        for r in read_jsonl(path):
            out[r["prompt_sha256"]] = r.get("text", "")
    return out


# ---------------------------------------------------------------------------
# Signal B -- prompt-perturbation agreement, computed with the pinned model
# ---------------------------------------------------------------------------


PERTURB_CACHE = OUT_DIR / "perturbation_cosines.jsonl"


def compute_signal_b(records: dict) -> None:
    """Encode the twin_redacted / twin_named answer pairs and cache cosines.

    Uses the *same pinned instrument* as channel 1, resolved and asserted by
    the confirmatory embed driver, so this number is on the same scale as the
    cosines already on the record.
    """
    import stage2_confirm_embed as EMB  # noqa: WPS433 - optional heavy import

    pin = EMB.resolve_pinned_model()
    model_st = EMB.load_model(pin, threads=EMB.DEFAULT_THREADS)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for model in MODELS:
        texts = load_generation_texts(model)
        red = {r["item_id"]: r for r in records.values()
               if r["model"] == model and r["arm"] == "twin_redacted"}
        nam = {r["item_id"]: r for r in records.values()
               if r["model"] == model and r["arm"] == "twin_named"}
        shared = sorted(set(red) & set(nam))
        pairs = [(item_id,
                  texts.get(red[item_id]["prompt_sha256"], ""),
                  texts.get(nam[item_id]["prompt_sha256"], ""))
                 for item_id in shared]
        flat = [t for _, a, b in pairs for t in (a, b)]
        vecs = EMB.encode(model_st, flat)
        for i, (item_id, _a, _b) in enumerate(pairs):
            rows.append({
                "model": model,
                "item_id": item_id,
                "canonical_id": red[item_id]["canonical_id"],
                "prompt_sha256_redacted": red[item_id]["prompt_sha256"],
                "prompt_sha256_named": nam[item_id]["prompt_sha256"],
                "perturbation_cosine": EMB.cosine(vecs[2 * i], vecs[2 * i + 1]),
                "embedding_model": pin["name"],
                "embedding_revision": pin["revision"],
            })
        print(f"[signal-b] {model}: {len(pairs)} redacted/named pairs encoded")

    with open(PERTURB_CACHE, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"[signal-b] wrote {rel(PERTURB_CACHE)} ({len(rows)} rows)")


def load_signal_b() -> dict:
    """(model, item_id) -> perturbation cosine, or {} when not computed."""
    if not PERTURB_CACHE.exists():
        return {}
    return {(r["model"], r["item_id"]): float(r["perturbation_cosine"])
            for r in read_jsonl(PERTURB_CACHE)}


# ---------------------------------------------------------------------------
# Monotone maps
# ---------------------------------------------------------------------------


def platt_fit(x: np.ndarray, y: np.ndarray) -> dict:
    """Logistic map p = sigmoid(a*x + b), Newton on Platt's smoothed targets.

    Smoothing (t+ = (n+ + 1)/(n+ + 2), t- = 1/(n- + 2)) is Platt's own guard
    against a separable sample driving |a| to infinity. Declared, not hidden:
    it shrinks the fitted map very slightly toward the middle.
    """
    x = np.asarray(x, dtype="float64")
    y = np.asarray(y, dtype="float64")
    n_pos = float(y.sum())
    n_neg = float(len(y) - n_pos)
    t_pos = (n_pos + 1.0) / (n_pos + 2.0)
    t_neg = 1.0 / (n_neg + 2.0)
    t = np.where(y > 0.5, t_pos, t_neg)

    a, b = 0.0, math.log(max(n_pos, 1.0) / max(n_neg, 1.0))
    for _ in range(PLATT_NEWTON_ITERS):
        z = a * x + b
        p = 1.0 / (1.0 + np.exp(-z))
        w = np.clip(p * (1.0 - p), 1e-12, None)
        r = p - t
        g = np.array([float((r * x).sum()), float(r.sum())])
        h = np.array([[float((w * x * x).sum()), float((w * x).sum())],
                      [float((w * x).sum()), float(w.sum())]])
        h[0, 0] += 1e-12
        h[1, 1] += 1e-12
        try:
            step = np.linalg.solve(h, g)
        except np.linalg.LinAlgError:  # pragma: no cover - degenerate sample
            break
        a -= float(step[0])
        b -= float(step[1])
        if float(np.abs(step).max()) < PLATT_TOL:
            break
    return {"kind": "platt", "a": a, "b": b,
            "monotone": "increasing" if a > 0 else
                        ("decreasing" if a < 0 else "flat")}


def platt_apply(fit: dict, x: np.ndarray) -> np.ndarray:
    z = fit["a"] * np.asarray(x, dtype="float64") + fit["b"]
    return 1.0 / (1.0 + np.exp(-z))


def isotonic_fit(x: np.ndarray, y: np.ndarray) -> dict:
    """Pool-adjacent-violators. Ties in x are averaged before pooling."""
    x = np.asarray(x, dtype="float64")
    y = np.asarray(y, dtype="float64")
    order = np.argsort(x, kind="stable")
    xs, ys = x[order], y[order]

    ux, uy, uw = [], [], []
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[j + 1] == xs[i]:
            j += 1
        ux.append(float(xs[i]))
        uy.append(float(ys[i:j + 1].mean()))
        uw.append(float(j - i + 1))
        i = j + 1

    vals, wts, edges = [], [], []
    for xi, yi, wi in zip(ux, uy, uw):
        vals.append(yi)
        wts.append(wi)
        edges.append(xi)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            w = wts[-2] + wts[-1]
            v = (vals[-2] * wts[-2] + vals[-1] * wts[-1]) / w
            vals[-2:] = [v]
            wts[-2:] = [w]
            edges[-2:] = [edges[-2]]
    return {"kind": "isotonic", "x_edges": edges, "values": vals,
            "monotone": "increasing (by construction)"}


def isotonic_apply(fit: dict, x: np.ndarray) -> np.ndarray:
    edges = np.asarray(fit["x_edges"], dtype="float64")
    vals = np.asarray(fit["values"], dtype="float64")
    idx = np.searchsorted(edges, np.asarray(x, dtype="float64"),
                          side="right") - 1
    idx = np.clip(idx, 0, len(vals) - 1)
    return np.clip(vals[idx], 0.0, 1.0)


MAPS = {
    "platt": (platt_fit, platt_apply),
    "isotonic": (isotonic_fit, isotonic_apply),
}


# ---------------------------------------------------------------------------
# Calibration metrics
# ---------------------------------------------------------------------------


def equal_width_bins(conf: np.ndarray, n_bins: int) -> list[np.ndarray]:
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(conf, edges[1:-1], right=False), 0, n_bins - 1)
    return [np.flatnonzero(idx == b) for b in range(n_bins)]


def equal_mass_bins(conf: np.ndarray, n_bins: int) -> list[np.ndarray]:
    order = np.argsort(conf, kind="stable")
    return [np.asarray(part) for part in np.array_split(order, n_bins)]


def bin_table(conf: np.ndarray, y: np.ndarray, groups: list[np.ndarray],
              scheme: str) -> list[dict]:
    rows, n = [], len(conf)
    for b, members in enumerate(groups):
        if len(members) == 0:
            rows.append({"bin": b, "scheme": scheme, "n": 0, "weight": 0.0,
                         "conf_lo": None, "conf_hi": None,
                         "mean_conf": None, "empirical_rate": None,
                         "gap": None})
            continue
        c, yy = conf[members], y[members]
        rows.append({
            "bin": b, "scheme": scheme, "n": int(len(members)),
            "weight": float(len(members)) / n,
            "conf_lo": float(c.min()), "conf_hi": float(c.max()),
            "mean_conf": float(c.mean()),
            "empirical_rate": float(yy.mean()),
            "gap": float(yy.mean() - c.mean()),
        })
    return rows


def ece_from_rows(rows: list[dict]) -> float:
    return float(sum(r["weight"] * abs(r["gap"])
                     for r in rows if r["n"] > 0))


def mce_from_rows(rows: list[dict]) -> float:
    gaps = [abs(r["gap"]) for r in rows if r["n"] > 0]
    return float(max(gaps)) if gaps else float("nan")


def auc(conf: np.ndarray, y: np.ndarray) -> float:
    pos = conf[y > 0.5]
    neg = conf[y <= 0.5]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    # Mann-Whitney with mid-ranks for ties.
    allv = np.concatenate([pos, neg])
    order = np.argsort(allv, kind="stable")
    sortv = allv[order]
    r = np.empty(len(allv), dtype="float64")
    i = 0
    while i < len(sortv):
        j = i
        while j + 1 < len(sortv) and sortv[j + 1] == sortv[i]:
            j += 1
        r[order[i:j + 1]] = (i + j + 2) / 2.0
        i = j + 1
    ranks = r
    rsum = float(ranks[:len(pos)].sum())
    return (rsum - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg))


def score_block(conf: np.ndarray, y: np.ndarray, subjects: np.ndarray,
                rng_seed: int) -> dict:
    """Every calibration number for one set of (confidence, outcome) pairs."""
    conf = np.asarray(conf, dtype="float64")
    y = np.asarray(y, dtype="float64")
    ew = bin_table(conf, y, equal_width_bins(conf, N_BINS), "equal_width")
    em = bin_table(conf, y, equal_mass_bins(conf, N_BINS), "equal_mass")
    base = float(y.mean())

    const = np.full(len(y), base)
    const_ew = ece_from_rows(bin_table(const, y,
                                       equal_width_bins(const, N_BINS),
                                       "equal_width"))

    out = {
        "n": int(len(y)),
        "n_subjects": int(len(set(subjects.tolist()))),
        "base_rate": base,
        "mean_confidence": float(conf.mean()),
        "ece_equal_width": ece_from_rows(ew),
        "ece_equal_mass": ece_from_rows(em),
        "mce_equal_width": mce_from_rows(ew),
        "mce_equal_mass": mce_from_rows(em),
        "brier": float(np.mean((conf - y) ** 2)),
        "brier_constant_baserate": float(np.mean((base - y) ** 2)),
        "auc": auc(conf, y),
        "constant_baserate_ece_equal_width": const_ew,
        "bins_equal_width": ew,
        "bins_equal_mass": em,
    }
    out.update(bootstrap_ci(conf, y, subjects, rng_seed))
    return out


def bootstrap_ci(conf: np.ndarray, y: np.ndarray, subjects: np.ndarray,
                 seed: int) -> dict:
    """Subject-clustered percentile CI on both ECEs.

    Resampling is over subjects, not items: two items from one subject are not
    independent draws, and the whole cohort is only 88 people.
    """
    uniq = sorted(set(subjects.tolist()))
    idx_of = {s: np.flatnonzero(subjects == s) for s in uniq}
    rng = np.random.default_rng(seed)
    ew_vals, em_vals = [], []
    for _ in range(BOOTSTRAP_B):
        pick = rng.integers(0, len(uniq), size=len(uniq))
        take = np.concatenate([idx_of[uniq[p]] for p in pick])
        c, yy = conf[take], y[take]
        ew_vals.append(ece_from_rows(bin_table(
            c, yy, equal_width_bins(c, N_BINS), "equal_width")))
        em_vals.append(ece_from_rows(bin_table(
            c, yy, equal_mass_bins(c, N_BINS), "equal_mass")))
    return {
        "ece_equal_width_ci95": [float(np.percentile(ew_vals, 2.5)),
                                 float(np.percentile(ew_vals, 97.5))],
        "ece_equal_mass_ci95": [float(np.percentile(em_vals, 2.5)),
                                float(np.percentile(em_vals, 97.5))],
        "bootstrap_B": BOOTSTRAP_B,
        "bootstrap_seed": seed,
        "bootstrap_unit": "subject (clustered)",
    }


# ---------------------------------------------------------------------------
# The split
# ---------------------------------------------------------------------------


def subject_folds(subjects: list[str], seed: int) -> dict:
    """Seeded two-way split of SUBJECTS (never of items)."""
    ordered = sorted(set(subjects))
    rng = random.Random(seed)
    shuffled = list(ordered)
    rng.shuffle(shuffled)
    half = len(shuffled) // 2
    return {"A": set(shuffled[:half]), "B": set(shuffled[half:]),
            "seed": seed, "n_A": half, "n_B": len(shuffled) - half,
            "order_note": "sorted, then Random(seed).shuffle"}


# ---------------------------------------------------------------------------
# One (model, arm, signal) analysis
# ---------------------------------------------------------------------------


def analyse(rows: list[dict], signal_key: str, map_name: str) -> dict:
    """Cross-fit held-out calibration plus the naive fit-on-everything one."""
    fit_fn, apply_fn = MAPS[map_name]
    x = np.array([r[signal_key] for r in rows], dtype="float64")
    y = np.array([1.0 if r["label"] == "SAME" else 0.0 for r in rows])
    subj = np.array([r["canonical_id"] for r in rows])

    folds = subject_folds(subj.tolist(), SPLIT_SEED)
    in_a = np.array([s in folds["A"] for s in subj])
    in_b = ~in_a
    if in_a.sum() == 0 or in_b.sum() == 0:
        raise fatal(f"a fold is empty for {signal_key}/{map_name}")

    fit_on_a = fit_fn(x[in_a], y[in_a])
    fit_on_b = fit_fn(x[in_b], y[in_b])

    # Cross-fit: each item scored by the map that never saw its subject.
    conf = np.empty(len(x))
    conf[in_b] = apply_fn(fit_on_a, x[in_b])
    conf[in_a] = apply_fn(fit_on_b, x[in_a])

    fit_all = fit_fn(x, y)
    conf_naive = apply_fn(fit_all, x)

    return {
        "map": map_name,
        "signal": signal_key,
        "split": {k: v for k, v in folds.items() if k not in ("A", "B")},
        "fit_on_A": fit_summary(fit_on_a),
        "fit_on_B": fit_summary(fit_on_b),
        "fit_on_all_NAIVE": fit_summary(fit_all),
        "held_out_crossfit": score_block(conf, y, subj, BOOTSTRAP_SEED),
        "held_out_fold_B_only": score_block(conf[in_b], y[in_b], subj[in_b],
                                           BOOTSTRAP_SEED + 1),
        "held_out_fold_A_only": score_block(conf[in_a], y[in_a], subj[in_a],
                                           BOOTSTRAP_SEED + 2),
        "naive_full_sample": score_block(conf_naive, y, subj,
                                         BOOTSTRAP_SEED + 3),
        "signal_mean": float(x.mean()),
        "signal_min": float(x.min()),
        "signal_max": float(x.max()),
    }


def fit_summary(fit: dict) -> dict:
    if fit["kind"] == "platt":
        return {"kind": "platt", "a": fit["a"], "b": fit["b"],
                "monotone": fit["monotone"]}
    return {"kind": "isotonic", "n_blocks": len(fit["values"]),
            "monotone": fit["monotone"],
            "value_range": [min(fit["values"]), max(fit["values"])]}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def build(records: dict, signal_b: dict) -> dict:
    by = {}
    for r in records.values():
        by.setdefault((r["model"], r["arm"]), []).append(r)
    for key in by:
        by[key].sort(key=lambda r: r["prompt_sha256"])

    n_primary = len(by[(PRIMARY_MODEL, PRIMARY_ARM)])
    primary_subjects = [r["canonical_id"]
                        for r in by[(PRIMARY_MODEL, PRIMARY_ARM)]]
    primary_folds = subject_folds(primary_subjects, SPLIT_SEED)
    out = {
        "banner": BANNER,
        "registered_h5_text": REGISTERED_H5,
        "registered_h5_bar": REGISTERED_H5_BAR,
        "rescope": ("PREREGISTRATION_AMENDMENT_2.md B9.b -- H5 re-scoped to "
                    "Stage 2 predictions after Stage 3 was demoted."),
        "verdict_on_registered_h5": ("NONE. The substituted estimator is a "
                                     "different quantity from the registered "
                                     "one; no pass/fail is claimed."),
        "signal_a_limitation": SIGNAL_A_LIMITATION,
        "degenerate_registered_estimator": {
            "generation_temperature": 0.0,
            "both_models_pinned": True,
            "consequence": ("greedy decoding returns one string, so k=10 "
                            "self-consistency samples are identical and the "
                            "agreement rate is 1.0 for every item"),
        },
        "registered_projection": registered_projection(n_primary),
        "split_seed": SPLIT_SEED,
        "split": {
            "unit": "subject (canonical_id), never item",
            "seed": SPLIT_SEED,
            "procedure": "sorted(subject_ids), then Random(seed).shuffle, "
                         "first half = fold A",
            "n_subjects": len(set(primary_subjects)),
            "fold_A_subjects": sorted(primary_folds["A"]),
            "fold_B_subjects": sorted(primary_folds["B"]),
        },
        "bootstrap_seed": BOOTSTRAP_SEED,
        "n_bins": N_BINS,
        "binning_note": ("No binning was frozen for H5. Equal-width and "
                         "equal-mass are both reported; neither is primary."),
        "unclear_exclusions": {},
        "results": {},
        "cost": {"api_usd": 0.0, "node_hours": 0.0,
                 "note": "CPU only, no API call, no GPU."},
    }

    for model in MODELS:
        for arm in (PRIMARY_ARM,) + SECONDARY_ARMS:
            rows = by.get((model, arm), [])
            if not rows:
                continue
            usable = [r for r in rows if r["label"] in ("SAME", "DIFFERENT")]
            unclear = [r for r in rows if r["label"] == "UNCLEAR"]
            other = [r for r in rows
                     if r["label"] not in ("SAME", "DIFFERENT", "UNCLEAR")]
            out["unclear_exclusions"][f"{model}|{arm}"] = {
                "rows": len(rows), "usable": len(usable),
                "unclear_excluded": len(unclear),
                "unclear_rate": len(unclear) / len(rows) if rows else None,
                "other_labels_excluded": len(other),
                "rule": ("Addendum A instrument parameter 6 (adopting "
                         "Amendment 3 C2.3): UNCLEAR leaves the denominator."),
            }
            if len(usable) < 30 or len({r["label"] for r in usable}) < 2:
                out["results"][f"{model}|{arm}"] = {
                    "skipped": "fewer than 30 usable rows, or one class only"}
                continue

            block = {"n_usable": len(usable),
                     "role": ("PRIMARY" if arm == PRIMARY_ARM else
                              "secondary")}
            for map_name in MAPS:
                block[f"signal_a_{map_name}"] = analyse(
                    usable, "cosine_to_real", map_name)

            if signal_b and arm in ("twin_redacted", "twin_named"):
                with_b = []
                for r in usable:
                    v = signal_b.get((model, r["item_id"]))
                    if v is not None:
                        rr = dict(r)
                        rr["perturbation_cosine"] = v
                        with_b.append(rr)
                if len(with_b) >= 30:
                    block["signal_b_rows"] = len(with_b)
                    for map_name in MAPS:
                        block[f"signal_b_{map_name}"] = analyse(
                            with_b, "perturbation_cosine", map_name)
            out["results"][f"{model}|{arm}"] = block
    return out


def write_csv(numbers: dict) -> Path:
    path = OUT_DIR / "reliability_bins.csv"
    cols = ["model", "arm", "signal", "map", "fit", "scheme", "bin", "n",
            "weight", "conf_lo", "conf_hi", "mean_conf", "empirical_rate",
            "gap"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for key, block in sorted(numbers["results"].items()):
            if "skipped" in block:
                continue
            model, arm = key.split("|")
            for sub, res in sorted(block.items()):
                if not isinstance(res, dict) or "held_out_crossfit" not in res:
                    continue
                signal = "A_cosine_to_real" if sub.startswith("signal_a") \
                    else "B_perturbation_cosine"
                for fit_name in ("held_out_crossfit", "naive_full_sample"):
                    for scheme in ("bins_equal_width", "bins_equal_mass"):
                        for row in res[fit_name][scheme]:
                            if row["n"] == 0:
                                continue
                            w.writerow({"model": model, "arm": arm,
                                        "signal": signal, "map": res["map"],
                                        "fit": fit_name, **row})
    return path


def write_summary_csv(numbers: dict) -> Path:
    path = OUT_DIR / "calibration_summary.csv"
    cols = ["model", "arm", "role", "signal", "map", "fit", "n", "n_subjects",
            "base_rate", "mean_confidence", "ece_equal_width",
            "ece_equal_width_lo", "ece_equal_width_hi", "ece_equal_mass",
            "ece_equal_mass_lo", "ece_equal_mass_hi", "brier",
            "brier_constant_baserate", "auc", "constant_baserate_ece"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for key, block in sorted(numbers["results"].items()):
            if "skipped" in block:
                continue
            model, arm = key.split("|")
            for sub, res in sorted(block.items()):
                if not isinstance(res, dict) or "held_out_crossfit" not in res:
                    continue
                signal = "A_cosine_to_real" if sub.startswith("signal_a") \
                    else "B_perturbation_cosine"
                for fit_name in ("held_out_crossfit", "naive_full_sample"):
                    s = res[fit_name]
                    w.writerow({
                        "model": model, "arm": arm, "role": block["role"],
                        "signal": signal, "map": res["map"], "fit": fit_name,
                        "n": s["n"], "n_subjects": s["n_subjects"],
                        "base_rate": round(s["base_rate"], 6),
                        "mean_confidence": round(s["mean_confidence"], 6),
                        "ece_equal_width": round(s["ece_equal_width"], 6),
                        "ece_equal_width_lo":
                            round(s["ece_equal_width_ci95"][0], 6),
                        "ece_equal_width_hi":
                            round(s["ece_equal_width_ci95"][1], 6),
                        "ece_equal_mass": round(s["ece_equal_mass"], 6),
                        "ece_equal_mass_lo":
                            round(s["ece_equal_mass_ci95"][0], 6),
                        "ece_equal_mass_hi":
                            round(s["ece_equal_mass_ci95"][1], 6),
                        "brier": round(s["brier"], 6),
                        "brier_constant_baserate":
                            round(s["brier_constant_baserate"], 6),
                        "auc": round(s["auc"], 6),
                        "constant_baserate_ece":
                            round(s["constant_baserate_ece_equal_width"], 6),
                    })
    return path


def write_figures(numbers: dict) -> list[Path]:
    try:
        import matplotlib
    except ImportError:
        raise fatal(
            "matplotlib is not a project dependency (see pyproject.toml). "
            "Run the figure step with:\n"
            "  uv run --no-project --with matplotlib --with numpy "
            "python experiments/h5_calibration.py --figure")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    written = []
    for signal_tag, sub_key in (("A_cosine_to_real", "signal_a_platt"),
                                ("B_perturbation_cosine", "signal_b_platt")):
        panels = []
        for model in MODELS:
            block = numbers["results"].get(f"{model}|{PRIMARY_ARM}", {})
            if sub_key in block:
                panels.append((model, block[sub_key]))
        if not panels:
            continue
        fig, axes = plt.subplots(len(panels), 2,
                                 figsize=(9.5, 4.2 * len(panels)),
                                 squeeze=False)
        for row, (model, res) in enumerate(panels):
            for col, fit_name in enumerate(("held_out_crossfit",
                                            "naive_full_sample")):
                ax = axes[row][col]
                s = res[fit_name]
                ax.plot([0, 1], [0, 1], ls="--", lw=1, color="0.6",
                        label="perfect calibration")
                for scheme, marker, lbl in (("bins_equal_width", "o",
                                             "equal-width bins"),
                                            ("bins_equal_mass", "s",
                                             "equal-mass bins")):
                    pts = [(b["mean_conf"], b["empirical_rate"], b["n"])
                           for b in s[scheme] if b["n"] > 0]
                    if not pts:
                        continue
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    sz = [12 + 90 * (p[2] / max(1, s["n"])) for p in pts]
                    ax.scatter(xs, ys, s=sz, marker=marker, alpha=0.8,
                               label=lbl)
                    ax.plot(xs, ys, lw=1, alpha=0.5)
                ax.axhline(s["base_rate"], color="0.4", lw=0.8, ls=":",
                           label=f"base rate {s['base_rate']:.3f}")
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.set_xlabel("mapped confidence")
                ax.set_ylabel("observed stance-match rate")
                title = ("held out (cross-fit)" if col == 0
                         else "NAIVE (fit = eval)")
                ax.set_title(
                    f"{model} - {title}\n"
                    f"ECE(equal-width) {s['ece_equal_width']:.4f} | "
                    f"ECE(equal-mass) {s['ece_equal_mass']:.4f} | "
                    f"AUC {s['auc']:.3f} | n={s['n']}", fontsize=8)
                ax.legend(fontsize=6, loc="upper left")
        fig.suptitle(
            f"Reliability - substituted H5 analysis, signal {signal_tag}, "
            f"Platt map, arm {PRIMARY_ARM}\n"
            "EXPLORATORY. Not the registered k=10 self-consistency estimator; "
            "no verdict on registered H5.", fontsize=9)
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        path = OUT_DIR / f"reliability_signal_{signal_tag}.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        written.append(path)
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--compute-signal-b", action="store_true",
                    help="encode the redacted/named answer pairs with the "
                         "pinned model and cache their cosines (CPU, $0)")
    ap.add_argument("--figure", action="store_true",
                    help="also write the reliability PNGs (needs matplotlib)")
    args = ap.parse_args()

    print(BANNER)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = load_records()
    print(f"[load] {len(records)} joined judge+embed rows")

    if args.compute_signal_b:
        compute_signal_b(records)

    signal_b = load_signal_b()
    print(f"[load] signal B rows: {len(signal_b)}")

    numbers = build(records, signal_b)
    out_json = OUT_DIR / "h5_numbers.json"
    with open(out_json, "w") as fh:
        json.dump(numbers, fh, indent=1, sort_keys=False)
    print(f"[write] {rel(out_json)}")
    print(f"[write] {rel(write_csv(numbers))}")
    print(f"[write] {rel(write_summary_csv(numbers))}")
    if args.figure:
        for p in write_figures(numbers):
            print(f"[write] {rel(p)}")

    proj = numbers["registered_projection"]["primary_model_only"]
    print(f"[projection] registered estimator on "
          f"{numbers['registered_projection']['cohort_items']} items x k=10: "
          f"{proj['node_hours']:.4f} node-hours (cap {CAP_NODE_HOURS}), "
          f"${proj['api_usd']:.4f} API (cap ${CAP_API_USD})")
    for key, block in numbers["results"].items():
        if "signal_a_platt" in block:
            s = block["signal_a_platt"]["held_out_crossfit"]
            print(f"[held-out] {key}: ECE(ew) {s['ece_equal_width']:.4f} "
                  f"ECE(em) {s['ece_equal_mass']:.4f} AUC {s['auc']:.3f} "
                  f"n={s['n']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
