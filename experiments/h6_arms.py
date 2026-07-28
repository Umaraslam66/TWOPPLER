#!/usr/bin/env python3
"""H6 arm construction on the CONFIRMATORY subjects: rich vs poor grounding.

CONFIRMATORY. This file builds the two H6 grounding arms and renders their
prompts. It renders and it STOPS: no API call, no GPU submission, no
generation. CPU only, $0.00.

The binding contract is ``results/stage2_openended/H6_B3_PARAM_SPEC_DRAFT.md``
(APPROVED by the owner 2026-07-28, with two rulings at the top), which fills
the H6 slot Amendment 2 B3 left to bar-lock. Every rule below is that
appendix's, quoted where it is applied:

* **Segment** -- one host turn plus the run of consecutive guest turns
  immediately after it, never split. A host turn with no guest reply keeps an
  empty reply and costs only its own words.
* **Chain** -- one NEW-TOPIC root plus the maximal run of FOLLOW-UP segments
  right after it in the same transcript. Depth = the number of FOLLOW-UP
  segments, root excluded. An unlabelled turn breaks the run. A FOLLOW-UP run
  with no root (rootless) is excluded from the rich arm.
* **RICH** -- every segment in a chain of depth >= 2, root included. Selection:
  whole chains deepest-first, ties by interview date descending, then
  transcript id, then root turn index; skip-not-stop; then top up from unused
  chain members newest first.
* **POOR** -- lone NEW-TOPIC segments (never a chain root, never inside any
  chain), newest first, skip-not-stop.
* **Both arms render chronologically** and are disjoint by construction.
* **Budgets** -- B = 1,000 words primary, B = 400 words as the dose check.
  Eligibility (B4.2): both arms fill to within +-5% of B.
* **Sensitivity arm (owner ruling 1, unconditional)** -- the root-excluded
  rich arm: follow-up turns only, roots dropped, same budgets, same selection
  discipline. Reported beside the registered contrast, never substituted.

Binding wording rule from the same ruling: the rich arm is
**"follow-up chains including their root"**, never "follow-up material". The
root share of rich-arm words is measured per subject and carried in the
manifest so the report can print it.

The D_min = 3 arm is NOT built. Its pre-commitment was conditional on the
part-2 FOLLOW-UP overturn rate exceeding 20%; the measured rate was 18.33%
(``results/stage2_openended/h6_part2_score_output.txt``), so the condition did
not fire.

Nothing here invents renderer behaviour. Selection is this file's; RENDERING is
``doppler.stage2_render.render_grounding`` and
``stage2_oe1.render_and_guard_open`` -- the same calls the confirmatory H1
render made, against the same frozen template, the same S1 scope, the same
guard set and the same generation config (temperature 0.0,
max_output_tokens 256, the 150-word instruction tail).

Outputs, all under ``results/stage2_confirm/h6/``::

    arms.json                     per-subject supply, fills, eligibility, flags
    items_confirm.jsonl           the H6-eligible subjects' items (H1's items)
    prompts/chunk_01.jsonl        API prompts (gemini-3.5-flash-lite)
    node/chunk_NN.prompts.jsonl   node prompts (Gemma-4-31B-it, Leonardo)
    node/chunk_NN.meta.jsonl      the join sidecar
    render_index.jsonl            every logical render -> (chunk, idx)
    render_manifest.json          the submission manifest
    grounding/<cid>.json          the rendered grounding block per arm

Chunking is by ARM GROUP, not by subject, and deliberately so: chunk_01 holds
the four arms both models generate (the registered contrast and the dose
check); chunk_02 holds the two root-excluded arms, which by the owner's
API-budget ruling run on the PRIMARY model only. Splitting them this way is
what lets the frozen embed/judge drivers see a complete chunk per model.

Run::

    .venv/bin/python experiments/h6_arms.py measure
    .venv/bin/python experiments/h6_arms.py render
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import stage2_oe1 as OE1  # noqa: E402
import stage2_pilot as P1  # noqa: E402

from doppler import oe_render as OE  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402
from doppler.followup_render import FOLLOW_UP, NEW_TOPIC  # noqa: E402

RESULTS_DIR = _ROOT / "results"
CONFIRM_DIR = RESULTS_DIR / "stage2_confirm"
H6_DIR = CONFIRM_DIR / "h6"
CLASSIFY_DIR = CONFIRM_DIR / "h6_classify"
DEV_SUBJECTS = RESULTS_DIR / "stage2_pilot/dev_subjects.json"

# --- the frozen H6/B3 parameters, APPROVED 2026-07-28 -----------------------

#: Appendix parameter 1 / 1b. Primary first: the report's registered contrast.
BUDGETS = (1000, 400)
BUDGET_PRIMARY = 1000
#: Appendix parameter 1, quoting Amendment 2 B2.3: "both arms filled to within
#: +-5% of B".
BUDGET_TOLERANCE = 0.05
#: Appendix parameter 2c.
D_MIN = 2
#: Appendix parameter 4b: a subject is analyzed separately when more than 60%
#: of its rich-arm words come from depth-2 chains.
BOUNDARY_DEPTH2_SHARE = 0.60
#: Appendix parameter 4a: unlabelable rate above which a subject is analyzed
#: separately.
FLAGGED_DROP_RATE = 0.05
#: The dev range of the root share of rich-arm words, for the report.
DEV_ROOT_SHARE_RANGE = (0.17, 0.45)

#: The rich arm is follow-up chains INCLUDING THEIR ROOT. Never
#: "follow-up material". Owner ruling 1, 2026-07-28.
RICH_WORDING = "follow-up chains including their root"

#: The arms, and the budget each one is filled to. ``base`` is the frozen
#: five-arm name each renders as: every H6 arm is an OWN-TWIN redacted arm
#: (Amendment 2 B6 -- "the H6 contrast itself is own-twin vs own-twin"), so
#: there is no imposter arm here.
ARMS = {
    "h6_rich_b1000":   {"kind": "rich",    "budget": 1000, "roots": True},
    "h6_poor_b1000":   {"kind": "poor",    "budget": 1000, "roots": True},
    "h6_rich_b400":    {"kind": "rich",    "budget": 400,  "roots": True},
    "h6_poor_b400":    {"kind": "poor",    "budget": 400,  "roots": True},
    "h6_richnr_b1000": {"kind": "rich_nr", "budget": 1000, "roots": False},
    "h6_richnr_b400":  {"kind": "rich_nr", "budget": 400,  "roots": False},
}
BASE_ARM = "twin_redacted"

#: chunk_01: both models. chunk_02: primary model only (owner API-budget
#: ruling -- the sensitivity arm is generated and scored on the PRIMARY model
#: only, and the report says so).
CHUNK_ARMS = {
    "chunk_01": ("h6_rich_b1000", "h6_poor_b1000",
                 "h6_rich_b400", "h6_poor_b400"),
    "chunk_02": ("h6_richnr_b1000", "h6_richnr_b400"),
}
BOTH_MODEL_CHUNKS = ("chunk_01",)

PRIMARY_MODEL = OE1.PRIMARY_MODEL
ROBUSTNESS_MODEL = OE1.ROBUSTNESS_MODEL
GEN_TEMPERATURE = OE1.GEN_TEMPERATURE
GEN_MAX_OUTPUT_TOKENS = OE.MAX_OUTPUT_TOKENS

BANNER = ("CONFIRMATORY H6. Rendered only; nothing here has been generated, "
          "judged or scored. No GPU submission, no API call, $0.00.")


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


def load_labels() -> tuple[dict, set, dict]:
    """(key -> label, keys the classifier could not label, per-subject drops).

    ``key`` is ``(canonical_id, transcript_id, turn_idx)``. Model labels and
    rule labels live in one records file; a model row whose label is None after
    the B4.3 retries is a DROP, and a drop breaks a chain rather than being
    guessed at.
    """
    rows = read_jsonl(CLASSIFY_DIR / "records/classify.jsonl")
    labels: dict = {}
    drops: set = set()
    per_subject: dict = defaultdict(lambda: {"model": 0, "dropped": 0})
    for row in rows:
        key = (row["canonical_id"], row["transcript_id"], int(row["turn_idx"]))
        label = row.get("label")
        if row.get("source") == "model":
            per_subject[row["canonical_id"]]["model"] += 1
            if label is None:
                drops.add(key)
                per_subject[row["canonical_id"]]["dropped"] += 1
                continue
        if label not in (FOLLOW_UP, NEW_TOPIC):
            raise fatal(f"{key}: unknown label {label!r}")
        labels[key] = label
    return labels, drops, dict(per_subject)


# ---------------------------------------------------------------------------
# Segments and chains -- the appendix's definitions, ported unchanged
# ---------------------------------------------------------------------------


def segments_for(cid: str) -> list[dict]:
    """One dict per host turn in a subject's grounding transcripts.

    Identical to ``experiments/h6_b3_measure.segments_for`` (the code the
    approved appendix was measured with), with the transcript's date and
    programme attached from the split so the block can be rendered.
    """
    base = CONFIRM_DIR / "subjects" / cid
    turns = read_jsonl(base / "grounding_turns.jsonl")
    split = json.loads((base / "split.json").read_text(encoding="utf-8"))

    meta = {g["transcript_id"]: g for g in split.get("grounding", [])}
    test_tid = (split.get("test") or {}).get("transcript_id")

    by_transcript: dict[str, list[dict]] = defaultdict(list)
    for t in turns:
        by_transcript[t["transcript_id"]].append(t)
    if test_tid and test_tid in by_transcript:
        raise fatal(f"{cid}: the test transcript {test_tid} appears in the "
                    "grounding turns -- the test interview must never enter "
                    "grounding")

    out = []
    for tid, rows in by_transcript.items():
        rows.sort(key=lambda r: r["turn_idx"])
        entry = meta.get(tid, {})
        for i, row in enumerate(rows):
            if row.get("role") != "host":
                continue
            host_text = (row.get("text") or "").strip()
            if not host_text:
                continue
            reply = []
            for nxt in rows[i + 1:]:
                if nxt.get("role") != "guest":
                    break
                txt = (nxt.get("text") or "").strip()
                if txt:
                    reply.append(txt)
            guest_text = " ".join(reply)
            out.append({
                "canonical_id": cid,
                "transcript_id": tid,
                "turn_idx": int(row["turn_idx"]),
                "date": entry.get("date", ""),
                "program": entry.get("program", ""),
                "host_text": host_text,
                "guest_text": guest_text,
                "words": R.word_count(host_text) + R.word_count(guest_text),
            })
    out.sort(key=lambda s: (s["date"], s["transcript_id"], s["turn_idx"]))
    return out


def attach_labels(segs: list[dict], labels: dict, drops: set) -> None:
    for s in segs:
        key = (s["canonical_id"], s["transcript_id"], s["turn_idx"])
        s["label"] = labels.get(key)
        s["dropped"] = key in drops


def chains_for(segs: list[dict]) -> list[dict]:
    """Chains under the approved definition (appendix parameter 2b).

    Ported from ``experiments/h6_b3_measure.chains_for``: a chain is one
    NEW-TOPIC root plus the maximal run of FOLLOW-UP segments immediately after
    it in the same transcript; an unlabelled turn breaks the run; a run with no
    root is ROOTLESS and is excluded from the rich arm.
    """
    out = []
    by_transcript: dict[str, list[dict]] = defaultdict(list)
    for s in segs:
        by_transcript[s["transcript_id"]].append(s)

    for tid, rows in by_transcript.items():
        rows.sort(key=lambda r: r["turn_idx"])
        i = 0
        while i < len(rows):
            if rows[i].get("label") != FOLLOW_UP or rows[i]["dropped"]:
                i += 1
                continue
            j = i
            while (j < len(rows) and rows[j].get("label") == FOLLOW_UP
                   and not rows[j]["dropped"]):
                j += 1
            run = rows[i:j]
            root = None
            if (i > 0 and rows[i - 1].get("label") == NEW_TOPIC
                    and not rows[i - 1]["dropped"]):
                root = rows[i - 1]
            members = ([root] if root else []) + run
            out.append({
                "transcript_id": tid,
                "date": run[0]["date"],
                "root_turn_idx": root["turn_idx"] if root else None,
                "rootless": root is None,
                "depth": len(run),
                "root": root,
                "followups": run,
                "members": members,
                "words": sum(m["words"] for m in members),
                "followup_words": sum(m["words"] for m in run),
                "root_words": root["words"] if root else 0,
            })
            i = j
    return out


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def _newest_first(segs: list[dict]) -> list[dict]:
    """Most recent first: date desc, transcript id desc, turn index desc.

    Same reading ``stage2_render.render_grounding`` uses for its own
    most-recent-first fill, so H6 inherits the tested ordering rather than
    inventing one.
    """
    return sorted(segs, key=lambda s: (s["date"], s["transcript_id"],
                                       s["turn_idx"]), reverse=True)


def _chain_order(chains: list[dict], dates: list[str]) -> list[dict]:
    """Deepest chain first; ties by date DESC, then transcript id, then root.

    The date rank is precomputed because a descending string cannot be mixed
    with ascending fields in one sort key.
    """
    rank = {d: i for i, d in enumerate(sorted(set(dates), reverse=True))}
    return sorted(
        chains,
        key=lambda c: (-c["depth"], rank.get(c["date"], len(rank)),
                       c["transcript_id"],
                       -1 if c["root_turn_idx"] is None else c["root_turn_idx"]),
    )


def _fill(candidates: list[dict], budget: int) -> tuple[list[dict], int]:
    """Skip-not-stop greedy fill: take what fits, keep walking."""
    kept, used = [], 0
    for seg in candidates:
        if used + seg["words"] <= budget:
            kept.append(seg)
            used += seg["words"]
    return kept, used


def select_rich(chains: list[dict], budget: int, *,
                roots: bool = True) -> tuple[list[dict], int]:
    """The rich arm at one budget.

    Whole chains of depth >= D_MIN, deepest first, skip-not-stop; then a top-up
    pass over the chain members that pass left unused, newest first. With
    ``roots=False`` the same discipline runs over follow-up turns only -- the
    root-excluded sensitivity arm of owner ruling 1.
    """
    qualifying = [c for c in chains
                  if c["depth"] >= D_MIN and not c["rootless"]]
    dates = [c["date"] for c in qualifying]

    def members(chain):
        return chain["members"] if roots else chain["followups"]

    kept: list[dict] = []
    used = 0
    taken: set = set()
    for chain in _chain_order(qualifying, dates):
        block = members(chain)
        cost = sum(m["words"] for m in block)
        if not block or used + cost > budget:
            continue                      # skip, do not stop
        kept.extend(block)
        used += cost
        taken.update((m["transcript_id"], m["turn_idx"]) for m in block)

    leftovers = [m for c in qualifying for m in members(c)
                 if (m["transcript_id"], m["turn_idx"]) not in taken]
    for seg in _newest_first(leftovers):
        if used + seg["words"] <= budget:
            kept.append(seg)
            used += seg["words"]
    return kept, used


def lone_new_topics(segs: list[dict], chains: list[dict]) -> list[dict]:
    """NEW-TOPIC segments that are neither a chain root nor inside any chain."""
    in_chain = {(m["transcript_id"], m["turn_idx"])
                for c in chains for m in c["members"]}
    return [s for s in segs
            if s.get("label") == NEW_TOPIC and not s["dropped"]
            and (s["transcript_id"], s["turn_idx"]) not in in_chain]


def select_poor(lone: list[dict], budget: int) -> tuple[list[dict], int]:
    """The poor arm at one budget: lone new-topic segments, newest first."""
    return _fill(_newest_first(lone), budget)


# ---------------------------------------------------------------------------
# Rendering a selection
# ---------------------------------------------------------------------------


def render_block(selected: list[dict]) -> tuple[str, int]:
    """A selection -> the frozen renderer's grounding block, chronological.

    Selection has already happened; ``render_grounding`` is called with a
    budget equal to the selection's own word count, so its greedy fill keeps
    everything handed to it and the only thing it decides is LAYOUT -- the
    chronological order, the interview headers and the HOST/GUEST lines. That
    is the same separation H1 uses: selection order and render order are
    different things.
    """
    if not selected:
        raise fatal("render_block got an empty selection")
    by_tid: dict[str, list[dict]] = defaultdict(list)
    for seg in selected:
        by_tid[seg["transcript_id"]].append(seg)

    segments = []
    for tid in sorted(by_tid, key=lambda t: (by_tid[t][0]["date"], t)):
        rows = sorted(by_tid[tid], key=lambda s: s["turn_idx"])
        segments.append({
            "transcript_id": tid,
            "date": rows[0]["date"],
            "program": rows[0]["program"],
            "exchanges": [{"host_text": s["host_text"],
                           "guest_text": s["guest_text"]} for s in rows],
        })
    total = sum(s["words"] for s in selected)
    block = R.render_grounding(segments, budget_words=total)
    return block, total


# ---------------------------------------------------------------------------
# Per-subject build
# ---------------------------------------------------------------------------


def build_subject(cid: str, labels: dict, drops: set, drop_stats: dict) -> dict:
    segs = segments_for(cid)
    attach_labels(segs, labels, drops)
    chains = chains_for(segs)
    lone = lone_new_topics(segs, chains)
    qualifying = [c for c in chains if c["depth"] >= D_MIN and not c["rootless"]]

    stats = drop_stats.get(cid, {"model": 0, "dropped": 0})
    drop_rate = (stats["dropped"] / stats["model"]) if stats["model"] else 0.0

    row: dict = {
        "canonical_id": cid,
        "n_host_turns": len(segs),
        "n_labelled": sum(1 for s in segs if s.get("label") and not s["dropped"]),
        "n_followup": sum(1 for s in segs if s.get("label") == FOLLOW_UP
                          and not s["dropped"]),
        "n_new_topic": sum(1 for s in segs if s.get("label") == NEW_TOPIC
                           and not s["dropped"]),
        "n_dropped_turns": stats["dropped"],
        "n_model_calls": stats["model"],
        "drop_rate": round(drop_rate, 6),
        "flag_unlabelable": drop_rate > FLAGGED_DROP_RATE,
        "n_chains": len(chains),
        "n_chains_rootless": sum(1 for c in chains if c["rootless"]),
        "n_chains_qualifying": len(qualifying),
        "depth_histogram": {str(d): sum(1 for c in chains if c["depth"] == d)
                            for d in sorted({c["depth"] for c in chains})},
        "supply_rich_words": sum(c["words"] for c in qualifying),
        "supply_rich_noroot_words": sum(c["followup_words"] for c in qualifying),
        "supply_poor_words": sum(s["words"] for s in lone),
        "supply_rich_segments": sum(len(c["members"]) for c in qualifying),
        "supply_poor_segments": len(lone),
        "followup_density": (
            round(sum(1 for s in segs if s.get("label") == FOLLOW_UP
                      and not s["dropped"])
                  / max(sum(1 for s in segs
                            if s.get("label") and not s["dropped"]), 1), 6)),
        "budgets": {},
        "selections": {},
    }

    for budget in BUDGETS:
        rich, rich_words = select_rich(chains, budget, roots=True)
        poor, poor_words = select_poor(lone, budget)
        nr, nr_words = select_rich(chains, budget, roots=False)

        root_keys = {(c["root"]["transcript_id"], c["root"]["turn_idx"])
                     for c in qualifying if c["root"]}
        root_words = sum(s["words"] for s in rich
                         if (s["transcript_id"], s["turn_idx"]) in root_keys)
        depth2_keys = {(m["transcript_id"], m["turn_idx"])
                       for c in qualifying if c["depth"] == 2
                       for m in c["members"]}
        depth2_words = sum(s["words"] for s in rich
                           if (s["transcript_id"], s["turn_idx"]) in depth2_keys)

        lo = (1.0 - BUDGET_TOLERANCE) * budget
        eligible = rich_words >= lo and poor_words >= lo
        nr_eligible = eligible and nr_words >= lo

        row["budgets"][str(budget)] = {
            "budget": budget,
            "rich_words": rich_words,
            "poor_words": poor_words,
            "rich_noroot_words": nr_words,
            "rich_fill": round(rich_words / budget, 4),
            "poor_fill": round(poor_words / budget, 4),
            "rich_noroot_fill": round(nr_words / budget, 4),
            "rich_segments": len(rich),
            "poor_segments": len(poor),
            "rich_noroot_segments": len(nr),
            "eligible": eligible,
            "eligible_reason": (
                None if eligible else
                "; ".join(
                    ([] if rich_words >= lo else
                     [f"rich arm fills {rich_words}/{budget} "
                      f"({rich_words / budget:.2f}), under 0.95"]) +
                    ([] if poor_words >= lo else
                     [f"poor arm fills {poor_words}/{budget} "
                      f"({poor_words / budget:.2f}), under 0.95"]))),
            "sensitivity_eligible": nr_eligible,
            "root_words_in_rich": root_words,
            "root_share_of_rich": (round(root_words / rich_words, 4)
                                   if rich_words else None),
            "depth2_words_in_rich": depth2_words,
            "depth2_share_of_rich": (round(depth2_words / rich_words, 4)
                                     if rich_words else None),
            "flag_boundary_risk": bool(
                rich_words and depth2_words / rich_words > BOUNDARY_DEPTH2_SHARE),
            "arms_disjoint": not (
                {(s["transcript_id"], s["turn_idx"]) for s in rich}
                & {(s["transcript_id"], s["turn_idx"]) for s in poor}),
        }
        row["selections"][str(budget)] = {"rich": rich, "poor": poor,
                                          "rich_nr": nr}
    return row


# ---------------------------------------------------------------------------
# Measure
# ---------------------------------------------------------------------------


def survivors_with_items() -> tuple[list[str], dict]:
    """Confirmatory subjects that carry H1 items, and those items by subject."""
    items = read_jsonl(CONFIRM_DIR / "items_confirm.jsonl")
    by_subject: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        by_subject[it["canonical_id"]].append(it)
    dev = {s["canonical_id"]
           for s in json.loads(DEV_SUBJECTS.read_text())["subjects"]}
    leaked = sorted(set(by_subject) & dev)
    if leaked:
        raise fatal(f"dev subjects in the confirmatory item set: {leaked}")
    return sorted(by_subject), dict(by_subject)


def measure(write: bool = True) -> dict:
    labels, drops, drop_stats = load_labels()
    with_items, items_by_subject = survivors_with_items()

    build = json.loads((CONFIRM_DIR / "build_full140.json").read_text())
    all_survivors = sorted(s["canonical_id"] for s in build["subjects"]
                           if s.get("survived"))
    no_items = [c for c in all_survivors if c not in set(with_items)]

    rows = []
    for cid in all_survivors:
        try:
            row = build_subject(cid, labels, drops, drop_stats)
        except SystemExit:
            raise
        row["has_items"] = cid in set(with_items)
        row["n_items"] = len(items_by_subject.get(cid, []))
        rows.append(row)

    summary = {
        "banner": BANNER,
        "contract": ("results/stage2_openended/H6_B3_PARAM_SPEC_DRAFT.md, "
                     "APPROVED 2026-07-28"),
        "rich_arm_wording": RICH_WORDING,
        "d_min": D_MIN,
        "budgets": list(BUDGETS),
        "budget_tolerance": BUDGET_TOLERANCE,
        "n_survivors": len(all_survivors),
        "n_with_items": len(with_items),
        "subjects_without_items": no_items,
        "d_min_3_arm_built": False,
        "d_min_3_reason": (
            "The D_min = 3 sensitivity arm was pre-committed CONDITIONALLY: "
            "appendix 4.3(c) requires it only when the part-2 FOLLOW-UP "
            "overturn rate exceeds 20%. The measured rate is 18.33% "
            "(11/60), below the tripwire, so the condition did not fire and "
            "the arm is not built."),
        "per_subject": [],
        "eligibility": {},
        "generated_utc": now(),
    }

    for budget in BUDGETS:
        key = str(budget)
        elig = [r for r in rows if r["has_items"] and r["budgets"][key]["eligible"]]
        sens = [r for r in elig if r["budgets"][key]["sensitivity_eligible"]]
        excl = [r for r in rows if r["has_items"]
                and not r["budgets"][key]["eligible"]]
        rich_only = [r for r in excl
                     if r["budgets"][key]["rich_fill"] < 0.95
                     and r["budgets"][key]["poor_fill"] >= 0.95]
        poor_only = [r for r in excl
                     if r["budgets"][key]["poor_fill"] < 0.95
                     and r["budgets"][key]["rich_fill"] >= 0.95]
        both = [r for r in excl
                if r["budgets"][key]["rich_fill"] < 0.95
                and r["budgets"][key]["poor_fill"] < 0.95]
        shares = [r["budgets"][key]["root_share_of_rich"] for r in elig
                  if r["budgets"][key]["root_share_of_rich"] is not None]
        summary["eligibility"][key] = {
            "budget": budget,
            "n_eligible": len(elig),
            "eligible_ids": [r["canonical_id"] for r in elig],
            "n_excluded": len(excl),
            "excluded_ids": [r["canonical_id"] for r in excl],
            "excluded_rich_only": [r["canonical_id"] for r in rich_only],
            "excluded_poor_only": [r["canonical_id"] for r in poor_only],
            "excluded_both": [r["canonical_id"] for r in both],
            "n_sensitivity_eligible": len(sens),
            "sensitivity_ids": [r["canonical_id"] for r in sens],
            "branch": branch_for(len(elig)),
            "n_items_eligible": sum(r["n_items"] for r in elig),
            "root_share_min": round(min(shares), 4) if shares else None,
            "root_share_median": (round(statistics.median(shares), 4)
                                  if shares else None),
            "root_share_max": round(max(shares), 4) if shares else None,
            "flag_boundary_risk_ids": [
                r["canonical_id"] for r in elig
                if r["budgets"][key]["flag_boundary_risk"]],
            "flag_unlabelable_ids": [r["canonical_id"] for r in elig
                                     if r["flag_unlabelable"]],
        }

    for r in rows:
        summary["per_subject"].append(
            {k: v for k, v in r.items() if k != "selections"})

    if write:
        H6_DIR.mkdir(parents=True, exist_ok=True)
        S.write_json(H6_DIR / "arms.json", summary)
    return summary


def branch_for(n: int) -> str:
    """Amendment 2 B3's subject-count branch, applied mechanically."""
    if n >= 80:
        return "confirmatory"
    if n >= 30:
        return "exploratory"
    return "descriptive"


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def render(argv_chunks=None) -> dict:
    labels, drops, drop_stats = load_labels()
    _with_items, items_by_subject = survivors_with_items()
    pool = {r["canonical_id"]: r for r in S.load_pool()}

    summary = measure(write=True)
    eligible_by_budget = {str(b): set(summary["eligibility"][str(b)]["eligible_ids"])
                          for b in BUDGETS}
    sens_by_budget = {str(b): set(summary["eligibility"][str(b)]["sensitivity_ids"])
                      for b in BUDGETS}
    all_eligible = sorted(set().union(*eligible_by_budget.values()))

    H6_DIR.mkdir(parents=True, exist_ok=True)
    (H6_DIR / "prompts").mkdir(exist_ok=True)
    (H6_DIR / "node").mkdir(exist_ok=True)
    (H6_DIR / "grounding").mkdir(exist_ok=True)

    rendered: list[dict] = []
    failures: list[dict] = []
    per_subject: dict[str, dict] = {}
    items_out: list[dict] = []

    for cid in all_eligible:
        row = build_subject(cid, labels, drops, drop_stats)
        variants = P1.name_variants(pool[cid])
        items = items_by_subject[cid]
        items_out.extend(items)
        blocks: dict[str, dict] = {}

        for arm, spec in ARMS.items():
            budget = str(spec["budget"])
            if spec["kind"] == "rich_nr":
                if cid not in sens_by_budget[budget]:
                    continue
                selection = row["selections"][budget]["rich_nr"]
            else:
                if cid not in eligible_by_budget[budget]:
                    continue
                selection = row["selections"][budget][
                    "rich" if spec["kind"] == "rich" else "poor"]
            block, words = render_block(selection)
            block = R.redact(block, variants)
            R.assert_redacted(block, variants)
            got = OE.grounding_speech_words(block)
            # Redaction collapses a multi-token name to the single token
            # ``GUEST``, so the rendered block can carry FEWER speech words
            # than the selection did. It can never carry more, and it can
            # never exceed the budget. Budget matching itself is judged on the
            # selection words -- the quantity the approved appendix measured
            # and froze the +-5% tolerance against -- and the post-redaction
            # number is recorded beside it rather than substituted for it.
            if got > words:
                raise fatal(f"{cid}/{arm}: rendered block carries {got} speech "
                            f"words, more than the {words} selected")
            if got > spec["budget"]:
                raise fatal(f"{cid}/{arm}: {got} words over the "
                            f"{spec['budget']}-word budget")
            blocks[arm] = {"block": block, "selection_words": words,
                           "words": got, "n_segments": len(selection),
                           "redaction_words_lost": words - got,
                           "block_sha256": R.sha256(block)}

        # Disjointness is a construction claim; prove it on the rendered arms.
        # The post-redaction word gap is measured here too: budget matching is
        # frozen on selection words, but if redaction pulled the two arms
        # apart by more than the same +-5% of B, the report says so.
        post_redaction_gaps = {}
        for budget in BUDGETS:
            rich_arm = f"h6_rich_b{budget}"
            poor_arm = f"h6_poor_b{budget}"
            if rich_arm in blocks and poor_arm in blocks:
                if blocks[rich_arm]["block"] == blocks[poor_arm]["block"]:
                    raise fatal(f"{cid}: rich and poor blocks are identical at "
                                f"B={budget}")
                gap = abs(blocks[rich_arm]["words"] - blocks[poor_arm]["words"])
                post_redaction_gaps[str(budget)] = {
                    "rich_rendered_words": blocks[rich_arm]["words"],
                    "poor_rendered_words": blocks[poor_arm]["words"],
                    "gap": gap,
                    "gap_over_tolerance": gap > BUDGET_TOLERANCE * budget,
                }

        for arm, built in blocks.items():
            for item in items:
                out = _guarded(arm, item, cid, pool[cid]["canonical_name"],
                               variants, built, failures)
                if out is not None:
                    rendered.append(out)

        per_subject[cid] = {
            "canonical_id": cid,
            "n_items": len(items),
            "arms": {a: {k: v for k, v in b.items() if k != "block"}
                     for a, b in blocks.items()},
            "post_redaction_gaps": post_redaction_gaps,
            "budgets": {k: v for k, v in row["budgets"].items()},
        }
        S.write_json(H6_DIR / "grounding" / f"{cid}.json", {
            "canonical_id": cid,
            "arms": {a: {"words": b["words"], "n_segments": b["n_segments"],
                         "block_sha256": b["block_sha256"], "block": b["block"]}
                     for a, b in blocks.items()},
        })

    if failures:
        raise fatal(f"{len(failures)} render guard failure(s); first: "
                    f"{failures[0]}")

    manifest = write_chunks(rendered, items_out, summary, per_subject)
    return manifest


def _guarded(arm: str, item: dict, cid: str, name: str, variants: list,
             built: dict, failures: list) -> dict | None:
    """One render with every H1 guard, plus H6's own budget guard."""
    spec = ARMS[arm]
    # ``items_confirm.jsonl`` is the render step's own item file: it keeps the
    # held-out answer under ``real_answer_verbatim``. The renderer's contract
    # is ``question`` / ``answer``. Mapped here, never rewritten on disk, so
    # H6 scores the SAME held-out items H1 scored.
    ritem = dict(item, answer=item["real_answer_verbatim"])
    try:
        out = OE1.render_and_guard_open(
            BASE_ARM, ritem, subject_name=name, subject_variants=variants,
            grounding_block=built["block"], donor_variants=None)
    except (SystemExit, ValueError, AssertionError, KeyError) as exc:
        failures.append({"canonical_id": cid, "item_id": item["item_id"],
                         "arm": arm, "guard": type(exc).__name__,
                         "reason": " ".join(str(exc).split())[:400]})
        return None

    prompt = out["prompt"]
    problems = []
    left = R.surviving_variants(prompt, variants)
    if left:
        problems.append(f"surviving name variants {sorted(set(left))[:3]}")
    if OE.forced_choice_residue(prompt):
        problems.append("forced-choice residue")
    if out["grounding_speech_words"] > spec["budget"]:
        problems.append(f"grounding {out['grounding_speech_words']} words over "
                        f"the {spec['budget']}-word budget")
    if out["instruction_tail_sha256"] != OE.INSTRUCTION_SHA256:
        problems.append("instruction tail is not the frozen tail")
    if problems:
        failures.append({"canonical_id": cid, "item_id": item["item_id"],
                         "arm": arm, "guard": "post_render_qa",
                         "reason": "; ".join(problems)})
        return None

    out.update({"item_id": item["item_id"], "canonical_id": cid, "arm": arm,
                "h6_kind": spec["kind"], "h6_budget": spec["budget"],
                "item_type": item["item_type"], "h7_bin": None,
                "cutoff_date": None, "delta_days": None, "donor_id": None})
    return out


API_FIELDS = ("idx", "chunk", "canonical_id", "item_id", "arm", "h6_kind",
              "h6_budget", "h7_bin", "cutoff_date", "delta_days", "item_type",
              "donor_id", "prompt_sha256", "prompt_words", "prompt_tokens_est",
              "grounding_speech_words", "max_output_tokens", "temperature",
              "model", "prompt")

NODE_META_FIELDS = ("idx", "item_id", "canonical_id", "arm", "h6_kind",
                    "h6_budget", "h7_bin", "cutoff_date", "delta_days",
                    "item_type", "prompt_sha256", "prompt_words",
                    "prompt_tokens_est")


def write_chunks(rendered: list[dict], items_out: list[dict], summary: dict,
                 per_subject: dict) -> dict:
    """Prompt files, node files, the join sidecars, and the manifest.

    Prompts are DEDUPED on ``prompt_sha256`` inside a chunk, exactly as the H1
    render deduped: two logical rows carrying byte-identical prompts are
    generated once and scored once, and ``render_index.jsonl`` re-attaches the
    logical rows afterwards. That cannot happen across arms here (the grounding
    differs), but a subject whose rich selection at B=1,000 equals its
    selection at B=400 would produce one -- so the guard runs rather than being
    argued away.
    """
    index_rows: list[dict] = []
    chunk_files: dict[str, list[dict]] = {}
    n_dupes = 0

    for chunk, arms in CHUNK_ARMS.items():
        rows = [r for r in rendered if r["arm"] in arms]
        rows.sort(key=lambda r: (r["canonical_id"], r["arm"], r["item_id"]))
        unique: dict[str, dict] = {}
        for r in rows:
            sha = r["prompt_sha256"]
            if sha not in unique:
                unique[sha] = dict(r, chunk=chunk, idx=len(unique))
            else:
                n_dupes += 1
            index_rows.append({
                "chunk": chunk, "idx": unique[sha]["idx"],
                "canonical_id": r["canonical_id"], "item_id": r["item_id"],
                "arm": r["arm"], "h6_kind": r["h6_kind"],
                "h6_budget": r["h6_budget"], "h7_bin": None,
                "prompt_sha256": sha,
            })
        chunk_files[chunk] = list(unique.values())

    for chunk, rows in chunk_files.items():
        node_prompts = [{"idx": r["idx"], "prompt": r["prompt"],
                         "max_output_tokens": GEN_MAX_OUTPUT_TOKENS}
                        for r in rows]
        S.write_jsonl(H6_DIR / "node" / f"{chunk}.prompts.jsonl", node_prompts)
        S.write_jsonl(H6_DIR / "node" / f"{chunk}.meta.jsonl",
                      [{k: r.get(k) for k in NODE_META_FIELDS} for r in rows])
        if chunk in BOTH_MODEL_CHUNKS:
            api_rows = [dict({k: r.get(k) for k in API_FIELDS},
                             model=ROBUSTNESS_MODEL,
                             temperature=GEN_TEMPERATURE,
                             max_output_tokens=GEN_MAX_OUTPUT_TOKENS)
                        for r in rows]
            S.write_jsonl(H6_DIR / "prompts" / f"{chunk}.jsonl", api_rows)

    S.write_jsonl(H6_DIR / "render_index.jsonl", index_rows)
    seen: dict[str, dict] = {}
    for it in items_out:
        seen[it["item_id"]] = it
    S.write_jsonl(H6_DIR / "items_confirm.jsonl",
                  [seen[k] for k in sorted(seen)])

    manifest = {
        "banner": BANNER,
        "contract": summary["contract"],
        "rich_arm_wording": RICH_WORDING,
        "d_min": D_MIN,
        "d_min_3_arm_built": False,
        "d_min_3_reason": summary["d_min_3_reason"],
        "arms": {a: dict(spec) for a, spec in ARMS.items()},
        "base_arm": BASE_ARM,
        "own_twin_only": ("Amendment 2 B6: the H6 contrast is own-twin vs "
                          "own-twin, so no imposter arm is built here."),
        "chunks": {c: {"arms": list(a),
                       "n_prompts": len(chunk_files[c]),
                       "models": ([PRIMARY_MODEL, ROBUSTNESS_MODEL]
                                  if c in BOTH_MODEL_CHUNKS
                                  else [PRIMARY_MODEL])}
                   for c, a in CHUNK_ARMS.items()},
        "sensitivity_primary_only": (
            "The root-excluded sensitivity arm is generated and scored on the "
            "PRIMARY model only, to conserve API budget. Stated in the report."),
        "n_logical_renders": len(index_rows),
        "n_unique_prompts": sum(len(v) for v in chunk_files.values()),
        "n_duplicate_prompt_rows": n_dupes,
        "n_items": len(seen),
        "n_subjects": len(per_subject),
        "eligibility": summary["eligibility"],
        "per_subject": per_subject,
        "generation": {"primary_model": PRIMARY_MODEL,
                       "robustness_model": ROBUSTNESS_MODEL,
                       "temperature": GEN_TEMPERATURE,
                       "max_output_tokens": GEN_MAX_OUTPUT_TOKENS,
                       "max_answer_words": OE.MAX_ANSWER_WORDS,
                       "instruction_tail_sha256": OE.INSTRUCTION_SHA256,
                       "template_sha256": OE.TEMPLATE_SHA256},
        "generated_utc": now(),
    }
    S.write_json(H6_DIR / "render_manifest.json", manifest)
    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_measure(summary: dict) -> None:
    print(f"\n=== H6 arm supply on the confirmatory subjects ===")
    print(f"survivors {summary['n_survivors']}, carrying items "
          f"{summary['n_with_items']}")
    if summary["subjects_without_items"]:
        print(f"no items at all: {summary['subjects_without_items']}")
    for budget in BUDGETS:
        e = summary["eligibility"][str(budget)]
        print(f"\nB = {budget}")
        print(f"  eligible (both arms within +-5%): {e['n_eligible']}  "
              f"-> branch {e['branch'].upper()}")
        print(f"  excluded: {e['n_excluded']}  "
              f"(rich-arm short {len(e['excluded_rich_only'])}, "
              f"poor-arm short {len(e['excluded_poor_only'])}, "
              f"both short {len(e['excluded_both'])})")
        print(f"  items over eligible subjects: {e['n_items_eligible']}")
        print(f"  sensitivity (root-excluded) eligible: "
              f"{e['n_sensitivity_eligible']}")
        print(f"  root share of rich-arm words: min {e['root_share_min']}, "
              f"median {e['root_share_median']}, max {e['root_share_max']} "
              f"(dev range {DEV_ROOT_SHARE_RANGE[0]}-{DEV_ROOT_SHARE_RANGE[1]})")
        print(f"  boundary-risk flags: {len(e['flag_boundary_risk_ids'])}  "
              f"unlabelable flags: {len(e['flag_unlabelable_ids'])}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("measure", "render"))
    args = ap.parse_args(argv)

    if args.command == "measure":
        print_measure(measure(write=True))
        return 0

    manifest = render()
    print_measure(json.loads((H6_DIR / "arms.json").read_text()))
    print(f"\n=== render ===")
    for chunk, info in manifest["chunks"].items():
        print(f"  {chunk}: {info['n_prompts']} prompts, arms {info['arms']}, "
              f"models {info['models']}")
    print(f"  logical renders {manifest['n_logical_renders']}, unique prompts "
          f"{manifest['n_unique_prompts']}, duplicates "
          f"{manifest['n_duplicate_prompt_rows']}")
    print(f"  items {manifest['n_items']}, subjects {manifest['n_subjects']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
