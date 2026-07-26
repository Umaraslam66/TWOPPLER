"""Bar-lock item 1: measure the D3.2 fuzzy host threshold on a labelled sample.

Replays SPEC D3.2's program_host_match over every transcript in the cached
corpus scan (data/mediasum_index/_scan_cache_v2.pkl), records the raw difflib
ratio of every *fuzzy-arm* candidate (i.e. labels the literal/normalised arms
did NOT already catch), and draws a seeded random sample of fired transcripts
for hand labelling.

Nothing here changes the threshold. It produces the evidence the owner needs to
freeze one.

Usage:
    uv run python experiments/barlock_fuzzy_host.py scan     # stage 1: ratios
    uv run python experiments/barlock_fuzzy_host.py sample   # stage 2: sample
"""

from __future__ import annotations

import difflib
import json
import pickle
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doppler import stage2_data as S  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mediasum_index as M  # noqa: E402  (origin speaker-role classifier)

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "mediasum_index" / "_scan_cache_v2.pkl"
OUT = ROOT / "results" / "stage2_pilot2" / "barlock"

#: The lowest ratio worth recording. Below this nothing is a plausible match and
#: keeping it only inflates the file.
FLOOR = 0.45

#: Seed for the labelling sample. Fixed so the owner can redraw it.
SAMPLE_SEED = 71
#: Stratified quota per ratio band. A simple random 40 out of the 498 rows at
#: >= 0.55 would put ~24 of them in the 0.55-0.60 band and leave 3-4 above 0.70,
#: which cannot estimate precision at 0.70. Band precisions are combined back to
#: threshold precision with the band's true population weight (see report).
SAMPLE_BANDS = [(0.55, 0.60, 12), (0.60, 0.65, 10), (0.65, 0.70, 8),
                (0.70, 0.75, 6), (0.75, 1.01, 6)]


def candidate_ratio(raw: str, program: str) -> tuple[str, float, str] | None:
    """(arm, ratio, descriptor) for one label/programme pair, or None.

    arm is "literal"/"normalized" when D3.2's exact arms fire (ratio 1.0), or
    "fuzzy" for everything else — including sub-threshold cases, which the
    production predicate discards and this scan keeps.
    """
    descriptor = S._descriptor_part(raw)
    if not descriptor or not program:
        return None
    du, pu = descriptor.upper(), program.upper()
    if du == pu or pu in du:
        return ("literal", 1.0, descriptor)
    dn, pn = S._normalize_show(descriptor), S._normalize_show(program)
    if not dn or not pn:
        return None
    if dn == pn or pn in dn or dn in pn:
        return ("normalized", 1.0, descriptor)
    return ("fuzzy", difflib.SequenceMatcher(None, dn, pn).ratio(), descriptor)


def scan() -> dict:
    t0 = time.time()
    with CACHE.open("rb") as fh:
        cache = pickle.load(fh)
    tid_rawlabels = cache["tid_rawlabels"]
    tid_info = cache["tid_info"]

    n_tids = 0
    fuzzy_rows: list[dict] = []            # one row per (tid, distinct label)
    literal_tids: set[str] = set()
    literal_turns = 0
    label_cache: dict[tuple[str, str], tuple[str, float, str] | None] = {}

    for tid, labels in tid_rawlabels.items():
        info = tid_info.get(tid)
        if not info:
            continue
        program = info[0]
        n_tids += 1
        counts: dict[str, int] = {}
        for lab in labels:
            counts[lab] = counts.get(lab, 0) + 1
        for lab, n in counts.items():
            key = (lab, program)
            if key not in label_cache:
                label_cache[key] = candidate_ratio(lab, program)
            res = label_cache[key]
            if res is None:
                continue
            arm, ratio, descriptor = res
            if arm != "fuzzy":
                literal_tids.add(tid)
                literal_turns += n
                continue
            if ratio < FLOOR:
                continue
            fuzzy_rows.append({
                "transcript_id": tid,
                "program": program,
                "title": info[1],
                "n_utt": info[2],
                "raw_label": lab,
                "descriptor": descriptor,
                "n_turns": n,
                "ratio": round(ratio, 4),
                "norm_descriptor": S._normalize_show(descriptor),
                "norm_program": S._normalize_show(program),
                # Does the ORIGIN classifier already call this label staff? If
                # it does, the fuzzy arm changes nothing for that turn, and the
                # threshold only decides how many NEW turns it converts.
                "already_staff": M.classify_speaker(lab)[0] == "staff",
            })

    fuzzy_rows.sort(key=lambda r: (-r["ratio"], r["transcript_id"]))
    payload = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cache": str(CACHE.relative_to(ROOT)),
        "n_transcripts_scanned": n_tids,
        "record_floor_ratio": FLOOR,
        "literal_or_normalized": {
            "transcripts": len(literal_tids),
            "turns": literal_turns,
        },
        "fuzzy_candidates_at_or_above_floor": len(fuzzy_rows),
        "rows": fuzzy_rows,
        "scan_secs": round(time.time() - t0, 1),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "fuzzy_host_scan.json").write_text(json.dumps(payload, indent=1))
    return payload


def bands(rows: list[dict]) -> dict:
    """Turn/transcript counts per ratio band, for the threshold table."""
    edges = [(0.45, 0.50), (0.50, 0.55), (0.55, 0.60), (0.60, 0.65),
             (0.65, 0.70), (0.70, 0.75), (0.75, 0.80), (0.80, 1.01)]
    out = {}
    for lo, hi in edges:
        sel = [r for r in rows if lo <= r["ratio"] < hi]
        new = [r for r in sel if not r.get("already_staff")]
        out[f"{lo:.2f}-{hi:.2f}"] = {
            "label_rows": len(sel),
            "turns": sum(r["n_turns"] for r in sel),
            "transcripts": len({r["transcript_id"] for r in sel}),
            "label_rows_not_already_staff": len(new),
            "turns_not_already_staff": sum(r["n_turns"] for r in new),
            "transcripts_not_already_staff": len({r["transcript_id"] for r in new}),
        }
    return out


def sample() -> dict:
    payload = json.loads((OUT / "fuzzy_host_scan.json").read_text())
    rows = payload["rows"]
    # The labelling sample covers everything the LOWEST candidate threshold
    # (0.55) would admit; that is the set whose precision the owner must judge.
    rng = random.Random(SAMPLE_SEED)
    picked: list[dict] = []
    strata = {}
    for lo, hi, quota in SAMPLE_BANDS:
        band = [r for r in rows if lo <= r["ratio"] < hi]
        band.sort(key=lambda r: (r["transcript_id"], r["raw_label"]))
        idx = list(range(len(band)))
        rng.shuffle(idx)
        take = [band[i] for i in idx[:quota]]
        for r in take:
            r = dict(r)
            r["band"] = f"{lo:.2f}-{hi:.2f}"
            picked.append(r)
        strata[f"{lo:.2f}-{hi:.2f}"] = {"population": len(band),
                                        "sampled": len(take)}
    out = {
        "seed": SAMPLE_SEED,
        "rule": ("Fuzzy-arm label rows with ratio >= 0.55 (the lowest threshold "
                 "under review) are split into 5 ratio bands; each band is "
                 "sorted by (transcript_id, raw_label), shuffled with a single "
                 "random.Random(71) walked band by band in ascending order, and "
                 "the band quota taken. Band precisions recombine to threshold "
                 "precision weighted by band population."),
        "pool_size": sum(v["population"] for v in strata.values()),
        "n_sampled": len(picked),
        "strata": strata,
        "bands": bands(rows),
        "sample": picked,
    }
    (OUT / "fuzzy_host_sample.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "scan"
    if what == "scan":
        p = scan()
        print(json.dumps({k: v for k, v in p.items() if k != "rows"}, indent=1))
        print("bands:", json.dumps(bands(p["rows"]), indent=1))
    else:
        s = sample()
        print(json.dumps({k: v for k, v in s.items() if k != "sample"}, indent=1))
