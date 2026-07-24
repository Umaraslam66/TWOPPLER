"""Build results/probe_known_answer.md from the probe run dir.

Analysis only, no API calls. Every number is read from the probe run's
summary.json, the gate report's frozen numbers, and cost_log.jsonl. The one
piece of prose that is not a number is the interpretation guide, which states
what a large vs small within-scale lift implies and nothing else.

Usage:
    uv run python experiments/probe_report.py --run results/<probe_dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from doppler.scoring import v2_probabilities  # noqa: E402

RESULTS_DIR = _ROOT / "results"
DEFAULT_OUT = RESULTS_DIR / "probe_known_answer.md"
DEFAULT_COST_LOG = RESULTS_DIR / "cost_log.jsonl"

# Frozen Stage-1 gate cross-domain numbers (results/stage1_gate_report.md,
# commit ce54d9b). Quoted here for the side-by-side; not recomputed.
GATE = {
    "primary": {
        "label": "Gate cross-domain, PRIMARY (gemini-3.5-flash-lite + v2)",
        "run": "gate_v2_k48_20260724-181226",
        "lift": 0.0850, "ci": (0.0689, 0.1012), "t": 10.3541, "p": 6.87e-23,
    },
    "secondary": {
        "label": "Gate cross-domain, SECONDARY (Gemma-4-31B-it + v2)",
        "run": "gate_v2_k48_20260724-182324_leonardo-batch",
        "lift": 0.0954, "ci": (0.0750, 0.1159), "t": 9.1686, "p": 1.25e-18,
    },
}

BANNER = (
    "> **DIAGNOSTIC ONLY — NOT A CONFIRMATORY RESULT AND NOT AN OUTCOME "
    "CLAIM.**\n"
    "> Declared in advance as PREREGISTRATION_AMENDMENT_1.md section A7, which "
    "attaches **no bar** to it.\n"
    "> Within-scale prediction stays disallowed as an outcome claim under the "
    "original registration.\n"
    "> The only job of this run is to bound the constructor. Nothing here "
    "passes, fails, or revises a hypothesis."
)

A7_VERBATIM = (
    "One diagnostic run on the gate persons (n=500): seed the twin on\n"
    "demographics + 5 TIPI items, predict the other 5, counterbalanced (folds\n"
    "{TIPI1-5} and {TIPI6-10}, so every predicted item has its same-trait pair in\n"
    "the seed; both directions run). Purpose: bound the constructor - if\n"
    "within-scale seeded lift is also small, the +0.085 gate lift reflects a weak\n"
    "constructor; if large, a hard task. Within-scale prediction remains\n"
    "disallowed as an outcome claim (original registration); this probe is\n"
    "reported as a diagnostic beside the gate number, with no bar."
)

FOLD_LABELS = {
    "A2B": "seed TIPI1-5 -> predict TIPI6-10",
    "B2A": "seed TIPI6-10 -> predict TIPI1-5",
}


def _fmt_p(p: float) -> str:
    return "n/a" if p != p else f"{p:.3g}"


def _mae_row(name: str, block: dict) -> str:
    lift = block["lift"]
    tests = block["tests"]
    return (f"| {name} | {block['twin']['mean']:.4f} | "
            f"{block['baseline']['mean']:.4f} | "
            f"{lift['mean']:+.4f} | [{lift['ci_low']:+.4f}, {lift['ci_high']:+.4f}] | "
            f"{tests['t_stat']:.4f} | {_fmt_p(tests['t_p'])} | "
            f"{_fmt_p(tests['wilcoxon_p'])} | {lift['n']} |")


def mechanism_diagnostics(run_dir: Path) -> dict:
    """Post-hoc, EXPLORATORY: does the twin use the seed, and how does it err?

    Computed from the run's own records.jsonl. Answers three questions the MAE
    number alone cannot: (a) does the seeded prompt change the prediction at
    all, (b) does the prediction track the seed answer on the trait partner,
    and (c) where does the error mass sit.
    """
    twin: dict[tuple[int, str], dict] = {}
    base: dict[tuple[int, str], dict] = {}
    with (run_dir / "records.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            (twin if r["arm"] == "twin" else base)[(r["person_id"], r["item"])] = r

    keys = sorted(k for k in twin if k in base)
    keys = [k for k in keys
            if twin[k]["prediction_ev"] is not None
            and base[k]["prediction_ev"] is not None]

    tev = np.array([twin[k]["prediction_ev"] for k in keys])
    bev = np.array([base[k]["prediction_ev"] for k in keys])
    truth = np.array([twin[k]["true_answer"] for k in keys], dtype=float)

    partner: dict[str, str] = {}
    for i in range(1, 6):
        partner[f"TIPI{i}"] = f"TIPI{i + 5}"
        partner[f"TIPI{i + 5}"] = f"TIPI{i}"
    true_by_key = {k: base[k]["true_answer"] for k in base}
    seed_ans = np.array([true_by_key[(p, partner[item])] for p, item in keys],
                        dtype=float)

    def peak_probs(recs: dict) -> np.ndarray:
        out = []
        for k in keys:
            vec = v2_probabilities(recs[k]["raw_response"])
            if vec:
                out.append(max(vec.values()))
        return np.asarray(out)

    tpk, bpk = peak_probs(twin), peak_probs(base)
    t_err, b_err = np.abs(tev - truth), np.abs(bev - truth)

    return {
        "n_pairs": len(keys),
        "pct_prediction_moved": 100.0 * float(np.mean(np.abs(tev - bev) > 1e-9)),
        "mean_abs_shift": float(np.mean(np.abs(tev - bev))),
        "sd": {"truth": float(truth.std()), "twin": float(tev.std()),
               "baseline": float(bev.std())},
        "rho_with_seed_partner_answer": {
            "twin": float(stats.spearmanr(tev, seed_ans).correlation),
            "baseline": float(stats.spearmanr(bev, seed_ans).correlation),
            "ground_truth": float(stats.spearmanr(truth, seed_ans).correlation),
        },
        "rho_with_truth": {
            "twin": float(stats.spearmanr(tev, truth).correlation),
            "baseline": float(stats.spearmanr(bev, truth).correlation),
        },
        "slope_on_truth": {"twin": float(np.polyfit(truth, tev, 1)[0]),
                           "baseline": float(np.polyfit(truth, bev, 1)[0])},
        "peak_prob": {"twin_mean": float(tpk.mean()),
                      "baseline_mean": float(bpk.mean()),
                      "twin_pct_ge_half": 100.0 * float(np.mean(tpk >= 0.5)),
                      "baseline_pct_ge_half": 100.0 * float(np.mean(bpk >= 0.5))},
        "error_tail": [
            {"threshold": thr,
             "twin_pct": 100.0 * float(np.mean(t_err > thr)),
             "baseline_pct": 100.0 * float(np.mean(b_err > thr))}
            for thr in (1, 2, 3, 4)
        ],
    }


def _cost_lines(run_id: str) -> list[dict]:
    if not DEFAULT_COST_LOG.exists():
        return []
    out = []
    with DEFAULT_COST_LOG.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                entry = json.loads(line)
                if entry.get("run_id") == run_id:
                    out.append(entry)
    return out


def build(run_dir: Path, out_path: Path) -> str:
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    cfg = summary["config"]
    sc = summary["scoring"]
    by_fold = summary["scoring_by_fold"]
    totals = summary["totals"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    mae = sc["mae"]
    lift = mae["lift"]
    tests = mae["tests"]

    L: list[str] = []
    L += [f"# Known-answer probe (A7) — {run_dir.name}", "", BANNER, "",
          f"Generated {now}", ""]

    # --- 1. What was run ---
    L += ["## 1. What was run", "",
          "Verbatim from PREREGISTRATION_AMENDMENT_1.md, section A7:", "",
          "> " + A7_VERBATIM.replace("\n", "\n> "), "",
          "Implementation:", "",
          f"- Persons: the frozen GATE set, n={cfg['n_persons']} "
          "(positions 21-520 of the seed-42 draw of 520). Verified identical to "
          "the gate run's person ids.",
          "- Twin prompt: the gate's demographics rendering, then five of the "
          "person's own TIPI items shown as already-answered questions with their "
          "true 1-7 answers, then the v2 probability-distribution elicitation for "
          "one held-out TIPI item. **No interest items anywhere in the prompt.**",
          "- Folds (both directions run for every person): "
          f"`A2B` = {FOLD_LABELS['A2B']}; `B2A` = {FOLD_LABELS['B2A']}. "
          "TIPI's same-trait pairs are (1,6) (2,7) (3,8) (4,9) (5,10), so every "
          "predicted item has its own trait partner sitting in the seed.",
          f"- Each person contributes one prediction per item: 10 per person, "
          f"{totals['n_twin_records']} twin completions in total.",
          f"- Model: Gemma-4-31B-it on Leonardo (vLLM 0.25.1, TP=4, bf16, "
          f"temperature 0), same stack as the gate secondary arm. Same v2 parser, "
          "same MAE-by-expected-value scoring, same parse-failure exclusion rule.",
          f"- Baseline: **reused** from the gate run `{cfg['baseline_source_run']}` "
          f"({totals['n_baseline_records']} demographics-only records). All 5,000 "
          "baseline prompts were byte-compared against the gate's and were "
          "identical, so regenerating them would have produced the same text at "
          "temperature 0.",
          ""]

    # --- 2. Headline ---
    L += ["## 2. Result: within-scale MAE lift, beside the gate's cross-domain lift",
          "",
          "MAE lift = baseline MAE − twin MAE, per person, averaged over that "
          "person's items. Positive = the seeded twin is closer to the truth. "
          "Paired t and Wilcoxon are over the 500 persons.", "",
          "| arm | twin MAE | baseline MAE | MAE lift | 95% CI | t | t p | Wilcoxon p | n |",
          "|---|---|---|---|---|---|---|---|---|",
          _mae_row("**PROBE within-scale** (this run)", mae)]
    for key in ("primary", "secondary"):
        g = GATE[key]
        L.append(f"| {g['label']} | — | — | {g['lift']:+.4f} | "
                 f"[{g['ci'][0]:+.4f}, {g['ci'][1]:+.4f}] | {g['t']:.4f} | "
                 f"{_fmt_p(g['p'])} | — | 500 |")
    L += ["",
          f"Probe vs gate secondary (the directly comparable pair — same model, "
          f"same 500 persons, same 10 items, same baseline records): "
          f"**{lift['mean']:+.4f}** within-scale vs **{GATE['secondary']['lift']:+.4f}** "
          f"cross-domain, a ratio of "
          f"{lift['mean'] / GATE['secondary']['lift']:.2f}x.",
          "",
          f"- persons scored: {sc['n_persons']}; parse failures: "
          f"{totals['n_parse_failures']}; excluded pairs: {sc['n_excluded_pairs']}; "
          f"missing completions: {totals['n_missing_completions']}",
          ""]

    # --- 3. Per fold direction ---
    L += ["## 3. By fold direction", "",
          "Each direction is 5 predicted items per person over the same 500 "
          "persons, so the two rows are independent in items but paired in people.",
          "",
          "| direction | twin MAE | baseline MAE | MAE lift | 95% CI | t | t p | Wilcoxon p | n |",
          "|---|---|---|---|---|---|---|---|---|"]
    for fold in ("A2B", "B2A"):
        L.append(_mae_row(f"`{fold}` ({FOLD_LABELS[fold]})", by_fold[fold]["mae"]))
    L.append("")

    # --- 4. Per item ---
    L += ["## 4. Per predicted item", "",
          "`seeded by` names the same-trait partner that was in the seed for that "
          "prediction. Pooled over persons (not a per-person paired test).", "",
          "| predicted item | seeded by | direction | n | twin MAE | baseline MAE | MAE lift |",
          "|---|---|---|---|---|---|---|"]
    partner = {}
    for i in range(1, 6):
        partner[f"TIPI{i}"] = f"TIPI{i + 5}"
        partner[f"TIPI{i + 5}"] = f"TIPI{i}"
    fold_of = {code: fold for fold, spec in cfg["folds"].items()
               for code in spec["predict"]}
    order = {f"TIPI{i}": i for i in range(1, 11)}
    for row in sorted(sc["per_item"], key=lambda r: order[r["item"]]):
        item = row["item"]
        L.append(f"| {item} | {partner[item]} | `{fold_of[item]}` | {row['n']} | "
                 f"{row['twin_mae']:.4f} | {row['baseline_mae']:.4f} | "
                 f"{row['mae_lift']:+.4f} |")
    L.append("")

    # --- 5. Secondaries ---
    w1, ex = sc["within1"], sc["exact"]
    L += ["## 5. Secondary metrics (never reported alone)", "",
          "| metric | twin | baseline | lift | 95% CI | t p |",
          "|---|---|---|---|---|---|",
          f"| within-1 (argmax) | {w1['twin']['mean']:.4f} | "
          f"{w1['baseline']['mean']:.4f} | {w1['lift']['mean']:+.4f} | "
          f"[{w1['lift']['ci_low']:+.4f}, {w1['lift']['ci_high']:+.4f}] | "
          f"{_fmt_p(w1['tests']['t_p'])} |",
          f"| exact match (argmax) | {ex['twin']['mean']:.4f} | "
          f"{ex['baseline']['mean']:.4f} | {ex['lift']['mean']:+.4f} | "
          f"[{ex['lift']['ci_low']:+.4f}, {ex['lift']['ci_high']:+.4f}] | "
          f"{_fmt_p(ex['tests']['t_p'])} |",
          ""]

    # --- 5b. Mechanism (exploratory) ---
    mech = mechanism_diagnostics(run_dir)
    rho_seed = mech["rho_with_seed_partner_answer"]
    rho_true = mech["rho_with_truth"]
    L += ["## 5b. Why the lift is small — mechanism (EXPLORATORY, post-hoc)", "",
          "_Not pre-registered. Computed after seeing the headline, to check the "
          "pipeline was working before the small lift is interpreted._", "",
          "**The twin is not ignoring the seed.** Handing it five of the person's "
          f"own answers moves the prediction in "
          f"{mech['pct_prediction_moved']:.1f}% of the "
          f"{mech['n_pairs']} (person, item) pairs, by "
          f"{mech['mean_abs_shift']:.2f} scale points on average.", "",
          "| diagnostic | twin (seeded) | baseline (demographics only) | truth |",
          "|---|---|---|---|",
          f"| Spearman rho with the seed answer on the trait partner | "
          f"{rho_seed['twin']:+.3f} | {rho_seed['baseline']:+.3f} | "
          f"{rho_seed['ground_truth']:+.3f} |",
          f"| Spearman rho with the true answer | {rho_true['twin']:+.3f} | "
          f"{rho_true['baseline']:+.3f} | — |",
          f"| regression slope of prediction on truth | "
          f"{mech['slope_on_truth']['twin']:.3f} | "
          f"{mech['slope_on_truth']['baseline']:.3f} | 1.000 |",
          f"| sd of the prediction | {mech['sd']['twin']:.3f} | "
          f"{mech['sd']['baseline']:.3f} | {mech['sd']['truth']:.3f} |",
          f"| mean peak stated probability | {mech['peak_prob']['twin_mean']:.3f} | "
          f"{mech['peak_prob']['baseline_mean']:.3f} | — |",
          f"| share of answers with peak probability >= 0.5 | "
          f"{mech['peak_prob']['twin_pct_ge_half']:.1f}% | "
          f"{mech['peak_prob']['baseline_pct_ge_half']:.1f}% | — |",
          "",
          "Read the first row carefully. Real respondents' answers on a "
          f"reverse-scored trait pair correlate {rho_seed['ground_truth']:+.3f}. "
          f"The seeded twin's predictions correlate {rho_seed['twin']:+.3f} with "
          "the seed — it treats the reverse item as a near-deterministic mirror "
          "of the one it was shown, far tighter than real people are. It applies "
          "the scoring rule, not the person.", "",
          "That over-commitment is exactly why the accuracy gains and the MAE "
          "gain disagree. Error mass, share of predictions off by more than:", "",
          "| error > | twin | baseline |",
          "|---|---|---|"]
    for row in mech["error_tail"]:
        unit = "point" if row["threshold"] == 1 else "points"
        L.append(f"| {row['threshold']} scale {unit} | {row['twin_pct']:.1f}% | "
                 f"{row['baseline_pct']:.1f}% |")
    L += ["",
          "The twin is right far more often (exact match "
          f"{ex['twin']['mean']:.3f} vs {ex['baseline']['mean']:.3f}, "
          f"lift {ex['lift']['mean']:+.4f}) and tracks the truth better in rank "
          f"terms (rho {rho_true['twin']:.3f} vs {rho_true['baseline']:.3f}), but "
          "it is badly wrong more often too. MAE prices both, so the two roughly "
          "cancel and the headline lift lands near zero. The baseline earns its "
          "MAE by hedging near the scale midpoint; the twin earns its exact "
          "matches by committing, and pays for the commitments it gets wrong.", ""]

    # --- 6. Leakage guards ---
    L += ["## 6. Leakage guards", "",
          "Enforced at prompt-build time; any violation raises and stops the run "
          "(`experiments/probe_known_answer.py`, unit-tested in "
          "`tests/test_probe_known_answer.py`):", "",
          "1. A predicted item is never in its own seed set, and no seed item "
          "carries the predicted item's text.",
          "2. The predicted statement appears exactly once in the whole prompt "
          "(only in `YOUR TASK`), and its recorded answer is never attached to it.",
          "3. No interest-item text and no interests block ever enters a probe "
          "prompt — the seed is TIPI + demographics only.",
          "4. Fold construction is unit-tested: 5/5 disjoint split, the two "
          "directions together cover each of the 10 items exactly once, and every "
          "predicted item's same-trait partner is in the seed.",
          "5. The baseline arm was byte-compared, all 5,000 prompts, against the "
          "gate run before its completions were reused.",
          ""]

    # --- 7. Interpretation guide ---
    ratio = lift["mean"] / GATE["secondary"]["lift"]
    L += ["## 7. How to read this (interpretation guide)", "",
          "This probe asks one question: **when the twin is handed five of the "
          "person's own answers on the very same questionnaire — including, for "
          "every prediction, the item measuring the same trait — how much better "
          "than a demographics-only guess does it get?** That is close to the "
          "easiest individuating information the constructor could ever be given, "
          "so it acts as a ceiling on what this constructor can extract from "
          "person-specific data.", "",
          "A **large** within-scale lift (several times the cross-domain lift) "
          "would say the constructor works fine — it uses individuating "
          "information well when that information is on-topic — and the small "
          "+0.085 / +0.095 gate lift is then mostly a statement about the task: "
          "predicting personality from vocational interests is genuinely hard, and "
          "there may not be much more signal in interests to extract. Under that "
          "reading, effort belongs on richer or better-matched evidence, not on "
          "the constructor.", "",
          "A **small** within-scale lift (of the same order as the cross-domain "
          "lift, or smaller) would say the opposite: even handed the answer's own "
          "trait partner, the twin barely improves on MAE. That points at the "
          "constructor and the elicitation rather than the task, and it caps how "
          "much any Stage-2 result can be attributed to person-specific "
          "grounding. It would also mean the gate's small lift should not be read "
          "as evidence that vocational interests carry little personality signal "
          "— the pipeline may simply not be converting individuating facts into "
          "better-calibrated predictions.", "",
          f"**This run landed in the second case:** within-scale lift "
          f"{lift['mean']:+.4f} [{lift['ci_low']:+.4f}, {lift['ci_high']:+.4f}], "
          f"paired t p={_fmt_p(tests['t_p'])} — not significant, and "
          f"**smaller** than the gate's cross-domain "
          f"{GATE['secondary']['lift']:+.4f} on the same model, the same 500 "
          f"people, and the same baseline records (ratio {ratio:.2f}x). The "
          "easiest possible individuating evidence does not buy more MAE than "
          "vocational interests did.", "",
          "Section 5b says why, and it matters for what you conclude. The twin "
          "clearly **uses** the seed — predictions move, and rank agreement with "
          "the truth and exact-match accuracy both rise well above baseline. What "
          "it does not do is stay calibrated: it treats a reverse-scored item as "
          "a near-deterministic mirror of the item it was shown, commits hard, "
          "and eats a fat error tail when the person does not behave like the "
          "scoring key. So the honest reading of this probe is **not** \"the "
          "constructor cannot use person-specific information\"; it is \"the "
          "constructor over-extrapolates from it, and MAE — the pre-registered "
          "primary metric — does not reward that.\" A calibration or hedging fix "
          "to the elicitation is the indicated next lever, ahead of hunting for "
          "richer evidence.", "",
          "One consequence for Stage 2: expect this constructor's headline lift "
          "to stay small on MAE even when its inputs get much richer, and expect "
          "accuracy-style secondaries to look better than MAE. That is a property "
          "of the pipeline, established here, not a fact about any Stage-2 "
          "corpus. It carries no bar and revises no hypothesis.", "",
          "One caveat that limits both readings: seeded and cross-domain runs share "
          "the same baseline, so the comparison is fair, but the probe's seed is "
          "five items in the same scale format the model is being asked to "
          "produce. Some of any lift can be format mimicry (copying the person's "
          "response style or scale-use) rather than trait inference. The per-item "
          "table is where that shows up — mimicry should help roughly evenly, "
          "trait inference should concentrate on the seeded trait partner.", ""]

    # --- 8. Cost ---
    lines = _cost_lines(run_dir.name)
    L += ["## 8. Cost", "",
          "| run_id | backend | node_hours | twin tokens in | twin tokens out |",
          "|---|---|---|---|---|"]
    if lines:
        for entry in lines:
            L.append(f"| {entry['run_id']} | {entry.get('backend')} | "
                     f"{entry.get('node_hours')} | {entry.get('tokens_in')} | "
                     f"{entry.get('tokens_out')} |")
    else:
        L.append("| (no cost_log line found) | | | | |")
    L += ["",
          f"Baseline arm cost: **zero** — {totals['n_baseline_records']} "
          f"completions reused from `{cfg['baseline_source_run']}` rather than "
          "regenerated. Budget cap for this probe was 1 node-hour.", ""]

    # --- 9. Provenance ---
    L += ["## 9. Provenance", "",
          f"- Run dir: `results/{run_dir.name}/` — `records.jsonl` (full prompts "
          "and raw responses, both arms), `summary.json`, example prompts.",
          f"- Twin completions: `{cfg['completions_file']}`",
          f"- Baseline records: copied from `results/{cfg['baseline_source_run']}/"
          "records.jsonl` (arm=baseline).",
          "- Task builder: `experiments/probe_known_answer.py`; report builder: "
          "`experiments/probe_report.py`; tests: "
          "`tests/test_probe_known_answer.py`.",
          "- Gate numbers quoted in section 2 are frozen from "
          "`results/stage1_gate_report.md`.",
          ""]

    text = "\n".join(L)
    out_path.write_text(text, encoding="utf-8")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the known-answer probe report.")
    ap.add_argument("--run", required=True, help="probe run dir under results/")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    run_dir = Path(args.run).resolve()
    if not (run_dir / "summary.json").exists():
        print(f"[fatal] no summary.json in {run_dir}", file=sys.stderr)
        return 2
    build(run_dir, Path(args.out))
    print(f"[report] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
