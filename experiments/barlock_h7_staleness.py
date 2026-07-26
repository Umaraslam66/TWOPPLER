"""Bar-lock item 6: can a staleness hypothesis (H7) be run at all?

H7 asks whether a twin gets worse as the gap between the newest grounding
interview and the test interview grows. To run it a subject needs several dated
interview events spread over time, so that the same test interview can be
predicted from grounding cut off at several different distances.

This script measures, from results/stage2_candidate_pool_v2.csv alone:
  (a) per dev subject: dated substantive clusters, span, the gap between every
      possible grounding cutoff and the test cluster, and how many staleness
      bins that chronology can fill;
  (b) over the full eligible pool: how many candidates meet the draft H7
      eligibility rule (>= 4 dated clusters spanning >= 2 years), plus the
      per-bin candidate counts.

CPU only, no network, no model calls. Seconds to run.

Usage: uv run python experiments/barlock_h7_staleness.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doppler.stage2_data import eligible_subjects, load_pool  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "stage2_pilot2" / "barlock"
DEV = ROOT / "results" / "stage2_pilot" / "dev_subjects.json"

#: Staleness bins, in days, as (label, low_inclusive, high_exclusive).
BINS = [
    ("<6m", 0, 183),
    ("6-12m", 183, 366),
    ("1-2y", 366, 731),
    ("2-3y", 731, 1096),
    (">3y", 1096, 10 ** 6),
]

#: Draft H7 eligibility rule under review.
MIN_CLUSTERS = 4
MIN_SPAN_DAYS = 731          # 2 years


def bin_of(days: int) -> str:
    for label, lo, hi in BINS:
        if lo <= days < hi:
            return label
    return BINS[-1][0]


def cluster_dates(row: dict) -> list[tuple[str, str]]:
    """[(cluster_id, cluster_date)] for substantive clusters, oldest first.

    Cluster date is the earliest member date, matching SPEC D2. Clusters that
    share a date with the test cluster are what D2 excludes; here we only need
    the distinct dated events, so same-date clusters collapse into one bin edge
    naturally through the gap arithmetic.
    """
    clusters: dict[str, list[str]] = {}
    for e in row["transcripts"]:
        if e["substantive"]:
            clusters.setdefault(e["cluster_id"], []).append(e["date"])
    out = [(cid, min(ds)) for cid, ds in clusters.items()]
    out.sort(key=lambda t: (t[1], t[0]))
    return out


def days_between(a: str, b: str) -> int:
    return abs((date.fromisoformat(b) - date.fromisoformat(a)).days)


def chronology(row: dict) -> dict:
    """Everything H7 needs to know about one subject's timeline."""
    cds = cluster_dates(row)
    if len(cds) < 2:
        return {"canonical_id": row["canonical_id"],
                "canonical_name": row["canonical_name"],
                "n_clusters": len(cds), "span_days": 0, "gaps": [],
                "bins_filled": [], "n_bins": 0, "h7_eligible": False}

    test_date = cds[-1][1]
    # A grounding cutoff at cluster k (0-based, k < last) means "ground on
    # clusters 0..k". Its staleness is test_date - date(k).
    gaps = [{"cutoff_cluster": cid, "cutoff_date": d,
             "delta_days": days_between(d, test_date),
             "bin": bin_of(days_between(d, test_date))}
            for cid, d in cds[:-1]]
    # Same-date-as-test clusters are excluded by D2; a zero gap is not a usable
    # cutoff, so drop them here too.
    gaps = [g for g in gaps if g["delta_days"] > 0]
    filled = sorted({g["bin"] for g in gaps},
                    key=lambda b: [x[0] for x in BINS].index(b))
    span = days_between(cds[0][1], test_date)
    return {
        "canonical_id": row["canonical_id"],
        "canonical_name": row["canonical_name"],
        "wiki_status": row.get("wiki_status", ""),
        "n_clusters": len(cds),
        "first_date": cds[0][1],
        "test_date": test_date,
        "span_days": span,
        "span_years": round(span / 365.25, 2),
        "gaps": gaps,
        "bins_filled": filled,
        "n_bins": len(filled),
        "h7_eligible": len(cds) >= MIN_CLUSTERS and span >= MIN_SPAN_DAYS,
    }


def main() -> int:
    t0 = time.time()
    pool = load_pool()
    elig = eligible_subjects(pool)
    by_id = {r["canonical_id"]: r for r in pool}

    dev_ids = [s["canonical_id"] for s in
               json.loads(DEV.read_text())["subjects"]]
    dev = [chronology(by_id[cid]) for cid in dev_ids]

    full = [chronology(r) for r in elig]

    per_bin_any = {label: 0 for label, _, _ in BINS}
    per_bin_elig = {label: 0 for label, _, _ in BINS}
    n_bins_hist = {}
    n_bins_hist_elig = {}
    for c in full:
        for b in c["bins_filled"]:
            per_bin_any[b] += 1
            if c["h7_eligible"]:
                per_bin_elig[b] += 1
        n_bins_hist[c["n_bins"]] = n_bins_hist.get(c["n_bins"], 0) + 1
        if c["h7_eligible"]:
            n_bins_hist_elig[c["n_bins"]] = n_bins_hist_elig.get(c["n_bins"], 0) + 1

    eligible = [c for c in full if c["h7_eligible"]]
    # Sensitivity: how the headline moves if the rule tightens or loosens.
    sensitivity = {}
    for mc in (3, 4, 5, 6):
        for sy, sd in (("1y", 366), ("2y", 731), ("3y", 1096)):
            n = sum(1 for c in full
                    if c["n_clusters"] >= mc and c["span_days"] >= sd)
            sensitivity[f">={mc} clusters, >={sy} span"] = n
    # Also: how many can fill >= k distinct bins.
    bins_at_least = {k: sum(1 for c in full if c["n_bins"] >= k)
                     for k in range(1, 6)}
    bins_at_least_elig = {k: sum(1 for c in eligible if c["n_bins"] >= k)
                          for k in range(1, 6)}

    payload = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pool_rows": len(pool),
        "n_eligible": len(elig),
        "bins": [{"label": b, "low_days": lo, "high_days": hi}
                 for b, lo, hi in BINS],
        "draft_rule": {"min_clusters": MIN_CLUSTERS,
                       "min_span_days": MIN_SPAN_DAYS},
        "dev_subjects": dev,
        "full_pool": {
            "n_h7_eligible": len(eligible),
            "share_h7_eligible": round(len(eligible) / len(elig), 4),
            "per_bin_candidates_any": per_bin_any,
            "per_bin_candidates_h7_eligible": per_bin_elig,
            "n_bins_histogram": dict(sorted(n_bins_hist.items())),
            "n_bins_histogram_h7_eligible": dict(sorted(n_bins_hist_elig.items())),
            "candidates_filling_at_least_k_bins": bins_at_least,
            "candidates_filling_at_least_k_bins_h7_eligible": bins_at_least_elig,
            "sensitivity_counts": sensitivity,
        },
        "runtime_secs": round(time.time() - t0, 2),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "h7_staleness.json").write_text(json.dumps(payload, indent=1))
    slim = dict(payload)
    slim["dev_subjects"] = [{k: v for k, v in d.items() if k != "gaps"}
                            for d in dev]
    print(json.dumps(slim, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
