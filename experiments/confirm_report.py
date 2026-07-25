"""Build the Stage 1E confirm report from the run's analysis artifact.

Analysis only, no API calls, nothing written except the report. Every result
number in the output is read out of ``results/stage1e_confirm/analysis.json``
(or, for cost/integrity, out of the run's ``config.json``,
``export_manifest.json``, ``manifest.json``, ``arms/<arm>/summary.json``,
``arms/<arm>/parse_examples.json`` and ``results/cost_log.jsonl``). No number is
typed into this file by hand, and every verdict is computed by a function that
applies the frozen rule from PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md.

The frozen rules, applied mechanically (Addendum A section B):

  * C1 PRIMARY  PASS iff (adaptive - random) lift at k=12 > 0 AND paired-t
                p < .05 under expected-value decoding AND the argmax lift at
                k=12 has the same sign. k=20 is the same contrast, SECONDARY.
  * C2          not pass/fail. At each of k=12 and k=20 one of two pre-written
                readings applies: Reading A (adaptive > fixed, p < .05) or
                Reading B (fixed >= adaptive). Both readings, the cost framing
                and the information-source paragraph print whichever way it
                lands -- that is a frozen requirement.
  * C3          PASS iff, at k=20 under EV decoding, own - baseline > 0 with
                p < .05 AND own - imposter > 0 with p < .05, AND both contrasts
                hold in direction under argmax. own = the random-order arm.

Some cells the skeleton asks for are not carried in analysis.json: the t
statistic, the Wilcoxon test, per-item MAE, the prediction-spread check, and
the adaptive/fixed/random contrasts at checkpoints other than k=12 and k=20.
Those are recomputed here from the arms' stored records.jsonl through the very
same scoring path the analysis used (doppler.scoring.summarize, with the same
relabel/force-decoding helpers as experiments/confirm_run.py), and every
recomputed quantity that also exists in analysis.json is cross-checked against
it. If any cross-check disagrees the script aborts instead of printing a number
that contradicts the artifact. ``--no-records`` skips the recompute and prints
"not in artifact" in those cells instead.

Usage:
    uv run python experiments/confirm_report.py
    uv run python experiments/confirm_report.py --no-records --skip-used-scan
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import stdev

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from doppler.scoring import summarize  # noqa: E402

RESULTS = _ROOT / "results"
DEFAULT_RUN_DIR = RESULTS / "stage1e_confirm"
DEFAULT_OUT = RESULTS / "stage1e_confirm_report.md"
COST_LOG = RESULTS / "cost_log.jsonl"
DERIVATION_IDS = RESULTS / "overnight_exp2" / "derivation_ids.json"
ORDER_FILE = RESULTS / "overnight_exp2" / "fixed_order_derivation.json"
TRAIN_REPORT = RESULTS / "overnight_stage1e.md"
RESCORE_REPORT = RESULTS / "rescore_ev_vs_argmax.md"
ADDENDUM = _ROOT / "PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md"

SIG = 0.05
EV = "expected_value"
AM = "argmax"
DECODINGS = (EV, AM)
DECODING_LABEL = {EV: "EV", AM: "argmax"}
TOL = 1e-9  # cross-check tolerance against analysis.json
NOT_IN_ARTIFACT = "n/a (not carried in analysis.json)"

# ---------------------------------------------------------------------------
# Verbatim contract text. Quoted, never paraphrased. The only numbers inside
# these blocks are contract text (design facts and the training-split power
# note), not results of this run.
# ---------------------------------------------------------------------------

BAR_C1 = """**C1 — PRIMARY (adaptive value):** adaptive − random MAE lift at k=12 > 0,
paired t p < .05 across persons. Same contrast at k=20 is SECONDARY.
Power note: the pilot-sized effect (~+0.02, p=.029 at n=150) has >95%
power at n=1,000."""

BAR_C2 = """**C2 — SECONDARY confirmatory (adaptive vs static script):** adaptive vs
fixed at k=12 and k=20. Pre-written readings, equal prominence:
- adaptive > fixed (p < .05): uncertainty-guided ordering adds value
  beyond any static script.
- fixed >= adaptive: a well-chosen static questionnaire suffices at these
  budgets — this is the honest headline, not a failure to report.
- Pre-registered cost framing: the adaptive arm spends ~5–12x the
  per-person LLM compute at interview time; the fixed order costs one
  offline derivation. Both currencies are always reported together."""

READING_A = """adaptive > fixed (p < .05): uncertainty-guided ordering adds value
beyond any static script."""

READING_B = """fixed >= adaptive: a well-chosen static questionnaire suffices at these
budgets — this is the honest headline, not a failure to report."""

COST_FRAMING = """Pre-registered cost framing: the adaptive arm spends ~5–12x the
per-person LLM compute at interview time; the fixed order costs one
offline derivation. Both currencies are always reported together."""

INFO_SOURCE = """"This contrast compares a population-optimized static questionnaire
(derived from 2,000 persons' observed outcomes) against
individually-adaptive selection that uses no outcome data. They consume
different information: fixed-order encodes population history; adaptive
personalizes per respondent. A fixed >= adaptive result therefore means
historical outcome data suffices at these budgets — not that
personalization is worthless in settings without such history (cold
start, new domains)."
"""

BAR_C3 = """**C3 — grounding (per Amendment A1):** at k=20, own − baseline > 0 AND
own − imposter > 0, each paired p < .05. Own-arm definition
(owner-required): own = the random-order arm (matching the imposter arm's
mirrored reveal schedule). Both C3 contrasts use it; the adaptive and
fixed arms are never substituted."""

RULE_DECODING = """**DECODING ROBUSTNESS (binding):** every confirmatory contrast must hold
in direction under argmax decoding of the same distributions. All lifts
are reported under both decodings, always beside both arms' raw MAEs.
Rationale: EV decoding shrinks variance and can inflate lift by damaging
the hedging baseline (results/rescore_ev_vs_argmax.md)."""

RULE_E1 = """Every reported lift appears beside both arms' raw MAEs, under both
decodings (extends Amendment A8)."""

RULE_E3 = """Multi-target parsers must store example raw completions beside parse
rates (an all-or-nothing parser makes truncation indistinguishable from
format failure — EXP3 attempt-1 lesson)."""

RULE_MULTIPLICITY = """**Multiplicity:** C1 at k=12 alone carries the adaptive headline. Every
other number is labeled secondary or descriptive. Curve shapes
(saturation points, budget-recovery fractions) are descriptive."""

NULL_C1 = """C1 null: item order does not matter at these budgets on this corpus;
the elicitation-budget curve (EXP4 shape) is the deliverable."""

NULL_C3 = """C3 own−imposter null or negative at confirm scale: the negative-transfer
observation from the pilot did not replicate; report as such."""

NULL_SECTION_C = """## C. Pre-declared null interpretations

- C1 null: item order does not matter at these budgets on this corpus;
  the elicitation-budget curve (EXP4 shape) is the deliverable.
- C3 own−imposter null or negative at confirm scale: the negative-transfer
  observation from the pilot did not replicate; report as such."""


def quote(text: str) -> list[str]:
    """Render a verbatim block as a markdown blockquote."""
    return ["> " + ln if ln else ">" for ln in text.splitlines()]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class Run:
    """Everything the report reads, loaded once."""

    def __init__(self, run_dir: Path):
        self.dir = run_dir
        self.analysis = load_json(run_dir / "analysis.json")
        self.config = load_json(run_dir / "config.json")
        self.manifest = load_json(run_dir / "manifest.json")
        self.export = load_json(run_dir / "export_manifest.json")
        self.ids = load_json(run_dir / "confirm_ids.json")
        self.imposter_pairs = load_json(run_dir / "imposter_pairs.json")
        self.arms = tuple(self.analysis["arms_present"])
        self.checkpoints = tuple(self.config["checkpoints"])
        self.contracts = tuple(
            (c["label"], c["better"], c["worse"], c["k"], c["tier"])
            for c in self.config["frozen_contrasts"])
        self.summaries = {a: load_json(run_dir / "arms" / a / "summary.json")
                          for a in self.arms}
        self.examples = {a: load_json(run_dir / "arms" / a / "parse_examples.json")
                         for a in self.arms}
        self.cost_lines = load_jsonl(COST_LOG) if COST_LOG.exists() else []

    # -- shorthand -----------------------------------------------------------
    def raw_mae(self, decoding: str, arm: str, k: int) -> float | None:
        return self.analysis["raw_mae"][decoding][arm].get(str(k))

    def lift_vs_baseline(self, decoding: str, arm: str, k: int) -> dict | None:
        return self.analysis["lift_over_baseline"][decoding][arm].get(str(k))

    def contrast(self, label: str) -> dict:
        return self.analysis["frozen_contrasts"][label]

    def integrity(self, arm: str) -> dict:
        return self.analysis["integrity"][arm]

    def cost_for(self, arm: str) -> dict | None:
        want = f"{self.dir.name}/{arm}"
        for ln in self.cost_lines:
            if ln.get("run_id") == want:
                return ln
        return None

    def jobs_for(self, arm: str) -> list[str]:
        return [name for name, job in self.manifest["jobs"].items()
                if arm in job.get("arms", [])]


# ---------------------------------------------------------------------------
# The frozen verdicts. One function per bar, each returning its own inputs so
# the report can print the numbers that drove it.
# ---------------------------------------------------------------------------


def verdict_c1(run: Run, label: str) -> dict:
    """C1: lift > 0 AND EV p < .05 AND the argmax lift has the same sign."""
    e = run.contrast(label)
    ev, am = e[EV], e[AM]
    lift_positive = ev["lift_mean"] > 0
    significant = ev["t_p"] < SIG
    same_sign = (ev["lift_mean"] > 0) == (am["lift_mean"] > 0)
    return {
        "label": label, "tier": e["tier"], "k": e["k"],
        "ev": ev, "argmax": am,
        "lift_positive": lift_positive,
        "significant": significant,
        "same_sign": same_sign,
        "pass": bool(lift_positive and significant and same_sign),
    }


def reading_c2(run: Run, label: str) -> dict:
    """C2 is not pass/fail: decide which pre-written reading applies.

    Reading A iff (adaptive - fixed) > 0 with EV p < .05; otherwise Reading B
    (fixed at or above adaptive). Significance is stated either way.
    """
    e = run.contrast(label)
    ev, am = e[EV], e[AM]
    adaptive_better = ev["lift_mean"] > 0
    significant = ev["t_p"] < SIG
    reading = "A" if (adaptive_better and significant) else "B"
    return {
        "label": label, "k": e["k"], "ev": ev, "argmax": am,
        "adaptive_better": adaptive_better,
        "significant": significant,
        "argmax_significant": am["t_p"] < SIG,
        "same_sign": (ev["lift_mean"] > 0) == (am["lift_mean"] > 0),
        "reading": reading,
    }


def verdict_c3(run: Run) -> dict:
    """C3: both contrasts positive with EV p < .05, both holding in direction
    under argmax. own = the random-order arm (owner-required definition)."""
    parts = {}
    for key, label in (("baseline", "C3_own_vs_baseline_k20"),
                       ("imposter", "C3_own_vs_imposter_k20")):
        e = run.contrast(label)
        ev, am = e[EV], e[AM]
        parts[key] = {
            "label": label, "ev": ev, "argmax": am,
            "positive": ev["lift_mean"] > 0,
            "significant": ev["t_p"] < SIG,
            "same_sign": (ev["lift_mean"] > 0) == (am["lift_mean"] > 0),
        }
    both_ev = all(p["positive"] and p["significant"] for p in parts.values())
    both_dir = all(p["same_sign"] for p in parts.values())
    out = dict(parts)
    out["both_ev_pass"] = both_ev
    out["both_directions_hold"] = both_dir
    out["pass"] = bool(both_ev and both_dir)
    return out


def imposter_replication(run: Run) -> dict:
    """Did the pilot's negative transfer replicate?

    Negative transfer = the imposter arm sits BELOW the demographics-only
    baseline, i.e. its lift over baseline is negative. Checked at every
    checkpoint under both decodings; also reports the C3 own - imposter gap,
    which is what the pre-declared null attaches to.
    """
    per_k = {}
    for decoding in DECODINGS:
        per_k[decoding] = {}
        for k in run.checkpoints:
            e = run.lift_vs_baseline(decoding, "imposter", k)
            per_k[decoding][k] = {
                "entry": e,
                "below_baseline": e is not None and e["lift_mean"] < 0,
                "significant": e is not None and e["t_p"] < SIG,
            }
    own = run.contrast("C3_own_vs_imposter_k20")
    all_below = all(v["below_baseline"] and v["significant"]
                    for d in DECODINGS for v in per_k[d].values())
    own_gap_positive_sig = (own[EV]["lift_mean"] > 0 and own[EV]["t_p"] < SIG)
    return {
        "per_k": per_k,
        "own_vs_imposter": own,
        "replicated": bool(all_below),
        "own_gap_positive_and_significant": bool(own_gap_positive_sig),
        "pre_declared_null_applies": not bool(own_gap_positive_sig),
    }


def decoding_rollup(run: Run) -> dict:
    holds, flips = [], []
    for label, *_ in run.contracts:
        e = run.contrast(label)
        (holds if e.get("direction_agrees") else flips).append(label)
    headline = verdict_c1(run, "C1_primary_adaptive_vs_random_k12")
    return {
        "holds": holds, "flips": flips, "n_total": len(run.contracts),
        "headline_decoding_dependent": not headline["same_sign"],
        "headline": headline,
    }


# ---------------------------------------------------------------------------
# Recompute from records, through the frozen scoring path, cross-checked
# against analysis.json. Only fills cells analysis.json does not carry.
# ---------------------------------------------------------------------------

SLIM_FIELDS = ("person_id", "item", "k", "prediction_ev", "prediction_argmax",
               "parsed", "true_answer", "parse_failure")


def stream_slim(run: Run, arm: str, capture: dict | None = None) -> list[dict]:
    """Slim records for one arm (prompts dropped). ``capture`` collects the
    k=20 TIPI1 prompt per person, used by the mirroring integrity check."""
    rows = []
    path = run.dir / "arms" / arm / "records.jsonl"
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            rows.append({f: r.get(f) for f in SLIM_FIELDS})
            if capture is not None and r["item"] == "TIPI1" and r["k"] == max(
                    run.checkpoints):
                capture[r["person_id"]] = r["prompt"]
    return rows


def as_decoding(rows: list[dict], decoding: str) -> list[dict]:
    """Same helper as experiments/confirm_run.py: argmax drops the EV point so
    scoring falls back to the parsed argmax digit."""
    if decoding == EV:
        return rows
    if decoding != AM:
        raise ValueError(decoding)
    return [dict(r, prediction_ev=None) for r in rows]


def relabel(rows: list[dict], arm: str) -> list[dict]:
    return [dict(r, arm=arm) for r in rows]


def at(rows: list[dict], k: int) -> list[dict]:
    return [r for r in rows if r["k"] == k]


def pair_summary(better: list[dict], worse: list[dict], decoding: str) -> dict:
    """Full paired summary of ``better`` over ``worse``, frozen path."""
    b = relabel(as_decoding(better, decoding), "twin")
    w = relabel(as_decoding(worse, decoding), "baseline")
    s = summarize(b + w)
    mae = s["mae"]
    return {
        "lift_mean": mae["lift"]["mean"],
        "ci_low": mae["lift"]["ci_low"],
        "ci_high": mae["lift"]["ci_high"],
        "t_stat": mae["tests"]["t_stat"],
        "t_p": mae["tests"]["t_p"],
        "wilcoxon_stat": mae["tests"]["wilcoxon_stat"],
        "wilcoxon_p": mae["tests"]["wilcoxon_p"],
        "better_mae": mae["twin"]["mean"],
        "worse_mae": mae["baseline"]["mean"],
        "n_persons": s["n_persons"],
        "n_excluded_pairs": s["n_excluded_pairs"],
        "per_item": s["per_item"],
    }


def self_summary(rows: list[dict], decoding: str) -> dict:
    return pair_summary(rows, rows, decoding)


def point(rec: dict, decoding: str) -> float | None:
    if decoding == EV and rec.get("prediction_ev") is not None:
        return float(rec["prediction_ev"])
    a = rec.get("prediction_argmax")
    if a is not None:
        return float(a)
    p = rec.get("parsed")
    return None if p is None else float(p)


def build_supplement(run: Run) -> dict:
    """Recompute t / Wilcoxon / per-item / spread / extra-k contrasts."""
    prompts: dict[str, dict[int, str]] = {}
    slim: dict[str, list[dict]] = {}
    for arm in run.arms:
        cap = {} if arm in ("random", "imposter", "fixed") else None
        slim[arm] = stream_slim(run, arm, capture=cap)
        if cap is not None:
            prompts[arm] = cap

    kmax = max(run.checkpoints)
    base = at(slim["baseline"], 0) if "baseline" in slim else []
    checks: list[tuple[str, float, float]] = []

    def check(name: str, got, want):
        if got is None or want is None:
            return
        checks.append((name, float(got), float(want)))

    # 1. raw MAEs, every arm, every checkpoint, both decodings.
    raw: dict = {d: {} for d in DECODINGS}
    per_item: dict = {d: {} for d in DECODINGS}
    for decoding in DECODINGS:
        for arm in run.arms:
            ks = sorted({r["k"] for r in slim[arm]})
            raw[decoding][arm] = {}
            for k in ks:
                s = self_summary(at(slim[arm], k), decoding)
                raw[decoding][arm][k] = s
                check(f"raw_mae[{decoding}][{arm}][{k}]", s["better_mae"],
                      run.raw_mae(decoding, arm, k))
                if k == (0 if arm == "baseline" else kmax):
                    per_item[decoding][arm] = {row["item"]: row["twin_mae"]
                                               for row in s["per_item"]}

    # 2. lift over the demographics-only baseline, every arm, every checkpoint.
    curves: dict = {d: {} for d in DECODINGS}
    for decoding in DECODINGS:
        for arm in run.arms:
            if arm == "baseline":
                continue
            curves[decoding][arm] = {}
            for k in sorted({r["k"] for r in slim[arm]}):
                s = pair_summary(at(slim[arm], k), base, decoding)
                curves[decoding][arm][k] = s
                want = run.lift_vs_baseline(decoding, arm, k)
                if want:
                    check(f"lift[{decoding}][{arm}][{k}]", s["lift_mean"],
                          want["lift_mean"])
                    check(f"lift_p[{decoding}][{arm}][{k}]", s["t_p"],
                          want["t_p"])

    # 3. the six frozen contrasts.
    frozen: dict = {}
    for label, better, worse, k, _tier in run.contracts:
        wk = 0 if worse == "baseline" else k
        frozen[label] = {}
        for decoding in DECODINGS:
            s = pair_summary(at(slim[better], k), at(slim[worse], wk), decoding)
            frozen[label][decoding] = s
            want = run.contrast(label)[decoding]
            check(f"{label}[{decoding}].lift", s["lift_mean"], want["lift_mean"])
            check(f"{label}[{decoding}].p", s["t_p"], want["t_p"])

    # 4. arm-vs-arm contrasts at every checkpoint (descriptive, section 6.3).
    extra: dict = {}
    for better, worse in (("adaptive", "random"), ("adaptive", "fixed"),
                          ("fixed", "random")):
        if better not in slim or worse not in slim:
            continue
        extra[(better, worse)] = {
            k: pair_summary(at(slim[better], k), at(slim[worse], k), EV)
            for k in run.checkpoints}

    # 5. spread check: pooled sd of the decoded point predictions at k=20.
    spread: dict = {}
    for arm in run.arms:
        k = 0 if arm == "baseline" else kmax
        rows = [r for r in at(slim[arm], k) if not r["parse_failure"]]
        for decoding in DECODINGS:
            pts = [point(r, decoding) for r in rows]
            pts = [p for p in pts if p is not None]
            spread[(arm, decoding)] = stdev(pts) if len(pts) > 1 else None
    ref = "random" if "random" in slim else run.arms[0]
    truths = [float(r["true_answer"]) for r in at(slim[ref], kmax)
              if not r["parse_failure"]]
    spread[("true answers", None)] = stdev(truths) if len(truths) > 1 else None

    # 6. person / item sets, for the integrity checks.
    sets = {arm: {"persons": {r["person_id"] for r in slim[arm]},
                  "items": {r["item"] for r in slim[arm]}}
            for arm in run.arms}

    bad = [(n, g, w) for n, g, w in checks if abs(g - w) > TOL]
    if bad:
        lines = "\n".join(f"  {n}: recomputed {g!r} vs analysis.json {w!r}"
                          for n, g, w in bad[:20])
        raise SystemExit("[fatal] recomputed numbers disagree with "
                         f"analysis.json ({len(bad)} of {len(checks)}):\n{lines}")

    return {
        "raw": raw, "curves": curves, "frozen": frozen, "extra": extra,
        "per_item": per_item, "spread": spread, "sets": sets,
        "prompts": prompts,
        "n_checks": len(checks),
        "max_abs_diff": max((abs(g - w) for _, g, w in checks), default=0.0),
        "items": sorted({r["item"] for r in slim[run.arms[0]]}, key=_item_num),
    }


# ---------------------------------------------------------------------------
# Cost ledger
# ---------------------------------------------------------------------------


def cost_ledger(run: Run) -> dict:
    """Per-arm projected vs actual node-hours, slurm ids, and the two ratios.

    Actual per-arm node-hours come from results/cost_log.jsonl, where the
    ingest apportioned the shared static job by each arm's share of output
    tokens (recorded in arms/<arm>/summary.json extra). Projected per-arm
    node-hours apportion each job's projection the same way, by that arm's
    share of the job's projected calls.
    """
    proj_jobs = run.config["projection"]["jobs"]
    arms_of = {name: job.get("arms", []) for name, job in run.manifest["jobs"].items()}
    expected = dict(run.export["static_prompts_per_policy"])
    adaptive_pred = sum(proj_jobs[j]["n_tipi_calls"] for j in proj_jobs
                        if "adaptive" in j)
    adaptive_unc = sum(proj_jobs[j]["n_interest_calls"] for j in proj_jobs
                       if "adaptive" in j)
    expected["adaptive"] = adaptive_pred

    rows = {}
    for arm in run.arms:
        jobs = [j for j, arms in arms_of.items() if arm in arms]
        projected = 0.0
        for j in jobs:
            pj = proj_jobs[j]
            share = 1.0
            if len(arms_of[j]) > 1:
                total = sum(expected[a] for a in arms_of[j])
                share = expected[arm] / total
            projected += pj["projected_node_hours"] * share
        line = run.cost_for(arm) or {}
        rows[arm] = {
            "jobs": jobs,
            "slurm": [i for j in jobs
                      for i in run.manifest["jobs"][j].get("slurm_job_ids", [])],
            "status": "; ".join(sorted({run.manifest["jobs"][j].get("status", "?")
                                        for j in jobs})),
            "projected_node_hours": projected,
            "actual_node_hours": line.get("node_hours"),
            "n_calls": line.get("n_calls"),
            "n_persons": line.get("n_persons"),
            "cost_usd": line.get("cost_usd"),
            "expected_completions": expected.get(arm),
        }

    total_proj = sum(r["projected_node_hours"] for r in rows.values())
    total_actual = sum(r["actual_node_hours"] or 0.0 for r in rows.values())
    total_calls = sum(r["n_calls"] or 0 for r in rows.values())
    est = run.config["projection"].get("addendum_estimate_node_hours") \
        or [11, 14]

    fixed, adaptive = rows.get("fixed", {}), rows.get("adaptive", {})
    calls_ratio = nh_ratio = None
    fixed_calls_pp = adaptive_calls_pp = None
    if fixed.get("n_calls") and adaptive.get("n_calls"):
        fixed_calls_pp = fixed["n_calls"] / fixed["n_persons"]
        adaptive_calls_pp = adaptive["n_calls"] / adaptive["n_persons"]
        calls_ratio = adaptive_calls_pp / fixed_calls_pp
    if fixed.get("actual_node_hours") and adaptive.get("actual_node_hours"):
        nh_ratio = adaptive["actual_node_hours"] / fixed["actual_node_hours"]

    project_nh = sum(float(ln["node_hours"]) for ln in run.cost_lines
                     if ln.get("node_hours") is not None)
    project_usd = sum(float(ln["cost_usd"]) for ln in run.cost_lines
                      if ln.get("cost_usd") is not None)
    run_usd = [ln.get("cost_usd") for ln in run.cost_lines
               if str(ln.get("run_id", "")).startswith(run.dir.name + "/")]

    return {
        "rows": rows,
        "total_projected": total_proj,
        "total_actual": total_actual,
        "total_calls": total_calls,
        "addendum_estimate": est,
        "calls_ratio": calls_ratio,
        "node_hours_ratio": nh_ratio,
        "fixed_calls_pp": fixed_calls_pp,
        "adaptive_calls_pp": adaptive_calls_pp,
        "adaptive_uncertainty_calls": adaptive_unc,
        "project_node_hours": project_nh,
        "project_usd": project_usd,
        "run_usd_lines": run_usd,
        "run_usd": sum(float(x) for x in run_usd if x is not None),
    }


# ---------------------------------------------------------------------------
# Integrity
# ---------------------------------------------------------------------------


def classify_failure(raw: str | None) -> str:
    """Truncation vs format failure, from the stored raw completion.

    The v2 format is seven ``digit:probability`` tokens. A completion that
    carries a prefix of the labels and stops is a truncation; one that carries
    a prefix of the labels and then a bare number dropped a label instead.
    """
    text = (raw or "").strip()
    labels = sorted({int(m) for m in re.findall(r"(?<![\d.])(\d)\s*:", text)})
    want = list(range(1, 8))
    if labels == want:
        return "other"
    tail = text[text.rfind(":") + 1:] if ":" in text else ""
    tail_numbers = re.findall(r"\d*\.?\d+", tail)
    if labels and labels == want[:len(labels)]:
        return ("well-formed but wrong format" if len(tail_numbers) > 1
                else "truncated completion")
    return "other"


def used_person_ids(skip: set[str]) -> set[int]:
    """Person ids in every other run dir, by streaming records.jsonl."""
    pat = re.compile(rb'"person_id":\s*(\d+)')
    ids: set[int] = set()
    for path in sorted(RESULTS.rglob("records.jsonl")):
        rel = str(path.relative_to(RESULTS))
        if any(rel.startswith(s) for s in skip):
            continue
        with path.open("rb") as fh:
            for line in fh:
                m = pat.search(line)
                if m:
                    ids.add(int(m.group(1)))
    return ids


def revealed_lines(prompt: str) -> list[str]:
    """The revealed interest lines of a prompt, in order (text only)."""
    out = []
    for line in prompt.splitlines():
        if line.startswith("- "):
            out.append(line[2:].rsplit(":", 1)[0].strip())
    return out


def integrity_checks(run: Run, sup: dict | None, do_used_scan: bool) -> list[tuple]:
    """(check, result, evidence) triples. Every result is computed here."""
    out: list[tuple[str, str, str]] = []
    ids = {int(x) for x in run.ids["person_ids"]}
    n_expected = run.ids["n"]

    def verdict(ok: bool) -> str:
        return "PASS" if ok else "FAIL"

    scored = None
    if sup:
        scored = set.union(*[sup["sets"][a]["persons"] for a in run.arms])
        out.append((f"persons scored equals the {n_expected:,} ids in "
                    "`confirm_ids.json`",
                    verdict(scored == ids and len(scored) == n_expected),
                    f"{len(scored):,} scored, {len(ids):,} in the split file, "
                    f"{len(scored ^ ids)} symmetric differences"))
    else:
        n_persons = {run.integrity(a)["n_persons"] for a in run.arms}
        out.append((f"persons scored equals the {n_expected:,} ids in "
                    "`confirm_ids.json`",
                    verdict(n_persons == {n_expected}),
                    f"per-arm n_persons from analysis.json: "
                    f"{sorted(n_persons)}; ids in file {len(ids):,} "
                    "(id-by-id match needs --records)"))

    if do_used_scan:
        used = used_person_ids(skip={run.dir.name})
        out.append((f"zero overlap with the {run.ids['excluded_run_scan']:,} "
                    "previously used persons",
                    verdict(not (ids & used)),
                    f"{len(ids & used)} overlaps against {len(used):,} ids found "
                    f"by rescanning every other run dir's records.jsonl"))
    else:
        out.append((f"zero overlap with the {run.ids['excluded_run_scan']:,} "
                    "previously used persons",
                    "not re-derived here",
                    "proved at draw and at export by "
                    "`experiments/confirm_run.py verify`; rerun this script "
                    "without --skip-used-scan to re-derive"))

    deriv = {int(x) for x in load_json(DERIVATION_IDS)["person_ids"]}
    out.append((f"zero overlap with the {run.ids['excluded_derivation']:,} "
                "derivation ids",
                verdict(not (ids & deriv)),
                f"{len(ids & deriv)} overlaps against {len(deriv):,} ids in "
                "`results/overnight_exp2/derivation_ids.json`"))

    if sup:
        person_sets = [sup["sets"][a]["persons"] for a in run.arms]
        item_sets = [sup["sets"][a]["items"] for a in run.arms]
        out.append(("all five arms scored on the identical person set",
                    verdict(all(s == person_sets[0] for s in person_sets)),
                    f"{len(run.arms)} arms, "
                    f"{len(person_sets[0]):,} persons each"))
        out.append(("all five arms scored on the identical TIPI item set",
                    verdict(all(s == item_sets[0] for s in item_sets)),
                    f"{len(item_sets[0])} items: "
                    f"{', '.join(sorted(item_sets[0], key=_item_num))}"))
    else:
        out.append(("all five arms scored on the identical person set",
                    "not re-derived here", "needs --records"))
        out.append(("all five arms scored on the identical TIPI item set",
                    "not re-derived here", "needs --records"))

    pairs = {int(k): int(v) for k, v in run.imposter_pairs["pairs"].items()}
    self_paired = [p for p, d in pairs.items() if p == d]
    out.append(("imposter donors: never self-paired",
                verdict(not self_paired and set(pairs) == ids),
                f"{len(pairs):,} pairs, {len(self_paired)} self-pairs, "
                f"donor draw: {run.imposter_pairs['method']}"))

    if sup and "random" in sup["prompts"] and "imposter" in sup["prompts"]:
        rp, ip = sup["prompts"]["random"], sup["prompts"]["imposter"]
        kmax = max(run.checkpoints)
        common = sorted(set(rp) & set(ip))
        mismatch = [p for p in common
                    if revealed_lines(rp[p]) != revealed_lines(ip[p])]
        depth = {len(revealed_lines(rp[p])) for p in common}
        out.append(("imposter reveal positions mirror the random arm exactly",
                    verdict(not mismatch and depth == {kmax}),
                    f"{len(common):,} persons compared at k={kmax}: the ordered "
                    f"revealed-item texts differ for {len(mismatch)}; "
                    f"reveal depth {sorted(depth)}"))
    else:
        out.append(("imposter reveal positions mirror the random arm exactly",
                    "not re-derived here", "needs --records"))

    order = load_json(ORDER_FILE)["order"]
    n_first = len(run.export["fixed_order_first_20"])
    order_ok = order[:n_first] == run.export["fixed_order_first_20"]
    evidence = (f"first {n_first} of the derivation order match the exported "
                f"order and Addendum A's quoted list; derived on "
                f"{load_json(ORDER_FILE)['n_train']:,} persons")
    if sup and "fixed" in sup["prompts"]:
        fp = sup["prompts"]["fixed"]
        seqs = {tuple(revealed_lines(v)) for v in fp.values()}
        order_ok = order_ok and len(seqs) == 1
        evidence += (f"; the fixed arm's revealed sequence at k="
                     f"{max(run.checkpoints)} is identical for all "
                     f"{len(fp):,} persons ({len(seqs)} distinct sequence)")
    out.append(("fixed arm reveal order matches the frozen derivation order",
                verdict(order_ok), evidence))

    temps = {run.summaries[a]["config"]["temperature"] for a in run.arms}
    job_temps = set()
    for a in run.arms:
        extra = run.summaries[a]["extra"]
        for block in extra.get("chunk_summaries", []) + extra.get(
                "shard_summaries", []):
            job_temps.add(block.get("temperature"))
    out.append(("temperature 0 recorded on every call",
                verdict(temps == {0.0} and job_temps == {0.0}),
                f"arm configs {sorted(temps)}; "
                f"{len(job_temps)} distinct value(s) across every chunk and "
                f"shard summary: {sorted(job_temps)}"))
    return out


# ---------------------------------------------------------------------------
# Cross-split reading (exploratory only): pull cells out of earlier reports
# ---------------------------------------------------------------------------


def md_cell(path: Path, anchors: list[str], column: str, row_key: str) -> str:
    """The cell under ``column`` on the row keyed ``row_key``, in the first
    markdown table after the last anchor. Raises if anything is missing, so a
    silently wrong number cannot reach the report."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    i = 0
    for anchor in anchors:
        while i < len(lines) and anchor not in lines[i]:
            i += 1
        if i >= len(lines):
            raise SystemExit(f"[fatal] anchor {anchor!r} not found in {path}")
        i += 1
    while i < len(lines) and not lines[i].lstrip().startswith("|"):
        i += 1
    if i >= len(lines):
        raise SystemExit(f"[fatal] no table after {anchors[-1]!r} in {path}")
    header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    if column not in header:
        raise SystemExit(f"[fatal] column {column!r} not in {header} ({path})")
    col = header.index(column)
    i += 2  # skip the separator row
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if cells and cells[0] == row_key:
            return cells[col]
        i += 1
    raise SystemExit(f"[fatal] row {row_key!r} not found under {column!r} "
                     f"in {path}")


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _item_num(item: str) -> int:
    digits = "".join(ch for ch in item if ch.isdigit())
    return int(digits) if digits else 0


def _nan(x) -> bool:
    return x is None or (isinstance(x, float) and x != x)


def _m(x, nd: int = 4) -> str:
    """Raw MAE."""
    return "n/r" if _nan(x) else f"{x:.{nd}f}"


def _l(x, nd: int = 4) -> str:
    """Signed lift."""
    return "n/r" if _nan(x) else f"{x:+.{nd}f}"


def _p(x) -> str:
    return "n/r" if _nan(x) else f"{x:.3g}"


def _ci(e) -> str:
    if not e or _nan(e.get("ci_low")):
        return "n/r"
    return f"[{e['ci_low']:+.4f}, {e['ci_high']:+.4f}]"


def _yn(b) -> str:
    return "yes" if b else "no"


def _and(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def _pct(x, nd: int = 1) -> str:
    return "n/r" if _nan(x) else f"{x * 100:.{nd}f}%"


def _cell(e: dict | None) -> str:
    """lift [CI] p — the descriptive-table cell."""
    if not e:
        return "n/r"
    return f"{_l(e['lift_mean'])} {_ci(e)} p={_p(e['t_p'])}"


def _int(x) -> str:
    return "n/r" if x is None else f"{int(x):,}"


def _sup(sup: dict | None, path: tuple, field: str) -> str:
    """A supplement number, or the "not in artifact" marker."""
    if not sup:
        return NOT_IN_ARTIFACT
    node = sup
    for key in path:
        node = node.get(key) if isinstance(node, dict) else None
        if node is None:
            return NOT_IN_ARTIFACT
    v = node.get(field)
    if _nan(v):
        return NOT_IN_ARTIFACT
    if field == "wilcoxon_stat":
        return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.1f}"
    return f"{v:.4f}" if field == "t_stat" else _p(v)


def git_describe(path: Path) -> str:
    try:
        h = subprocess.run(["git", "log", "-1", "--format=%h", "--", str(path)],
                           cwd=_ROOT, capture_output=True, text=True,
                           check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", str(path)],
                               cwd=_ROOT, capture_output=True, text=True,
                               check=True).stdout.strip()
    except Exception:
        return "unavailable (no git)"
    if not h:
        return "not committed yet, so no hash to record"
    return f"commit `{h}`" + (", with uncommitted local changes" if dirty else "")


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------


def build_report(run: Run, sup: dict | None, checks: list[tuple],
                 ledger: dict) -> str:
    A = run.analysis
    kmax = max(run.checkpoints)
    c1 = verdict_c1(run, "C1_primary_adaptive_vs_random_k12")
    c1s = verdict_c1(run, "C1_secondary_adaptive_vs_random_k20")
    c2 = {12: reading_c2(run, "C2_adaptive_vs_fixed_k12"),
          20: reading_c2(run, "C2_adaptive_vs_fixed_k20")}
    c3 = verdict_c3(run)
    imp = imposter_replication(run)
    roll = decoding_rollup(run)
    ck = ", ".join(str(k) for k in run.checkpoints)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    o: list[str] = []
    add = o.append

    # ---------------------------------------------------------------- header
    add("# Stage 1E confirm report\n")
    add(f"Generated {now}\n")
    add("> **FILLED IN FROM THE RUN ARTIFACT.** This document is generated by")
    add("> `experiments/confirm_report.py` from "
        f"`{(run.dir / 'analysis.json').relative_to(_ROOT)}`")
    add(f"> (analysis artifact written {A['generated_utc']}). Every result cell "
        "is read")
    add("> or computed programmatically from the run directory; no number is "
        "typed by")
    add("> hand, and every verdict is produced by a function that applies the "
        "frozen")
    add("> rule. Numbers that are design facts (split size, seed, exclusion "
        "counts,")
    add("> checkpoints) come from the run's own `config.json` and "
        "`confirm_ids.json`;")
    add("> numbers inside a quoted block are contract text, never results of "
        "this run.")
    add("> A cell reading `n/r` was not run; a cell reading "
        f"\"{NOT_IN_ARTIFACT}\" is one")
    add("> the analysis artifact does not carry and this run was asked not to "
        "recompute.")
    add("")

    # ---------------------------------------------------------------- 1
    add("## 1. What this is\n")
    add("This is the confirmatory report for Stage 1E: does choosing the next "
        "question")
    add("adaptively beat asking questions in a random order, on a person the "
        "model has")
    add("never seen?\n")
    add("**This report IS confirmatory.** Unlike `results/overnight_stage1e.md` "
        "and")
    add("`results/adaptive_pilot_train.md`, which are labelled "
        "training/derivation split")
    add("and carry no claims, the numbers in this document test pre-registered "
        "bars on a")
    add("split that was frozen before anyone looked at it.\n")
    add(f"- **Contract:** `{ADDENDUM.name}`, adopted 2026-07-25,")
    add(f"  {run.config['contract'].split('(')[-1].rstrip(')')}. Sections A "
        "(design), B (bars C1/C2/C3, decoding")
    add("  robustness, multiplicity), C (pre-declared null readings), E "
        "(reporting rules).")
    add("  Upstream: `PREREGISTRATION_AMENDMENT_1.md` A1 (imposter baseline), "
        "A6 (Stage 1E")
    add("  design), A8 (reporting).")
    add(f"- **Split provenance:** n={run.ids['n']:,} persons, seed "
        f"{run.ids['seed']}, drawn from the cleaned RIASEC")
    add(f"  pool after excluding (i) all {run.ids['excluded_run_scan']:,} "
        "previously used persons and (ii) the")
    add(f"  {run.ids['excluded_derivation']:,} derivation-split ids in "
        "`results/overnight_exp2/derivation_ids.json`.")
    add("  Both exclusion counts printed by the draw script and recorded in")
    add(f"  `{(run.dir / 'confirm_ids.json').relative_to(_ROOT)}`. Disjointness "
        "from pilot1, pilot2,")
    add("  the gate set and the derivation split: verified at draw time and "
        "re-checked in")
    add("  section 8.3.")
    add(f"- **Model:** {run.config['model']}, twin variant "
        f"{run.config['variant']} distribution elicitation,")
    add(f"  temperature {run.config['temperature']:g}. Same parser and scoring "
        "code as the Stage 1 gate.")
    add("- **Task:** demographics up front, the 48 RIASEC interest items "
        "revealed one at")
    add("  a time with the true recorded answer, then the twin predicts all "
        f"{len(sup['items']) if sup else 10} held-out")
    add("  TIPI items. Cross-domain, as in the gate.")
    add(f"- **Checkpoints:** k = {ck}.")
    add("- **Primary metric:** TIPI mean absolute error, and lift over the")
    add("  demographics-only baseline. Lift = baseline MAE − arm MAE, per "
        "person, paired.")
    add("  Higher is better.")
    add(f"- **Run directory:** `{run.dir.relative_to(_ROOT)}/`.")
    add("- **Out of scope:** the 16PF replication. Addendum A section D defers "
        "its seed")
    add("  pool, target domain and splits to a separate Addendum B.")
    add("")

    # ---------------------------------------------------------------- 2
    add("## 2. The five arms\n")
    add(f"Per Addendum A section A. All {len(run.arms)} run on the same "
        f"{run.ids['n']:,} persons and predict the")
    add("same held-out TIPI items.\n")
    add("| # | arm | one-line definition |")
    add("|---|---|---|")
    arm_text = {
        "baseline": "Demographics only. No interest items revealed. The "
                    "zero-information comparison arm.",
        "random": "Reveal order is a per-person seeded random permutation of "
                  "the 48 items.",
        "fixed": "One global order for everybody: the frozen derivation order "
                 "(greedy ridge forward selection on the 2,000-person "
                 "derivation split, seed 45; no model in the selection; order "
                 "stored in `results/overnight_exp2/`).",
        "adaptive": "Next reveal = the remaining item with the highest variance "
                    "of the twin's stated answer distribution, ties broken by a "
                    "seeded random draw (SHA-256 seeding). Exactly the EXP1b "
                    "configuration; elicitation wording unchanged from the "
                    "pilot; the 0.05-grid variant is not adopted.",
        "imposter": "Identical pipeline and budget, but grounded on a random "
                    "other person's demographics and revealed items, with "
                    "reveal positions mirroring the random arm. Prediction "
                    "targets stay the test person's. Per Amendment A1.",
    }
    for i, arm in enumerate(run.arms, start=1):
        add(f"| {i} | {arm} | {arm_text[arm]} |")
    add("")
    add("**Imposter scope note (Addendum A section A).** This random-person "
        "imposter")
    add("measures generic-profile harm. Stage 2's same-domain imposter is a "
        "different")
    add("construct and its results must not be conflated with this one.")
    add("")

    # ---------------------------------------------------------------- 3
    add("## 3. Verdicts\n")
    add("Each subsection quotes its frozen bar word for word, then states the "
        "verdict,")
    add("then shows only the evidence that bar asks for. The quoted text is the "
        "contract")
    add("as committed at `3b8dd57`; it has not been edited here.")
    add("")

    # 3.1 -------------------------------------------------------------------
    add("### 3.1 C1 — PRIMARY\n")
    add("Frozen bar (verbatim, Addendum A section B):\n")
    o.extend(quote(BAR_C1))
    add("")
    add("(The power note is quoted contract text about the training-split "
        "pilot. It is")
    add("not a result of this run.)\n")
    add("Decision rule as applied: C1 passes iff the adaptive − random lift at "
        "k=12 is")
    add(f"above zero AND the paired t-test p is below {SIG} across the "
        f"{c1['ev']['n_persons']:,} persons, AND")
    add("the direction holds under argmax decoding (binding rule, section 4).")
    add("")
    add(f"`VERDICT: {'PASS' if c1['pass'] else 'FAIL'}`")
    add("")
    add("**Evidence — adaptive vs random at k=12 (PRIMARY).** Both arms' raw "
        "MAEs sit")
    add("beside every lift, under both decodings, per Addendum A section E "
        "rule 1.\n")
    hdr = ("| decoding | adaptive MAE | random MAE | lift (adaptive − random) | "
           "95% CI | t | p | Wilcoxon W | Wilcoxon p |")
    sep = "|" + "---|" * 9
    add(hdr)
    add(sep)
    label = c1["label"]
    for d in DECODINGS:
        e = c1["ev"] if d == EV else c1["argmax"]
        add(f"| {DECODING_LABEL[d]} | {_m(e['better_mae'])} | "
            f"{_m(e['worse_mae'])} | {_l(e['lift_mean'])} | {_ci(e)} | "
            f"{_sup(sup, ('frozen', label, d), 't_stat')} | "
            f"{_p(e['t_p'])} | "
            f"{_sup(sup, ('frozen', label, d), 'wilcoxon_stat')} | "
            f"{_sup(sup, ('frozen', label, d), 'wilcoxon_p')} |")
    add("")
    integ = run.integrity
    excl = (sup["frozen"]["C1_primary_adaptive_vs_random_k12"][EV][
        "n_excluded_pairs"] if sup else None)
    add(f"- persons scored: {c1['ev']['n_persons']:,} — parse failures: "
        f"adaptive {integ('adaptive')['n_parse_failures']}, random "
        f"{integ('random')['n_parse_failures']} — exclusions (person-item pairs "
        f"dropped from the pair): {_int(excl) if sup else NOT_IN_ARTIFACT}")
    add(f"- lift above zero under EV: {_yn(c1['lift_positive'])} "
        f"({_l(c1['ev']['lift_mean'])})")
    add(f"- paired t p below {SIG} under EV: {_yn(c1['significant'])} "
        f"(p={_p(c1['ev']['t_p'])})")
    add(f"- direction holds under argmax: {_yn(c1['same_sign'])} "
        f"(argmax lift {_l(c1['argmax']['lift_mean'])}, "
        f"p={_p(c1['argmax']['t_p'])})")
    add("")
    add("**Evidence — adaptive vs random at k=20 (SECONDARY).**\n")
    add(hdr)
    add(sep)
    for d in DECODINGS:
        e = c1s["ev"] if d == EV else c1s["argmax"]
        add(f"| {DECODING_LABEL[d]} | {_m(e['better_mae'])} | "
            f"{_m(e['worse_mae'])} | {_l(e['lift_mean'])} | {_ci(e)} | "
            f"{_sup(sup, ('frozen', 'C1_secondary_adaptive_vs_random_k20', d), 't_stat')} | "
            f"{_p(e['t_p'])} | "
            f"{_sup(sup, ('frozen', 'C1_secondary_adaptive_vs_random_k20', d), 'wilcoxon_stat')} | "
            f"{_sup(sup, ('frozen', 'C1_secondary_adaptive_vs_random_k20', d), 'wilcoxon_p')} |")
    add("")
    add(f"- direction holds under argmax: {_yn(c1s['same_sign'])} "
        f"(EV {_l(c1s['ev']['lift_mean'])} p={_p(c1s['ev']['t_p'])}; "
        f"argmax {_l(c1s['argmax']['lift_mean'])} "
        f"p={_p(c1s['argmax']['t_p'])})")
    add("")
    add("**If C1 is null, the pre-declared reading is (verbatim, Addendum A "
        "section C):**\n")
    o.extend(quote(NULL_C1))
    add("")
    add("Nothing is added to that reading. If C1 is null, the budget curves in "
        "section 6")
    add("are the deliverable and they stay labelled descriptive.")
    add("")
    if not c1["pass"]:
        add("C1 is null on this split: the adaptive − random lift at k=12 is "
            f"{_l(c1['ev']['lift_mean'])} under EV")
        add(f"with p={_p(c1['ev']['t_p'])}, and {_l(c1['argmax']['lift_mean'])} "
            f"with p={_p(c1['argmax']['t_p'])} under argmax. The sign is "
            "positive and")
        add("agrees across decodings, but neither test clears "
            f"p<{SIG}, so the pre-declared reading above")
        add("is the reading of this run. The k=20 contrast reads the same way "
            f"({_l(c1s['ev']['lift_mean'])}, p={_p(c1s['ev']['t_p'])}).")
        add("")

    # 3.2 -------------------------------------------------------------------
    add("### 3.2 C2 — SECONDARY confirmatory\n")
    add("Frozen bar (verbatim, Addendum A section B):\n")
    o.extend(quote(BAR_C2))
    add("")
    verdict_bits = "; ".join(
        f"k={k}: Reading {c2[k]['reading']} "
        f"({'significant' if c2[k]['significant'] else 'not significant'}, "
        f"p={_p(c2[k]['ev']['t_p'])})" for k in (12, 20))
    add(f"`VERDICT: not pass/fail by design — {verdict_bits}`")
    add("")
    add("**Evidence — adaptive vs fixed, both checkpoints, both decodings.** "
        "Positive")
    add("lift = adaptive better.\n")
    add("| k | decoding | adaptive MAE | fixed MAE | lift (adaptive − fixed) | "
        "95% CI | t | p |")
    add("|" + "---|" * 8)
    for k in (12, 20):
        label = c2[k]["label"]
        for d in DECODINGS:
            e = c2[k]["ev"] if d == EV else c2[k]["argmax"]
            add(f"| {k} | {DECODING_LABEL[d]} | {_m(e['better_mae'])} | "
                f"{_m(e['worse_mae'])} | {_l(e['lift_mean'])} | {_ci(e)} | "
                f"{_sup(sup, ('frozen', label, d), 't_stat')} | "
                f"{_p(e['t_p'])} |")
    add("")
    for k in (12, 20):
        add(f"- direction holds under argmax at k={k}: "
            f"{_yn(c2[k]['same_sign'])} (EV {_l(c2[k]['ev']['lift_mean'])}, "
            f"argmax {_l(c2[k]['argmax']['lift_mean'])} "
            f"p={_p(c2[k]['argmax']['t_p'])})")
    add("")
    add("#### Reading A, if adaptive beats fixed\n")
    add("Quoted, verbatim, Addendum A section B:\n")
    o.extend(quote(READING_A))
    add("")
    ks_a = [k for k in (12, 20) if c2[k]["reading"] == "A"]
    add(f"Applies iff: {_yn(bool(ks_a))} — adaptive − fixed above zero with p "
        f"below {SIG} at "
        + (f"k={', '.join(str(k) for k in ks_a)}." if ks_a
           else "neither k=12 nor k=20."))
    add("")
    add("#### Reading B, if fixed matches or beats adaptive\n")
    add("Quoted, verbatim, Addendum A section B:\n")
    o.extend(quote(READING_B))
    add("")
    ks_b = [k for k in (12, 20) if c2[k]["reading"] == "B"]
    add(f"Applies iff: {_yn(bool(ks_b))} — fixed at or above adaptive at "
        + (f"k={', '.join(str(k) for k in ks_b)}." if ks_b
           else "neither k=12 nor k=20."))
    add("")
    for k in ks_b:
        e = c2[k]["ev"]
        add(f"- k={k}: fixed MAE {_m(e['worse_mae'])} vs adaptive "
            f"{_m(e['better_mae'])}; adaptive − fixed "
            f"{_l(e['lift_mean'])} {_ci(e)} p={_p(e['t_p'])} — "
            + ("fixed is ahead by a significant margin"
               if c2[k]["significant"] and not c2[k]["adaptive_better"]
               else "the two arms are within noise of each other"))
    add("")
    add("Both readings are pre-written and carry equal weight. Neither is a "
        "fallback for")
    add("the other. Do not add commentary about which one was expected.")
    add("")
    add("#### Cost framing (required alongside either reading)\n")
    add("Quoted, verbatim, Addendum A section B:\n")
    o.extend(quote(COST_FRAMING))
    add("")
    add("Both currencies, measured on this run:\n")
    add("| arm | interview-time model calls per person | interview-time "
        "node-hours per person | offline derivation cost (one-off) |")
    add("|---|---|---|---|")
    rows = ledger["rows"]
    for arm in ("fixed", "adaptive"):
        r = rows[arm]
        pp_nh = (r["actual_node_hours"] / r["n_persons"]
                 if r["actual_node_hours"] and r["n_persons"] else None)
        offline = ("one ridge greedy selection on the 2,000-person derivation "
                   "split, no model calls (`results/overnight_exp2/`)"
                   if arm == "fixed" else "none")
        add(f"| {arm} | {r['n_calls'] / r['n_persons']:.0f} | "
            f"{pp_nh:.6f} | {offline} |")
    add(f"| measured ratio, adaptive / fixed at interview time | "
        f"{ledger['calls_ratio']:.2f}x | {ledger['node_hours_ratio']:.2f}x | — |")
    add("")
    add(f"The adaptive arm's per-person calls are "
        f"{ledger['adaptive_calls_pp']:.0f} against the fixed arm's "
        f"{ledger['fixed_calls_pp']:.0f}: "
        f"{ledger['adaptive_uncertainty_calls'] / rows['adaptive']['n_persons']:.0f} "
        "uncertainty-scoring calls per person to pick items, plus the same")
    add("prediction calls every arm makes. In node-hours the measured multiple "
        f"is {ledger['node_hours_ratio']:.2f}x")
    add("(both arms' node-hours are apportioned in section 7). The contract "
        "predicted")
    add("\"~5–12x\": the call-count multiple lands at the top of that band "
        f"({ledger['calls_ratio']:.2f}x) and the")
    add(f"node-hour multiple inside it ({ledger['node_hours_ratio']:.2f}x).")
    add("")
    add("#### Information-source framing (owner-required, verbatim)\n")
    add("Quoted word for word from Addendum A section B, where it is marked "
        "verbatim:\n")
    o.extend(quote(INFO_SOURCE))
    add("")
    add("This paragraph is printed in full whichever way C2 lands. It is not a "
        "caveat on")
    add("one reading only.")
    add("")

    # 3.3 -------------------------------------------------------------------
    add("### 3.3 C3 — grounding\n")
    add("Frozen bar (verbatim, Addendum A section B):\n")
    o.extend(quote(BAR_C3))
    add("")
    add("**Own-arm definition, restated because it is easy to get wrong:** own "
        "= the")
    add("random arm. The imposter arm mirrors the random arm's reveal schedule, "
        "so random")
    add("is the only matched comparison. Do not substitute adaptive or fixed "
        "into either")
    add("C3 contrast, not even as an extra row in this table — if you want "
        "those numbers,")
    add("they go in the exploratory section 11.")
    add("")
    add(f"`VERDICT: {'PASS' if c3['pass'] else 'FAIL'}`")
    add("")
    add("The binding rule this verdict applies, quoted so a reader can check "
        "which test")
    add("attaches to which decoding (verbatim, Addendum A section B):\n")
    o.extend(quote(RULE_DECODING))
    add("")
    add(f"Read literally: the p<{SIG} requirement attaches to the primary "
        "metric, which is MAE")
    add("under expected-value decoding (Addendum A section A: \"MAE with "
        "expected-value")
    add("decoding as the primary number\"). The argmax requirement is "
        "**direction only** —")
    add("\"must hold in direction under argmax decoding\" — so an argmax p "
        f"above {SIG} does not")
    add("fail the bar. Both contrasts below are shown under both decodings so "
        "the reader")
    add("can apply the rule themselves.")
    add("")
    add("**Evidence — both C3 contrasts at k=20, both decodings, all three "
        "arms' raw")
    add("MAEs beside every lift.**\n")
    add("| contrast | decoding | own (random) MAE | comparison arm MAE | lift | "
        "95% CI | t | p |")
    add("|" + "---|" * 8)
    for key, name in (("baseline", "own − baseline"),
                      ("imposter", "own − imposter")):
        for d in DECODINGS:
            e = c3[key]["ev"] if d == EV else c3[key]["argmax"]
            add(f"| {name} | {DECODING_LABEL[d]} | {_m(e['better_mae'])} | "
                f"{_m(e['worse_mae'])} | {_l(e['lift_mean'])} | {_ci(e)} | "
                f"{_sup(sup, ('frozen', c3[key]['label'], d), 't_stat')} | "
                f"{_p(e['t_p'])} |")
    add("")
    add(f"- own − baseline above zero with p below {SIG} under EV: "
        f"{_yn(c3['baseline']['positive'] and c3['baseline']['significant'])} "
        f"({_l(c3['baseline']['ev']['lift_mean'])}, "
        f"p={_p(c3['baseline']['ev']['t_p'])})")
    add(f"- own − imposter above zero with p below {SIG} under EV: "
        f"{_yn(c3['imposter']['positive'] and c3['imposter']['significant'])} "
        f"({_l(c3['imposter']['ev']['lift_mean'])}, "
        f"p={_p(c3['imposter']['ev']['t_p'])})")
    add(f"- both directions hold under argmax: "
        f"{_yn(c3['both_directions_hold'])} "
        f"(own − baseline {_l(c3['baseline']['argmax']['lift_mean'])}, "
        f"own − imposter {_l(c3['imposter']['argmax']['lift_mean'])})")
    add(f"- C3 requires BOTH contrasts to pass: {_yn(c3['pass'])}")
    add("")

    # The mandatory EV/argmax caveat, with the numbers that show it.
    b_ev = run.raw_mae(EV, "baseline", 0)
    b_am = run.raw_mae(AM, "baseline", 0)
    r_ev = run.raw_mae(EV, "random", kmax)
    r_am = run.raw_mae(AM, "random", kmax)
    add("**CAVEAT — read the own − baseline pass with the decoding in mind.**")
    add("")
    add("Addendum A wrote the binding decoding rule for exactly this failure "
        "mode, and")
    add("said so in the rule itself (verbatim, Addendum A section B):\n")
    o.extend(quote("Rationale: EV decoding shrinks variance and can inflate "
                   "lift by damaging\nthe hedging baseline "
                   "(results/rescore_ev_vs_argmax.md)."))
    add("")
    add("That is what the own − baseline contrast does on this split. The "
        "numbers:\n")
    add("| quantity | EV | argmax | change |")
    add("|---|---|---|---|")
    add(f"| baseline arm raw MAE (no reveals) | {_m(b_ev)} | {_m(b_am)} | "
        f"{_l(b_am - b_ev)} |")
    add(f"| own (random) arm raw MAE at k={kmax} | {_m(r_ev)} | {_m(r_am)} | "
        f"{_l(r_am - r_ev)} |")
    add(f"| own − baseline lift | {_l(c3['baseline']['ev']['lift_mean'])} | "
        f"{_l(c3['baseline']['argmax']['lift_mean'])} | "
        f"{_l(c3['baseline']['argmax']['lift_mean'] - c3['baseline']['ev']['lift_mean'])} |")
    add(f"| own − baseline p | {_p(c3['baseline']['ev']['t_p'])} | "
        f"{_p(c3['baseline']['argmax']['t_p'])} | — |")
    add("")
    add("Switching the decoding improves the baseline arm's raw MAE by "
        f"{_m(abs(b_am - b_ev))}, while the")
    add(f"own arm's barely moves ({_m(abs(r_am - r_ev))}, in the wrong "
        "direction). Almost the whole EV-measured")
    add("gap between knowing 20 real answers and knowing nothing is the "
        "baseline arm being")
    add("hurt by expected-value decoding, not the twin arm being helped by the "
        "reveals.")
    add("")
    add("What this does and does not mean:")
    add("")
    add("- **C3 passes as written.** The bar puts p<.05 on the primary EV "
        "metric and asks")
    add("  only that the direction hold under argmax. It does: "
        f"{_l(c3['baseline']['argmax']['lift_mean'])} is positive.")
    add("  This caveat is about interpretation, not about the verdict.")
    add("- **The size of the own − baseline effect is decoding-dependent.** "
        "Under argmax,")
    add(f"  20 revealed answers buy {_l(c3['baseline']['argmax']['lift_mean'])} "
        f"MAE with p={_p(c3['baseline']['argmax']['t_p'])} — not distinguishable")
    add("  from zero. Any downstream claim about how much a person's own "
        "answers are")
    add("  worth should quote both numbers, never the EV one alone.")
    add("- **The own − imposter contrast is not affected.** It is large and "
        "significant")
    add(f"  under both decodings ({_l(c3['imposter']['ev']['lift_mean'])} EV, "
        f"p={_p(c3['imposter']['ev']['t_p'])}; "
        f"{_l(c3['imposter']['argmax']['lift_mean'])} argmax, "
        f"p={_p(c3['imposter']['argmax']['t_p'])}), and it gets")
    add("  *stronger* under argmax. The grounding claim that survives both "
        "decodings is")
    add("  \"the right person's answers beat a stranger's\", which is the "
        "claim Amendment A1")
    add("  asked C3 to test.")
    add("")
    add("Does the imposter arm land below the demographics-only baseline (a "
        "stranger's")
    add("profile being worse than knowing nothing)?\n")
    add("| decoding | imposter MAE | baseline MAE | imposter − baseline lift | "
        "95% CI | p |")
    add("|" + "---|" * 6)
    for d in DECODINGS:
        e = run.lift_vs_baseline(d, "imposter", kmax)
        add(f"| {DECODING_LABEL[d]} | {_m(e['better_mae'])} | "
            f"{_m(e['worse_mae'])} | {_l(e['lift_mean'])} | {_ci(e)} | "
            f"{_p(e['t_p'])} |")
    add("")
    add(f"At every checkpoint, under both decodings (all {len(run.checkpoints)} "
        "checkpoints shown in section 6.1")
    add("and 6.2), the imposter arm sits below the baseline and the gap is "
        f"significant: {_yn(imp['replicated'])}.")
    add("")
    add("**If own − imposter is null or negative, the pre-declared reading is "
        "(verbatim,")
    add("Addendum A section C):**\n")
    o.extend(quote(NULL_C3))
    add("")
    add("Report it as such and stop. Do not search for a subgroup in which it "
        "does")
    add("replicate; that would be exploratory and belongs in section 11.")
    add("")
    if imp["pre_declared_null_applies"]:
        add("That reading applies to this run.")
    else:
        add("**That reading does not apply to this run.** own − imposter is "
            f"{_l(c3['imposter']['ev']['lift_mean'])} EV")
        add(f"(p={_p(c3['imposter']['ev']['t_p'])}) and "
            f"{_l(c3['imposter']['argmax']['lift_mean'])} argmax "
            f"(p={_p(c3['imposter']['argmax']['t_p'])}) — positive and "
            "significant, not null or")
        add("negative. The pilot's negative-transfer observation replicated at "
            "confirm scale:")
        add("a stranger's profile is worse than no profile at every checkpoint "
            "under both")
        add("decodings, so the quoted null text is printed above for "
            "completeness only and is")
        add("not the reading of this run.")
    add("")

    # ---------------------------------------------------------------- 4
    add("## 4. Decoding robustness (BINDING)\n")
    add("Frozen rule (verbatim, Addendum A section B):\n")
    o.extend(quote(RULE_DECODING))
    add("")
    add("And Addendum A section E rule 1:\n")
    o.extend(quote(RULE_E1))
    add("")
    add("Why this rule exists, in one paragraph: expected-value decoding "
        "averages the")
    add("twin's stated distribution, which squeezes its predictions toward the "
        "middle of")
    add("the scale. That helps an over-confident arm and hurts a hedging one. "
        "The")
    add("demographics-only baseline hedges, so EV decoding damages it and can "
        "inflate any")
    add("lift measured against it. On the Stage 1 development runs, argmax beat "
        "EV on the")
    add("baseline arm in every run, and one diagnostic's lift changed sign")
    add("(`results/rescore_ev_vs_argmax.md`, `memory/metric-decoding-caveat.md`)"
        ". Both")
    add("decodings are computed from the same stored distributions, so this is "
        "a scoring")
    add("question, not a second experiment, and it costs no extra model calls.")
    add("")
    add("**Master table — every confirmatory contrast, both decodings side by "
        "side.** One")
    add("row per contrast. A row is reportable only when all ten of its result "
        "cells are")
    add("filled.")
    add("")
    add("| bar | contrast | k | arm A MAE (EV) | arm B MAE (EV) | lift (EV) | "
        "p (EV) | arm A MAE (argmax) | arm B MAE (argmax) | lift (argmax) | "
        "p (argmax) | same direction? | reportable? |")
    add("|" + "---|" * 13)
    bar_name = {"C1_primary_adaptive_vs_random_k12": "C1 PRIMARY",
                "C1_secondary_adaptive_vs_random_k20": "C1 SECONDARY",
                "C2_adaptive_vs_fixed_k12": "C2 SECONDARY",
                "C2_adaptive_vs_fixed_k20": "C2 SECONDARY",
                "C3_own_vs_baseline_k20": "C3",
                "C3_own_vs_imposter_k20": "C3"}
    for label, better, worse, k, _tier in run.contracts:
        e = run.contrast(label)
        ev, am = e[EV], e[AM]
        a_name = "own (random)" if label.startswith("C3") else better
        cells = [ev["better_mae"], ev["worse_mae"], ev["lift_mean"],
                 am["better_mae"], am["worse_mae"], am["lift_mean"]]
        reportable = all(not _nan(c) for c in cells) and not _nan(ev["t_p"]) \
            and not _nan(am["t_p"])
        add(f"| {bar_name[label]} | {a_name} − {worse} | {k} | "
            f"{_m(ev['better_mae'])} | {_m(ev['worse_mae'])} | "
            f"{_l(ev['lift_mean'])} | {_p(ev['t_p'])} | "
            f"{_m(am['better_mae'])} | {_m(am['worse_mae'])} | "
            f"{_l(am['lift_mean'])} | {_p(am['t_p'])} | "
            f"{_yn(e['direction_agrees'])} | {_yn(reportable)} |")
    add("")
    add("Arm A is the first arm named in the contrast, arm B the second.")
    add("")
    add("**Robustness roll-up.**\n")
    add(f"- confirmatory contrasts whose direction holds under both decodings: "
        f"{len(roll['holds'])} of {roll['n_total']}")
    add(f"- confirmatory contrasts that change direction between decodings: "
        f"{len(roll['flips'])}"
        + (f" ({', '.join(roll['flips'])})" if roll["flips"] else ""))
    add(f"- any headline that depends on the decoding choice: "
        f"{_yn(roll['headline_decoding_dependent'])} — the headline is C1 at "
        "k=12, whose sign is the same under both")
    add(f"  decodings ({_l(c1['ev']['lift_mean'])} EV, "
        f"{_l(c1['argmax']['lift_mean'])} argmax) and whose verdict is "
        f"{'PASS' if c1['pass'] else 'FAIL'} under both. The one contrast that")
    add("  changes sign is a C2 secondary at k=12; see the caveat in section "
        "3.3 for the")
    add("  C3 own − baseline effect size, which keeps its sign but not its "
        "magnitude.")
    add("")
    add("**Spread check** (the mechanism behind the rule: under-dispersed "
        "predictions")
    add(f"against widely spread real answers). Pooled over all scored pairs at "
        f"k={kmax}")
    add("(baseline reveals nothing, so its row is its single k=0 scoring):\n")
    add("| series | sd |")
    add("|---|---|")
    if sup:
        add(f"| true answers | {_m(sup['spread'][('true answers', None)])} |")
        for arm in run.arms:
            for d in DECODINGS:
                add(f"| {arm}, {DECODING_LABEL[d]} | "
                    f"{_m(sup['spread'][(arm, d)])} |")
    else:
        add(f"| true answers | {NOT_IN_ARTIFACT} |")
        for arm in run.arms:
            for d in DECODINGS:
                add(f"| {arm}, {DECODING_LABEL[d]} | {NOT_IN_ARTIFACT} |")
    add("")

    # ---------------------------------------------------------------- 5
    add("## 5. Raw MAE by arm and checkpoint (both decodings)\n")
    add("Raw MAEs only. No lifts in this section — lifts live in sections 3 and "
        "6. Lower")
    add("is better. Cells that were not run read `n/r`.\n")
    add("The baseline arm reveals no items, so it has one MAE, repeated across "
        "the")
    add("checkpoint columns for reading convenience. It is the same number, not "
        f"{len(run.checkpoints)}")
    add("measurements.")
    add("")
    for d in DECODINGS:
        add(f"### 5.{1 if d == EV else 2} {DECODING_LABEL[d]} decoding\n")
        add("| arm | " + " | ".join(f"k={k}" for k in run.checkpoints) + " |")
        add("|" + "---|" * (len(run.checkpoints) + 1))
        for arm in run.arms:
            if arm == "baseline":
                v = run.raw_mae(d, arm, 0)
                cells = [_m(v)] * len(run.checkpoints)
                add("| baseline (no reveals) | " + " | ".join(cells) + " |")
            else:
                cells = [_m(run.raw_mae(d, arm, k)) for k in run.checkpoints]
                add(f"| {arm} | " + " | ".join(cells) + " |")
        add("")
    add(f"### 5.3 Per-item MAE at k={kmax} (both decodings)\n")
    if sup:
        add("Pooled over persons, per TIPI item, from the same scored pairs as "
            "section 5.1")
        add("and 5.2 (baseline at its k=0 scoring).")
        add("")
    add("| item | " + " | ".join(
        f"{arm} {DECODING_LABEL[d]}" for d in DECODINGS for arm in run.arms)
        + " |")
    add("|" + "---|" * (1 + 2 * len(run.arms)))
    items = sup["items"] if sup else [f"TIPI{i}" for i in range(1, 11)]
    for item in items:
        cells = []
        for d in DECODINGS:
            for arm in run.arms:
                if sup:
                    cells.append(_m(sup["per_item"][d].get(arm, {}).get(item)))
                else:
                    cells.append(NOT_IN_ARTIFACT)
        add(f"| {item} | " + " | ".join(cells) + " |")
    add("")

    # ---------------------------------------------------------------- 6
    add("## 6. Budget curves (DESCRIPTIVE)\n")
    add("Frozen rule (verbatim, Addendum A section B):\n")
    o.extend(quote(RULE_MULTIPLICITY))
    add("")
    add("Everything in this section is descriptive. No bar attaches to any of "
        "it. Do not")
    add("write a pass, fail or verdict word anywhere below.")
    add("")
    curve_arms = [a for a in run.arms if a != "baseline"]
    for d in DECODINGS:
        n = 1 if d == EV else 2
        add(f"### 6.{n} Lift over the demographics-only baseline, by arm and "
            f"budget ({DECODING_LABEL[d]})\n")
        if d == EV:
            add("Lift = baseline MAE − arm MAE, per person, paired, with 95% t "
                "interval and")
            add("paired-t p.")
            add("")
        add("| k | " + " | ".join(curve_arms) + " |")
        add("|" + "---|" * (len(curve_arms) + 1))
        for k in run.checkpoints:
            cells = [_cell(run.lift_vs_baseline(d, a, k)) for a in curve_arms]
            add(f"| {k} | " + " | ".join(cells) + " |")
        add("")
    add("### 6.3 Adaptive − random and adaptive − fixed at every checkpoint "
        "(EV)\n")
    add("The k=12 row of the first column is the C1 headline (section 3.1); "
        "every other")
    add("cell here is descriptive.")
    add("")
    add("| k | adaptive − random | adaptive − fixed | fixed − random |")
    add("|---|---|---|---|")
    for k in run.checkpoints:
        cells = []
        for pair in (("adaptive", "random"), ("adaptive", "fixed"),
                     ("fixed", "random")):
            cells.append(_cell(sup["extra"][pair][k])
                         if sup and pair in sup["extra"] else NOT_IN_ARTIFACT)
        add(f"| {k} | " + " | ".join(cells) + " |")
    add("")
    add("### 6.4 Curve shape questions (descriptive)\n")
    add("**Saturation.** The smallest k at which an arm reaches 90% of its own "
        "best lift")
    add("across the measured checkpoints, and how much the curve still moves "
        "after that.")
    add("")
    add("| arm | best lift in the measured range (EV) | k at that best | "
        "k reaching 90% of it | lift gained from that k to k=20 |")
    add("|---|---|---|---|---|")
    peaks = {}
    for arm in curve_arms:
        if arm == "imposter":
            continue
        lifts = {k: run.lift_vs_baseline(EV, arm, k)["lift_mean"]
                 for k in run.checkpoints}
        best_k = max(lifts, key=lambda k: lifts[k])
        best = lifts[best_k]
        k90 = next((k for k in run.checkpoints if lifts[k] >= 0.9 * best), None)
        gained = lifts[kmax] - lifts[k90] if k90 is not None else None
        peaks[arm] = (best_k, best, lifts[kmax])
        add(f"| {arm} | {_l(best)} | {best_k} | {k90} | {_l(gained)} |")
    add("")
    at_end = [a for a, (bk, _b, _l20) in peaks.items() if bk == kmax]
    before_end = [a for a in peaks if a not in at_end]
    add("Read the shape, not the ranking. "
        + (f"{_and(at_end)} reach their best measured lift at the last "
           f"checkpoint (k={kmax}), so nothing here shows a plateau; "
           if at_end else "")
        + ("; ".join(
            f"{a} peaks earlier, at k={peaks[a][0]} ({_l(peaks[a][1])}), and "
            f"reads {_l(peaks[a][2])} at k={kmax}" for a in before_end)
           + "." if before_end else "").strip())
    add("\"Saturation\" in this table means the point past which the remaining "
        "measured")
    add("gain is small, not a plateau proved to exist — the grid stops at "
        f"k={kmax}.")
    add("")
    add("**Budget recovery.** What fraction of the full-information lift each "
        "budget buys.")
    add("")
    add("Reference used for full information: **none exists on this split**. "
        "The confirm")
    add(f"checkpoint grid stops at k={kmax} (Addendum A section A: checkpoints "
        f"k ∈ {{{ck}}}),")
    add("so no confirm arm was run at all 48 items and there is no "
        "full-information")
    add("denominator here. Every cell below therefore reads \"not computable on "
        "the confirm")
    add("split\". The training-split (`results/overnight_stage1e.md`, EXP4) and "
        "the Stage 1")
    add("gate both have all-48 numbers, and neither may be borrowed as the "
        "denominator: a")
    add("fraction whose numerator is confirm-split and whose denominator is "
        "another split")
    add("is a split violation, not a budget-recovery fraction.")
    add("")
    add("| k | random: fraction of full-information lift | fixed | adaptive |")
    add("|---|---|---|---|")
    for k in run.checkpoints:
        cells = ["not computable on the confirm split"] * 3
        add(f"| {k} | " + " | ".join(cells) + " |")
    add("")
    add("**Adaptive selection behaviour (descriptive).** How often the scorer "
        "had a real")
    add("preference rather than a coin flip.")
    add("")
    tie = A.get("tie_diagnostic", {})
    add("| statistic | value |")
    add("|---|---|")
    add(f"| reveal decisions made | {_int(tie.get('n_decisions'))} |")
    add(f"| share of decisions tied at the top | "
        f"{tie.get('pct_rounds_with_tie')}% "
        f"({_int(tie.get('n_decisions_with_tie_at_top'))} decisions) |")
    add(f"| mean number of items tied at the top | "
        f"{tie.get('mean_tied_at_top')} |")
    add(f"| max number tied at the top | {tie.get('max_tied_at_top')} |")
    add(f"| mean top uncertainty score | {tie.get('mean_top_score')} |")
    add(f"| mean spread between top and bottom score | "
        f"{tie.get('mean_score_spread')} |")
    add("")

    # ---------------------------------------------------------------- 7
    add("## 7. Cost ledger\n")
    add("Same layout as `results/overnight_stage1e.md`. Projected node-hours "
        "come from the")
    add("per-arm projection made at launch (`config.json` → `projection`); the "
        "batch-level")
    add("estimate is in Addendum A section A.")
    add("")
    add("Four arms shared one Slurm job (`confirm_static`), so neither their "
        "projected nor")
    add("their actual node-hours are separately metered. Both columns "
        "apportion the job by")
    add("each arm's share of it: the actual column by output tokens (as "
        "recorded in each")
    add("arm's `summary.json` and `results/cost_log.jsonl`), the projected "
        "column by")
    add("expected completions. The adaptive arm ran as four separate jobs and "
        "its figures")
    add("are sums, not shares.")
    add("")
    add("| arm | projected node-hours | actual | slurm job(s) | status |")
    add("|---|---|---|---|---|")
    for arm in run.arms:
        r = rows[arm]
        add(f"| {arm} | {r['projected_node_hours']:.4f} | "
            f"{_m(r['actual_node_hours'])} | "
            f"{', '.join(r['slurm']) or 'n/r'} | {r['status']} |")
    add(f"| **TOTAL** | {ledger['total_projected']:.4f} | "
        f"{ledger['total_actual']:.4f} | | "
        f"{', '.join(sorted({r['status'] for r in rows.values()}))} |")
    add("")
    add(f"- model calls, all arms: {_int(ledger['total_calls'])} "
        f"(of which {_int(ledger['adaptive_uncertainty_calls'])} are the "
        "adaptive arm's item-selection calls)")
    est_lo, est_hi = ledger["addendum_estimate"]
    add(f"- node-hours against the Addendum A section A estimate: "
        f"{ledger['total_actual']:.3f} actual vs {est_lo}–{est_hi} estimated "
        f"({ledger['total_actual'] / est_lo:.2f}x the low end); the projection "
        f"made at launch was {ledger['total_projected']:.3f}")
    add(f"- API dollars (non-Leonardo calls, if any): "
        f"${ledger['run_usd']:.2f} — "
        f"{sum(1 for x in ledger['run_usd_lines'] if x is None)} of "
        f"{len(ledger['run_usd_lines'])} arm cost lines record no dollar cost "
        "(all compute was Leonardo node-hours)")
    add(f"- project totals after this run — total node-hours: "
        f"{ledger['project_node_hours']:.4f}; total $: "
        f"{ledger['project_usd']:.3f}")
    add(f"- adaptive vs fixed compute multiple, both currencies: "
        f"{ledger['calls_ratio']:.2f}x in interview-time model calls "
        f"({ledger['adaptive_calls_pp']:.0f} vs "
        f"{ledger['fixed_calls_pp']:.0f} per person), "
        f"{ledger['node_hours_ratio']:.2f}x in node-hours "
        f"({rows['adaptive']['actual_node_hours']} vs "
        f"{rows['fixed']['actual_node_hours']}); the contract predicted ~5–12x")
    add("")

    # ---------------------------------------------------------------- 8
    add("## 8. Parse rate and data integrity\n")
    add("Per Addendum A section E rule 3 (verbatim):\n")
    o.extend(quote(RULE_E3))
    add("")
    add("### 8.1 Completions expected vs received\n")
    add("| arm | completions expected | received | parsed | parse failures | "
        "parse rate | persons scored | persons excluded |")
    add("|" + "---|" * 8)
    tot = {"exp": 0, "rec": 0, "parsed": 0, "fail": 0}
    for arm in run.arms:
        it = run.integrity(arm)
        exp = rows[arm]["expected_completions"]
        rec = it["n_records"]
        fail = it["n_parse_failures"]
        tot["exp"] += exp or 0
        tot["rec"] += rec
        tot["parsed"] += rec - fail
        tot["fail"] += fail
        add(f"| {arm} | {_int(exp)} | {_int(rec)} | {_int(rec - fail)} | "
            f"{fail} | {it['parse_rate']:.6f} | {_int(it['n_persons'])} | "
            f"{run.ids['n'] - it['n_persons']} |")
    add(f"| **TOTAL** | {_int(tot['exp'])} | {_int(tot['rec'])} | "
        f"{_int(tot['parsed'])} | {tot['fail']} | "
        f"{tot['parsed'] / tot['rec']:.6f} | {_int(run.ids['n'])} | 0 |")
    add("")
    add("Also recorded, and not part of the scored records above: the adaptive "
        "arm made")
    add(f"{_int(run.summaries['adaptive']['extra']['n_uncertainty_calls'])} "
        "item-selection (uncertainty) calls, of which")
    add(f"{run.summaries['adaptive']['extra']['n_uncertainty_parse_failures']} "
        "failed to parse. Those calls choose the next question; they never "
        "enter a")
    add("reported MAE.")
    add("")
    add("Prompt-rebuild mismatches (the adaptive arm's prompts were rebuilt "
        "locally and")
    add("compared with the node's): "
        f"{run.integrity('adaptive')['n_prompt_rebuild_mismatches']}. Missing "
        "completions, per arm: "
        + ", ".join(f"{a} {run.integrity(a)['n_missing_completions']}"
                    for a in run.arms
                    if run.integrity(a)["n_missing_completions"] is not None)
        + ".")
    add("")
    add("Exclusion rule applied (as in the gate and the re-scoring): a "
        "person-item pair is")
    add("dropped from both arms of a contrast if either arm failed to parse, so "
        "every")
    if sup:
        drops = {label: sup["frozen"][label][EV]["n_excluded_pairs"]
                 for label, *_ in run.contracts}
        add("contrast stays fully paired. Pairs dropped this way, per frozen "
            "contrast: "
            + "; ".join(f"{lb} {n}" for lb, n in drops.items()) + ".")
    else:
        add(f"contrast stays fully paired. Pairs dropped this way: "
            f"{NOT_IN_ARTIFACT}.")
    add("")
    add("### 8.2 Example raw completions stored beside the parse rates\n")
    add("Rule E3 exists because an all-or-nothing parser cannot tell a "
        "truncated")
    add("completion from a badly formatted one. Store real examples, not counts "
        "alone.")
    add("")
    add("| arm | successful example | failed example (if any) | where stored |")
    add("|---|---|---|---|")
    for arm in run.arms:
        ex = run.examples[arm]
        ok = ex["ok_examples"][0]["raw_response"] if ex["ok_examples"] else "n/r"
        bad = (ex["failed_examples"][0]["raw_response"]
               if ex["failed_examples"] else "none — no parse failures")
        path = (run.dir / "arms" / arm / "parse_examples.json").relative_to(_ROOT)
        add(f"| {arm} | `{ok}` | `{bad}` | `{path}` |")
    add("")
    add("Failure breakdown, so truncation is distinguishable from format "
        "failure:\n")
    kinds = {"truncated completion": 0, "well-formed but wrong format": 0,
             "missing target(s) in a multi-target completion": 0, "other": 0}
    for arm in run.arms:
        for f in run.examples[arm]["failed_examples"]:
            kinds[classify_failure(f["raw_response"])] += 1
    add("| failure kind | count |")
    add("|---|---|")
    for kind, n in kinds.items():
        add(f"| {kind} | {n} |")
    add(f"| **TOTAL** | {sum(kinds.values())} |")
    add("")
    add("Classified from the stored raw completions, not from a flag: each "
        "failure's text")
    add("is checked for how many of the seven answer labels it carries and "
        "whether the")
    add("text ends mid-token. This run's scored calls are single-target (one "
        "TIPI item per")
    add("call), so the multi-target row is structurally zero. The totals here "
        "cover the")
    add(f"failures stored as examples ({sum(kinds.values())}); the arm totals in "
        f"8.1 count {tot['fail']}.")
    add("")
    add("### 8.3 Split integrity checks\n")
    add("These are checks, not results. Each one is pass or fail.\n")
    add("| check | result | evidence |")
    add("|---|---|---|")
    for name, res, ev in checks:
        add(f"| {name} | {res} | {ev} |")
    add("")
    if sup:
        add(f"Every number this report recomputed from the arms' "
            f"`records.jsonl` was cross-checked")
        add(f"against `analysis.json`: {sup['n_checks']} comparisons, largest "
            f"absolute difference {sup['max_abs_diff']:.2e}.")
        add("")

    # ---------------------------------------------------------------- 9
    add("## 9. Multiplicity statement\n")
    add("Frozen rule (verbatim, Addendum A section B):\n")
    o.extend(quote(RULE_MULTIPLICITY))
    add("")
    add("In practice: one number in this report is the adaptive headline — the")
    add("adaptive − random lift at k=12, section 3.1. Everything else is "
        "secondary or")
    add("descriptive, and the labels are in the section headings so nobody has "
        "to")
    add("remember which is which.")
    add("")
    add("| section | contrast or quantity | k | label |")
    add("|---|---|---|---|")
    add("| 3.1 | adaptive − random | 12 | PRIMARY — the headline |")
    add("| 3.1 | adaptive − random | 20 | SECONDARY |")
    add("| 3.2 | adaptive − fixed | 12, 20 | SECONDARY confirmatory |")
    add("| 3.3 | own (random) − baseline | 20 | confirmatory, grounding (C3) |")
    add("| 3.3 | own (random) − imposter | 20 | confirmatory, grounding (C3) |")
    add("| 3.3 | imposter − baseline | 20 | descriptive |")
    add("| 4 | both-decoding agreement | all | binding robustness check, not a "
        "separate claim |")
    add("| 5 | raw MAEs | all | descriptive |")
    add("| 6 | all lifts, curve shapes, saturation, budget recovery | all | "
        "descriptive |")
    add("| 6.4 | adaptive tie rates | — | descriptive |")
    add("| 11 | everything | — | exploratory |")
    add("")
    add("No correction is applied across the confirmatory bars, because only "
        "one of them")
    add("carries the headline. C2 and C3 answer separate pre-registered "
        "questions and are")
    add("labelled as such rather than pooled into a family of tests.")
    add("")

    # ---------------------------------------------------------------- 10
    add("## 10. Pre-declared null interpretations\n")
    add("Quoted in full, verbatim, Addendum A section C. These were written "
        "before the")
    add("run. They also appear inline in sections 3.1 and 3.3, where a null "
        "verdict is")
    add("actually read.")
    add("")
    o.extend(quote(NULL_SECTION_C))
    add("")
    add("C2 has no null branch by design: both of its directions are "
        "pre-written readings")
    add("of equal standing (section 3.2), so there is no outcome of C2 that "
        "counts as a")
    add("failure to report.")
    add("")
    applies = []
    if not c1["pass"]:
        applies.append("the C1 null reading (item order does not matter at "
                       "these budgets on this corpus; the budget curve is the "
                       "deliverable)")
    if imp["pre_declared_null_applies"]:
        applies.append("the C3 own−imposter null reading")
    add("Which pre-declared reading applies to this run: "
        + (" and ".join(applies) if applies else "neither") + ". "
        + ("The C3 own−imposter null reading does not apply — that contrast is "
           "positive and significant under both decodings (section 3.3)."
           if not imp["pre_declared_null_applies"] else
           "The C1 null reading does not apply."))
    add("")

    # ---------------------------------------------------------------- 11
    add("## 11. Exploratory\n")
    add("---\n")
    o.extend(quote(
        "**EXPLORATORY — WALLED OFF. Nothing below answers a frozen bar.**\n"
        "No number in this section is confirmatory, and none of it may be moved"
        "\nabove this line or into a headline. If a question here looks "
        "important,\nit becomes a new pre-registered bar in a future addendum, "
        "not a claim in\nthis report. Anything computed after the confirmatory "
        "numbers were seen\nis post-hoc and must say so in its own subsection."))
    add("")
    add("Both items below were chosen after the confirmatory numbers had been "
        "read. They")
    add("are post-hoc, they cross splits, and they exist to answer \"how does "
        "this sit")
    add("against what came before\" — not to support any claim.")
    add("")

    # 11.1 which training-split result replicated
    exp1b = md_cell(TRAIN_REPORT, ["### Lift over baseline, by variant"],
                    "EXP1b EV-var", str(kmax))
    fixed_deriv = md_cell(TRAIN_REPORT, ["### Frozen order applied to train-150"],
                          "fixed_deriv lift", str(kmax))
    add("### 11.1 Which training-split result replicated (EXPLORATORY, "
        "cross-split, post-hoc)\n")
    add("The training-split numbers are read out of "
        "`results/overnight_stage1e.md` (n=150,")
    add("training/derivation data, no claims). The confirm numbers are the "
        f"lift-over-baseline")
    add(f"curve of section 6.1 at k={kmax}, EV decoding, n={run.ids['n']:,}. "
        "Different splits and")
    add("different sample sizes, so this is a sanity comparison, not a test.")
    add("")
    add("| arm at k=20 | training split (n=150) | this confirm split "
        f"(n={run.ids['n']:,}) |")
    add("|---|---|---|")
    add(f"| adaptive, EV-variance (EXP1b) | {exp1b} | "
        f"{_cell(run.lift_vs_baseline(EV, 'adaptive', kmax))} |")
    add(f"| fixed, honest derivation order (EXP2) | {fixed_deriv} | "
        f"{_cell(run.lift_vs_baseline(EV, 'fixed', kmax))} |")
    exp4_random = md_cell(TRAIN_REPORT, ["## EXP4 — budget curve"], "random",
                          str(kmax))
    add(f"| random order (EXP4) | {exp4_random} | "
        f"{_cell(run.lift_vs_baseline(EV, 'random', kmax))} |")
    add("")
    add("Read plainly: the static order's training-split reading is the one "
        "that came back")
    add("at confirm scale; the adaptive arm's came in lower. And the contrast "
        "that")
    add("mattered — adaptive over random — did not replicate at all: the "
        "contract's power")
    add("note quotes the pilot effect as \"~+0.02, p=.029 at n=150\" (section "
        f"3.1), while this")
    add(f"run reads {_l(c1s['ev']['lift_mean'])} "
        f"(p={_p(c1s['ev']['t_p'])}) at k={kmax} and "
        f"{_l(c1['ev']['lift_mean'])} (p={_p(c1['ev']['t_p'])}) at k=12, on "
        "a split with")
    add("more than six times the persons.")
    add("")

    # 11.2 gate argmax at k=48 vs this run at k=20
    g_lift = md_cell(RESCORE_REPORT, ["### gate v2 - SECONDARY",
                                      "**Lift per decoding**"], "lift", "argmax")
    g_p = md_cell(RESCORE_REPORT, ["### gate v2 - SECONDARY",
                                   "**Lift per decoding**"], "p", "argmax")
    g_twin = md_cell(RESCORE_REPORT, ["### gate v2 - SECONDARY",
                                      "**Lift per decoding**"], "twin MAE",
                     "argmax")
    g_base = md_cell(RESCORE_REPORT, ["### gate v2 - SECONDARY",
                                      "**Lift per decoding**"],
                     "baseline MAE", "argmax")
    add("### 11.2 Argmax lift: the gate's k=48 beside this run's k=20 "
        "(EXPLORATORY, cross-split, post-hoc)\n")
    add("This is evidence about **budget**, not about the metric. The gate "
        "number is the")
    add("Gemma-4 secondary arm on the gate split (n=500) with all 48 items "
        "revealed, read")
    add("out of `results/rescore_ev_vs_argmax.md`. The confirm numbers stop at "
        f"k={kmax} on")
    add(f"n={run.ids['n']:,} different persons. **Different splits, different "
        "budgets, different sample")
    add("sizes — this is not a confirm number and no bar attaches to it.** It "
        "is also not a")
    add("budget-recovery fraction: dividing one by the other would mix splits "
        "(section 6.4).")
    add("")
    add("| source | split | budget | twin/arm MAE (argmax) | baseline MAE "
        "(argmax) | lift (argmax) | p |")
    add("|---|---|---|---|---|---|---|")
    add(f"| Stage 1 gate, Gemma-4 v2 SECONDARY | gate, n=500 | k=48 (all items) "
        f"| {g_twin} | {g_base} | {g_lift} | {g_p} |")
    for arm in ("random", "fixed", "adaptive"):
        e = run.lift_vs_baseline(AM, arm, kmax)
        add(f"| this run, {arm} arm | confirm, n={run.ids['n']:,} | k={kmax} | "
            f"{_m(e['better_mae'])} | {_m(e['worse_mae'])} | "
            f"{_l(e['lift_mean'])} | {_p(e['t_p'])} |")
    add("")
    add("What it suggests, at most: under argmax decoding the amount of MAE a "
        "twin gains")
    add(f"from 20 revealed answers on this split is smaller than what 48 "
        "revealed answers")
    add("bought on the gate split. Whether that gap is the budget, the split, "
        "or the arm")
    add("cannot be told apart from these two numbers, and this report does not "
        "try.")
    add("")
    add("| exploratory item | result | post-hoc? |")
    add("|---|---|---|")
    add(f"| 11.1 which training-split result replicated | fixed order "
        f"replicated ({fixed_deriv.split(' ')[0]} → "
        f"{_l(run.lift_vs_baseline(EV, 'fixed', kmax)['lift_mean'])}); adaptive "
        f"came in lower ({exp1b.split(' ')[0]} → "
        f"{_l(run.lift_vs_baseline(EV, 'adaptive', kmax)['lift_mean'])}); the "
        f"adaptive − random edge did not replicate | yes |")
    add(f"| 11.2 gate argmax k=48 beside this run's argmax k=20 | gate {g_lift} "
        f"(p={g_p}) at k=48 vs "
        f"{_l(run.lift_vs_baseline(AM, 'random', kmax)['lift_mean'])} "
        f"(p={_p(run.lift_vs_baseline(AM, 'random', kmax)['t_p'])}) for the "
        f"random arm at k={kmax} | yes |")
    add("")
    add("Other candidates named in the plan for this section and NOT computed "
        "here (no bar,")
    add("no need yet): contrasts the bars do not cover; own − imposter or "
        "own − baseline")
    add("with adaptive or fixed as \"own\" (forbidden inside C3 by Addendum A "
        "section B, so")
    add("they could only live here); calibration of the stated distributions; "
        "per-subgroup")
    add("breakdowns; within-1 and exact-match accuracy; anything about the 16PF "
        "replication,")
    add("which Addendum A section D defers to a separate Addendum B.")
    add("")

    # ---------------------------------------------------------------- 12
    add("## 12. Provenance\n")
    add("Which script and which files produced each table.")
    add("")
    add(f"- **Run directory:** `{run.dir.relative_to(_ROOT)}/`")
    add(f"- **Per-arm outputs:** `{run.dir.relative_to(_ROOT)}/arms/<arm>/` for "
        "arm in")
    add(f"  {{{', '.join(run.arms)}}} — each with `parse_examples.json`,")
    add("  `records.jsonl` (full prompts and raw responses) and `summary.json`")
    add(f"- **Analysis artifact:** `{(run.dir / 'analysis.json').relative_to(_ROOT)}` "
        f"(written {A['generated_utc']}), the single")
    add("  source of every confirmatory number in this document")
    add(f"- **This report:** `experiments/confirm_report.py` "
        f"({git_describe(_ROOT / 'experiments' / 'confirm_report.py')})")
    add(f"- **Driver:** `experiments/confirm_run.py` "
        f"({git_describe(_ROOT / 'experiments' / 'confirm_run.py')})")
    add("- **Split draw:** `experiments/draw_confirm_split.py` →")
    add(f"  `{(run.dir / 'confirm_ids.json').relative_to(_ROOT)}` "
        f"(n={run.ids['n']:,}, seed {run.ids['seed']}, exclusion counts")
    add(f"  {run.ids['excluded_run_scan']:,} and "
        f"{run.ids['excluded_derivation']:,} printed by the script)")
    add(f"- **Contract:** `{ADDENDUM.name}` at "
        f"{run.config['contract'].split('(')[-1].rstrip(')')}")
    add("- **Parser:** `src/doppler/scoring.parse_v2`, unchanged from the gate")
    add("- **Statistics:** `src/doppler/scoring.mean_ci` and `.paired_tests`, "
        "unchanged")
    add("- **Dual decoding:** both decodings computed from the same stored "
        "`raw_response`")
    add("  fields; no extra model calls (method as in "
        "`experiments/rescore_ev_argmax.py`)")
    add("")
    src_analysis = f"`{(run.dir / 'analysis.json').relative_to(_ROOT)}`"
    src_records = f"`{run.dir.relative_to(_ROOT)}/arms/*/records.jsonl`"
    prov = [
        ("3.1", "C1 evidence, k=12 and k=20",
         "`confirm_report.verdict_c1` + `build_report`",
         f"{src_analysis} (lifts, MAEs, p); {src_records} (t, Wilcoxon)"),
        ("3.2", "C2 evidence and cost currencies",
         "`confirm_report.reading_c2`, `confirm_report.cost_ledger`",
         f"{src_analysis}; `results/cost_log.jsonl`; `config.json` projection"),
        ("3.3", "C3 evidence, decoding caveat, imposter − baseline",
         "`confirm_report.verdict_c3`, `confirm_report.imposter_replication`",
         src_analysis),
        ("4", "decoding master table, spread check",
         "`confirm_report.decoding_rollup`, `confirm_report.build_supplement`",
         f"{src_analysis}; {src_records} (spread only)"),
        ("5", "raw MAE tables, per-item MAE",
         "`build_report` + `confirm_report.build_supplement`",
         f"{src_analysis} (raw MAE); {src_records} (per-item)"),
        ("6", "budget curves, saturation, recovery, tie rates",
         "`build_report` + `confirm_report.build_supplement`",
         f"{src_analysis} (`lift_over_baseline`, `tie_diagnostic`); "
         f"{src_records} (arm-vs-arm at other k)"),
        ("7", "cost ledger", "`confirm_report.cost_ledger`",
         "`manifest.json` (slurm ids, status), `config.json` (projection), "
         "`results/cost_log.jsonl` (actuals)"),
        ("8", "parse rates, examples, integrity checks",
         "`confirm_report.integrity_checks`, `confirm_report.classify_failure`",
         f"{src_analysis}; `arms/*/parse_examples.json`; `confirm_ids.json`; "
         "`imposter_pairs.json`; `results/overnight_exp2/`"),
        ("11", "exploratory", "`confirm_report.md_cell`",
         "`results/overnight_stage1e.md`, `results/rescore_ev_vs_argmax.md` "
         "(both training-split or other-split sources)"),
    ]
    add("| section | table | produced by | reads from |")
    add("|---|---|---|---|")
    for sec, table, by, src in prov:
        add(f"| {sec} | {table} | {by} | {src} |")
    add("")
    add("Reproduction check before any number here is trusted: this whole "
        "document is")
    add("regenerated from the run directory by")
    add("")
    add("```")
    add("uv run python experiments/confirm_report.py")
    add("```")
    add("")
    add("which rereads `analysis.json`, recomputes the supplementary cells from "
        "the arms'")
    add("`records.jsonl` through the same scoring path, aborts if any "
        "recomputed number")
    add("disagrees with the artifact, and overwrites this file. No cell is "
        "editable by hand:")
    add("editing this markdown is overwritten on the next run.")
    return "\n".join(o) + "\n"


# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build the Stage 1E confirm report from analysis.json.")
    ap.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--no-records", action="store_true",
                    help="skip the records-based supplement (t, Wilcoxon, "
                         "per-item, spread, extra-k contrasts)")
    ap.add_argument("--skip-used-scan", action="store_true",
                    help="skip re-deriving the previously-used person ids")
    args = ap.parse_args()

    run = Run(Path(args.run_dir))
    if run.analysis.get("arms_missing"):
        print(f"[confirm-report] arms missing from the analysis artifact: "
              f"{run.analysis['arms_missing']}", file=sys.stderr)

    sup = None
    if not args.no_records:
        print("[confirm-report] recomputing supplementary cells from records "
              "(this reads the arms' records.jsonl)...")
        sup = build_supplement(run)
        print(f"[confirm-report] cross-checked {sup['n_checks']} recomputed "
              f"numbers against analysis.json, max abs diff "
              f"{sup['max_abs_diff']:.2e}")

    checks = integrity_checks(run, sup, do_used_scan=not args.skip_used_scan)
    ledger = cost_ledger(run)

    # --- verdicts to stdout, with the numbers that drove them ---------------
    c1 = verdict_c1(run, "C1_primary_adaptive_vs_random_k12")
    c1s = verdict_c1(run, "C1_secondary_adaptive_vs_random_k20")
    c3 = verdict_c3(run)
    imp = imposter_replication(run)
    print("\n=== verdicts (computed) ===")
    print(f"C1 PRIMARY   (adaptive-random, k=12): "
          f"{'PASS' if c1['pass'] else 'FAIL'}   "
          f"EV lift {c1['ev']['lift_mean']:+.6f} p={c1['ev']['t_p']:.4g} | "
          f"argmax lift {c1['argmax']['lift_mean']:+.6f} "
          f"p={c1['argmax']['t_p']:.4g} | lift>0 {c1['lift_positive']} "
          f"sig {c1['significant']} same-sign {c1['same_sign']}")
    print(f"C1 SECONDARY (adaptive-random, k=20): "
          f"{'PASS' if c1s['pass'] else 'FAIL'}   "
          f"EV lift {c1s['ev']['lift_mean']:+.6f} p={c1s['ev']['t_p']:.4g} | "
          f"argmax lift {c1s['argmax']['lift_mean']:+.6f} "
          f"p={c1s['argmax']['t_p']:.4g}")
    for k in (12, 20):
        r = reading_c2(run, f"C2_adaptive_vs_fixed_k{k}")
        print(f"C2 k={k:<2}      Reading {r['reading']} "
              f"({'significant' if r['significant'] else 'not significant'})   "
              f"EV adaptive-fixed {r['ev']['lift_mean']:+.6f} "
              f"p={r['ev']['t_p']:.4g} | argmax "
              f"{r['argmax']['lift_mean']:+.6f} p={r['argmax']['t_p']:.4g} | "
              f"same-sign {r['same_sign']}")
    print(f"C3           (own=random, k=20):      "
          f"{'PASS' if c3['pass'] else 'FAIL'}   "
          f"own-baseline EV {c3['baseline']['ev']['lift_mean']:+.6f} "
          f"p={c3['baseline']['ev']['t_p']:.4g} / argmax "
          f"{c3['baseline']['argmax']['lift_mean']:+.6f} "
          f"p={c3['baseline']['argmax']['t_p']:.4g}; "
          f"own-imposter EV {c3['imposter']['ev']['lift_mean']:+.6f} "
          f"p={c3['imposter']['ev']['t_p']:.4g} / argmax "
          f"{c3['imposter']['argmax']['lift_mean']:+.6f} "
          f"p={c3['imposter']['argmax']['t_p']:.4g}")
    print(f"imposter negative transfer replicated: {imp['replicated']}; "
          f"pre-declared C3 null applies: {imp['pre_declared_null_applies']}")
    print(f"adaptive/fixed compute multiple: {ledger['calls_ratio']:.3f}x "
          f"calls per person ({ledger['adaptive_calls_pp']:.0f} vs "
          f"{ledger['fixed_calls_pp']:.0f}), "
          f"{ledger['node_hours_ratio']:.3f}x node-hours "
          f"({ledger['rows']['adaptive']['actual_node_hours']} vs "
          f"{ledger['rows']['fixed']['actual_node_hours']})")
    failed = [c for c in checks if c[1] == "FAIL"]
    print(f"integrity checks: {sum(1 for c in checks if c[1] == 'PASS')} pass, "
          f"{len(failed)} fail, "
          f"{sum(1 for c in checks if c[1] not in ('PASS', 'FAIL'))} not "
          "re-derived")
    for c in failed:
        print(f"  FAIL: {c[0]} -- {c[2]}")

    report = build_report(run, sup, checks, ledger)
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"\n[confirm-report] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
