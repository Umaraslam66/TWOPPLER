"""Phase B — Wikipedia long-tail check for every canonical candidate.

Phase A only had a raw-label-based check for a random 500-guest sample, which
covered 133 of the 1,162 pool candidates; 501 clean candidates were never
checked with the good method (the other 200 carried the biased v1 flag from
mediasum_index.py, which queried the title-cased *normalized* name and
produced false long-tails).

This script checks ALL canonical pool subjects with the good method — the most
frequent RAW transcript label, honorifics/roles stripped, original casing kept
(title-cased only when the label is all-caps, since Wikipedia titles are
case-sensitive after char 1). It then unions the result with the v1 re-check.

Network: Wikipedia free API only. Batches of 50, redirects=1, >=1.1 s sleep,
User-Agent set. No paid API, no LLM.

Run: uv run python experiments/wiki_recheck_v2.py
"""
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mediasum_index as M  # noqa: E402
import wiki_recheck as W  # noqa: E402  (reuse raw_to_query + wiki_exists)

OUT_DIR = M.OUT_DIR
CANON_STATS = os.path.join(OUT_DIR, "canonical_stats_v2.csv")
V1_CSV = os.path.join(OUT_DIR, "wiki_recheck.csv")
OUT_CSV = os.path.join(OUT_DIR, "wiki_recheck_v2.csv")
SUMMARY = os.path.join(OUT_DIR, "wiki_recheck_v2_summary.json")


def main():
    t0 = time.time()
    rows = []
    with open(CANON_STATS) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    print(f"canonical subjects: {len(rows)}")

    v1 = {}
    with open(V1_CSV) as f:
        for r in csv.DictReader(f):
            v1[r["normalized_name"]] = r

    # Two titles per subject: the raw transcript label (original casing, roles
    # stripped) AND the canonical name. A subject counts as long-tail only if
    # BOTH miss — one query form alone produces false long-tails.
    todo = []
    for r in rows:
        raw = r["top_raw_label"]
        q1 = W.raw_to_query(raw)[1] if raw else ""
        q2 = W.raw_to_query(r["canonical_name"])[1]
        todo.append((r["canonical_name"], raw, q1, q2))

    queries = sorted({q for _n, _raw, a, b in todo for q in (a, b) if q})
    print(f"distinct Wikipedia titles to query: {len(queries)} "
          f"({(len(queries)+49)//50} batches of 50)")
    ex = W.wiki_exists(queries)

    out = {}
    for name, raw, q1, q2 in todo:
        e1, e2 = ex.get(q1), ex.get(q2)
        if e1 is None and e2 is None:
            exists = None
        else:
            exists = bool(e1) or bool(e2)
        hit = q1 if e1 else (q2 if e2 else "")
        out[name] = {
            "normalized_name": name,
            "raw_label_queried": raw,
            "wikipedia_query": q1,
            "canonical_query": q2,
            "matched_title": hit,
            "page_exists": "" if exists is None else ("yes" if exists else "no"),
            "source": "v2_pool",
            "v1_page_exists": v1.get(name, {}).get("page_exists", ""),
        }
    # union in the v1 sample rows that are not canonical pool subjects
    for name, r in v1.items():
        if name in out:
            out[name]["source"] = "v1_recheck+v2_pool"
            continue
        out[name] = {
            "normalized_name": name,
            "raw_label_queried": r["raw_label_queried"],
            "wikipedia_query": r["wikipedia_query"],
            "canonical_query": "",
            "matched_title": "",
            "page_exists": r["page_exists"],
            "source": "v1_recheck",
            "v1_page_exists": r["page_exists"],
        }

    fields = ["normalized_name", "raw_label_queried", "wikipedia_query",
              "canonical_query", "matched_title", "page_exists", "source",
              "v1_page_exists"]
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for name in sorted(out):
            w.writerow(out[name])
    print(f"wrote {OUT_CSV} ({len(out)} rows)")

    new = [v for v in out.values() if v["source"].endswith("v2_pool")]
    checked = [v for v in new if v["page_exists"]]
    lt = [v for v in checked if v["page_exists"] == "no"]
    agree = [v for v in checked if v["v1_page_exists"]]
    flips = [v for v in agree if v["v1_page_exists"] != v["page_exists"]]
    print(f"\n=== WIKI v2 ===")
    print(f"canonical subjects checked: {len(checked)} / {len(new)}")
    print(f"long-tail (no page): {len(lt)} ({len(lt)/max(1,len(checked)):.1%})")
    print(f"overlap with v1 re-check: {len(agree)}; disagreements: {len(flips)}")
    with open(SUMMARY, "w") as f:
        json.dump({"checked": len(checked), "long_tail": len(lt),
                   "rate": len(lt) / max(1, len(checked)),
                   "overlap_v1": len(agree), "flips": len(flips),
                   "secs": time.time() - t0}, f, indent=2)
    print(f"took {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
