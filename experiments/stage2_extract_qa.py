"""Build the Stage 2 forced-choice items: Q-A extraction + distractors (D4/D5/D6).

Run:    uv run python experiments/stage2_extract_qa.py
Rebuild: uv run python experiments/stage2_extract_qa.py --force

What it writes, all under results/stage2_pilot/:

    distractor_bank.jsonl                       every donor Q-A pair (SPEC D6)
    distractor_bank_meta.json                   seed, donor ids, bank stats
    subjects/<canonical_id>/qa_items.jsonl      the subject's questions (D4)
    subjects/<canonical_id>/distractors.jsonl   4 options per item (D6)

It reads the frozen dev-subject draw and the frozen splits and never touches
them. It refuses to overwrite its own outputs without --force, for the same
reason the draw script does: the prompts, the scores and the contamination
meter downstream are all built against a particular option set, and silently
re-rolling it would invalidate them.

Nothing here calls a model. CPU only, no network. The one expensive step is a
single streaming pass over the 4.45 GB corpus for the ~200 donor transcripts.

A note on the yield: D4's filters are frozen and are NOT to be tuned to make
more items. How many items six real interviews produce is a finding about the
corpus, and the summary prints the drop reasons so that finding is legible.
"""

from __future__ import annotations

import hashlib
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

from doppler.distractors import (
    BANK_SEED,
    N_DONORS,
    bank_stats,
    build_bank,
    entity_density,
    density_bucket,
    sample_donor_ids,
    select_distractors,
)
from doppler.qa_extract import extract_qa_verbose
from doppler.stage2_data import (
    PILOT_DIR,
    POOL_CSV,
    RAW_JSON,
    SCAN_CACHE,
    fetch_records,
    load_dev_subjects,
    load_guest_words,
    load_pool,
    load_split,
    read_jsonl,
    subject_dir,
    write_json,
    write_jsonl,
)

BANK_PATH = Path(PILOT_DIR) / "distractor_bank.jsonl"
BANK_META_PATH = Path(PILOT_DIR) / "distractor_bank_meta.json"

#: The bank is a function of these three files, not of the SPEC alone. In
#: particular it calls stage2_data.extract_turns on every donor transcript, so
#: a change to D3/D3.1 role assignment silently changes which host turns exist
#: and therefore which Q-A pairs the bank holds. Recording the hashes means a
#: stale bank is detectable instead of invisible.
SOURCE_FILES = [
    "src/doppler/stage2_data.py",
    "src/doppler/qa_extract.py",
    "src/doppler/distractors.py",
]


def source_hashes() -> dict:
    from doppler.stage2_data import ROOT
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:16]
            for p in SOURCE_FILES}


def outputs(dev_ids: list[str]) -> list[Path]:
    paths = [BANK_PATH, BANK_META_PATH]
    for cid in dev_ids:
        paths.append(subject_dir(cid) / "qa_items.jsonl")
        paths.append(subject_dir(cid) / "distractors.jsonl")
    return paths


def guard(dev_ids: list[str], force: bool) -> None:
    existing = [p for p in outputs(dev_ids) if p.exists()]
    if existing and not force:
        listing = "\n  ".join(str(p) for p in existing)
        raise SystemExit(
            f"[refused] {len(existing)} output(s) already exist:\n  {listing}\n"
            "Item sets are frozen once anything has been rendered or scored "
            "against them. Pass --force only if you mean to discard them."
        )
    if existing:
        print(f"[force] discarding {len(existing)} existing output file(s)")


def extract_items(dev_ids: list[str]) -> tuple[dict, dict]:
    """D4 over each dev subject's held-out test interview."""
    items, drops = {}, {}
    for cid in dev_ids:
        split = load_split(cid)
        tid = split["test"]["transcript_id"]
        turns = read_jsonl(subject_dir(cid) / "test_turns.jsonl")
        got, dropped = extract_qa_verbose(turns, cid, tid)
        items[cid] = got
        drops[cid] = dropped
    return items, drops


def print_items_table(dev_ids, items, drops, draw) -> None:
    burned = {s["canonical_id"] for s in draw["subjects"]
              if s.get("burned_for_qa")}
    names = {s["canonical_id"]: s["canonical_name"] for s in draw["subjects"]}
    print("\nD4 — Q-A items from each held-out test interview")
    print(f"{'subject':<9} {'name':<18} {'items':>5} {'cand':>5}  drops")
    for cid in dev_ids:
        reasons = Counter(d["reason"] for d in drops[cid])
        detail = ", ".join(f"{k}={v}" for k, v in sorted(reasons.items())) or "-"
        tag = names[cid] + (" *" if cid in burned else "")
        print(f"{cid:<9} {tag:<18} {len(items[cid]):>5} "
              f"{len(items[cid]) + len(drops[cid]):>5}  {detail}")
    print(f"{'TOTAL':<9} {'':<18} {sum(len(v) for v in items.values()):>5}")
    if burned:
        print("  * retired for Q-A (SPEC D1); processed anyway, its yield is "
              "reported as found")


def main(argv: list[str]) -> int:
    args = argv[1:]
    force = "--force" in args
    unknown = [a for a in args if a != "--force"]
    if unknown:
        raise SystemExit(f"unknown argument(s): {unknown}. Only --force is "
                         "accepted.")

    t0 = time.time()
    for path in (POOL_CSV, RAW_JSON, SCAN_CACHE):
        if not Path(path).exists():
            raise SystemExit(f"[fatal] missing input: {path}")

    draw = load_dev_subjects()
    dev_ids = [s["canonical_id"] for s in draw["subjects"]]
    guard(dev_ids, force)
    print(f"dev subjects ({len(dev_ids)}): {', '.join(dev_ids)}")

    # ---- D4 -------------------------------------------------------------
    items, drops = extract_items(dev_ids)
    print_items_table(dev_ids, items, drops, draw)

    # ---- D6 bank --------------------------------------------------------
    pool = load_pool(POOL_CSV)
    by_id = {r["canonical_id"]: r for r in pool}
    donor_ids = sample_donor_ids(pool, dev_ids, seed=BANK_SEED,
                                 n_donors=N_DONORS)
    overlap = sorted(set(donor_ids) & set(dev_ids))
    if overlap:                                  # cannot happen; asserted anyway
        raise SystemExit(f"[fatal] dev subjects in the donor sample: {overlap}")
    print(f"\nD6 — distractor bank: {len(donor_ids)} donors sampled with seed "
          f"{BANK_SEED}, all {len(dev_ids)} dev subjects excluded")

    guest_words = load_guest_words([by_id[c] for c in donor_ids], SCAN_CACHE)
    notes: list[tuple[str, str]] = []
    per_donor: dict[str, int] = {}
    n_truncated = 0

    def on_donor(cid, tid, donor_items, note):
        nonlocal n_truncated
        per_donor[cid] = len(donor_items)
        n_truncated += sum(1 for it in donor_items if "truncated" in it["flags"])
        if note:
            notes.append((cid, note))

    t1 = time.time()
    print(f"  streaming {RAW_JSON} once for the donor transcripts...")
    bank = build_bank(pool, dev_ids, seed=BANK_SEED, n_donors=N_DONORS,
                      fetch_fn=lambda ids: fetch_records(ids, RAW_JSON),
                      guest_words=guest_words, on_donor=on_donor)
    fetch_secs = time.time() - t1
    stats = bank_stats(bank)
    print(f"  {stats['n_rows']} bank rows from "
          f"{stats['n_donor_subjects_with_items']}/{len(donor_ids)} donors "
          f"in {fetch_secs:.1f}s")
    print(f"  buckets: {stats['buckets']}   answer words: "
          f"min {stats['answer_words']['min']}, median "
          f"{stats['answer_words']['median']}, max {stats['answer_words']['max']}"
          f"   truncated: {n_truncated}")
    for cid, note in notes[:5]:
        print(f"  [skip] {cid}: {note}")
    if len(notes) > 5:
        print(f"  ... and {len(notes) - 5} more skipped donors")

    write_jsonl(BANK_PATH, bank)
    write_json(BANK_META_PATH, {
        "seed": BANK_SEED,
        "rule": ("random.Random(48).sample of 200 canonical_ids from the "
                 "lexicographically sorted eligible pool (qualifies AND clean "
                 "AND NOT ambiguous_identity), with every dev subject removed "
                 "first. Q-A items are extracted under SPEC D4 from each "
                 "donor's LATEST cluster representative transcript only."),
        "built_at": date.today().isoformat(),
        "n_donors": len(donor_ids),
        "dev_ids_excluded": dev_ids,
        "donor_ids": donor_ids,
        "items_per_donor": per_donor,
        "skipped": [{"canonical_id": c, "note": n} for c, n in notes],
        "n_truncated": n_truncated,
        "stats": stats,
        "source_sha256": source_hashes(),
        "runtime_secs": round(fetch_secs, 1),
        "cost_usd": 0.0,
    })

    # ---- D6 selection ---------------------------------------------------
    rungs: Counter = Counter()
    short: list[str] = []
    n_options = 0
    n_items = 0
    print("\nD6 — distractor selection")
    for cid in dev_ids:
        rows = []
        for item in items[cid]:
            sel = select_distractors(item, bank, n=3)
            rungs[sel["relax_rung"]] += 1
            n_options += len(sel["options"])
            n_items += 1
            if "insufficient_candidates" in sel["flags"]:
                short.append(sel["item_id"])
            rows.append(sel)
        write_jsonl(subject_dir(cid) / "qa_items.jsonl", items[cid])
        write_jsonl(subject_dir(cid) / "distractors.jsonl", rows)
        if rows:
            bucket = density_bucket(entity_density(items[cid][0]["answer"]))
            print(f"  {cid}: {len(rows)} item(s) written  "
                  f"(first item bucket {bucket})")
        else:
            print(f"  {cid}: 0 items — qa_items.jsonl and distractors.jsonl "
                  "written empty")

    print("\nrelaxation rungs (0 = the pre-registered +-20% / same-bucket "
          "control):")
    for k in range(4):
        label = ["0: +-20%, same bucket", "1: +-30%, same bucket",
                 "2: +-30%, adjacent bucket", "3: +-50%, adjacent bucket"][k]
        print(f"  rung {label:<30} {rungs.get(k, 0)}")
    print(f"mean options per item: "
          f"{(n_options / n_items) if n_items else 0:.2f}  "
          f"({n_items} items)")
    if short:
        print(f"[warn] {len(short)} item(s) could not reach 4 options even at "
              f"the last rung: {short}")

    print(f"\nbank -> {BANK_PATH}")
    print(f"done in {time.time() - t0:.1f}s   API calls: 0   cost: $0.00")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
