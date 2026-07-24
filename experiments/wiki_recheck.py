"""Unbiased Wikipedia long-tail re-check for the MediaSum guest pool.

Fixes two biases in the original check inside mediasum_index.py:
  1. Coverage: the original checked only the top-2000 candidates BY WORD COUNT
     (the famous end). Here we sample the *mid-tail* of the realistic pool.
  2. Query form: the original queried the per-word title-cased *normalized*
     name, and surname-only rows (61% of candidates) plus stray casing caused
     false long-tail flags. Here we query each guest's most frequent *raw*
     transcript label (honorifics + role suffix stripped, casing preserved
     where it is genuine).

Sampling rule (frozen): 500 guests, seed 43, uniform, from the pool
  passes_key_filter AND normalized-name has >= 2 tokens AND the guest is NOT in
  the top 500 by total_guest_words *within that >=2-token candidate pool*
  (i.e. drop the famous end of the pool we actually sample from).

Casing note (empirical, see report addendum): MediaSum name labels are ~60%
ALL-CAPS. Wikipedia's title API is case-sensitive after char 1, so a literal
all-caps query ("BOB DOLE") misses every page. We therefore title-case a label
only when it is all-caps; genuine mixed-case labels are preserved. Wikipedia
redirects then absorb internal-capital variants ("Mike Dewine" -> "Mike
DeWine", "Ronald Mcdonald" -> "Ronald McDonald").

Run: uv run python experiments/wiki_recheck.py
Network: Wikipedia API only (batches of 50, redirects=1, >=1s sleep, UA set).
"""
import csv
import json
import math
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mediasum_index as M  # noqa: E402  (reuse parser + classifier)

SEED = 43
SAMPLE_N = 500
TOP_EXCLUDE = 500
OUT_CSV = os.path.join(M.OUT_DIR, "wiki_recheck.csv")
WIKI_UA = M.WIKI_UA


# ---------------------------------------------------------------------------
def build_sample():
    pool = []  # (name, words)
    with open(M.INDEX_CSV) as f:
        r = csv.DictReader(f)
        for row in r:
            if row["passes_key_filter"] != "1":
                continue
            name = row["normalized_name"]
            if len(name.split()) < 2:
                continue
            pool.append((name, int(row["total_guest_words"])))
    pool_names = {n for n, _ in pool}
    top = {n for n, _ in sorted(pool, key=lambda x: -x[1])[:TOP_EXCLUDE]}
    realistic = sorted(n for n in pool_names if n not in top)
    rng = random.Random(SEED)
    sample = rng.sample(realistic, SAMPLE_N)
    print(f"pool(passes_key & >=2 tokens)={len(pool_names)} "
          f"top{TOP_EXCLUDE}_excluded={len(top)} "
          f"realistic={len(realistic)} sample={len(sample)}")
    return set(sample)


# ---------------------------------------------------------------------------
def scan_raw_labels(sample_set):
    """One pass over the corpus: for each sampled guest, count raw labels."""
    counts = defaultdict(Counter)  # norm_name -> Counter(raw_label)
    speaker_cache = {}
    t0 = time.time()
    n = 0
    for rec in M.stream_records(M.RAW_JSON):
        n += 1
        if n % 50000 == 0:
            print(f"  scan {n} recs ({time.time()-t0:.0f}s)")
        for raw in (rec.get("speaker") or []):
            c = speaker_cache.get(raw)
            if c is None:
                c = M.classify_speaker(raw)
                speaker_cache[raw] = c
            kind, name, _ = c
            if kind == "guest" and name in sample_set:
                counts[name][raw] += 1
    print(f"  scan done: {n} recs in {time.time()-t0:.0f}s; "
          f"found labels for {len(counts)}/{len(sample_set)} sampled guests")
    return counts


# ---------------------------------------------------------------------------
_PAREN = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_DASH = re.compile(r"\s[-–—:]\s")
_ALPHA = re.compile(r"[A-Za-z]+")


def raw_to_query(raw):
    """Strip honorific + role suffix + 'reporting'; keep casing.

    Returns (stripped_raw_original_casing, wikipedia_query_string).
    """
    s = _PAREN.sub(" ", raw)
    s = s.split(",")[0]
    s = _DASH.split(s)[0]
    s = re.sub(r"\breporting\b", " ", s, flags=re.I)
    s = s.strip().strip(".").strip()
    # strip leading honorifics (case-insensitive), preserve remaining casing
    changed = True
    while changed and s:
        changed = False
        su = s.upper()
        for ph in M.HONORIFIC_MULTI:
            if su.startswith(ph + " "):
                s = s[len(ph):].strip()
                changed = True
                break
        if changed:
            continue
        parts = s.split(None, 1)
        if len(parts) > 1 and parts[0].rstrip(".").upper() in M.HONORIFIC:
            s = parts[1].strip()
            changed = True
    s = re.sub(r"\s+", " ", s).strip(" .,-")
    # decide casing for the query
    name_letters = [c for c in s if c.isalpha()]
    if name_letters and not any(c.islower() for c in name_letters):
        # all-caps -> title-case per word (Wikipedia redirects fix inner caps)
        q = _ALPHA.sub(lambda m: m.group(0)[:1].upper() + m.group(0)[1:].lower(), s)
    else:
        q = s
    return s, q


# ---------------------------------------------------------------------------
def wiki_exists(queries):
    """queries: list of unique query strings -> {q: True/False/None}."""
    out = {}
    for start in range(0, len(queries), 50):
        batch = queries[start:start + 50]
        params = {"action": "query", "titles": "|".join(batch),
                  "redirects": 1, "format": "json"}
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  wiki batch @{start} failed: {e}")
            time.sleep(2)
            continue
        q = data.get("query", {})
        norm = {d["from"]: d["to"] for d in q.get("normalized", [])}
        redir = {d["from"]: d["to"] for d in q.get("redirects", [])}
        by_title = {p.get("title", ""): ("missing" not in p)
                    for p in q.get("pages", {}).values()}
        by_ci = {k.lower(): v for k, v in by_title.items()}
        for name in batch:
            t = norm.get(name, name)
            t = redir.get(t, t)
            ex = by_title.get(t)
            if ex is None:
                ex = by_ci.get(t.lower())
            out[name] = bool(ex) if ex is not None else False
        time.sleep(1.1)
        print(f"  wiki {min(start+50, len(queries))}/{len(queries)}")
    return out


# ---------------------------------------------------------------------------
def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


# ---------------------------------------------------------------------------
def main():
    sample_set = build_sample()
    counts = scan_raw_labels(sample_set)

    # most frequent raw label per guest (tie -> higher count, then longer label)
    rows = []
    for name in sorted(sample_set):
        c = counts.get(name)
        if not c:
            rows.append({"name": name, "raw": "", "query": "", "found": False,
                         "exists": None, "occ": 0})
            continue
        raw = sorted(c.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))[0][0]
        stripped, query = raw_to_query(raw)
        rows.append({"name": name, "raw": raw, "stripped": stripped,
                     "query": query, "found": True, "exists": None,
                     "occ": c[raw]})

    queries = sorted({r["query"] for r in rows if r.get("query")})
    print(f"Querying Wikipedia for {len(queries)} distinct titles ...")
    ex = wiki_exists(queries)
    for r in rows:
        if r.get("query"):
            r["exists"] = ex.get(r["query"], False)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["normalized_name", "raw_label_queried", "wikipedia_query",
                    "raw_label_occurrences", "page_exists"])
        for r in rows:
            w.writerow([
                r["name"], r.get("raw", ""), r.get("query", ""), r["occ"],
                "" if r["exists"] is None else ("yes" if r["exists"] else "no"),
            ])

    checked = [r for r in rows if r["exists"] is not None]
    n = len(checked)
    longtail = [r for r in checked if r["exists"] is False]
    k = len(longtail)
    lo, hi = wilson_ci(k, n)
    print("\n=== WIKI RE-CHECK RESULT ===")
    print(f"sample_requested={SAMPLE_N} with_raw_label={n} "
          f"no_raw_label={SAMPLE_N - n}")
    print(f"long_tail={k} has_page={n-k} of n={n}")
    print(f"long_tail_rate={k/n:.3f}  95%CI_Wilson=[{lo:.3f}, {hi:.3f}]")
    print("example long-tail names:")
    for r in longtail[:15]:
        print(f"   {r['name']}  (raw={r['raw']!r} -> q={r['query']!r})")
    # stash summary for the addendum writer
    with open(os.path.join(M.OUT_DIR, "wiki_recheck_summary.json"), "w") as f:
        json.dump({"n": n, "k": k, "rate": k / n if n else 0,
                   "ci": [lo, hi], "no_raw": SAMPLE_N - n,
                   "examples": [r["name"] for r in longtail[:15]]}, f, indent=2)
    print(f"\nwrote {OUT_CSV}")


if __name__ == "__main__":
    main()
