"""Build the Stage-1 gate report from a primary and a secondary run dir.

Analysis only, no API calls. Everything is a mechanical rule applied to the
runs' summary.json / records.jsonl / cost_log.jsonl; the only prose is the
verbatim quoted bar and pre-commitment. Exploratory sections are labelled.

The gate bar and the promotion pre-commitment are quoted verbatim from
results/stage1_gate_note.md and applied mechanically:
  * GATE PASS  iff  primary MAE lift > 0 AND paired-t p < 0.05.
  * PROMOTED   iff  secondary MAE lift > 0 AND paired-t p < 0.05.

Usage:
    uv run python experiments/gate_report.py --primary results/<gemini_gate_dir> \\
        --secondary results/<gemma_gate_dir>

Calibration figure: matplotlib is NOT a dependency, so the reliability curve is
emitted as an ASCII table only (no PNG).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from doppler.scoring import v2_probabilities  # noqa: E402

DEFAULT_COST_LOG = _ROOT / "results" / "cost_log.jsonl"
DEFAULT_OUT = _ROOT / "results" / "stage1_gate_report.md"
SIG = 0.05
N_BINS = 10
UNIFORM = 1.0 / 7.0

# Verbatim from results/stage1_gate_note.md, "Bar (frozen, from PREREGISTRATION.md)".
BAR_TEXT = (
    "The gate passes iff the PRIMARY arm shows twin lift over the "
    "demographics-only baseline that is positive and significant (MAE lift > 0; "
    "paired t-test p < .05 across the 500 persons; Wilcoxon reported alongside)."
)

# Verbatim from results/stage1_gate_note.md, "Pre-commitment on the secondary arm".
PRECOMMITMENT_TEXT = (
    "- If the secondary (Gemma-4 + v2) shows positive AND significant MAE lift\n"
    "  (same test, p < .05) at n=500: Gemma-4-31B-it + v2 becomes the primary\n"
    "  simulation model for all later stages (speed + cost), with Gemini demoted\n"
    "  to robustness checks.\n"
    "- If not: Gemini stays primary and the open-model failure to use\n"
    "  individuating information is a documented Stage 1 finding.\n"
    "- The gate pass/fail verdict itself depends ONLY on the primary arm."
)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_summary(run_dir: str | Path) -> dict:
    return json.loads((Path(run_dir) / "summary.json").read_text(encoding="utf-8"))


def load_records(run_dir: str | Path) -> list[dict]:
    recs = []
    with (Path(run_dir) / "records.jsonl").open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def load_cost_lines(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    lines = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    return lines


# ---------------------------------------------------------------------------
# Mechanical verdicts
# ---------------------------------------------------------------------------


def _positive_and_significant(summary: dict) -> bool:
    mae = summary["scoring"]["mae"]
    mean = mae["lift"]["mean"]
    p = mae["tests"]["t_p"]
    return (mean is not None and mean > 0) and (p is not None and p < SIG)


def gate_pass(summary: dict) -> bool:
    """GATE PASS iff primary MAE lift > 0 AND paired-t p < 0.05."""
    return _positive_and_significant(summary)


def promotion_pass(secondary_summary: dict) -> bool:
    """PROMOTED iff secondary MAE lift > 0 AND paired-t p < 0.05."""
    return _positive_and_significant(secondary_summary)


# ---------------------------------------------------------------------------
# Calibration (exploratory)
# ---------------------------------------------------------------------------


def v2_calibration_pairs(records: list[dict]) -> list[tuple[dict[int, float], int]]:
    """Twin, non-failed, v2 records -> (normalized prob vector, true answer)."""
    pairs = []
    for r in records:
        if r.get("arm") != "twin" or r.get("parse_failure") or r.get("variant") != "v2":
            continue
        probs = v2_probabilities(r.get("raw_response"))
        if probs is None:
            continue
        pairs.append((probs, int(r["true_answer"])))
    return pairs


def calibration(pairs: list[tuple[dict[int, float], int]]) -> dict:
    """Reliability bins + ECE from (prob-vector, true) pairs.

    Each answer option's stated probability is a confidence; the event is
    "this option was the true answer". Ten equal-width bins over [0, 1];
    ECE = sum_b (n_b / N) * |mean_conf_b - freq_b|.
    """
    acc = [{"sum_conf": 0.0, "sum_event": 0.0, "n": 0} for _ in range(N_BINS)]
    total = 0
    true_probs = []
    for probs, true in pairs:
        true_probs.append(probs[true])
        for k in range(1, 8):
            p = probs[k]
            idx = min(int(p * N_BINS), N_BINS - 1)
            acc[idx]["sum_conf"] += p
            acc[idx]["sum_event"] += 1.0 if k == true else 0.0
            acc[idx]["n"] += 1
            total += 1

    bins, ece = [], 0.0
    for i, b in enumerate(acc):
        if b["n"] > 0:
            mc = b["sum_conf"] / b["n"]
            fr = b["sum_event"] / b["n"]
            ece += (b["n"] / total) * abs(mc - fr)
        else:
            mc = fr = None
        bins.append({"lo": i / N_BINS, "hi": (i + 1) / N_BINS,
                     "n": b["n"], "mean_conf": mc, "freq": fr})

    return {
        "n_records": len(pairs),
        "n_pairs": total,
        "ece": ece if total else None,
        "mean_true_prob": (sum(true_probs) / len(true_probs)) if true_probs else None,
        "uniform": UNIFORM,
        "bins": bins,
    }


# ---------------------------------------------------------------------------
# Cost ledger
# ---------------------------------------------------------------------------


def cost_ledger(lines: list[dict], gate_run_ids: set[str]) -> dict:
    gate = [ln for ln in lines if ln.get("run_id") in gate_run_ids]
    totals = {
        "gemini_calls": sum(int(ln.get("n_calls", 0) or 0)
                            for ln in lines if ln.get("backend") == "gemini"),
        "usd": sum(float(ln["cost_usd"]) for ln in lines
                   if ln.get("cost_usd") is not None),
        "node_hours": sum(float(ln["node_hours"]) for ln in lines
                          if ln.get("node_hours") is not None),
    }
    return {"gate_lines": gate, "totals": totals}


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _f(x, nd: int = 4) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"{x:.{nd}f}"


def _p(x) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"{x:.3g}"


def _lift(summary: dict, metric: str) -> str:
    b = summary["scoring"][metric]["lift"]
    return f"{_f(b['mean'])} [{_f(b['ci_low'])}, {_f(b['ci_high'])}]"


def _item_num(item: str) -> int:
    digits = "".join(ch for ch in item if ch.isdigit())
    return int(digits) if digits else 0


def _hist_rows(summary: dict, arm: str) -> list[str]:
    hist = (summary.get("scoring") or {}).get("histograms", {}).get(arm, {})
    rows = []
    for series in ("predicted", "true"):
        counts = hist.get(series, {})
        cells = " | ".join(str(counts.get(str(i), counts.get(i, 0)))
                           for i in range(1, 8))
        rows.append(f"| {arm} {series} | {cells} |")
    return rows


def _verdict_block(label: str, run_dir: Path, summary: dict) -> list[str]:
    mae = summary["scoring"]["mae"]
    totals = summary.get("totals", {})
    return [
        f"- Run dir: `{run_dir.name}`",
        f"- MAE lift: {_lift(summary, 'mae')}",
        f"- paired t: t={_f(mae['tests']['t_stat'])}, p={_p(mae['tests']['t_p'])}",
        f"- Wilcoxon: W={_f(mae['tests']['wilcoxon_stat'])}, "
        f"p={_p(mae['tests']['wilcoxon_p'])}",
        f"- within-1 lift: {_lift(summary, 'within1')}",
        f"- exact lift: {_lift(summary, 'exact')}",
        f"- persons scored: {summary['scoring'].get('n_persons', 'n/a')}; "
        f"parse failures: {totals.get('n_parse_failures', 'n/a')}; "
        f"exclusions: {summary['scoring'].get('n_excluded_pairs', 'n/a')}",
    ]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def build_report(primary_dir: Path, secondary_dir: Path, cost_log: Path) -> str:
    primary = load_summary(primary_dir)
    secondary = load_summary(secondary_dir)

    passed = gate_pass(primary)
    promoted = promotion_pass(secondary)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [f"# Stage 1 gate report\n\nGenerated {now}\n"]

    # 1. Primary verdict.
    out.append("## 1. Primary verdict\n")
    out += _verdict_block("primary", primary_dir, primary)
    out.append("")
    out.append(f"Bar (verbatim, stage1_gate_note.md): {BAR_TEXT}")
    out.append("")
    out.append(f"GATE: {'PASS' if passed else 'FAIL'}  "
               "(rule: MAE lift > 0 AND paired-t p < 0.05)")
    out.append("")

    # 2. Secondary verdict + promotion.
    out.append("## 2. Secondary verdict and promotion decision\n")
    out += _verdict_block("secondary", secondary_dir, secondary)
    out.append("")
    out.append("Pre-commitment (verbatim, stage1_gate_note.md):\n")
    out += ["> " + ln for ln in PRECOMMITMENT_TEXT.splitlines()]
    out.append("")
    decision = ("PROMOTED: Gemma-4+v2 primary for future stages" if promoted
                else "NOT PROMOTED: Gemini stays primary")
    out.append(f"{decision}  "
               "(rule: secondary MAE lift > 0 AND paired-t p < 0.05)")
    out.append("")

    # 3. Per-item table.
    out.append("## 3. Per-item MAE (primary | secondary)\n")
    out.append("| item | pri twin MAE | pri base MAE | pri MAE lift | "
               "sec twin MAE | sec base MAE | sec MAE lift |")
    out.append("|---|---|---|---|---|---|---|")
    pri_items = {r["item"]: r for r in primary["scoring"].get("per_item", [])}
    sec_items = {r["item"]: r for r in secondary["scoring"].get("per_item", [])}
    for item in sorted(set(pri_items) | set(sec_items), key=_item_num):
        pr = pri_items.get(item, {})
        se = sec_items.get(item, {})
        out.append(
            f"| {item} | {_f(pr.get('twin_mae'))} | {_f(pr.get('baseline_mae'))} | "
            f"{_f(pr.get('mae_lift'))} | {_f(se.get('twin_mae'))} | "
            f"{_f(se.get('baseline_mae'))} | {_f(se.get('mae_lift'))} |")
    out.append("")

    # 4. Histograms.
    out.append("## 4. Predicted (argmax) vs true histograms\n")
    for label, summ in (("primary", primary), ("secondary", secondary)):
        for arm in ("twin", "baseline"):
            out.append(f"### {label} {arm}\n")
            out.append("| series | 1 | 2 | 3 | 4 | 5 | 6 | 7 |")
            out.append("|" + "---|" * 8)
            out += _hist_rows(summ, arm)
            out.append("")

    # 5. Calibration (exploratory).
    out.append("## 5. Calibration diagnostic (EXPLORATORY)\n")
    out.append("_Exploratory; from the primary arm's v2 twin records. "
               "matplotlib is not a dependency, so this is an ASCII reliability "
               "table only (no PNG)._\n")
    try:
        pairs = v2_calibration_pairs(load_records(primary_dir))
    except FileNotFoundError:
        pairs = []
    if not pairs:
        out.append("Calibration N/A: no parseable v2 twin distributions in the "
                   "primary run.")
    else:
        cal = calibration(pairs)
        out.append(f"- records: {cal['n_records']}; option-pairs: {cal['n_pairs']}")
        out.append(f"- ECE (weighted |conf - freq|): {_f(cal['ece'])}")
        out.append(f"- mean stated prob of the true answer: "
                   f"{_f(cal['mean_true_prob'])} vs uniform 1/7 = {_f(UNIFORM)}")
        out.append("")
        out.append("| bin | n | mean stated prob | empirical freq true |")
        out.append("|---|---|---|---|")
        for b in cal["bins"]:
            out.append(f"| [{b['lo']:.1f}, {b['hi']:.1f}) | {b['n']} | "
                       f"{_f(b['mean_conf'])} | {_f(b['freq'])} |")
    out.append("")

    # 6. Cost ledger.
    out.append("## 6. Cost ledger\n")
    ledger = cost_ledger(load_cost_lines(cost_log),
                         {primary_dir.name, secondary_dir.name})
    out.append("Gate-run cost lines:\n")
    if not ledger["gate_lines"]:
        out.append("_No cost_log lines matched the two gate run dirs._")
    else:
        out.append("| run_id | backend | n_calls | cost_usd | node_hours |")
        out.append("|---|---|---|---|---|")
        for ln in ledger["gate_lines"]:
            out.append(f"| {ln.get('run_id')} | {ln.get('backend')} | "
                       f"{ln.get('n_calls')} | {ln.get('cost_usd')} | "
                       f"{ln.get('node_hours')} |")
    out.append("")
    t = ledger["totals"]
    out.append("Project totals to date (all cost_log lines):")
    out.append(f"- total Gemini calls: {t['gemini_calls']}")
    out.append(f"- total $ (sum cost_usd): {_f(t['usd'])}")
    out.append(f"- total node-hours: {_f(t['node_hours'])}")
    out.append("")

    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the Stage-1 gate report.")
    ap.add_argument("--primary", required=True, metavar="DIR")
    ap.add_argument("--secondary", required=True, metavar="DIR")
    ap.add_argument("--cost-log", default=str(DEFAULT_COST_LOG))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    report = build_report(Path(args.primary), Path(args.secondary),
                          Path(args.cost_log))
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"[gate-report] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
