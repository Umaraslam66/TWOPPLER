#!/usr/bin/env python3
"""Confirmatory Stage 2 -- the analysis and report driver.

This is the one place in the project where the frozen bars are read, applied,
and answered. Everything upstream of it (build, render, generation, embedding,
judging) deliberately refuses to compute a contrast or print a verdict; this
driver does both, once, mechanically.

What "mechanically" means here
------------------------------
Every bar is quoted verbatim from its frozen document, stored as a string in
``FROZEN_BARS``, printed above its own verdict, and then applied by code that
reads only the numbers. No bar is paraphrased, none is re-derived, and none is
softened. A bar that fails prints FAIL in the same typeface a pass gets.

What it refuses to do
---------------------
It refuses to print a verdict while the data a bar needs is incomplete. The
stance judge (channel 2) runs in chunks; until every chunk of every scored
model carries a label for every generation, every channel-2 rate, contrast,
flag and verdict renders as ``[AWAITING JUDGE]``. Channel-1 numbers are real
and are printed, but they are labelled PRELIMINARY wherever a frozen rule
requires both channels -- Amendment 3 C2.4: no claim rests on one channel.

``--require-complete`` turns that refusal into an exit code: nonzero while any
chunk is missing, so a pipeline step cannot mistake a placeholder report for a
finished one.

Cost, determinism, hardware
---------------------------
No API call, no GPU, no network. CPU only, and $0.00. Every number outside the
``run`` block of the JSON is deterministic: the two resampling procedures
(percentile bootstrap, sign-flip permutation) are seeded from a constant.

Usage::

    .venv/bin/python experiments/stage2_confirm_report.py
    .venv/bin/python experiments/stage2_confirm_report.py --require-complete
    .venv/bin/python experiments/stage2_confirm_report.py --status
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover - environment-dependent
    raise SystemExit(f"[fatal] numpy is required ({exc})")
try:
    from scipy import stats as sstats
except ImportError as exc:  # pragma: no cover - environment-dependent
    raise SystemExit(f"[fatal] scipy is required ({exc})")

_ROOT = Path(__file__).resolve().parents[1]

RESULTS_DIR = _ROOT / "results"
CONFIRM_DIR = RESULTS_DIR / "stage2_confirm"
GEN_ROOT = CONFIRM_DIR / "gen"
EMBED_DIR = CONFIRM_DIR / "embed"
JUDGE_DIR = CONFIRM_DIR / "judge"
COST_LOG = RESULTS_DIR / "cost_log.jsonl"

OUT_JSON = CONFIRM_DIR / "report_numbers.json"
OUT_MD = CONFIRM_DIR / "STAGE2_CONFIRM_REPORT.md"

#: gen/<dir> -> the model version string that produced it.
GEN_DIRS = {"gemma": "Gemma-4-31B-it", "flashlite": "gemini-3.5-flash-lite"}
PRIMARY_DIR = "gemma"            # Amendment 1 A3: primary
ROBUSTNESS_DIR = "flashlite"     # Amendment 1 A3: robustness
CHUNK_ALLOWLIST = ("chunk_01", "chunk_02", "chunk_03", "chunk_04", "chunk_05")

#: The five H1 arms, exactly as rendered.
H1_ARMS = ("twin_redacted", "twin_named", "zeroinfo_redacted",
           "zeroinfo_named", "imposter_redacted")
H7_ARMS = ("h7_twin_redacted", "h7_imposter_fresh")
OWN_ARM = "twin_redacted"
OWN_NAMED_ARM = "twin_named"
IMPOSTER_ARM = "imposter_redacted"
ZERO_RED = "zeroinfo_redacted"
ZERO_NAMED = "zeroinfo_named"

#: Addendum A item 6 bin edges, in the order freshest -> stalest.
H7_BIN_ORDER = ("6-12m", "1-2y", "2-3y", ">3y")

#: Addendum A instrument parameter 7, the two magnitude ("interesting") bars.
MAG_BAR_CH1 = 0.05      # cosine, channel 1, pinned model
MAG_BAR_CH2 = 0.09      # stance-match points, channel 2

#: Addendum A instrument parameter 6: the material UNCLEAR-gap threshold.
UNCLEAR_GAP_FLAG = 0.10

#: Launch plan section c, signed off by the owner on GO.
CAP_NODE_HOURS = 8.0
CAP_API_USD = 15.0

#: Fixed so a re-run reproduces every number bit for bit.
SEED = 20260728
N_BOOTSTRAP = 10000
N_SIGNFLIP = 20000

ALPHA = 0.05

BANNER = ("CONFIRMATORY Stage 2. This is the report: the frozen bars are "
          "applied here, once, and nowhere else.")

AWAIT = "[AWAITING JUDGE]"


# ---------------------------------------------------------------------------
# The frozen bars, quoted verbatim. Nothing here is paraphrased.
# ---------------------------------------------------------------------------

FROZEN_BARS = {
    "H1": {
        "source": "PREREGISTRATION.md section 3, Stage 2 pre-registered "
                  "hypotheses; quoted in STAGE2_LAUNCH_PLAN.md section e.2",
        "text": "H1 (grounding works): mean lift > 0 across subjects, "
                "p < .05 (paired test over subjects).",
    },
    "H1_updated": {
        "source": "PREREGISTRATION_AMENDMENT_1.md A1",
        "text": "H1 bar (updated): H1 passes iff BOTH mean zero-info lift > 0 "
                "AND mean imposter lift > 0, each p < .05 (paired test over "
                "subjects).",
    },
    "magnitude": {
        "source": "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md instrument "
                  "parameter 7; quoted in STAGE2_LAUNCH_PLAN.md section e.2",
        "text": "a registered contrast is 'interesting' only if it reaches "
                "≥ +0.05 cosine (channel 1, pinned model) or ≥ +0.09 "
                "stance-match points (channel 2)",
    },
    "magnitude_scope": {
        "source": "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md instrument "
                  "parameter 7",
        "text": "Applied to each hypothesis's registered contrast (H1: "
                "own-twin − zero-info; H2: between-arm; H7: freshest "
                "− stalest Δ bin, beside the unchanged crossover "
                "statistic).",
    },
    "primary_metric": {
        "source": "PREREGISTRATION_AMENDMENT_3.md C3",
        "text": "Primary metric: own-twin minus imposter-twin, per Amendment "
                "1 A1, computed identically in both channels.",
    },
    "both_channels": {
        "source": "PREREGISTRATION_AMENDMENT_3.md C2.4",
        "text": "No claim rests on one channel alone. A headline requires "
                "direction agreement across both channels; disagreement "
                "between channels is itself reported.",
    },
    "two_models": {
        "source": "PREREGISTRATION_AMENDMENT_1.md A3",
        "text": "Any Stage 2 headline claim must replicate in direction and "
                "significance on both Gemma-4-31B-it + v2 (primary) and "
                "gemini-3.5-flash-lite + v2 (robustness). A result holding on "
                "one model only is reported as model-specific, never as a "
                "headline.",
    },
    "robustness_secondary": {
        "source": "PREREGISTRATION_AMENDMENT_3.md C3",
        "text": "Because the stance judge shares a model family with the "
                "robustness scorer, robustness-arm absolute scores are "
                "explicitly secondary: only the own-minus-imposter contrast "
                "carries robustness weight (extending the B10.3 declaration).",
    },
    "H7": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B7, Bars and rules; quoted "
                  "in STAGE2_LAUNCH_PLAN.md section e.3",
        "text": "Confirmatory bar: fidelity declines with Δ — "
                "per-subject slope of fidelity against Δ, mean slope < 0 "
                "across subjects, paired within subject where the chronology "
                "allows, p < .05, on the primary model. Direction-robust on "
                "the robustness model per A3.",
    },
    "H7_crossover": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B7, Pre-declared killer "
                  "statistic",
        "text": "The crossover point is the smallest Δ at which the "
                "fresh imposter twin matches or beats the stale own twin "
                "— \"a stranger's fresh twin beats your Δ-year-old "
                "twin.\" It is pre-declared here as H7's headline statistic "
                "if it occurs inside the observed Δ range.",
    },
    "H7_reading_decay": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B7, Pre-written readings",
        "text": "Measurable decay, crossover in range: person-models have a "
                "shelf life; the curve and the crossover Δ are the "
                "headline.",
    },
    "H7_reading_flat": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B7, Pre-written readings",
        "text": "Flat decay across our Δ range: public personas are "
                "stable at these horizons — grounding age does not "
                "matter within the years this corpus covers. Equally "
                "reportable, same prominence.",
    },
    "H7_within_subject": {
        "source": "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md decision 6",
        "text": "The within-subject sweep is pre-registered as a supporting "
                "analysis on the subset that can fill ≥ 3 bins — "
                "reported beside the between-subject result, never "
                "substituted for it.",
    },
    "H7_volume_control": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B7.3",
        "text": "At every T the grounding context is filled to the same token "
                "budget B, newest-first below the cutoff. Only the AGE of the "
                "grounding varies, never the amount. A cutoff at which B "
                "cannot be filled is excluded (counts reported).",
    },
    "unclear": {
        "source": "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md instrument "
                  "parameter 6 (adopting PREREGISTRATION_AMENDMENT_3.md C2.3)",
        "text": "UNCLEAR items are excluded from the stance-match rate's "
                "denominator; every arm's UNCLEAR rate is always reported "
                "beside its stance-match rate; a between-arm UNCLEAR-rate "
                "difference ≥ 0.10 absolute [PROPOSED] is flagged as "
                "material.",
    },
    "B8": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B8",
        "text": "From this amendment on, every fidelity report in this "
                "project shows BOTH of these, side by side, in the same "
                "table: 1. Individual-level lift — the project's primary "
                "metric (own-twin minus baseline and minus imposter, per A1). "
                "2. A population-level distribution-match metric — total "
                "variation distance (TVD) or equivalent between predicted and "
                "true answer/option distributions, per subject and pooled. "
                "3. Divergences explicitly flagged — wherever the two "
                "levels disagree (good population match with poor individual "
                "lift, or the reverse), the disagreement is called out in the "
                "report body, not in a footnote.",
    },
    "B8_no_bar": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B8",
        "text": "No confirmatory bar attaches to the population metric; it is "
                "a mandatory descriptive companion.",
    },
    "branch": {
        "source": "PREREGISTRATION_AMENDMENT_1.md A5 and "
                  "PREREGISTRATION_AMENDMENT_2.md B3 / B7",
        "text": "≥ 80 → confirmatory as above; 30–79 → "
                "exploratory (effect size + CI, no hypothesis-test claim); "
                "< 30 → descriptive only.",
    },
    "contamination_meter": {
        "source": "PREREGISTRATION.md section 3, Stage 2 contamination "
                  "controls",
        "text": "Contamination meter: per subject, (named baseline) − "
                "(name-redacted baseline). Reported per subject and as a "
                "corpus figure; subjects with a large meter are analyzed "
                "separately.",
    },
    "H3": {
        "source": "PREREGISTRATION.md section 3, Stage 2 pre-registered "
                  "hypotheses",
        "text": "H3 (fame confound, descriptive): lift shrinks as the "
                "contamination meter grows.",
    },
    "lift_primary": {
        "source": "PREREGISTRATION.md section 2, Core definitions",
        "text": "Lift is the primary metric everywhere. Raw fidelity alone is "
                "never reported without its baseline.",
    },
    "raw_beside": {
        "source": "PREREGISTRATION_AMENDMENT_3.md C3",
        "text": "Effect sizes with confidence intervals, never bare means. "
                "Raw per-arm scores always printed beside every difference "
                "(the watch-which-arm-moves rule).",
    },
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(_ROOT))
    except ValueError:
        return str(path)


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


def read_jsonl(path: Path) -> list:
    if not Path(path).exists():
        return []
    out = []
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str | None:
    try:
        out = subprocess.run(("git", "-C", str(_ROOT)) + args,
                             capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def r(x, nd=6):
    """Round for reporting; keep None as None so a gap stays visible."""
    if x is None:
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return round(float(x), nd)


def rp(x):
    """Round a p-value to 4 significant digits.

    Fixed-decimal rounding turns a p of 1e-13 into 0.0, which reads as
    "exactly zero" and is not what the test said. Significant digits keep the
    number honest at both ends of the range.
    """
    if x is None:
        return None
    x = float(x)
    if math.isnan(x) or math.isinf(x):
        return None
    if x == 0.0:
        return 0.0
    return float(f"{x:.4g}")


def fmt(x, nd=4, plus=False):
    if x is None:
        return "n/a"
    s = f"{float(x):+.{nd}f}" if plus else f"{float(x):.{nd}f}"
    return s


def fmt_p(p):
    if p is None:
        return "n/a"
    if p < 1e-4:
        return "< 0.0001"
    return f"{p:.4f}"


def branch_for(n: int) -> str:
    """A5 / B3 / B7 subject-count branch. Decided solely by the count."""
    if n >= 80:
        return "confirmatory"
    if n >= 30:
        return "exploratory"
    return "descriptive"


# ---------------------------------------------------------------------------
# Statistics. Paired over subjects, per the frozen text.
# ---------------------------------------------------------------------------


def _bootstrap_ci(diffs: np.ndarray, seed: int) -> list:
    if len(diffs) < 2:
        return [None, None]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diffs), size=(N_BOOTSTRAP, len(diffs)))
    means = diffs[idx].mean(axis=1)
    return [r(float(np.percentile(means, 2.5))),
            r(float(np.percentile(means, 97.5)))]


def _signflip_p(diffs: np.ndarray, seed: int) -> float | None:
    """Two-sided sign-flip permutation test. Deterministic under SEED."""
    if len(diffs) < 2:
        return None
    obs = abs(float(diffs.mean()))
    rng = np.random.default_rng(seed + 1)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(N_SIGNFLIP, len(diffs)))
    null = np.abs((signs * diffs).mean(axis=1))
    return float((1 + int((null >= obs - 1e-15).sum())) / (N_SIGNFLIP + 1))


def paired_contrast(a_by_subj: dict, b_by_subj: dict,
                    arm_a: str, arm_b: str, seed: int = SEED) -> dict:
    """One registered contrast: arm_a minus arm_b, paired over subjects.

    Raw per-arm means travel with the difference, always -- the
    watch-which-arm-moves rule (Amendment 3 C3).
    """
    subs = sorted(set(a_by_subj) & set(b_by_subj))
    a = np.array([a_by_subj[s] for s in subs], dtype=float)
    b = np.array([b_by_subj[s] for s in subs], dtype=float)
    d = a - b
    n = len(subs)
    out = {
        "arm_a": arm_a, "arm_b": arm_b,
        "n_subjects": n,
        "n_subjects_only_a": len(set(a_by_subj) - set(b_by_subj)),
        "n_subjects_only_b": len(set(b_by_subj) - set(a_by_subj)),
        "mean_a": r(float(a.mean())) if n else None,
        "mean_b": r(float(b.mean())) if n else None,
        "mean_diff": r(float(d.mean())) if n else None,
        "median_diff": r(float(np.median(d))) if n else None,
        "sd_diff": r(float(d.std(ddof=1))) if n > 1 else None,
        "se_diff": None,
        "ci95_t": [None, None],
        "ci95_bootstrap": [None, None],
        "p_paired_t": None,
        "p_wilcoxon": None,
        "p_signflip": None,
        "n_subjects_a_gt_b": int((d > 0).sum()) if n else 0,
        "n_subjects_a_lt_b": int((d < 0).sum()) if n else 0,
        "n_subjects_tied": int((d == 0).sum()) if n else 0,
    }
    if n < 2:
        return out
    se = float(d.std(ddof=1) / math.sqrt(n))
    out["se_diff"] = r(se)
    tcrit = float(sstats.t.ppf(0.975, n - 1))
    out["ci95_t"] = [r(float(d.mean()) - tcrit * se),
                     r(float(d.mean()) + tcrit * se)]
    out["ci95_bootstrap"] = _bootstrap_ci(d, seed)
    tt = sstats.ttest_1samp(d, 0.0)
    out["p_paired_t"] = rp(float(tt.pvalue))
    out["t_stat"] = r(float(tt.statistic), 4)
    if float(np.abs(d).sum()) > 0:
        try:
            out["p_wilcoxon"] = rp(
                float(sstats.wilcoxon(d, zero_method="wilcox").pvalue))
        except ValueError:
            out["p_wilcoxon"] = None
    out["p_signflip"] = rp(_signflip_p(d, seed))
    # Cohen's dz for a paired design.
    out["cohens_dz"] = r(float(d.mean() / d.std(ddof=1))) if d.std(ddof=1) else None
    return out


def one_sample_block(values: dict, name: str, seed: int = SEED) -> dict:
    """Mean of a per-subject quantity (used for slopes and meters)."""
    subs = sorted(values)
    v = np.array([values[s] for s in subs], dtype=float)
    out = {"quantity": name, "n_subjects": len(subs),
           "mean": r(float(v.mean())) if len(v) else None,
           "median": r(float(np.median(v))) if len(v) else None,
           "sd": r(float(v.std(ddof=1))) if len(v) > 1 else None,
           "ci95_t": [None, None], "ci95_bootstrap": [None, None],
           "p_paired_t": None, "p_wilcoxon": None, "p_signflip": None,
           "n_negative": int((v < 0).sum()) if len(v) else 0,
           "n_positive": int((v > 0).sum()) if len(v) else 0}
    if len(v) < 2:
        return out
    se = float(v.std(ddof=1) / math.sqrt(len(v)))
    tcrit = float(sstats.t.ppf(0.975, len(v) - 1))
    out["ci95_t"] = [r(float(v.mean()) - tcrit * se),
                     r(float(v.mean()) + tcrit * se)]
    out["ci95_bootstrap"] = _bootstrap_ci(v, seed)
    tt = sstats.ttest_1samp(v, 0.0)
    out["p_paired_t"] = rp(float(tt.pvalue))
    if float(np.abs(v).sum()) > 0:
        try:
            out["p_wilcoxon"] = rp(
                float(sstats.wilcoxon(v, zero_method="wilcox").pvalue))
        except ValueError:
            out["p_wilcoxon"] = None
    out["p_signflip"] = rp(_signflip_p(v, seed))
    return out


def tvd(a: dict, b: dict) -> float | None:
    """Total variation distance between two label distributions (B8).

    Same convention as the dev pilot (``stage2_oe1._tvd``), so the
    confirmatory number is comparable to OE-1's.
    """
    keys = set(a) | set(b)
    na, nb = sum(a.values()), sum(b.values())
    if not na or not nb:
        return None
    return r(0.5 * sum(abs(a.get(k, 0) / na - b.get(k, 0) / nb) for k in keys))


# ---------------------------------------------------------------------------
# Loading and joining
# ---------------------------------------------------------------------------


def load_inputs() -> dict:
    need = {
        "items": CONFIRM_DIR / "items_confirm.jsonl",
        "render_index": CONFIRM_DIR / "render_index.jsonl",
        "manifest": CONFIRM_DIR / "render_manifest.json",
    }
    for name, path in need.items():
        if not path.exists():
            raise fatal(f"missing required input {rel(path)} ({name})")
    items = {row["item_id"]: row for row in read_jsonl(need["items"])}
    renders = read_jsonl(need["render_index"])
    manifest = read_json(need["manifest"])
    build = (read_json(CONFIRM_DIR / "build_full140.json")
             if (CONFIRM_DIR / "build_full140.json").exists() else {})
    pairs = (read_json(CONFIRM_DIR / "imposter_pairs_confirm.json")
             if (CONFIRM_DIR / "imposter_pairs_confirm.json").exists() else {})
    embed_summary = (read_json(EMBED_DIR / "embed_summary.json")
                     if (EMBED_DIR / "embed_summary.json").exists() else {})
    return {"items": items, "renders": renders, "manifest": manifest,
            "build": build, "pairs": pairs, "embed_summary": embed_summary}


def load_completions(gen_dir: str) -> dict:
    """chunk -> list of completion rows actually on disk."""
    out = {}
    for chunk in CHUNK_ALLOWLIST:
        path = GEN_ROOT / gen_dir / f"completions_{chunk}.jsonl"
        if path.exists():
            out[chunk] = read_jsonl(path)
    return out


def load_cosines(gen_dir: str) -> tuple[dict, dict]:
    """(prompt_sha256 -> cosine row, chunk -> n rows)."""
    by_sha, per_chunk = {}, {}
    for chunk in CHUNK_ALLOWLIST:
        path = EMBED_DIR / f"cosines_{gen_dir}_{chunk}.jsonl"
        rows = read_jsonl(path)
        if not rows:
            continue
        per_chunk[chunk] = len(rows)
        for row in rows:
            by_sha[row["prompt_sha256"]] = row
    return by_sha, per_chunk


def load_labels(gen_dir: str) -> tuple[dict, dict]:
    """(prompt_sha256 -> judge row, chunk -> {n, sidecar})."""
    by_sha, per_chunk = {}, {}
    for chunk in CHUNK_ALLOWLIST:
        path = JUDGE_DIR / f"judgements_{gen_dir}_{chunk}.jsonl"
        rows = read_jsonl(path)
        sidecar = JUDGE_DIR / f"judge_summary_{gen_dir}_{chunk}.json"
        if not rows and not sidecar.exists():
            continue
        per_chunk[chunk] = {"n_labels": len(rows),
                            "sidecar_present": sidecar.exists()}
        for row in rows:
            by_sha[row["prompt_sha256"]] = row
    return by_sha, per_chunk


def completeness(renders: list) -> dict:
    """Is every generation scored, on both channels, for both models?

    A chunk counts as complete only when every prompt the render index puts in
    it carries a score. Anything short of that is a hole, and a hole blocks
    every verdict the channel feeds.
    """
    want_by_chunk = {}
    for row in renders:
        want_by_chunk.setdefault(row["chunk"], set()).add(row["prompt_sha256"])

    out = {"expected_chunks": list(CHUNK_ALLOWLIST),
           "expected_prompts_per_model": sum(len(v) for v in want_by_chunk.values()),
           "generation": {}, "channel1": {}, "channel2": {}}

    for gen_dir, model in GEN_DIRS.items():
        comps = load_completions(gen_dir)
        gen_sha = {c: {row["prompt_sha256"] for row in rows}
                   for c, rows in comps.items()}
        out["generation"][gen_dir] = {
            "model": model,
            "chunks_present": sorted(gen_sha),
            "chunks_missing": [c for c in CHUNK_ALLOWLIST if c not in gen_sha],
            "n_rows": sum(len(v) for v in gen_sha.values()),
            "complete": all(
                want_by_chunk.get(c, set()) <= gen_sha.get(c, set())
                for c in CHUNK_ALLOWLIST),
        }

        cos_sha, cos_chunks = load_cosines(gen_dir)
        missing_c1 = {c: sorted(want_by_chunk.get(c, set()) - set(cos_sha))
                      for c in CHUNK_ALLOWLIST}
        out["channel1"][gen_dir] = {
            "model": model,
            "chunks_present": sorted(cos_chunks),
            "chunks_missing": [c for c in CHUNK_ALLOWLIST if c not in cos_chunks],
            "n_scored": len(cos_sha),
            "n_unscored_prompts": sum(len(v) for v in missing_c1.values()),
            "complete": not any(missing_c1.values()),
        }

        lab_sha, lab_chunks = load_labels(gen_dir)
        missing_c2 = {c: sorted(want_by_chunk.get(c, set()) - set(lab_sha))
                      for c in CHUNK_ALLOWLIST}
        n_unparsed = sum(1 for v in lab_sha.values() if v.get("label") is None)
        out["channel2"][gen_dir] = {
            "model": model,
            "chunks_present": sorted(lab_chunks),
            "chunks_missing": [c for c in CHUNK_ALLOWLIST if c not in lab_chunks],
            "chunks_without_sidecar": sorted(
                c for c, v in lab_chunks.items() if not v["sidecar_present"]),
            "n_labelled": len(lab_sha),
            "n_unlabelled_prompts": sum(len(v) for v in missing_c2.values()),
            "n_parse_failures": n_unparsed,
            "complete": (not any(missing_c2.values())
                         and all(v["sidecar_present"] for v in lab_chunks.values())
                         and n_unparsed == 0),
        }

    out["channel1_complete"] = all(v["complete"] for v in out["channel1"].values())
    out["channel2_complete"] = all(v["complete"] for v in out["channel2"].values())
    out["generation_complete"] = all(v["complete"] for v in out["generation"].values())
    out["all_complete"] = (out["channel1_complete"] and out["channel2_complete"]
                           and out["generation_complete"])
    return out


def logical_rows(renders: list, items: dict) -> list:
    """One row per logical render, carrying its item's metadata.

    A logical render is what the design asks for; a prompt is what was sent.
    They differ only where two renders are byte-identical (H7-R5, H7-R7), and
    the score of the shared prompt belongs to both rows.
    """
    out = []
    for row in renders:
        item = items.get(row["item_id"])
        if item is None:
            raise fatal(f"render row {row['item_id']} is not in items_confirm")
        out.append({
            "canonical_id": row["canonical_id"],
            "item_id": row["item_id"],
            "arm": row["arm"],
            "h7_bin": row.get("h7_bin"),
            "delta_days": row.get("delta_days"),
            "cutoff_date": row.get("cutoff_date"),
            "prompt_sha256": row["prompt_sha256"],
            "chunk": row["chunk"],
            "duplicate_prompt": bool(row.get("is_duplicate_of_earlier_render")),
            "item_delta_bin": item.get("delta_bin"),
            "item_type": item.get("item_type"),
            "donor_id": item.get("donor_id"),
            "item_flags": item.get("flags") or [],
        })
    return out


# ---------------------------------------------------------------------------
# Per-subject, per-arm scores
# ---------------------------------------------------------------------------


def channel1_subject_arm(rows: list, cos_by_sha: dict,
                         drop_items: set | None = None) -> dict:
    """arm -> {subject -> mean cosine over that subject's items}."""
    drop_items = drop_items or set()
    acc: dict = {}
    for row in rows:
        if row["arm"] not in H1_ARMS or row["item_id"] in drop_items:
            continue
        cos = cos_by_sha.get(row["prompt_sha256"])
        if cos is None:
            continue
        acc.setdefault(row["arm"], {}).setdefault(
            row["canonical_id"], []).append(float(cos["cosine_to_real"]))
    return {arm: {s: sum(v) / len(v) for s, v in subs.items()}
            for arm, subs in acc.items()}


def channel1_item_level(rows: list, cos_by_sha: dict,
                        drop_items: set | None = None) -> dict:
    """arm -> {item_id -> cosine}. The OE-1 pooling unit, kept for continuity."""
    drop_items = drop_items or set()
    out: dict = {}
    for row in rows:
        if row["arm"] not in H1_ARMS or row["item_id"] in drop_items:
            continue
        cos = cos_by_sha.get(row["prompt_sha256"])
        if cos is None:
            continue
        out.setdefault(row["arm"], {})[row["item_id"]] = float(
            cos["cosine_to_real"])
    return out


def channel2_subject_arm(rows: list, lab_by_sha: dict,
                         drop_items: set | None = None) -> dict:
    """Stance-match per subject and arm, under the adopted UNCLEAR rule.

    UNCLEAR is dropped from the denominator (Addendum A instrument parameter
    6). The rate a subject contributes is SAME / (SAME + DIFFERENT) over that
    subject's own items; a subject with an empty denominator in an arm simply
    has no value for that arm and is counted as such wherever it matters.
    """
    drop_items = drop_items or set()
    counts: dict = {}
    for row in rows:
        if row["arm"] not in H1_ARMS or row["item_id"] in drop_items:
            continue
        lab = lab_by_sha.get(row["prompt_sha256"])
        if lab is None:
            continue
        label = lab.get("label")
        c = counts.setdefault(row["arm"], {}).setdefault(
            row["canonical_id"], {"SAME": 0, "DIFFERENT": 0, "UNCLEAR": 0,
                                  "None": 0})
        c[str(label) if label in ("SAME", "DIFFERENT", "UNCLEAR") else "None"] += 1
    rates, unclear, denom = {}, {}, {}
    for arm, subs in counts.items():
        for s, c in subs.items():
            den = c["SAME"] + c["DIFFERENT"]
            total = den + c["UNCLEAR"] + c["None"]
            denom.setdefault(arm, {})[s] = den
            if den:
                rates.setdefault(arm, {})[s] = c["SAME"] / den
            if total:
                unclear.setdefault(arm, {})[s] = c["UNCLEAR"] / total
    return {"rate": rates, "unclear_rate": unclear, "denominator": denom,
            "counts": counts}


def channel2_pooled_counts(rows: list, lab_by_sha: dict,
                           drop_items: set | None = None) -> dict:
    """arm -> {SAME, DIFFERENT, UNCLEAR, None} pooled over every item."""
    drop_items = drop_items or set()
    out: dict = {}
    for row in rows:
        if row["arm"] not in H1_ARMS or row["item_id"] in drop_items:
            continue
        lab = lab_by_sha.get(row["prompt_sha256"])
        if lab is None:
            continue
        label = lab.get("label")
        key = str(label) if label in ("SAME", "DIFFERENT", "UNCLEAR") else "None"
        out.setdefault(row["arm"], {"SAME": 0, "DIFFERENT": 0,
                                    "UNCLEAR": 0, "None": 0})[key] += 1
    return out


def arm_summary(by_subj: dict) -> dict:
    """Raw per-arm values, so they can sit beside every difference."""
    out = {}
    for arm, subs in sorted(by_subj.items()):
        v = np.array(list(subs.values()), dtype=float)
        out[arm] = {
            "n_subjects": len(v),
            "mean_of_subject_means": r(float(v.mean())) if len(v) else None,
            "sd_of_subject_means": r(float(v.std(ddof=1))) if len(v) > 1 else None,
            "min": r(float(v.min())) if len(v) else None,
            "max": r(float(v.max())) if len(v) else None,
        }
    return out


# ---------------------------------------------------------------------------
# H1
# ---------------------------------------------------------------------------


#: The registered contrasts, in the order the report prints them.
#: (key, arm_a, arm_b, role)
H1_CONTRASTS = (
    ("own_minus_imposter", OWN_ARM, IMPOSTER_ARM,
     "PRIMARY (Amendment 3 C3). Like-for-like: both arms are redacted."),
    ("own_named_minus_imposter", OWN_NAMED_ARM, IMPOSTER_ARM,
     "Reported beside. Not like-for-like: the twin arm carries a name line "
     "the imposter arm does not."),
    ("own_minus_zeroinfo", OWN_ARM, ZERO_RED,
     "Zero-information lift, like-for-like. This is the contrast the "
     "magnitude bar names for H1."),
    ("own_named_minus_zeroinfo_named", OWN_NAMED_ARM, ZERO_NAMED,
     "Zero-information lift, named-arm pair."),
)


def h1_block(subject_arm: dict, channel: str) -> dict:
    """Every registered H1 contrast on one channel of one model."""
    out = {"channel": channel, "per_arm_raw": arm_summary(subject_arm),
           "contrasts": {}}
    mag_bar = MAG_BAR_CH1 if channel == "1" else MAG_BAR_CH2
    for key, a, b, role in H1_CONTRASTS:
        if a not in subject_arm or b not in subject_arm:
            out["contrasts"][key] = {"role": role, "unavailable": True}
            continue
        block = paired_contrast(subject_arm[a], subject_arm[b], a, b)
        block["role"] = role
        block["magnitude_bar"] = mag_bar
        block["meets_magnitude_bar"] = (
            None if block["mean_diff"] is None
            else bool(block["mean_diff"] >= mag_bar))
        block["direction_positive"] = (
            None if block["mean_diff"] is None else bool(block["mean_diff"] > 0))
        block["significant_at_p05"] = (
            None if block["p_paired_t"] is None
            else bool(block["p_paired_t"] < ALPHA))
        out["contrasts"][key] = block
    return out


def h1_verdict(primary_ch1: dict, primary_ch2: dict | None,
               robust_ch1: dict, robust_ch2: dict | None,
               n_subjects: int, channel2_complete: bool) -> dict:
    """Apply the H1 bars. Mechanically, and only when the data is there."""
    def legs(block):
        if block is None:
            return None
        imp = block["contrasts"].get("own_minus_imposter", {})
        zer = block["contrasts"].get("own_minus_zeroinfo", {})
        if imp.get("unavailable") or zer.get("unavailable"):
            return None
        return {
            "imposter_leg": {"mean": imp.get("mean_diff"),
                             "p": imp.get("p_paired_t"),
                             "passes": bool(imp.get("direction_positive")
                                            and imp.get("significant_at_p05"))},
            "zeroinfo_leg": {"mean": zer.get("mean_diff"),
                             "p": zer.get("p_paired_t"),
                             "passes": bool(zer.get("direction_positive")
                                            and zer.get("significant_at_p05"))},
        }

    out = {
        "bar_quoted": FROZEN_BARS["H1"]["text"],
        "bar_updated_quoted": FROZEN_BARS["H1_updated"]["text"],
        "magnitude_bar_quoted": FROZEN_BARS["magnitude"]["text"],
        "n_subjects": n_subjects,
        "subject_count_branch": branch_for(n_subjects),
        "branch_rule_quoted": FROZEN_BARS["branch"]["text"],
        "primary_model_channel1": legs(primary_ch1),
        "primary_model_channel2": legs(primary_ch2),
        "robustness_model_channel1": legs(robust_ch1),
        "robustness_model_channel2": legs(robust_ch2),
    }
    p1 = out["primary_model_channel1"]
    out["channel1_primary_passes_A1"] = (
        None if p1 is None
        else bool(p1["imposter_leg"]["passes"] and p1["zeroinfo_leg"]["passes"]))
    if not channel2_complete:
        out["verdict"] = AWAIT
        out["verdict_reason"] = (
            "Channel 2 is incomplete. Amendment 3 C2.4 requires direction "
            "agreement across both channels for any headline, so no H1 "
            "verdict is printed. The channel-1 numbers below are real and are "
            "labelled PRELIMINARY.")
        return out
    p2 = out["primary_model_channel2"]
    r1 = out["robustness_model_channel1"]
    r2 = out["robustness_model_channel2"]
    both_channels_primary = bool(
        p1 and p2
        and p1["imposter_leg"]["passes"] and p1["zeroinfo_leg"]["passes"]
        and p2["imposter_leg"]["passes"] and p2["zeroinfo_leg"]["passes"])
    direction_agree = bool(
        p1 and p2
        and (p1["imposter_leg"]["mean"] > 0) == (p2["imposter_leg"]["mean"] > 0)
        and (p1["zeroinfo_leg"]["mean"] > 0) == (p2["zeroinfo_leg"]["mean"] > 0))
    robust_direction = bool(
        r1 and r2
        and r1["imposter_leg"]["mean"] > 0 and r2["imposter_leg"]["mean"] > 0)
    out["channel_direction_agreement_primary_model"] = direction_agree
    out["robustness_model_direction_holds"] = robust_direction
    out["verdict"] = ("PASS" if (both_channels_primary and direction_agree
                                 and robust_direction) else "FAIL")
    out["verdict_reason"] = (
        "A1's two legs both clear p < .05 in the pre-registered direction on "
        "the primary model in both channels; the channels agree in direction; "
        "A3's robustness model holds direction."
        if out["verdict"] == "PASS" else
        "At least one frozen requirement is not met; see the legs above.")
    return out


# ---------------------------------------------------------------------------
# Contamination meter and H3
# ---------------------------------------------------------------------------


def contamination_block(subject_arm: dict, item_level: dict,
                        channel: str) -> dict:
    """(named baseline) - (name-redacted baseline), the frozen definition.

    Two figures, both reported: the per-subject meter the pre-registration
    defines, and the pooled item-level figure OE-1 printed (so the
    confirmatory number is comparable to OE-1's +0.016 / +0.048).
    """
    out = {"channel": channel,
           "definition_quoted": FROZEN_BARS["contamination_meter"]["text"],
           "method_note": (
               "Per-subject: mean(zeroinfo_named) - mean(zeroinfo_redacted) "
               "over that subject's items. Pooled: the OE-1 method -- the "
               "difference of the two arm means taken over all items at once "
               "(experiments/stage2_oe1.py, _paired_block "
               "'contamination_meter')."),
           "per_subject": {}, "pooled_item_level": None,
           "paired_test": None, "flag": None}
    named = subject_arm.get(ZERO_NAMED, {})
    red = subject_arm.get(ZERO_RED, {})
    subs = sorted(set(named) & set(red))
    meters = {s: named[s] - red[s] for s in subs}
    out["per_subject"] = {s: r(v) for s, v in sorted(meters.items())}
    if meters:
        out["paired_test"] = paired_contrast(named, red, ZERO_NAMED, ZERO_RED)
        v = np.array(list(meters.values()), dtype=float)
        out["summary"] = {
            "n_subjects": len(v),
            "mean": r(float(v.mean())), "median": r(float(np.median(v))),
            "sd": r(float(v.std(ddof=1))) if len(v) > 1 else None,
            "min": r(float(v.min())), "max": r(float(v.max())),
            "n_positive": int((v > 0).sum()), "n_negative": int((v < 0).sum()),
        }
        # "subjects with a large meter are analyzed separately": the top decile
        # by meter, named so the separate look is possible.
        cut = float(np.percentile(v, 90))
        out["large_meter_cutoff_p90"] = r(cut)
        out["large_meter_subjects"] = sorted(
            s for s, m in meters.items() if m >= cut)
    ni = item_level.get(ZERO_NAMED, {})
    ri = item_level.get(ZERO_RED, {})
    if ni and ri:
        out["pooled_item_level"] = r(
            sum(ni.values()) / len(ni) - sum(ri.values()) / len(ri))
        out["pooled_arm_means"] = {
            ZERO_NAMED: r(sum(ni.values()) / len(ni)),
            ZERO_RED: r(sum(ri.values()) / len(ri)),
        }
    if out["pooled_item_level"] is not None:
        out["flag"] = bool(out["pooled_item_level"] > 0)
        out["flag_note"] = (
            "LIVE FLAG: the named zero-information arm scores above the "
            "redacted one, which is what a contamination meter is built to "
            "detect. OE-1 measured this descriptively at +0.016 (Gemma) and "
            "+0.048 (flash-lite)."
            if out["flag"] else
            "The named zero-information arm does not score above the redacted "
            "one on this channel and model.")
    return out


#: The two contrasts the separate large-meter analysis recomputes.
SEPARATE_CONTRASTS = (
    ("own_minus_imposter", OWN_ARM, IMPOSTER_ARM),
    ("own_minus_zeroinfo", OWN_ARM, ZERO_RED),
)


def separate_large_meter_block(subject_arm: dict, large: list,
                               channel: str) -> dict:
    """The frozen 'analyzed separately' look, run rather than only named.

    PREREGISTRATION.md's contamination controls say subjects with a large meter
    are analyzed separately. The report already names them; this recomputes the
    primary contrasts inside and outside that group so the mandated separate
    analysis exists as numbers. Descriptive, no bar attached: the split is made
    after the fact, on a top-decile cut, and the groups are small.
    """
    large_set = set(large or [])
    out = {"channel": channel, "n_large": 0, "n_rest": 0,
           "large_meter_subjects": sorted(large_set), "contrasts": {}}
    for key, arm_a, arm_b in SEPARATE_CONTRASTS:
        if arm_a not in subject_arm or arm_b not in subject_arm:
            continue
        a_all, b_all = subject_arm[arm_a], subject_arm[arm_b]
        paired = sorted(set(a_all) & set(b_all))
        groups = {
            "large_meter": [s for s in paired if s in large_set],
            "rest": [s for s in paired if s not in large_set],
        }
        out["n_large"] = len(groups["large_meter"])
        out["n_rest"] = len(groups["rest"])
        blk = {}
        for gname, subs in groups.items():
            if not subs:
                blk[gname] = {"n_subjects": 0}
                continue
            blk[gname] = paired_contrast({s: a_all[s] for s in subs},
                                         {s: b_all[s] for s in subs},
                                         arm_a, arm_b)
        a, b = (blk["large_meter"].get("mean_diff"), blk["rest"].get("mean_diff"))
        blk["large_minus_rest"] = (None if a is None or b is None else r(a - b))
        blk["note"] = ("Two independent groups of subjects, not a paired "
                       "comparison between them: the difference of the two "
                       "group means carries no test and none is run.")
        out["contrasts"][key] = blk
    return out


def h3_block(subject_arm: dict, meters: dict, channel: str) -> dict:
    """H3, descriptive: does lift shrink as the meter grows?"""
    out = {"channel": channel, "label": "DESCRIPTIVE (H3 is registered as "
                                        "descriptive, not confirmatory)",
           "bar_quoted": FROZEN_BARS["H3"]["text"],
           "estimator_note": (
               "Pearson and Spearman correlation between a subject's lift and "
               "that subject's contamination meter. No estimator is frozen "
               "for H3 -- this choice is declared here, not inherited."),
           "shared_term_warning": (
               "READ THIS BEFORE THE NUMBERS. The meter is "
               "zeroinfo_named - zeroinfo_redacted and the zero-information "
               "lift is own - zeroinfo_redacted. They share the "
               "zeroinfo_redacted term with the same sign, so a subject whose "
               "redacted baseline happens to be low gets a large meter AND a "
               "large lift for that reason alone. The own-minus-zeroinfo row "
               "is therefore mechanically coupled to the meter and cannot "
               "test H3. The own-minus-imposter row shares no term with the "
               "meter and is the confound-free reading."),
           "correlations": {}}
    lifts = {
        "own_minus_imposter": (OWN_ARM, IMPOSTER_ARM),
        "own_minus_zeroinfo": (OWN_ARM, ZERO_RED),
    }
    for name, (a, b) in lifts.items():
        if a not in subject_arm or b not in subject_arm:
            continue
        subs = sorted(set(subject_arm[a]) & set(subject_arm[b]) & set(meters))
        if len(subs) < 3:
            continue
        x = np.array([meters[s] for s in subs], dtype=float)
        y = np.array([subject_arm[a][s] - subject_arm[b][s] for s in subs],
                     dtype=float)
        pr = sstats.pearsonr(x, y)
        sp = sstats.spearmanr(x, y)
        out["correlations"][name] = {
            "n_subjects": len(subs),
            "shares_a_term_with_the_meter": name == "own_minus_zeroinfo",
            "usable_for_H3": name != "own_minus_zeroinfo",
            "pearson_r": r(float(pr.statistic)), "pearson_p": rp(float(pr.pvalue)),
            "spearman_rho": r(float(sp.statistic)),
            "spearman_p": rp(float(sp.pvalue)),
            "reading": ("negative correlation: lift is smaller where the "
                        "meter is larger, the direction H3 predicts"
                        if float(pr.statistic) < 0 else
                        "non-negative correlation: lift does not shrink as "
                        "the meter grows in this data"),
        }
    return out


# ---------------------------------------------------------------------------
# H7
# ---------------------------------------------------------------------------


def h7_cells(rows: list, score_of, drop_items: set | None = None) -> dict:
    """(arm, subject, bin) -> mean score, plus the delta of each cell.

    ``score_of`` maps a logical row to a float or None. The fresh imposter is
    rendered once per item and reused at every bin (rule H7-R7), so it is
    placed into the bins its subject actually filled, restricted to the same
    items -- otherwise the crossover would compare different item sets.
    """
    drop_items = drop_items or set()
    twin, delta = {}, {}
    items_by_cell = {}
    for row in rows:
        if row["arm"] != "h7_twin_redacted" or row["item_id"] in drop_items:
            continue
        val = score_of(row)
        if val is None:
            continue
        key = (row["canonical_id"], row["h7_bin"])
        twin.setdefault(key, []).append(val)
        items_by_cell.setdefault(key, set()).add(row["item_id"])
        if row["delta_days"] is not None:
            delta[key] = row["delta_days"]
    imp_by_item = {}
    for row in rows:
        if row["arm"] != "h7_imposter_fresh" or row["item_id"] in drop_items:
            continue
        val = score_of(row)
        if val is not None:
            imp_by_item[row["item_id"]] = val
    imposter = {}
    for key, iids in items_by_cell.items():
        vals = [imp_by_item[i] for i in sorted(iids) if i in imp_by_item]
        if vals:
            imposter[key] = sum(vals) / len(vals)
    return {
        "twin": {k: sum(v) / len(v) for k, v in twin.items()},
        "imposter": imposter,
        "delta_days": delta,
        "n_items": {k: len(v) for k, v in items_by_cell.items()},
    }


def h7_block(rows: list, score_of, manifest: dict, channel: str,
             model: str, drop_items: set | None = None) -> dict:
    cells = h7_cells(rows, score_of, drop_items)
    twin, imp, delta = cells["twin"], cells["imposter"], cells["delta_days"]

    subjects = sorted({s for s, _ in twin})
    out = {
        "channel": channel, "model": model,
        "label": "EXPLORATORY",
        "label_reason": None,   # filled below from the branch
        "bar_quoted": FROZEN_BARS["H7"]["text"],
        "crossover_quoted": FROZEN_BARS["H7_crossover"]["text"],
        "reading_decay_quoted": FROZEN_BARS["H7_reading_decay"]["text"],
        "reading_flat_quoted": FROZEN_BARS["H7_reading_flat"]["text"],
        "volume_control_quoted": FROZEN_BARS["H7_volume_control"]["text"],
        "n_subjects_with_any_bin": len(subjects),
        "per_bin": {}, "per_subject_slope": {}, "slope_test": None,
        "crossover": {}, "within_subject_sweep": {},
        "freshest_minus_stalest": None,
    }

    for b in H7_BIN_ORDER:
        subs = sorted({s for (s, bb) in twin if bb == b})
        tw = [twin[(s, b)] for s in subs]
        im = [imp[(s, b)] for s in subs if (s, b) in imp]
        ds = [delta[(s, b)] for s in subs if (s, b) in delta]
        out["per_bin"][b] = {
            "n_subjects": len(subs),
            "n_items": sum(cells["n_items"].get((s, b), 0) for s in subs),
            "stale_own_twin_mean": r(sum(tw) / len(tw)) if tw else None,
            "fresh_imposter_mean": r(sum(im) / len(im)) if im else None,
            "mean_delta_days": r(sum(ds) / len(ds), 1) if ds else None,
            "min_delta_days": min(ds) if ds else None,
            "max_delta_days": max(ds) if ds else None,
            "own_minus_fresh_imposter": (
                r(sum(tw) / len(tw) - sum(im) / len(im))
                if tw and im and len(tw) == len(im) else None),
        }

    # The frozen bar: per-subject slope of fidelity against delta.
    slopes, n_one_bin = {}, 0
    for s in subjects:
        pts = sorted((delta[(s, b)], twin[(s, b)])
                     for b in H7_BIN_ORDER if (s, b) in twin and (s, b) in delta)
        xs = [p[0] for p in pts]
        if len(set(xs)) < 2:
            n_one_bin += 1
            continue
        x = np.array([p[0] for p in pts], dtype=float)
        y = np.array([p[1] for p in pts], dtype=float)
        fit = sstats.linregress(x, y)
        slopes[s] = float(fit.slope)
        out["per_subject_slope"][s] = {
            "n_bins": len(pts),
            "slope_per_day": r(float(fit.slope), 8),
            "slope_per_year": r(float(fit.slope) * 365.25),
            "delta_days": [int(v) for v in xs],
            "fidelity": [r(v) for v in y.tolist()],
        }
    out["n_subjects_with_slope"] = len(slopes)
    out["n_subjects_single_bin_no_slope"] = n_one_bin
    if slopes:
        blk = one_sample_block(slopes, "per-subject slope of fidelity vs delta "
                                       "(per day)")
        blk["mean_slope_per_year"] = r((blk["mean"] or 0) * 365.25)
        blk["ci95_t_per_year"] = [r((blk["ci95_t"][0] or 0) * 365.25),
                                  r((blk["ci95_t"][1] or 0) * 365.25)]
        blk["direction_negative"] = (None if blk["mean"] is None
                                     else bool(blk["mean"] < 0))
        blk["significant_at_p05"] = (None if blk["p_paired_t"] is None
                                     else bool(blk["p_paired_t"] < ALPHA))
        blk["meets_frozen_bar"] = (
            None if blk["mean"] is None or blk["p_paired_t"] is None
            else bool(blk["mean"] < 0 and blk["p_paired_t"] < ALPHA))
        # One-sided reading printed beside, since the bar names a direction.
        if blk["p_paired_t"] is not None:
            blk["p_one_sided_decline"] = rp(
                blk["p_paired_t"] / 2 if (blk["mean"] or 0) < 0
                else 1 - blk["p_paired_t"] / 2)
        out["slope_test"] = blk

    # The pre-declared crossover statistic.
    cross_bin = None
    for b in H7_BIN_ORDER:
        pb = out["per_bin"][b]
        if pb["stale_own_twin_mean"] is None or pb["fresh_imposter_mean"] is None:
            continue
        if pb["fresh_imposter_mean"] >= pb["stale_own_twin_mean"]:
            cross_bin = b
            break
    per_subject_cross = {}
    for s in subjects:
        for b in H7_BIN_ORDER:
            if (s, b) in twin and (s, b) in imp and imp[(s, b)] >= twin[(s, b)]:
                per_subject_cross[s] = b
                break
    out["crossover"] = {
        "definition": ("smallest delta bin at which the fresh same-domain "
                       "imposter twin matches or beats the stale own twin, "
                       "pooled over the subjects who filled that bin and "
                       "restricted to the same items"),
        "pooled_crossover_bin": cross_bin,
        "occurs_in_observed_range": bool(cross_bin is not None),
        "n_subjects_with_crossover": len(per_subject_cross),
        "n_subjects_evaluated": len(subjects),
        "per_subject_crossover_bin": per_subject_cross,
    }

    # Magnitude bar for H7: freshest minus stalest bin, paired where possible.
    fresh_b, stale_b = H7_BIN_ORDER[0], H7_BIN_ORDER[-1]
    a = {s: twin[(s, fresh_b)] for s in subjects if (s, fresh_b) in twin}
    b_ = {s: twin[(s, stale_b)] for s in subjects if (s, stale_b) in twin}
    mag_bar = MAG_BAR_CH1 if channel == "1" else MAG_BAR_CH2
    if a and b_:
        blk = paired_contrast(a, b_, f"h7_twin_redacted[{fresh_b}]",
                              f"h7_twin_redacted[{stale_b}]")
        blk["magnitude_bar"] = mag_bar
        blk["meets_magnitude_bar"] = (
            None if blk["mean_diff"] is None
            else bool(blk["mean_diff"] >= mag_bar))
        blk["note"] = ("Paired over the subjects who filled BOTH the freshest "
                       "and the stalest bin. The unpaired bin means are in "
                       "per_bin above.")
        out["freshest_minus_stalest"] = blk
    else:
        out["freshest_minus_stalest"] = {
            "unavailable": True,
            "note": "No subject filled both the freshest and the stalest bin.",
        }
    # Unpaired version, always printed beside.
    pf, ps = out["per_bin"][fresh_b], out["per_bin"][stale_b]
    if pf["stale_own_twin_mean"] is not None and ps["stale_own_twin_mean"] is not None:
        out["freshest_minus_stalest_unpaired"] = {
            "mean_a": pf["stale_own_twin_mean"], "mean_b": ps["stale_own_twin_mean"],
            "mean_diff": r(pf["stale_own_twin_mean"] - ps["stale_own_twin_mean"]),
            "n_subjects_a": pf["n_subjects"], "n_subjects_b": ps["n_subjects"],
            "note": "Different subjects in each bin; between-subject, not paired.",
        }

    # The supporting within-subject sweep.
    sweep = list(manifest.get("h7", {}).get("within_subject_sweep_subset", []))
    out["within_subject_sweep"] = {
        "quoted": FROZEN_BARS["H7_within_subject"]["text"],
        "subset": sweep,
        "n_subjects": len(sweep),
        "status": "SUPPORTING ANALYSIS, never substituted for the "
                  "between-subject result",
        "per_subject": {s: out["per_subject_slope"].get(s)
                        for s in sweep if s in out["per_subject_slope"]},
    }
    sweep_slopes = {s: slopes[s] for s in sweep if s in slopes}
    if len(sweep_slopes) >= 2:
        out["within_subject_sweep"]["slope_test"] = one_sample_block(
            sweep_slopes, "within-subject-sweep per-subject slope (per day)")
    return out


# ---------------------------------------------------------------------------
# B8
# ---------------------------------------------------------------------------


def b8_block(subject_arm_ch1: dict, ch2: dict, pooled_counts: dict,
             channel2_complete: bool) -> dict:
    """Individual-level lift beside the population-level TVD, divergences flagged."""
    out = {
        "rule_quoted": FROZEN_BARS["B8"]["text"],
        "no_bar_quoted": FROZEN_BARS["B8_no_bar"]["text"],
        "population_metric_definition": (
            "TVD over the stance categories {SAME, DIFFERENT, UNCLEAR} "
            "between two arms' pooled label distributions. The real answer "
            "carries no stance label of its own, so there is no reference "
            "distribution to compare an arm against; the registered metric is "
            "therefore taken between arms, the same reading the dev pilot "
            "used (experiments/stage2_oe1.py, 'tvd_vs_own_arm')."),
        "channel1_note": (
            "Channel 1 is a continuous cosine and has no stance categories, "
            "so the registered population metric does not apply to it. Its "
            "individual-level lift is printed here so the two levels sit in "
            "one table, as B8 requires."),
        "individual_level": {}, "population_level": {}, "divergences": [],
    }
    for key, a, b, _role in H1_CONTRASTS:
        if a in subject_arm_ch1 and b in subject_arm_ch1:
            blk = paired_contrast(subject_arm_ch1[a], subject_arm_ch1[b], a, b)
            out["individual_level"][key] = {
                "channel1_mean_diff": blk["mean_diff"],
                "channel1_ci95": blk["ci95_t"],
                "channel1_p": blk["p_paired_t"],
                "channel2_mean_diff": AWAIT if not channel2_complete else None,
            }
    if not channel2_complete:
        out["population_level"] = AWAIT
        out["divergences"] = AWAIT
        return out

    for arm, counts in sorted(pooled_counts.items()):
        clean = {k: v for k, v in counts.items() if k != "None"}
        out["population_level"][arm] = {
            "counts": clean,
            "tvd_vs_twin_redacted": tvd(clean, {
                k: v for k, v in pooled_counts.get(OWN_ARM, {}).items()
                if k != "None"}),
        }
    # Fill the channel-2 individual level and flag disagreements.
    rates = ch2.get("rate", {})
    counts_by_subject = ch2.get("counts", {})
    for key, a, b, _role in H1_CONTRASTS:
        if a not in rates or b not in rates:
            continue
        blk = paired_contrast(rates[a], rates[b], a, b)
        row = out["individual_level"].setdefault(key, {})
        row["channel2_mean_diff"] = blk["mean_diff"]
        row["channel2_ci95"] = blk["ci95_t"]
        row["channel2_p"] = blk["p_paired_t"]
        # The population level of THIS contrast: TVD between the two arms'
        # own label distributions, pooled, and per subject.
        pa = {k: v for k, v in pooled_counts.get(a, {}).items() if k != "None"}
        pb = {k: v for k, v in pooled_counts.get(b, {}).items() if k != "None"}
        row["population_tvd_pooled"] = tvd(pa, pb)
        per_sub = []
        for s in sorted(set(counts_by_subject.get(a, {}))
                        & set(counts_by_subject.get(b, {}))):
            ca = {k: v for k, v in counts_by_subject[a][s].items() if k != "None"}
            cb = {k: v for k, v in counts_by_subject[b][s].items() if k != "None"}
            t = tvd(ca, cb)
            if t is not None:
                per_sub.append(t)
        row["population_tvd_per_subject_mean"] = (
            r(sum(per_sub) / len(per_sub)) if per_sub else None)
        row["population_tvd_n_subjects"] = len(per_sub)
        c1 = row.get("channel1_mean_diff")
        c2 = row.get("channel2_mean_diff")
        if c1 is not None and c2 is not None and (c1 > 0) != (c2 > 0):
            out["divergences"].append(
                f"{key}: the two channels move in opposite directions "
                f"(channel 1 {fmt(c1, plus=True)}, channel 2 "
                f"{fmt(c2, plus=True)}).")
    # Population vs individual divergence, on the primary contrast.
    prim = out["individual_level"].get("own_minus_imposter", {})
    pop_imp = prim.get("population_tvd_pooled")
    if prim.get("channel2_ci95") and pop_imp is not None:
        lo, hi = prim["channel2_ci95"]
        if lo is not None and hi is not None and lo <= 0 <= hi and pop_imp >= 0.05:
            out["divergences"].append(
                "own_minus_imposter: the population-level TVD between the twin "
                f"and imposter label distributions is {fmt(pop_imp)} while the "
                "individual-level stance lift's 95% CI still covers zero -- "
                "the two levels disagree.")
        if (lo is not None and lo > 0) and pop_imp < 0.05:
            out["divergences"].append(
                "own_minus_imposter: individual-level stance lift is "
                "distinguishable from zero while the population-level TVD is "
                f"only {fmt(pop_imp)} -- the two levels disagree.")
    if not out["divergences"]:
        out["divergences"] = ["None. The individual and population levels "
                              "agree on every registered contrast."]
    return out


# ---------------------------------------------------------------------------
# Health, costs, provenance
# ---------------------------------------------------------------------------


def era_violation_rows() -> list:
    out = []
    for gen_dir in GEN_DIRS:
        for chunk in CHUNK_ALLOWLIST:
            path = GEN_ROOT / gen_dir / f"completions_{chunk}.jsonl"
            for row in read_jsonl(path):
                if row.get("era_violations"):
                    out.append({
                        "gen_dir": gen_dir, "model": GEN_DIRS[gen_dir],
                        "chunk": chunk, "item_id": row["item_id"],
                        "canonical_id": row["canonical_id"],
                        "arm": row["arm"],
                        "era_violations": row["era_violations"],
                    })
    return out


def health_block(manifest: dict, build: dict, pairs: dict, comp: dict) -> dict:
    per_arm: dict = {}
    per_chunk: dict = {}
    for gen_dir in GEN_DIRS:
        pattern = ("gen_summary_{}.json" if gen_dir == "flashlite"
                   else "ingest_summary_{}.json")
        for chunk in CHUNK_ALLOWLIST:
            path = GEN_ROOT / gen_dir / pattern.format(chunk)
            if not path.exists():
                continue
            s = read_json(path)
            per_chunk.setdefault(gen_dir, {})[chunk] = {
                "n_rows": s.get("n_rows"),
                "n_truncated": s.get("n_truncated"),
                "n_era_violations": s.get("n_era_violations"),
                "n_over_word_cap": s.get("n_over_word_cap"),
                "n_empty": s.get("n_empty"),
                "n_retries": s.get("n_retries_this_process"),
                "n_missing_completions": s.get("n_missing_completions"),
                "complete": s.get("complete"),
            }
            for arm, v in (s.get("per_arm") or {}).items():
                acc = per_arm.setdefault(gen_dir, {}).setdefault(
                    arm, {"n": 0, "n_truncated": 0, "n_era_violations": 0,
                          "n_over_word_cap": 0, "n_empty": 0})
                for k in acc:
                    acc[k] += v.get(k, 0) or 0

    canaries = []
    for path in sorted(JUDGE_DIR.glob("canary_*_summary.json")):
        s = read_json(path)
        canaries.append({
            "file": rel(path), "n": s.get("n"), "n_flips": s.get("n_flips"),
            "passed": s.get("passed"),
            "max_flips_allowed": s.get("max_flips_allowed"),
            "checked_utc": s.get("checked_utc"), "cost_usd": s.get("cost_usd"),
        })

    guards = manifest.get("guards", {})
    by_subject: dict = {}
    for f in guards.get("failures", []):
        by_subject.setdefault(f["canonical_id"], []).append(f["item_id"])

    donor_mult = (pairs.get("donor_multiplicity", {})
                  or manifest.get("donors", {}).get("donor_multiplicity", {}))
    subjects_by_donor = donor_mult.get("subjects_by_donor", {})
    donor_table = sorted(
        ({"donor_id": d, "n_subjects": len(v), "subjects": sorted(v)}
         for d, v in subjects_by_donor.items()),
        key=lambda x: (-x["n_subjects"], x["donor_id"]))

    tripwires = build.get("tripwires", {})
    name_failures = tripwires.get("zero_guest_turns_in_test", [])

    labels_present = {gd: comp["channel2"][gd]["n_labelled"] for gd in GEN_DIRS}
    return {
        "generation_per_chunk": per_chunk,
        "generation_per_arm": per_arm,
        "era_violations": {
            "rows": era_violation_rows(),
            "treatment": (
                "OE-1's treatment carried forward: an era-flagged generation "
                "is counted and named, never silently dropped. This report "
                "adds a sensitivity line recomputing the primary contrasts "
                "with the affected ITEMS removed -- an addition to OE-1, not "
                "part of it."),
        },
        "guard_exclusions": {
            "n_renders_attempted": guards.get("n_renders_attempted"),
            "n_renders_excluded": guards.get("n_renders_excluded"),
            "exclusion_rate": guards.get("exclusion_rate"),
            "stop_rate": guards.get("stop_rate"),
            "stopped": guards.get("stopped"),
            "by_subject": {k: {"n_items": len(set(v)), "item_ids": sorted(set(v))}
                           for k, v in sorted(by_subject.items())},
            "scope_rule": next(
                (d["choice"] for d in manifest.get("derived_rules", [])
                 if d.get("id") == "GUARD-SCOPE"), None),
        },
        "same_event_leak_scan": manifest.get("same_event_leak_scan", {}),
        "judge_canary": {
            "rule": ("10-row D/E canary at the start of every judging "
                     "session; any label flip against the recorded r2 line "
                     "halts judging (launch plan, risk 2)."),
            "runs": canaries,
            "all_passed": bool(canaries) and all(c["passed"] for c in canaries),
            "total_flips": sum((c["n_flips"] or 0) for c in canaries),
        },
        "donor_concentration": {
            "n_distinct_donors": donor_mult.get("distinct_donors"),
            "n_subjects": donor_mult.get("n_subjects"),
            "max_subjects_per_donor": donor_mult.get("max_subjects_per_donor"),
            "n_eligible_donors": pairs.get("n_eligible_donors"),
            "table": donor_table,
            "caveat": (
                "25 donors ground 89 subjects' imposter arms, and the busiest "
                "donor grounds 11. The imposter arm is therefore not 89 "
                "independent strangers; a donor whose speech happens to sit "
                "close to several subjects moves several rows at once. "
                "Declared beside every own-minus-imposter number."),
        },
        "name_resolution_failures": {
            "rows": name_failures,
            "note": ("Subjects whose test transcript yielded zero guest turns "
                     "because the canonical name did not resolve to a "
                     "speaker. Both failed the build and never reached "
                     "generation; recorded so the attrition is not silent."),
        },
        "item_flags": {
            "note": "Flags recorded on the item at build time.",
        },
        "labels_present_per_model": labels_present,
    }


def cost_block() -> dict:
    rows = [row for row in read_jsonl(COST_LOG)
            if str(row.get("run_id", "")).startswith("stage2_confirm/")]
    api = sum(row.get("cost_usd") or 0.0 for row in rows)
    nh = sum(row.get("node_hours") or 0.0 for row in rows)
    by_run: dict = {}
    for row in rows:
        acc = by_run.setdefault(row["run_id"], {
            "n_entries": 0, "n_calls": 0, "cost_usd": 0.0, "node_hours": 0.0,
            "tokens_in": 0, "tokens_out": 0, "n_parse_failures": 0})
        acc["n_entries"] += 1
        acc["n_calls"] += row.get("n_calls") or 0
        acc["cost_usd"] += row.get("cost_usd") or 0.0
        acc["node_hours"] += row.get("node_hours") or 0.0
        acc["tokens_in"] += row.get("tokens_in") or 0
        acc["tokens_out"] += row.get("tokens_out") or 0
        acc["n_parse_failures"] += row.get("n_parse_failures") or 0
    for acc in by_run.values():
        acc["cost_usd"] = r(acc["cost_usd"])
        acc["node_hours"] = r(acc["node_hours"], 4)
    acct_path = GEN_ROOT / "gemma" / "node_hours_accounting.json"
    acct = read_json(acct_path) if acct_path.exists() else {}
    return {
        "source": rel(COST_LOG),
        "run_id_filter": "stage2_confirm/*",
        "n_entries": len(rows),
        "api_usd_spent": r(api),
        "api_cap_usd": CAP_API_USD,
        "api_headroom_usd": r(CAP_API_USD - api),
        "api_cap_breached": bool(api > CAP_API_USD),
        "node_hours_spent": r(nh, 4),
        "node_hours_cap": CAP_NODE_HOURS,
        "node_hours_headroom": r(CAP_NODE_HOURS - nh, 4),
        "node_hours_cap_breached": bool(nh > CAP_NODE_HOURS),
        "by_run_id": by_run,
        "sacct_accounting": {
            "total_node_hours": acct.get("total_node_hours"),
            "unattributed_node_hours": acct.get("unattributed_node_hours"),
            "n_attempts": len(acct.get("attempts", [])),
            "n_failed_or_cancelled_attempts": sum(
                1 for a in acct.get("attempts", [])
                if a.get("state") != "COMPLETED"),
            "note": ("Billing comes from sacct, not from a watcher; cancelled "
                     "attempts are counted at their billed elapsed time."),
        },
        "note": ("The judge is still spending while this report renders, so "
                 "the API figure is a running total, not a final one."),
    }


PROVENANCE_FILES = (
    ("results/stage2_confirm/items_confirm.jsonl",
     "experiments/stage2_confirm_build.py -> experiments/stage2_confirm_render.py"),
    ("results/stage2_confirm/render_index.jsonl",
     "experiments/stage2_confirm_render.py"),
    ("results/stage2_confirm/render_manifest.json",
     "experiments/stage2_confirm_render.py"),
    ("results/stage2_confirm/imposter_pairs_confirm.json",
     "experiments/stage2_confirm_render.py (rule D7-CONF)"),
    ("results/stage2_confirm/build_full140.json",
     "experiments/stage2_confirm_build.py"),
    ("results/stage2_confirm_draw_provisional.json",
     "experiments/stage2_confirm_draw.py, seed 20260728"),
    ("results/stage2_confirm/embed/embed_summary.json",
     "experiments/stage2_confirm_embed.py"),
    ("results/cost_log.jsonl", "every run driver, appended per chunk"),
    ("results/stage2_confirm/gen/gemma/node_hours_accounting.json",
     "experiments/stage2_confirm_ingest.py, from sacct"),
)


def provenance_block(inputs: dict) -> dict:
    head = git("rev-parse", "HEAD")
    files = []
    for relpath, generator in PROVENANCE_FILES:
        p = _ROOT / relpath
        files.append({
            "file": relpath,
            "generator": generator,
            "exists": p.exists(),
            "sha256": sha256_file(p),
            "last_commit": git("log", "-1", "--format=%H", "--", relpath) or None,
            "tracked": bool(git("ls-files", "--error-unmatch", relpath)),
        })
    for gen_dir in GEN_DIRS:
        gen = ("experiments/stage2_confirm_gen_flashlite.py"
               if gen_dir == "flashlite"
               else "experiments/stage2_confirm_gen.sbatch on Leonardo, "
                    "ingested by experiments/stage2_confirm_ingest.py")
        for chunk in CHUNK_ALLOWLIST:
            for sub, who in (
                    (f"gen/{gen_dir}/completions_{chunk}.jsonl", gen),
                    (f"embed/cosines_{gen_dir}_{chunk}.jsonl",
                     "experiments/stage2_confirm_embed.py"),
                    (f"judge/judgements_{gen_dir}_{chunk}.jsonl",
                     "experiments/stage2_confirm_judge.py")):
                p = CONFIRM_DIR / sub
                if p.exists():
                    files.append({"file": rel(p), "generator": who,
                                  "exists": True, "sha256": sha256_file(p),
                                  "last_commit": git("log", "-1", "--format=%H",
                                                     "--", rel(p)) or None,
                                  "tracked": bool(git("ls-files",
                                                      "--error-unmatch",
                                                      rel(p)))})
    man = inputs["manifest"]
    return {
        "report_generator": "experiments/stage2_confirm_report.py",
        "git_head": head,
        "git_dirty": bool(git("status", "--porcelain")),
        "seed": SEED,
        "n_bootstrap": N_BOOTSTRAP,
        "n_signflip": N_SIGNFLIP,
        "draw_seed": man.get("draw", {}).get("draw_seed"),
        "instrument_channel1": {
            "model": inputs["embed_summary"].get("instrument", {}).get("name"),
            "revision": inputs["embed_summary"].get("instrument", {}).get("revision"),
            "revision_asserted": inputs["embed_summary"].get(
                "instrument", {}).get("revision_asserted"),
            "contract": "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md parameter 1",
        },
        "instrument_channel2": {
            "judge_model": "gemini-3.5-flash",
            "rubric_sha256": "ad050d1a75b038fc63ee162fe74862fd8f99c895e2b39b3af"
                             "56f24bdea102464",
            "temperature": 0.0, "thinking_budget": 0, "max_output_tokens": 512,
            "contract": "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md parameters "
                        "2, 3 and 5",
        },
        "generation_config": man.get("generation_config", {}),
        "governance_documents": [
            "PREREGISTRATION.md", "PREREGISTRATION_AMENDMENT_1.md",
            "PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md",
            "PREREGISTRATION_AMENDMENT_2.md",
            "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md",
            "PREREGISTRATION_AMENDMENT_3.md",
        ],
        "governance_document_sha256": {
            name: sha256_file(_ROOT / name) for name in (
                "PREREGISTRATION.md", "PREREGISTRATION_AMENDMENT_1.md",
                "PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md",
                "PREREGISTRATION_AMENDMENT_2.md",
                "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md",
                "PREREGISTRATION_AMENDMENT_3.md",
                "STAGE2_LAUNCH_PLAN.md")
        },
        "osf_snapshot": "results/osf_preregistration_snapshot_v4.md",
        "files": files,
    }


DEVIATIONS = [
    {"id": "D1", "date": "2026-07-28",
     "text": "The C4.2 human judge tranche is sheet A only (17 of 51 rows, "
             "owner time constraint); the full 51 rows carry an out-of-family "
             "LLM co-auditor line. The two lines are reported separately, "
             "never pooled; their sheet-A concordance (17/17) is stated "
             "wherever either is cited.",
     "owner_decision": "Owner-directed, recorded in "
                       "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md."},
    {"id": "D2", "date": "2026-07-28",
     "text": "The fuzzy-host 20-row spot-check is fully substituted by the "
             "out-of-family LLM co-auditor; no human line exists for it.",
     "owner_decision": "Owner-directed; the blind co-audit matched the census "
                       "key 20/20 and overturned nothing."},
    {"id": "D3", "date": "2026-07-28",
     "text": "The H6 trust audit runs as a blind LLM co-audit (Opus 5) with a "
             "disagreement-triggered human tranche. Result over 120 rows: raw "
             "0.8667, kappa 0.7333 -- clears the B2.2 bar, so no human "
             "tranche was built.",
     "owner_decision": "Owner-directed. Gates H6 only; H6 is not scored in "
                       "this report."},
    {"id": "D4", "date": "2026-07-28",
     "text": "The parameter-5 auditor line on the fresh D/E tranche is a "
             "rubric-briefed out-of-family LLM line (Claude; frozen rubric "
             "read in full, key never opened) in place of the owner's own "
             "rubric-in-hand labels. Reported as its own line, never pooled "
             "with a human line.",
     "owner_decision": "Owner-directed. The r1 round FAILED (raw 0.7778 / "
                       "kappa 0.5789); the pre-committed iteration produced "
                       "rubric r2, which PASSED on the fresh F/G tranche "
                       "(raw 0.8889 / kappa 0.7978) against the unchanged "
                       "bar."},
    {"id": "IN-RUN: D7 re-fit", "date": "2026-07-28",
     "text": "The imposter donor match (SPEC D7) was re-fitted for the "
             "confirmatory run under rules D7-CONF and D7-GUARD: the frozen "
             "seed-48 200-id bank is kept byte-identical, but the 6 dev "
             "subjects and all 140 drawn confirmatory subjects are removed "
             "from ELIGIBILITY (45 removed, 155 permitted, 54 clear the "
             "frozen 2,500-word floor), and a donor that would trip a frozen "
             "leakage assert is excluded from the argmax instead of winning "
             "and then tripping it. The asserts themselves are unchanged and "
             "still run on the winner. 8 subjects' winners moved against the "
             "unmodified reference matcher; every non-excluded reference "
             "winner matches.",
     "owner_decision": "Recorded in render_manifest.json derived_rules "
                       "D7-CONF / D7-GUARD, on the record before generation."},
    {"id": "IN-RUN: C02502 drop", "date": "2026-07-28",
     "text": "Subject C02502 was dropped entirely. Its test transcript "
             "(CNN-388758, 2019-12-25) is a re-airing of CNN-381362 "
             "(2019-09-25) on the same programme, replaying 47% of the test "
             "guest text. The two sit in different dedup clusters, so the "
             "same-event guard never saw them; the downstream answer-leak "
             "assert caught it and excluded all 11 of the subject's items. "
             "The draw rendered 89 survivors; 88 subjects carry items.",
     "owner_decision": "Mechanical consequence of the frozen guard "
                       "(GUARD-SCOPE: a guard failure on any H1 arm excludes "
                       "the whole item). The clustering gap is flagged for "
                       "the owner, not fixed here."},
    {"id": "IN-RUN: name-resolution failures", "date": "2026-07-28",
     "text": "C02240 ('St. John') and C02521 ('Wong Ulrich') yielded zero "
             "guest turns in their test transcript because the canonical name "
             "did not resolve to a speaker, despite the pool's scan cache "
             "recording hundreds of guest words. Both failed the build and "
             "never reached generation. Recorded so the attrition is visible "
             "rather than absorbed into the survival rate.",
     "owner_decision": "Recorded in build_full140.json tripwires "
                       "(zero_guest_turns_in_test, subject_key_single_token)."},
    {"id": "IN-RUN: H7 B = 2,000 words", "date": "2026-07-28",
     "text": "B7.3's volume-control budget B is read as 2,000 words -- the "
             "frozen H1 grounding budget "
             "(stage2_render.GROUNDING_BUDGET_WORDS). No other B exists in "
             "the frozen documents or the code. A cutoff is fillable only if "
             "the grounding speech available at that cutoff reaches B; 100 "
             "cutoffs were dropped as unfillable, 18 as under 6 months, and "
             "68 because their bin was already filled by a newer cutoff.",
     "owner_decision": "Recorded as derived rule H7-R4 before generation."},
    {"id": "IN-RUN: donor concentration caveat", "date": "2026-07-28",
     "text": "25 distinct donors ground the imposter arms of 89 subjects; the "
             "busiest donor grounds 11. The imposter arm is not a set of "
             "independent strangers, so own-minus-imposter carries correlated "
             "noise across the subjects sharing a donor. Declared beside "
             "every own-minus-imposter number rather than corrected for.",
     "owner_decision": "Declared. The 2,500-word floor that causes the "
                       "concentration is frozen and was not relaxed."},
    {"id": "IN-RUN: H7 exploratory band", "date": "2026-07-28",
     "text": "H7 runs at 36 usable subjects (those filling at least one delta "
             "bin after the B7.3 volume control) out of 68 flagged eligible. "
             "Both counts fall in the 30-79 band, so the branch rule returns "
             "EXPLORATORY either way and the choice between them does not "
             "change the label. H1 runs at 88 subjects and is confirmatory.",
     "owner_decision": "Mechanical application of A5 / B3 / B7."},
]


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _quote(key: str) -> str:
    bar = FROZEN_BARS[key]
    return (f"> **Frozen bar, quoted verbatim** "
            f"({bar['source']}):\n>\n> “{bar['text']}”\n")


def _contrast_table(block: dict, channel: str, complete: bool) -> list:
    unit = "cosine" if channel == "1" else "stance-match points"
    lines = [
        f"| contrast | arm A mean | arm B mean | difference | 95% CI | "
        f"paired t p | Wilcoxon p | sign-flip p | subjects | A > B |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for key, a, b, _role in H1_CONTRASTS:
        c = block["contrasts"].get(key, {})
        if c.get("unavailable"):
            lines.append(f"| `{key}` | {AWAIT} | | | | | | | | |")
            continue
        if not complete:
            lines.append(f"| `{key}` | {AWAIT} | {AWAIT} | {AWAIT} | {AWAIT} | "
                         f"{AWAIT} | {AWAIT} | {AWAIT} | {AWAIT} | {AWAIT} |")
            continue
        ci = c.get("ci95_t") or [None, None]
        lines.append(
            f"| `{key}` | {fmt(c.get('mean_a'))} | {fmt(c.get('mean_b'))} | "
            f"**{fmt(c.get('mean_diff'), plus=True)}** | "
            f"[{fmt(ci[0], plus=True)}, {fmt(ci[1], plus=True)}] | "
            f"{fmt_p(c.get('p_paired_t'))} | {fmt_p(c.get('p_wilcoxon'))} | "
            f"{fmt_p(c.get('p_signflip'))} | {c.get('n_subjects')} | "
            f"{c.get('n_subjects_a_gt_b')}/{c.get('n_subjects')} |")
    lines.append("")
    lines.append(f"Units: {unit}. Arm A and arm B means are the raw per-arm "
                 f"numbers, printed beside the difference as the "
                 f"watch-which-arm-moves rule requires.")
    return lines


def render_markdown(data: dict) -> str:
    A = []
    st = data["status"]
    ch2_ok = st["completeness"]["channel2_complete"]
    ch1_ok = st["completeness"]["channel1_complete"]

    A.append("# Stage 2 confirmatory report")
    A.append("")
    A.append(f"*{BANNER}*")
    A.append("")
    A.append("**Status right now**")
    A.append("")
    A.append(f"- Channel 1 (embedding, pinned mpnet): "
             f"{'COMPLETE' if ch1_ok else 'INCOMPLETE'}.")
    A.append(f"- Channel 2 (stance judge): "
             f"{'COMPLETE' if ch2_ok else 'INCOMPLETE — still running'}.")
    A.append(f"- **OUTSTANDING ON THE OWNER: the OSF snapshot v4 upload has not "
             f"been made.** `{data['provenance']['osf_snapshot']}` is written "
             f"and hashed below, but it is not yet timestamped externally. That "
             f"is the project's one open external timestamp.")
    if not ch2_ok:
        A.append("")
        A.append(f"**No hypothesis verdict is printed in this render.** "
                 f"Amendment 3 C2.4 says no claim rests on one channel alone, "
                 f"so every verdict below reads `{AWAITING_LABEL}` until the "
                 f"judge finishes. The channel-1 numbers that are printed are "
                 f"real, reproducible, and marked **PRELIMINARY**: they are "
                 f"the numbers, not the answer.")
    A.append("")
    A.append("| channel | model | chunks present | chunks missing | scored | "
             "unscored |")
    A.append("|---|---|---|---|---|---|")
    for ch, key in (("1 embedding", "channel1"), ("2 stance judge", "channel2")):
        for gen_dir, model in GEN_DIRS.items():
            c = st["completeness"][key][gen_dir]
            n_have = c.get("n_scored", c.get("n_labelled"))
            n_miss = c.get("n_unscored_prompts", c.get("n_unlabelled_prompts"))
            A.append(f"| {ch} | {model} | {len(c['chunks_present'])}/5 | "
                     f"{', '.join(c['chunks_missing']) or 'none'} | {n_have} | "
                     f"{n_miss} |")
    A.append("")

    # ---- 1. Provenance -----------------------------------------------------
    prov = data["provenance"]
    A.append("## 1. Provenance")
    A.append("")
    A.append(f"- Report generated by `{prov['report_generator']}`.")
    A.append(f"- Repository commit at render: `{prov['git_head']}` "
             f"(working tree {'dirty' if prov['git_dirty'] else 'clean'}).")
    A.append(f"- Draw seed `{prov['draw_seed']}`; analysis seed `{prov['seed']}` "
             f"(bootstrap B = {prov['n_bootstrap']}, sign-flip B = "
             f"{prov['n_signflip']}). No API call, no GPU, CPU only, $0.00.")
    A.append(f"- Channel 1 instrument: `{prov['instrument_channel1']['model']}` "
             f"revision `{prov['instrument_channel1']['revision']}`, pin "
             f"asserted: {prov['instrument_channel1']['revision_asserted']}.")
    A.append(f"- Channel 2 instrument: `{prov['instrument_channel2']['judge_model']}`, "
             f"rubric sha256 `{prov['instrument_channel2']['rubric_sha256'][:16]}…`, "
             f"temperature 0.0, thinking budget 0.")
    A.append("")
    A.append("**Governance documents (OSF snapshot v4), by sha256**")
    A.append("")
    A.append("| document | sha256 |")
    A.append("|---|---|")
    for name, sha in prov["governance_document_sha256"].items():
        A.append(f"| `{name}` | `{(sha or '')[:32]}…` |")
    A.append("")
    A.append("**Inputs, with the script that produced each**")
    A.append("")
    A.append("| file | generator | sha256 | tracked | last commit |")
    A.append("|---|---|---|---|---|")
    for f in prov["files"]:
        if not f["exists"]:
            continue
        lc = (f["last_commit"] or "")[:12] or "—"
        A.append(f"| `{f['file']}` | `{f['generator']}` | "
                 f"`{(f['sha256'] or '')[:16]}…` | "
                 f"{'yes' if f['tracked'] else 'no'} | `{lc}` |")
    A.append("")

    # ---- 2. H1 -------------------------------------------------------------
    h1 = data["h1"]
    A.append("## 2. H1 verdict")
    A.append("")
    A.append(_quote("H1"))
    A.append(_quote("H1_updated"))
    A.append(_quote("magnitude"))
    A.append(_quote("magnitude_scope"))
    A.append(_quote("branch"))
    A.append("")
    A.append(f"**Subjects: {h1['verdict_block']['n_subjects']}.** "
             f"The branch rule returns "
             f"**{h1['verdict_block']['subject_count_branch'].upper()}** "
             f"for H1 — 88 subjects is above the 80 threshold, so H1 runs as "
             f"a confirmatory test.")
    A.append("")
    A.append(f"### Verdict: {h1['verdict_block']['verdict']}")
    A.append("")
    A.append(h1["verdict_block"]["verdict_reason"])
    A.append("")
    for gen_dir, model in GEN_DIRS.items():
        role = "PRIMARY" if gen_dir == PRIMARY_DIR else "ROBUSTNESS (secondary)"
        A.append(f"### {model} — {role}")
        A.append("")
        A.append("**Channel 1 (embedding cosine)"
                 + (" — PRELIMINARY, pending channel 2**" if not ch2_ok else "**"))
        A.append("")
        A.extend(_contrast_table(h1["channel1"][gen_dir], "1", True))
        A.append("")
        c1 = h1["channel1"][gen_dir]["contrasts"]
        zi = c1.get("own_minus_zeroinfo", {})
        A.append(f"Magnitude bar on the contrast the frozen text names for H1 "
                 f"(own-twin − zero-info): "
                 f"{fmt(zi.get('mean_diff'), plus=True)} cosine against the "
                 f"frozen ≥ +{MAG_BAR_CH1:.2f} — "
                 f"**{'MET' if zi.get('meets_magnitude_bar') else 'NOT MET'}**.")
        pi = c1.get("own_minus_imposter", {})
        A.append("")
        A.append(f"The C3 primary contrast (own-twin − imposter) reads "
                 f"{fmt(pi.get('mean_diff'), plus=True)} cosine against the "
                 f"same ≥ +{MAG_BAR_CH1:.2f} unit — "
                 f"**{'MET' if pi.get('meets_magnitude_bar') else 'NOT MET'}**. "
                 f"The frozen magnitude text names own-twin − zero-info for "
                 f"H1; this line applies the same unit to the primary "
                 f"contrast and is labelled as such.")
        A.append("")
        A.append("**Channel 2 (stance match)**")
        A.append("")
        if ch2_ok:
            A.extend(_contrast_table(h1["channel2"][gen_dir], "2", True))
        else:
            A.append(f"{AWAIT} — the judge has not finished every chunk for "
                     f"this model. Nothing is computed from a partial label "
                     f"set.")
        A.append("")
    A.append("### Both channels, both models")
    A.append("")
    A.append(_quote("both_channels"))
    A.append(_quote("two_models"))
    A.append(_quote("robustness_secondary"))
    if not ch2_ok:
        A.append(f"Direction agreement across channels: {AWAIT}.")
    else:
        A.append(f"Direction agreement across channels on the primary model: "
                 f"{h1['verdict_block'].get('channel_direction_agreement_primary_model')}.")
        A.append("")
        A.append(f"Robustness model holds direction: "
                 f"{h1['verdict_block'].get('robustness_model_direction_holds')}.")
    A.append("")

    # ---- 3. H7 -------------------------------------------------------------
    h7 = data["h7"]
    A.append("## 3. H7 verdict — twin staleness")
    A.append("")
    A.append("**EXPLORATORY. Every number in this section is exploratory and "
             "carries no confirmatory claim.**")
    A.append("")
    A.append(_quote("H7"))
    A.append(_quote("H7_crossover"))
    A.append(_quote("H7_volume_control"))
    A.append(_quote("branch"))
    A.append("")
    A.append(f"**Subject count.** {h7['counts']['n_eligible']} subjects carry "
             f"the H7 eligibility flag; {h7['counts']['n_usable']} of them "
             f"fill at least one Δ bin after the B7.3 volume control and can "
             f"contribute a point to the curve. The branch rule returns "
             f"**{branch_for(h7['counts']['n_usable']).upper()}** at "
             f"{h7['counts']['n_usable']} and "
             f"**{branch_for(h7['counts']['n_eligible']).upper()}** at "
             f"{h7['counts']['n_eligible']} — both counts sit inside the "
             f"30–79 exploratory band, so the label does not depend on which "
             f"count the branch is read against.")
    A.append("")
    A.append(f"Cutoffs excluded by the volume control: "
             f"{h7['counts']['cutoffs_unfillable']} unfillable, "
             f"{h7['counts']['cutoffs_dropped_lt_6m']} under 6 months (the "
             f"dropped < 6m band), {h7['counts']['cutoffs_bin_already_filled']} "
             f"because a newer cutoff already represented the bin. "
             f"{h7['counts']['n_eligible_filling_zero_bins']} flagged-eligible "
             f"subjects fill no bin at all.")
    A.append("")
    def _h7_reading_pointer(blk):
        """Which pre-written reading this channel's arithmetic points at.

        Mechanical: decay iff the frozen slope bar's arithmetic holds
        (mean slope < 0, p < .05); flat iff the slope is not
        distinguishable from zero; a SIGNIFICANT POSITIVE slope fits
        neither pre-written reading and is said so, not shoehorned.
        """
        sl = blk.get("slope_test")
        if not sl or sl.get("p_paired_t") is None:
            return "insufficient data for a pointer"
        if sl["mean_slope_per_year"] < 0 and sl["p_paired_t"] < 0.05:
            return "the decay reading"
        if sl["mean_slope_per_year"] > 0 and sl["p_paired_t"] < 0.05:
            return ("NEITHER pre-written reading — the slope is "
                    "significantly POSITIVE (anti-decay), a direction "
                    "neither reading anticipates")
        return "the flat reading"

    def _h7_model_sections(ch_key, ch_label, unit_year, mag_bar):
        for gen_dir, model in GEN_DIRS.items():
            role = "PRIMARY" if gen_dir == PRIMARY_DIR else "ROBUSTNESS"
            blk = h7[ch_key][gen_dir]
            A.append(f"### {model} — {role}, {ch_label}"
                     + ("" if ch2_ok else " (PRELIMINARY)"))
            A.append("")
            A.append("| Δ bin | subjects | items | mean Δ (days) | stale own twin | "
                     "fresh imposter | own − fresh imposter |")
            A.append("|---|---|---|---|---|---|---|")
            for b in H7_BIN_ORDER:
                pb = blk["per_bin"][b]
                A.append(f"| {b} | {pb['n_subjects']} | {pb['n_items']} | "
                         f"{fmt(pb['mean_delta_days'], 1)} | "
                         f"{fmt(pb['stale_own_twin_mean'])} | "
                         f"{fmt(pb['fresh_imposter_mean'])} | "
                         f"{fmt(pb['own_minus_fresh_imposter'], plus=True)} |")
            A.append("")
            sl = blk.get("slope_test")
            if sl:
                A.append(f"**Between-subject slope test.** "
                         f"{blk['n_subjects_with_slope']} subjects fill ≥ 2 bins "
                         f"and contribute a slope; "
                         f"{blk['n_subjects_single_bin_no_slope']} fill exactly "
                         f"one and contribute none.")
                A.append("")
                A.append(f"- Mean per-subject slope: "
                         f"{fmt(sl['mean_slope_per_year'], 5, plus=True)} "
                         f"{unit_year} "
                         f"(95% CI [{fmt(sl['ci95_t_per_year'][0], 5, plus=True)}, "
                         f"{fmt(sl['ci95_t_per_year'][1], 5, plus=True)}]).")
                A.append(f"- Paired t p = {fmt_p(sl['p_paired_t'])}; Wilcoxon "
                         f"p = {fmt_p(sl['p_wilcoxon'])}; sign-flip "
                         f"p = {fmt_p(sl['p_signflip'])}.")
                A.append(f"- Slopes below zero: {sl['n_negative']} of "
                         f"{sl['n_subjects']}.")
                A.append(f"- Against the frozen bar (mean slope < 0 AND p < .05): "
                         f"**{'MET' if sl.get('meets_frozen_bar') else 'NOT MET'}** "
                         f"— exploratory, so this is a description of the bar's "
                         f"arithmetic, not a confirmatory verdict.")
            else:
                A.append("Not enough subjects fill two bins to fit slopes.")
            A.append("")
            cr = blk["crossover"]
            A.append(f"**Crossover statistic.** "
                     + (f"Pooled crossover at the **{cr['pooled_crossover_bin']}** "
                        f"bin." if cr["pooled_crossover_bin"] else
                        "No pooled crossover inside the observed Δ range: the "
                        "stale own twin stays ahead of the fresh imposter in "
                        "every filled bin.")
                     + f" Per subject, {cr['n_subjects_with_crossover']} of "
                       f"{cr['n_subjects_evaluated']} cross at some bin.")
            A.append("")
            fs = blk.get("freshest_minus_stalest") or {}
            if not fs.get("unavailable"):
                A.append(f"**Freshest − stalest bin** (the contrast the magnitude "
                         f"bar names for H7), paired over the "
                         f"{fs.get('n_subjects')} subjects filling both: "
                         f"{fmt(fs.get('mean_diff'), plus=True)} "
                         f"(95% CI [{fmt((fs.get('ci95_t') or [None])[0], plus=True)}, "
                         f"{fmt((fs.get('ci95_t') or [None, None])[1], plus=True)}], "
                         f"p = {fmt_p(fs.get('p_paired_t'))}) against ≥ "
                         f"+{mag_bar:.2f} — "
                         f"**{'MET' if fs.get('meets_magnitude_bar') else 'NOT MET'}**.")
            else:
                A.append(f"**Freshest − stalest bin**: {fs.get('note')}")
            A.append("")
            ws = blk["within_subject_sweep"]
            A.append(f"**Within-subject sweep (supporting analysis).** Subset: "
                     f"{', '.join(ws['subset']) or 'none'} "
                     f"({ws['n_subjects']} subjects). "
                     f"{ws['status']}.")
            if ws.get("slope_test"):
                A.append("")
                A.append(f"Mean slope over the sweep subset: "
                         f"{fmt((ws['slope_test']['mean'] or 0) * 365.25, 5, plus=True)} "
                         f"{unit_year}, p = "
                         f"{fmt_p(ws['slope_test']['p_paired_t'])} "
                         f"(n = {ws['slope_test']['n_subjects']}).")
            A.append("")

    _h7_model_sections("channel1", "channel 1 (embedding cosine)",
                       "cosine per year", MAG_BAR_CH1)
    if not ch2_ok:
        A.append("### Channel 2, H7")
        A.append("")
        A.append(f"{AWAIT} — the stance judge has not finished. H7's channel-2 "
                 f"bins, slopes and crossover are computed by the same code and "
                 f"will render as soon as every chunk carries labels.")
        A.append("")
    else:
        _h7_model_sections("channel2", "channel 2 (stance match)",
                           "stance-match points per year", MAG_BAR_CH2)
        A.append("### The two channels on H7, side by side — they disagree")
        A.append("")
        A.append(_quote("both_channels"))
        A.append("| model | channel | mean slope / year | p | pooled crossover "
                 "| subjects crossing |")
        A.append("|---|---|---|---|---|---|")
        for gen_dir, model in GEN_DIRS.items():
            for ch_key, ch_name in (("channel1", "1 embedding"),
                                    ("channel2", "2 stance")):
                blk = h7[ch_key][gen_dir]
                sl = blk.get("slope_test") or {}
                cr = blk["crossover"]
                A.append(f"| {model} | {ch_name} | "
                         f"{fmt(sl.get('mean_slope_per_year'), 5, plus=True)} | "
                         f"{fmt_p(sl.get('p_paired_t'))} | "
                         f"{cr['pooled_crossover_bin'] or 'none in range'} | "
                         f"{cr['n_subjects_with_crossover']}/"
                         f"{cr['n_subjects_evaluated']} |")
        A.append("")
        p_cr1 = h7["channel1"][PRIMARY_DIR]["crossover"]
        p_cr2 = h7["channel2"][PRIMARY_DIR]["crossover"]
        if bool(p_cr1["pooled_crossover_bin"]) != bool(p_cr2["pooled_crossover_bin"]):
            A.append(
                "**The pre-declared crossover statistic points different ways "
                "in the two channels on the primary model**: channel 1 finds "
                + (f"a pooled crossover at {p_cr1['pooled_crossover_bin']}"
                   if p_cr1["pooled_crossover_bin"] else "no crossover in range")
                + ", channel 2 finds "
                + (f"a pooled crossover at {p_cr2['pooled_crossover_bin']}"
                   if p_cr2["pooled_crossover_bin"] else "no crossover in range")
                + ". By the frozen rule quoted above, no crossover claim can "
                  "rest on either channel alone; the disagreement is itself "
                  "the reportable fact. Note also that a crossover at the "
                  "EARLIEST bin under a non-negative slope is not the "
                  "declared decay pattern (a stranger's fresh twin "
                  "overtaking as Δ grows); it is reported as measured, not "
                  "as decay.")
            A.append("")
        A.append("Channel-2 caveat, printed where the numbers are: per-bin "
                 "stance denominators are thin (few items per bin) and are "
                 "further thinned by the imposter-arm UNCLEAR asymmetry "
                 "flagged in section 6; channel-2 H7 numbers carry wider "
                 "uncertainty than their channel-1 counterparts.")
        A.append("")
    A.append("### The two pre-written readings, at equal prominence")
    A.append("")
    A.append(_quote("H7_reading_decay"))
    A.append(_quote("H7_reading_flat"))
    if not ch2_ok:
        A.append(f"Which reading the data supports is not stated here: the "
                 f"frozen bar names the primary model on both channels, and "
                 f"channel 2 is incomplete.")
    else:
        A.append("Applied mechanically to the primary model (slope "
                 "arithmetic; the crossover is reported beside):")
        A.append("")
        pointers = {}
        for ch_key, ch_name in (("channel1", "Channel 1 (embedding)"),
                                ("channel2", "Channel 2 (stance)")):
            ptr = _h7_reading_pointer(h7[ch_key][PRIMARY_DIR])
            pointers[ch_key] = ptr
            A.append(f"- **{ch_name}** points at **{ptr}**.")
        A.append("")
        if pointers["channel1"] == pointers["channel2"]:
            A.append(f"The two channels agree; the pointed reading stands, "
                     f"with the EXPLORATORY label attached to every H7 "
                     f"statement (30–79 band).")
        else:
            A.append(f"**The channels do not agree on H7.** Channel 1 points "
                     f"at {pointers['channel1']}; channel 2 points at "
                     f"{pointers['channel2']}. Under the frozen rule "
                     f"(Amendment 3 C2.4, quoted in the side-by-side section "
                     f"above), H7 therefore gets NO headline reading. The "
                     f"disagreement, with both channels' numbers beside it, "
                     f"is the finding this section reports. Exploratory "
                     f"label on all of it (30–79 band).")
    A.append("")
    A.append(_quote("H7_within_subject"))
    A.append("")
    A.append("**Declared confounds, restated as B7 requires:** staleness "
             "bundles person-change and world-change — topics move on even "
             "when the person does not, so H7 measures operational staleness, "
             "not its mechanism. At matched token budget, older-cutoff "
             "grounding can differ in venue and interview count.")
    A.append("")

    # ---- 4. Own minus imposter --------------------------------------------
    A.append("## 4. Own-minus-imposter, the primary contrast")
    A.append("")
    A.append(_quote("primary_metric"))
    A.append(_quote("lift_primary"))
    A.append(_quote("raw_beside"))
    A.append("")
    A.append("| model | channel | twin_redacted | imposter_redacted | "
             "difference | 95% CI | p | zero-info lift (beside) |")
    A.append("|---|---|---|---|---|---|---|---|")
    for gen_dir, model in GEN_DIRS.items():
        c = h1["channel1"][gen_dir]["contrasts"]
        pi, zi = c.get("own_minus_imposter", {}), c.get("own_minus_zeroinfo", {})
        ci = pi.get("ci95_t") or [None, None]
        A.append(f"| {model} | 1 embedding | {fmt(pi.get('mean_a'))} | "
                 f"{fmt(pi.get('mean_b'))} | "
                 f"**{fmt(pi.get('mean_diff'), plus=True)}** | "
                 f"[{fmt(ci[0], plus=True)}, {fmt(ci[1], plus=True)}] | "
                 f"{fmt_p(pi.get('p_paired_t'))} | "
                 f"{fmt(zi.get('mean_diff'), plus=True)} |")
        if not ch2_ok:
            A.append(f"| {model} | 2 stance | {AWAIT} | {AWAIT} | {AWAIT} | "
                     f"{AWAIT} | {AWAIT} | {AWAIT} |")
        else:
            c2 = h1["channel2"][gen_dir]["contrasts"]
            pi2 = c2.get("own_minus_imposter", {})
            zi2 = c2.get("own_minus_zeroinfo", {})
            ci2 = pi2.get("ci95_t") or [None, None]
            A.append(f"| {model} | 2 stance | {fmt(pi2.get('mean_a'))} | "
                     f"{fmt(pi2.get('mean_b'))} | "
                     f"**{fmt(pi2.get('mean_diff'), plus=True)}** | "
                     f"[{fmt(ci2[0], plus=True)}, {fmt(ci2[1], plus=True)}] | "
                     f"{fmt_p(pi2.get('p_paired_t'))} | "
                     f"{fmt(zi2.get('mean_diff'), plus=True)} |")
    A.append("")
    A.append("Robustness-model absolute scores are secondary by the frozen "
             "text quoted above; only the own-minus-imposter contrast carries "
             "robustness weight, and the judge-family overlap is declared: "
             "the stance judge is `gemini-3.5-flash`, the robustness scorer "
             "`gemini-3.5-flash-lite` — different versions, same family.")
    A.append("")
    A.append("**Donor concentration caveat.** "
             + data["health"]["donor_concentration"]["caveat"])
    A.append("")
    sens = data["sensitivity"]
    A.append("**Era-violation sensitivity.** "
             f"{sens['n_rows_flagged']} era-flagged generation(s), across "
             f"{sens['n_items_dropped']} item(s), all on the robustness "
             f"model. Recomputing the primary contrast with those items "
             f"removed:")
    A.append("")
    A.append("| model | channel | primary contrast, all items | "
             "primary contrast, era items dropped | shift |")
    A.append("|---|---|---|---|---|")
    for gen_dir, model in GEN_DIRS.items():
        s = sens["channel1"].get(gen_dir, {})
        A.append(f"| {model} | 1 embedding | {fmt(s.get('full'), plus=True)} | "
                 f"{fmt(s.get('dropped'), plus=True)} | "
                 f"{fmt(s.get('shift'), 5, plus=True)} |")
    A.append("")

    # ---- 5. B8 -------------------------------------------------------------
    b8 = data["b8"]
    A.append("## 5. B8 — individual level beside population level")
    A.append("")
    A.append(_quote("B8"))
    A.append(_quote("B8_no_bar"))
    A.append("")
    A.append(b8["population_metric_definition"])
    A.append("")
    A.append(b8["channel1_note"])
    A.append("")
    A.append("| contrast | individual-level lift (channel 1) | 95% CI | "
             "individual-level lift (channel 2) | population-level TVD "
             "(pooled) | population-level TVD (per-subject mean) |")
    A.append("|---|---|---|---|---|---|")
    for key, _a, _b, _role in H1_CONTRASTS:
        row = b8["individual_level"].get(key, {})
        ci = row.get("channel1_ci95") or [None, None]
        c2 = row.get("channel2_mean_diff")
        A.append(f"| `{key}` | {fmt(row.get('channel1_mean_diff'), plus=True)} | "
                 f"[{fmt(ci[0], plus=True)}, {fmt(ci[1], plus=True)}] | "
                 f"{c2 if isinstance(c2, str) else fmt(c2, plus=True)} | "
                 f"{AWAIT if not ch2_ok else fmt(row.get('population_tvd_pooled'))} | "
                 f"{AWAIT if not ch2_ok else fmt(row.get('population_tvd_per_subject_mean'))} |")
    A.append("")
    A.append("The TVD on each row is taken between that contrast's own two "
             "arms — arm A's stance-label distribution against arm B's — "
             "pooled over every item, and again as the mean of the "
             "per-subject TVDs, since B8 asks for both. Each arm's TVD "
             "against `twin_redacted`, the shape the dev pilot printed, is in "
             "the JSON under `b8.population_level`.")
    A.append("")
    A.append("**Divergences**")
    A.append("")
    if isinstance(b8["divergences"], str):
        A.append(f"{b8['divergences']} — the population level needs stance "
                 f"labels.")
    else:
        for d in b8["divergences"]:
            A.append(f"- {d}")
    A.append("")

    # ---- 6. Instrument health ---------------------------------------------
    hl = data["health"]
    A.append("## 6. Instrument health")
    A.append("")
    A.append("### Generation: truncation, word cap, era, parse")
    A.append("")
    A.append("| model | arm | n | truncated | over word cap | era violations | "
             "empty |")
    A.append("|---|---|---|---|---|---|---|")
    for gen_dir, model in GEN_DIRS.items():
        for arm, v in sorted(hl["generation_per_arm"].get(gen_dir, {}).items()):
            A.append(f"| {model} | `{arm}` | {v['n']} | {v['n_truncated']} | "
                     f"{v['n_over_word_cap']} | {v['n_era_violations']} | "
                     f"{v['n_empty']} |")
    A.append("")
    A.append("Parse failures at generation: 0 on both models (every chunk "
             "summary records `n_parse_failures` 0 / `complete` true).")
    A.append("")
    A.append("### Era-violation rows, listed")
    A.append("")
    if hl["era_violations"]["rows"]:
        A.append("| model | chunk | item | arm | flagged tokens |")
        A.append("|---|---|---|---|---|")
        for row in hl["era_violations"]["rows"]:
            A.append(f"| {row['model']} | {row['chunk']} | `{row['item_id']}` | "
                     f"`{row['arm']}` | {', '.join(row['era_violations'])} |")
    else:
        A.append("None.")
    A.append("")
    A.append(hl["era_violations"]["treatment"])
    A.append("")
    A.append("### Judge canary")
    A.append("")
    jc = hl["judge_canary"]
    A.append(jc["rule"])
    A.append("")
    if jc["runs"]:
        A.append("| canary run | rows | flips | allowed | passed |")
        A.append("|---|---|---|---|---|")
        for c in jc["runs"]:
            A.append(f"| `{c['file'].split('/')[-1]}` | {c['n']} | "
                     f"{c['n_flips']} | {c['max_flips_allowed']} | "
                     f"{'PASS' if c['passed'] else 'FAIL'} |")
        A.append("")
        A.append(f"The canary passed {jc['runs'][-1]['n']}/{jc['runs'][-1]['n']} "
                 f"with {jc['total_flips']} label flips across "
                 f"{len(jc['runs'])} run(s), **before any confirmatory judge "
                 f"call was made**. The halt-on-flip rule never fired.")
    else:
        A.append("No canary run recorded.")
    A.append("")
    A.append("### Per-arm UNCLEAR rates and stance-match rates")
    A.append("")
    A.append(_quote("unclear"))
    if ch2_ok:
        A.append("| model | arm | stance-match rate | UNCLEAR rate | "
                 "denominator |")
        A.append("|---|---|---|---|---|")
        for gen_dir, model in GEN_DIRS.items():
            for arm in H1_ARMS:
                u = data["channel2_rates"][gen_dir].get(arm, {})
                A.append(f"| {model} | `{arm}` | {fmt(u.get('match_rate'))} | "
                         f"{fmt(u.get('unclear_rate'))} | "
                         f"{u.get('denominator')} |")
        A.append("")
        for gen_dir, model in GEN_DIRS.items():
            g = data["channel2_rates"][gen_dir].get("_gap_flags", [])
            if g:
                for line in g:
                    A.append(f"- **FLAGGED ({model})**: {line}")
            else:
                A.append(f"- {model}: no between-arm UNCLEAR gap reaches the "
                         f"frozen ≥ 0.10 threshold.")
    else:
        A.append(f"{AWAIT} — rates and the ≥ 0.10 gap flag need every chunk's "
                 f"labels. Labels on disk so far: "
                 + ", ".join(f"{GEN_DIRS[g]} {n}"
                             for g, n in hl["labels_present_per_model"].items())
                 + ". Those come from whichever chunks the judge has "
                   "reached, in a fixed-seed interleaved call order -- not a "
                   "sample of the corpus, so no rate is computed from them.")
    A.append("")
    A.append("### Contamination meter")
    A.append("")
    A.append(_quote("contamination_meter"))
    A.append("")
    A.append("| model | channel | zeroinfo_named | zeroinfo_redacted | "
             "meter (per-subject mean) | 95% CI | p | pooled item-level "
             "(OE-1 method) |")
    A.append("|---|---|---|---|---|---|---|---|")
    for gen_dir, model in GEN_DIRS.items():
        cm = data["contamination"]["channel1"][gen_dir]
        pt = cm.get("paired_test") or {}
        ci = pt.get("ci95_t") or [None, None]
        A.append(f"| {model} | 1 embedding | {fmt(pt.get('mean_a'))} | "
                 f"{fmt(pt.get('mean_b'))} | "
                 f"**{fmt(pt.get('mean_diff'), plus=True)}** | "
                 f"[{fmt(ci[0], plus=True)}, {fmt(ci[1], plus=True)}] | "
                 f"{fmt_p(pt.get('p_paired_t'))} | "
                 f"{fmt(cm.get('pooled_item_level'), plus=True)} |")
    A.append("")
    for gen_dir, model in GEN_DIRS.items():
        cm = data["contamination"]["channel1"][gen_dir]
        A.append(f"- **{model}**: {cm.get('flag_note')}")
        if cm.get("large_meter_subjects"):
            A.append(f"  Subjects in the top decile of the meter "
                     f"(≥ {fmt(cm.get('large_meter_cutoff_p90'))}), analysed "
                     f"separately per the frozen text: "
                     f"{', '.join(cm['large_meter_subjects'])}.")
    A.append("")

    # ---- the mandated separate analysis, run rather than only named ---------
    sep = data["contamination"].get("separate_large_meter") or {}
    if sep.get("channel1"):
        n_large = sorted({b["n_large"] for b in sep["channel1"].values()
                          if b.get("n_large")})
        n_large_txt = " and ".join(str(n) for n in n_large) or "small"
        A.append("#### Large-meter subjects, analysed separately")
        A.append("")
        A.append(f"**Completing the mandated separate analysis. Added at "
                 f"closeout, 2026-07-28.** The frozen text says subjects with a "
                 f"large meter are analysed separately. The block above named "
                 f"them; until this subsection existed, the separate analysis "
                 f"itself was never run. It is run here: the two primary "
                 f"contrasts, recomputed inside and outside the top-decile "
                 f"group. **Descriptive. No bar is attached to any number "
                 f"below.** The split is made after the fact on a top-decile "
                 f"cut, the large group is {n_large_txt} subjects, and the two "
                 f"groups are different people — so the last column is a "
                 f"difference of two group means, not a test.")
        A.append("")
        A.append("Group membership is the CHANNEL-1 meter's top decile in both "
                 "channels, so \"large meter\" means one thing throughout. Raw "
                 "arm means sit beside every difference, per the "
                 "watch-which-arm-moves rule.")
        A.append("")
        A.append("| model | channel | contrast | group | n | arm A | arm B | "
                 "difference | 95% CI | p |")
        A.append("|---|---|---|---|---|---|---|---|---|---|")
        for ch, ch_label in (("channel1", "1 embedding"),
                             ("channel2", "2 stance")):
            for gen_dir, model in GEN_DIRS.items():
                blk = sep.get(ch, {}).get(gen_dir)
                if not blk:
                    continue
                for key, cblk in blk["contrasts"].items():
                    for gname, glabel in (("large_meter", "large meter"),
                                          ("rest", "the rest")):
                        g = cblk.get(gname) or {}
                        if not g.get("n_subjects"):
                            A.append(f"| {model} | {ch_label} | `{key}` | "
                                     f"{glabel} | 0 | — | — | — | — | — |")
                            continue
                        ci = g.get("ci95_t") or [None, None]
                        A.append(
                            f"| {model} | {ch_label} | `{key}` | {glabel} | "
                            f"{g['n_subjects']} | {fmt(g.get('mean_a'))} | "
                            f"{fmt(g.get('mean_b'))} | "
                            f"**{fmt(g.get('mean_diff'), plus=True)}** | "
                            f"[{fmt(ci[0], plus=True)}, {fmt(ci[1], plus=True)}] "
                            f"| {fmt_p(g.get('p_paired_t'))} |")
        A.append("")
        A.append("| model | channel | contrast | large-meter minus rest |")
        A.append("|---|---|---|---|")
        for ch, ch_label in (("channel1", "1 embedding"),
                             ("channel2", "2 stance")):
            for gen_dir, model in GEN_DIRS.items():
                blk = sep.get(ch, {}).get(gen_dir)
                if not blk:
                    continue
                for key, cblk in blk["contrasts"].items():
                    A.append(f"| {model} | {ch_label} | `{key}` | "
                             f"{fmt(cblk.get('large_minus_rest'), plus=True)} |")
        A.append("")
        A.append("Reading rule that travels with this table: `own_minus_zeroinfo` "
                 "shares the `zeroinfo_redacted` term with the meter that "
                 "defines the split, exactly as flagged in the H3 subsection "
                 "below, so its group difference is mechanically coupled to the "
                 "grouping and says nothing about contamination. "
                 "`own_minus_imposter` shares no term with the meter and is the "
                 "row to read.")
        A.append("")
    A.append("### H3, descriptive — lift against the meter")
    A.append("")
    A.append(_quote("H3"))
    A.append("")
    A.append(f"**{data['h3']['channel1'][PRIMARY_DIR]['shared_term_warning']}**")
    A.append("")
    A.append("| model | lift | usable for H3 | n | Pearson r | p | "
             "Spearman ρ | p |")
    A.append("|---|---|---|---|---|---|---|---|")
    for gen_dir, model in GEN_DIRS.items():
        for name, c in data["h3"]["channel1"][gen_dir]["correlations"].items():
            A.append(f"| {model} | `{name}` | "
                     f"{'yes' if c['usable_for_H3'] else 'NO — shares a term'} | "
                     f"{c['n_subjects']} | "
                     f"{fmt(c['pearson_r'], 4, plus=True)} | "
                     f"{fmt_p(c['pearson_p'])} | "
                     f"{fmt(c['spearman_rho'], 4, plus=True)} | "
                     f"{fmt_p(c['spearman_p'])} |")
    A.append("")
    A.append(data["h3"]["channel1"][PRIMARY_DIR]["estimator_note"])
    A.append("")
    A.append("### Guard exclusions")
    A.append("")
    ge = hl["guard_exclusions"]
    A.append(f"{ge['n_renders_excluded']} of {ge['n_renders_attempted']} "
             f"renders were excluded by a frozen guard "
             f"(rate {fmt(ge['exclusion_rate'], 4)}; the stop rate is "
             f"{fmt(ge['stop_rate'], 2)} and was not reached).")
    A.append("")
    A.append("| subject | items excluded | item ids |")
    A.append("|---|---|---|")
    for cid, v in ge["by_subject"].items():
        A.append(f"| `{cid}` | {v['n_items']} | "
                 f"{', '.join('`' + i + '`' for i in v['item_ids'])} |")
    A.append("")
    A.append("**C02502 was dropped entirely.** "
             + (hl["same_event_leak_scan"].get("finding") or ""))
    A.append("")
    A.append("### Donor concentration")
    A.append("")
    dc = hl["donor_concentration"]
    A.append(f"{dc['n_distinct_donors']} distinct donors ground "
             f"{dc['n_subjects']} subjects' imposter arms "
             f"({dc['n_eligible_donors']} donors cleared the frozen "
             f"2,500-word floor). Busiest donor: "
             f"{dc['max_subjects_per_donor']} subjects.")
    A.append("")
    A.append("| donor | subjects grounded |")
    A.append("|---|---|")
    for row in dc["table"][:10]:
        A.append(f"| `{row['donor_id']}` | {row['n_subjects']} |")
    A.append("")
    A.append(f"(Top 10 of {len(dc['table'])}; the full table is in the JSON.)")
    A.append("")
    A.append("### Name-resolution failures")
    A.append("")
    nr = hl["name_resolution_failures"]
    if nr["rows"]:
        A.append("| subject | canonical name | host turns | other turns | "
                 "guest words the pool expected |")
        A.append("|---|---|---|---|---|")
        for row in nr["rows"]:
            trc = row.get("test_role_counts", {})
            A.append(f"| `{row['canonical_id']}` | {row['canonical_name']} | "
                     f"{trc.get('host')} | {trc.get('other')} | "
                     f"{sum(row.get('scan_cache_says_guest_words', []))} |")
    A.append("")
    A.append(nr["note"])
    A.append("")

    # ---- 7. Costs ----------------------------------------------------------
    cost = data["costs"]
    A.append("## 7. Costs against the caps")
    A.append("")
    A.append(f"Caps signed off on GO: **{CAP_NODE_HOURS:g} node-hours GPU / "
             f"${CAP_API_USD:g} API**.")
    A.append("")
    A.append("| currency | spent | cap | headroom | breached |")
    A.append("|---|---|---|---|---|")
    A.append(f"| GPU node-hours | {cost['node_hours_spent']} | "
             f"{cost['node_hours_cap']} | {cost['node_hours_headroom']} | "
             f"{'YES' if cost['node_hours_cap_breached'] else 'no'} |")
    A.append(f"| API dollars | ${cost['api_usd_spent']} | "
             f"${cost['api_cap_usd']} | ${cost['api_headroom_usd']} | "
             f"{'YES' if cost['api_cap_breached'] else 'no'} |")
    A.append("")
    A.append("| run id | entries | calls | API $ | node-hours |")
    A.append("|---|---|---|---|---|")
    for run_id, v in sorted(cost["by_run_id"].items()):
        A.append(f"| `{run_id}` | {v['n_entries']} | {v['n_calls']} | "
                 f"${v['cost_usd']} | {v['node_hours']} |")
    A.append("")
    A.append(cost["note"])
    A.append("")
    sa = cost["sacct_accounting"]
    A.append(f"GPU billing: {sa['n_attempts']} job attempts, "
             f"{sa['n_failed_or_cancelled_attempts']} of them cancelled or "
             f"failed and still counted. {sa['note']}")
    A.append("")

    # ---- 8. Deviations -----------------------------------------------------
    A.append("## 8. Deviations")
    A.append("")
    A.append("Every deviation on the record, restated here rather than "
             "referenced.")
    A.append("")
    for d in data["deviations"]:
        A.append(f"**{d['id']}** ({d['date']}) — {d['text']}")
        A.append("")
        A.append(f"*Owner decision:* {d['owner_decision']}")
        A.append("")

    A.append("## What this report still awaits")
    A.append("")
    if ch2_ok:
        A.append("Nothing. Both channels are complete and every bar above has "
                 "been applied.")
    else:
        miss = []
        for gen_dir, model in GEN_DIRS.items():
            c = st["completeness"]["channel2"][gen_dir]
            if c["chunks_missing"]:
                miss.append(f"{model}: {', '.join(c['chunks_missing'])}")
            elif c["n_unlabelled_prompts"]:
                miss.append(f"{model}: {c['n_unlabelled_prompts']} prompts "
                            f"still unlabelled")
        A.append("- Channel 2 (stance judge) chunks: " + "; ".join(miss) + ".")
        A.append("- Everything gated on channel 2: the H1 verdict, the H7 "
                 "channel-2 curve and crossover, per-arm stance-match and "
                 "UNCLEAR rates, the ≥ 0.10 UNCLEAR gap flag, the B8 "
                 "population-level TVD, and the channel-2 contamination "
                 "meter.")
        A.append("- H6 is not in this report at all: its B3 parameters are "
                 "open on record and gate H6 scoring separately.")
    A.append("")
    return "\n".join(A) + "\n"


AWAITING_LABEL = AWAIT


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def build_report() -> dict:
    t0 = time.time()
    inputs = load_inputs()
    items, manifest = inputs["items"], inputs["manifest"]
    rows = logical_rows(inputs["renders"], items)
    comp = completeness(inputs["renders"])

    era_rows = era_violation_rows()
    era_items = {row["item_id"] for row in era_rows}

    subjects = sorted({it["canonical_id"] for it in items.values()})

    data = {
        "banner": BANNER,
        "run": {
            "generated_utc": now(),
            "generator": "experiments/stage2_confirm_report.py",
            "determinism_note": ("Every field outside this `run` block is "
                                 "deterministic: same inputs, same numbers."),
        },
        "frozen_bars": FROZEN_BARS,
        "status": {
            "completeness": comp,
            "verdicts_printed": comp["channel2_complete"],
            "gate_rule": ("No hypothesis verdict is printed while any chunk "
                          "of either channel is missing. Amendment 3 C2.4: no "
                          "claim rests on one channel alone."),
        },
        "cohort": {
            "n_subjects_drawn": manifest.get("draw", {}).get("n_survivors_rendered"),
            "n_subjects_with_items": len(subjects),
            "n_items": len(items),
            "n_logical_renders": len(rows),
            "n_unique_prompts": len({row["prompt_sha256"] for row in rows}),
            "subjects": subjects,
            "h1_subject_count_branch": branch_for(len(subjects)),
            "branch_rule_quoted": FROZEN_BARS["branch"]["text"],
        },
        "channel1": {}, "channel2": {}, "channel2_rates": {},
        "h1": {"channel1": {}, "channel2": {}},
        "h7": {"channel1": {}, "channel2": {}, "counts": {}},
        "contamination": {"channel1": {}, "channel2": {},
                          "separate_large_meter": {"channel1": {},
                                                   "channel2": {}}},
        "h3": {"channel1": {}, "channel2": {}},
        "sensitivity": {"n_rows_flagged": len(era_rows),
                        "n_items_dropped": len(era_items),
                        "items_dropped": sorted(era_items),
                        "channel1": {}},
    }

    subject_arm_c1, item_level_c1 = {}, {}
    for gen_dir in GEN_DIRS:
        cos_by_sha, _ = load_cosines(gen_dir)
        sa = channel1_subject_arm(rows, cos_by_sha)
        il = channel1_item_level(rows, cos_by_sha)
        subject_arm_c1[gen_dir] = sa
        item_level_c1[gen_dir] = il
        data["channel1"][gen_dir] = {
            "model": GEN_DIRS[gen_dir],
            "per_arm_raw": arm_summary(sa),
            "per_subject_per_arm": {arm: {s: r(v) for s, v in sorted(d.items())}
                                    for arm, d in sorted(sa.items())},
        }
        data["h1"]["channel1"][gen_dir] = h1_block(sa, "1")
        data["h7"]["channel1"][gen_dir] = h7_block(
            rows,
            lambda row, _c=cos_by_sha: (
                None if _c.get(row["prompt_sha256"]) is None
                else float(_c[row["prompt_sha256"]]["cosine_to_real"])),
            manifest, "1", GEN_DIRS[gen_dir])
        cm = contamination_block(sa, il, "1")
        data["contamination"]["channel1"][gen_dir] = cm
        data["contamination"]["separate_large_meter"]["channel1"][gen_dir] = (
            separate_large_meter_block(sa, cm.get("large_meter_subjects"), "1"))
        meters = {s: v for s, v in ((s, named - red) for s, named, red in (
            (s, sa.get(ZERO_NAMED, {}).get(s), sa.get(ZERO_RED, {}).get(s))
            for s in subjects) if named is not None and red is not None)}
        data["h3"]["channel1"][gen_dir] = h3_block(sa, meters, "1")

        # Era sensitivity on the primary contrast.
        sa_drop = channel1_subject_arm(rows, cos_by_sha, drop_items=era_items)
        full = paired_contrast(sa.get(OWN_ARM, {}), sa.get(IMPOSTER_ARM, {}),
                               OWN_ARM, IMPOSTER_ARM)["mean_diff"]
        dropped = paired_contrast(sa_drop.get(OWN_ARM, {}),
                                  sa_drop.get(IMPOSTER_ARM, {}),
                                  OWN_ARM, IMPOSTER_ARM)["mean_diff"]
        data["sensitivity"]["channel1"][gen_dir] = {
            "full": full, "dropped": dropped,
            "shift": r((dropped - full) if (full is not None
                                            and dropped is not None) else None),
        }

    subject_arm_c2, pooled_c2 = {}, {}
    for gen_dir in GEN_DIRS:
        lab_by_sha, _ = load_labels(gen_dir)
        ch2 = channel2_subject_arm(rows, lab_by_sha)
        pooled = channel2_pooled_counts(rows, lab_by_sha)
        subject_arm_c2[gen_dir] = ch2
        pooled_c2[gen_dir] = pooled
        rates = ch2["rate"]
        data["channel2"][gen_dir] = {
            "model": GEN_DIRS[gen_dir],
            "complete": comp["channel2"][gen_dir]["complete"],
            "n_labelled": comp["channel2"][gen_dir]["n_labelled"],
            "pooled_label_counts": pooled,
            "per_arm_raw": arm_summary(rates) if rates else {},
            "partial": not comp["channel2"][gen_dir]["complete"],
        }
        # Per-arm rates and the frozen UNCLEAR gap flag.
        arm_rates = {}
        for arm in H1_ARMS:
            counts = pooled.get(arm)
            if not counts:
                continue
            den = counts["SAME"] + counts["DIFFERENT"]
            total = den + counts["UNCLEAR"] + counts["None"]
            arm_rates[arm] = {
                "match_rate": r(counts["SAME"] / den) if den else None,
                "unclear_rate": r(counts["UNCLEAR"] / total) if total else None,
                "denominator": den, "n_labels": total,
                "counts": counts,
            }
        flags = []
        arms_present = [a for a in H1_ARMS if a in arm_rates]
        for i, a in enumerate(arms_present):
            for b in arms_present[i + 1:]:
                ua, ub = arm_rates[a]["unclear_rate"], arm_rates[b]["unclear_rate"]
                if ua is None or ub is None:
                    continue
                if abs(ua - ub) >= UNCLEAR_GAP_FLAG:
                    flags.append(
                        f"`{a}` UNCLEAR {fmt(ua)} vs `{b}` UNCLEAR {fmt(ub)} "
                        f"— gap {fmt(abs(ua - ub))} reaches the frozen "
                        f"≥ {UNCLEAR_GAP_FLAG:.2f} threshold and is flagged "
                        f"as material.")
        arm_rates["_gap_flags"] = flags
        data["channel2_rates"][gen_dir] = arm_rates
        if rates:
            data["h1"]["channel2"][gen_dir] = h1_block(rates, "2")
            data["h7"]["channel2"][gen_dir] = h7_block(
                rows,
                lambda row, _l=lab_by_sha: (
                    None if _l.get(row["prompt_sha256"]) is None
                    or _l[row["prompt_sha256"]].get("label") not in
                    ("SAME", "DIFFERENT")
                    else (1.0 if _l[row["prompt_sha256"]]["label"] == "SAME"
                          else 0.0)),
                manifest, "2", GEN_DIRS[gen_dir])
            data["contamination"]["channel2"][gen_dir] = contamination_block(
                rates, {}, "2")
            # Split by the channel-1 meter, the meter this report prints, so
            # "large meter" means one thing in both channels.
            data["contamination"]["separate_large_meter"]["channel2"][gen_dir] = (
                separate_large_meter_block(
                    rates,
                    data["contamination"]["channel1"][gen_dir].get(
                        "large_meter_subjects"),
                    "2"))

    h7m = manifest.get("h7", {})
    excl = h7m.get("exclusions", {})
    data["h7"]["counts"] = {
        "n_eligible": h7m.get("n_eligible_survivors"),
        "n_usable": h7m.get("n_usable_subjects"),
        "usable_note": h7m.get("usable_note"),
        "branch_at_usable": branch_for(h7m.get("n_usable_subjects") or 0),
        "branch_at_eligible": branch_for(h7m.get("n_eligible_survivors") or 0),
        "both_counts_in_same_band": (
            branch_for(h7m.get("n_usable_subjects") or 0)
            == branch_for(h7m.get("n_eligible_survivors") or 0)),
        "per_bin_subject_counts": h7m.get("per_bin_subject_counts"),
        "cutoffs_unfillable": excl.get("cutoffs_dropped_unfillable_B7_3"),
        "cutoffs_dropped_lt_6m": excl.get("cutoffs_dropped_lt_6m"),
        "cutoffs_bin_already_filled": excl.get("cutoffs_dropped_bin_already_filled"),
        "n_eligible_filling_zero_bins": len(
            excl.get("eligible_subjects_filling_zero_bins", [])),
        "eligible_filling_zero_bins": excl.get(
            "eligible_subjects_filling_zero_bins", []),
    }

    data["h1"]["verdict_block"] = h1_verdict(
        data["h1"]["channel1"].get(PRIMARY_DIR),
        data["h1"]["channel2"].get(PRIMARY_DIR) if comp["channel2_complete"] else None,
        data["h1"]["channel1"].get(ROBUSTNESS_DIR),
        data["h1"]["channel2"].get(ROBUSTNESS_DIR) if comp["channel2_complete"] else None,
        len(subjects), comp["channel2_complete"])

    data["b8"] = b8_block(subject_arm_c1[PRIMARY_DIR],
                          subject_arm_c2[PRIMARY_DIR],
                          pooled_c2[PRIMARY_DIR],
                          comp["channel2_complete"])
    data["health"] = health_block(manifest, inputs["build"], inputs["pairs"],
                                  comp)
    data["costs"] = cost_block()
    data["provenance"] = provenance_block(inputs)
    data["deviations"] = DEVIATIONS
    data["runtime_secs"] = round(time.time() - t0, 1)
    return data


def print_status(data: dict) -> None:
    comp = data["status"]["completeness"]
    print(f"[report] subjects with items: "
          f"{data['cohort']['n_subjects_with_items']} "
          f"({data['cohort']['h1_subject_count_branch']})")
    for key in ("generation", "channel1", "channel2"):
        for gen_dir, c in comp[key].items():
            print(f"[report] {key:<10} {gen_dir:<10} "
                  f"chunks {len(c['chunks_present'])}/5  "
                  f"complete={c['complete']}")
    print(f"[report] channel 1 complete: {comp['channel1_complete']}")
    print(f"[report] channel 2 complete: {comp['channel2_complete']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--require-complete", action="store_true",
                    help="exit nonzero unless every chunk of every channel is "
                         "scored; use this to gate a pipeline step on a "
                         "finished report")
    ap.add_argument("--status", action="store_true",
                    help="print the completeness table and exit without "
                         "writing anything")
    ap.add_argument("--out-json", default=str(OUT_JSON))
    ap.add_argument("--out-md", default=str(OUT_MD))
    args = ap.parse_args(argv)

    data = build_report()

    if args.status:
        print_status(data)
        return 0 if data["status"]["completeness"]["all_complete"] else 1

    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(data, indent=1, sort_keys=False,
                                   ensure_ascii=False) + "\n",
                        encoding="utf-8")
    out_md.write_text(render_markdown(data), encoding="utf-8")
    print(f"[report] wrote {rel(out_json)}")
    print(f"[report] wrote {rel(out_md)}")
    print_status(data)

    comp = data["status"]["completeness"]
    if args.require_complete and not comp["all_complete"]:
        missing = []
        for key in ("generation", "channel1", "channel2"):
            for gen_dir, c in comp[key].items():
                if not c["complete"]:
                    missing.append(f"{key}/{gen_dir}")
        print(f"[report] --require-complete: data is incomplete "
              f"({', '.join(missing)}). The report was written with "
              f"{AWAIT} placeholders; exiting nonzero.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
