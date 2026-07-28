"""PROVISIONAL confirmatory subject draw for the Stage 2 launch plan.

PROVISIONAL means: this lists WHO would be drawn, from metadata already on
disk (the committed candidate pool CSV). No transcript of any drawn
subject is opened, rendered, or scored until the owner's explicit GO —
the untouchability rule holds until then.

Procedure, with its provenance:
- Eligible = qualifies AND clean AND NOT ambiguous_identity in
  results/stage2_candidate_pool_v2.csv — the same rule, on the same
  file, as the committed dev draw (results/stage2_pilot/
  dev_subjects.json, seed 47, n_eligible=578).
- The 292-subject staff reserve is excluded by construction: reserve
  subjects are not clean/qualifying rows in this pool (they were dropped
  at curation); additionally, no drawn row may carry staff evidence —
  asserted, not assumed.
- All six dev subjects (C00292 included) are excluded by ID. Dev
  subjects are burned forever.
- Composition: long-tail-biased mix at the committed 3:1 ratio (the
  shortlist's 90:30 expression of the owner's long-tail-bias decision);
  the draw order interleaves LT,LT,LT,A.
- Priority (addendum item 10, frozen): subjects with >= 4 dated dedup
  clusters are drawn before subjects below 4 within each stratum.
- Within each stratum x priority band: lexicographic sort then one
  shuffle with random.Random(SEED) — the dev draw's own pattern.
- Draw depth 140: the addendum item-4 floor (>= 3 D4-eligible items in
  the test cluster, one-on-one programmes preferred) is checked at BUILD
  time in draw order, and the measured 70% survival (95% CI 57.5-80.1)
  puts 140 draws at ~98 expected survivors against the >= 80 branch.
- H7-eligible (B7, frozen: >= 4 dated clusters spanning >= 2 years) is
  flagged per drawn subject from pool metadata.

Deterministic from SEED; rerun reproduces the list byte-identically.
"""
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "results" / "stage2_candidate_pool_v2.csv"
DEV = ROOT / "results" / "stage2_pilot" / "dev_subjects.json"
OUT = ROOT / "results" / "stage2_confirm_draw_provisional.json"
SEED = 20260728
DRAW_DEPTH = 140
RATIO = 3  # long-tail : article, the committed 3:1 bias


def main():
    dev = json.load(open(DEV))
    dev_ids = sorted({s["canonical_id"] for s in dev["subjects"]})
    rows = list(csv.DictReader(open(POOL)))
    eligible = [r for r in rows
                if r["qualifies"] == "True" and r["clean"] == "True"
                and r["ambiguous_identity"] == "False"]
    assert len(eligible) == dev["n_eligible"] == 578, len(eligible)
    pool = [r for r in eligible if r["canonical_id"] not in dev_ids]

    strata = {"long-tail": [], "article": []}
    for r in pool:
        key = "long-tail" if r["wiki_status"] == "long-tail" else "article"
        strata[key].append(r)

    rng = random.Random(SEED)
    ordered = {}
    for key, subs in strata.items():
        hi = [r for r in subs if int(r["n_dedup_clusters"]) >= 4]
        lo = [r for r in subs if int(r["n_dedup_clusters"]) < 4]
        for band in (hi, lo):
            band.sort(key=lambda r: r["canonical_id"])
            rng.shuffle(band)
        ordered[key] = hi + lo

    draw, i_lt, i_a = [], 0, 0
    while len(draw) < DRAW_DEPTH:
        for _ in range(RATIO):
            if i_lt < len(ordered["long-tail"]) and len(draw) < DRAW_DEPTH:
                draw.append(ordered["long-tail"][i_lt]); i_lt += 1
        if i_a < len(ordered["article"]) and len(draw) < DRAW_DEPTH:
            draw.append(ordered["article"][i_a]); i_a += 1
        if i_lt >= len(ordered["long-tail"]) and i_a >= len(ordered["article"]):
            break

    def h7_eligible(r):
        return int(r["n_dedup_clusters"]) >= 4 and int(r["span_days_dedup"]) >= 730

    subjects = [{
        "draw_pos": i + 1, "canonical_id": r["canonical_id"],
        "stratum": "long-tail" if r["wiki_status"] == "long-tail" else "article",
        "n_dedup_clusters": int(r["n_dedup_clusters"]),
        "span_days_dedup": int(r["span_days_dedup"]),
        "h7_eligible": h7_eligible(r),
    } for i, r in enumerate(draw)]

    # Disjointness proof — asserted, then printed.
    drawn_ids = {s["canonical_id"] for s in subjects}
    assert not drawn_ids & set(dev_ids), "dev subject leaked into the draw"
    assert all(r["canonical_id"] in {x["canonical_id"] for x in eligible}
               for r in draw), "non-eligible row drawn"
    staff_rows = [r["canonical_id"] for r in draw
                  if (r["staff_evidence"] or "no") != "no" or r["staff_marker"]]
    assert not staff_rows, f"staff-evidence rows drawn: {staff_rows}"

    proof = {
        "dev_ids_excluded": dev_ids,
        "dev_intersection_with_draw": sorted(drawn_ids & set(dev_ids)),
        "n_eligible_pool": len(eligible),
        "n_after_dev_exclusion": len(pool),
        "n_drawn": len(subjects),
        "drawn_all_qualify_clean_unambiguous": True,
        "drawn_with_staff_evidence": staff_rows,
        "reserve_note": "the 292-subject staff reserve is not in the "
                        "clean/qualifying pool (dropped at curation) and so "
                        "is excluded by construction; re-admission still "
                        "gates on the owner's 20-dossier spot-check",
    }
    out = {
        "status": "PROVISIONAL — no drawn subject is touched by any Stage 2 "
                  "machinery until the owner's explicit GO on the launch plan",
        "seed": SEED, "draw_depth": DRAW_DEPTH,
        "ratio_longtail_to_article": "3:1",
        "expected_survival": "0.70 (95% CI 57.5-80.1%) against the >= 3-item "
                             "build-time floor -> ~98 expected of 140, "
                             ">= 80 branch holds",
        "composition": {
            "long-tail": sum(1 for s in subjects if s["stratum"] == "long-tail"),
            "article": sum(1 for s in subjects if s["stratum"] == "article"),
        },
        "h7_eligible_in_draw": sum(1 for s in subjects if s["h7_eligible"]),
        "clusters_ge4_in_draw": sum(1 for s in subjects
                                    if s["n_dedup_clusters"] >= 4),
        "disjointness_proof": proof,
        "subjects": subjects,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "subjects"},
                     indent=1))


if __name__ == "__main__":
    main()
