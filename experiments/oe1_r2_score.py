"""STEP 1 + STEP 2 of the 2026-07-28 batch: r2 regression and parameter 5.

STEP 1 — regression on D/E: did r2 fix the four r1 disagreements (D6,
E6, E7, E9 vs the rubric-briefed auditor line), and did it preserve the
14 agreements? Owner branch rule, set before the run: >2 previously-
correct rows broken -> STOP, overfitted.

STEP 2 — parameter 5 on F/G: r2-judge vs the rubric-briefed auditor
line, unchanged pre-committed bar (raw >= 0.80 AND kappa >= 0.60),
verdict mechanical. Also fills judge_label_r2/central/why into
fresh_tranche_r2_key.json (the key's r1 labels were draw-balance only).

Both auditor lines are recorded verbatim in AUDIT_LINES_2026-07-28.md;
kappa is 3-category, identical to every prior audit scoring.
"""
import json
from pathlib import Path

from oe1_param5_score import AUDITOR as AUDITOR_DE, kappa

BASE = Path(__file__).resolve().parent.parent / "results" / "stage2_openended"

AUDITOR_FG = {
    "F1": "SAME", "F2": "SAME", "F3": "SAME", "F4": "SAME",
    "F5": "DIFFERENT", "F6": "SAME", "F7": "SAME", "F8": "DIFFERENT",
    "F9": "SAME",
    "G1": "UNCLEAR", "G2": "SAME", "G3": "SAME", "G4": "SAME",
    "G5": "SAME", "G6": "UNCLEAR", "G7": "UNCLEAR", "G8": "DIFFERENT",
    "G9": "DIFFERENT",
}
LOW_CONFIDENCE_FG = ["F4", "G3", "G5", "G7"]
R1_DISAGREEMENTS = ["D6", "E6", "E7", "E9"]
BREAK_LIMIT = 2  # owner: >2 broken previously-correct rows -> STOP


def load_labels(fname):
    return {r["entry"]: r for r in
            (json.loads(line) for line in open(BASE / "judge" / fname))}


def main():
    # STEP 1 — regression on D/E
    r1 = {e["entry"]: e["judge_label"]
          for e in json.load(open(BASE / "fresh_tranche_key.json"))["entries"]}
    r2_de = load_labels("judgements_r2_regression.jsonl")
    fixes, breaks, still_wrong = [], [], []
    for entry, aud in sorted(AUDITOR_DE.items()):
        was_correct = r1[entry] == aud
        now_correct = r2_de[entry]["label"] == aud
        row = {"entry": entry, "auditor": aud, "r1": r1[entry],
               "r2": r2_de[entry]["label"],
               "central_r2": r2_de[entry]["central"]}
        if not was_correct and now_correct:
            fixes.append(row)
        elif was_correct and not now_correct:
            breaks.append(row)
        elif not was_correct and not now_correct:
            still_wrong.append(row)
    regression = {
        "fixed": fixes, "n_fixed": len(fixes),
        "fixed_of": R1_DISAGREEMENTS,
        "broken": breaks, "n_broken": len(breaks),
        "still_wrong": still_wrong,
        "de_agreement_r1": sum(r1[e] == a for e, a in AUDITOR_DE.items()),
        "de_agreement_r2": sum(r2_de[e]["label"] == a
                               for e, a in AUDITOR_DE.items()),
        "branch_rule": f"STOP if n_broken > {BREAK_LIMIT}",
        "overfit_stop": len(breaks) > BREAK_LIMIT,
    }

    # STEP 2 — parameter 5 on F/G
    r2_fg = load_labels("judgements_r2_fg.jsonl")
    assert set(r2_fg) == set(AUDITOR_FG)
    pairs = [(AUDITOR_FG[e], r2_fg[e]["label"]) for e in sorted(AUDITOR_FG)]
    raw, k = kappa(pairs)
    disagree = {e: {"auditor": AUDITOR_FG[e], "judge_r2": r2_fg[e]["label"],
                    "central_r2": r2_fg[e]["central"]}
                for e in sorted(AUDITOR_FG)
                if AUDITOR_FG[e] != r2_fg[e]["label"]}
    verdict = "PASS" if (raw >= 0.80 and k >= 0.60) else "FAIL"

    # Fill the r2 line into the sealed key (now open: both sheets labeled).
    keypath = BASE / "fresh_tranche_r2_key.json"
    key = json.load(open(keypath))
    for e in key["entries"]:
        row = r2_fg[e["entry"]]
        e["judge_label_r2"] = row["label"]
        e["judge_central_r2"] = row["central"]
        e["judge_why_r2"] = row["why"]
    key["balance_drift_note"] = (
        "r2 judge labels on this tranche: "
        + json.dumps({lab: sum(1 for e in key["entries"]
                               if e["judge_label_r2"] == lab)
                      for lab in ("SAME", "DIFFERENT", "UNCLEAR")})
        + " (draw was balanced on r1 labels 9/4/5; drift reported, not repaired)")
    json.dump(key, open(keypath, "w"), indent=1)

    out = {
        "step1_regression": regression,
        "step2_parameter5": {
            "n": len(pairs), "raw": round(raw, 4), "kappa": round(k, 4),
            "bar": "raw >= 0.80 AND kappa >= 0.60 (pre-committed, unchanged)",
            "verdict": verdict,
            "disagreements": disagree,
            "auditor_low_confidence": LOW_CONFIDENCE_FG,
        },
    }
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
