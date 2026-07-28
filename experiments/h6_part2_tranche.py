#!/usr/bin/env python3
"""Build the part-2 blind audit tranche for the H6 classifier trust gate.

Addendum A precondition 5 part 2, binding: after the classifier first runs on
confirmatory subjects, a second blind audit tranche of **>= 60 labels drawn
from >= 10 confirmatory subjects** goes to the owner BEFORE any confirmatory
H6 scoring -- same blind format as part 1, same trust bar (raw >= 0.85,
Cohen's kappa >= 0.60). Failing it halts H6 scoring pending rubric revision.

Two files come out, mirroring the part-1 precedent
(``experiments/h6_audit_sample.py``):

* ``results/stage2_openended/h6_part2_sheet.md`` -- BLIND. Row number, the
  exact PREV/GUEST/TARGET evidence the classifier saw, and an empty field for
  the co-auditor's label. No classifier label, no reasoning, no provenance.
* ``results/stage2_openended/h6_part2_key.json`` -- the sealed key. Row -> the
  classifier's label and the record it came from.

What is different from part 1, and why
--------------------------------------
1. **Subject supply is no longer the binding constraint.** Part 1 could only
   reach 6 subjects (dev only) and over-sampled rows to 120 to compensate. Here
   89 confirmatory subjects are available, so the >= 10-subject floor clears
   with room and the row count sits at the pre-registered floor unless the
   caller raises it with ``--rows``.
2. **Subject order for the even split is seeded-shuffled, not lexicographic.**
   With 6 subjects and 120 rows part 1 used every subject, so remainder order
   never mattered. With 89 subjects and 60 rows only some subjects can be
   drawn, and taking "the lexicographically first N" would make the tranche a
   function of canonical_id ordering rather than a sample. The shuffle is
   seeded, so the draw is still exactly reproducible.

Everything else is carried over unchanged: only ``source == "model"`` rows are
auditable (rule rows are NEW-TOPIC by definition and would measure the
definition, not the rubric); dropped turns are not judgements and are excluded;
no two rows from one transcript sit within ``MIN_TURN_GAP`` turn indices, so no
turn is ever both a TARGET to label and the PREV of another row.

Pure stdlib, no network, no model calls, deterministic given SEED.

Run:  .venv/bin/python experiments/h6_part2_tranche.py
"""

from __future__ import annotations

import argparse
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
# Parameters
# --------------------------------------------------------------------------

#: Sampling seed for the part-2 draw. Distinct from every seed already spent:
#: 47 (dev-subject draw), 49 (pilot item sampler), 61 (part-1 H6 audit),
#: 63 (declared-unused in the B3 measurement), 611/613 (open-ended re-tranches).
SEED = 62

#: Pre-registered floor: >= 60 labels. Raise with --rows if the owner wants a
#: tighter read on the 20% / 35% FOLLOW-UP overturn tripwire; supply is ample.
N_TOTAL_DEFAULT = 60

#: Same as part 1. A case renders as host(N) / guest(N+1) / host(N+2), so its
#: PREV is the host turn two back; a gap of 3 stops any turn appearing both as
#: a TARGET to judge and as another row's PREV.
MIN_TURN_GAP = 3

#: Floor from Addendum A precondition 5 part 2.
MIN_SUBJECTS = 10

CLASSIFY_DIR = REPO / "results/stage2_confirm/h6_classify"
RECORDS = CLASSIFY_DIR / "records/classify.jsonl"
PROMPTS = CLASSIFY_DIR / "exports/prompts_classify.jsonl"
META = CLASSIFY_DIR / "exports/meta_classify.jsonl"
STATS = CLASSIFY_DIR / "stats.json"

DEV_SUBJECTS = REPO / "results/stage2_pilot/dev_subjects.json"
PART1_KEY = REPO / "results/stage2_openended/h6_audit_key.json"

OUT_DIR = REPO / "results/stage2_openended"
SHEET = OUT_DIR / "h6_part2_sheet.md"
KEY = OUT_DIR / "h6_part2_key.json"


def read_jsonl(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def case_text(prompt: str) -> str:
    """The PREV/GUEST/TARGET block, sliced out of the rendered prompt.

    Taken from the prompt rather than re-derived from the transcripts, so the
    co-auditor judges byte-for-byte the same evidence the classifier saw --
    same 60/120/120-word truncations, same "..." marks. Bounded by two frozen
    constants, which also excludes the rubric's few-shot examples and their
    LABEL lines.
    """
    start = prompt.index(CASE_HEADER) + len(CASE_HEADER)
    end = prompt.index(OUTPUT_INSTRUCTION)
    block = prompt[start:end].strip()
    if "LABEL:" in block:
        raise AssertionError("case block leaked a LABEL line")
    return block


# --------------------------------------------------------------------------
# Pool
# --------------------------------------------------------------------------


def load_pool() -> tuple[list[dict], dict]:
    records = read_jsonl(RECORDS)
    prompts = {row["idx"]: row["prompt"] for row in read_jsonl(PROMPTS)}
    meta_by_key = {(m["canonical_id"], m["transcript_id"], m["turn_idx"]): m
                   for m in read_jsonl(META)}

    dev = json.loads(DEV_SUBJECTS.read_text())
    dev_ids = {s["canonical_id"] for s in dev["subjects"]}
    part1 = json.loads(PART1_KEY.read_text())
    part1_rows = {(r["canonical_id"], r["transcript_id"], r["turn_idx"])
                  for r in part1["key"]}

    pool: list[dict] = []
    excluded = {"rule": 0, "unlabelled": 0, "duplicate_case": 0}
    seen_cases: set[str] = set()

    for line_no, rec in enumerate(records, start=1):
        if rec.get("source") != "model":
            excluded["rule"] += 1
            continue
        if rec.get("label") is None or rec.get("parse_failure") \
                or rec.get("missing_completion"):
            excluded["unlabelled"] += 1
            continue
        key = (rec["canonical_id"], rec["transcript_id"], rec["turn_idx"])
        if rec["canonical_id"] in dev_ids:
            raise AssertionError(f"dev subject {rec['canonical_id']} in the "
                                 "confirmatory classifier records")
        if key in part1_rows:
            raise AssertionError(f"{key} was already audited in part 1")
        meta = meta_by_key.get(key)
        if meta is None:
            raise AssertionError(f"no meta row for {key}")
        if meta["prompt_sha256"] != rec["prompt_sha256"]:
            raise AssertionError(f"prompt hash disagrees for {key}")
        case = case_text(prompts[meta["idx"]])
        # 19 confirmatory prompts are byte-identical to another prompt. Two
        # sheet rows showing the same text would be one judgement counted
        # twice, so only the first occurrence is auditable.
        if case in seen_cases:
            excluded["duplicate_case"] += 1
            continue
        seen_cases.add(case)
        pool.append({
            "record_line": line_no,
            "canonical_id": rec["canonical_id"],
            "transcript_id": rec["transcript_id"],
            "turn_idx": rec["turn_idx"],
            "label": rec["label"],
            "case": case,
            "key": key,
        })

    pool.sort(key=lambda r: (r["canonical_id"], r["transcript_id"], r["turn_idx"]))
    for i, row in enumerate(pool):
        row["pool_pos"] = i
    return pool, excluded


# --------------------------------------------------------------------------
# Allocation and draw
# --------------------------------------------------------------------------


def allocate(supply: dict[str, int], quota: int, order: list[str]) -> dict[str, int]:
    """Spread ``quota`` draws over subjects as evenly as supply allows.

    Same shape as part 1: even split first (remainder to the first subjects in
    ``order``), every cell capped at its supply, then the deficit handed one
    row at a time to whichever subject has the most unused rows left. The one
    change is that ``order`` is the caller's seeded permutation rather than
    lexicographic -- see the module docstring.
    """
    base, rem = divmod(quota, len(order))
    target = {s: base + (1 if i < rem else 0) for i, s in enumerate(order)}

    deficit = 0
    for s in order:
        if target[s] > supply[s]:
            deficit += target[s] - supply[s]
            target[s] = supply[s]

    rank = {s: i for i, s in enumerate(order)}
    while deficit > 0:
        headroom = {s: supply[s] - target[s] for s in order}
        candidates = [s for s in order if headroom[s] > 0]
        if not candidates:
            break
        best = min(candidates, key=lambda s: (-headroom[s], rank[s]))
        target[best] += 1
        deficit -= 1
    return target


def draw(pool: list[dict], n_total: int) -> tuple[list[dict], dict]:
    """Balanced by label, spread over subjects, gap-respecting, seeded."""
    rng = random.Random(SEED)
    subjects = sorted({r["canonical_id"] for r in pool})
    order = list(subjects)
    rng.shuffle(order)
    per_label = n_total // len(LABELS)

    picked: list[dict] = []
    chosen: set[int] = set()
    taken: dict[tuple[str, str], list[int]] = {}

    def fits(row: dict) -> bool:
        if row["pool_pos"] in chosen:
            return False
        key = (row["canonical_id"], row["transcript_id"])
        return all(abs(row["turn_idx"] - t) >= MIN_TURN_GAP
                   for t in taken.get(key, ()))

    def take(row: dict) -> None:
        taken.setdefault((row["canonical_id"], row["transcript_id"]), []).append(
            row["turn_idx"])
        chosen.add(row["pool_pos"])
        picked.append(row)

    plan: dict[str, dict[str, int]] = {}
    supply_by = {}
    # FOLLOW-UP first: it is the scarcer label, so it gets first claim on the
    # contested turn positions. Same order as part 1.
    for label in (FOLLOW_UP, NEW_TOPIC):
        cells = {
            s: sorted((r for r in pool
                       if r["canonical_id"] == s and r["label"] == label),
                      key=lambda r: (r["transcript_id"], r["turn_idx"]))
            for s in subjects
        }
        supply_by[label] = {s: len(v) for s, v in cells.items()}
        target = allocate(supply_by[label], per_label, order)

        got = {s: 0 for s in subjects}
        for s in order:
            if target[s] <= 0:
                continue
            for row in rng.sample(cells[s], len(cells[s])):
                if got[s] >= target[s]:
                    break
                if fits(row):
                    take(row)
                    got[s] += 1

        while sum(got.values()) < per_label:
            progressed = False
            for s in sorted(subjects, key=lambda s: (got[s], order.index(s))):
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
        plan[label] = {s: n for s, n in got.items() if n}

    rng.shuffle(picked)  # blind: row order must carry no signal
    for n, row in enumerate(picked, start=1):
        row["row"] = n

    for (cid, tid), turns in taken.items():
        ordered = sorted(turns)
        for a, b in zip(ordered, ordered[1:]):
            if b - a < MIN_TURN_GAP:
                raise AssertionError(f"gap rule violated in {cid}/{tid}: {a},{b}")

    drawn_subjects = sorted({r["canonical_id"] for r in picked})
    stats = {
        "seed": SEED,
        "min_turn_gap": MIN_TURN_GAP,
        "n_rows": len(picked),
        "n_rows_requested": n_total,
        "per_label_target": per_label,
        "achieved_by_label": {
            label: sum(1 for r in picked if r["label"] == label)
            for label in sorted(LABELS)},
        "n_subjects_drawn": len(drawn_subjects),
        "subjects_drawn": drawn_subjects,
        "n_subjects_in_pool": len(subjects),
        "pool_size": len(pool),
        "achieved_by_subject": {
            s: sum(1 for r in picked if r["canonical_id"] == s)
            for s in drawn_subjects},
        "achieved_by_subject_label": {label: plan[label] for label in sorted(LABELS)},
        "pool_supply_by_label": {
            label: sum(supply_by[label].values()) for label in sorted(LABELS)},
        "subject_order_seeded": order[:20],
    }
    return picked, stats


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

INSTRUCTIONS = """# H6 classifier audit sheet -- part 2 (confirmatory subjects)

**What this is.** A machine read {n} interviewer turns and sorted each one into
one of two boxes. Your job is to sort the same {n} turns yourself, without
seeing what the machine said. Afterwards we compare. If we agree often enough,
the machine's labels get used to build the H6 arms. If we don't, H6 scoring
stops and the instructions the machine was given get rewritten.

**This is the second of two checks.** The first one ran on the 6 development
people and passed. This one runs on the real study subjects, which is the check
that actually gates the science. The bar is the same as last time.

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
whoever is scoring it (rows marked `X` are dropped, and the check needs at
least 60 answered rows to count).

Text is cut to the same length the machine saw it, so `...` means words were
removed there. That is normal - judge what's shown.

## Coverage

These {n} rows come from **{n_subjects} different people**, drawn from a pool of
{pool_size} machine labels over {n_subjects_pool} study subjects. The plan asks
for at least 60 rows across at least 10 people, so this sheet clears both. None
of these rows appeared on the first sheet, and none of these people were used
in development.

---

"""

FOOTER_TEMPLATE = """
---

## Provenance

- Sampling seed: **{seed}**. Rebuild this exact sheet with
  `.venv/bin/python experiments/h6_part2_tranche.py`.
- Rows: **{n_rows}**, drawn from **{pool_size}** model classifications over
  **{n_subjects_pool}** confirmatory subjects; **{n_subjects}** subjects appear.
- Classifier: Gemma-4-31B-it, rubric hash (frozen) `{rubric}`
- Classifier records: `results/stage2_confirm/h6_classify/records/classify.jsonl`
- Answer key (do not open until finished):
  `results/stage2_openended/h6_part2_key.json`
"""


def write_sheet(rows: list[dict], stats: dict) -> None:
    parts = [INSTRUCTIONS.format(
        n=stats["n_rows"],
        n_subjects=stats["n_subjects_drawn"],
        n_subjects_pool=stats["n_subjects_in_pool"],
        pool_size=stats["pool_size"])]
    for row in rows:
        parts.append(f"### Row {row['row']}\n\n```\n{row['case']}\n```\n\n")
        parts.append("**YOUR LABEL (F or N):** ______\n\n")
    parts.append(FOOTER_TEMPLATE.format(
        seed=stats["seed"], n_rows=stats["n_rows"],
        pool_size=stats["pool_size"],
        n_subjects=stats["n_subjects_drawn"],
        n_subjects_pool=stats["n_subjects_in_pool"],
        rubric=RUBRIC_SHA256))
    text = "".join(parts)
    banned = ["FOLLOW-UP", "NEW-TOPIC", "canonical_id"]
    # Provenance must not be recoverable from the sheet either: no subject id
    # and no transcript id of any drawn row may appear in it.
    banned += sorted({r["canonical_id"] for r in rows})
    banned += sorted({r["transcript_id"] for r in rows})
    for token in banned:
        if token in text:
            raise AssertionError(f"sheet leaked {token!r}")
    SHEET.write_text(text)


def write_key(rows: list[dict], stats: dict, excluded: dict) -> None:
    payload = {
        "purpose": "Sealed answer key for the H6 classifier trust gate, part 2 "
                   "(Amendment 2 Addendum A precondition 5 part 2). Do not open "
                   "until the co-auditor has finished labelling "
                   "h6_part2_sheet.md.",
        "generated_by": "experiments/h6_part2_tranche.py",
        "seed": stats["seed"],
        "classifier": "Gemma-4-31B-it",
        "rubric_sha256": RUBRIC_SHA256,
        "records_path": "results/stage2_confirm/h6_classify/records/classify.jsonl",
        "trust_bar": {"raw_agreement": 0.85, "cohens_kappa": 0.60,
                      "on_failure": "H6 scoring halts pending rubric revision"},
        "tripwire": {
            "source": "H6/B3 appendix section 4.3(c), APPROVED 2026-07-28",
            "follow_up_overturn_gt_0_20": "pre-committed D_min = 3 sensitivity "
                                          "arm, both arms reported",
            "follow_up_overturn_gt_0_35": "H6 scoring halts pending rubric "
                                          "revision",
            "dev_part1_follow_up_overturn": 0.25},
        "sampling": {
            "eligible_pool": "source == 'model', label not null, no parse "
                             "failure, no missing completion",
            "excluded_rule_labels": "source == 'rule' rows are NEW-TOPIC by SPEC "
                                    "D9 definition (no guest answer behind the "
                                    "turn), cost no model call and involve no "
                                    "judgement; auditing them would measure the "
                                    "definition, not the rubric",
            "excluded_counts": excluded,
            "balance_rule": "even split across labels, then across a seeded "
                            "permutation of subjects, each cell capped by "
                            "supply, deficit to the subject with the most "
                            "unused rows",
            "min_turn_gap": f"no two sampled rows from one transcript are "
                            f"within {MIN_TURN_GAP} turn indices, so no turn "
                            f"appears both as a TARGET to label and as the PREV "
                            f"of another row",
            "disjoint_from_part1": "asserted at build time on (canonical_id, "
                                   "transcript_id, turn_idx)",
            "no_dev_subjects": "asserted at build time against "
                               "results/stage2_pilot/dev_subjects.json",
            "grounding_only": "every case comes from grounding_turns.jsonl; the "
                              "test interview is never classified or shown",
        },
        "achieved": {k: stats[k] for k in (
            "n_rows", "n_rows_requested", "per_label_target",
            "achieved_by_label", "n_subjects_drawn", "subjects_drawn",
            "n_subjects_in_pool", "pool_size", "min_turn_gap",
            "achieved_by_subject", "achieved_by_subject_label",
            "pool_supply_by_label")},
        "compliance": {
            "requires_rows": 60,
            "requires_subjects": MIN_SUBJECTS,
            "rows_ok": stats["n_rows"] >= 60,
            "subjects_ok": stats["n_subjects_drawn"] >= MIN_SUBJECTS,
            "balanced": len(set(stats["achieved_by_label"].values())) == 1,
        },
        "key": [{
            "row": r["row"],
            "classifier_label": r["label"],
            "canonical_id": r["canonical_id"],
            "transcript_id": r["transcript_id"],
            "turn_idx": r["turn_idx"],
            "source_record":
                f"results/stage2_confirm/h6_classify/records/classify.jsonl:"
                f"{r['record_line']}",
        } for r in rows],
    }
    KEY.write_text(json.dumps(payload, indent=1) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", type=int, default=N_TOTAL_DEFAULT,
                    help="total rows; must be even and >= 60")
    args = ap.parse_args()
    if args.rows < 60 or args.rows % 2:
        raise SystemExit("FATAL: --rows must be even and at least 60")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pool, excluded = load_pool()
    rows, stats = draw(pool, args.rows)
    write_sheet(rows, stats)
    write_key(rows, stats, excluded)

    print(f"pool: {stats['pool_size']} auditable model labels over "
          f"{stats['n_subjects_in_pool']} confirmatory subjects "
          f"(excluded: {excluded})")
    print(f"drew: {stats['n_rows']} rows, seed {stats['seed']}")
    print(f"by label:    {stats['achieved_by_label']}")
    print(f"subjects:    {stats['n_subjects_drawn']} "
          f"(floor {MIN_SUBJECTS})")
    if stats["n_rows"] < args.rows:
        print(f"SHORTFALL: asked for {args.rows} rows, supply gave "
              f"{stats['n_rows']}")
    if len(set(stats["achieved_by_label"].values())) != 1:
        print(f"SHORTFALL: labels are not balanced: "
              f"{stats['achieved_by_label']}")
    print(f"wrote: {SHEET.relative_to(REPO)}")
    print(f"wrote: {KEY.relative_to(REPO)}")


if __name__ == "__main__":
    main()
