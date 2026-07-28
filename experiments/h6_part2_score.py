#!/usr/bin/env python3
"""Score the part-2 H6 classifier trust gate against the frozen bars.

**Written and committed before any co-audit label existed.** That is the whole
point of this file: the arithmetic, the bar comparisons and the tripwire
verdicts were all settled while the answer was still unknown, so nobody can
pick a favourable scoring rule after seeing the labels. Do not edit the bars or
the verdict logic in this file to accommodate a result. If a genuine bug is
found, fix it and say so in the commit message.

Inputs
------
1. ``results/stage2_openended/h6_part2_key.json`` -- the sealed key built by
   ``experiments/h6_part2_tranche.py``. Row -> classifier label + provenance.
2. ``--labels <file.json>`` -- the co-auditor's line. Tolerant about shape;
   any of these work, and unknown extra fields are ignored:

       {"1": "F", "2": "N", ...}
       {"1": "FOLLOW-UP", "2": "NEW-TOPIC", ...}
       {"labels": {"1": "F", ...}, "low_confidence_rows": [4, 9]}
       {"rows": [{"row": 1, "label": "F", "confidence": "low",
                  "rationale": "..."}, ...]}

   ``X`` (or ``SKIP`` / ``UNJUDGEABLE``) marks a row the auditor could not
   judge. Those rows are dropped from every statistic and reported, exactly as
   the sheet's own instructions promise.

What it prints
--------------
Raw agreement, Cohen's kappa, the FOLLOW-UP and NEW-TOPIC overturn rates,
per-subject disagreement counts, and the mechanical verdicts. The bars are
printed verbatim next to each verdict so the reader never has to trust this
file's summary of them.

The bars, quoted from the frozen documents
------------------------------------------
Trust bar -- Amendment 2 B2.2, carried to part 2 by Addendum A precondition 5
part 2 ("the same trust bar carried over"):

    ">= 85% raw agreement AND Cohen's kappa >= 0.6"

and the consequence of failing it, from precondition 5 part 2:

    "If part 2 fails the bar, H6 scoring halts pending rubric revision."

Tripwires -- H6/B3 parameter appendix section 4.3(c), APPROVED 2026-07-28:

    "Part-2 FOLLOW-UP overturn rate > 20% -> H6's rich arm is additionally
    built at D_min = 3 as a pre-committed sensitivity arm, and both results
    are reported side by side. Direction must survive both for any headline."

    "> 35% -> H6 scoring halts pending rubric revision."

Both thresholds are strict ">" as written. A rate of exactly 0.20 does not
fire the sensitivity arm; exactly 0.35 does not halt.

Pure stdlib, no network, no model calls, deterministic.

Run::

    .venv/bin/python experiments/h6_part2_score.py --labels coaudit.json
    .venv/bin/python experiments/h6_part2_score.py --labels coaudit.json \
        --out results/stage2_openended/h6_part2_scores.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

FOLLOW_UP = "FOLLOW-UP"
NEW_TOPIC = "NEW-TOPIC"
LABELS = (FOLLOW_UP, NEW_TOPIC)

KEY_PATH = REPO / "results/stage2_openended/h6_part2_key.json"

# --- the frozen bars, as numbers and as the sentences they came from --------

RAW_BAR = 0.85
KAPPA_BAR = 0.60
TRUST_BAR_TEXT = (
    'Amendment 2 B2.2, carried to part 2 by Addendum A precondition 5 part 2: '
    '">= 85% raw agreement AND Cohen\'s kappa >= 0.6". '
    'On failure: "If part 2 fails the bar, H6 scoring halts pending rubric '
    'revision."')

TRIPWIRE_DMIN3 = 0.20
TRIPWIRE_HALT = 0.35
TRIPWIRE_TEXT = (
    'H6/B3 appendix section 4.3(c), APPROVED 2026-07-28: '
    '"Part-2 FOLLOW-UP overturn rate > 20% -> H6\'s rich arm is additionally '
    'built at D_min = 3 as a pre-committed sensitivity arm, and both results '
    'are reported side by side. Direction must survive both for any headline." '
    '"> 35% -> H6 scoring halts pending rubric revision."')

#: For context only -- never used in a verdict.
DEV_PART1 = {"raw": 0.8667, "kappa": 0.7333, "n": 120,
             "follow_up_overturn": 0.25, "new_topic_overturn": 0.017}

_SKIP = {"X", "SKIP", "UNJUDGEABLE", "?", ""}
_ALIASES = {
    "F": FOLLOW_UP, "FOLLOWUP": FOLLOW_UP, "FOLLOW-UP": FOLLOW_UP,
    "FOLLOW UP": FOLLOW_UP,
    "N": NEW_TOPIC, "NEWTOPIC": NEW_TOPIC, "NEW-TOPIC": NEW_TOPIC,
    "NEW TOPIC": NEW_TOPIC,
}


def fatal(msg: str) -> SystemExit:
    return SystemExit(f"FATAL: {msg}")


def _display_path(path) -> str:
    """Repo-relative when it can be, absolute otherwise.

    A key or label file may legitimately sit outside the repo (a scratch copy,
    a self-test fixture), and printing a path must never be the thing that
    crashes a scoring run.
    """
    path = Path(path)
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def normalise(value) -> str | None:
    """One auditor answer -> a label, or None for 'could not judge'.

    Anything unrecognised is a hard error rather than a silent skip: a typo in
    an auditor line must not quietly shrink the denominator.
    """
    if value is None:
        return None
    text = str(value).strip().upper().strip(".*_`\"'")
    if text in _SKIP:
        return None
    if text in _ALIASES:
        return _ALIASES[text]
    raise fatal(f"unrecognised auditor label {value!r}; expected F/N, "
                "FOLLOW-UP/NEW-TOPIC, or X for unjudgeable")


def load_auditor(path: Path) -> tuple[dict[int, str | None], dict]:
    """Read the co-auditor's line out of any of the tolerated shapes."""
    doc = json.loads(Path(path).read_text())
    extras: dict = {}
    raw: dict = {}

    if isinstance(doc, dict) and "rows" in doc and isinstance(doc["rows"], list):
        for entry in doc["rows"]:
            if not isinstance(entry, dict):
                raise fatal("'rows' must hold objects with 'row' and 'label'")
            if "row" not in entry:
                raise fatal(f"row entry without a 'row' field: {entry}")
            label = entry.get("label", entry.get("auditor_label"))
            raw[entry["row"]] = label
            for field in ("confidence", "rationale", "why", "note"):
                if field in entry:
                    extras.setdefault(field, {})[str(entry["row"])] = entry[field]
    elif isinstance(doc, dict):
        table = doc.get("labels") if isinstance(doc.get("labels"), dict) else None
        if table is None:
            table = {k: v for k, v in doc.items() if str(k).lstrip("-").isdigit()}
            if not table:
                raise fatal("no labels found; expected a row->label map, a "
                            "'labels' object, or a 'rows' list")
        else:
            extras = {k: v for k, v in doc.items() if k != "labels"}
        raw = dict(table)
    else:
        raise fatal("labels file must be a JSON object")

    out: dict[int, str | None] = {}
    for key, value in raw.items():
        try:
            row = int(key)
        except (TypeError, ValueError):
            raise fatal(f"row id {key!r} is not an integer")
        if row in out:
            raise fatal(f"row {row} appears twice in the auditor file")
        out[row] = normalise(value)
    return out, extras


def cohens_kappa(pairs: list[tuple[str, str]]) -> tuple[float, float, dict]:
    """Raw agreement and Cohen's kappa for two raters over two categories.

    kappa = (po - pe) / (1 - pe), with pe the chance agreement implied by each
    rater's own marginal rates. Returns (raw, kappa, detail).
    """
    n = len(pairs)
    if not n:
        raise fatal("no scorable rows")
    po = sum(1 for a, b in pairs if a == b) / n
    a_marg = Counter(a for a, _ in pairs)
    b_marg = Counter(b for _, b in pairs)
    pe = sum((a_marg[label] / n) * (b_marg[label] / n) for label in LABELS)
    if pe == 1.0:
        # Both raters used one label for everything: kappa is undefined, and
        # saying so is better than printing a 0 that reads like disagreement.
        return po, float("nan"), {"po": po, "pe": pe, "undefined": True,
                                  "reason": "both raters used a single label; "
                                            "chance agreement is 1.0"}
    kappa = (po - pe) / (1 - pe)
    return po, kappa, {"po": po, "pe": pe, "undefined": False,
                       "classifier_marginals": dict(a_marg),
                       "auditor_marginals": dict(b_marg)}


def score(key_path: Path, labels_path: Path) -> dict:
    key_doc = json.loads(Path(key_path).read_text())
    key_rows = {int(r["row"]): r for r in key_doc["key"]}
    auditor, extras = load_auditor(labels_path)

    unknown = sorted(set(auditor) - set(key_rows))
    if unknown:
        raise fatal(f"auditor file has rows not in the key: {unknown[:10]}")
    missing = sorted(set(key_rows) - set(auditor))
    skipped = sorted(r for r, v in auditor.items() if v is None)

    pairs: list[tuple[str, str]] = []
    disagreements = []
    per_subject: dict[str, dict] = {}
    for row in sorted(key_rows):
        auditor_label = auditor.get(row)
        if auditor_label is None:
            continue
        classifier_label = key_rows[row]["classifier_label"]
        pairs.append((classifier_label, auditor_label))
        cid = key_rows[row]["canonical_id"]
        cell = per_subject.setdefault(cid, {"n": 0, "agree": 0, "disagree": 0})
        cell["n"] += 1
        if classifier_label == auditor_label:
            cell["agree"] += 1
        else:
            cell["disagree"] += 1
            disagreements.append({
                "row": row,
                "classifier_label": classifier_label,
                "auditor_label": auditor_label,
                "canonical_id": cid,
                "transcript_id": key_rows[row]["transcript_id"],
                "turn_idx": key_rows[row]["turn_idx"],
            })

    raw, kappa, detail = cohens_kappa(pairs)

    overturn = {}
    for label in LABELS:
        n_label = sum(1 for a, _ in pairs if a == label)
        n_over = sum(1 for a, b in pairs if a == label and b != label)
        overturn[label] = {
            "n_classifier_rows": n_label,
            "n_overturned": n_over,
            "rate": round(n_over / n_label, 6) if n_label else None,
        }

    fu_rate = overturn[FOLLOW_UP]["rate"]
    trust_pass = (raw >= RAW_BAR) and (kappa == kappa) and (kappa >= KAPPA_BAR)

    if fu_rate is None:
        tripwire = "UNDEFINED — no FOLLOW-UP rows were scorable"
        dmin3, halt = False, False
    else:
        halt = fu_rate > TRIPWIRE_HALT
        dmin3 = fu_rate > TRIPWIRE_DMIN3
        tripwire = ("HALT — H6 scoring stops pending rubric revision"
                    if halt else
                    "D_min = 3 sensitivity arm is MANDATORY, both arms reported"
                    if dmin3 else
                    "no tripwire fired")

    return {
        "generated_by": "experiments/h6_part2_score.py",
        "scorer_precommitted": "written and committed before any co-audit "
                               "label existed",
        "key_path": _display_path(key_path),
        "labels_path": str(labels_path),
        "seed": key_doc.get("seed"),
        "rubric_sha256": key_doc.get("rubric_sha256"),
        "classifier": key_doc.get("classifier"),
        "n_key_rows": len(key_rows),
        "n_scored": len(pairs),
        "n_skipped_unjudgeable": len(skipped),
        "skipped_rows": skipped,
        "n_missing_from_auditor": len(missing),
        "missing_rows": missing,
        "raw_agreement": round(raw, 4),
        "cohens_kappa": (None if kappa != kappa else round(kappa, 4)),
        "kappa_detail": detail,
        "overturn": overturn,
        "n_disagreements": len(disagreements),
        "disagreements": disagreements,
        "disagreement_direction": {
            "classifier_FOLLOW-UP_auditor_NEW-TOPIC": sum(
                1 for d in disagreements
                if d["classifier_label"] == FOLLOW_UP),
            "classifier_NEW-TOPIC_auditor_FOLLOW-UP": sum(
                1 for d in disagreements
                if d["classifier_label"] == NEW_TOPIC),
        },
        "per_subject": dict(sorted(per_subject.items())),
        "n_subjects_scored": len(per_subject),
        "bars": {
            "trust_bar_text": TRUST_BAR_TEXT,
            "raw_bar": RAW_BAR,
            "kappa_bar": KAPPA_BAR,
            "tripwire_text": TRIPWIRE_TEXT,
            "tripwire_dmin3_above": TRIPWIRE_DMIN3,
            "tripwire_halt_above": TRIPWIRE_HALT,
        },
        "verdicts": {
            "trust_gate": "PASS" if trust_pass else "FAIL",
            "trust_gate_consequence": (
                "part 2 satisfied; H6 arm building may proceed"
                if trust_pass else
                "H6 scoring HALTS pending rubric revision"),
            "tripwire": tripwire,
            "dmin3_sensitivity_arm_required": dmin3,
            "h6_scoring_halts": (not trust_pass) or halt,
        },
        "dev_part1_for_context_only": DEV_PART1,
    }


def report(out: dict) -> None:
    v, b = out["verdicts"], out["bars"]
    print("H6 classifier trust gate -- PART 2 (confirmatory subjects)")
    print("=" * 66)
    print(f"key            : {out['key_path']} (seed {out['seed']})")
    print(f"auditor labels : {out['labels_path']}")
    print(f"classifier     : {out['classifier']}")
    print(f"rubric sha256  : {out['rubric_sha256']}")
    print()
    print(f"rows in key    : {out['n_key_rows']}")
    print(f"rows scored    : {out['n_scored']}")
    if out["n_skipped_unjudgeable"]:
        print(f"  unjudgeable  : {out['n_skipped_unjudgeable']} "
              f"{out['skipped_rows']}")
    if out["n_missing_from_auditor"]:
        print(f"  MISSING      : {out['n_missing_from_auditor']} "
              f"{out['missing_rows']}")
    print(f"subjects       : {out['n_subjects_scored']}")
    print()
    print("AGREEMENT")
    print(f"  raw agreement : {out['raw_agreement']}")
    print(f"  Cohen's kappa : {out['cohens_kappa']}")
    print(f"  disagreements : {out['n_disagreements']}")
    d = out["disagreement_direction"]
    print(f"    classifier FOLLOW-UP / auditor NEW-TOPIC : "
          f"{d['classifier_FOLLOW-UP_auditor_NEW-TOPIC']}")
    print(f"    classifier NEW-TOPIC / auditor FOLLOW-UP : "
          f"{d['classifier_NEW-TOPIC_auditor_FOLLOW-UP']}")
    print()
    print("OVERTURN RATES (classifier label overturned by the auditor)")
    for label in LABELS:
        cell = out["overturn"][label]
        print(f"  {label:<10} {cell['n_overturned']:>4} / "
              f"{cell['n_classifier_rows']:<4} = {cell['rate']}")
    print()
    print("THE BAR, VERBATIM")
    print(f"  {b['trust_bar_text']}")
    print(f"  VERDICT: trust gate {v['trust_gate']} "
          f"(raw {out['raw_agreement']} vs >= {b['raw_bar']}; "
          f"kappa {out['cohens_kappa']} vs >= {b['kappa_bar']})")
    print(f"  -> {v['trust_gate_consequence']}")
    print()
    print("THE TRIPWIRE, VERBATIM")
    print(f"  {b['tripwire_text']}")
    print(f"  VERDICT: {v['tripwire']}")
    print()
    print(f"H6 SCORING HALTS: {'YES' if v['h6_scoring_halts'] else 'no'}")
    print(f"D_min = 3 SENSITIVITY ARM REQUIRED: "
          f"{'YES' if v['dmin3_sensitivity_arm_required'] else 'no'}")
    print()
    print("For context only, never a verdict input -- dev part 1: "
          f"raw {DEV_PART1['raw']}, kappa {DEV_PART1['kappa']}, "
          f"FOLLOW-UP overturn {DEV_PART1['follow_up_overturn']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--labels", required=True,
                    help="co-auditor label file (JSON)")
    ap.add_argument("--key", default=str(KEY_PATH),
                    help="sealed key (default: the part-2 key)")
    ap.add_argument("--out", default=None,
                    help="also write the full result as JSON here")
    ap.add_argument("--allow-missing", action="store_true",
                    help="score anyway when the auditor left rows unanswered; "
                         "without this a missing row is a hard stop, because a "
                         "silently shrunk denominator flatters every statistic")
    args = ap.parse_args()

    out = score(Path(args.key), Path(args.labels))
    if out["n_missing_from_auditor"] and not args.allow_missing:
        report(out)
        raise fatal(f"{out['n_missing_from_auditor']} key rows have no auditor "
                    f"label: {out['missing_rows'][:20]}. Re-run with "
                    "--allow-missing only if that is genuinely intended.")
    report(out)
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
