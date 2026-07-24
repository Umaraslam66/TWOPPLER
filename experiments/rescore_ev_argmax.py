#!/usr/bin/env python3
"""EXPLORATORY re-scoring of the v2 runs: expected-value vs argmax decoding.

Motivation (post-hoc, prompted by the literature check in results/lit_check.md):
Ahnert et al. (arXiv 2510.11586) report that point elicitation beats
distribution elicitation at the individual level, but they decode elicited
distributions by ARGMAX. Every DOPPLER v2 number published so far decodes the
same distributions by EXPECTED VALUE. Those are different claims. This script
re-scores the v2 records already on disk under BOTH decodings, from the same
raw model responses, and asks whether EV beats argmax on the same
distributions, per person.

Nothing here is confirmatory. Stage 1 is development data (see
PREREGISTRATION.md). This is labelled EXPLORATORY throughout.

No network. No API calls. Reads records.jsonl files, writes one markdown file.

Run:
    python experiments/rescore_ev_argmax.py
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from doppler.scoring import mean_ci, paired_tests, parse_v2  # noqa: E402

OUT_PATH = REPO / "results" / "rescore_ev_vs_argmax.md"

# Reproduction gate: EV-decoded MAE lift must reproduce these published numbers
# to within TOLERANCE. Sources are named per run below.
TOLERANCE = 0.0005

# ---------------------------------------------------------------------------
# Run registry
# ---------------------------------------------------------------------------
# published_lift  : the number already in a committed report (the gate target)
# published_src   : where that number is written down
# v0_dir          : the v0 (point-elicitation) counterpart used for the
#                   twin-driven vs baseline-driven decomposition. None = N/A.

RUNS = [
    {
        "key": "pilot2-gemini",
        "label": "pilot2 v2 - gemini",
        "model": "gemini-3.5-flash-lite",
        "split": "pilot2 (n=50)",
        "dir": "results/pilot2_v2_k48_20260724-180024",
        "published_lift": 0.091,
        "published_src": "results/pilot2_comparison.md",
        "v0_dir": "results/pilot2_v0_k48_20260724-142949",
        "v0_label": "pilot2 v0 - gemini",
    },
    {
        "key": "pilot2-gemma4",
        "label": "pilot2 v2 - gemma-4",
        "model": "leonardo-gemma4-31b",
        "split": "pilot2 (n=50)",
        "dir": "results/pilot2_v2_k48_20260724-173317_leonardo-batch",
        "published_lift": 0.085,
        "published_src": "results/pilot2_comparison.md",
        "v0_dir": "results/pilot2_v0_k48_20260724-173311_leonardo-batch",
        "v0_label": "pilot2 v0 - gemma-4",
    },
    {
        "key": "pilot2-qwen",
        "label": "pilot2 v2 - qwen",
        "model": "leonardo-qwen3.6-27b",
        "split": "pilot2 (n=50)",
        "dir": "results/pilot2_v2_k48_20260724-165234_leonardo-batch",
        "published_lift": 0.003,
        "published_src": "results/pilot2_comparison.md",
        "v0_dir": "results/pilot2_v0_k48_20260724-165228_leonardo-batch",
        "v0_label": "pilot2 v0 - qwen",
    },
    {
        "key": "gate-primary",
        "label": "gate v2 - PRIMARY",
        "model": "gemini-3.5-flash-lite",
        "split": "gate (n=500)",
        "dir": "results/gate_v2_k48_20260724-181226",
        "published_lift": 0.0850,
        "published_src": "results/stage1_gate_report.md",
        "v0_dir": None,
        "v0_label": None,
    },
    {
        "key": "gate-secondary",
        "label": "gate v2 - SECONDARY",
        "model": "leonardo-gemma4-31b",
        "split": "gate (n=500)",
        "dir": "results/gate_v2_k48_20260724-182324_leonardo-batch",
        "published_lift": 0.0954,
        "published_src": "results/stage1_gate_report.md",
        "v0_dir": None,
        "v0_label": None,
    },
    {
        "key": "probe-knownanswer",
        "label": "probe known-answer v2",
        "model": "leonardo-gemma4-31b",
        "split": "gate (n=500)",
        "dir": "results/probe_knownanswer_v2_20260724-211148_leonardo-batch",
        # Not part of the mandated reproduction gate (the probe is a
        # diagnostic, no bar). Checked against its own summary.json anyway.
        "published_lift": 0.0453,
        "published_src": "results/probe_known_answer.md (diagnostic, no bar)",
        "v0_dir": None,
        "v0_label": None,
    },
]


# ---------------------------------------------------------------------------
# Decoding helpers
# ---------------------------------------------------------------------------


def round_ev(ev: float) -> int:
    """Round an expected value to the nearest scale point, .5 rounds up.

    Used ONLY for the within-1 / exact-match columns labelled "rounded EV".
    Python's built-in round() is banker's rounding, which would send 4.5 to 4;
    floor(x + 0.5) is the ordinary half-up rule and is what a reader expects.
    """
    return max(1, min(7, int(math.floor(ev + 0.5))))


def load_run(run_dir: Path) -> tuple[dict, dict]:
    """Load one run's records, re-parsing every v2 response from scratch.

    Returns (pairs, audit).

    ``pairs`` maps (person_id, item) -> {"true": int, "twin": dist, "baseline": dist}
    where ``dist`` is the parse_v2 output dict or None on a parse failure.
    Only (person, item) keys seen in BOTH arms are kept.

    ``audit`` records disagreements between the fresh parse and the values
    stored in the file, so a silent parser drift cannot pass unnoticed.
    """
    by_arm: dict[str, dict] = {"twin": {}, "baseline": {}}
    audit = {
        "n_records": 0,
        "stored_parse_fail": 0,
        "fresh_parse_fail": 0,
        "parse_flag_mismatch": 0,
        "ev_mismatch": 0,
        "argmax_mismatch": 0,
        "variants": set(),
    }

    with (run_dir / "records.jsonl").open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            audit["n_records"] += 1
            audit["variants"].add(rec.get("variant"))
            arm = rec["arm"]
            key = (int(rec["person_id"]), rec["item"])

            fresh = parse_v2(rec.get("raw_response"))
            stored_fail = bool(rec.get("parse_failure"))
            if stored_fail:
                audit["stored_parse_fail"] += 1
            if fresh is None:
                audit["fresh_parse_fail"] += 1
            if (fresh is None) != stored_fail:
                audit["parse_flag_mismatch"] += 1
            if fresh is not None and rec.get("prediction_ev") is not None:
                if abs(fresh["ev"] - float(rec["prediction_ev"])) > 1e-9:
                    audit["ev_mismatch"] += 1
                if fresh["argmax"] != int(rec["prediction_argmax"]):
                    audit["argmax_mismatch"] += 1

            by_arm[arm][key] = {"true": int(rec["true_answer"]), "dist": fresh}

    pairs = {}
    for key, twin in by_arm["twin"].items():
        base = by_arm["baseline"].get(key)
        if base is None:
            continue
        pairs[key] = {"true": twin["true"], "twin": twin["dist"], "baseline": base["dist"]}

    audit["variants"] = sorted(v for v in audit["variants"] if v)
    audit["n_twin_only"] = len(by_arm["twin"]) - len(pairs)
    audit["n_baseline_only"] = len(by_arm["baseline"]) - len(pairs)
    return pairs, audit


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_run(pairs: dict) -> dict:
    """Per-person means for every arm x decoding, then the paired statistics.

    Exclusion rule is the pre-registered one (src/doppler/scoring.summarize):
    a (person, item) pair is dropped from BOTH arms if EITHER arm failed to
    parse. The parse is identical for both decodings, so both decodings score
    exactly the same set of pairs - the comparison is fully paired.
    """
    persons: dict[int, list] = {}
    for (pid, item), rec in pairs.items():
        persons.setdefault(pid, []).append(rec)

    n_excluded_pairs = 0
    # per-person mean containers
    cols = {
        ("twin", "ev"): [], ("twin", "argmax"): [],
        ("baseline", "ev"): [], ("baseline", "argmax"): [],
    }
    w1 = {k: [] for k in cols}
    ex = {k: [] for k in cols}
    n_persons = 0
    n_scored_pairs = 0

    for pid in sorted(persons):
        acc = {k: [] for k in cols}
        acc_w1 = {k: [] for k in cols}
        acc_ex = {k: [] for k in cols}
        for rec in persons[pid]:
            if rec["twin"] is None or rec["baseline"] is None:
                n_excluded_pairs += 1
                continue
            true = rec["true"]
            for arm in ("twin", "baseline"):
                d = rec[arm]
                ev, am = d["ev"], d["argmax"]
                ev_disc = round_ev(ev)
                acc[(arm, "ev")].append(abs(ev - true))
                acc[(arm, "argmax")].append(abs(am - true))
                acc_w1[(arm, "ev")].append(abs(ev_disc - true) <= 1)
                acc_w1[(arm, "argmax")].append(abs(am - true) <= 1)
                acc_ex[(arm, "ev")].append(ev_disc == true)
                acc_ex[(arm, "argmax")].append(am == true)
            n_scored_pairs += 1
        if not acc[("twin", "ev")]:
            continue  # every pair excluded -> person drops out
        n_persons += 1
        for k in cols:
            cols[k].append(float(np.mean(acc[k])))
            w1[k].append(float(np.mean(acc_w1[k])))
            ex[k].append(float(np.mean(acc_ex[k])))

    out = {
        "n_persons": n_persons,
        "n_excluded_pairs": n_excluded_pairs,
        "n_scored_pairs": n_scored_pairs,
        "mae": {f"{a}_{d}": cols[(a, d)] for a, d in cols},
        "within1": {f"{a}_{d}": w1[(a, d)] for a, d in w1},
        "exact": {f"{a}_{d}": ex[(a, d)] for a, d in ex},
    }

    # --- lift per decoding: baseline - twin, matched decoding -------------
    out["lift"] = {}
    for dec in ("ev", "argmax"):
        t = out["mae"][f"twin_{dec}"]
        b = out["mae"][f"baseline_{dec}"]
        lift = [bi - ti for ti, bi in zip(t, b)]
        out["lift"][dec] = {
            "twin_mae": mean_ci(t),
            "baseline_mae": mean_ci(b),
            "lift": mean_ci(lift),
            "tests": paired_tests(b, t),  # b - t = lift
        }

    # --- EV vs argmax head-to-head, per arm -------------------------------
    # gap = argmax MAE - EV MAE, so positive = EV decoding is better.
    out["head_to_head"] = {}
    for arm in ("twin", "baseline"):
        ev = out["mae"][f"{arm}_ev"]
        am = out["mae"][f"{arm}_argmax"]
        gap = [a - e for e, a in zip(ev, am)]
        out["head_to_head"][arm] = {
            "ev_mae": mean_ci(ev),
            "argmax_mae": mean_ci(am),
            "gap": mean_ci(gap),
            "tests": paired_tests(am, ev),  # am - ev = gap
            "n_ev_better": sum(1 for g in gap if g > 0),
            "n_argmax_better": sum(1 for g in gap if g < 0),
            "n_tie": sum(1 for g in gap if g == 0),
        }

    # --- dispersion diagnostic -------------------------------------------
    # Why a decoding wins or loses on MAE is mostly a spread story: EV always
    # compresses a distribution toward its centre, argmax keeps whatever spread
    # the modes have. Pooled over every scored pair.
    pooled = {k: [] for k in cols}
    truths: list[int] = []
    for (pid, item), rec in pairs.items():
        if rec["twin"] is None or rec["baseline"] is None:
            continue
        truths.append(rec["true"])
        for arm in ("twin", "baseline"):
            pooled[(arm, "ev")].append(rec[arm]["ev"])
            pooled[(arm, "argmax")].append(float(rec[arm]["argmax"]))
    out["dispersion"] = {
        "true_sd": float(np.std(truths)) if truths else float("nan"),
        "true_mean": float(np.mean(truths)) if truths else float("nan"),
        **{f"{a}_{d}_sd": float(np.std(pooled[(a, d)])) for a, d in pooled},
        **{f"{a}_{d}_mean": float(np.mean(pooled[(a, d)])) for a, d in pooled},
    }

    # --- secondary metrics: lift per decoding -----------------------------
    for name in ("within1", "exact"):
        block = {}
        for dec in ("ev", "argmax"):
            t = out[name][f"twin_{dec}"]
            b = out[name][f"baseline_{dec}"]
            lift = [ti - bi for ti, bi in zip(t, b)]  # higher = better here
            block[dec] = {
                "twin": mean_ci(t),
                "baseline": mean_ci(b),
                "lift": mean_ci(lift),
                "tests": paired_tests(t, b),
            }
        out[f"{name}_blocks"] = block

    return out


def score_v0_run(run_dir: Path) -> dict:
    """Per-person MAE means for a v0 (single-digit) run, both arms.

    Used only for the twin-driven vs baseline-driven decomposition. v0 has one
    decoding (the digit itself), so there is nothing to compare across
    decodings here.
    """
    by_arm: dict[str, dict] = {"twin": {}, "baseline": {}}
    with (run_dir / "records.jsonl").open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            key = (int(rec["person_id"]), rec["item"])
            by_arm[rec["arm"]][key] = rec

    persons: dict[int, dict] = {}
    n_excluded = 0
    for key, t in by_arm["twin"].items():
        b = by_arm["baseline"].get(key)
        if b is None:
            continue
        if t.get("parse_failure") or b.get("parse_failure"):
            n_excluded += 1
            continue
        pid = key[0]
        true = int(t["true_answer"])
        acc = persons.setdefault(pid, {"twin": [], "baseline": []})
        acc["twin"].append(abs(float(t["parsed"]) - true))
        acc["baseline"].append(abs(float(b["parsed"]) - true))

    twin, base, pids = [], [], []
    for pid in sorted(persons):
        acc = persons[pid]
        if not acc["twin"]:
            continue
        pids.append(pid)
        twin.append(float(np.mean(acc["twin"])))
        base.append(float(np.mean(acc["baseline"])))
    return {
        "person_ids": pids,
        "twin_mae": twin,
        "baseline_mae": base,
        "n_excluded_pairs": n_excluded,
    }


def classify_lift(v2: dict, v0: dict) -> dict | None:
    """Decompose the v2-vs-v0 lift change into twin gain and baseline damage.

    lift             = baseline_MAE - twin_MAE
    lift(v2)-lift(v0) = [twin_MAE(v0) - twin_MAE(v2)]  (twin got better)
                      + [baseline_MAE(v0) - baseline_MAE(v2)] * -1
                        i.e. + [baseline_MAE(v2) - baseline_MAE(v0)] (baseline got worse)

    So the change in lift is exactly (twin improvement) + (baseline damage).
    Persons are matched by id; both runs cover the same pilot2 people.
    """
    # match persons by id
    v0_index = {pid: i for i, pid in enumerate(v0["person_ids"])}
    common = [pid for pid in v2["person_ids"] if pid in v0_index]
    if not common:
        return None

    t2 = [v2["twin_ev"][v2["person_index"][pid]] for pid in common]
    b2 = [v2["baseline_ev"][v2["person_index"][pid]] for pid in common]
    t0 = [v0["twin_mae"][v0_index[pid]] for pid in common]
    b0 = [v0["baseline_mae"][v0_index[pid]] for pid in common]

    twin_gain = [a - b for a, b in zip(t0, t2)]       # + = twin improved in v2
    base_damage = [a - b for a, b in zip(b2, b0)]     # + = baseline got worse in v2
    lift0 = [b - t for t, b in zip(t0, b0)]
    lift2 = [b - t for t, b in zip(t2, b2)]
    delta = [a - b for a, b in zip(lift2, lift0)]

    tg = float(np.mean(twin_gain))
    bd = float(np.mean(base_damage))
    total = tg + bd
    # share of the lift CHANGE attributable to each channel
    denom = abs(tg) + abs(bd)
    twin_share = abs(tg) / denom if denom > 0 else float("nan")
    base_share = abs(bd) / denom if denom > 0 else float("nan")

    if not math.isfinite(twin_share):
        verdict = "undetermined"
    elif tg <= 0 and bd > 0:
        # Only one channel is pushing the lift up, and it is the baseline
        # getting worse. The twin actually regressed. Unambiguous.
        verdict = "BASELINE-DRIVEN"
    elif bd <= 0 and tg > 0:
        verdict = "TWIN-DRIVEN"
    elif tg <= 0 and bd <= 0:
        verdict = "neither (lift fell)"
    elif base_share >= 0.60:
        verdict = "BASELINE-DRIVEN"
    elif twin_share >= 0.60:
        verdict = "TWIN-DRIVEN"
    else:
        verdict = "MIXED"

    # --- the sharper question -------------------------------------------
    # Does the v2 twin beat the BEST zero-information baseline available for
    # these people - the v0 baseline, when the v0 baseline is the better of the
    # two? If not, the v2 lift is bought by a damaged comparison arm.
    cross = [b - t for t, b in zip(t2, b0)]  # v0 baseline MAE - v2 twin MAE
    best_base_is_v0 = float(np.mean(b0)) < float(np.mean(b2))

    return {
        "n_common": len(common),
        "cross_lift": mean_ci(cross),
        "cross_tests": paired_tests(b0, t2),
        "best_base_is_v0": best_base_is_v0,
        "v0_twin_mae": mean_ci(t0),
        "v0_baseline_mae": mean_ci(b0),
        "v2_twin_mae": mean_ci(t2),
        "v2_baseline_mae": mean_ci(b2),
        "v0_lift": mean_ci(lift0),
        "v2_lift": mean_ci(lift2),
        "delta_lift": mean_ci(delta),
        "twin_gain": mean_ci(twin_gain),
        "twin_gain_tests": paired_tests(t0, t2),
        "baseline_damage": mean_ci(base_damage),
        "baseline_damage_tests": paired_tests(b2, b0),
        "twin_share": twin_share,
        "baseline_share": base_share,
        "total_change": total,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def f4(x) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.4f}"


def sgn4(x) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:+.4f}"


def ci(block) -> str:
    """CI for a signed quantity (a lift or a gap) - signs shown."""
    return f"[{sgn4(block['ci_low'])}, {sgn4(block['ci_high'])}]"


def ci_plain(block) -> str:
    """CI for a magnitude (an MAE) - no signs, they are always positive."""
    return f"[{f4(block['ci_low'])}, {f4(block['ci_high'])}]"


def pfmt(p) -> str:
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "n/a"
    if p < 1e-4:
        return f"{p:.2e}"
    return f"{p:.4g}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    results = {}
    gate_rows = []
    gate_failures = []

    for run in RUNS:
        run_dir = REPO / run["dir"]
        pairs, audit = load_run(run_dir)
        scored = score_run(pairs)

        # index persons for the v0 decomposition
        pids = sorted({pid for pid, _ in pairs})
        # rebuild the person order used by score_run (sorted, dropouts removed)
        # score_run appends in sorted person order and only skips fully-excluded
        # persons; with 0 exclusions the orders match. Rebuild explicitly:
        kept = []
        by_person: dict[int, list] = {}
        for (pid, item), rec in pairs.items():
            by_person.setdefault(pid, []).append(rec)
        for pid in sorted(by_person):
            if any(r["twin"] is not None and r["baseline"] is not None for r in by_person[pid]):
                kept.append(pid)
        scored["person_ids"] = kept
        scored["person_index"] = {pid: i for i, pid in enumerate(kept)}
        scored["twin_ev"] = scored["mae"]["twin_ev"]
        scored["baseline_ev"] = scored["mae"]["baseline_ev"]

        # summary.json cross-check (the file's own published EV numbers)
        summary = json.loads((run_dir / "summary.json").read_text())
        stored = summary["scoring"]["mae"]
        scored["stored"] = {
            "twin": stored["twin"]["mean"],
            "baseline": stored["baseline"]["mean"],
            "lift": stored["lift"]["mean"],
            "n_persons": summary["scoring"]["n_persons"],
            "n_excluded_pairs": summary["scoring"]["n_excluded_pairs"],
        }

        ev_lift = scored["lift"]["ev"]["lift"]["mean"]
        target = run["published_lift"]
        delta = ev_lift - target
        passed = abs(delta) <= TOLERANCE
        stored_delta = ev_lift - stored["lift"]["mean"]
        gate_rows.append({
            "run": run["label"],
            "target": target,
            "src": run["published_src"],
            "recomputed": ev_lift,
            "delta": delta,
            "pass": passed,
            "stored_delta": stored_delta,
        })
        if not passed:
            gate_failures.append((run["label"], target, ev_lift, delta))

        # v0 decomposition
        classification = None
        if run["v0_dir"]:
            v0 = score_v0_run(REPO / run["v0_dir"])
            classification = classify_lift(scored, v0)
        scored["classification"] = classification
        scored["audit"] = audit
        results[run["key"]] = scored

    # ---- REPRODUCTION GATE: hard stop --------------------------------------
    if gate_failures:
        print("REPRODUCTION GATE FAILED - not writing the report.\n")
        for label, target, got, delta in gate_failures:
            print(f"  {label}: published {target:+.4f}  recomputed {got:+.6f}  "
                  f"delta {delta:+.6f}  (tolerance {TOLERANCE})")
        return 2

    write_report(results, gate_rows)
    print(f"wrote {OUT_PATH}")
    for row in gate_rows:
        print(f"  GATE OK  {row['run']:<24} published {row['target']:+.4f} "
              f"recomputed {row['recomputed']:+.6f} delta {row['delta']:+.6f}")
    return 0


def write_report(results: dict, gate_rows: list) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L: list[str] = []
    add = L.append

    add("# Re-scoring the v2 runs: expected value vs argmax (EXPLORATORY)")
    add("")
    add("> **EXPLORATORY. Not confirmatory, not an outcome claim.**")
    add("> Stage 1 development data, re-scored after the fact from records already on disk.")
    add("> Prompted by the literature check (`results/lit_check.md`), not pre-registered.")
    add("> No bar in PREREGISTRATION.md attaches to anything below. No new model calls were made;")
    add("> compute cost of this analysis is zero (CPU re-scoring of existing files).")
    add("")
    add(f"Generated {now}")
    add("")

    # -------- 1. the question ----------------------------------------------
    add("## 1. The question")
    add("")
    add("The v2 elicitation asks the model for a probability over each of the 7 answers.")
    add("A distribution has to be turned into a number before it can be scored. There are two")
    add("obvious ways:")
    add("")
    add("- **EV (expected value)**: the probability-weighted average, e.g. `1:0.1 ... 7:0.1` -> 4.0.")
    add("  A continuous number between 1 and 7. This is what every published DOPPLER v2 number uses.")
    add("- **argmax**: the single answer with the highest probability. An integer 1-7.")
    add("")
    add("The closest prior work (Ahnert et al., arXiv 2510.11586) reports that asking for a point")
    add("answer beats asking for a distribution at the individual level. But they decode the")
    add("distribution by **argmax**. That is a different comparison from ours. The open question is")
    add("narrow and answerable from data already on disk: **on the same distributions, does EV")
    add("decoding beat argmax decoding, per person?**")
    add("")
    add("Everything below re-parses the raw model responses with `src/doppler/scoring.parse_v2` and")
    add("scores the identical set of (person, item) pairs under both decodings. The pre-registered")
    add("exclusion rule is kept: a pair is dropped from both arms if either arm failed to parse.")
    add("Parsing is identical for the two decodings, so the two are scored on exactly the same")
    add("pairs and every comparison is fully paired.")
    add("")
    add("Two labelling notes:")
    add("")
    add("- MAE under EV uses the continuous EV. MAE under argmax uses the integer.")
    add("- Within-1 and exact-match need an integer. Under argmax that is the argmax. Under EV")
    add("  there is no natural integer, so the EV is rounded to the nearest scale point")
    add("  (half rounds up) and the column is labelled **rounded EV** everywhere. Rounded-EV")
    add("  accuracy is a derived convenience number, not a decoding anyone proposed.")
    add("")

    # -------- 2. reproduction gate -----------------------------------------
    add("## 2. Reproduction gate")
    add("")
    add("Before any new number is trusted, the EV-decoded lift recomputed here has to reproduce")
    add(f"the already-published lift for each run, to within {TOLERANCE}. All runs pass.")
    add("")
    add("| run | published lift | source | recomputed (EV) | difference | vs run's own summary.json | gate |")
    add("|---|---|---|---|---|---|---|")
    for row in gate_rows:
        add(f"| {row['run']} | {row['target']:+.4f} | `{row['src']}` | "
            f"{row['recomputed']:+.6f} | {row['delta']:+.6f} | {row['stored_delta']:+.2e} | "
            f"{'PASS' if row['pass'] else 'FAIL'} |")
    add("")
    add("The last column is a tighter check: the difference against the full-precision lift stored")
    add("in each run's own `summary.json` (the published table rounds to 3 or 4 decimals).")
    add("")
    add("Parser audit - the fresh parse was compared record by record against the values stored in")
    add("each file. Any drift would show up here.")
    add("")
    add("| run | records | stored parse failures | fresh parse failures | flag mismatches | EV mismatches | argmax mismatches |")
    add("|---|---|---|---|---|---|---|")
    for run in RUNS:
        a = results[run["key"]]["audit"]
        add(f"| {run['label']} | {a['n_records']} | {a['stored_parse_fail']} | "
            f"{a['fresh_parse_fail']} | {a['parse_flag_mismatch']} | {a['ev_mismatch']} | "
            f"{a['argmax_mismatch']} |")
    add("")

    # -------- 3. per-run tables --------------------------------------------
    add("## 3. Per-run results")
    add("")
    for run in RUNS:
        r = results[run["key"]]
        add(f"### {run['label']}")
        add("")
        add(f"`{run['dir']}` - model {run['model']}, {run['split']}, "
            f"persons scored {r['n_persons']}, pairs scored {r['n_scored_pairs']}, "
            f"pairs excluded {r['n_excluded_pairs']}")
        if run["key"] == "probe-knownanswer":
            add("")
            add("Baseline arm is the gate secondary's baseline records, reused byte-identical")
            add("(`results/probe_known_answer.md` section 9). The baseline rows below are therefore")
            add("the same records as the gate secondary row, scored over the probe's item set.")
        add("")

        add("**MAE, all four arm x decoding cells** (lower is better):")
        add("")
        add("| arm | EV decoding | argmax decoding |")
        add("|---|---|---|")
        for arm in ("twin", "baseline"):
            ev = mean_ci(r["mae"][f"{arm}_ev"])
            am = mean_ci(r["mae"][f"{arm}_argmax"])
            add(f"| {arm} | {f4(ev['mean'])} {ci_plain(ev)} | {f4(am['mean'])} {ci_plain(am)} |")
        add("")

        add("**Lift per decoding** (lift = baseline MAE - twin MAE, matched decoding; "
            "positive = twin better). Both arms' raw MAEs are shown beside every lift so a lift "
            "cannot be read without seeing which arm moved:")
        add("")
        add("| decoding | twin MAE | baseline MAE | lift | 95% CI | t | p |")
        add("|---|---|---|---|---|---|---|")
        for dec in ("ev", "argmax"):
            b = r["lift"][dec]
            add(f"| {dec.upper() if dec == 'ev' else dec} | {f4(b['twin_mae']['mean'])} | "
                f"{f4(b['baseline_mae']['mean'])} | {sgn4(b['lift']['mean'])} | "
                f"{ci(b['lift'])} | {b['tests']['t_stat']:.4f} | {pfmt(b['tests']['t_p'])} |")
        add("")

        add("**Individual-level head-to-head, EV vs argmax on the same distributions.** "
            "gap = argmax MAE - EV MAE, per person, paired t across persons. "
            "Positive gap = EV decoding is better:")
        add("")
        add("| arm | EV MAE | argmax MAE | gap (argmax - EV) | 95% CI | t | p | persons EV better | argmax better | tie |")
        add("|---|---|---|---|---|---|---|---|---|---|")
        for arm in ("twin", "baseline"):
            h = r["head_to_head"][arm]
            add(f"| {arm} | {f4(h['ev_mae']['mean'])} | {f4(h['argmax_mae']['mean'])} | "
                f"{sgn4(h['gap']['mean'])} | {ci(h['gap'])} | {h['tests']['t_stat']:.4f} | "
                f"{pfmt(h['tests']['t_p'])} | {h['n_ev_better']} | {h['n_argmax_better']} | "
                f"{h['n_tie']} |")
        add("")

        add("**Secondary accuracy metrics.** argmax columns are the real thing; rounded-EV columns "
            "are EV rounded to the nearest scale point (labelled, see section 1):")
        add("")
        add("| metric | decoding | twin | baseline | lift | 95% CI | p |")
        add("|---|---|---|---|---|---|---|")
        for name, nice in (("within1", "within-1"), ("exact", "exact match")):
            for dec, dec_nice in (("argmax", "argmax"), ("ev", "rounded EV")):
                blk = r[f"{name}_blocks"][dec]
                add(f"| {nice} | {dec_nice} | {f4(blk['twin']['mean'])} | "
                    f"{f4(blk['baseline']['mean'])} | {sgn4(blk['lift']['mean'])} | "
                    f"{ci(blk['lift'])} | {pfmt(blk['tests']['t_p'])} |")
        add("")

    # -------- 4. cross-run summary -----------------------------------------
    add("## 4. Cross-run summary")
    add("")
    add("Every lift with both arms' raw MAEs beside it, under both decodings.")
    add("")
    add("| run | model | twin EV | base EV | lift EV | p (EV) | twin argmax | base argmax | lift argmax | p (argmax) |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    for run in RUNS:
        r = results[run["key"]]
        e, a = r["lift"]["ev"], r["lift"]["argmax"]
        add(f"| {run['label']} | {run['model']} | {f4(e['twin_mae']['mean'])} | "
            f"{f4(e['baseline_mae']['mean'])} | {sgn4(e['lift']['mean'])} | "
            f"{pfmt(e['tests']['t_p'])} | {f4(a['twin_mae']['mean'])} | "
            f"{f4(a['baseline_mae']['mean'])} | {sgn4(a['lift']['mean'])} | "
            f"{pfmt(a['tests']['t_p'])} |")
    add("")

    add("**Changing the decoding changes the lift.** Same responses, same people, same items -")
    add("only the rule for turning a distribution into a number differs:")
    add("")
    add("| run | lift EV | lift argmax | change | what happens to the headline |")
    add("|---|---|---|---|---|")
    for run in RUNS:
        r = results[run["key"]]
        e, a = r["lift"]["ev"]["lift"]["mean"], r["lift"]["argmax"]["lift"]["mean"]
        pe, pa = r["lift"]["ev"]["tests"]["t_p"], r["lift"]["argmax"]["tests"]["t_p"]
        sig_e, sig_a = pe < 0.05, pa < 0.05
        if (e > 0) != (a > 0):
            note = "**sign flips**"
        elif sig_e and not sig_a:
            note = "significant -> not significant"
        elif sig_a and not sig_e:
            note = "not significant -> significant"
        elif sig_e and sig_a:
            frac = a / e if e != 0 else float("nan")
            note = f"stays significant, size x{frac:.2f}"
        else:
            note = "not significant either way"
        add(f"| {run['label']} | {sgn4(e)} | {sgn4(a)} | {sgn4(a - e)} | {note} |")
    add("")

    add("**The EV-vs-argmax verdict, twin arm, one row per run:**")
    add("")
    add("| run | twin EV MAE | twin argmax MAE | gap (argmax - EV) | 95% CI | t | p | who wins |")
    add("|---|---|---|---|---|---|---|---|")
    for run in RUNS:
        h = results[run["key"]]["head_to_head"]["twin"]
        gap = h["gap"]["mean"]
        p = h["tests"]["t_p"]
        if p < 0.05:
            who = "EV" if gap > 0 else "argmax"
        else:
            who = "tie (n.s.)"
        add(f"| {run['label']} | {f4(h['ev_mae']['mean'])} | {f4(h['argmax_mae']['mean'])} | "
            f"{sgn4(gap)} | {ci(h['gap'])} | {h['tests']['t_stat']:.4f} | {pfmt(p)} | {who} |")
    add("")
    add("Same table for the baseline arm, because the decoding choice hits both arms and a lift is")
    add("a difference of two arms:")
    add("")
    add("| run | base EV MAE | base argmax MAE | gap (argmax - EV) | 95% CI | t | p | who wins |")
    add("|---|---|---|---|---|---|---|---|")
    for run in RUNS:
        h = results[run["key"]]["head_to_head"]["baseline"]
        gap = h["gap"]["mean"]
        p = h["tests"]["t_p"]
        if p < 0.05:
            who = "EV" if gap > 0 else "argmax"
        else:
            who = "tie (n.s.)"
        add(f"| {run['label']} | {f4(h['ev_mae']['mean'])} | {f4(h['argmax_mae']['mean'])} | "
            f"{sgn4(gap)} | {ci(h['gap'])} | {h['tests']['t_stat']:.4f} | {pfmt(p)} | {who} |")
    add("")

    add("**Why the two decodings differ: spread.** EV always pulls a prediction toward the middle")
    add("of the distribution; argmax keeps whatever spread the modes have. Pooled over every scored")
    add("pair, against the spread of the real answers:")
    add("")
    add("| run | sd(true) | sd(twin EV) | sd(twin argmax) | sd(base EV) | sd(base argmax) |")
    add("|---|---|---|---|---|---|")
    for run in RUNS:
        d = results[run["key"]]["dispersion"]
        add(f"| {run['label']} | {f4(d['true_sd'])} | {f4(d['twin_ev_sd'])} | "
            f"{f4(d['twin_argmax_sd'])} | {f4(d['baseline_ev_sd'])} | "
            f"{f4(d['baseline_argmax_sd'])} |")
    add("")

    # -------- 5. twin-driven vs baseline-driven ----------------------------
    add("## 5. Is each lift twin-driven or baseline-driven?")
    add("")
    add("A lift is `baseline MAE - twin MAE`. It can go up because the twin got better, or because")
    add("the baseline got worse. The second one is not a result worth having. The lit check flagged")
    add("that some DOPPLER lifts look like the second kind, so each v2 lift is decomposed against")
    add("its v0 (single-integer point elicitation) counterpart on the same people and items:")
    add("")
    add("```")
    add("lift(v2) - lift(v0)  =  [twin MAE improvement from v0 to v2]")
    add("                      + [baseline MAE damage from v0 to v2]")
    add("```")
    add("")
    add("Both numbers below are per person, paired, matched by person id. Positive twin gain = the")
    add("twin got better under v2. Positive baseline damage = the baseline got **worse** under v2.")
    add("The verdict rule, in order: if only one of the two channels is pushing the lift up, that")
    add("channel names the lift outright (a negative twin gain with positive baseline damage is")
    add("BASELINE-DRIVEN however small the share column looks). If both channels push the same way,")
    add("whichever supplies >= 60% of the change names it, and below 60% it is MIXED. The 60%")
    add("threshold is a reporting convention chosen here, not a pre-registered bar.")
    add("v2 numbers are EV-decoded, matching the published lift.")
    add("")
    add("| run | v0 twin | v0 base | v0 lift | v2 twin | v2 base | v2 lift | change | twin gain | p | baseline damage | p | share twin / base | verdict |")
    add("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for run in RUNS:
        c = results[run["key"]]["classification"]
        if c is None:
            add(f"| {run['label']} | - | - | - | - | - | - | - | - | - | - | - | - | N/A (no v0 counterpart) |")
            continue
        add(
            f"| {run['label']} | {f4(c['v0_twin_mae']['mean'])} | {f4(c['v0_baseline_mae']['mean'])} | "
            f"{sgn4(c['v0_lift']['mean'])} | {f4(c['v2_twin_mae']['mean'])} | "
            f"{f4(c['v2_baseline_mae']['mean'])} | {sgn4(c['v2_lift']['mean'])} | "
            f"{sgn4(c['delta_lift']['mean'])} | {sgn4(c['twin_gain']['mean'])} | "
            f"{pfmt(c['twin_gain_tests']['t_p'])} | {sgn4(c['baseline_damage']['mean'])} | "
            f"{pfmt(c['baseline_damage_tests']['t_p'])} | "
            f"{c['twin_share'] * 100:.0f}% / {c['baseline_share'] * 100:.0f}% | {c['verdict']} |"
        )
    add("")
    add("Runs marked N/A have no v0 counterpart: the gate was only ever run at v2 (the variant was")
    add("chosen from pilot2 before the gate), and the known-answer probe is a v2-only diagnostic")
    add("with a different prompt construction, so there is nothing to decompose against.")
    add("")
    add("Read the verdict precisely: it names what drove the **change in lift from v0 to v2**, not")
    add("the whole of the v2 lift. A run can have had a real lift at v0 already.")
    add("")
    add("### 5b. The sharper test: can the v2 twin beat the *best* baseline?")
    add("")
    add("The decomposition above can be gamed by a reader who only looks at one variant. The blunt")
    add("version of the same question: each run has two zero-information baselines on the same")
    add("people - the v0 one and the v2 one. Take the v0 baseline and ask whether the **v2 twin**")
    add("beats it. If a twin cannot beat the other variant's baseline, its own variant's lift is")
    add("mostly a statement about a damaged comparison arm.")
    add("")
    add("| run | v2 twin MAE | v2 baseline MAE | v0 baseline MAE | which baseline is stronger | v2 twin vs v0 baseline | 95% CI | p | vs its own v2 lift |")
    add("|---|---|---|---|---|---|---|---|---|")
    for run in RUNS:
        c = results[run["key"]]["classification"]
        if c is None:
            add(f"| {run['label']} | - | - | - | - | - | - | - | N/A (no v0 counterpart) |")
            continue
        stronger = "v0" if c["best_base_is_v0"] else "v2"
        add(f"| {run['label']} | {f4(c['v2_twin_mae']['mean'])} | {f4(c['v2_baseline_mae']['mean'])} | "
            f"{f4(c['v0_baseline_mae']['mean'])} | {stronger} | {sgn4(c['cross_lift']['mean'])} | "
            f"{ci(c['cross_lift'])} | {pfmt(c['cross_tests']['t_p'])} | "
            f"{sgn4(c['v2_lift']['mean'])} |")
    add("")

    # -------- 6. conclusion -------------------------------------------------
    add("## 6. What this says, in plain language")
    add("")
    twin_gaps = []
    for run in RUNS:
        h = results[run["key"]]["head_to_head"]["twin"]
        twin_gaps.append((run["label"], h["gap"]["mean"], h["tests"]["t_p"],
                          h["n_ev_better"], h["n_argmax_better"] + h["n_tie"]))
    n_runs = len(twin_gaps)
    ev_sig = [g for g in twin_gaps if g[2] < 0.05 and g[1] > 0]
    am_sig = [g for g in twin_gaps if g[2] < 0.05 and g[1] < 0]
    ev_dir = sum(1 for _, g, _, _, _ in twin_gaps if g > 0)
    am_dir = n_runs - ev_dir

    add("### The headline answer")
    add("")
    add("**Does EV decoding beat argmax decoding of the same distributions, at the individual")
    add(f"level, consistently? No.** On the twin arm, the two decodings are statistically")
    add(f"indistinguishable in {n_runs - len(ev_sig) - len(am_sig)} of the {n_runs} runs, and the")
    add(f"numerical direction is not even consistent: EV is nominally ahead in {ev_dir} runs and")
    add(f"argmax in {am_dir}. Only one run shows a real gap, and it is the run with the most")
    add("over-confident twin (details below). This does **not** replicate as a general rule.")
    add("")
    add("The gaps, twin arm, run by run (positive = EV better):")
    add("")
    for label, gap, p, n_ev, n_other in twin_gaps:
        verdict = "**significant**" if p < 0.05 else "not significant"
        add(f"- **{label}**: EV is {abs(gap):.4f} MAE points "
            f"{'better' if gap > 0 else 'worse'} than argmax, p = {pfmt(p)} ({verdict}); "
            f"EV wins for {n_ev} of {n_ev + n_other} people.")
    add("")
    add("### The finding that does replicate: the baseline arm")
    add("")
    add("Look at the baseline instead and the picture is clean and consistent. **Argmax beats EV on")
    add("the baseline arm in every run**, significantly in all three of the n=500 runs (the pilot2")
    add("runs point the same way at n=50 and cannot resolve it). This is the opposite of what the")
    add("EV-is-better story would predict, and it is the more reliable of the two results.")
    add("")
    add("The spread table in section 4 says why. EV is an averaging operation - it always pulls a")
    add("prediction toward the middle of its own distribution. The baseline (demographics only) is")
    add("already badly under-dispersed: it hedges near the scale midpoint while real answers are")
    add("spread across the whole 1-7 range. Averaging a hedged distribution squeezes it further,")
    add("and against a widely spread truth that costs MAE. Argmax at least lands on a mode and")
    add("keeps some spread. So EV *damages the baseline*.")
    add("")
    add("The spread numbers make this exact. Real answers have sd about 1.98. Every EV-decoded arm in")
    add("every run sits between 0.90 and 1.62 - under-dispersed, all of them. Argmax runs 1.30 to")
    add("2.12, closer to the truth. There is exactly one cell in the whole table where argmax")
    add("*over*-shoots the truth's spread: the known-answer probe's twin, at 2.1155 against a true")
    add("1.9771. That is the one and only run where EV beats argmax on the twin. The rule and the")
    add("exception are the same fact.")
    add("")
    add("That probe run is also the one whose own report (`results/probe_known_answer.md` section 5b)")
    add("documents an over-committed twin: peak stated probability >= 0.5 on 27.4% of answers versus")
    add("0.9% for the baseline, and a fat error tail. Over-dispersed, so averaging helps it. Same")
    add("operation, opposite sign, depending on whether the arm was over- or under-confident.")
    add("")
    add("**One rule covers both directions: EV compresses spread. That helps an over-confident")
    add("predictor and hurts a hedging one.** It is not a better decoding; it is a variance")
    add("shrinker, and whether shrinking helps depends on the arm.")
    add("")
    add("### Why this matters for the published lifts")
    add("")
    add("In four of the six runs EV hurts the hedging baseline more than it hurts the twin, so EV")
    add("decoding inflates the lift and switching to argmax shrinks it. The two exceptions are the")
    add("gemini runs at pilot2 scale and the qwen run, where the twin is hurt about as much as the")
    add("baseline and the lift moves the other way by a small amount. The runs that move most:")
    add("")
    for run in RUNS:
        r = results[run["key"]]
        e = r["lift"]["ev"]["lift"]["mean"]
        a = r["lift"]["argmax"]["lift"]["mean"]
        pe = r["lift"]["ev"]["tests"]["t_p"]
        pa = r["lift"]["argmax"]["tests"]["t_p"]
        add(f"- **{run['label']}**: {sgn4(e)} (p={pfmt(pe)}) under EV -> {sgn4(a)} "
            f"(p={pfmt(pa)}) under argmax.")
    add("")
    add("Two of those deserve to be said out loud:")
    add("")
    add("- **The gate secondary lift halves.** +0.0954 under EV, +0.0479 under argmax. It stays")
    add("  significant, but half of the headline number is a decoding choice, not the twin.")
    add("- **The known-answer probe flips sign.** +0.0453 (n.s.) under EV becomes -0.0684 under")
    add("  argmax, and the negative version is significant at p=0.042. Under argmax the seeded twin")
    add("  is *worse* than a demographics-only guess. The probe's stated conclusion - that the")
    add("  constructor over-extrapolates and MAE does not reward it - survives this and is arguably")
    add("  strengthened, but the sign of its headline number is not decoding-independent and the")
    add("  report should say so.")
    add("")
    add("### Does this contradict Ahnert et al.?")
    add("")
    add("No, and it does not rescue our design either. Their claim is that point elicitation beats")
    add("distribution elicitation, decoded by argmax. What this re-scoring adds is that the decoding")
    add("is not a neutral implementation detail: on the same distributions it moves the lift by up")
    add("to a factor of two and in one case flips its sign. So a point-vs-distribution comparison")
    add("that decodes by argmax is measuring elicitation and decoding together - and so is ours,")
    add("which decodes by EV. Neither is the clean experiment.")
    add("")
    add("The uncomfortable version: our published v2 lifts use the decoding that flatters them. EV")
    add("was chosen before any of this was known (it is the natural summary of a distribution and it")
    add("is what the pre-registration froze), so this is not a case of picking the winner after the")
    add("fact. But it now has a known direction of bias and every v2 lift should carry the argmax")
    add("number beside it.")
    add("")
    add("### Twin-driven or baseline-driven?")
    add("")
    for run in RUNS:
        c = results[run["key"]]["classification"]
        if c is None:
            add(f"- **{run['label']}**: N/A - no v0 counterpart exists for this run.")
            continue
        add(f"- **{run['label']}**: **{c['verdict']}** - twin gain {sgn4(c['twin_gain']['mean'])} "
            f"(p={pfmt(c['twin_gain_tests']['t_p'])}), baseline damage "
            f"{sgn4(c['baseline_damage']['mean'])} "
            f"(p={pfmt(c['baseline_damage_tests']['t_p'])}), of a "
            f"{sgn4(c['delta_lift']['mean'])} change in lift from v0 to v2.")
    add("")
    add("The gemini case is the one the lit check was worried about, and it is confirmed: going from")
    add("v0 to v2 made the gemini **twin worse** (MAE 1.3660 -> 1.4296) and the **baseline worse")
    add("still** (1.4380 -> 1.5203, p=0.049). The lift went up only because the comparison arm fell")
    add("further. Section 5b makes the consequence concrete: the gemini v2 twin beats the *v0*")
    add("baseline by +0.0084 - essentially nothing - while advertising a +0.0907 lift against its")
    add("own damaged v2 baseline. The qwen run is the same shape at the other end: its v2 twin is")
    add("-0.0094 against the v0 baseline, i.e. worse than a zero-information guess made under the")
    add("other variant.")
    add("")
    add("Gemma-4 is the exception and it supports the existing choice of it as the Stage 2 model. Its")
    add("twin genuinely improved from v0 to v2 (1.4960 -> 1.3843, p=0.027), its baseline barely moved")
    add("(+0.0297, p=0.33), and its v2 twin is the only one that is ahead of the v0 baseline by a")
    add("non-trivial margin (+0.0557). Be honest about that last number though: at n=50 it is not")
    add("significant (p=0.111). It is the right sign and the right size, not proof.")
    add("")
    add("Caveat on qwen: its v2 lift is +0.0033, statistically zero. Classifying the *change* in a")
    add("lift that is itself zero says something about the v0 run (where the twin was worse than")
    add("baseline), not about a v2 result worth having.")
    add("")

    add("## 7. Limits")
    add("")
    add("- Stage 1 development data only. No bar attaches. Nothing here passes or fails a hypothesis.")
    add("- Post-hoc: the decodings were compared after the EV numbers were published, prompted by")
    add("  the literature check. It is a re-analysis of one design choice, not a new experiment.")
    add("- The two decodings share the raw responses, so they cannot be independent evidence. This")
    add("  is a question about scoring, not about model behaviour.")
    add("- Rounded-EV accuracy (within-1, exact) is a convenience column. No one proposed rounding")
    add("  the EV as a decoding; it exists so the accuracy metrics have an EV-side entry at all.")
    add("- The known-answer probe shares its baseline records with the gate secondary run, so those")
    add("  two rows are not independent on the baseline side. The three baseline-arm argmax wins in")
    add("  section 4 are therefore two independent facts, not three.")
    add("- The 60% threshold in section 5 is a reporting convention invented for this document. The")
    add("  raw twin-gain and baseline-damage numbers are printed beside every verdict so a reader can")
    add("  apply a different threshold.")
    add("- Section 5 decomposes the *change* in lift from v0 to v2. It is not a decomposition of the")
    add("  whole v2 lift, and it needs a v0 counterpart, which the gate and probe runs do not have.")
    add("- The pilot2 runs are n=50. Nothing there resolves an effect of the size being discussed;")
    add("  the n=500 runs carry the weight.")
    add("- EV was frozen as the decoding before any of this was known, so no result here was selected")
    add("  after the fact. But that also means the argmax numbers have never been through a")
    add("  pre-registered analysis, and they are exploratory in exactly the same way.")
    add("")
    add("## 8. Provenance")
    add("")
    add("- Script: `experiments/rescore_ev_argmax.py` (no network, no API calls, CPU only).")
    add("- Parser: `src/doppler/scoring.parse_v2`, unchanged, re-run over the stored `raw_response`.")
    add("- Statistics helpers: `src/doppler/scoring.mean_ci` and `.paired_tests`, unchanged.")
    add("- Inputs: the `records.jsonl` of each run listed in section 3, plus the v0 runs named in")
    add("  section 5. Read-only: no pre-existing file was modified, this document is the only output.")
    add("- Cost: zero (no model calls).")
    add("")

    OUT_PATH.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
