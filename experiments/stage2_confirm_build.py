"""Confirmatory Stage 2 BUILD: split, turns and D4 items for drawn subjects.

Run:     uv run python experiments/stage2_confirm_build.py --from 1 --to 40
Rebuild: uv run python experiments/stage2_confirm_build.py --from 1 --to 40 --force

This is the confirmatory generalization of the dev build pipeline. It reuses the
frozen machinery byte-for-byte and adds nothing to it:

    doppler.stage2_data.chronological_split   D2  (test = chronologically last)
    doppler.stage2_data.extract_turns         D3 + D3.1-r2 + D3.2
    doppler.qa_extract.extract_qa_verbose     D4  (cue filter, dedup, cap 20)

and applies the Amendment 2 Addendum A item-4 floor: a subject survives only if
its test-interview cluster yields >= 3 D4-eligible Q-A items.

What it writes, all under results/stage2_confirm/:

    subjects/<canonical_id>/split.json              grounding + test clusters
    subjects/<canonical_id>/grounding_turns.jsonl   D3 turns, grounding side
    subjects/<canonical_id>/test_turns.jsonl        D3 turns, test side
    subjects/<canonical_id>/qa_items.jsonl          D4 items (may be empty)
    subjects/<canonical_id>/build.json              the per-subject build record
    build_first40.json                              the tranche summary

Deterministic and resumable. A subject with a build.json whose recorded code
fingerprint still matches is skipped on re-run; --force rebuilds the range.

A broken subject is never silently substituted: it is written out with
``survived: false`` and a reason, and the run continues.

CPU only. No model call, no network, no GPU. The one expensive step is a single
streaming pass over the 4.45 GB corpus for the tranche's transcripts.

--------------------------------------------------------------------------
The one-on-one preference (Addendum A item 4), and why it is a FLAG here
--------------------------------------------------------------------------
Item 4 reads: "one-on-one interview programmes are preferred in the draw order
before panels/roundtables". Generalized beyond dev this is ambiguous: it could
mean the test cluster is *chosen* to be a one-on-one where the subject has one.

The dev pipeline's code does not do that, and this script does what the dev
pipeline's code does. See AMBIGUITY_CHOICES below for the full record.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doppler.qa_extract import extract_qa_verbose            # noqa: E402
from doppler.stage2_data import (                            # noqa: E402
    POOL_CSV,
    RAW_JSON,
    SCAN_CACHE,
    SPLIT_RULE,
    chronological_split,
    extract_turns,
    iter_wanted_raw,
    label_tokens,
    load_guest_words,
    load_pool,
    load_titles,
    subject_token_lists,
    word_count,
)

ROOT = Path(__file__).resolve().parents[1]
DRAW = ROOT / "results" / "stage2_confirm_draw_provisional.json"
OUT = ROOT / "results" / "stage2_confirm"
SUBJECTS = OUT / "subjects"

#: Addendum A item 4, frozen.
ITEM_FLOOR = 3

#: The pre-registered expectation this tranche is measured against
#: (Addendum A item 4, restated in the launch plan and the draw file).
EXPECTED_SURVIVAL = 0.70
EXPECTED_CI = (0.575, 0.801)

#: Launch-plan risk-table row 4: cumulative survival below the pre-registered
#: CI floor is an item-yield collapse and stops the build for an owner call.
CI_FLOOR = EXPECTED_CI[0]

#: The halt is not armed until this many positions are in hand. The launch plan
#: checks "after every 20 subjects built", and below that the rate is not a
#: measurement: a run that starts on a failing subject sits at 0% after one
#: position and would stop itself before it began.
HALT_MIN_N = 20

#: Bumped whenever the artifact contract changes, so stale build.json files
#: rebuild instead of being trusted.
SCHEMA_VERSION = 1

#: A build is a function of the frozen rule code, the pool and the draw. Hash
#: them, so a rule change invalidates the resume instead of being invisible.
FINGERPRINT_FILES = [
    "src/doppler/stage2_data.py",
    "src/doppler/qa_extract.py",
    "results/stage2_candidate_pool_v2.csv",
    "results/stage2_confirm_draw_provisional.json",
]

AMBIGUITY_CHOICES = [
    {
        "id": "A1",
        "rule": "Addendum A item 4, clause 2: 'one-on-one interview programmes "
                "are preferred in the draw order before panels/roundtables'",
        "ambiguity": "Generalized beyond dev, this could be read as a "
                     "TEST-CLUSTER SELECTION rule (pick a one-on-one cluster as "
                     "the test interview when the subject has one) rather than "
                     "an ordering remark.",
        "choice": "Test cluster = the chronologically last cluster, full stop "
                  "(frozen D2, doppler.stage2_data.chronological_split). "
                  "one_on_one is RECORDED as a per-subject flag, never used to "
                  "select.",
        "why_this_reading": "It is the reading the dev pipeline's code already "
            "embodies. chronological_split contains no one-on-one term "
            "anywhere; the string 'one_on_one' occurs in exactly one file in "
            "the repository, experiments/barlock_eligibility.py, where it is "
            "computed POST HOC from the already-selected test transcript's "
            "role counts and used only to report a pass-rate breakdown "
            "(88.6% one-on-one vs 44.0% panels). Critically, the 70% survival "
            "expectation (95% CI 57.5-80.1) that this tranche is scored "
            "against was measured that same way, so selecting on one-on-one "
            "here would raise survival above its own benchmark and make the "
            "comparison meaningless.",
        "impact": "None on which cluster is tested; the flag is reported.",
    },
    {
        "id": "A2",
        "rule": "one_on_one definition",
        "ambiguity": "MediaSum has no programme-format field, so 'one-on-one' "
                     "has to be operationalized.",
        "choice": "The dev proxy, copied verbatim from "
                  "experiments/barlock_eligibility.py: a test transcript whose "
                  "D3 role counts have zero 'other' turns and at least one "
                  "'host' turn and at least one 'guest' turn.",
        "why_this_reading": "It is the only definition the dev pipeline ever "
            "used, and it is the definition under which the 88.6%/44.0% split "
            "was measured.",
        "impact": "Reported flag only.",
    },
    {
        "id": "A3",
        "rule": "D2 invariant failures (dev: build_subject raises SystemExit)",
        "ambiguity": "The dev pipeline aborted the whole run on a broken "
                     "subject; at 140 confirmatory subjects that would let one "
                     "bad row halt the tranche.",
        "choice": "The same invariants are checked in the same order, but a "
                  "violation marks THAT subject failed with the reason and the "
                  "run continues. No invariant was weakened, and no subject is "
                  "ever substituted for another.",
        "why_this_reading": "Task constraint: 'if a subject's data is broken, "
            "mark failed with reason and continue (never silently substitute)'. "
            "The checks themselves are unchanged.",
        "impact": "Failure taxonomy gains split_invariant_violated, "
                  "transcript_missing_from_corpus, transcript_unparsable and "
                  "turn_extraction_failed.",
    },
    {
        "id": "A4",
        "rule": "Item-floor failure reasons",
        "ambiguity": "Item 4 gives one floor (>= 3), so a plain reading has a "
                     "single failure reason.",
        "choice": "Split into zero_d4_items (n_items == 0) and "
                  "below_item_floor (1 or 2 items). Both are failures; the "
                  "floor is unchanged.",
        "why_this_reading": "A zero-item subject is a named tripwire for this "
            "tranche, and it is also the exact dev pathology (C00292, "
            "DIPLOMATIC LICENSE roundtable). Separating them makes the "
            "tripwire legible in the histogram rather than hidden inside a "
            "generic bucket.",
        "impact": "Reporting only; identical survivor set either way.",
    },
]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def sha16(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def fingerprint() -> dict[str, str]:
    return {p: sha16(ROOT / p) for p in FINGERPRINT_FILES}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval — the interval barlock_eligibility.py used."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


_DATE_RE = re.compile(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})")


def norm_date(value) -> tuple[int, int, int] | None:
    """Day-granularity form of a date. The corpus writes '2000-7-21', the pool
    writes '2000-07-21'; those are the same day and must not read as a clash."""
    m = _DATE_RE.match(str(value or ""))
    if m is None:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def jsonl_text(rows) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, doc) -> None:
    write_text(path, json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Corpus access — tolerant, so one bad transcript fails one subject
# ---------------------------------------------------------------------------

def fetch_tolerant(transcript_ids) -> tuple[dict[str, dict], dict[str, str]]:
    """One streaming pass. Returns (records, {transcript_id: failure reason}).

    Same scan and same decode as stage2_data.fetch_records; the only difference
    is that a missing or undecodable transcript is REPORTED rather than raised,
    because at tranche scale one bad row must not take the run down with it.
    """
    wanted = set(transcript_ids)
    if not wanted:
        return {}, {}
    decoder = json.JSONDecoder()
    out: dict[str, dict] = {}
    bad: dict[str, str] = {}
    for rid, raw in iter_wanted_raw(RAW_JSON, wanted):
        try:
            record, _ = decoder.raw_decode(raw.decode("utf-8"))
        except Exception as exc:                        # noqa: BLE001
            bad[rid] = f"json_decode_error: {type(exc).__name__}: {exc}"
            continue
        if record.get("id") != rid:
            bad[rid] = (f"record_boundary_error: marker said {rid}, decoded "
                        f"{record.get('id')}")
            continue
        out[rid] = record
    for tid in sorted(wanted - set(out) - set(bad)):
        bad[tid] = "not_found_in_corpus"
    return out, bad


# ---------------------------------------------------------------------------
# Per-subject build
# ---------------------------------------------------------------------------

def split_entries(split: dict) -> list[dict]:
    return [*split["grounding"], split["test"], *split["excluded_same_date"]]


def build_one(entry_draw: dict, row: dict, split: dict,
              records: dict[str, dict], bad: dict[str, str]) -> dict:
    """Build one drawn subject. Never raises for bad data — it reports.

    Mirrors experiments/stage2_draw_dev.py build_subject: the corpus records are
    authoritative for title/program/guest-word counts, every split entry is
    refreshed from them, the D2 invariants are re-checked, then D3 turns and D4
    items. The dev version raises SystemExit on a violation; here a violation
    becomes this subject's failure reason (choice A3).
    """
    cid = row["canonical_id"]
    rec_base = {
        "schema_version": SCHEMA_VERSION,
        "canonical_id": cid,
        "canonical_name": row["canonical_name"],
        "draw_pos": entry_draw["draw_pos"],
        "stratum": entry_draw["stratum"],
        "h7_eligible": entry_draw["h7_eligible"],
        "wiki_status": row["wiki_status"],
        "n_dedup_clusters": entry_draw["n_dedup_clusters"],
        "span_days_dedup": entry_draw["span_days_dedup"],
        "fingerprint": fingerprint(),
        "item_floor": ITEM_FLOOR,
    }

    def fail(reason: str, detail=None, **extra) -> dict:
        return {**rec_base, "survived": False, "n_items": 0,
                "failure_reason": reason, "failure_detail": detail, **extra}

    # --- every transcript this subject needs must have decoded --------------
    needed = [e["transcript_id"] for e in split_entries(split)]
    missing = [t for t in needed if t in bad and bad[t] == "not_found_in_corpus"]
    unparsable = [t for t in needed if t in bad and bad[t] != "not_found_in_corpus"]
    if missing:
        return fail("transcript_missing_from_corpus",
                    {t: bad[t] for t in missing}, transcripts_affected=missing)
    if unparsable:
        return fail("transcript_unparsable",
                    {t: bad[t] for t in unparsable},
                    transcripts_affected=unparsable)

    # --- refresh the split from the records (dev build_subject, verbatim) ----
    warnings, date_clashes = [], []
    pool_dates = {e["transcript_id"]: e["date"] for e in row["transcripts"]}
    try:
        for e in split_entries(split):
            rec = records[e["transcript_id"]]
            e["title"] = rec.get("title", "")
            e["program"] = rec.get("program", e["program"])
            cached = e["guest_words"]
            actual = sum(word_count(t["text"]) for t in extract_turns(rec, row)
                         if t["role"] == "guest")
            e["guest_words"] = actual
            if cached and abs(actual - cached) > 0.1 * cached:
                warnings.append({"transcript_id": e["transcript_id"],
                                 "extracted": actual, "scan_cache": cached})
    except ValueError as exc:      # utt/speaker length mismatch in a record
        return fail("turn_extraction_failed", str(exc))

    # --- tripwire: pool CSV date vs corpus date, day granularity ------------
    for tid in sorted({e["transcript_id"] for e in split_entries(split)}):
        pool_d = norm_date(pool_dates.get(tid))
        corpus_d = norm_date(records[tid].get("date"))
        if pool_d != corpus_d:
            date_clashes.append({"transcript_id": tid,
                                 "pool_date": pool_dates.get(tid),
                                 "corpus_date": records[tid].get("date")})

    # --- D2 invariants (dev build_subject, same order) ----------------------
    test_tid = split["test"]["transcript_id"]
    ground_tids = [e["transcript_id"] for e in split["grounding"]]
    if test_tid in ground_tids:
        return fail("split_invariant_violated",
                    "the test transcript is also in grounding")
    if split["test"]["date"] <= max(e["date"] for e in split["grounding"]):
        return fail("split_invariant_violated",
                    "the test cluster is not strictly later than every "
                    "grounding cluster")
    for e in split["grounding"]:
        if max(e.get("member_dates") or [e["date"]]) >= split["test"]["date"]:
            return fail("split_invariant_violated",
                        f"grounding cluster {e['cluster_id']} has a member "
                        "transcript dated on or after the test date "
                        "(D2 leak guard)")

    # --- D3 turns -----------------------------------------------------------
    try:
        ground_turns = [t for tid in ground_tids
                        for t in extract_turns(records[tid], row)]
        test_turns = extract_turns(records[test_tid], row)
    except ValueError as exc:
        return fail("turn_extraction_failed", str(exc))
    if any(t["transcript_id"] == test_tid for t in ground_turns):
        return fail("split_invariant_violated",
                    "test text leaked into grounding turns")

    # --- D4 items -----------------------------------------------------------
    try:
        items, drops = extract_qa_verbose(test_turns, cid, test_tid)
    except ValueError as exc:
        return fail("qa_extraction_failed", str(exc))

    roles = Counter(t["role"] for t in test_turns)
    # Choice A2: the dev proxy, copied from barlock_eligibility.py.
    one_on_one = (roles.get("other", 0) == 0 and roles.get("host", 0) > 0
                  and roles.get("guest", 0) > 0)

    n_items = len(items)
    survived = n_items >= ITEM_FLOOR
    if survived:
        reason = None
    elif n_items == 0:
        reason = "zero_d4_items"                        # choice A4
    else:
        reason = "below_item_floor"

    record = {
        **rec_base,
        "survived": survived,
        "n_items": n_items,
        "failure_reason": reason,
        "failure_detail": None if survived else
                          f"{n_items} D4-eligible item(s), floor is {ITEM_FLOOR}",
        "test_cluster": {
            "cluster_id": split["test"]["cluster_id"],
            "transcript_id": test_tid,
            "date": split["test"]["date"],
            "programme": split["test"]["program"],
            "title": split["test"]["title"],
            "n_transcripts_in_cluster": split["test"]["n_transcripts_in_cluster"],
            "member_dates": split["test"]["member_dates"],
            "guest_words": split["test"]["guest_words"],
        },
        "one_on_one": one_on_one,
        "test_role_counts": dict(sorted(roles.items())),
        "n_grounding_clusters": len(split["grounding"]),
        "grounding_guest_words": sum(word_count(t["text"]) for t in ground_turns
                                     if t["role"] == "guest"),
        "n_excluded_clusters": len(split["excluded_same_date"]),
        "n_qa_candidates": n_items + len(drops),
        "drop_reasons": dict(sorted(Counter(d["reason"] for d in drops).items())),
        "guest_word_warnings": warnings,
        "date_disagreements": date_clashes,
        "files": {
            "split.json": json.dumps(split, indent=1, ensure_ascii=False) + "\n",
            "grounding_turns.jsonl": jsonl_text(ground_turns),
            "test_turns.jsonl": jsonl_text(test_turns),
            "qa_items.jsonl": jsonl_text(items),
        },
    }
    return record


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def already_built(cid: str, fp: dict) -> dict | None:
    path = SUBJECTS / cid / "build.json"
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:                                   # noqa: BLE001
        return None
    if doc.get("schema_version") != SCHEMA_VERSION or doc.get("fingerprint") != fp:
        return None
    return doc


def parse_args(argv: list[str]) -> tuple[int, int, bool, str | None]:
    args, lo, hi, force, out = argv[1:], 1, 40, False, None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--force":
            force = True
        elif a == "--from":
            i += 1
            lo = int(args[i])
        elif a == "--to":
            i += 1
            hi = int(args[i])
        elif a == "--out":
            i += 1
            out = args[i]
        else:
            raise SystemExit(f"unknown argument: {a!r}. Accepted: --from N "
                             "--to M --out NAME --force")
        i += 1
    if lo < 1 or hi < lo:
        raise SystemExit(f"bad position range {lo}..{hi}")
    if out is not None and ("/" in out or not out.endswith(".json")):
        raise SystemExit(f"--out must be a bare .json filename, got {out!r}")
    return lo, hi, force, out


def main(argv: list[str]) -> int:
    lo, hi, force, out_name = parse_args(argv)
    t0 = time.time()
    for path in (POOL_CSV, RAW_JSON, SCAN_CACHE, DRAW):
        if not Path(path).exists():
            raise SystemExit(f"[fatal] missing input: {path}")

    draw = json.loads(DRAW.read_text(encoding="utf-8"))
    wanted_rows = [s for s in draw["subjects"] if lo <= s["draw_pos"] <= hi]
    if len(wanted_rows) != hi - lo + 1:
        raise SystemExit(f"[fatal] draw file has {len(wanted_rows)} subjects in "
                         f"positions {lo}..{hi}, expected {hi - lo + 1}")
    wanted_rows.sort(key=lambda s: s["draw_pos"])
    print(f"tranche: draw positions {lo}-{hi} ({len(wanted_rows)} subjects), "
          f"seed {draw['seed']}, floor >= {ITEM_FLOOR} D4 items")

    pool = load_pool(POOL_CSV)
    by_id = {r["canonical_id"]: r for r in pool}
    fp = fingerprint()

    todo, reused = [], {}
    for s in wanted_rows:
        cid = s["canonical_id"]
        if cid not in by_id:
            raise SystemExit(f"[fatal] drawn subject {cid} is not in the pool "
                             "CSV — the draw and the pool disagree, stop.")
        cached = None if force else already_built(cid, fp)
        if cached is not None:
            reused[cid] = cached
        else:
            todo.append(s)
    if reused:
        print(f"resume: {len(reused)} subject(s) already built and current, "
              f"{len(todo)} to build")

    # --- D2 splits for everything still to build ---------------------------
    rows = [by_id[s["canonical_id"]] for s in todo]
    splits: dict[str, dict] = {}
    split_errors: dict[str, str] = {}
    if rows:
        guest_words = load_guest_words(rows, SCAN_CACHE)
        titles = load_titles([e["transcript_id"] for r in rows
                              for e in r["transcripts"]], SCAN_CACHE)
        for r in rows:
            cid = r["canonical_id"]
            try:
                splits[cid] = chronological_split(
                    r, guest_words.get(cid, {}), titles)
            except ValueError as exc:
                split_errors[cid] = str(exc)

    # --- one corpus pass ----------------------------------------------------
    wanted_tids: set[str] = set()
    for split in splits.values():
        wanted_tids |= {e["transcript_id"] for e in split_entries(split)}
    records, bad = {}, {}
    if wanted_tids:
        print(f"streaming {RAW_JSON} once for {len(wanted_tids)} transcripts...")
        t1 = time.time()
        records, bad = fetch_tolerant(wanted_tids)
        print(f"  fetched {len(records)}/{len(wanted_tids)} in "
              f"{time.time() - t1:.1f}s"
              + (f"  [{len(bad)} unavailable]" if bad else ""))

    # --- build --------------------------------------------------------------
    built: dict[str, dict] = {}
    halted: dict | None = None
    for s in todo:
        cid = s["canonical_id"]
        row = by_id[cid]
        if cid in split_errors:
            msg = split_errors[cid]
            reason = ("no_grounding_clusters" if "no grounding" in msg
                      else "no_substantive_transcripts"
                      if "no substantive" in msg else "split_failed")
            rec = {
                "schema_version": SCHEMA_VERSION,
                "canonical_id": cid,
                "canonical_name": row["canonical_name"],
                "draw_pos": s["draw_pos"],
                "stratum": s["stratum"],
                "h7_eligible": s["h7_eligible"],
                "wiki_status": row["wiki_status"],
                "n_dedup_clusters": s["n_dedup_clusters"],
                "span_days_dedup": s["span_days_dedup"],
                "fingerprint": fp,
                "item_floor": ITEM_FLOOR,
                "survived": False,
                "n_items": 0,
                "failure_reason": reason,
                "failure_detail": msg,
            }
        else:
            rec = build_one(s, row, splits[cid], records, bad)
        files = rec.pop("files", None)
        d = SUBJECTS / cid
        if files:
            for fname, text in files.items():
                write_text(d / fname, text)
        write_json(d / "build.json", rec)
        built[cid] = rec
        flag = "ok " if rec["survived"] else "FAIL"
        extra = (f"one_on_one={rec.get('one_on_one')}" if rec["survived"]
                 else rec["failure_reason"])
        print(f"  [{rec['draw_pos']:>3}] {cid} {rec['canonical_name'][:24]:<24} "
              f"{flag} items={rec['n_items']:>2}  {extra}")

        # Launch-plan risk-table row 4. Cumulative survival over EVERY position
        # built so far, re-checked after each subject. A breach finishes the
        # position in hand (this one) and stops the run: extending the draw or
        # invoking the A5 subject-count branch is an owner decision, not one a
        # build script may make by carrying on.
        done_now = {**reused, **built}
        seen = [x for x in wanted_rows
                if x["draw_pos"] <= s["draw_pos"] and x["canonical_id"] in done_now]
        n_cum = len(seen)
        k_cum = sum(1 for x in seen if done_now[x["canonical_id"]]["survived"])
        cum = k_cum / n_cum if n_cum else 0.0
        if s["draw_pos"] % 20 == 0:
            print(f"      -- checkpoint @ pos {s['draw_pos']}: cumulative "
                  f"{k_cum}/{n_cum} = {cum:.1%}"
                  + ("   *** BELOW THE 57.5% CI FLOOR ***"
                     if cum < CI_FLOOR else f"   (floor {CI_FLOOR:.1%}, ok)"))
        if n_cum >= HALT_MIN_N and cum < CI_FLOOR:
            halted = {
                "halted": True,
                "at_draw_pos": s["draw_pos"],
                "halt_min_n": HALT_MIN_N,
                "cumulative_n": n_cum,
                "cumulative_survived": k_cum,
                "cumulative_rate": round(cum, 4),
                "ci_floor": CI_FLOOR,
                "rule": "launch plan risk-table row 4 (item-yield collapse): "
                        "cumulative survival fell below the pre-registered "
                        "95% CI floor of 57.5%. The current position was "
                        "finished and the run stopped. Extending the draw in "
                        "the same seeded order, or invoking the A5 "
                        "subject-count branch, is the owner's call.",
            }
            print(f"\n[HALT] cumulative survival {k_cum}/{n_cum} = {cum:.1%} is "
                  f"below the {CI_FLOOR:.1%} CI floor. Finished position "
                  f"{s['draw_pos']} and stopped — risk-table row 4, owner "
                  "decision required.")
            break

    # --- summary over the positions actually completed ----------------------
    done = {**reused, **built}
    completed_rows = [s for s in wanted_rows if s["canonical_id"] in done]
    per_subject = []
    for s in completed_rows:
        rec = done[s["canonical_id"]]
        per_subject.append({k: v for k, v in rec.items() if k != "fingerprint"})
    per_subject.sort(key=lambda r: r["draw_pos"])

    n = len(per_subject)
    survivors = [r for r in per_subject if r["survived"]]
    failures = [r for r in per_subject if not r["survived"]]
    k = len(survivors)
    lo_w, hi_w = wilson(k, n)
    rate = k / n if n else 0.0

    reasons = Counter(r["failure_reason"] for r in failures)
    item_hist = Counter(r["n_items"] for r in per_subject)

    # Running survival every 20 positions — the launch plan's kill-rule check.
    running = []
    cuts = list(range(20, n + 1, 20))
    if n and (not cuts or cuts[-1] != n):
        cuts.append(n)                       # always close on the final position
    for cut in cuts:
        head = per_subject[:cut]
        kk = sum(1 for r in head if r["survived"])
        running.append({"through_draw_pos": head[-1]["draw_pos"],
                        "n": cut, "n_survived": kk,
                        "rate": round(kk / cut, 4),
                        "below_ci_floor_0.575": (kk / cut) < CI_FLOOR,
                        "partial_checkpoint": cut % 20 != 0})

    oo = [r for r in per_subject if r.get("one_on_one")]
    non_oo = [r for r in per_subject
              if r.get("one_on_one") is False and "test_cluster" in r]

    def band(rows_):
        if not rows_:
            return {"n": 0, "n_survived": 0, "rate": None, "mean_items": None}
        kk = sum(1 for r in rows_ if r["survived"])
        return {"n": len(rows_), "n_survived": kk,
                "rate": round(kk / len(rows_), 4),
                "mean_items": round(sum(r["n_items"] for r in rows_)
                                    / len(rows_), 2)}

    # --- tripwires ----------------------------------------------------------
    single_token_subjects = []
    for r in per_subject:
        row = by_id[r["canonical_id"]]
        toks = subject_token_lists(row)
        if toks and all(len(t) < 2 for t in toks):
            single_token_subjects.append({
                "canonical_id": r["canonical_id"], "draw_pos": r["draw_pos"],
                "canonical_name": row["canonical_name"],
                "particle_surname": row.get("particle_surname"),
                "comparison_tokens": toks,
                "n_items": r["n_items"], "survived": r["survived"]})

    # A subject spelling that survives as a NAME but is thrown away as a token
    # LIST. subject_token_lists de-duplicates on " ".join(tokens), and a
    # hyphenated surname tokenises to ONE token containing a space
    # ("Wong-Ulrich" -> ['wong ulrich']) whose join key is identical to the
    # spaced form's (['wong','ulrich']). The hyphen spelling is therefore
    # dropped as a duplicate even though the two lists can never match each
    # other under name_matches_subject's contiguous-run test. When the corpus
    # writes the hyphenated form, the subject goes unrecognised.
    variant_collapse = []
    for r in per_subject:
        row = by_id[r["canonical_id"]]
        kept = subject_token_lists(row)
        kept_keys = {" ".join(t) for t in kept}
        dropped = [{"spelling": nm, "tokens": t}
                   for nm in [row["canonical_name"], *row.get("variants", [])]
                   for t in [label_tokens(nm)]
                   if t and t not in kept and " ".join(t) in kept_keys]
        if dropped:
            variant_collapse.append({
                "canonical_id": r["canonical_id"], "draw_pos": r["draw_pos"],
                "canonical_name": row["canonical_name"],
                "kept_token_lists": kept, "collapsed_spellings": dropped,
                "n_items": r["n_items"], "survived": r["survived"]})

    tripwires = {
        "transcripts_failed_to_parse": [
            {"canonical_id": r["canonical_id"], "draw_pos": r["draw_pos"],
             "reason": r["failure_reason"], "detail": r["failure_detail"]}
            for r in per_subject
            if r["failure_reason"] in ("transcript_missing_from_corpus",
                                       "transcript_unparsable",
                                       "turn_extraction_failed",
                                       "qa_extraction_failed")],
        "zero_d4_items": [
            {"canonical_id": r["canonical_id"], "draw_pos": r["draw_pos"],
             "programme": (r.get("test_cluster") or {}).get("programme"),
             "one_on_one": r.get("one_on_one"),
             "n_qa_candidates": r.get("n_qa_candidates"),
             "drop_reasons": r.get("drop_reasons")}
            for r in per_subject if r["n_items"] == 0],
        "date_disagreements_pool_vs_corpus": [
            {"canonical_id": r["canonical_id"], "draw_pos": r["draw_pos"],
             "clashes": r["date_disagreements"]}
            for r in per_subject if r.get("date_disagreements")],
        "split_invariant_violations": [
            {"canonical_id": r["canonical_id"], "draw_pos": r["draw_pos"],
             "detail": r["failure_detail"]}
            for r in per_subject
            if r["failure_reason"] == "split_invariant_violated"],
        "guest_word_warnings": [
            {"canonical_id": r["canonical_id"], "draw_pos": r["draw_pos"],
             "warnings": r["guest_word_warnings"]}
            for r in per_subject if r.get("guest_word_warnings")],
        # A subject the D3 rules cannot recognise anywhere in its own test
        # interview. The symptom of a name-resolution failure rather than of a
        # quiet interview, and it must never be read as "this person said
        # nothing" — the scan cache usually shows hundreds of guest words.
        "zero_guest_turns_in_test": [
            {"canonical_id": r["canonical_id"], "draw_pos": r["draw_pos"],
             "canonical_name": r["canonical_name"],
             "test_role_counts": r.get("test_role_counts"),
             "scan_cache_says_guest_words": [
                 w["scan_cache"] for w in (r.get("guest_word_warnings") or [])]}
            for r in per_subject
            if r.get("test_role_counts") is not None
            and r["test_role_counts"].get("guest", 0) == 0],
        # The cause behind the symptom above, detectable before extraction: a
        # subject whose every accepted spelling reduces to a SINGLE comparison
        # token. name_matches_subject needs two shared tokens to match by
        # containment, so such a subject can only ever match a label by exact
        # equality — and D3.1-r2 surname resolution rewrites a bare label to its
        # full introduced form, which then has two tokens and cannot match.
        "subject_key_single_token": single_token_subjects,
        "subject_variant_token_collapse": variant_collapse,
    }

    runtime = round(time.time() - t0, 1)
    summary = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tranche": {"draw_positions_requested": [lo, hi],
                    "n_subjects_requested": len(wanted_rows),
                    "n_subjects_completed": n,
                    "draw_positions_completed": (
                        [completed_rows[0]["draw_pos"],
                         completed_rows[-1]["draw_pos"]] if completed_rows
                        else []),
                    "not_built": [s["draw_pos"] for s in wanted_rows
                                  if s["canonical_id"] not in done],
                    "draw_file": str(DRAW.relative_to(ROOT)),
                    "draw_seed": draw["seed"]},
        "halted_early": halted,
        "rule": {
            "floor": f"a subject survives only if its test-interview cluster "
                     f"yields >= {ITEM_FLOOR} D4-eligible Q-A items "
                     "(PREREGISTRATION_AMENDMENT_2_ADDENDUM_A item 4, frozen)",
            "split": SPLIT_RULE,
            "extraction": "doppler.qa_extract.extract_qa_verbose, unmodified: "
                          "intro host turn dropped, question >= 5 words, "
                          "'?' or interrogative/imperative cue word, answer "
                          ">= 30 words, > 400 words truncated to ~300 at a "
                          "sentence boundary, near-duplicate questions "
                          "(Jaccard >= 0.8) dropped, first 20 survivors kept",
            "turns": "doppler.stage2_data.extract_turns, unmodified "
                     "(D3 + D3.1-r2 surname resolution + D3.2 programme-host)",
        },
        "ambiguity_choices": AMBIGUITY_CHOICES,
        "n_survived": k,
        "n_failed": n - k,
        "survival_rate": round(rate, 4),
        "survival_wilson95": [round(lo_w, 4), round(hi_w, 4)],
        "vs_preregistered_expectation": {
            "expected_rate": EXPECTED_SURVIVAL,
            "expected_ci95": list(EXPECTED_CI),
            "observed_rate": round(rate, 4),
            "observed_inside_expected_ci": EXPECTED_CI[0] <= rate <= EXPECTED_CI[1],
            "expected_inside_observed_ci": lo_w <= EXPECTED_SURVIVAL <= hi_w,
            "below_ci_floor_0.575": rate < EXPECTED_CI[0],
            "delta_vs_expected": round(rate - EXPECTED_SURVIVAL, 4),
            "projected_survivors_of_140_at_this_rate": round(140 * rate, 1),
            "projected_of_140_wilson95": [round(140 * lo_w, 1),
                                          round(140 * hi_w, 1)],
            "note": "The expectation was measured on a seeded 60-candidate "
                    "sample (experiments/barlock_eligibility.py, seed 73) drawn "
                    "from the same eligible pool minus the dev subjects, using "
                    "this same D2/D3/D4 code. It is a different sample from "
                    "this tranche, so agreement is a check, not a tautology.",
        },
        "failure_reason_histogram": dict(sorted(reasons.items())),
        "item_count_histogram": {str(kk): v
                                 for kk, v in sorted(item_hist.items())},
        "running_survival_every_20": running,
        "programme_shape": {"one_on_one": band(oo), "multi_speaker": band(non_oo),
                            "note": "Descriptive only — one_on_one never "
                                    "selects a test cluster (ambiguity choice "
                                    "A1)."},
        "by_stratum": {
            s_: band([r for r in per_subject if r["stratum"] == s_])
            for s_ in ("long-tail", "article")},
        "h7_eligible_survivors": sum(1 for r in survivors if r["h7_eligible"]),
        "tripwires": tripwires,
        "tripwires_fired": sorted(kk for kk, v in tripwires.items() if v),
        "cost": {"api_calls": 0, "gpu_hours": 0.0, "cost_usd": 0.0,
                 "note": "CPU only. No model call, no network fetch, no GPU. "
                         "$0.00."},
        "runtime_secs": runtime,
        "n_subjects_built_this_run": len(built),
        "n_subjects_reused": len(reused),
        "subjects": per_subject,
    }
    name = out_name or (f"build_first{hi}.json" if lo == 1
                        else f"build_pos{lo}_{hi}.json")
    write_json(OUT / name, summary)

    print(f"\nsurvived {k}/{n} = {rate:.1%}  "
          f"(Wilson 95% {lo_w:.1%}-{hi_w:.1%})")
    print(f"pre-registered: {EXPECTED_SURVIVAL:.0%} "
          f"(95% CI {EXPECTED_CI[0]:.1%}-{EXPECTED_CI[1]:.1%})  ->  "
          f"observed inside expected CI: "
          f"{summary['vs_preregistered_expectation']['observed_inside_expected_ci']}")
    print(f"failure reasons: {dict(sorted(reasons.items())) or '-'}")
    print(f"tripwires fired: {summary['tripwires_fired'] or '-'}")
    print(f"\nwritten under {OUT} in {runtime}s   API calls: 0   cost: $0.00")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
