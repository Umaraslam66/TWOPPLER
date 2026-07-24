"""Global staff cross-reference for the Stage-2 candidate pool.

Network journalists appear under several labels: 'CARRIE KAHN, BYLINE' or
'CARRIE KAHN, NPR NEWS' in some transcripts, bare 'CARRIE KAHN' or 'CARRIE
KAHN reporting' in others. The bare form slips into the guest pool. This script
scans all 463,596 records once and marks any normalized name that EVER appears
anywhere with staff evidence, then cross-references the pool.

Staff evidence on a raw label =
  - a role marker word: HOST | ANCHOR | CORRESPONDENT | BYLINE | REPORTER |
    COMMENTATOR (strength 3), OR
  - a trailing 'reporting' sign-off (strength 2), OR
  - 'NPR' or 'CNN' appearing in the role part after the first comma (strength 1).

Name normalization matches mediasum_index.classify_speaker exactly, except a
standalone 'reporting' token is stripped first so 'NINA TOTENBERG reporting'
maps to the same key as bare 'NINA TOTENBERG'.

CPU only, no network. Writes data/mediasum_index/staff_crossref.csv only.
Run: uv run python experiments/staff_crossref.py
"""
import csv
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mediasum_index as M  # noqa: E402

POOL_CSV = os.path.join(M.ROOT, "results/stage2_candidate_pool.csv")
OUT_CSV = os.path.join(M.OUT_DIR, "staff_crossref.csv")

_REPORTING = re.compile(r"\breporting\b", re.I)
_ROLE = re.compile(r"\b(HOST|ANCHOR|CORRESPONDENT|BYLINE|REPORTER|COMMENTATOR)\b")
_NPRCNN = re.compile(r"\b(NPR|CNN)\b")


def normalize_name(raw):
    """Same as classify_speaker's guest-path, minus the staff early-return,
    plus a 'reporting' strip. Returns None for anonymous/generic/empty."""
    if not raw:
        return None
    if M.ANON_RE.search(raw.upper()):
        return None
    name = M._PAREN_RE.sub(" ", raw)
    name = name.split(",")[0]
    name = M._DASH_SPLIT_RE.split(name)[0]
    name = _REPORTING.sub(" ", name)
    name = name.strip().strip(".").strip()
    changed = True
    while changed and name:
        changed = False
        nu = name.upper()
        for phrase in M.HONORIFIC_MULTI:
            if nu.startswith(phrase + " "):
                name = name[len(phrase):].strip()
                changed = True
                break
        if changed:
            continue
        parts = name.split(None, 1)
        if not parts:
            break
        if parts[0].rstrip(".").upper() in M.HONORIFIC and len(parts) > 1:
            name = parts[1].strip()
            changed = True
    name = re.sub(r"\s+", " ", name).strip(" .,-")
    toks = M._ALPHA_RUN_RE.findall(name.upper())
    if not toks or all(t in M.GENERIC_TOKENS for t in toks):
        return None
    return M._titlecase(name)


def staff_evidence(raw):
    """Return (strength, marker) or None."""
    up = raw.upper()
    m = _ROLE.search(up)
    if m:
        return (3, m.group(1))
    if _REPORTING.search(raw):
        return (2, "REPORTING")
    if "," in raw:
        role = raw.split(",", 1)[1].upper()
        m2 = _NPRCNN.search(role)
        if m2:
            return (1, m2.group(1))
    return None


def main():
    # load pool
    pool = {}
    with open(POOL_CSV) as f:
        r = csv.DictReader(f)
        for row in r:
            pool[row["normalized_name"]] = row
    print(f"pool rows: {len(pool)}")

    # one pass: build staff-evidence dict over ALL distinct labels
    staff = {}  # norm_name -> (strength, marker, example_raw)
    seen = set()
    t0 = time.time()
    n = 0
    for rec in M.stream_records(M.RAW_JSON):
        n += 1
        if n % 50000 == 0:
            print(f"  scan {n} recs ({time.time()-t0:.0f}s), "
                  f"staff names so far={len(staff)}")
        for raw in (rec.get("speaker") or []):
            if raw in seen:
                continue
            seen.add(raw)
            ev = staff_evidence(raw)
            if not ev:
                continue
            name = normalize_name(raw)
            if not name:
                continue
            cur = staff.get(name)
            if cur is None or ev[0] > cur[0]:
                staff[name] = (ev[0], ev[1], raw)
    print(f"  scan done: {n} recs in {time.time()-t0:.0f}s; distinct labels="
          f"{len(seen)}; distinct staff-flagged names={len(staff)}")

    # cross-reference pool, write CSV
    flagged = 0
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["normalized_name", "staff_evidence", "marker",
                    "example_raw_label"])
        for name in pool:
            ev = staff.get(name)
            if ev:
                flagged += 1
                w.writerow([name, "yes", ev[1], ev[2]])
            else:
                w.writerow([name, "no", "", ""])
    print(f"wrote {OUT_CSV}; flagged {flagged}/{len(pool)}")

    # ---- report numbers ----
    def is_longtail(row):
        return (row.get("wiki_status") or "").startswith("long-tail")

    lt_rows = [r for r in pool.values() if is_longtail(r)]
    lt_flagged = sum(1 for r in lt_rows if r["normalized_name"] in staff)
    cleaned_pool = len(pool) - flagged
    cleaned_lt = [r for r in lt_rows if r["normalized_name"] not in staff]

    print("\n=== STAFF CROSS-REF RESULT ===")
    print(f"pool total: {len(pool)}")
    print(f"flagged as staff: {flagged}")
    print(f"long-tail rows: {len(lt_rows)}; long-tail flagged: {lt_flagged}")
    print(f"cleaned pool size: {cleaned_pool}")
    print(f"cleaned long-tail count: {len(cleaned_lt)}")

    def wc(r):
        return int(r["total_guest_words"])
    cleaned_lt.sort(key=lambda r: -wc(r))
    print("\n15 example CLEANED long-tail candidates "
          "(name | subst_appearances | total_words | span_days | npr_share):")
    for r in cleaned_lt[:15]:
        print(f"   {r['normalized_name']} | {r['subst_appearances']} | "
              f"{r['total_guest_words']} | {r['span_days']} | {r['npr_share']}")

    # sanity checks
    print("\n=== SANITY ===")
    for nm in ["Carrie Kahn", "Martin Kaste", "Pam Fessler"]:
        ev = staff.get(nm)
        print(f"  {nm}: flagged={'YES' if ev else 'NO'}"
              + (f" ({ev[1]} | {ev[2]!r})" if ev else "")
              + (" [in pool]" if nm in pool else " [NOT in pool]"))
    for nm in ["Suleika Jaouad", "Don Pettit", "Ramez Maluf"]:
        ev = staff.get(nm)
        print(f"  {nm}: flagged={'YES' if ev else 'NO'}"
              + (f" ({ev[1]} | {ev[2]!r})" if ev else "")
              + (" [in pool]" if nm in pool else " [NOT in pool]"))


if __name__ == "__main__":
    main()
