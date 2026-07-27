#!/usr/bin/env python3
"""Build the H6 classifier trust-gate audit sheet (Amendment 2, B2.2).

B2.2 requires the owner to spot-check >= 100 classifications, sampled across
>= 10 subjects and balanced across the two labels, before any confirmatory H6
arm is built. This script draws that sample deterministically and writes two
files:

* ``results/stage2_openended/h6_audit_sheet.md`` -- BLIND. Row number, the
  exact evidence the classifier saw, and an empty field for the owner's label.
  It carries no classifier label, no reasoning, and no provenance (no subject
  id, transcript id or turn index), so nothing in it can be joined back to the
  labelled records while the owner is labelling.
* ``results/stage2_openended/h6_audit_key.json`` -- the key. Row number ->
  classifier label + the record it came from.

KNOWN SHORTFALL, recorded in both outputs. The classifier has only ever run on
the 6 dev subjects, because B3 and Addendum A hold confirmatory subjects
untouched by all Stage 2 machinery until the bar-lock addendum is committed,
and that addendum is still a DRAFT whose precondition 5 is this very gate. So
"across >= 10 subjects" is not satisfiable from existing outputs without
breaking confirmatory-untouched discipline. The sheet uses all 6 available
subjects and over-samples rows (120, not 100) to partly offset the narrower
subject base. Deciding whether that clears B2.2 is the owner's call.

Pure stdlib, no network, no model calls. Deterministic given SEED.

Run:  uv run python experiments/h6_audit_sample.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from doppler.followup_render import (  # noqa: E402
    CASE_HEADER,
    FOLLOW_UP,
    LABELS,
    NEW_TOPIC,
    OUTPUT_INSTRUCTION,
    RUBRIC_SHA256,
)

# --------------------------------------------------------------------------
# Parameters (change nothing here without re-recording the seed in the sheet)
# --------------------------------------------------------------------------

#: Sampling seed. Distinct from the dev-subject draw (47) and the pilot's
#: item sampler (49) so this draw is independent of both.
SEED = 61

#: Total rows. B2.2's floor is 100; we draw 120 so the gate still has >= 100
#: usable rows if the owner throws some out as unjudgeable, and because the
#: subject base is narrower than B2.2 asks for (see the shortfall note above).
N_TOTAL = 120

#: Minimum turn-index distance between two sampled rows from the same
#: transcript. A case is rendered as host(N) / guest(N+1) / host(N+2), so its
#: PREV field is the host turn two back. Without a gap the owner would meet the
#: same sentence twice -- once as a TARGET to label, once as the PREV of a
#: later row -- and the two judgements would not be independent. A gap of 3
#: removes that overlap entirely. Supply is ample: 126 FOLLOW-UP and 187
#: NEW-TOPIC rows survive the constraint, against the 60 + 60 needed.
MIN_TURN_GAP = 3

RECORDS = REPO / "results/stage2_pilot/records/classify.jsonl"
PROMPTS = REPO / "results/stage2_pilot/exports/prompts_classify.jsonl"
META = REPO / "results/stage2_pilot/exports/meta_classify.jsonl"

OUT_DIR = REPO / "results/stage2_openended"
SHEET = OUT_DIR / "h6_audit_sheet.md"
KEY = OUT_DIR / "h6_audit_key.json"


# --------------------------------------------------------------------------
# Load
# --------------------------------------------------------------------------


def read_jsonl(path: Path) -> list[dict]:
    with path.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


def case_text(prompt: str) -> str:
    """The PREV/GUEST/TARGET block, sliced out of the rendered prompt.

    Taking it from the prompt rather than re-deriving it from the transcripts
    guarantees the owner judges byte-for-byte the same evidence the classifier
    was given -- same 60/120/120-word truncations, same "..." marks. The slice
    is bounded by two frozen constants, and it excludes the rubric's few-shot
    examples, which carry LABEL lines that would break the blind.
    """
    start = prompt.index(CASE_HEADER) + len(CASE_HEADER)
    end = prompt.index(OUTPUT_INSTRUCTION)
    block = prompt[start:end].strip()
    if "LABEL:" in block:
        raise AssertionError("case block leaked a LABEL line")
    return block


def load_pool() -> list[dict]:
    """Every auditable classification, in a fixed order.

    Only ``source == "model"`` rows are auditable. The 271 ``source == "rule"``
    rows are NEW-TOPIC by definition (SPEC D9: a host turn with no guest answer
    behind it), cost no model call and involve no judgement -- including them
    would measure the definition, not the rubric, and would inflate both raw
    agreement and kappa.
    """
    records = read_jsonl(RECORDS)
    prompts = {row["idx"]: row["prompt"] for row in read_jsonl(PROMPTS)}
    meta = {row["idx"]: row for row in read_jsonl(META)}

    pool = []
    for line_no, rec in enumerate(records, start=1):
        if rec.get("source") != "model":
            continue
        if rec.get("parse_failure") or rec.get("missing_completion"):
            continue  # B4.3 drops these from selection; they are not judgements
        idx = rec["idx"]
        m = meta[idx]
        if (m["canonical_id"], m["transcript_id"], m["turn_idx"]) != (
            rec["canonical_id"],
            rec["transcript_id"],
            rec["turn_idx"],
        ):
            raise AssertionError(f"meta/record mismatch at idx {idx}")
        pool.append(
            {
                "idx": idx,
                "record_line": line_no,
                "canonical_id": rec["canonical_id"],
                "transcript_id": rec["transcript_id"],
                "turn_idx": rec["turn_idx"],
                "label": rec["label"],
                "case": case_text(prompts[idx]),
            }
        )

    seen = set()
    for row in pool:
        if row["case"] in seen:
            raise AssertionError("duplicate case block in pool")
        seen.add(row["case"])

    pool.sort(key=lambda r: (r["canonical_id"], r["transcript_id"], r["turn_idx"]))
    return pool


# --------------------------------------------------------------------------
# Allocation
# --------------------------------------------------------------------------


def allocate(supply: dict[str, int], quota: int) -> dict[str, int]:
    """Spread ``quota`` draws over subjects as evenly as supply allows.

    Even split first (remainder to the lexicographically first subjects), then
    every cell capped at its supply, then the resulting deficit handed to
    whichever subject has the most unused rows left -- ties by subject id, one
    row at a time. Deterministic, and it keeps the label total exact whenever
    the label has enough rows overall.
    """
    subjects = sorted(supply)
    base, rem = divmod(quota, len(subjects))
    target = {s: base + (1 if i < rem else 0) for i, s in enumerate(subjects)}

    deficit = 0
    for s in subjects:
        if target[s] > supply[s]:
            deficit += target[s] - supply[s]
            target[s] = supply[s]

    while deficit > 0:
        headroom = {s: supply[s] - target[s] for s in subjects}
        candidates = [s for s in subjects if headroom[s] > 0]
        if not candidates:
            break  # label is exhausted corpus-wide; caller reports the shortfall
        best = min(candidates, key=lambda s: (-headroom[s], s))
        target[best] += 1
        deficit -= 1

    return target


def draw(pool: list[dict]) -> tuple[list[dict], dict]:
    """Draw the sample: balanced by label, spread over subjects, gap-respecting.

    Three passes. First an even per-(subject, label) target from raw supply.
    Then a greedy fill that refuses any row sitting within :data:`MIN_TURN_GAP`
    turns of one already taken from the same transcript, which can leave a cell
    short. Then a top-up that restores the exact per-label total, taken from
    whichever subject is furthest below its share. Label balance is the
    constraint that always holds; subject evenness bends to supply.

    FOLLOW-UP is filled before NEW-TOPIC because it is the scarcer label, so it
    gets first claim on the contested turn positions.
    """
    rng = random.Random(SEED)
    subjects = sorted({r["canonical_id"] for r in pool})
    per_label = N_TOTAL // len(LABELS)

    picked: list[dict] = []
    chosen: set[int] = set()                      # record idx already taken
    taken: dict[tuple[str, str], list[int]] = {}  # (subject, transcript) -> turns

    def fits(row: dict) -> bool:
        if row["idx"] in chosen:
            return False
        key = (row["canonical_id"], row["transcript_id"])
        return all(abs(row["turn_idx"] - t) >= MIN_TURN_GAP for t in taken.get(key, ()))

    def take(row: dict) -> None:
        taken.setdefault((row["canonical_id"], row["transcript_id"]), []).append(
            row["turn_idx"]
        )
        chosen.add(row["idx"])
        picked.append(row)

    plan: dict[str, dict[str, int]] = {}
    for label in (FOLLOW_UP, NEW_TOPIC):
        cells = {
            s: sorted(
                (r for r in pool if r["canonical_id"] == s and r["label"] == label),
                key=lambda r: (r["transcript_id"], r["turn_idx"]),
            )
            for s in subjects
        }
        target = allocate({s: len(v) for s, v in cells.items()}, per_label)

        got = {s: 0 for s in subjects}
        for s in subjects:
            for row in rng.sample(cells[s], len(cells[s])):
                if got[s] >= target[s]:
                    break
                if fits(row):
                    take(row)
                    got[s] += 1

        # Top-up: gap conflicts may have left the label short of per_label.
        while sum(got.values()) < per_label:
            progressed = False
            for s in sorted(subjects, key=lambda s: (got[s], s)):
                if sum(got.values()) >= per_label:
                    break
                for row in rng.sample(cells[s], len(cells[s])):
                    if fits(row):
                        take(row)
                        got[s] += 1
                        progressed = True
                        break
            if not progressed:
                break  # label exhausted under the gap rule; reported as shortfall
        plan[label] = got

    rng.shuffle(picked)  # blind: label order must carry no signal
    for n, row in enumerate(picked, start=1):
        row["row"] = n

    # The gap rule is a correctness claim about the sheet, so verify it.
    for (cid, tid), turns in taken.items():
        ordered = sorted(turns)
        for a, b in zip(ordered, ordered[1:]):
            if b - a < MIN_TURN_GAP:
                raise AssertionError(f"gap rule violated in {cid}/{tid}: {a},{b}")

    stats = {
        "seed": SEED,
        "min_turn_gap": MIN_TURN_GAP,
        "n_rows": len(picked),
        "n_subjects": len(subjects),
        "subjects": subjects,
        "pool_size": len(pool),
        "per_label_target": per_label,
        "achieved_by_label": {
            label: sum(1 for r in picked if r["label"] == label) for label in sorted(LABELS)
        },
        "achieved_by_subject": {
            s: sum(1 for r in picked if r["canonical_id"] == s) for s in subjects
        },
        "achieved_by_subject_label": {
            label: plan[label] for label in sorted(LABELS)
        },
        "pool_supply_by_subject_label": {
            label: {
                s: sum(
                    1 for r in pool if r["canonical_id"] == s and r["label"] == label
                )
                for s in subjects
            }
            for label in sorted(LABELS)
        },
    }
    return picked, stats


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

INSTRUCTIONS = """# H6 classifier audit sheet

**What this is.** A machine read {n} interviewer turns and sorted each one into
one of two boxes. Your job is to sort the same {n} turns yourself, without
seeing what the machine said. Afterwards we compare. If we agree often enough,
the machine's labels get used in the H6 experiment. If we don't, the
instructions it was given get rewritten and we try again.

**This sheet is blind on purpose.** The machine's answers are in a separate
file you should not open until you have finished. The rows are shuffled, and
the subject and interview each row came from are deliberately not shown, so
nothing here hints at the answer.

## The two labels

Every row shows three things:

- **PREV** - what the interviewer said last time.
- **GUEST** - what the guest said back.
- **TARGET** - the interviewer's next turn. **This is the only thing you label.**

Write **F** if TARGET is a **follow-up**: it picks up something in GUEST. It
quotes it, questions it, pushes back on it, asks the guest to explain or back
it up, or just asks for more of the same ("Go on.", "Meaning what?").

Write **N** if it's a **new topic**: TARGET brings in material that did not come
from GUEST. A prepared question, a change of subject, a hand-off to the next
segment, a sign-off, or a question aimed at someone else.

## The tricky ones (these are where we're most likely to disagree)

1. **Comment plus question -> judge the question.** "That's alarming. Who
   decides who gets tested?" is **F** - the compliment is filler, the question
   digs into the answer.
2. **Praise then swerve is N.** "Fascinating. Now, the budget vote..." looks
   friendly but takes nothing from GUEST.
3. **Same subject is not enough.** A question can be about the very thing the
   guest just discussed and still be **N** if it takes nothing from what they
   actually said.
4. **Guest dodged, interviewer asks again**: **F** only if TARGET names the
   dodge or quotes the answer. A plain repeat of the original question is **N**.
5. **Going back to the interviewer's own earlier line of questioning**, as if
   the guest's answer hadn't happened, is **N**.
6. **Part from GUEST, part new -> F.**
7. **Judge the words on the page**, not what you think the interviewer meant.

## How to fill this in

Go top to bottom. For each row write `F` or `N` on the **YOUR LABEL** line.
Don't skip and come back - first read, best guess. Every row needs an answer;
if a row is genuinely impossible to judge, write `X` and one word why, and tell
whoever is scoring it (rows marked `X` are dropped, and the gate needs at least
100 answered rows to count).

Text is cut to the same length the machine saw it, so `...` means words were
removed there. That is normal - judge what's shown.

## One thing to know before you start

The plan said this check should cover at least 10 different people. This sheet
covers **{n_subjects}**. That is not an oversight and nothing was left out: the
machine has only ever been run on the {n_subjects} development subjects,
because the rules keep every other subject untouched until this very check
passes. Running it on more people first would break that rule. To make up some
of the difference the sheet has {n_rows} rows instead of the required 100.
Whether that is good enough to count is your call, and it gets written down
either way.

---

"""

FOOTER_TEMPLATE = """
---

## Provenance

- Sampling seed: **{seed}**. Rebuild this exact sheet with
  `uv run python experiments/h6_audit_sample.py`.
- Rows: **{n_rows}**, drawn from **{pool_size}** model classifications over
  **{n_subjects}** subjects.
- Classifier rubric hash (frozen): `{rubric}`
- Classifier records: `results/stage2_pilot/records/classify.jsonl`
- Answer key (do not open until finished):
  `results/stage2_openended/h6_audit_key.json`
"""


def write_sheet(rows: list[dict], stats: dict) -> None:
    parts = [
        INSTRUCTIONS.format(
            n=stats["n_rows"],
            n_rows=stats["n_rows"],
            n_subjects=stats["n_subjects"],
        )
    ]
    for row in rows:
        parts.append(f"### Row {row['row']}\n\n```\n{row['case']}\n```\n\n")
        parts.append("**YOUR LABEL (F or N):** ______\n\n")
    parts.append(
        FOOTER_TEMPLATE.format(
            seed=stats["seed"],
            n_rows=stats["n_rows"],
            pool_size=stats["pool_size"],
            n_subjects=stats["n_subjects"],
            rubric=RUBRIC_SHA256,
        )
    )
    text = "".join(parts)

    for banned in ("FOLLOW-UP", "NEW-TOPIC", "canonical_id"):
        if banned in text:
            raise AssertionError(f"sheet leaked {banned!r}")
    SHEET.write_text(text)


def write_key(rows: list[dict], stats: dict) -> None:
    payload = {
        "purpose": "Answer key for the H6 classifier trust gate (Amendment 2 B2.2). "
        "Do not open until the owner has finished labelling h6_audit_sheet.md.",
        "generated_by": "experiments/h6_audit_sample.py",
        "seed": stats["seed"],
        "rubric_sha256": RUBRIC_SHA256,
        "records_path": "results/stage2_pilot/records/classify.jsonl",
        "sampling": {
            "eligible_pool": "source == 'model' and not parse_failure and not "
            "missing_completion, from results/stage2_pilot/records/classify.jsonl",
            "excluded_rule_labels": "271 rows with source == 'rule' (NEW-TOPIC by "
            "SPEC D9 definition, no model call) are not auditable and are excluded",
            "balance_rule": "even split across labels, then across subjects, each "
            "cell capped by supply, deficit given to the subject with the most "
            "unused rows",
            "min_turn_gap": f"no two sampled rows from one transcript are within "
            f"{MIN_TURN_GAP} turn indices, so no turn appears both as a TARGET to "
            f"label and as the PREV of another row",
        },
        "achieved": {
            k: stats[k]
            for k in (
                "n_rows",
                "n_subjects",
                "subjects",
                "pool_size",
                "min_turn_gap",
                "achieved_by_label",
                "achieved_by_subject",
                "achieved_by_subject_label",
                "pool_supply_by_subject_label",
            )
        },
        "shortfall": {
            "b2_2_requires_subjects": 10,
            "subjects_available": stats["n_subjects"],
            "compliant": stats["n_subjects"] >= 10,
            "reason": "The classifier has only ever been run on the 6 dev subjects. "
            "B3 and Addendum A keep confirmatory subjects untouched by all Stage 2 "
            "machinery until the bar-lock addendum is committed, and that addendum's "
            "precondition 5 is this trust gate. Sampling >= 10 subjects would require "
            "running the classifier on confirmatory subjects first, which the "
            "pre-registration forbids. Rows were raised from 100 to 120 to partly "
            "offset the narrower subject base. Whether this clears B2.2 is an owner "
            "decision; it is a documented deviation either way.",
        },
        "key": [
            {
                "row": r["row"],
                "classifier_label": r["label"],
                "canonical_id": r["canonical_id"],
                "transcript_id": r["transcript_id"],
                "turn_idx": r["turn_idx"],
                "record_idx": r["idx"],
                "source_record": f"results/stage2_pilot/records/classify.jsonl:{r['record_line']}",
            }
            for r in rows
        ],
    }
    KEY.write_text(json.dumps(payload, indent=1) + "\n")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pool = load_pool()
    rows, stats = draw(pool)
    write_sheet(rows, stats)
    write_key(rows, stats)

    print(f"pool: {stats['pool_size']} model classifications, "
          f"{stats['n_subjects']} subjects")
    print(f"drew: {stats['n_rows']} rows, seed {stats['seed']}")
    print(f"by label:   {stats['achieved_by_label']}")
    print(f"by subject: {stats['achieved_by_subject']}")
    if stats["n_subjects"] < 10:
        print(f"SHORTFALL: B2.2 wants >= 10 subjects, only "
              f"{stats['n_subjects']} exist (dev subjects only)")
    print(f"wrote: {SHEET.relative_to(REPO)}")
    print(f"wrote: {KEY.relative_to(REPO)}")


if __name__ == "__main__":
    main()
