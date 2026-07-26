"""Bar-lock item 4: how many subjects survive a D4 item-count floor?

Report 8.7 proposes that a subject's test interview must yield >= 3 D4-eligible
Q-A items before the subject is drawn at all. That floor decides how many
subjects Stage 2 can deliver, so this measures it:

  (a) the 6 dev subjects, from their committed qa_items.jsonl;
  (b) a seeded random sample of the full 578-row eligible pool, extracted the
      same way the pilot did (D2 split -> D3 turns -> D4 items) and reported as
      a survival rate with a Wilson 95% interval.

The sample exists because a full 578-subject extraction would stream the 4.45 GB
corpus for ~578 transcripts; the sample streams it once for ~60 and gives an
interval instead of a point.

CPU only, no network, no model calls.

Usage:
    uv run python experiments/barlock_eligibility.py fetch    # one corpus pass
    uv run python experiments/barlock_eligibility.py measure
"""

from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doppler.qa_extract import extract_qa_verbose  # noqa: E402
from doppler.stage2_data import (  # noqa: E402
    RAW_JSON,
    chronological_split,
    eligible_subjects,
    extract_turns,
    fetch_records,
    load_guest_words,
    load_pool,
    load_titles,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "stage2_pilot2" / "barlock"
PILOT = ROOT / "results" / "stage2_pilot"
CACHE_DIR = ROOT / "data" / "stage2_cache"          # gitignored
RECORDS = CACHE_DIR / "barlock_records.json"

SAMPLE_SEED = 73
SAMPLE_N = 60
FLOOR = 3


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval — behaves at the small n this sample has."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def sample_rows() -> list[dict]:
    """The seeded candidate sample: eligible pool minus the dev subjects."""
    pool = load_pool()
    elig = eligible_subjects(pool)
    dev_ids = {s["canonical_id"] for s in
               json.loads((PILOT / "dev_subjects.json").read_text())["subjects"]}
    cand = sorted((r for r in elig if r["canonical_id"] not in dev_ids),
                  key=lambda r: r["canonical_id"])
    rng = random.Random(SAMPLE_SEED)
    idx = list(range(len(cand)))
    rng.shuffle(idx)
    return [cand[i] for i in idx[:SAMPLE_N]]


def wanted_transcripts(rows: list[dict]) -> dict[str, dict]:
    """{canonical_id: split} for the sample, plus the test transcript ids."""
    gw = load_guest_words(rows)
    splits: dict[str, dict] = {}
    for row in rows:
        cid = row["canonical_id"]
        try:
            titles = load_titles([e["transcript_id"] for e in row["transcripts"]])
            splits[cid] = chronological_split(row, gw.get(cid, {}), titles)
        except ValueError as exc:               # no grounding / no substantive
            splits[cid] = {"error": str(exc)}
    return splits


def fetch() -> int:
    """One streaming pass: the sample's test transcripts + item 1's contexts."""
    t0 = time.time()
    rows = sample_rows()
    splits = wanted_transcripts(rows)
    (OUT / "eligibility_splits.json").write_text(json.dumps(
        {cid: (s if "error" in s else
               {"test": s["test"], "n_grounding": len(s["grounding"])})
         for cid, s in splits.items()}, indent=1))

    wanted = {s["test"]["transcript_id"] for s in splits.values()
              if "error" not in s}
    fuzzy_path = OUT / "fuzzy_host_sample.json"
    if fuzzy_path.exists():
        wanted |= {r["transcript_id"]
                   for r in json.loads(fuzzy_path.read_text())["sample"]}
    print(f"streaming {RAW_JSON} once for {len(wanted)} transcripts...")
    recs = fetch_records(sorted(wanted), RAW_JSON)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RECORDS.write_text(json.dumps(recs))
    print(f"  fetched {len(recs)} in {time.time() - t0:.1f}s -> {RECORDS}")
    return 0


def dev_counts() -> list[dict]:
    out = []
    dev = json.loads((PILOT / "dev_subjects.json").read_text())["subjects"]
    for s in dev:
        cid = s["canonical_id"]
        path = PILOT / "subjects" / cid / "qa_items.jsonl"
        n = 0
        if path.exists():
            n = sum(1 for line in path.read_text().splitlines() if line.strip())
        split = json.loads((PILOT / "subjects" / cid / "split.json").read_text())
        out.append({
            "canonical_id": cid,
            "canonical_name": s["canonical_name"],
            "n_items": n,
            "test_program": split["test"]["program"],
            "test_transcript": split["test"]["transcript_id"],
            "passes_floor_3": n >= FLOOR,
        })
    return out


def measure() -> int:
    t0 = time.time()
    rows = sample_rows()
    by_id = {r["canonical_id"]: r for r in rows}
    splits = wanted_transcripts(rows)
    recs = json.loads(RECORDS.read_text())

    per_subject = []
    for cid in sorted(by_id):
        row, split = by_id[cid], splits[cid]
        if "error" in split:
            per_subject.append({"canonical_id": cid,
                                "canonical_name": row["canonical_name"],
                                "n_items": 0, "status": "no_split",
                                "detail": split["error"]})
            continue
        tid = split["test"]["transcript_id"]
        rec = recs.get(tid)
        if rec is None:
            per_subject.append({"canonical_id": cid,
                                "canonical_name": row["canonical_name"],
                                "n_items": 0, "status": "record_missing"})
            continue
        turns = extract_turns(rec, row)
        items, drops = extract_qa_verbose(turns, cid, tid)
        stats: dict[str, int] = {}
        for d in drops:
            stats[d["reason"]] = stats.get(d["reason"], 0) + 1
        roles = {}
        for t in turns:
            roles[t["role"]] = roles.get(t["role"], 0) + 1
        per_subject.append({
            "canonical_id": cid,
            "canonical_name": row["canonical_name"],
            "wiki_status": row.get("wiki_status", ""),
            "test_transcript": tid,
            "test_program": split["test"]["program"],
            "test_date": split["test"]["date"],
            "n_turns": len(turns),
            "role_counts": roles,
            "n_items": len(items),
            "drop_stats": stats,
            "status": "ok",
        })

    # SPEC 8.7's second clause: "prefer one-on-one interview programmes".
    # Proxy, measured rather than asserted: a test transcript whose turns are
    # only the guest and one host role (no "other" speakers) is a two-person
    # interview; anything with "other" turns is a panel, roundtable or package.
    for p in per_subject:
        rc = p.get("role_counts") or {}
        p["one_on_one"] = (rc.get("other", 0) == 0 and rc.get("host", 0) > 0
                           and rc.get("guest", 0) > 0)
    oo = [p for p in per_subject if p.get("one_on_one")]
    non_oo = [p for p in per_subject if not p.get("one_on_one")]
    shape = {
        "one_on_one": {
            "n": len(oo),
            "mean_items": round(sum(p["n_items"] for p in oo) / len(oo), 2) if oo else 0,
            "pass_floor_3": sum(1 for p in oo if p["n_items"] >= FLOOR),
            "pass_rate": round(sum(1 for p in oo if p["n_items"] >= FLOOR) / len(oo), 4) if oo else 0,
        },
        "multi_speaker": {
            "n": len(non_oo),
            "mean_items": round(sum(p["n_items"] for p in non_oo) / len(non_oo), 2) if non_oo else 0,
            "pass_floor_3": sum(1 for p in non_oo if p["n_items"] >= FLOOR),
            "pass_rate": round(sum(1 for p in non_oo if p["n_items"] >= FLOOR) / len(non_oo), 4) if non_oo else 0,
        },
    }

    n = len(per_subject)
    counts = {}
    for p in per_subject:
        counts[p["n_items"]] = counts.get(p["n_items"], 0) + 1
    survival = {}
    for floor in (1, 2, 3, 4, 5, 6, 8, 10):
        k = sum(1 for p in per_subject if p["n_items"] >= floor)
        lo, hi = wilson(k, n)
        survival[f">={floor}"] = {
            "n_pass": k, "n": n, "rate": round(k / n, 4),
            "wilson95": [round(lo, 4), round(hi, 4)],
            "projected_of_578": round(578 * k / n, 1),
            "projected_of_578_wilson95": [round(578 * lo, 1), round(578 * hi, 1)],
        }

    payload = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": SAMPLE_SEED,
        "rule": ("Eligible pool (qualifies AND clean AND NOT ambiguous_identity, "
                 "578 rows) minus the 6 dev subjects, sorted by canonical_id, "
                 "shuffled with random.Random(73), first 60 taken. Each is split "
                 "by D2, its test transcript's turns extracted by D3/D3.1-r2/D3.2 "
                 "and its Q-A items by D4 — the same code the pilot ran."),
        "floor_under_review": FLOOR,
        "n_sampled": n,
        "item_count_histogram": dict(sorted(counts.items())),
        "programme_shape": shape,
        "survival_by_floor": survival,
        "dev_subjects": dev_counts(),
        "per_subject": per_subject,
        "runtime_secs": round(time.time() - t0, 1),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "eligibility_floor.json").write_text(json.dumps(payload, indent=1))
    slim = {k: v for k, v in payload.items() if k != "per_subject"}
    print(json.dumps(slim, indent=1))
    return 0


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "measure"
    raise SystemExit(fetch() if what == "fetch" else measure())
