"""Third Wikipedia pass: catch FALSE long-tails caused by name spelling.

The exact-title check in wiki_recheck_v2.py asks "is there a page with exactly
this title?". MediaSum's speaker labels are not clean enough for that to be
the last word:

  Karen Deyoung  -> the page is "Karen DeYoung"       (our per-word title-case)
  Nicholas Lardy -> the page is "Nicholas R. Lardy"   (middle initial)
  Tim Brookes    -> the page is "Tim Brooks"          (transcription spelling)
  Andy Kohut     -> the page is "Andrew Kohut"        (nickname)

A sampled search over 25 shortlist long-tails found 3 such misses (12%), which
would inflate the pre-registered long-tail count. This pass runs Wikipedia's
search API for every subject currently marked long-tail and records the closest
title, so "long-tail" can be downgraded when a near-identical article exists.

Network: Wikipedia free API only, 1 search/second, User-Agent set. $0, no LLM.
Run: uv run python experiments/wiki_fuzzy_v2.py
"""
import csv
import difflib
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mediasum_index as M  # noqa: E402

OUT_DIR = M.OUT_DIR
WIKI_V2 = os.path.join(OUT_DIR, "wiki_recheck_v2.csv")
CANON_STATS = os.path.join(OUT_DIR, "canonical_stats_v2.csv")
OUT_CSV = os.path.join(OUT_DIR, "wiki_fuzzy_v2.csv")

# Similarity at or above this on the best search hit means "same person";
# calibrated on the 25-name sample (Karen Deyoung 1.00, Tim Brookes 0.95,
# Nicholas Lardy 0.90 were all true pages; the highest true long-tail was
# Sheila Smith at 0.83 against an unrelated "Sheila Kaye-Smith").
SAME_PERSON = 0.88
UA = M.WIKI_UA


def search(title, limit=3):
    p = {"action": "query", "list": "search", "srsearch": title,
         "srlimit": limit, "format": "json"}
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(p)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
        return [x["title"] for x in d.get("query", {}).get("search", [])]
    except Exception as e:  # noqa: BLE001
        print(f"  search failed for {title!r}: {e}")
        time.sleep(2)
        return []


def main():
    t0 = time.time()
    names = []
    with open(CANON_STATS) as f:
        canon = [r["canonical_name"] for r in csv.DictReader(f)]
    with open(WIKI_V2) as f:
        for r in csv.DictReader(f):
            if r["page_exists"] == "no" and r["normalized_name"] in set(canon):
                names.append(r["normalized_name"])
    names.sort()
    print(f"long-tail subjects to verify by search: {len(names)} "
          f"(~{len(names)*1.1/60:.0f} min)")

    rows = []
    n_down = 0
    for i, nm in enumerate(names, 1):
        res = search(nm)
        best_t, best_s = "", 0.0
        for t in res:
            s = difflib.SequenceMatcher(None, nm.lower(), t.lower()).ratio()
            if s > best_s:
                best_s, best_t = s, t
        same = best_s >= SAME_PERSON
        n_down += same
        rows.append([nm, best_t, round(best_s, 3),
                     "has-page-fuzzy" if same else "long-tail"])
        if i % 25 == 0:
            print(f"  {i}/{len(names)} ({time.time()-t0:.0f}s), "
                  f"downgraded so far={n_down}")
        time.sleep(1.05)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["canonical_name", "closest_wikipedia_title", "similarity",
                    "fuzzy_status"])
        w.writerows(rows)
    print(f"\nwrote {OUT_CSV} ({len(rows)} rows)")
    print(f"exact-title long-tails: {len(names)}")
    print(f"  downgraded to has-page-fuzzy: {n_down} ({n_down/max(1,len(names)):.1%})")
    print(f"  confirmed long-tail: {len(names)-n_down}")
    print(f"took {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
