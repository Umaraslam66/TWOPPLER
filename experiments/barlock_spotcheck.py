"""Bar-lock holds: the fuzzy-host spot-check sheet and the H7 date-sanity pass.

Two owner-requested checks on work already delivered in BARLOCK_MEASUREMENTS.md.
Both are CPU only and read dev/pool metadata plus the raw corpus.

HOLD 1 — spot-check sheet.
  A seeded 20-row sample of the 151-pair fuzzy-host census, stratified across
  the four ratio bands AND across my three labels, so the owner sees several of
  my `staff` and `false` calls and not only the easy `anchor` ones. The sheet
  carries no labels; my labels go to a separate key file.

HOLD 2 — H7 date sanity.
  The H7 feasibility numbers used the pool CSV's dates without checking them.
  This takes a seeded 30 of the 262 H7-eligible candidates, 2-3 transcripts
  each, and compares the CSV date against the raw MediaSum record's own `date`
  field and against date evidence inside the transcript text.

Usage:
    uv run python experiments/barlock_spotcheck.py plan     # what to fetch
    uv run python experiments/barlock_spotcheck.py fetch    # one corpus pass
    uv run python experiments/barlock_spotcheck.py sheet    # hold 1 output
    uv run python experiments/barlock_spotcheck.py dates    # hold 2 output
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doppler.stage2_data import (  # noqa: E402
    RAW_JSON, eligible_subjects, fetch_records, load_pool,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "stage2_pilot2" / "barlock"
CACHE_DIR = ROOT / "data" / "stage2_cache"          # gitignored
RECORDS = CACHE_DIR / "barlock_records.json"        # from barlock_eligibility
EXTRA = CACHE_DIR / "barlock_spotcheck_records.json"

SPOTCHECK_SEED = 79
DATE_SEED = 81
N_DATE_SUBJECTS = 30
TRANSCRIPTS_PER_SUBJECT = 3

BANDS = [(0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 1.01)]

#: (band, label) -> how many pairs to draw. Every one of the twelve cells is
#: represented; the extra eight rows go to the largest cells. The result is
#: 7 anchor / 5 staff / 8 false, so the owner is checking my hard calls and not
#: just the obvious anchors.
QUOTA = {
    ("0.55-0.60", "anchor"): 2, ("0.55-0.60", "staff"): 2, ("0.55-0.60", "false"): 3,
    ("0.60-0.65", "anchor"): 2, ("0.60-0.65", "staff"): 1, ("0.60-0.65", "false"): 2,
    ("0.65-0.70", "anchor"): 1, ("0.65-0.70", "staff"): 1, ("0.65-0.70", "false"): 1,
    ("0.70-1.01", "anchor"): 2, ("0.70-1.01", "staff"): 1, ("0.70-1.01", "false"): 2,
}

# ---------------------------------------------------------------------------
# Hold 1 — the sample
# ---------------------------------------------------------------------------


def band_of(ratio: float) -> str:
    return next(f"{lo:.2f}-{hi:.2f}" for lo, hi in BANDS if lo <= ratio < hi)


def load_census() -> dict[tuple[str, str], dict]:
    """{(descriptor, programme): {label, ratio, band, rows}} for the census."""
    labels = {}
    for line in (OUT / "fuzzy_host_labels.tsv").read_text().splitlines():
        if line.strip():
            v, d, p = line.split("\t")
            labels[(d, p)] = v
    scan = json.loads((OUT / "fuzzy_host_scan.json").read_text())
    pairs: dict[tuple[str, str], dict] = {}
    for r in scan["rows"]:
        if r["ratio"] < 0.55:
            continue
        k = (r["descriptor"], r["program"])
        e = pairs.setdefault(k, {"label": labels[k], "ratio": r["ratio"],
                                 "band": band_of(r["ratio"]), "rows": []})
        e["rows"].append(r)
    for e in pairs.values():
        # The most talkative transcript first: a spot-check row is only useful
        # if the speaker says something in it.
        e["rows"].sort(key=lambda r: (-r["n_turns"], r["transcript_id"]))
    return pairs


def draw_spotcheck() -> list[dict]:
    """The 20 pairs, in a single deterministic walk of the twelve cells."""
    pairs = load_census()
    rng = random.Random(SPOTCHECK_SEED)
    picked = []
    for cell in sorted(QUOTA):
        band, label = cell
        pool = sorted((k for k, v in pairs.items()
                       if v["band"] == band and v["label"] == label))
        idx = list(range(len(pool)))
        rng.shuffle(idx)
        for i in idx[:QUOTA[cell]]:
            k = pool[i]
            e = pairs[k]
            rep = e["rows"][0]      # most turns, then smallest transcript_id
            picked.append({
                "descriptor": k[0], "program": k[1], "ratio": e["ratio"],
                "band": band, "my_label": e["label"],
                "n_label_rows": len(e["rows"]),
                "transcript_id": rep["transcript_id"],
                "raw_label": rep["raw_label"], "title": rep["title"],
                "cell_population": len(pool),
            })
    # Present the sheet in ratio order so the owner reads a gradient, not my
    # stratification; the label column stays hidden either way.
    picked.sort(key=lambda r: (-r["ratio"], r["transcript_id"]))
    return picked


# ---------------------------------------------------------------------------
# Hold 2 — the date sample
# ---------------------------------------------------------------------------

MIN_CLUSTERS, MIN_SPAN_DAYS = 4, 731


def h7_eligible_rows() -> list[dict]:
    rows = []
    for r in eligible_subjects(load_pool()):
        clusters: dict[str, list[str]] = {}
        for e in r["transcripts"]:
            if e["substantive"]:
                clusters.setdefault(e["cluster_id"], []).append(e["date"])
        if len(clusters) < MIN_CLUSTERS:
            continue
        ds = sorted(min(v) for v in clusters.values())
        span = (_date.fromisoformat(ds[-1]) - _date.fromisoformat(ds[0])).days
        if span >= MIN_SPAN_DAYS:
            rows.append(r)
    return sorted(rows, key=lambda r: r["canonical_id"])


def draw_date_sample() -> list[dict]:
    rows = h7_eligible_rows()
    rng = random.Random(DATE_SEED)
    idx = list(range(len(rows)))
    rng.shuffle(idx)
    out = []
    for i in idx[:N_DATE_SUBJECTS]:
        r = rows[i]
        subs = sorted((e for e in r["transcripts"] if e["substantive"]),
                      key=lambda e: e["transcript_id"])
        j = list(range(len(subs)))
        rng.shuffle(j)
        out.append({"canonical_id": r["canonical_id"],
                    "canonical_name": r["canonical_name"],
                    "n_eligible_pool": len(rows),
                    "picks": [subs[x] for x in j[:TRANSCRIPTS_PER_SUBJECT]]})
    out.sort(key=lambda x: x["canonical_id"])
    return out


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def wanted() -> set[str]:
    ids = {r["transcript_id"] for r in draw_spotcheck()}
    for s in draw_date_sample():
        ids |= {p["transcript_id"] for p in s["picks"]}
    return ids


def all_records() -> dict[str, dict]:
    recs: dict[str, dict] = {}
    for p in (RECORDS, EXTRA):
        if p.exists():
            recs.update(json.loads(p.read_text()))
    return recs


def fetch() -> int:
    have = set(all_records())
    need = sorted(wanted() - have)
    print(f"wanted {len(wanted())}, cached {len(wanted() & have)}, "
          f"fetching {len(need)}")
    if not need:
        return 0
    t0 = time.time()
    recs = fetch_records(need, RAW_JSON)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    existing = json.loads(EXTRA.read_text()) if EXTRA.exists() else {}
    existing.update(recs)
    EXTRA.write_text(json.dumps(existing))
    print(f"  fetched {len(recs)} in {time.time() - t0:.1f}s")
    return 0


# ---------------------------------------------------------------------------
# Hold 1 output
# ---------------------------------------------------------------------------

def context_lines(rec: dict, raw_label: str, n: int = 2) -> list[str]:
    """Up to n of this speaker's longest turns, plus who spoke before them.

    Longest rather than first, because a first turn is often "Thank you." and
    says nothing about whether the speaker runs the show. The preceding
    speaker's label is included because "the anchor asked me a question" is the
    single most useful signal for the judgment.
    """
    if rec is None:
        return ["(transcript not fetched)"]
    hits = [(i, u) for i, (lab, u) in enumerate(zip(rec["speaker"], rec["utt"]))
            if lab == raw_label]
    if not hits:
        return ["(speaker label not found in the fetched record)"]
    hits.sort(key=lambda t: (-len(t[1]), t[0]))
    out = []
    for i, u in hits[:n]:
        prev = rec["speaker"][i - 1] if i > 0 else "(opens the transcript)"
        out.append(f"[after {prev}] " + " ".join(u.split())[:260])
    return out


def md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def sheet() -> int:
    rows = draw_spotcheck()
    recs = all_records()
    OUT.mkdir(parents=True, exist_ok=True)

    head = [
        "# Fuzzy host rule — owner spot-check sheet",
        "",
        "20 of the 151 (descriptor, programme) pairs the D3.2 fuzzy arm fires on",
        "at ratio >= 0.55. Drawn with `random.Random(79)`, stratified across the",
        "four ratio bands and across the three verdicts, then printed in ratio",
        "order. **My verdicts are not in this file** — they are in",
        "`fuzzy_host_spotcheck_key.md`.",
        "",
        "For each row, decide what the speaker is **on this programme**:",
        "",
        "* `anchor` — they present this show (what D3.2 exists to find)",
        "* `staff` — house staff of the show: correspondent, analyst, producer",
        "  (host side of the host/guest split, but not the interviewer)",
        "* `false` — a guest, a relative of the host, someone from another",
        "  network, or parse noise",
        "",
        "`ratio` is difflib's similarity between the normalised descriptor and the",
        "normalised programme. The current threshold is 0.60; the proposal is 0.65",
        "plus a guard. `rows` is how many label rows in the whole corpus carry this",
        "exact pair, so a wrong call on a high-`rows` line costs more.",
        "",
        "---",
        "",
    ]
    body = []
    for i, r in enumerate(rows, 1):
        rec = recs.get(r["transcript_id"])
        ctx = context_lines(rec, r["raw_label"])
        body += [
            f"### {i}. ratio {r['ratio']:.4f} — {r['transcript_id']} "
            f"({r['n_label_rows']} label row"
            f"{'' if r['n_label_rows'] == 1 else 's'} corpus-wide)",
            "",
            f"* **descriptor**: `{r['descriptor']}`",
            f"* **programme**: `{r['program']}`",
            f"* full speaker label: `{r['raw_label']}`",
            f"* transcript title: {r['title'] or '(none)'}",
            "",
            "What this speaker actually says (their longest turns, with who "
            "spoke immediately before):",
            "",
        ]
        for c in ctx:
            body += [f"> {c}", ""]
        body += ["**Your verdict (anchor / staff / false): ______________**", "",
                 "---", ""]

    tail = [
        "## Answer grid",
        "",
        "| # | ratio | transcript | descriptor | programme | your verdict |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        tail.append(
            f"| {i} | {r['ratio']:.4f} | {r['transcript_id']} | "
            f"`{md_escape(r['descriptor'])}` | `{md_escape(r['program'])}` |  |")
    tail.append("")

    (OUT / "fuzzy_host_spotcheck_sheet.md").write_text(
        "\n".join(head + body + tail))

    key = [
        "# Fuzzy host spot-check — my key",
        "",
        "My verdicts for the 20 rows in `fuzzy_host_spotcheck_sheet.md`, in the",
        "same order. Do not read this before filling in the sheet.",
        "",
        "Draw: `random.Random(79)` over the 151-pair census in",
        "`fuzzy_host_labels.tsv`, stratified by (ratio band, my verdict) with the",
        "quota in `experiments/barlock_spotcheck.py`. Sheet order is by descending",
        "ratio, so the stratification is not visible in the sheet.",
        "",
        "| # | ratio | band | transcript | descriptor | programme | my verdict | rows | cell pop |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        key.append(
            f"| {i} | {r['ratio']:.4f} | {r['band']} | {r['transcript_id']} | "
            f"`{md_escape(r['descriptor'])}` | `{md_escape(r['program'])}` | "
            f"**{r['my_label']}** | {r['n_label_rows']} | {r['cell_population']} |")
    counts = {v: sum(1 for r in rows if r["my_label"] == v)
              for v in ("anchor", "staff", "false")}
    key += [
        "",
        f"Verdict mix in this sample: anchor {counts['anchor']}, "
        f"staff {counts['staff']}, false {counts['false']}.",
        "",
        "`rows` = label rows in the whole corpus carrying this exact pair.",
        "`cell pop` = how many distinct pairs sit in this (band, verdict) cell,",
        "so a cell of 1 means this row IS the cell.",
        "",
        "Reading the result: disagreement on `anchor` vs `staff` moves only the",
        "lenient precision column in BARLOCK_MEASUREMENTS.md section 1;",
        "disagreement on either of those vs `false` moves the strict column and",
        "the guard's numbers.",
        "",
    ]
    (OUT / "fuzzy_host_spotcheck_key.md").write_text("\n".join(key))
    print(f"sheet: 20 rows, mix {counts}")
    return 0


# ---------------------------------------------------------------------------
# Hold 2 output
# ---------------------------------------------------------------------------

MONTHS = ("january february march april may june july august september "
          "october november december").split()
_FULLDATE_RE = re.compile(
    r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
    re.IGNORECASE)
_MONTHDAY_RE = re.compile(
    r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?\b",
    re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19\d{2}|20[0-3]\d)\b")

_LOOSE_DATE_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})")


def norm_date(s: str) -> str | None:
    """MediaSum's own date string as ISO, or None if it will not parse.

    The raw file writes both "2014-04-04" and "2014-4-4"; the corpus scan
    recorded 193,925 of 463,596 records needing this padding fix. Comparing the
    strings would call those a mismatch, which they are not.
    """
    m = _LOOSE_DATE_RE.match((s or "").strip())
    if not m:
        return None
    y, mo, d = (int(g) for g in m.groups())
    try:
        return _date(y, mo, d).isoformat()
    except ValueError:
        return None


#: The five H7 staleness bins, as (label, low_days, high_days).
BINS = [("<6m", 0, 183), ("6-12m", 183, 366), ("1-2y", 366, 731),
        ("2-3y", 731, 1096), (">3y", 1096, 10 ** 6)]


def bin_of(days: int) -> str:
    for label, lo, hi in BINS:
        if lo <= days < hi:
            return label
    return BINS[-1][0]


_RELATIVE_RE = re.compile(
    r"\b(today|tonight|this morning|this evening|this afternoon|yesterday|"
    r"last night|this week)\b", re.IGNORECASE)


def internal_evidence(rec: dict, csv_date: str) -> dict:
    """Cheap date evidence from the transcript's own words.

    Broadcast transcripts in this corpus almost never state their own date --
    they say "today's Washington Post", not "April 4th, 2014" -- so
    corroboration is rare by nature and its absence is not evidence of an error.

    The signal that DOES work is falsification: a broadcast cannot discuss a
    year later than the year it aired. If the newest four-digit year in the text
    is more than one year after the recorded date, the recorded date is wrong.
    (One year of slack, because a December show discusses next year.)

    Four signals:
      * an explicit full date ("March 14, 2011") matching the record;
      * a bare month+day matching the record, anywhere in the text;
      * whether the record's own year is mentioned at all;
      * the newest year mentioned, and whether it is an anachronism.
    """
    whole = " ".join(rec["utt"])
    d = _date.fromisoformat(csv_date)
    full = [(m.group(1).lower(), int(m.group(2)), int(m.group(3)))
            for m in _FULLDATE_RE.finditer(whole)]
    md = {(m.group(1).lower(), int(m.group(2)))
          for m in _MONTHDAY_RE.finditer(whole)}
    years = {int(y) for y in _YEAR_RE.findall(whole)}
    want = (MONTHS[d.month - 1], d.day, d.year)
    newest = max(years) if years else None
    return {
        "full_date_match": want in full,
        "full_dates_found": len(full),
        "month_day_match": (want[0], want[1]) in md,
        "year_mentioned": d.year in years,
        "newest_year_mentioned": newest,
        "anachronism": bool(newest is not None and newest > d.year + 1),
        "anachronism_years": (newest - d.year) if newest is not None else None,
        "has_relative_self_reference": bool(_RELATIVE_RE.search(whole)),
        "years_mentioned_sample": sorted(years)[-6:],
        "example_full_dates": [f"{a.title()} {b}, {c}" for a, b, c in full[:3]],
    }


def dates() -> int:
    t0 = time.time()
    sample = draw_date_sample()
    recs = all_records()

    per_transcript, per_subject = [], []
    n_ok = n_mismatch = n_missing = n_padding = 0
    max_delta = 0
    for s in sample:
        rows, deltas = [], []
        for p in s["picks"]:
            tid, csv_date = p["transcript_id"], p["date"]
            rec = recs.get(tid)
            if rec is None:
                n_missing += 1
                rows.append({"transcript_id": tid, "csv_date": csv_date,
                             "status": "record_missing"})
                continue
            ms = (rec.get("date") or "").strip()
            # MediaSum writes some dates unpadded ("2014-4-4"), which the pool
            # build normalised; compare CALENDAR DAYS, and report the raw string
            # difference separately so the two are never confused.
            exact_string = ms == csv_date
            ms_norm = norm_date(ms)
            same = ms_norm is not None and ms_norm == csv_date
            delta = None
            if ms_norm is not None and not same:
                delta = abs((_date.fromisoformat(ms_norm)
                             - _date.fromisoformat(csv_date)).days)
            if same:
                n_ok += 1
                if not exact_string:
                    n_padding += 1
            else:
                n_mismatch += 1
                if delta:
                    max_delta = max(max_delta, delta)
                    deltas.append(delta)
            rows.append({
                "transcript_id": tid, "csv_date": csv_date,
                "mediasum_date": ms, "mediasum_date_normalised": ms_norm,
                "exact_string_match": exact_string,
                "match": same, "delta_days": delta,
                "program_csv": p["program"],
                "program_mediasum": rec.get("program", ""),
                "internal": internal_evidence(rec, csv_date),
                "status": "ok",
            })
        per_transcript += rows
        per_subject.append({"canonical_id": s["canonical_id"],
                            "canonical_name": s["canonical_name"],
                            "n_checked": len(rows),
                            "n_mismatch": sum(1 for r in rows
                                              if r.get("match") is False),
                            "n_padding_only": sum(
                                1 for r in rows
                                if r.get("match") and not r.get("exact_string_match")),
                            "max_delta_days": max(deltas) if deltas else 0})

    checked = n_ok + n_mismatch
    ok_rows = [r for r in per_transcript if r["status"] == "ok"]
    corrob = sum(1 for r in ok_rows if r["internal"]["full_date_match"]
                 or r["internal"]["month_day_match"])
    year_ok = sum(1 for r in ok_rows if r["internal"]["year_mentioned"])
    anach = [r for r in ok_rows if r["internal"]["anachronism"]]
    relative = sum(1 for r in ok_rows
                   if r["internal"]["has_relative_self_reference"])

    # Would any observed discrepancy move a subject across an H7 bin? The bin
    # edges are 183 / 366 / 731 / 1096 days; a shift of `max_delta` can only
    # cross an edge if a real gap sits within `max_delta` of one.
    edges = [183, 366, 731, 1096]
    gaps_by_subject = []
    for r in eligible_subjects(load_pool()):
        clusters: dict[str, list[str]] = {}
        for e in r["transcripts"]:
            if e["substantive"]:
                clusters.setdefault(e["cluster_id"], []).append(e["date"])
        ds = sorted(min(v) for v in clusters.values())
        if len(ds) < 2:
            continue
        test = _date.fromisoformat(ds[-1])
        gaps_by_subject.append(
            [(test - _date.fromisoformat(x)).days for x in ds[:-1]])

    def at_risk_count(err: int) -> int:
        """Subjects with a gap close enough to a bin edge that `err` days of
        date error could move it across."""
        if err <= 0:
            return 0                 # no shift, so nothing can cross
        return sum(1 for gaps in gaps_by_subject
                   if any(abs(g - e) <= err for g in gaps for e in edges))

    ladder = {f"{err}d": at_risk_count(err) for err in (0, 1, 3, 7, 30)}
    at_risk = ["x"] * at_risk_count(max_delta)

    payload = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": DATE_SEED,
        "rule": (f"{N_DATE_SUBJECTS} subjects drawn with random.Random({DATE_SEED}) "
                 f"from the {sample[0]['n_eligible_pool']} H7-eligible candidates "
                 "(>= 4 dated substantive clusters spanning >= 2 years), sorted by "
                 "canonical_id; then up to "
                 f"{TRANSCRIPTS_PER_SUBJECT} of each subject's substantive "
                 "transcripts drawn from the same generator."),
        "n_subjects": len(sample),
        "n_transcripts_checked": checked,
        "n_records_missing": n_missing,
        "same_calendar_day": n_ok,
        "different_calendar_day": n_mismatch,
        "same_day_but_different_string_padding": n_padding,
        "exact_string_match": n_ok - n_padding,
        "calendar_day_match_rate": round(n_ok / checked, 4) if checked else None,
        "exact_string_match_rate": (round((n_ok - n_padding) / checked, 4)
                                    if checked else None),
        "max_delta_days": max_delta,
        "internal_evidence": {
            "of": len(ok_rows),
            "transcripts_with_matching_full_date_or_month_day": corrob,
            "transcripts_mentioning_the_recorded_year": year_ok,
            "transcripts_with_a_relative_self_reference": relative,
            "transcripts_with_an_anachronism": len(anach),
            "anachronism_examples": [
                {"transcript_id": r["transcript_id"], "csv_date": r["csv_date"],
                 "newest_year_mentioned": r["internal"]["newest_year_mentioned"]}
                for r in anach[:5]],
            "note": ("this corpus almost never states its own broadcast date, "
                     "so low corroboration is expected; the anachronism count "
                     "is the falsification test and it is the informative one"),
        },
        "bin_risk": {
            "bin_edges_days": edges,
            "max_observed_date_error_days": max_delta,
            "eligible_subjects_that_could_change_bin": at_risk_count(max_delta),
            "of_eligible": len(gaps_by_subject),
            "hypothetical_at_risk_by_error": ladder,
            "note": ("at 0 days of error nothing shifts, so nothing can cross a "
                     "bin edge; the ladder prices errors that were NOT observed"),
        },
        "per_subject": per_subject,
        "per_transcript": per_transcript,
        "runtime_secs": round(time.time() - t0, 1),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "h7_date_sanity.json").write_text(json.dumps(payload, indent=1))
    print(json.dumps({k: v for k, v in payload.items()
                      if k not in ("per_subject", "per_transcript")}, indent=1))
    return 0


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if what == "plan":
        w = wanted()
        have = set(all_records())
        print(f"{len(w)} transcripts wanted, {len(w & have)} cached, "
              f"{len(w - have)} to fetch")
    elif what == "fetch":
        raise SystemExit(fetch())
    elif what == "sheet":
        raise SystemExit(sheet())
    else:
        raise SystemExit(dates())
