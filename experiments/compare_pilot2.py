"""Compare pilot2 runs across variants (v0/v1/v2) and N models.

Each run's model identity is a label:
  * Gemini runs (no backend, or backend "gemini") -> ``gemini``.
  * Batch-ingested runs -> the summary config's ``model_label`` if set, else the
    ``backend`` name mapped through an explicit alias table (so the three
    existing runs stored as backend "leonardo-batch" read as the Qwen model
    without rewriting their files).

Auto-discovers pilot2 run dirs and writes ``results/pilot2_comparison.md``:
  * one main table, rows = model x variant: MAE lift [CI], t/Wilcoxon p,
    within-1 lift, exact lift, parse-fails/exclusions;
  * a histograms section per model x variant x arm;
  * a wide per-item MAE-lift table (items as rows, model x variant as columns),
    for the models actually present.

Missing runs are marked PENDING. Read-only; writes only the comparison file.

Usage:
    uv run python experiments/compare_pilot2.py
    uv run python experiments/compare_pilot2.py --runs leonardo-llama70b:v0=results/DIR
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
K = 48
EXPECTED = 1000

#: Legacy backend names -> per-model labels (files are not rewritten).
BACKEND_LABEL_ALIASES = {"leonardo-batch": "leonardo-qwen3.6-27b"}


def _summary(run_dir: Path) -> dict | None:
    p = run_dir / "summary.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def label_of(summary: dict) -> str:
    """Resolve a run's model label from its summary config."""
    cfg = summary.get("config") or {}
    backend = cfg.get("backend")
    if backend in (None, "gemini"):
        return "gemini"
    if cfg.get("model_label"):
        return cfg["model_label"]
    return BACKEND_LABEL_ALIASES.get(backend, backend)


def discover() -> dict[tuple[str, str], Path]:
    """Map (variant, label) -> most-progressed run dir."""
    found: dict[tuple[str, str], tuple[int, Path]] = {}
    for variant in VARIANTS:
        for d in RESULTS.glob(f"pilot2_{variant}_k{K}_*"):
            if not d.is_dir():
                continue
            summ = _summary(d)
            if summ is None:
                # In-flight run with no summary yet: only a pure-timestamp name
                # is unambiguously a Gemini run; skip summaryless batch dirs.
                if re.match(rf"pilot2_{variant}_k{K}_\d{{8}}-\d{{6}}$", d.name):
                    label, n = "gemini", 0
                else:
                    continue
            else:
                label = label_of(summ)
                n = (summ.get("totals") or {}).get("n_records", 0)
            key = (variant, label)
            if key not in found or n > found[key][0]:
                found[key] = (n, d)
    return {k: v[1] for k, v in found.items()}


def _ordered_models(runs: dict[tuple[str, str], Path]) -> list[str]:
    labels = {label for (_v, label) in runs}
    labels.add("gemini")
    others = sorted(labels - {"gemini"})
    return ["gemini", *others]


# --- formatting helpers ---------------------------------------------------


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


def _hist_rows(hist: dict) -> list[str]:
    header = "| arm/series | " + " | ".join(str(i) for i in range(1, 8)) + " |"
    rows = [header, "|" + "---|" * 8]
    for arm in ("twin", "baseline"):
        for series in ("predicted", "true"):
            counts = (hist.get(arm) or {}).get(series, {})
            cells = " | ".join(str(counts.get(str(i), counts.get(i, 0)))
                               for i in range(1, 8))
            rows.append(f"| {arm} {series} | {cells} |")
    return rows


# --- report ---------------------------------------------------------------


def build_report(runs: dict[tuple[str, str], Path]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    models = _ordered_models(runs)
    summaries: dict[tuple[str, str], dict] = {}
    for (variant, label), d in runs.items():
        summ = _summary(d)
        if summ is not None:
            summaries[(label, variant)] = summ

    out = [f"# pilot2 comparison across models\n\nGenerated {now}\n"]

    # Runs discovered.
    out += ["## Runs discovered\n",
            "| model | variant | dir | records | status |",
            "|---|---|---|---|---|"]
    for model in models:
        for variant in VARIANTS:
            d = runs.get((variant, model))
            if d is None:
                out.append(f"| {model} | {variant} | - | - | PENDING |")
                continue
            summ = _summary(d)
            if summ is None:
                out.append(f"| {model} | {variant} | {d.name} | ? | "
                           "in flight (no summary) |")
                continue
            n = (summ.get("totals") or {}).get("n_records", 0)
            status = "complete" if n >= EXPECTED else f"partial {n}/{EXPECTED}"
            out.append(f"| {model} | {variant} | {d.name} | {n} | {status} |")
    out.append("")

    # Main metrics table.
    out += ["## Metrics (lift = twin better)\n",
            "| model | variant | MAE lift [95% CI] | p(t) | p(Wilcoxon) | "
            "within-1 lift [CI] | exact lift | parse fails | exclusions |",
            "|---|---|---|---|---|---|---|---|---|"]
    for model in models:
        for variant in VARIANTS:
            summ = summaries.get((model, variant))
            if summ is None:
                out.append(f"| {model} | {variant} | PENDING | - | - | - | - | - | - |")
                continue
            sc = summ.get("scoring", {})
            totals = summ.get("totals", {})
            out.append(
                f"| {model} | {variant} | {_fmt_lift(sc.get('mae'))} | "
                f"{_fmt_p(sc.get('mae'), 't_p')} | "
                f"{_fmt_p(sc.get('mae'), 'wilcoxon_p')} | "
                f"{_fmt_lift(sc.get('within1'))} | {_fmt_lift(sc.get('exact'))} | "
                f"{totals.get('n_parse_failures', '-')} | "
                f"{sc.get('n_excluded_pairs', '-')} |")
    out.append("")

    # Histograms per model x variant x arm.
    out.append("## Predicted-vs-true histograms\n")
    for model in models:
        for variant in VARIANTS:
            summ = summaries.get((model, variant))
            if summ is None:
                continue
            out.append(f"### {model} {variant}\n")
            out += _hist_rows((summ.get("scoring") or {}).get("histograms", {}))
            out.append("")

    # Wide per-item MAE-lift table.
    present = [(model, variant) for model in models for variant in VARIANTS
               if summaries.get((model, variant))
               and (summaries[(model, variant)].get("scoring") or {}).get("per_item")]
    out.append("## Per-item MAE lift (wide)\n")
    if not present:
        out.append("_No scored runs with a per-item table yet._\n")
    else:
        cols = [f"{m} {v}" for (m, v) in present]
        out.append("| item | " + " | ".join(cols) + " |")
        out.append("|" + "---|" * (len(cols) + 1))
        maps = {
            (m, v): {r["item"]: r["mae_lift"]
                     for r in summaries[(m, v)]["scoring"]["per_item"]}
            for (m, v) in present
        }
        items = sorted({it for mp in maps.values() for it in mp},
                       key=lambda s: (len(s), s)) or [f"TIPI{i}" for i in range(1, 11)]
        for it in items:
            cells = " | ".join(
                (f"{maps[(m, v)][it]:+.3f}" if it in maps[(m, v)] else "-")
                for (m, v) in present)
            out.append(f"| {it} | {cells} |")
        out.append("")

    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare pilot2 runs across models.")
    ap.add_argument("--runs", nargs="*", default=[],
                    help="explicit overrides like leonardo-llama70b:v0=results/DIR")
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

    Path(args.out).write_text(build_report(runs), encoding="utf-8")
    print(f"[compare] wrote {args.out} ({len(runs)} run dir(s) discovered)")
    for (variant, model), d in sorted(runs.items()):
        print(f"[compare]   {model} {variant}: {d.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
