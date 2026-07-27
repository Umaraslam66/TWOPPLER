"""Score the parameter-5 fresh tranche: rubric-briefed auditor line vs judge.

The bar was pre-committed 2026-07-28 BEFORE this line existed:
raw agreement >= 0.80 AND Cohen's kappa >= 0.60. Verdict is mechanical.

The auditor line is recorded verbatim in AUDIT_LINES_2026-07-28.md and
mirrored here; the judge line comes from fresh_tranche_key.json. Kappa is
3-category (SAME/DIFFERENT/UNCLEAR), identical to the A/B/C scoring.
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "results" / "stage2_openended"

AUDITOR = {
    "D1": "SAME", "D2": "SAME", "D3": "SAME", "D4": "DIFFERENT",
    "D5": "DIFFERENT", "D6": "SAME", "D7": "SAME", "D8": "DIFFERENT",
    "D9": "DIFFERENT",
    "E1": "SAME", "E2": "DIFFERENT", "E3": "SAME", "E4": "SAME",
    "E5": "SAME", "E6": "SAME", "E7": "UNCLEAR", "E8": "DIFFERENT",
    "E9": "DIFFERENT",
}
LOW_CONFIDENCE = ["D6", "D9", "E2", "E6"]
CATS = ["SAME", "DIFFERENT", "UNCLEAR"]


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pe = sum(
        (sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n)
        for c in CATS
    )
    return po, (po - pe) / (1 - pe)


def main():
    key = json.load(open(BASE / "fresh_tranche_key.json"))
    judge = {e["entry"]: e["judge_label"] for e in key["entries"]}
    assert set(judge) == set(AUDITOR)
    pairs = [(AUDITOR[e], judge[e]) for e in sorted(AUDITOR)]
    raw, k = kappa(pairs)
    disagree = sorted(e for e in AUDITOR if AUDITOR[e] != judge[e])
    verdict = "PASS" if (raw >= 0.80 and k >= 0.60) else "FAIL"
    out = {
        "n": len(pairs),
        "raw": round(raw, 4),
        "kappa": round(k, 4),
        "bar": "raw >= 0.80 AND kappa >= 0.60 (pre-committed 2026-07-28)",
        "verdict": verdict,
        "disagreements": {e: {"auditor": AUDITOR[e], "judge": judge[e]}
                          for e in disagree},
        "auditor_low_confidence": LOW_CONFIDENCE,
        "agreements": len(pairs) - len(disagree),
    }
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
