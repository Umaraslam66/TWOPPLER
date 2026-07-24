"""MediaSum guest-transcript extractor — Stage 2 corpus-quality recon (DOPPLER).

Reusable helper. Two jobs:

  1. sample_pool()  — build the structurally-qualifying guest pool and draw a
     reproducible stratified sample (seed 42), exactly per the audit spec.
  2. dump_guests()  — stream the 4.45 GB news_dialogue.json ONCE and write every
     sampled guest's transcripts (full text, speaker-labeled turns) to per-guest
     files under data/mediasum_index/quality_sample/ for human reading.

Sampling rule (frozen by the audit spec):
  Pool = guests where
    (a) >= 3 transcripts each individually SUBSTANTIVE
        (>= 300 guest words AND >= 5 guest turns), counted from
        guest_interviews.csv;
    (b) normalized name has >= 2 whitespace tokens;
    (c) NOT in the top 500 by total_guest_words (skips the celebrity/staff head).
  Stratify: 10 guests with 3-5 qualifying transcripts, 10 with 6-15 qualifying.
  Random within strata, seed 42.

Reuses classify_speaker / stream_records / RAW_JSON from mediasum_index.py.
No paid/LLM API, CPU only.

Run:  uv run python experiments/mediasum_extract.py
"""
import csv
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mediasum_index import (  # noqa: E402
    classify_speaker, stream_records, RAW_JSON, OUT_DIR,
    INDEX_CSV, INTERVIEWS_CSV,
)

SAMPLE_DIR = os.path.join(OUT_DIR, "quality_sample")

SUBST_MIN_WORDS = 300
SUBST_MIN_TURNS = 5
TOP_N_EXCLUDE = 500
STRATUM_A = (3, 5)     # qualifying transcripts, inclusive
STRATUM_B = (6, 15)    # qualifying transcripts, inclusive
N_PER_STRATUM = 10
SEED = 42

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name):
    return _SLUG_RE.sub("_", name.lower()).strip("_")


def load_index_words():
    """normalized_name -> total_guest_words (int)."""
    words = {}
    with open(INDEX_CSV, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            words[row["normalized_name"]] = int(row["total_guest_words"])
    return words


def load_interviews():
    """normalized_name -> list of dicts (one per transcript)."""
    guests = {}
    with open(INTERVIEWS_CSV, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            name = row["normalized_name"]
            guests.setdefault(name, []).append({
                "tid": row["transcript_id"],
                "date": row["date"],
                "program": row["program"],
                "title": row["title"],
                "guest_words": int(row["guest_words"]),
                "guest_turns": int(row["guest_turns"]),
                "total_turns": int(row["total_turns_in_transcript"]),
            })
    return guests


def sample_pool():
    """Return (sampled, report) where report holds the cascade counts."""
    words = load_index_words()
    guests = load_interviews()

    n_total_index = len(words)
    n_in_interviews = len(guests)

    # top-500 by total_guest_words (across the full index)
    top500 = set(sorted(words, key=lambda n: -words.get(n, 0))[:TOP_N_EXCLUDE])

    # (a) >= 3 substantive transcripts
    qual = {}   # name -> list of qualifying transcript dicts
    for name, txs in guests.items():
        q = [t for t in txs
             if t["guest_words"] >= SUBST_MIN_WORDS
             and t["guest_turns"] >= SUBST_MIN_TURNS]
        if len(q) >= 3:
            qual[name] = q
    after_a = len(qual)

    # (b) name has >= 2 tokens
    after_b_names = [n for n in qual if len(n.split()) >= 2]
    after_b = len(after_b_names)

    # (c) not in top 500 by total_guest_words
    pool_names = [n for n in after_b_names if n not in top500]
    after_c = len(pool_names)

    # strata by qualifying-transcript count
    stratA, stratB, stratC_over15 = [], [], []
    for n in pool_names:
        k = len(qual[n])
        if STRATUM_A[0] <= k <= STRATUM_A[1]:
            stratA.append(n)
        elif STRATUM_B[0] <= k <= STRATUM_B[1]:
            stratB.append(n)
        elif k > STRATUM_B[1]:
            stratC_over15.append(n)

    rng = random.Random(SEED)
    pickA = sorted(rng.sample(sorted(stratA), min(N_PER_STRATUM, len(stratA))))
    rng2 = random.Random(SEED + 1)
    pickB = sorted(rng2.sample(sorted(stratB), min(N_PER_STRATUM, len(stratB))))

    sampled = []
    for n in pickA:
        sampled.append((n, "A_3-5", qual[n]))
    for n in pickB:
        sampled.append((n, "B_6-15", qual[n]))

    report = {
        "n_total_index": n_total_index,
        "n_in_interviews": n_in_interviews,
        "after_a_3subst": after_a,
        "after_b_2tokens": after_b,
        "after_c_not_top500": after_c,
        "strat_A_3to5": len(stratA),
        "strat_B_6to15": len(stratB),
        "strat_over15": len(stratC_over15),
        "picked_A": pickA,
        "picked_B": pickB,
        "top500_min_words": min(words[n] for n in top500),
    }
    return sampled, report, qual


def _select_three(txs):
    """Earliest / middle / latest by date (empty dates sorted last)."""
    ordered = sorted(txs, key=lambda t: (t["date"] == "", t["date"], t["tid"]))
    if len(ordered) <= 3:
        return ordered
    return [ordered[0], ordered[len(ordered) // 2], ordered[-1]]


def dump_guests(sampled):
    """Stream the raw JSON once, dump per-guest transcript files.

    Returns manifest dict {guest: {...}} written to disk too.
    """
    os.makedirs(SAMPLE_DIR, exist_ok=True)

    # map every needed transcript id -> list of (guest_name) that need it
    tid_to_guests = {}
    guest_meta = {}
    for name, stratum, qtxs in sampled:
        allrows = None  # we dump ALL of a guest's qualifying transcripts? no:
        # dump the FULL set the guest appears in that are qualifying + the 3
        # chosen for reading. Keep all qualifying so spot-checks are possible.
        chosen = _select_three(qtxs)
        chosen_tids = {t["tid"] for t in chosen}
        guest_meta[name] = {
            "slug": slugify(name),
            "stratum": stratum,
            "n_qualifying": len(qtxs),
            "qualifying": qtxs,
            "chosen_for_reading": [t["tid"] for t in chosen],
        }
        for t in qtxs:
            tid_to_guests.setdefault(t["tid"], []).append(name)

    needed = set(tid_to_guests)
    print(f"Need {len(needed)} transcripts across {len(sampled)} guests. "
          "Streaming raw JSON ...")

    # collect the raw records we need
    records = {}
    t0 = time.time()
    n_seen = 0
    for rec in stream_records(RAW_JSON):
        n_seen += 1
        if n_seen % 100000 == 0:
            print(f"  ...scanned {n_seen} ({time.time()-t0:.0f}s), "
                  f"found {len(records)}/{len(needed)}")
        tid = rec.get("id")
        if tid in needed:
            records[tid] = rec
            if len(records) == len(needed):
                print(f"  all {len(needed)} found after {n_seen} records "
                      f"({time.time()-t0:.0f}s)")
                break
    print(f"Collected {len(records)}/{len(needed)} transcripts "
          f"({time.time()-t0:.0f}s).")

    # write per-guest dirs
    for name, stratum, qtxs in sampled:
        meta = guest_meta[name]
        gdir = os.path.join(SAMPLE_DIR, meta["slug"])
        os.makedirs(gdir, exist_ok=True)
        # which raw speaker labels map to this guest name?
        for idx, t in enumerate(sorted(qtxs, key=lambda x: (x["date"] == "",
                                                            x["date"], x["tid"]))):
            rec = records.get(t["tid"])
            if rec is None:
                continue
            _write_transcript_file(gdir, idx, name, t, rec)
        with open(os.path.join(gdir, "_manifest.json"), "w") as f:
            json.dump(meta, f, indent=2)

    # top-level manifest
    top = {name: guest_meta[name] for name, _, _ in sampled}
    with open(os.path.join(SAMPLE_DIR, "_sample_manifest.json"), "w") as f:
        json.dump(top, f, indent=2)
    return guest_meta


def _write_transcript_file(gdir, idx, guest_name, tmeta, rec):
    utt = rec.get("utt") or []
    spk = rec.get("speaker") or []
    m = min(len(utt), len(spk))
    date = tmeta["date"] or "no-date"
    fname = f"{idx:02d}_{date}_{tmeta['tid']}.txt"
    path = os.path.join(gdir, fname)

    # tag which raw labels normalize to this guest
    guest_raw_labels = set()
    for raw in spk[:m]:
        kind, nm, _ = classify_speaker(raw)
        if kind == "guest" and nm == guest_name:
            guest_raw_labels.add(raw)

    lines = []
    A = lines.append
    A(f"# TRANSCRIPT {tmeta['tid']}")
    A(f"guest_of_interest : {guest_name}")
    A(f"raw_labels_mapping_to_guest : {sorted(guest_raw_labels)}")
    A(f"program : {rec.get('program','')}")
    A(f"date : {rec.get('date','')}")
    A(f"title : {rec.get('title','')}")
    A(f"guest_words : {tmeta['guest_words']}  guest_turns : {tmeta['guest_turns']}"
      f"  total_turns : {tmeta['total_turns']}")
    A(f"len(utt)={len(utt)} len(speaker)={len(spk)}"
      f"{'  <-- LENGTH MISMATCH' if len(utt) != len(spk) else ''}")
    A("")
    A("SUMMARY:")
    A(rec.get("summary", "") or "(none)")
    A("")
    A("=" * 78)
    A("TURNS (>>> marks a turn attributed to the guest of interest):")
    A("=" * 78)
    for i in range(m):
        raw = spk[i]
        text = utt[i] or ""
        mark = ">>>" if raw in guest_raw_labels else "   "
        A(f"{mark} [{i:03d}] {raw}:")
        A(f"        {text}")
    if len(utt) != len(spk):
        A("")
        A(f"!! length mismatch: {len(utt)} utterances vs {len(spk)} speakers; "
          "trailing entries not shown")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    sampled, report, qual = sample_pool()
    print("\n=== SAMPLING CASCADE ===")
    for k, v in report.items():
        print(f"  {k}: {v}")
    if report["after_c_not_top500"] < 40:
        print("\n!!! POOL AFTER FILTERS < 40 — STOPPING PER SPEC !!!")
        # still write the report file line for the caller
        with open(os.path.join(OUT_DIR, "_sample_report.json"), "w") as f:
            json.dump(report, f, indent=2)
        return
    dump_guests(sampled)
    with open(os.path.join(OUT_DIR, "_sample_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nDumped {len(sampled)} guests to {SAMPLE_DIR}")


if __name__ == "__main__":
    main()
