"""Draw the frozen Stage 2 dev subjects and build their splits (SPEC D1/D2/D3).

Run:    uv run python experiments/stage2_draw_dev.py
Redraw: uv run python experiments/stage2_draw_dev.py --force   (owner call only)

What it writes, all under results/stage2_pilot/:

    dev_subjects.json                       the draw: seed, rule, 5 subjects
    subjects/<canonical_id>/split.json      grounding clusters + test cluster
    subjects/<canonical_id>/grounding_turns.jsonl
    subjects/<canonical_id>/test_turns.jsonl

Read-never-redraw, same discipline as the Stage 1E confirm split
(experiments/confirm_run.py confirm_ids): once dev_subjects.json exists the
script refuses to run, because a silently re-drawn dev set would invalidate
every downstream artifact that was built against the old one. --force is the
deliberate override and prints what it is discarding.

CPU only, no network, no model calls. The one expensive step is a single
streaming pass over the 4.45 GB corpus to pull the ~27 split transcripts.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from doppler.stage2_data import (
    PILOT_DIR,
    POOL_CSV,
    RAW_JSON,
    SCAN_CACHE,
    chronological_split,
    draw_dev_subjects,
    extract_turns,
    fetch_records,
    load_guest_words,
    load_pool,
    load_titles,
    subject_dir,
    word_count,
    write_json,
    write_jsonl,
)

BURNED: tuple[str, ...] = ()   # dev subjects retired for cause; see SPEC D1


def guard(force: bool) -> None:
    out = Path(PILOT_DIR) / "dev_subjects.json"
    if out.exists() and not force:
        raise SystemExit(
            f"[refused] {out} already exists.\n"
            "The dev-subject draw is frozen — read it, never re-draw it. "
            "Every split, prompt and score downstream was built against these "
            "ids. Pass --force only on an explicit owner decision to discard "
            "them (and remember: a discarded subject stays burned, SPEC D1)."
        )
    if out.exists():
        print(f"[force] discarding the existing draw at {out}")


def main(argv: list[str]) -> int:
    force = "--force" in argv[1:]
    unknown = [a for a in argv[1:] if a != "--force"]
    if unknown:
        raise SystemExit(f"unknown argument(s): {unknown}. Only --force is accepted.")
    guard(force)

    t0 = time.time()
    for path in (POOL_CSV, RAW_JSON, SCAN_CACHE):
        if not Path(path).exists():
            raise SystemExit(f"[fatal] missing input: {path}")

    pool = load_pool(POOL_CSV)
    draw = draw_dev_subjects(pool, burned=BURNED)
    by_id = {r["canonical_id"]: r for r in pool}
    rows = [by_id[s["canonical_id"]] for s in draw["subjects"]]
    print(f"pool: {len(pool)} rows, {draw['n_eligible']} eligible; "
          f"drew {len(rows)} dev subjects with seed {draw['seed']}")

    # Cluster representatives need per-transcript guest word counts. They are
    # already in the v2 scan cache, so this costs one pickle load, not a scan.
    guest_words = load_guest_words(rows, SCAN_CACHE)
    all_tids = [e["transcript_id"] for r in rows for e in r["transcripts"]]
    titles = load_titles(all_tids, SCAN_CACHE)

    splits = {r["canonical_id"]: chronological_split(r, guest_words[r["canonical_id"]], titles)
              for r in rows}

    wanted = set()
    for split in splits.values():
        wanted.update(e["transcript_id"] for e in split["grounding"])
        wanted.add(split["test"]["transcript_id"])
    print(f"fetching {len(wanted)} transcripts from {RAW_JSON} (one pass)...")
    t1 = time.time()
    records = fetch_records(sorted(wanted), RAW_JSON)
    print(f"  fetched {len(records)} records in {time.time() - t1:.1f}s")

    summary = []
    for row in rows:
        cid = row["canonical_id"]
        split = splits[cid]
        # The records are authoritative for title/program/word counts; the scan
        # cache only had to be good enough to pick cluster representatives.
        for entry in [*split["grounding"], split["test"], *split["excluded_same_date"]]:
            rec = records.get(entry["transcript_id"])
            if rec is None:
                continue
            entry["title"] = rec.get("title", "")
            entry["program"] = rec.get("program", entry["program"])
            cached = entry["guest_words"]
            actual = sum(word_count(t["text"]) for t in extract_turns(rec, row)
                         if t["role"] == "guest")
            entry["guest_words"] = actual
            if cached and abs(actual - cached) > 0.1 * cached:
                print(f"  [warn] {cid} {entry['transcript_id']}: guest words "
                      f"{actual} extracted vs {cached} in the scan cache")

        test_tid = split["test"]["transcript_id"]
        ground_tids = [e["transcript_id"] for e in split["grounding"]]
        assert test_tid not in ground_tids, f"{cid}: test transcript in grounding"
        assert split["test"]["date"] > max(e["date"] for e in split["grounding"]), \
            f"{cid}: test cluster is not strictly later than every grounding cluster"

        ground_turns = [t for tid in ground_tids
                        for t in extract_turns(records[tid], row)]
        test_turns = extract_turns(records[test_tid], row)
        assert all(t["transcript_id"] != test_tid for t in ground_turns), \
            f"{cid}: test text leaked into grounding turns"

        d = subject_dir(cid)
        write_json(d / "split.json", split)
        write_jsonl(d / "grounding_turns.jsonl", ground_turns)
        write_jsonl(d / "test_turns.jsonl", test_turns)

        gw = sum(word_count(t["text"]) for t in ground_turns if t["role"] == "guest")
        tw = sum(word_count(t["text"]) for t in test_turns if t["role"] == "guest")
        summary.append({
            "canonical_id": cid,
            "name": row["canonical_name"],
            "wiki_status": row["wiki_status"],
            "n_grounding": len(split["grounding"]),
            "grounding_words": gw,
            "test_date": split["test"]["date"],
            "test_words": tw,
            "excluded": len(split["excluded_same_date"]),
            "n_guest_turns_test": sum(1 for t in test_turns if t["role"] == "guest"),
            "n_host_turns_test": sum(1 for t in test_turns if t["role"] == "host"),
        })

    draw["runtime_secs"] = round(time.time() - t0, 1)
    draw["cost_usd"] = 0.0          # CPU only: no API calls, no GPU
    draw["n_transcripts_fetched"] = len(records)
    write_json(Path(PILOT_DIR) / "dev_subjects.json", draw)

    hdr = (f"{'subject':<28}{'wiki':<16}{'grnd':>5}{'grnd words':>12}"
           f"{'test date':>13}{'test words':>12}{'excl':>6}")
    print()
    print(hdr)
    print("-" * len(hdr))
    for s in summary:
        label = f"{s['canonical_id']} {s['name']}"
        print(f"{label:<28}{s['wiki_status']:<16}{s['n_grounding']:>5}"
              f"{s['grounding_words']:>12,}{s['test_date']:>13}"
              f"{s['test_words']:>12,}{s['excluded']:>6}")
    print("-" * len(hdr))
    print(f"grounding words = guest-role words across the grounding transcripts; "
          f"test words = guest-role words in the test transcript.")
    print(f"written under {PILOT_DIR} in {draw['runtime_secs']}s "
          f"(0 API calls, $0.00)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
