"""Phase B curation — single corpus pass that feeds every downstream fix.

One stream over news_dialogue.json (463,596 records) that collects, in one go:

  1. Every transcript's date, re-parsed with a TOLERANT parser (MediaSum mixes
     zero-padded "2013-05-13" and non-padded "2013-5-13"; the Phase A parser
     required two digits and silently dropped 41.8% of all records).
  2. Global staff evidence for every name we might merge into a candidate
     (same rule as staff_crossref.py, extended to merge partners).
  3. For the transcripts that belong to the candidate pool (and to their
     possible label variants): the guest's own words, hashed into 5-word
     shingles for near-duplicate detection, plus the raw speaker labels and
     which candidate names co-occur in the same transcript (merge evidence).

Everything is cached so the analysis step (curate_pool_v2.py) can be re-run
without touching the 4.4 GB file again.

CPU only, no network, no LLM. Run: uv run python experiments/curate_scan_v2.py
"""
import datetime
import hashlib
import os
import pickle
import re
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mediasum_index as M  # noqa: E402  (reuse parser + classifier)
import staff_crossref as SC  # noqa: E402  (reuse staff-evidence rules)

ROOT = M.ROOT
POOL_CSV = os.path.join(ROOT, "results/stage2_candidate_pool.csv")
OUT_DIR = M.OUT_DIR
CACHE_PKL = os.path.join(OUT_DIR, "_scan_cache_v2.pkl")
DATES_CSV = os.path.join(OUT_DIR, "transcript_dates_v2.csv")

SHINGLE_K = 5

# ---------------------------------------------------------------------------
# 1. Tolerant date parser
# ---------------------------------------------------------------------------
# Empirical check over all 463,596 raw date strings (10,315 distinct):
#   269,669 zero-padded YYYY-MM-DD, 193,927 non-padded YYYY-M-D, 0 empty,
#   0 otherwise unparseable, 2 with an implausible year (3007).
# "2000-1-1" occurs 55 times, right in line with its January-2000 neighbours
# (45-79 per day), so it is a REAL date, not a placeholder. See the curation
# report for the full check.
_DATE_TOL = re.compile(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$")
MIN_YEAR, MAX_YEAR = 1990, 2021


def parse_date_tolerant(s):
    """Return (iso_date_or_empty, quality_flag).

    quality in {ok, ok_padding_fixed, implausible_year, invalid_calendar,
    unparseable, missing}.
    """
    if not s or not isinstance(s, str):
        return ("", "missing")
    m = _DATE_TOL.match(s)
    if not m:
        return ("", "unparseable")
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        dt = datetime.date(y, mo, d)
    except ValueError:
        return ("", "invalid_calendar")
    if not (MIN_YEAR <= y <= MAX_YEAR):
        return (dt.isoformat(), "implausible_year")
    padded = len(m.group(2)) == 2 and len(m.group(3)) == 2
    return (dt.isoformat(), "ok" if padded else "ok_padding_fixed")


# ---------------------------------------------------------------------------
# 2. Shingling for near-duplicate detection
# ---------------------------------------------------------------------------
_WORD_RE = re.compile(r"[a-z0-9']+")


def _h64(s):
    return int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(),
                          "big")


def shingle_set(text, k=SHINGLE_K):
    """Sorted unique uint64 hashes of k-word shingles of `text`."""
    words = _WORD_RE.findall(text.lower())
    if not words:
        return np.zeros(0, dtype=np.uint64)
    if len(words) < k:
        return np.array([_h64(" ".join(words))], dtype=np.uint64)
    grams = [" ".join(words[i:i + k]) for i in range(len(words) - k + 1)]
    return np.unique(np.fromiter((_h64(g) for g in grams), dtype=np.uint64,
                                 count=len(grams)))


# ---------------------------------------------------------------------------
# 3. Which names / transcripts the scan has to look at
# ---------------------------------------------------------------------------
def _tokens(name):
    return name.split()


def _is_initial(tok):
    return len(tok.rstrip(".")) <= 1 and tok.rstrip(".").isalpha()


def _punct_key(name):
    """Letters-only uppercase key: 'J.J. Sutherland' == 'Jj Sutherland'."""
    return re.sub(r"[^A-Za-z]", "", name).upper()


def build_name_universe(pool_names, index_names):
    """Pool names + every name that could be a label variant of one of them.

    Returns (universe_set, candidate_pairs) where candidate_pairs is a list of
    (name_a, name_b, rule) proposals still needing evidence.
    """
    pool = set(pool_names)
    idx = set(index_names)

    # index by "everything after the first token" for initial<->full matching
    by_rest = defaultdict(list)
    by_punct = defaultdict(list)
    for n in idx:
        t = _tokens(n)
        if len(t) >= 2:
            by_rest[tuple(t[1:])].append(n)
        by_punct[_punct_key(n)].append(n)

    pairs = []
    seen_pairs = set()

    def add(a, b, rule):
        if a == b:
            return
        key = (min(a, b), max(a, b), rule)
        if key in seen_pairs:
            return
        seen_pairs.add(key)
        pairs.append((key[0], key[1], rule))

    ext_honorific = set(M.HONORIFIC) | {
        "MONSIGNOR", "MSGR", "SWAMI", "GURU", "CHANCELLOR", "PREMIER",
        "CHAIRMAN", "CHAIRWOMAN", "SHERIFF", "MARSHAL", "PRIVATE", "PVT",
        "SPECIALIST", "AIRMAN", "SEAMAN", "CADET", "DEPUTY", "ALDERMAN",
        "TREASURER", "COMPTROLLER", "PRINCIPAL", "SUPT", "ENSIGN", "EMIR",
        "SULTAN", "BARON", "VISCOUNT", "EARL", "DUKE", "DUCHESS", "COUNT",
    }

    for p in pool:
        t = _tokens(p)

        # R2: "X Reporting" sign-off suffix
        if len(t) >= 3 and t[-1] == "Reporting":
            base = " ".join(t[:-1])
            if base in idx:
                add(p, base, "reporting_suffix")
        cand = p + " Reporting"
        if cand in idx:
            add(p, cand, "reporting_suffix")

        # R1: leading honorific that normalization did not strip
        if len(t) >= 3 and t[0].rstrip(".").upper() in ext_honorific:
            base = " ".join(t[1:])
            if base in idx:
                add(p, base, "honorific_residue")

        # R3: initial + surname  <->  full first name + surname
        if len(t) >= 2 and _is_initial(t[0]):
            letter = t[0].rstrip(".").upper()
            for q in by_rest.get(tuple(t[1:]), ()):
                qt = _tokens(q)
                if len(qt) == len(t) and not _is_initial(qt[0]) \
                        and qt[0][:1].upper() == letter:
                    add(p, q, "initial_vs_full")
        elif len(t) >= 2:
            for q in by_rest.get(tuple(t[1:]), ()):
                qt = _tokens(q)
                if len(qt) == len(t) and _is_initial(qt[0]) \
                        and qt[0].rstrip(".")[:1].upper() == t[0][:1].upper():
                    add(p, q, "initial_vs_full")

        # R4: middle initial dropped ("John F. Smith" ~ "John Smith")
        if len(t) == 3 and _is_initial(t[1]):
            base = t[0] + " " + t[2]
            if base in idx:
                add(p, base, "middle_initial")
        if len(t) == 2:
            for q in idx.intersection(
                    {f"{t[0]} {c}. {t[1]}" for c in
                     "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}):
                add(p, q, "middle_initial")

        # R5: punctuation-only difference ("J.J. X" vs "Jj X")
        for q in by_punct.get(_punct_key(p), ()):
            if q != p:
                add(p, q, "punctuation_variant")

    universe = set(pool)
    for a, b, _ in pairs:
        universe.add(a)
        universe.add(b)
    return universe, pairs


# ---------------------------------------------------------------------------
def load_inputs():
    import csv as _csv
    pool_names, pool_rows = [], {}
    with open(POOL_CSV) as f:
        for row in _csv.DictReader(f):
            pool_names.append(row["normalized_name"])
            pool_rows[row["normalized_name"]] = row

    index_names = []
    index_examples = {}
    with open(M.INDEX_CSV) as f:
        for row in _csv.DictReader(f):
            n = row["normalized_name"]
            index_names.append(n)
            index_examples[n] = [t for t in
                                 (row["example_transcript_ids"] or "").split(";") if t]

    name_tids = defaultdict(set)
    with open(M.INTERVIEWS_CSV) as f:
        for row in _csv.DictReader(f):
            name_tids[row["normalized_name"]].add(row["transcript_id"])
    return pool_names, pool_rows, index_names, index_examples, name_tids


# ---------------------------------------------------------------------------
def main():
    t_start = time.time()
    (pool_names, pool_rows, index_names, index_examples,
     name_tids) = load_inputs()
    print(f"pool={len(pool_names)} index_names={len(index_names)} "
          f"names_with_2plus_transcripts={len(name_tids)}")

    universe, pairs = build_name_universe(pool_names, index_names)
    rule_counts = Counter(r for _, _, r in pairs)
    print(f"name universe = {len(universe)} "
          f"(pool {len(pool_names)} + {len(universe)-len(pool_names)} possible variants)")
    print(f"variant proposals: {len(pairs)} -> {dict(rule_counts)}")

    relevant = set()
    for n in universe:
        tids = name_tids.get(n)
        relevant |= tids if tids else set(index_examples.get(n, []))
    print(f"relevant transcripts: {len(relevant)}")

    # ---- the one pass ----
    tid_date = {}          # tid -> (iso, quality, program)  for ALL transcripts
    date_qual = Counter()
    staff_ev = {}          # name in universe -> (strength, marker, raw)
    seen_labels = set()
    shingles = {}          # (name, tid) -> np.uint64 array
    stats = {}             # (name, tid) -> [words, turns]
    tid_names = {}         # tid -> set of universe names present
    tid_rawlabels = {}     # tid -> list of raw labels (relevant tids only)
    raw_counts = defaultdict(Counter)   # name -> Counter(raw label)
    tid_info = {}          # tid -> (program, title, total_turns)

    speaker_cache = {}
    t0 = time.time()
    n = 0
    for rec in M.stream_records(M.RAW_JSON):
        n += 1
        if n % 50000 == 0:
            print(f"  ...{n} recs ({time.time()-t0:.0f}s) "
                  f"shingled={len(shingles)}")
        tid = rec.get("id")
        iso, q = parse_date_tolerant(rec.get("date"))
        date_qual[q] += 1
        program = (rec.get("program") or "").strip()
        tid_date[tid] = (iso, q, program)

        spk = rec.get("speaker") or []
        is_rel = tid in relevant

        # global staff evidence, restricted to names we might merge
        for raw in spk:
            if raw in seen_labels:
                continue
            seen_labels.add(raw)
            ev = SC.staff_evidence(raw)
            if not ev:
                continue
            nm = SC.normalize_name(raw)
            if nm is None or nm not in universe:
                continue
            cur = staff_ev.get(nm)
            if cur is None or ev[0] > cur[0]:
                staff_ev[nm] = (ev[0], ev[1], raw)

        if not is_rel:
            continue

        utt = rec.get("utt") or []
        m = min(len(utt), len(spk))
        tid_info[tid] = (program, (rec.get("title") or "").strip(), len(utt))
        tid_rawlabels[tid] = list(spk)
        local = defaultdict(list)   # name -> [texts]
        local_stats = defaultdict(lambda: [0, 0])
        for i in range(m):
            raw = spk[i]
            c = speaker_cache.get(raw)
            if c is None:
                c = M.classify_speaker(raw)
                speaker_cache[raw] = c
            kind, name, _hon = c
            if kind != "guest" or name not in universe:
                continue
            text = utt[i] or ""
            local[name].append(text)
            local_stats[name][0] += len(text.split())
            local_stats[name][1] += 1
            raw_counts[name][raw] += 1
        if local:
            tid_names[tid] = set(local.keys())
            for name, texts in local.items():
                shingles[(name, tid)] = shingle_set(" ".join(texts))
                stats[(name, tid)] = local_stats[name]

    scan_secs = time.time() - t0
    print(f"scan done: {n} records in {scan_secs:.0f}s; "
          f"distinct raw labels={len(seen_labels)}; "
          f"(name,tid) shingle sets={len(shingles)}")
    print("date quality:", dict(date_qual))

    # ---- outputs ----
    os.makedirs(OUT_DIR, exist_ok=True)
    import csv as _csv
    with open(DATES_CSV, "w", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["transcript_id", "date", "date_quality", "program"])
        for tid, (iso, q, prog) in tid_date.items():
            w.writerow([tid, iso, q, prog])
    print(f"wrote {DATES_CSV} ({len(tid_date)} rows)")

    with open(CACHE_PKL, "wb") as f:
        pickle.dump({
            "universe": universe,
            "pairs": pairs,
            "relevant": relevant,
            "shingles": shingles,
            "stats": stats,
            "tid_names": tid_names,
            "tid_rawlabels": tid_rawlabels,
            "tid_info": tid_info,
            "raw_counts": {k: dict(v) for k, v in raw_counts.items()},
            "staff_ev": staff_ev,
            "date_qual": dict(date_qual),
            "scan_secs": scan_secs,
            "n_records": n,
            "n_distinct_labels": len(seen_labels),
        }, f, protocol=4)
    print(f"wrote {CACHE_PKL} "
          f"({os.path.getsize(CACHE_PKL)/1e6:.0f} MB)")
    print(f"TOTAL {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
