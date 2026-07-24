"""Compare pilot2 runs across variants (v0/v1/v2) and models (gemini, qwen).

Auto-discovers pilot2 run dirs, reads their summary.json, and writes
``results/pilot2_comparison.md`` with, per variant x model: MAE lift [CI] with
t/Wilcoxon p-values, within-1 lift [CI], exact lift, parse failures and
exclusions, predicted-vs-true histograms per arm, and the per-item MAE-lift
table for both models side by side.

Graceful with missing runs: anything without a summary.json is marked PENDING
(the Gemini v1/v2 runs may still be in flight; Qwen may not be ingested yet).
Read-only; makes no API calls and writes only the comparison file.

Usage:
    uv run python experiments/compare_pilot2.py
    uv run python experiments/compare_pilot2.py --runs gemini:v0=results/DIR qwen:v1=results/DIR
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
RESULTS = _ROOT / "results"
OUT = RESULTS / "pilot2_comparison.md"
VARIANTS = ("v0", "v1", "v2")
MODELS = ("gemini", "qwen")
K = 48
EXPECTED = 1000


def _summary(run_dir: Path) -> dict | None:
    p = run_dir / "summary.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _model_of(summary: dict) -> str:
    backend = (summary.get("config") or {}).get("backend")
    return "gemini" if backend in (None, "gemini") else "qwen"


def discover() -> dict[tuple[str, str], Path]:
    """Map (variant, model) -> run dir, choosing the most-progressed per slot."""
    found: dict[tuple[str, str], tuple[int, Path]] = {}
    for variant in VARIANTS:
        for d in RESULTS.glob(f"pilot2_{variant}_k{K}_*"):
            if not d.is_dir():
                continue
            summ = _summary(d)
            if summ is None:
                # No summary yet (e.g. in-flight Gemini). Classify by dir name.
                model = "gemini" if re.match(
                    rf"pilot2_{variant}_k{K}_\d{{8}}-\d{{6}}$", d.name) else "qwen"
                n = 0
            else:
                model = _model_of(summ)
                n = (summ.get("totals") or {}).get("n_records", 0)
            key = (variant, model)
            if key not in found or n > found[key][0]:
                found[key] = (n, d)
    return {k: v[1] for k, v in found.items()}


def _fmt_lift(block: dict | None) -> str:
    if not block:
        return "-"
    lift = block.get("lift", {})
    m, lo, hi = lift.get("mean"), lift.get("ci_low"), lift.get("ci_high")
    if m is None:
        return "-"
    ci = "" if lo is None or (isinstance(lo, float) and lo != lo) \
        else f" [{lo:+.3f}, {hi:+.3f}]"
    return f"{m:+.3f}{ci}"


def _fmt_p(block: dict | None, key: str) -> str:
    if not block:
        return "-"
    p = (block.get("tests") or {}).get(key)
    if p is None or (isinstance(p, float) and p != p):
        return "-"
    return f"{p:.3g}"


def _hist_table(hist: dict) -> list[str]:
    header = "| arm/series | " + " | ".join(str(i) for i in range(1, 8)) + " |"
    sep = "|" + "---|" * 8
    rows = [header, sep]
    for arm in ("twin", "baseline"):
        for series in ("predicted", "true"):
            counts = (hist.get(arm) or {}).get(series, {})
            cells = " | ".join(str(counts.get(str(i), counts.get(i, 0)))
                               for i in range(1, 8))
            rows.append(f"| {arm} {series} | {cells} |")
    return rows


def build_report(runs: dict[tuple[str, str], Path]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [f"# pilot2 comparison: Gemini vs Qwen\n\nGenerated {now}\n"]

    # Availability.
    out.append("## Runs discovered\n")
    out.append("| variant | model | dir | records | status |")
    out.append("|---|---|---|---|---|")
    summaries: dict[tuple[str, str], dict] = {}
    for variant in VARIANTS:
        for model in MODELS:
            d = runs.get((variant, model))
            if d is None:
                out.append(f"| {variant} | {model} | - | - | PENDING |")
                continue
            summ = _summary(d)
            if summ is None:
                out.append(f"| {variant} | {model} | {d.name} | ? | "
                           "in flight (no summary) |")
                continue
            summaries[(variant, model)] = summ
            n = (summ.get("totals") or {}).get("n_records", 0)
            status = "complete" if n >= EXPECTED else f"partial {n}/{EXPECTED}"
            out.append(f"| {variant} | {model} | {d.name} | {n} | {status} |")
    out.append("")

    # Metrics table.
    out.append("## Metrics (lift = twin better)\n")
    out.append("| variant | model | MAE lift [95% CI] | p(t) | p(Wilcoxon) | "
               "within-1 lift [CI] | exact lift | parse fails | exclusions |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for variant in VARIANTS:
        for model in MODELS:
            summ = summaries.get((variant, model))
            if summ is None:
                out.append(f"| {variant} | {model} | PENDING | - | - | - | - | - | - |")
                continue
            sc = summ.get("scoring", {})
            totals = summ.get("totals", {})
            out.append(
                f"| {variant} | {model} | {_fmt_lift(sc.get('mae'))} | "
                f"{_fmt_p(sc.get('mae'), 't_p')} | "
                f"{_fmt_p(sc.get('mae'), 'wilcoxon_p')} | "
                f"{_fmt_lift(sc.get('within1'))} | {_fmt_lift(sc.get('exact'))} | "
                f"{totals.get('n_parse_failures', '-')} | "
                f"{sc.get('n_excluded_pairs', '-')} |")
    out.append("")

    # Per-variant detail: histograms + per-item MAE-lift.
    for variant in VARIANTS:
        out.append(f"## {variant} detail\n")
        any_model = False
        for model in MODELS:
            summ = summaries.get((variant, model))
            if summ is None:
                out.append(f"### {model}: PENDING\n")
                continue
            any_model = True
            out.append(f"### {model} — predicted vs true histogram\n")
            out += _hist_table((summ.get("scoring") or {}).get("histograms", {}))
            out.append("")

        # Per-item MAE-lift, gemini vs qwen side by side.
        g = summaries.get((variant, "gemini"))
        q = summaries.get((variant, "qwen"))
        if g or q:
            out.append(f"### {variant} per-item MAE lift (gemini | qwen)\n")
            out.append("| item | gemini MAE lift | qwen MAE lift |")
            out.append("|---|---|---|")
            gmap = {r["item"]: r["mae_lift"]
                    for r in ((g or {}).get("scoring", {}) or {}).get("per_item", [])}
            qmap = {r["item"]: r["mae_lift"]
                    for r in ((q or {}).get("scoring", {}) or {}).get("per_item", [])}
            items = sorted(set(gmap) | set(qmap)) or [f"TIPI{i}" for i in range(1, 11)]
            for it in items:
                gv = f"{gmap[it]:+.3f}" if it in gmap else "-"
                qv = f"{qmap[it]:+.3f}" if it in qmap else "-"
                out.append(f"| {it} | {gv} | {qv} |")
            out.append("")
        if not any_model:
            out.append("_No runs available for this variant yet._\n")

    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare pilot2 Gemini vs Qwen runs.")
    ap.add_argument("--runs", nargs="*", default=[],
                    help="explicit overrides like gemini:v0=results/DIR")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    runs = discover()
    for token in args.runs:
        try:
            key, path = token.split("=", 1)
            model, variant = key.split(":", 1)
        except ValueError:
            print(f"[warn] bad --runs token {token!r}; expected model:variant=DIR",
                  file=sys.stderr)
            continue
        runs[(variant, model)] = Path(path)

    report = build_report(runs)
    Path(args.out).write_text(report, encoding="utf-8")
    n = len(runs)
    print(f"[compare] wrote {args.out} ({n} run dir(s) discovered)")
    for (variant, model), d in sorted(runs.items()):
        print(f"[compare]   {variant} {model}: {d.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
