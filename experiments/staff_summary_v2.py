"""Second staff filter: what the transcript SUMMARY says about the speaker.

The Phase A staff cross-reference only fires when a speaker LABEL somewhere in
the corpus carries a role marker. Network correspondents whose label is always
bare ("ALEX KELLOGG" in all 74 of its occurrences, "BRIAN UNGER" in all 162)
are invisible to it — and the hand audit found exactly those two still passing
as clean guests.

MediaSum's per-transcript `summary` field names them: "a group of teens ...
talk to NPR's Alex Kellogg", "our humorist Brian Unger examines ...". This
script reads every summary with a regex-only stream (8 s, no JSON parsing) and
flags subjects the summaries describe as network staff.

Two tiers, because precision matters more than recall here — an outside
journalist interviewed as an expert (Brian Bennett of the LA Times, Dexter
Filkins of the New Yorker) is a legitimate subject and must not be dropped:

  tier 1  network-owned phrasing: "NPR's X", "X, NPR News", "NPR correspondent
          X", "our humorist X"  -> exclude
  tier 2  a bare role word next to the name with no network possessive
          -> flag for human review, do not exclude

CPU only, no network, no LLM.
Run: uv run python experiments/staff_summary_v2.py
"""
import csv
import os
import re
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mediasum_index as M  # noqa: E402

OUT_DIR = M.OUT_DIR
DEDUP_MAP = os.path.join(OUT_DIR, "dedup_map_v2.csv")
CANON_MAP = os.path.join(OUT_DIR, "canonical_map_v2.csv")
OUT_CSV = os.path.join(OUT_DIR, "staff_summary_v2.csv")

# id, program, date, url, [title,] summary — NPR records carry a title field,
# CNN records do not.
REC_RE = re.compile(
    r'\{"id": "([^"]+)", "program": "(?:[^"\\]|\\.)*", "date": "[^"]*", '
    r'"url": "(?:[^"\\]|\\.)*", (?:"title": "(?:[^"\\]|\\.)*", )?'
    r'"summary": "((?:[^"\\]|\\.)*)"')

NET = r"(?:NPR|CNN)"
ROLE = (r"(?:correspondent|reporter|host|anchor|analyst|commentator|"
        r"contributor|producer|editor|humorist|critic|columnist|"
        r"news analyst|senior editor)")


def tier1_patterns(name):
    n = re.escape(name)
    return [
        ("network_possessive", rf"\b{NET}'s\s+{n}\b"),
        ("name_comma_network", rf"\b{n}\s*,?\s+(?:of\s+)?{NET}\s+News\b"),
        ("network_role_name", rf"\b{NET}\s+(?:\w+\s+){{0,3}}{ROLE}\s+{n}\b"),
        ("our_role_name", rf"\bour\s+(?:\w+\s+){{0,2}}{ROLE}\s+{n}\b"),
        ("name_of_network", rf"\b{n}\s*,\s*{NET}\b"),
    ]


def tier2_patterns(name):
    n = re.escape(name)
    return [
        ("bare_role_name", rf"\b{ROLE}\s+{n}\b"),
        ("name_reports", rf"\b{n}\s+report(?:s|ing)\b"),
    ]


def main():
    t0 = time.time()
    # subject -> transcripts, and every label variant we should look for
    subj_tids = defaultdict(set)
    with open(DEDUP_MAP) as f:
        for r in csv.DictReader(f):
            subj_tids[r["canonical_name"]].add(r["transcript_id"])
    variants = defaultdict(set)
    with open(CANON_MAP) as f:
        for r in csv.DictReader(f):
            variants[r["canonical_name"]].add(r["variant_name"])
    for c in subj_tids:
        variants[c].add(c)

    tid_subjects = defaultdict(list)
    for c, tids in subj_tids.items():
        for t in tids:
            tid_subjects[t].append(c)
    print(f"subjects={len(subj_tids)} transcripts of interest={len(tid_subjects)}")

    # compile one regex per subject per tier (names only, so this is small)
    compiled = {}
    for c in subj_tids:
        names = sorted({v for v in variants[c]
                        if len(v.split()) >= 2 and not v.endswith(" Reporting")})
        t1, t2 = [], []
        for nm in names:
            t1 += [(k, re.compile(p, re.I)) for k, p in tier1_patterns(nm)]
            t2 += [(k, re.compile(p, re.I)) for k, p in tier2_patterns(nm)]
        compiled[c] = (t1, t2)

    hits1 = defaultdict(Counter)
    hits2 = defaultdict(Counter)
    ex1, ex2 = {}, {}
    n = 0
    buf = ""
    with open(M.RAW_JSON, encoding="utf-8") as f:
        while True:
            chunk = f.read(64 * 1024 * 1024)
            if not chunk:
                break
            buf += chunk
            last = 0
            for m in REC_RE.finditer(buf):
                n += 1
                last = m.end()
                tid = m.group(1)
                subs = tid_subjects.get(tid)
                if not subs:
                    continue
                summ = m.group(2)
                for c in subs:
                    t1, t2 = compiled[c]
                    for k, rx in t1:
                        if rx.search(summ):
                            hits1[c][k] += 1
                            ex1.setdefault(c, (tid, summ[:220]))
                            break
                    else:
                        for k, rx in t2:
                            if rx.search(summ):
                                hits2[c][k] += 1
                                ex2.setdefault(c, (tid, summ[:220]))
                                break
            buf = buf[last:] if last else buf[-8000:]
    print(f"scanned {n} summaries in {time.time()-t0:.0f}s")

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["canonical_name", "n_transcripts", "tier1_hits",
                    "tier1_patterns", "tier2_hits", "tier2_patterns",
                    "summary_staff", "example_summary"])
        n1 = n2 = 0
        for c in sorted(subj_tids):
            h1 = sum(hits1[c].values())
            h2 = sum(hits2[c].values())
            verdict = "staff" if h1 >= 1 else ("review" if h2 >= 2 else "no")
            n1 += verdict == "staff"
            n2 += verdict == "review"
            ex = ex1.get(c) or ex2.get(c) or ("", "")
            w.writerow([c, len(subj_tids[c]), h1, ";".join(sorted(hits1[c])),
                        h2, ";".join(sorted(hits2[c])), verdict, ex[1]])
    print(f"wrote {OUT_CSV}: tier1 staff={n1}, tier2 review={n2}, "
          f"clean={len(subj_tids)-n1-n2}")

    print("\n=== precision check against the 20-guest hand audit ===")
    known_staff = ["Alex Kellogg", "Corey Dade", "Allison Aubrey",
                   "Jj Sutherland", "Brian Unger", "Emily Green"]
    known_good = ["Brian Bennett", "Don Pettit", "Suleika Jaouad",
                  "Suzanne Dimaggio", "Dexter Filkins", "Gustavo Arellano",
                  "Mary Kate Cary", "Michael Dimock", "Ramez Maluf",
                  "Vin Weber", "George Miller"]
    for label, names in (("SHOULD be flagged", known_staff),
                         ("should NOT be flagged", known_good)):
        print(f"-- {label} --")
        for nm in names:
            h1 = sum(hits1.get(nm, {}).values())
            h2 = sum(hits2.get(nm, {}).values())
            v = "staff" if h1 >= 1 else ("review" if h2 >= 2 else "no")
            print(f"   {nm:22s} tier1={h1:>3} tier2={h2:>3} -> {v}"
                  + ("" if nm in subj_tids else "   [not a subject]"))


if __name__ == "__main__":
    main()
