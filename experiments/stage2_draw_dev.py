"""Draw the frozen Stage 2 dev subjects and build their splits (SPEC D1/D2/D3).

Run:    uv run python experiments/stage2_draw_dev.py
Redraw: uv run python experiments/stage2_draw_dev.py --force         (owner call only)
Turns:  uv run python experiments/stage2_draw_dev.py --regen-turns
Extend: uv run python experiments/stage2_draw_dev.py --extend        (owner call only)

--regen-turns is the safe mode for a change to the turn-extraction rules (D3,
D3.1): it reads the committed draw and the committed splits, re-extracts the
turn files from the corpus, and never touches the subject ids. Use it whenever
role assignment changes. It rewrites split.json too, because the guest word
counts in it come from the extracted turns, and prints whether that file
actually changed.

--extend is the safe mode for adding a subject after a retirement (SPEC D1,
BURNED_FOR_QA below): it re-derives the draw from the same seed with the raised
quota and refuses to write unless every committed subject survives at its
original shuffle position. It cannot drop or reorder a subject.

What it writes, all under results/stage2_pilot/:

    dev_subjects.json                       the draw: seed, rule, subjects
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

import json
import sys
import time
from datetime import date
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
    load_dev_subjects,
    load_guest_words,
    load_pool,
    load_split,
    load_titles,
    subject_dir,
    word_count,
    write_json,
    write_jsonl,
)

# Dev subjects dropped from the study entirely; see SPEC D1. Empty so far.
BURNED: tuple[str, ...] = ()

# Dev subjects retired for one purpose but still carried, with the reason.
# Each one raises its stratum's quota by one, so the next same-stratum id in
# the shuffled order joins the study alongside it.
BURNED_FOR_QA: dict[str, str] = {
    "C00292": ("Yields no Q-A items: DIPLOMATIC LICENSE is a roundtable, and "
               "every host turn before one of its guest turns is a statement, "
               "so D4's cue filter rejects all of them. Owner decision "
               "2026-07-26: the cue filter stays, the subject stays for "
               "classifier sampling and renderer exercise, and a sixth "
               "subject is added."),
}


def guard(force: bool, pilot_dir=PILOT_DIR) -> None:
    out = Path(pilot_dir) / "dev_subjects.json"
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


def check_extension(old: dict, new: dict) -> list[str]:
    """The extended draw must contain the committed one, unchanged."""
    old_by = {s["canonical_id"]: s for s in old["subjects"]}
    new_by = {s["canonical_id"]: s for s in new["subjects"]}
    missing = sorted(set(old_by) - set(new_by))
    if missing:
        raise SystemExit(f"[fatal] extending would drop committed dev "
                         f"subjects: {missing}. That is a re-draw, not an "
                         "extension — stop.")
    for cid, was in old_by.items():
        now = new_by[cid]
        if now["shuffle_pos"] != was["shuffle_pos"]:
            raise SystemExit(f"[fatal] {cid} moved from shuffle position "
                             f"{was['shuffle_pos']} to {now['shuffle_pos']}")
    # Subjects are listed in shuffled order, so an added subject slots in at
    # its own position rather than at the end. What must hold is that the
    # committed subjects keep their relative order.
    order_old = [s["canonical_id"] for s in old["subjects"]]
    kept = [s["canonical_id"] for s in new["subjects"] if s["canonical_id"] in old_by]
    if kept != order_old:
        raise SystemExit("[fatal] the committed subjects changed relative order")
    added = [s["canonical_id"] for s in new["subjects"] if s["canonical_id"]
             not in old_by]
    if not added:
        raise SystemExit("[refused] nothing to add — the draw already matches "
                         "BURNED_FOR_QA. Use --regen-turns to rebuild turns.")
    print(f"extending the committed draw: {len(old_by)} -> "
          f"{len(new_by)} subjects, adding {added}")
    return added


def split_identity(split: dict) -> tuple:
    """The part of a split that --regen-turns must never move.

    Guest word counts are derived from the turns and may legitimately shift
    when role assignment changes. Which clusters and which transcripts are on
    which side of the split may not.
    """
    def triples(entries):
        return tuple((e["cluster_id"], e["transcript_id"], e["date"])
                     for e in entries)
    return (triples(split["grounding"]),
            triples([split["test"]]),
            triples(split["excluded_same_date"]))


def build_subject(row: dict, split: dict, records: dict) -> dict:
    """Everything one subject contributes, computed in memory. Writes nothing."""
    cid = row["canonical_id"]
    # The records are authoritative for title/program/word counts; the scan
    # cache only had to be good enough to pick cluster representatives. Every
    # entry in the split -- including the excluded ones -- is refreshed here,
    # which is why the excluded transcripts are fetched too.
    warnings = []
    for entry in [*split["grounding"], split["test"], *split["excluded_same_date"]]:
        rec = records.get(entry["transcript_id"])
        if rec is None:
            raise SystemExit(f"[fatal] {cid}: {entry['transcript_id']} was not "
                             "fetched, so its split entry cannot be refreshed "
                             "from the corpus")
        entry["title"] = rec.get("title", "")
        entry["program"] = rec.get("program", entry["program"])
        cached = entry["guest_words"]
        actual = sum(word_count(t["text"]) for t in extract_turns(rec, row)
                     if t["role"] == "guest")
        entry["guest_words"] = actual
        if cached and abs(actual - cached) > 0.1 * cached:
            warnings.append((entry["transcript_id"], actual, cached))

    test_tid = split["test"]["transcript_id"]
    ground_tids = [e["transcript_id"] for e in split["grounding"]]
    if test_tid in ground_tids:
        raise SystemExit(f"[fatal] {cid}: the test transcript is also in "
                         "grounding")
    if split["test"]["date"] <= max(e["date"] for e in split["grounding"]):
        raise SystemExit(f"[fatal] {cid}: the test cluster is not strictly "
                         "later than every grounding cluster")
    for e in split["grounding"]:
        if max(e.get("member_dates") or [e["date"]]) >= split["test"]["date"]:
            raise SystemExit(f"[fatal] {cid}: grounding cluster "
                             f"{e['cluster_id']} has a member transcript dated "
                             "on or after the test date (D2 leak guard)")

    ground_turns = [t for tid in ground_tids
                    for t in extract_turns(records[tid], row)]
    test_turns = extract_turns(records[test_tid], row)
    if any(t["transcript_id"] == test_tid for t in ground_turns):
        raise SystemExit(f"[fatal] {cid}: test text leaked into grounding turns")

    return {
        "canonical_id": cid,
        "row": row,
        "split": split,
        "ground_turns": ground_turns,
        "test_turns": test_turns,
        "warnings": warnings,
        "files": {
            "split.json": json.dumps(split, indent=1, ensure_ascii=False) + "\n",
            "grounding_turns.jsonl": jsonl_text(ground_turns),
            "test_turns.jsonl": jsonl_text(test_turns),
        },
    }


def jsonl_text(rows) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def on_disk(cid: str, name: str) -> str | None:
    path = subject_dir(cid) / name
    return path.read_text(encoding="utf-8") if path.exists() else None


def main(argv: list[str]) -> int:
    args = argv[1:]
    force = "--force" in args
    regen = "--regen-turns" in args
    extend = "--extend" in args
    modes = [a for a in ("--force", "--regen-turns", "--extend") if a in args]
    unknown = [a for a in args if a not in
               ("--force", "--regen-turns", "--extend")]
    if unknown:
        raise SystemExit(f"unknown argument(s): {unknown}. Only --force, "
                         "--regen-turns and --extend are accepted.")
    if len(modes) > 1:
        raise SystemExit(f"{modes} are mutually exclusive: pick one.")
    if not (regen or extend):
        guard(force)

    t0 = time.time()
    for path in (POOL_CSV, RAW_JSON, SCAN_CACHE):
        if not Path(path).exists():
            raise SystemExit(f"[fatal] missing input: {path}")

    pool = load_pool(POOL_CSV)
    by_id = {r["canonical_id"]: r for r in pool}
    frozen: set[str] = set()

    if regen:
        # Read the frozen draw. Nothing is re-drawn. The splits are re-derived
        # from the same pool rather than read back, so a change to the D2 rules
        # is exercised too — but split_identity below then refuses to write if
        # any cluster or transcript actually moved sides.
        draw = load_dev_subjects()
        rows = [by_id[s["canonical_id"]] for s in draw["subjects"]]
        identity_before = {r["canonical_id"]:
                           split_identity(load_split(r["canonical_id"]))
                           for r in rows}
        print(f"regenerating turns for the {len(rows)} committed dev subjects "
              f"(seed {draw['seed']}, drawn {draw['drawn_at']}) — no re-draw")
    else:
        draw = draw_dev_subjects(pool, burned=BURNED,
                                 burned_for_qa=BURNED_FOR_QA)
        identity_before = {}
        if extend:
            committed = load_dev_subjects()
            added = check_extension(committed, draw)
            frozen = {s["canonical_id"] for s in committed["subjects"]}
            draw["drawn_at"] = committed["drawn_at"]     # the draw date stands
            draw["extended_at"] = date.today().isoformat()
        rows = [by_id[s["canonical_id"]] for s in draw["subjects"]]
        if not extend:
            print(f"pool: {len(pool)} rows, {draw['n_eligible']} eligible; "
                  f"drew {len(rows)} dev subjects with seed {draw['seed']}")

    # Cluster representatives need per-transcript guest word counts. They are
    # already in the v2 scan cache: one pickle load, not a scan.
    guest_words = load_guest_words(rows, SCAN_CACHE)
    all_tids = [e["transcript_id"] for r in rows for e in r["transcripts"]]
    titles = load_titles(all_tids, SCAN_CACHE)
    splits = {r["canonical_id"]:
              chronological_split(r, guest_words[r["canonical_id"]], titles)
              for r in rows}

    wanted = set()
    for split in splits.values():
        for entry in [*split["grounding"], split["test"],
                      *split["excluded_same_date"]]:
            wanted.add(entry["transcript_id"])
    print(f"fetching {len(wanted)} transcripts from {RAW_JSON} (one pass)...")
    t1 = time.time()
    records = fetch_records(sorted(wanted), RAW_JSON)
    print(f"  fetched {len(records)} records in {time.time() - t1:.1f}s")

    # ---- build everything in memory, verify, and only then write -----------
    built = [build_subject(row, splits[row["canonical_id"]], records)
             for row in rows]

    for b in built:
        for tid, actual, cached in b["warnings"]:
            source = "the committed split" if regen else "the scan cache"
            print(f"  [warn] {b['canonical_id']} {tid}: guest words {actual} "
                  f"extracted vs {cached} in {source}")

    if regen:
        moved = [b["canonical_id"] for b in built
                 if split_identity(b["split"]) != identity_before[b["canonical_id"]]]
        if moved:
            raise SystemExit(
                f"[refused] --regen-turns would move the split itself for "
                f"{moved}. Turn rules may change guest word counts; they may "
                "not change which clusters or transcripts are on which side. "
                "Nothing was written.")
        changed = [(b["canonical_id"], name)
                   for b in built for name, text in b["files"].items()
                   if on_disk(b["canonical_id"], name) != text]
        if not changed:
            print("  no file would change; nothing to rewrite")
        else:
            for cid, name in changed:
                print(f"  [rewrite] {cid}/{name}")

    if extend:
        stale = [(b["canonical_id"], name)
                 for b in built if b["canonical_id"] in frozen
                 for name, text in b["files"].items()
                 if on_disk(b["canonical_id"], name) not in (None, text)]
        if stale:
            lines = "\n".join(f"    {cid}/{name}" for cid, name in stale)
            raise SystemExit(
                "[refused] --extend would rewrite files belonging to the "
                f"frozen subjects:\n{lines}\n"
                "Extending adds a subject; it must never touch the ones "
                "already committed. The turn rules must have changed since "
                "they were built — run --regen-turns first, commit that, then "
                "extend. Nothing was written.")

    for b in built:
        d = subject_dir(b["canonical_id"])
        for name, text in b["files"].items():
            path = d / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    summary = []
    for b in built:
        split, row = b["split"], b["row"]
        gw = sum(word_count(t["text"]) for t in b["ground_turns"]
                 if t["role"] == "guest")
        tw = sum(word_count(t["text"]) for t in b["test_turns"]
                 if t["role"] == "guest")
        summary.append({
            "canonical_id": b["canonical_id"],
            "name": row["canonical_name"],
            "wiki_status": row["wiki_status"],
            "n_grounding": len(split["grounding"]),
            "grounding_words": gw,
            "test_date": split["test"]["date"],
            "test_words": tw,
            "excluded": len(split["excluded_same_date"]),
            "n_guest_turns_test": sum(1 for t in b["test_turns"]
                                      if t["role"] == "guest"),
            "n_host_turns_test": sum(1 for t in b["test_turns"]
                                     if t["role"] == "host"),
            "n_host_turns_grounding": sum(1 for t in b["ground_turns"]
                                          if t["role"] == "host"),
        })

    runtime = round(time.time() - t0, 1)
    if not regen:
        draw["runtime_secs"] = runtime
        draw["cost_usd"] = 0.0      # CPU only: no API calls, no GPU
        draw["n_transcripts_fetched"] = len(records)
        write_json(Path(PILOT_DIR) / "dev_subjects.json", draw)

    hdr = (f"{'subject':<28}{'wiki':<16}{'grnd':>5}{'grnd words':>12}"
           f"{'grnd host':>11}{'test date':>13}{'test words':>12}"
           f"{'test host':>11}{'excl':>6}")
    print()
    print(hdr)
    print("-" * len(hdr))
    qa_burned = {s["canonical_id"] for s in draw["subjects"]
                 if s.get("burned_for_qa")}
    for s in summary:
        mark = " *" if s["canonical_id"] in qa_burned else ""
        label = f"{s['canonical_id']} {s['name']}{mark}"
        print(f"{label:<28}{s['wiki_status']:<16}{s['n_grounding']:>5}"
              f"{s['grounding_words']:>12,}{s['n_host_turns_grounding']:>11}"
              f"{s['test_date']:>13}{s['test_words']:>12,}"
              f"{s['n_host_turns_test']:>11}{s['excluded']:>6}")
    print("-" * len(hdr))
    print("grounding words = guest-role words across the grounding transcripts; "
          "grnd host / test host = host-role turns on each side; "
          "test words = guest-role words in the test transcript.")
    if qa_burned:
        print(f"* retired for Q-A (still a dev subject): {sorted(qa_burned)}")
    print(f"written under {PILOT_DIR} in {runtime}s (0 API calls, $0.00)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
