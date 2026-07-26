"""Match every dev subject to a same-domain imposter donor (SPEC D7, A1).

Run:    uv run python experiments/stage2_imposters.py
Redo:   uv run python experiments/stage2_imposters.py --force     (owner call only)

What it writes, all under results/stage2_pilot/:

    imposter_pairs.json          the D7 record: pairs, similarities, runners-up
    donor_texts/<cid>.txt        grounding-side guest text of every donor that
                                 won a pair or made a runner-up list
    donors/<cid>/split.json      the matched donors' D2 split, and
    donors/<cid>/grounding_turns.jsonl   their grounding turns, so the imposter
                                 arm can be rendered later without a second
                                 corpus pass (same schema as subjects/<cid>/)

Read-never-redo, same discipline as the dev draw: once imposter_pairs.json
exists the script refuses to run, because silently re-matching donors would
invalidate any imposter prompt already built against the old pairs. --force is
the deliberate override and prints what it discards.

The expensive step is one streaming pass over the 4.45 GB corpus for the 200
donors' grounding transcripts (~700 records). Its result is cached under
data/stage2_cache/ (gitignored), keyed by the donor sample AND by the bytes of
stage2_data.py, so a re-run costs seconds but a change to the turn-extraction
rules always re-reads the corpus. CPU only, no network, no model calls, $0.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path

from doppler.imposter2 import (
    DONOR_SEED,
    N_DONORS,
    WORD_FLOOR,
    collect_donor_texts,
    donor_dir,
    donor_sample,
    donor_text_path,
    grounding_text,
    match_donors,
    sample_sha256,
)
from doppler.stage2_data import (
    PILOT_DIR,
    RAW_JSON,
    extract_turns,
    fetch_records,
    load_dev_subjects,
    load_guest_words,
    load_pool,
    subject_dir,
    word_count,
    write_json,
    write_jsonl,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = PILOT_DIR / "imposter_pairs.json"
CACHE = ROOT / "data/stage2_cache/donor_grounding_v1.json"
STAGE2_DATA_PY = ROOT / "src/doppler/stage2_data.py"


# ---------------------------------------------------------------------------

def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cache_key(fingerprint: str) -> str:
    """Donor sample AND the extraction rules that produced the texts.

    Donor grounding text comes out of stage2_data.extract_turns, which T1 is
    still amending (D3.1-r2 label cleaning, guest containment matching). A
    cache keyed only on the donor ids would happily serve text built under the
    old rules against a subject side built under the new ones, and nothing
    downstream would notice. Keying on the module's bytes forces a re-pass
    whenever those rules move — 5 seconds, and it cannot go stale silently.
    """
    return hashlib.sha256(
        (fingerprint + ":" + sha256_file(STAGE2_DATA_PY)).encode()).hexdigest()


def load_cache(key: str):
    """The cached donor texts, but only for the same donors AND same rules."""
    if not CACHE.exists():
        return None
    doc = json.loads(CACHE.read_text(encoding="utf-8"))
    if doc.get("cache_key") != key:
        return None
    return doc["texts"]


def save_cache(key: str, texts: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({"cache_key": key, "texts": texts},
                                ensure_ascii=False), encoding="utf-8")


def cross_check_with_t2(pool, dev_ids, donor_ids) -> str:
    """The bank sample (T2) and the imposter donor pool (T3) must be one list.

    Both tasks derive it from the pool with random.Random(48) rather than one
    reading the other's output, so this is the only place the two derivations
    ever meet. T2's module may not exist yet; that is not an error.
    """
    try:
        from doppler.distractors import sample_donor_ids
    except Exception:
        return "T2's distractors module is not importable yet — not checked"
    theirs = sample_donor_ids(pool, dev_ids)
    if list(theirs) == list(donor_ids):
        return "identical to T2's sample_donor_ids (order and membership)"
    return ("MISMATCH with T2's sample_donor_ids: "
            f"{len(set(theirs) & set(donor_ids))}/{len(donor_ids)} shared ids")


def headline(row: dict) -> str:
    """One line a human can eyeball for topical match: role/affiliation."""
    affiliations = (row.get("affiliations") or "").split(" / ")
    first = affiliations[0].strip()
    if not first:
        first = (row.get("top_raw_label") or "").strip()
    return first[:58]


def top_programs(split: dict, k: int = 2) -> str:
    counts: dict[str, int] = {}
    for entry in split["grounding"]:
        counts[entry["program"]] = counts.get(entry["program"], 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
    return ", ".join(f"{p} x{n}" for p, n in ranked)


# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    force = "--force" in argv
    unknown = [a for a in argv if a != "--force"]
    if unknown:
        print(f"[fatal] unknown argument(s): {unknown}", file=sys.stderr)
        return 1
    if OUT.exists() and not force:
        print(f"[stop] {OUT} already exists.\n"
              "       Donor pairs are frozen once written — anything rendered\n"
              "       against them would silently change meaning. Re-run with\n"
              "       --force only on an owner call.", file=sys.stderr)
        return 1
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        print(f"[force] discarding the existing pairs: {old.get('pairs')}")

    t0 = time.time()
    pool = load_pool()
    by_id = {r["canonical_id"]: r for r in pool}
    dev_doc = load_dev_subjects()
    dev_ids = [s["canonical_id"] for s in dev_doc["subjects"]]
    print(f"dev subjects ({len(dev_ids)}): {', '.join(dev_ids)}")

    donor_ids = donor_sample(pool, dev_ids, seed=DONOR_SEED, n=N_DONORS)
    fingerprint = sample_sha256(donor_ids)
    print(f"donor sample: {len(donor_ids)} ids, seed {DONOR_SEED}, "
          f"sha256 {fingerprint[:16]}")
    print(f"cross-check:  {cross_check_with_t2(pool, dev_ids, donor_ids)}")

    # Subject side: the committed turn files, guest role only, grounding only.
    subject_texts = {cid: grounding_text(cid) for cid in dev_ids}
    # T1 is still amending turn extraction, so record exactly which turn files
    # this match was computed from. A refresh that changes any of these hashes
    # is a refresh that can change the pairs.
    turn_sha = {cid: sha256_file(subject_dir(cid) / "grounding_turns.jsonl")[:16]
                for cid in sorted(dev_ids)}

    # Donor side: one corpus pass, cached.
    guest_words = load_guest_words([by_id[c] for c in donor_ids])
    key = cache_key(fingerprint)
    cached = load_cache(key)
    if cached is not None:
        donor_texts = cached
        from doppler.imposter2 import donor_splits
        splits, skipped = donor_splits(donor_ids, pool, guest_words)
        print(f"donor texts:  {len(donor_texts)} from cache {CACHE}")
    else:
        print(f"donor texts:  streaming {RAW_JSON} ...")
        donor_texts, meta = collect_donor_texts(donor_ids, pool, RAW_JSON,
                                                guest_words)
        splits, skipped = meta["splits"], meta["skipped_no_grounding"]
        if meta["missing_transcripts"]:
            print(f"[fatal] transcripts not found: "
                  f"{meta['missing_transcripts'][:5]}", file=sys.stderr)
            return 1
        if meta["malformed"]:
            print(f"[warn] {len(meta['malformed'])} malformed (donor, "
                  f"transcript) pairs skipped: {list(meta['malformed'])[:3]}")
        print(f"              {meta['n_transcripts_read']} grounding "
              f"transcripts read in {time.time() - t0:.1f}s")
        save_cache(key, donor_texts)
    if skipped:
        print(f"              {len(skipped)} donors have no grounding side "
              "(single-cluster subjects), dropped")

    doc = match_donors(dev_doc["subjects"], pool, subject_texts, donor_texts,
                       generated_at=date.today().isoformat())
    doc["donor_sample"] = donor_ids
    doc["n_donors_no_grounding"] = len(skipped)
    doc["n_donors_below_floor"] = (len(donor_texts) - len(skipped)
                                   - doc["n_eligible_donors"])
    # Distinct transcripts behind the donor side. Derived from the splits, not
    # from the run, so a cached run records the same number as a cold one.
    doc["n_donor_grounding_transcripts"] = len(
        {e["transcript_id"] for sp in splits.values() for e in sp["grounding"]})
    # Provenance of the inputs, so a later refresh can prove what moved.
    doc["stage2_data_sha256"] = sha256_file(STAGE2_DATA_PY)[:16]
    doc["subject_turns_sha256"] = turn_sha
    doc["runtime_secs"] = round(time.time() - t0, 1)
    doc["cost_usd"] = 0.0
    write_json(OUT, doc)

    # The texts behind every recorded donor, so a reader can check the match
    # without the corpus. Winners and runners-up only — not all 200.
    for cid in doc["donors_recorded"]:
        path = donor_text_path(cid)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(donor_texts[cid].rstrip("\n") + "\n", encoding="utf-8")

    # The matched donors' grounding TURNS (host + guest, with dates and
    # programs), which is what the imposter arm actually renders from. Second
    # pass, ~30 transcripts.
    winners = sorted(set(doc["pairs"].values()))
    wanted = sorted({e["transcript_id"] for cid in winners
                     for e in splits[cid]["grounding"]})
    records = fetch_records(wanted, RAW_JSON)
    for cid in winners:
        turns = []
        for entry in splits[cid]["grounding"]:
            turns.extend(extract_turns(records[entry["transcript_id"]], by_id[cid]))
        out_dir = donor_dir(cid)
        split = dict(splits[cid])
        split["role"] = "imposter donor (SPEC D7); test cluster is NEVER used"
        write_json(out_dir / "split.json", split)
        n = write_jsonl(out_dir / "grounding_turns.jsonl", turns)
        guest = sum(word_count(t["text"]) for t in turns if t["role"] == "guest")
        assert guest == word_count(donor_texts[cid]), \
            f"{cid}: turn file and matched text disagree ({guest} vs matched)"
        assert all(t["transcript_id"] != splits[cid]["test"]["transcript_id"]
                   for t in turns), f"{cid}: test transcript leaked into grounding"
        print(f"  donors/{cid}: {n} turns, {guest} guest words")

    # ---- the table --------------------------------------------------------
    print(f"\n{len(dev_ids)} pairs — subject then donor, "
          f"floor {WORD_FLOOR} words, {doc['n_eligible_donors']} eligible "
          f"donors, max_df {doc['max_df']}, {doc['vocabulary_terms']:,} terms\n")
    for cid in sorted(dev_ids):
        srow = by_id[cid]
        did = doc["pairs"][cid]
        drow = by_id[did]
        burned = " [burned for Q-A]" if any(
            s.get("burned_for_qa") for s in dev_doc["subjects"]
            if s["canonical_id"] == cid) else ""
        print(f"{cid} {srow['canonical_name']:<22} "
              f"{doc['subject_words'][cid]:>6}w  {headline(srow)}{burned}")
        print(f"  -> {did} {drow['canonical_name']:<19} "
              f"{doc['donor_words'][did]:>6}w  {headline(drow)}")
        print(f"     cosine {doc['similarity'][cid]:.4f}   "
              f"{top_programs(splits[did])}")
        runners = ", ".join(f"{d} {by_id[d]['canonical_name']} {s:.3f}"
                            for d, s in doc["runner_up_top5"][cid])
        print(f"     runners-up: {runners}")
        blocked = doc["excluded_by_name"].get(cid, [])
        if blocked:
            print(f"     name-excluded: "
                  f"{', '.join(b['donor'] + ' (' + b['reason'] + ')' for b in blocked)}")
        print()

    mult = doc["donor_multiplicity"]
    print(f"donor multiplicity: {mult['distinct_donors']} distinct donors for "
          f"{mult['n_subjects']} subjects, at most "
          f"{mult['max_subjects_per_donor']} subjects on one donor")
    for donor in mult["shared_donors"]:
        print(f"  {donor} {by_id[donor]['canonical_name']} serves "
              f"{', '.join(mult['subjects_by_donor'][donor])}")

    print(f"wrote {OUT}")
    print(f"      {len(doc['donors_recorded'])} donor texts, "
          f"{len(winners)} donor turn sets")
    print(f"runtime {doc['runtime_secs']}s, 0 API calls, $0.00, CPU only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
