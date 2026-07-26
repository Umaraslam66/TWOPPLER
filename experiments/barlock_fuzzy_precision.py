"""Bar-lock item 1, stage 3: precision of the D3.2 fuzzy arm at each threshold.

The fuzzy arm at >= 0.55 fires on only 151 distinct (descriptor, programme)
pairs across the whole corpus scan, so this is a CENSUS, not a sample: every
pair is hand-labelled once and the label applies to every turn that carries it.

Labels (in results/stage2_pilot2/barlock/fuzzy_host_labels.json):
  anchor  the speaker presents THIS programme — exactly what D3.2 exists for
  staff   house staff of the show (correspondent, analyst, producer) — on the
          host side of the host/guest split, but not the interviewer
  false   a guest, a relative of the host, an outside-network person, or noise

Two precisions are reported because the design question has two readings:
  strict  = anchor / all fires        (does D3.2 find the anchor?)
  lenient = (anchor+staff) / all fires (does D3.2 keep guests out of the host
            role, which is all D4 actually needs?)

Both are also reported on the fires that CHANGE something — the labels the
origin classify_speaker() does not already call staff.

Usage: uv run python experiments/barlock_fuzzy_precision.py [labels.tsv]
       (defaults to results/stage2_pilot2/barlock/fuzzy_host_labels.tsv)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "stage2_pilot2" / "barlock"

THRESHOLDS = (0.55, 0.60, 0.65, 0.70)
BANDS = [(0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 1.01)]


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def load_labels(path: Path) -> dict[tuple[str, str], str]:
    out = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        verdict, descriptor, program = line.split("\t")
        out[(descriptor, program)] = verdict
    return out


def main(argv) -> int:
    t0 = time.time()
    labels_path = (Path(argv[1]) if len(argv) > 1
                   else OUT / "fuzzy_host_labels.tsv")
    labels = load_labels(labels_path)
    scan = json.loads((OUT / "fuzzy_host_scan.json").read_text())
    rows = [r for r in scan["rows"] if r["ratio"] >= 0.55]

    missing = sorted({(r["descriptor"], r["program"]) for r in rows}
                     - set(labels))
    if missing:
        print(f"UNLABELLED PAIRS ({len(missing)}):")
        for m in missing[:20]:
            print("  ", m)
        return 1

    for r in rows:
        r["verdict"] = labels[(r["descriptor"], r["program"])]

    def tally(sel):
        n = len(sel)
        turns = sum(x["n_turns"] for x in sel)
        a = sum(1 for x in sel if x["verdict"] == "anchor")
        s = sum(1 for x in sel if x["verdict"] == "staff")
        f = n - a - s
        return {
            "label_rows": n, "turns": turns,
            "anchor": a, "staff": s, "false": f,
            "precision_strict": round(a / n, 4) if n else None,
            "precision_strict_ci95": wilson(a, n),
            "precision_lenient": round((a + s) / n, 4) if n else None,
            "precision_lenient_ci95": wilson(a + s, n),
            "turns_anchor": sum(x["n_turns"] for x in sel
                                if x["verdict"] == "anchor"),
            "turns_false": sum(x["n_turns"] for x in sel
                               if x["verdict"] == "false"),
        }

    per_band = {f"{lo:.2f}-{hi:.2f}": tally([r for r in rows
                                             if lo <= r["ratio"] < hi])
                for lo, hi in BANDS}
    per_threshold = {}
    for t in THRESHOLDS:
        sel = [r for r in rows if r["ratio"] >= t]
        new = [r for r in sel if not r["already_staff"]]
        per_threshold[f">={t:.2f}"] = {
            "all_fires": tally(sel),
            "fires_that_change_a_turn": tally(new),
            "transcripts": len({r["transcript_id"] for r in sel}),
            "transcripts_changed": len({r["transcript_id"] for r in new}),
        }

    # --- a cheap guard, priced on the same census ------------------------
    # Two thirds of the false fires are one of two shapes: a relationship to
    # the host ("LARRY KING'S WIFE", "SON OF LARRY KING") or a descriptor that
    # merely rhymes with the show ("NEW YORK" vs "NEW DAY", "POLITICO" vs
    # "INSIDE POLITICS"). Both are cheap to exclude and neither can touch a
    # typo, which is the only thing the fuzzy arm exists for.
    import re as _re

    RELATION = _re.compile(r"'S\b|\bS\b|\bOF\b|\bWIFE\b|\bSON\b|\bDAUGHTER\b"
                           r"|\bBROTHER\b|\bSISTER\b|\bMOTHER\b|\bFATHER\b"
                           r"|\bFRIEND\b|\bWIDOW\b", _re.IGNORECASE)

    def shares_long_word(dn: str, pn: str) -> bool:
        a = {w for w in dn.split() if len(w) >= 4}
        b = {w for w in pn.split() if len(w) >= 4}
        return bool(a & b)

    def passes_guard(r: dict) -> bool:
        if RELATION.search(r["descriptor"]):
            return False
        return shares_long_word(r["norm_descriptor"], r["norm_program"])

    guard = {}
    for t in THRESHOLDS:
        sel = [r for r in rows if r["ratio"] >= t and passes_guard(r)]
        new = [r for r in sel if not r["already_staff"]]
        dropped = [r for r in rows if r["ratio"] >= t and not passes_guard(r)]
        guard[f">={t:.2f} + guard"] = {
            "all_fires": tally(sel),
            "fires_that_change_a_turn": tally(new),
            "dropped_rows": len(dropped),
            "dropped_anchor_rows": sum(1 for r in dropped
                                       if r["verdict"] == "anchor"),
            "dropped_anchor_examples": sorted({
                f'{r["descriptor"]} || {r["program"]}'
                for r in dropped if r["verdict"] == "anchor"})[:8],
        }

    # The case D3.2 was built for.
    dl = [r for r in rows if "Linense" in r["program"]]
    payload = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": ("census over every distinct (descriptor, programme) pair "
                   "the fuzzy arm fires on at ratio >= 0.55; each pair labelled "
                   "once by hand and applied to all its turns"),
        "labels": str(labels_path.relative_to(ROOT)),
        "n_pairs_labelled": len(labels),
        "n_label_rows": len(rows),
        "label_definitions": {
            "anchor": "presents this programme (D3.2's stated target)",
            "staff": "house staff of the show, not the interviewer",
            "false": "guest, relative of the host, outside network, or noise",
        },
        "per_band": per_band,
        "per_threshold": per_threshold,
        "per_threshold_with_guard": guard,
        "guard_rule": (
            "reject a descriptor containing a relationship marker ('S / OF / "
            "WIFE / SON / DAUGHTER / BROTHER / SISTER / MOTHER / FATHER / "
            "FRIEND / WIDOW), and require the normalised descriptor and "
            "programme to share at least one word of >= 4 letters"),
        "diplomatic_license_case": {
            "label_rows": len(dl), "turns": sum(r["n_turns"] for r in dl),
            "ratio": sorted({r["ratio"] for r in dl}),
            "verdicts": sorted({r["verdict"] for r in dl}),
            "note": "the one case v1.5 was written for; it sits at 0.68",
        },
        "runtime_secs": round(time.time() - t0, 2),
    }
    (OUT / "fuzzy_host_precision.json").write_text(json.dumps(payload, indent=1))
    # keep the labels next to the numbers so the owner can spot-check
    (OUT / "fuzzy_host_labels.json").write_text(json.dumps(
        [{"verdict": v, "descriptor": d, "program": p,
          "label_rows": sum(1 for r in rows
                            if r["descriptor"] == d and r["program"] == p),
          "ratio": next(r["ratio"] for r in rows
                        if r["descriptor"] == d and r["program"] == p)}
         for (d, p), v in labels.items()], indent=1))
    print(json.dumps(payload, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
