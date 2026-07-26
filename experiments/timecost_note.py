"""Reproduce results/stage1e_timecost_note.md: Stage 1E budgets priced in seconds.

Descriptive re-analysis of closed Stage 1E data. CPU only, no API calls, no GPU.
Nothing here re-opens a frozen bar: the lift values are read verbatim out of
``results/stage1e_confirm/analysis.json`` and only the x-axis (items -> cumulative
respondent-seconds) is new.

What it does, in the order the note presents it:

  1. Builds a seconds-per-Likert-item cost model from MACH-IV's per-item response
     times (``data/mach/MACH_data/data.csv``, columns ``QnE`` elapsed ms and
     ``QnI`` presentation position). MACH presented its 20 items ONE AT A TIME in
     a RANDOMISED order, which is why it is the donor: the presentation protocol
     matches Stage 1E's reveals, and randomisation leaves position effects
     unconfounded with item identity.
  2. Trims to 500 ms <= RT <= 60 s (the documented rule) and reports the headline
     figure under four alternative rules, because the sensitivity IS the result
     that licenses the rule.
  3. Fits median RT against item text length across the 20 items and rescales to
     RIASEC's shorter items -- the largest single correction in the chain.
  4. Cross-checks that rescaling against RIASEC's own ``testelapse`` page timer,
     an independent route to the same quantity on the right instrument.
  5. Re-expresses the frozen k grid {1,2,4,8,12,16,20} as cumulative respondent
     time and prints the note's tables under both decodings.
  6. Prices the one asymmetry item counts hide: an adaptive interviewer makes the
     respondent wait while it scores candidates; a static script waits zero.

Two guards, in the spirit of experiments/confirm_report.py:

  * No lift number is typed into this file. Every one is read from analysis.json,
    and the arms/checkpoints are validated against the frozen grid on load.
  * ``--check`` asserts the headline figures still match the ones written into
    results/stage1e_timecost_note.md, so the note and the code cannot drift
    apart silently. It aborts rather than print a number the note contradicts.

The figure needs matplotlib, which is NOT a project dependency (see
pyproject.toml). It is imported lazily and only under ``--figure``; every table
reproduces without it.

Usage:
    uv run --no-project python experiments/timecost_note.py --check
    uv run --no-project --with matplotlib python experiments/timecost_note.py --figure
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MACH_CSV = ROOT / "data/mach/MACH_data/data.csv"
RIASEC_CSV = ROOT / "data/riasec/data.csv"
ANALYSIS_JSON = ROOT / "results/stage1e_confirm/analysis.json"
FIGURE_PNG = ROOT / "results/stage1e_timecost_curves.png"

K_GRID = [1, 2, 4, 8, 12, 16, 20]
ARMS = ["random", "fixed", "adaptive", "imposter"]
DECODINGS = [("expected_value", "expected-value (pre-registered primary)"),
             ("argmax", "argmax (binding robustness check)")]
N_MACH_ITEMS = 20

# Trim rules as (label, lo_ms, hi_ms); None/None means no trim.
TRIM_PRIMARY = ("500 ms - 60 s (primary)", 500, 60_000)
TRIM_RULES = [
    ("none (all values)", None, None),
    ("300 ms - 120 s", 300, 120_000),
    TRIM_PRIMARY,
    ("750 ms - 45 s", 750, 45_000),
    ("1 s - 30 s", 1000, 30_000),
]

# RIASEC testelapse is a whole-page timer for all 48 items; trim to a plausible
# sitting (0.5 s/item at the fast end, 40 minutes at the slow end).
RIASEC_TE_LO_S, RIASEC_TE_HI_S = 24, 2400
RIASEC_N_ITEMS = 48

# Adaptive-arm ledger, quoted from results/stage1e_findings.md section (b).
ADAPTIVE_SELECTION_CALLS = 770_000
ADAPTIVE_TOTAL_CALLS = 840_000
ADAPTIVE_NODE_HOURS = 3.928
CONFIRM_N_PERSONS = 1_000
POOL_SIZE = 48  # RIASEC interest items available to reveal

# Item texts, transcribed from the two codebooks (data/*/codebook.txt). Only the
# character counts are used, and --check re-verifies them against the codebooks.
MACH_ITEM_TEXT = {
    1: "Never tell anyone the real reason you did something unless it is useful to do so.",
    2: "The best way to handle people is to tell them what they want to hear.",
    3: "One should take action only when sure it is morally right.",
    4: "Most people are basically good and kind.",
    5: "It is safest to assume that all people have a vicious streak and it will come out when they are given a chance.",
    6: "Honesty is the best policy in all cases.",
    7: "There is no excuse for lying to someone else.",
    8: "Generally speaking, people won't work hard unless they're forced to do so.",
    9: "All in all, it is better to be humble and honest than to be important and dishonest.",
    10: "When you ask someone to do something for you, it is best to give the real reasons for wanting it rather than giving reasons which carry more weight.",
    11: "Most people who get ahead in the world lead clean, moral lives.",
    12: "Anyone who completely trusts anyone else is asking for trouble.",
    13: "The biggest difference between most criminals and other people is that the criminals are stupid enough to get caught.",
    14: "Most people are brave.",
    15: "It is wise to flatter important people.",
    16: "It is possible to be good in all respects.",
    17: "P.T. Barnum was wrong when he said that there's a sucker born every minute.",
    18: "It is hard to get ahead without cutting corners here and there.",
    19: "People suffering from incurable diseases should have the choice of being put painlessly to death.",
    20: "Most people forget more easily the death of their parents than the loss of their property.",
}

RIASEC_ITEM_TEXT = [
    "Test the quality of parts before shipment", "Lay brick or tile",
    "Work on an offshore oil-drilling rig", "Assemble electronic parts",
    "Operate a grinding machine in a factory", "Fix a broken faucet",
    "Assemble products in a factory", "Install flooring in houses",
    "Study the structure of the human body", "Study animal behavior",
    "Do research on plants or animals", "Develop a new medical treatment or procedure",
    "Conduct biological research", "Study whales and other types of marine life",
    "Work in a biology lab", "Make a map of the bottom of an ocean",
    "Conduct a musical choir", "Direct a play", "Design artwork for magazines",
    "Write a song", "Write books or plays", "Play a musical instrument",
    "Perform stunts for a movie or television show", "Design sets for plays",
    "Give career guidance to people", "Do volunteer work at a non-profit organization",
    "Help people who have problems with drugs or alcohol",
    "Teach an individual an exercise routine", "Help people with family-related problems",
    "Supervise the activities of children at a camp", "Teach children how to read",
    "Help elderly people with their daily activities",
    "Sell restaurant franchises to individuals", "Sell merchandise at a department store",
    "Manage the operations of a hotel", "Operate a beauty salon or barber shop",
    "Manage a department within a large company", "Manage a clothing store",
    "Sell houses", "Run a toy store",
    "Generate the monthly payroll checks for an office",
    "Inventory supplies using a hand-held computer",
    "Use a computer program to generate customer bills", "Maintain employee records",
    "Compute and record statistical and other numerical data", "Operate a calculator",
    "Handle customers' bank transactions", "Keep shipping and receiving records",
]

# Headline figures as written into results/stage1e_timecost_note.md. --check
# asserts the recomputation still lands on them, to within the note's own
# rounding. Drift here means the note is wrong, not the tolerance.
NOTE_CLAIMS = {
    "pct_kept_primary": (98.68, 0.01),
    "median_of_item_medians_primary_s": (6.78, 0.01),
    "trim_spread_s": (0.10, 0.005),
    "spearman_len_vs_rt": (0.92, 0.005),
    "mach_mean_chars": (71.05, 0.05),
    "riasec_mean_chars": (32.46, 0.05),
    "length_scale": (0.656, 0.001),
    "per_item_length_adjusted_s": (4.65, 0.01),
    "riasec_per_item_s": (4.85, 0.01),
    "riasec_median_total_s": (233.0, 0.5),
    "cum20_central_s": (91.6, 0.05),
    "cum12_central_s": (57.9, 0.05),
    "cum20_mach_direct_s": (139.7, 0.05),
    "selection_calls_per_person": (770, 0),
    "marginal_late_item_s": (4.17, 0.01),
}


# --------------------------------------------------------------------- helpers
def quantile(sorted_xs: list[float], q: float) -> float:
    """Linear-interpolation quantile over an already-sorted sequence."""
    if not sorted_xs:
        return float("nan")
    if len(sorted_xs) == 1:
        return float(sorted_xs[0])
    pos = q * (len(sorted_xs) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return float(sorted_xs[lo])
    return float(sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (pos - lo))


def pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    return num / (da * db) if da and db else float("nan")


def _ranks(v: list[float]) -> list[float]:
    order = sorted(range(len(v)), key=lambda i: v[i])
    out = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def spearman(a: list[float], b: list[float]) -> float:
    return pearson(_ranks(a), _ranks(b))


def ols(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Return (intercept, slope) of the least-squares line y ~ x."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    return my - slope * mx, slope


def trimmed(vals, lo, hi):
    return list(vals) if lo is None else [v for v in vals if lo <= v <= hi]


# ------------------------------------------------------------------ data loads
def load_mach():
    """Return (per_item_ms, per_position_ms, respondent_by_position, n_rows)."""
    if not MACH_CSV.exists():
        raise SystemExit(
            f"missing {MACH_CSV}\n"
            "Download it (data/ is gitignored, so it is not in the repo):\n"
            "  curl -L -o data/mach/MACH_data.zip "
            "https://openpsychometrics.org/_rawdata/MACH_data.zip\n"
            "  cd data/mach && unzip MACH_data.zip"
        )
    per_item = {i: [] for i in range(1, N_MACH_ITEMS + 1)}
    per_pos = {p: [] for p in range(1, N_MACH_ITEMS + 1)}
    respondents = []
    n_rows = 0
    with MACH_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for rec in csv.DictReader(fh, delimiter="\t"):
            n_rows += 1
            by_pos, complete = {}, True
            for i in range(1, N_MACH_ITEMS + 1):
                try:
                    ms = int(rec[f"Q{i}E"])
                    pos = int(rec[f"Q{i}I"])
                except (TypeError, ValueError):
                    complete = False
                    continue
                per_item[i].append(ms)
                if 1 <= pos <= N_MACH_ITEMS:
                    per_pos[pos].append(ms)
                    by_pos[pos] = ms
                else:
                    complete = False
            if complete and len(by_pos) == N_MACH_ITEMS:
                respondents.append(by_pos)
    return per_item, per_pos, respondents, n_rows


def load_riasec_testelapse() -> list[float]:
    if not RIASEC_CSV.exists():
        raise SystemExit(f"missing {RIASEC_CSV} (data/ is gitignored; see data/riasec/PROVENANCE.txt)")
    out = []
    with RIASEC_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for rec in csv.DictReader(fh, delimiter="\t"):
            try:
                out.append(float(rec["testelapse"]))
            except (TypeError, ValueError):
                continue
    return out


def load_lifts() -> dict:
    """Lift per arm per k per decoding, straight out of the frozen artifact."""
    if not ANALYSIS_JSON.exists():
        raise SystemExit(f"missing {ANALYSIS_JSON}")
    blob = json.loads(ANALYSIS_JSON.read_text())["lift_over_baseline"]
    lifts = {}
    for dec, _ in DECODINGS:
        if dec not in blob:
            raise SystemExit(f"analysis.json has no '{dec}' decoding")
        lifts[dec] = {}
        for arm in ARMS:
            if arm not in blob[dec]:
                raise SystemExit(f"analysis.json has no '{arm}' arm under {dec}")
            got = sorted(int(k) for k in blob[dec][arm])
            if got != K_GRID:
                raise SystemExit(
                    f"frozen grid mismatch for {dec}/{arm}: {got} != {K_GRID}")
            lifts[dec][arm] = {k: blob[dec][arm][str(k)]["lift_mean"] for k in K_GRID}
    return lifts


# ------------------------------------------------------------------ cost model
def build_cost_model():
    per_item, per_pos, respondents, n_rows = load_mach()
    all_ms = [v for vs in per_item.values() for v in vs]
    m = {
        "n_rows": n_rows,
        "n_complete": len(respondents),
        "n_obs": len(all_ms),
        "census": {
            "min_ms": min(all_ms), "max_ms": max(all_ms),
            "n_le_0": sum(1 for v in all_ms if v <= 0),
            "n_lt_500ms": sum(1 for v in all_ms if v < 500),
            "n_gt_60s": sum(1 for v in all_ms if v > 60_000),
            "n_gt_10min": sum(1 for v in all_ms if v > 600_000),
            "median_ms": quantile(sorted(all_ms), 0.5),
            "mean_ms": sum(all_ms) / len(all_ms),
            "p99_ms": quantile(sorted(all_ms), 0.99),
        },
    }

    # trim sensitivity
    sens = []
    for label, lo, hi in TRIM_RULES:
        item_meds = [quantile(sorted(trimmed(per_item[i], lo, hi)), 0.5) / 1000
                     for i in range(1, N_MACH_ITEMS + 1)]
        pos_meds = [quantile(sorted(trimmed(per_pos[p], lo, hi)), 0.5) / 1000
                    for p in range(1, N_MACH_ITEMS + 1)]
        kept = sum(len(trimmed(per_item[i], lo, hi)) for i in range(1, N_MACH_ITEMS + 1))
        sens.append({
            "label": label,
            "pct_kept": 100 * kept / m["n_obs"],
            "median_of_item_medians_s": quantile(sorted(item_meds), 0.5),
            "pooled_median_s": quantile(sorted(trimmed(all_ms, lo, hi)), 0.5) / 1000,
            "cum20_s": sum(pos_meds),
            "item_medians_s": item_meds,
            "position_medians_s": pos_meds,
        })
    m["trim_sensitivity"] = sens
    primary = next(s for s in sens if s["label"] == TRIM_PRIMARY[0])
    m["primary"] = primary
    heads = [s["median_of_item_medians_s"] for s in sens]
    m["trim_spread_s"] = max(heads) - min(heads)

    # length -> RT, then rescale to RIASEC-length items
    mach_chars = [len(MACH_ITEM_TEXT[i]) for i in range(1, N_MACH_ITEMS + 1)]
    riasec_chars = [len(t) for t in RIASEC_ITEM_TEXT]
    item_meds = primary["item_medians_s"]
    intercept, slope = ols([float(c) for c in mach_chars], item_meds)
    mach_mean_chars = sum(mach_chars) / len(mach_chars)
    riasec_mean_chars = sum(riasec_chars) / len(riasec_chars)
    pred_mach = intercept + slope * mach_mean_chars
    pred_riasec = intercept + slope * riasec_mean_chars
    m["length"] = {
        "spearman": spearman([float(c) for c in mach_chars], item_meds),
        "pearson": pearson([float(c) for c in mach_chars], item_meds),
        "spearman_words": spearman(
            [float(len(MACH_ITEM_TEXT[i].split())) for i in range(1, N_MACH_ITEMS + 1)],
            item_meds),
        "intercept_s": intercept,
        "slope_s_per_char": slope,
        "mach_mean_chars": mach_mean_chars,
        "riasec_mean_chars": riasec_mean_chars,
        "mach_char_range": (min(mach_chars), max(mach_chars)),
        "riasec_char_range": (min(riasec_chars), max(riasec_chars)),
        "n_riasec_inside_mach_range": sum(
            1 for c in riasec_chars if min(mach_chars) <= c <= max(mach_chars)),
        "pred_at_mach_mean_s": pred_mach,
        "pred_at_riasec_mean_s": pred_riasec,
        "scale": pred_riasec / pred_mach,
    }

    # cumulative seconds per checkpoint, plus the between-respondent band
    lo, hi = TRIM_PRIMARY[1], TRIM_PRIMARY[2]
    scale = m["length"]["scale"]
    pos_meds = primary["position_medians_s"]
    cum = {}
    for k in K_GRID:
        sums = []
        for by_pos in respondents:
            total, ok = 0, True
            for p in range(1, k + 1):
                v = by_pos[p]
                if not (lo <= v <= hi):
                    ok = False
                    break
                total += v
            if ok:
                sums.append(total / 1000)
        sums.sort()
        cum[k] = {
            "mach_direct_s": sum(pos_meds[:k]),
            "central_s": scale * sum(pos_meds[:k]),
            "p25_s": scale * quantile(sums, 0.25),
            "p75_s": scale * quantile(sums, 0.75),
            "n_respondents": len(sums),
        }
    m["cumulative"] = cum
    m["marginal_late_item_s"] = scale * pos_meds[N_MACH_ITEMS - 1]

    # RIASEC's own page timer, an independent route to the same quantity
    te_all = load_riasec_testelapse()
    te = sorted(v for v in te_all if RIASEC_TE_LO_S <= v <= RIASEC_TE_HI_S)
    med_total = quantile(te, 0.5)
    m["riasec"] = {
        "n_raw": len(te_all), "n_trimmed": len(te),
        "pct_kept": 100 * len(te) / len(te_all),
        "median_total_s": med_total,
        "p25_total_s": quantile(te, 0.25), "p75_total_s": quantile(te, 0.75),
        "per_item_s": med_total / RIASEC_N_ITEMS,
        "p25_per_item_s": quantile(te, 0.25) / RIASEC_N_ITEMS,
        "p75_per_item_s": quantile(te, 0.75) / RIASEC_N_ITEMS,
    }
    return m


# --------------------------------------------------------------------- reports
def print_cost_model(m):
    c = m["census"]
    print("## MACH-IV cost model\n")
    print(f"rows {m['n_rows']:,} | complete-position respondents {m['n_complete']:,} "
          f"| item responses {m['n_obs']:,}\n")
    print("raw QnE census (the garbage problem):")
    print(f"  min {c['min_ms']:,} ms | max {c['max_ms']:,} ms "
          f"({c['max_ms']/86_400_000:.1f} days)")
    print(f"  <=0: {c['n_le_0']:,} | <500 ms: {c['n_lt_500ms']:,} | "
          f">60 s: {c['n_gt_60s']:,} | >10 min: {c['n_gt_10min']:,}")
    print(f"  median {c['median_ms']:,.0f} ms | mean {c['mean_ms']:,.0f} ms "
          f"(mean is meaningless) | p99 {c['p99_ms']:,.0f} ms\n")

    print("trim sensitivity (medians throughout):\n")
    print("| trim rule | kept | median of 20 item medians | pooled median | cumulative 20 items |")
    print("|---|---|---|---|---|")
    for s in m["trim_sensitivity"]:
        print(f"| {s['label']} | {s['pct_kept']:.2f}% | "
              f"{s['median_of_item_medians_s']:.2f} s | {s['pooled_median_s']:.2f} s | "
              f"{s['cum20_s']:.1f} s |")
    print(f"\nheadline moves {m['trim_spread_s']:.2f} s across all five rules "
          f"({100*m['trim_spread_s']/m['primary']['median_of_item_medians_s']:.1f}%) "
          "-- the trim rule is almost decorative.\n")

    pm = m["primary"]["position_medians_s"]
    print("position medians (MACH randomised order, so these are clean):")
    print("  " + "  ".join(f"p{p}={pm[p-1]:.2f}s" for p in (1, 2, 3, 4, 8, 12, 16, 20)))
    print("  first two items cost ~50% more than the ~6.4 s steady state\n")

    L = m["length"]
    print("item length -> response time:")
    print(f"  Spearman chars vs median RT: {L['spearman']:.2f}  "
          f"(Pearson {L['pearson']:.2f}, Spearman on words {L['spearman_words']:.2f})")
    print(f"  fit: RT = {L['intercept_s']:.3f} + {L['slope_s_per_char']:.4f} * characters")
    print(f"  MACH mean {L['mach_mean_chars']:.2f} chars (range {L['mach_char_range'][0]}-"
          f"{L['mach_char_range'][1]}) -> {L['pred_at_mach_mean_s']:.2f} s")
    print(f"  RIASEC mean {L['riasec_mean_chars']:.2f} chars (range {L['riasec_char_range'][0]}-"
          f"{L['riasec_char_range'][1]}) -> {L['pred_at_riasec_mean_s']:.2f} s")
    print(f"  {L['n_riasec_inside_mach_range']}/{len(RIASEC_ITEM_TEXT)} RIASEC items sit "
          "inside MACH's observed length range (interpolation, not extrapolation)")
    print(f"  => length scale {L['scale']:.4f}\n")

    r = m["riasec"]
    print("independent cross-check, RIASEC's own testelapse page timer:")
    print(f"  {r['n_trimmed']:,}/{r['n_raw']:,} respondents kept ({r['pct_kept']:.1f}%)")
    print(f"  median {r['median_total_s']:.0f} s for {RIASEC_N_ITEMS} items "
          f"(IQR {r['p25_total_s']:.0f}-{r['p75_total_s']:.0f} s)")
    print(f"  => {r['per_item_s']:.2f} s per item, versus "
          f"{L['pred_at_riasec_mean_s']:.2f} s from the length-adjusted MACH model")
    disagree = abs(r["per_item_s"] - L["pred_at_riasec_mean_s"]) / r["per_item_s"]
    print(f"  two unrelated routes disagree by {100*disagree:.0f}%\n")


def print_conversion(m):
    print("## Cumulative respondent time per checkpoint\n")
    print("| k | MACH direct (s) | central estimate (s) | RIASEC pro-rata (s) "
          "| p25 (s) | p75 (s) | central (min) |")
    print("|---|---|---|---|---|---|---|")
    per_item = m["riasec"]["per_item_s"]
    for k in K_GRID:
        c = m["cumulative"][k]
        print(f"| {k} | {c['mach_direct_s']:.1f} | **{c['central_s']:.1f}** | "
              f"{per_item*k:.1f} | {c['p25_s']:.1f} | {c['p75_s']:.1f} | "
              f"{c['central_s']/60:.2f} |")
    print()


def print_curves(m, lifts):
    for dec, name in DECODINGS:
        print(f"## Budget curves, {name} decoding\n")
        print("| k | respondent time | " + " | ".join(ARMS) + " |")
        print("|---|---|" + "---|" * len(ARMS))
        for k in K_GRID:
            cells = " | ".join(f"{lifts[dec][arm][k]:+.4f}" for arm in ARMS)
            print(f"| {k} | {m['cumulative'][k]['central_s']:.0f} s | {cells} |")
        print()

    print("## Lift per minute of respondent time (EV, descriptive only)\n")
    print("Within a row this ranks identically to lift -- time is shared across arms.")
    print("What it shows is the rate of return falling as the budget grows.\n")
    print("| k | time (s) | " + " | ".join(ARMS[:3]) + " |")
    print("|---|---|---|---|---|")
    for k in K_GRID:
        secs = m["cumulative"][k]["central_s"]
        cells = " | ".join(
            f"{lifts['expected_value'][arm][k] / (secs/60):+.3f}" for arm in ARMS[:3])
        print(f"| {k} | {secs:.0f} | {cells} |")
    print()


def print_latency(m):
    print("## The one real asymmetry: the respondent waits while adaptive thinks\n")
    per_person = ADAPTIVE_SELECTION_CALLS // CONFIRM_N_PERSONS
    expected = sum(POOL_SIZE - j for j in range(max(K_GRID)))
    print(f"selection calls per person: {ADAPTIVE_SELECTION_CALLS:,} / "
          f"{CONFIRM_N_PERSONS:,} = {per_person}")
    print(f"sum(48-j) over {max(K_GRID)} reveals = {expected}  "
          f"-> {'exact match' if per_person == expected else 'MISMATCH'}")
    if per_person != expected:
        raise SystemExit("selection-call ledger does not match the scoring mechanism")
    print("  => at every reveal the policy scores every remaining unrevealed item,\n"
          "     one model call each (48 candidates before the first question, 29 before the 20th)\n")

    thr = ADAPTIVE_TOTAL_CALLS / (ADAPTIVE_NODE_HOURS * 3600)
    print(f"run throughput: {ADAPTIVE_TOTAL_CALLS:,} calls / {ADAPTIVE_NODE_HOURS} node-hours "
          f"= {thr:.1f} calls per node-second ({thr/4:.1f} per GPU-second)")
    print(f"  which divides out to {1000/thr:.1f} ms per call -- DO NOT USE THAT AS LATENCY.")
    print("  It is offline batch throughput with nobody waiting. Stage 1E never measured")
    print("  single-request latency, so the scenarios below use ASSUMED values.\n")

    base = m["cumulative"][20]["central_s"]
    print(f"per interview at k=20, against {base:.0f} s of answering:\n")
    print("| serving mode | assumed latency | added wall clock | interview grows by |")
    print("|---|---|---|---|")
    for lat in (0.05, 0.20, 1.00):
        add = per_person * lat
        print(f"| all {per_person} candidate scores served one at a time | "
              f"{lat*1000:.0f} ms/call | {add:.0f} s | +{100*add/base:.0f}% |")
    for batch in (0.15, 0.50, 2.00):
        add = max(K_GRID) * batch
        print(f"| one reveal's candidates batched into a single pass | "
              f"{batch:.2f} s/reveal | {add:.0f} s | +{100*add/base:.0f}% |")
    print("\n=> between +3% and +840%, driven by an engineering choice (batched vs serial),")
    print("   not by a property of the policy. A static script pays exactly zero.\n")

    marginal = m["marginal_late_item_s"]
    print(f"matched-wall-clock reading, UNSCORED (the frozen grid stops at k=20).")
    print(f"at the {marginal:.2f} s steady-state item cost, adaptive's added time buys the "
          "static script:")
    for add in (3, 10, 40, 154):
        print(f"  +{add:>3} s  ->  ~{add/marginal:.1f} extra items")
    print()


def print_verdict():
    print("## Verdict\n")
    print("Every arm answers k items at checkpoint k, so the seconds column is IDENTICAL")
    print("across arms and the transform is one shared monotonic rescaling of the x-axis.")
    print("It cannot reorder arms at a matched budget, and it did not.\n")
    print("The static order still wins per second, and once thinking time is counted it")
    print("wins by more. Nothing here changes results/stage1e_findings.md.\n")


# ----------------------------------------------------------------------- check
def run_check(m, lifts):
    """Assert the recomputation still matches the note, and the artifact."""
    got = {
        "pct_kept_primary": m["primary"]["pct_kept"],
        "median_of_item_medians_primary_s": m["primary"]["median_of_item_medians_s"],
        "trim_spread_s": m["trim_spread_s"],
        "spearman_len_vs_rt": m["length"]["spearman"],
        "mach_mean_chars": m["length"]["mach_mean_chars"],
        "riasec_mean_chars": m["length"]["riasec_mean_chars"],
        "length_scale": m["length"]["scale"],
        "per_item_length_adjusted_s": m["length"]["pred_at_riasec_mean_s"],
        "riasec_per_item_s": m["riasec"]["per_item_s"],
        "riasec_median_total_s": m["riasec"]["median_total_s"],
        "cum20_central_s": m["cumulative"][20]["central_s"],
        "cum12_central_s": m["cumulative"][12]["central_s"],
        "cum20_mach_direct_s": m["cumulative"][20]["mach_direct_s"],
        "selection_calls_per_person": ADAPTIVE_SELECTION_CALLS / CONFIRM_N_PERSONS,
        "marginal_late_item_s": m["marginal_late_item_s"],
    }
    failures = []
    for key, (want, tol) in NOTE_CLAIMS.items():
        have = got[key]
        if abs(have - want) > tol:
            failures.append(f"  {key}: note says {want}, recomputed {have:.4f} (tol {tol})")

    # item texts must match the codebooks they were transcribed from
    for path, texts in ((ROOT / "data/mach/MACH_data/codebook.txt",
                         list(MACH_ITEM_TEXT.values())),
                        (ROOT / "data/riasec/codebook.txt", RIASEC_ITEM_TEXT)):
        if not path.exists():
            failures.append(f"  cannot verify item texts: missing {path}")
            continue
        book = path.read_text(encoding="utf-8", errors="replace")
        missing = [t for t in texts if t not in book]
        if missing:
            failures.append(
                f"  {len(missing)} item text(s) not found verbatim in {path.name}, "
                f"first: {missing[0][:60]!r}")

    # the note reprints lifts from the artifact; spot-check the two it bolds
    for dec, arm, k, want in (("expected_value", "fixed", 20, 0.0680),
                              ("argmax", "fixed", 20, 0.0218),
                              ("expected_value", "adaptive", 20, 0.0493)):
        have = lifts[dec][arm][k]
        if abs(have - want) > 5e-5:
            failures.append(f"  lift {dec}/{arm}/k={k}: note says {want}, artifact {have}")

    if failures:
        print("CHECK FAILED -- the note and the code have drifted:")
        print("\n".join(failures))
        raise SystemExit(1)
    print(f"CHECK PASSED: {len(NOTE_CLAIMS)} headline figures, "
          f"{N_MACH_ITEMS + len(RIASEC_ITEM_TEXT)} item texts, and 3 spot-checked lifts "
          "all match results/stage1e_timecost_note.md")


# ---------------------------------------------------------------------- figure
def make_figure(m, lifts):
    try:
        import matplotlib
    except ModuleNotFoundError:
        raise SystemExit(
            "matplotlib is not a project dependency (see pyproject.toml). Run with:\n"
            "  uv run --no-project --with matplotlib python experiments/timecost_note.py --figure")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    secs = [m["cumulative"][k]["central_s"] for k in K_GRID]
    # categorical slots 1-4 of the validated light-mode palette
    colors = {"random": "#2a78d6", "fixed": "#eb6834",
              "adaptive": "#1baf7a", "imposter": "#eda100"}
    ink, ink2, muted, surface = "#0b0b0b", "#52514e", "#8a8880", "#fcfcfb"

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.9), sharey=True)
    fig.patch.set_facecolor(surface)
    titles = ("Expected-value decoding (pre-registered primary)",
              "Argmax decoding (robustness check)")
    for ax, (dec, _), title in zip(axes, DECODINGS, titles):
        ax.set_facecolor(surface)
        ax.axhline(0, color=muted, lw=1, ls=(0, (4, 3)), zorder=1)
        for arm in ARMS:
            ax.plot(secs, [lifts[dec][arm][k] for k in K_GRID], color=colors[arm],
                    lw=2, marker="o", markersize=6, markeredgecolor=surface,
                    markeredgewidth=1.5, zorder=3, solid_capstyle="round", label=arm)
        ax.set_title(title, fontsize=10.5, color=ink, pad=26, loc="left")
        ax.set_xlabel("cumulative respondent time (seconds)", fontsize=9.5, color=ink2)
        ax.grid(axis="y", color="#e6e5e0", lw=0.8, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#d8d7d1")
        ax.tick_params(colors=ink2, labelsize=9, length=3)
        ax.set_xlim(-3, 108)
        ax.set_xticks([0, 20, 40, 60, 80, 100])
        top = ax.secondary_xaxis("top")
        top.set_xticks(secs)
        top.set_xticklabels([str(k) for k in K_GRID], fontsize=8.5)
        top.tick_params(colors=muted, length=0, pad=2)
        top.set_xlabel("items asked (k)", fontsize=8.5, color=muted, labelpad=4)
        for sp in top.spines.values():
            sp.set_visible(False)

    axes[0].set_ylabel("lift over demographics-only baseline (MAE)", fontsize=9.5, color=ink2)
    # direct labels stay in ink tokens, never the series color; nudge the two
    # near-coincident arms apart so reading order matches line order
    for arm, dy in (("random", -8), ("fixed", 0), ("adaptive", 8), ("imposter", 0)):
        axes[1].annotate(arm, xy=(secs[-1], lifts["argmax"][arm][20]), xytext=(7, dy),
                         textcoords="offset points", va="center", fontsize=9, color=ink2)
    axes[0].legend(frameon=False, fontsize=9, loc="lower right", labelcolor=ink2,
                   handlelength=1.6, borderpad=0.2)

    fig.suptitle("Stage 1E budget curves priced in respondent time  ·  "
                 "descriptive re-analysis, no new claims",
                 fontsize=11.5, color=ink, x=0.008, ha="left", y=0.985, fontweight="semibold")
    fig.text(0.008, 0.015,
             f"Time axis = MACH-IV per-item response times (n={m['n_complete']:,}; "
             f"500 ms–60 s trim; position-aware; length-adjusted to RIASEC-length items, "
             f"×{m['length']['scale']:.2f}).\nRescaling is identical for every arm, so it "
             "cannot change which arm leads at a matched budget. Adaptive's between-item "
             "thinking time is NOT included here.",
             fontsize=8, color=muted, ha="left", va="bottom")
    fig.subplots_adjust(left=0.075, right=0.90, top=0.82, bottom=0.20, wspace=0.09)
    fig.savefig(FIGURE_PNG, dpi=170, facecolor=surface)
    print(f"wrote {FIGURE_PNG.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="assert the recomputation matches the note, then exit non-zero if not")
    ap.add_argument("--figure", action="store_true",
                    help="also write results/stage1e_timecost_curves.png (needs matplotlib)")
    ap.add_argument("--quiet", action="store_true", help="suppress the tables")
    args = ap.parse_args()

    model = build_cost_model()
    lifts = load_lifts()

    if not args.quiet:
        print("# Stage 1E budgets priced in respondent time (descriptive re-analysis)\n")
        print_cost_model(model)
        print_conversion(model)
        print_curves(model, lifts)
        print_latency(model)
        print_verdict()

    if args.figure:
        make_figure(model, lifts)
    if args.check:
        run_check(model, lifts)


if __name__ == "__main__":
    main()
