"""Stage 2 OPEN-ENDED dev pilot (OE-1) driver.

PILOT. Dev subjects only. Nothing here answers a pre-registered bar; the
confirmatory subjects are untouched by everything in this file.

Binding design: ``results/stage2_openended/PILOT_SPEC.md`` (owner-approved
2026-07-27), under ``PREREGISTRATION_AMENDMENT_3.md``. Contract lineage:
``results/stage2_pilot4/SPEC_v1.10.md`` — everything the spec does not change
carries over, and this driver reuses rounds 1-4's machinery rather than
restating it: the five D8 arms, the 2,000-word most-recent-first grounding
fill, the name redactor and its guards, the D7 imposter donors, the D6-v4.9
twin rule, the era checker and the cost log.

What OE-1 measures (spec section 0): whether the open-ended instrument
separates own-twin from imposter-twin on dev subjects, in the pre-registered
direction, on the primary model. It makes no claims. If separation fails,
Stage 2 pauses for a design review (Amendment 3 C4.3).

Subcommands
-----------
``build``          render the 85 prompts, export them, run the build QA.
                   Offline: no API, no GPU, no network. Costs nothing.
``gen-flashlite``  robustness generations on gemini-3.5-flash-lite (API).
``judge``          channel 2, the stance judge on gemini-3.5-flash (API).
``embed``          channel 1, four local CPU embedding candidates (no API).
``report``         the C4 validation-gate report in the section-7 format.

**Owner gate.** Everything after ``build`` spends money or node-hours and is
held behind the standing stop-before-GPU checkpoint: the build runs, then
STOPS for owner review of the rendered prompts and the costs. The Gemma job's
sbatch is written by ``build`` and is never submitted by this driver.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import stage2_pilot as P1  # noqa: E402
import stage2_pilot2 as P2  # noqa: E402
import stage2_pilot3 as P3  # noqa: E402
import stage2_pilot4 as P4  # noqa: E402

from doppler import counterfactuals as CF  # noqa: E402
from doppler import counterfactuals4 as C4  # noqa: E402
from doppler import oe_render as OE  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402
from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402

RESULTS_DIR = _ROOT / "results"
PILOT1_DIR = RESULTS_DIR / "stage2_pilot"
PILOT4_DIR = RESULTS_DIR / "stage2_pilot4"
OE_DIR = RESULTS_DIR / "stage2_openended"
SPEC_PATH = OE_DIR / "PILOT_SPEC.md"
COST_LOG = RESULTS_DIR / "cost_log.jsonl"

PILOT_BANNER = ("PILOT -- open-ended instrument validation on dev subjects; "
                "no research conclusions.")
CONTRACT = ("results/stage2_openended/PILOT_SPEC.md (Amendment 3), lineage "
            "results/stage2_pilot4/SPEC_v1.10.md")

SCORED_CLAIM = (
    "The claim scored is that the twin, asked the person's held-out question "
    "cold, produces a free-text reply that lands closer to what the person "
    "actually said than an imposter twin's reply does -- on embedding "
    "similarity (channel 1) and on stance match (channel 2). No forced choice "
    "is involved and no option set exists.")

# ---------------------------------------------------------------------------
# Models. None of these is chosen here; all four come from the spec.
# ---------------------------------------------------------------------------

#: Spec section 1: both scored models generate for every arm.
PRIMARY_MODEL = "Gemma-4-31B-it"          # Leonardo, the primary
ROBUSTNESS_MODEL = "gemini-3.5-flash-lite"  # API, secondary absolute scores
SCORED_MODELS = (PRIMARY_MODEL, ROBUSTNESS_MODEL, P2.MODEL_LABEL)

#: Spec section 4: generator-side family, never a scored model, different
#: version from the robustness scorer.
JUDGE_MODEL = "gemini-3.5-flash"

#: Spec section 3, in the spec's own order. ``housekeeping.json`` overrides
#: this list if it exists; it does not have to.
EMBED_CANDIDATES = (
    {"name": "sentence-transformers/all-mpnet-base-v2", "size": "110M",
     "role": "proposed primary"},
    {"name": "BAAI/bge-large-en-v1.5", "size": "335M", "role": "candidate"},
    {"name": "intfloat/e5-large-v2", "size": "335M",
     "role": "candidate; needs query:/passage: prefixes"},
    {"name": "sentence-transformers/all-MiniLM-L6-v2", "size": "22M",
     "role": "sanity check only; never the pinned channel"},
)
#: e5 is the one candidate that is not symmetric out of the box, and the spec
#: calls the prefixes "a footgun we pin down explicitly if chosen". Pinned:
#: the text being scored is the query, the reference text is the passage —
#: the same assignment ``housekeeping.json`` recorded when it smoke-tested the
#: four candidates.
E5_QUERY_PREFIX = "query: "
E5_PASSAGE_PREFIX = "passage: "

GEN_TEMPERATURE = OE.TEMPERATURE          # 0.0, both scored models
GEN_MAX_OUTPUT_TOKENS = OE.MAX_OUTPUT_TOKENS  # 256, both scored models
JUDGE_TEMPERATURE = 0.0

#: Owner decision 2026-07-27, after the v1 judge run: thinking EXPLICITLY
#: disabled, max_output_tokens 512, everything else unchanged. Rationale on
#: record: the rubric asks for a mechanical classification with an auditable
#: WHY line; hidden thinking is budget-unstable at temperature 0 (the v1 probe
#: in results/stage2_openended/judge/thinking_budget_probe.json flipped a label
#: between a 256 and a 1024 budget) and it defeats the owner's >=50-label
#: spot-check by truncating every WHY. These two become PINNED judge
#: parameters at bar-lock.
JUDGE_MAX_OUTPUT_TOKENS = 512
JUDGE_THINKING_BUDGET = 0

#: Spec section 6 caps. Overshoot stops the run and reports.
API_BUDGET_USD = 0.40
NODE_HOUR_BUDGET = 0.25

#: Hard ceiling on API calls for one invocation of an API subcommand.
DEFAULT_CALL_CAP = 400

#: Fixed and recorded (spec section 4): the judge's call order is randomized so
#: no arm sits in a block, and the shuffle is reproducible from this seed.
JUDGE_ORDER_SEED = 20260727

#: Leonardo. Its own run directory: OE-1 must never overwrite round 4's
#: completions on the node.
NODE_RUN = f"{P2.NODE_ROOT}/runs/stage2_oe1"
GEN_WALLTIME = "00:20:00"
GEN_QOS = P2.GATE_QOS
LEONARDO_SET = "oe1"

#: Spec section 9 / addendum item 6: the four frozen H7 staleness bins. This
#: pilot does not run H7; it reports each item's grounding-to-test delta as a
#: smoke check that the outcome variable computes per bin with no new
#: machinery.
DELTA_BINS = (
    ("6-12m", 183, 365),
    ("1-2y", 365, 730),
    ("2-3y", 730, 1095),
    (">3y", 1095, 10 ** 6),
)

ZEROINFO_PREAMBLE_NOTE = (
    "FLAGGED, NOT CHANGED. The frozen v1.10 zero-information preamble still "
    "reads 'Predict which answer they gave.', which is forced-choice wording "
    "in an open-ended prompt. PILOT_SPEC section 2 explicitly keeps every arm's "
    "existing preamble so the instruction tail stays byte-identical across "
    "arms, so this driver renders it unchanged. Rewording it is a bar-lock "
    "decision for the owner, not an implementation one.")

S1_NOTE = (
    "S1 (host-intro clause redaction, BARLOCK_MEASUREMENTS section 8.1) is "
    "applied to ALL FIVE arms, not only the three '*_redacted' ones. Applying "
    "it to the redacted arms alone would make a named arm differ from its "
    "redacted counterpart by more than the single name line, which is the "
    "one-factor invariant the contamination meter rests on. The build QA "
    "reports the check on the redacted arms as required. Note that rounds 1-4 "
    "did NOT apply S1 in their render path, so OE-1 prompts are not "
    "byte-comparable to round 4's on this dimension.")

TWIN_RULE = P4.TWIN_RULE
assert_no_cross_visible_twins = P4.assert_no_cross_visible_twins


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


def rel(path: Path) -> str:
    return P1.rel(path)


def safe_id(item_id: str) -> str:
    return item_id.replace(":", "_")


def _mmm(values, digits: int = 2) -> dict:
    """n / min / mean / max. ``digits`` because a cosine mean rounded to 2
    decimals throws away most of an own-minus-imposter difference."""
    vals = [v for v in values if v is not None]
    if not vals:
        return {"n": 0, "min": None, "mean": None, "max": None}
    return {"n": len(vals), "min": min(vals),
            "mean": round(sum(vals) / len(vals), digits), "max": max(vals)}


# ---------------------------------------------------------------------------
# Items, subjects, donors
# ---------------------------------------------------------------------------


def all_items(pilot1_dir: Path) -> list[dict]:
    """The 17 D4-eligible Q-A items over the 5 Q-A dev subjects (spec 5).

    C00292 stays excluded: ``prediction_subjects`` filters on the
    ``burned_for_qa`` annotation, not on the id.
    """
    return P3.all_items(pilot1_dir)


def _days_between(later: str, earlier: str):
    try:
        a = date.fromisoformat(str(later)[:10])
        b = date.fromisoformat(str(earlier)[:10])
    except (TypeError, ValueError):
        return None
    return (a - b).days


def delta_bin(days) -> str | None:
    if days is None:
        return None
    for name, lo, hi in DELTA_BINS:
        if lo <= days < hi:
            return name
    return "<6m"


def item_type_map(pilot4_dir: Path, items: list[dict]) -> dict:
    """Item type per item id, with the source of each call recorded.

    ``results/stage2_pilot4/item_types.json`` is the hand-final classification
    the spec names, but it covers the 15 items round 3 BUILT, not all 17 D4
    items. The two items it does not reach get the documented cue rule
    (``counterfactuals4.classify_question``) instead, flagged as such: a rule
    tuned on these same dev questions is a cross-check, not independent
    evidence, and it must not pass silently as a hand call.
    """
    hand = {}
    path = pilot4_dir / "item_types.json"
    if path.exists():
        doc = json.loads(path.read_text(encoding="utf-8"))
        for row in doc.get("items", []):
            if row.get("hand_kind"):
                hand[row["item_id"]] = row["hand_kind"]
    out = {}
    for item in items:
        iid = item["item_id"]
        if iid in hand:
            out[iid] = {"kind": hand[iid], "source": "hand_final_pilot4"}
        else:
            rule = C4.classify_question(item["question"])
            out[iid] = {"kind": rule["kind"], "source": "cue_rule_fallback",
                        "rule": rule}
    return out


def subject_blocks(pilot1_dir: Path) -> dict:
    """Per Q-A dev subject: name, variants, both grounding blocks, dates.

    The twin block is the subject's own grounding, redacted with the subject's
    variants; the imposter block is the D7 donor's grounding, redacted with the
    DONOR's variants. Both come from the committed artifacts, so the donor
    assignment is exactly the one rounds 1-4 used — nothing is re-drawn here.
    """
    pool = P1.pool_rows()
    pairs = P1.imposter_pairs(pilot1_dir / "imposter_pairs.json")
    dev_ids = {s["canonical_id"] for s in P1.dev_subjects(pilot1_dir)}
    out = {}
    for subject in P1.prediction_subjects(P1.dev_subjects(pilot1_dir)):
        cid = subject["canonical_id"]
        if subject.get("burned_for_qa"):
            raise fatal(f"{cid} is burned_for_qa and must not be rendered")
        row = pool[cid]
        variants = P1.name_variants(row)
        segments, _turns = P1.subject_grounding(cid, pilot1_dir)
        twin_block = R.redact(
            R.render_grounding(segments, OE.GROUNDING_BUDGET_WORDS), variants)
        R.assert_redacted(twin_block, variants)

        donor_id = pairs.get(cid)
        if donor_id is None:
            raise fatal(f"{cid} has no imposter donor in imposter_pairs.json")
        if donor_id in dev_ids:
            raise fatal(f"donor {donor_id} for {cid} is itself a dev subject")
        donor_variants = P1.name_variants(pool[donor_id])
        dsegs, _dturns = P1.donor_grounding(donor_id, pilot1_dir)
        donor_block = R.redact(
            R.render_grounding(dsegs, OE.GROUNDING_BUDGET_WORDS),
            donor_variants)
        R.assert_redacted(donor_block, donor_variants)

        split = S.load_split(cid, pilot1_dir)
        test_date = (split.get("test") or {}).get("date")
        gdates = sorted(g.get("date", "") for g in split.get("grounding", [])
                        if g.get("date"))
        newest = gdates[-1] if gdates else None
        delta_days = _days_between(test_date, newest) if newest else None
        out[cid] = {
            "canonical_id": cid,
            "canonical_name": row["canonical_name"],
            "variants": variants,
            "twin_block": twin_block,
            "donor_id": donor_id,
            "donor_variants": donor_variants,
            "donor_block": donor_block,
            "test_date": test_date,
            "grounding_dates": gdates,
            "newest_grounding_date": newest,
            "delta_days": delta_days,
            "delta_bin": delta_bin(delta_days),
        }
    return out


# ---------------------------------------------------------------------------
# Render + guard
# ---------------------------------------------------------------------------

_REDACTED_TWIN = {"twin_named": "twin_redacted",
                  "zeroinfo_named": "zeroinfo_redacted"}


def render_and_guard_open(arm: str, item: dict, *, subject_name: str,
                          subject_variants: list, grounding_block,
                          donor_variants=None) -> dict:
    """Render one open-ended prompt and prove every guard on it.

    Same guard set as ``stage2_pilot.render_and_guard``, minus the option
    machinery and plus the open-ended shape guard:

      (a) the real held-out answer must not be quoted in the grounding;
      (b) no subject name variant may survive the rendered string (and, in the
          imposter arm, no donor variant either — two identities, two asserts);
      (c) a zero-information prompt carries no excerpts, program or date;
      (d) a named arm is its redacted counterpart plus exactly one name line;
      (e) the prompt ends with the frozen instruction and carries no option
          line, no choice line and no distribution instruction.
    """
    grounded = arm in OE.GROUNDED_ARMS
    named = arm in OE.NAMED_ARMS
    question = R.redact(item["question"], subject_variants)

    rendered = OE.render_open_prompt(
        arm, question,
        grounding_block=grounding_block if grounded else None,
        name=subject_name if named else None,
    )

    guarded = rendered
    if named:
        line = (R.TWIN_NAME_LINE if grounded else R.ZEROINFO_NAME_LINE).format(
            name=R._norm_ws(subject_name))
        marker = f"{line}\n\n"
        if marker not in rendered:
            raise fatal(f"{arm} {item['item_id']}: the name line is not where "
                        "the template says it is")
        guarded = rendered.replace(marker, "", 1)
        twin = OE.render_open_prompt(
            _REDACTED_TWIN[arm], question,
            grounding_block=grounding_block if grounded else None)
        if guarded != twin:
            raise fatal(f"{arm} {item['item_id']}: differs from its redacted "
                        "counterpart by more than the name line")
    R.assert_redacted(guarded, subject_variants)
    if donor_variants is not None:
        R.assert_redacted(rendered, donor_variants)

    if grounded:
        R.assert_no_answer_leak(grounding_block, item["answer"])
    else:
        if OE.carries_excerpts(rendered):
            raise fatal(f"{arm} {item['item_id']}: a zero-information prompt "
                        "carries an excerpt block")

    OE.assert_open_ended(rendered)

    words = R.word_count(rendered)
    excerpts = OE.excerpt_block_of(rendered)
    return {
        "prompt": rendered,
        "prompt_sha256": R.sha256(rendered),
        "prompt_words": words,
        "prompt_tokens_est": int(round(words * P1.TOKENS_PER_WORD)),
        "max_output_tokens": OE.MAX_OUTPUT_TOKENS,
        "grounding_speech_words": (OE.grounding_speech_words(excerpts)
                                   if grounded else 0),
        "instruction_tail_sha256": R.sha256(OE.tail_of(rendered)),
    }


def build_rows(pilot1_dir: Path, pilot4_dir: Path) -> dict:
    """Every open-ended prompt: 17 items x 5 arms, with per-subject bookkeeping."""
    items = all_items(pilot1_dir)
    ctx = subject_blocks(pilot1_dir)
    types = item_type_map(pilot4_dir, items)

    sets = {arm: [] for arm in OE.ARMS}
    per_subject: dict[str, dict] = {}
    item_rows: list[dict] = []
    for item in items:
        cid = item["canonical_id"]
        c = ctx[cid]
        item_rows.append({
            "item_id": item["item_id"], "canonical_id": cid,
            "transcript_id": item["transcript_id"],
            "q_turn_idx": item["q_turn_idx"],
            "question": item["question"],
            "real_answer_verbatim": item["answer"],
            "answer_words": item.get("answer_words") or R.word_count(item["answer"]),
            "item_type": types[item["item_id"]]["kind"],
            "item_type_source": types[item["item_id"]]["source"],
            "test_date": c["test_date"],
            "newest_grounding_date": c["newest_grounding_date"],
            "delta_days": c["delta_days"],
            "delta_bin": c["delta_bin"],
            "donor_id": c["donor_id"],
        })
        for arm in OE.ARMS:
            if arm == "imposter_redacted":
                block, donor_check = c["donor_block"], c["donor_variants"]
            elif arm in OE.GROUNDED_ARMS:
                block, donor_check = c["twin_block"], None
            else:
                block, donor_check = None, None
            built = render_and_guard_open(
                arm, item, subject_name=c["canonical_name"],
                subject_variants=c["variants"], grounding_block=block,
                donor_variants=donor_check)
            built.update({
                "item_id": item["item_id"], "canonical_id": cid,
                "arm": arm,
                "item_type": types[item["item_id"]]["kind"],
                "donor_id": c["donor_id"] if arm == "imposter_redacted" else None,
                "delta_bin": c["delta_bin"],
            })
            sets[arm].append(built)
        per_subject.setdefault(cid, {
            "canonical_id": cid, "canonical_name": c["canonical_name"],
            "donor_id": c["donor_id"], "test_date": c["test_date"],
            "delta_days": c["delta_days"], "delta_bin": c["delta_bin"],
            "item_ids": []})
        per_subject[cid]["item_ids"].append(item["item_id"])
    for entry in per_subject.values():
        entry["n_items"] = len(entry["item_ids"])

    counts = {arm: len(rows) for arm, rows in sets.items()}
    if len(set(counts.values())) != 1:
        raise fatal(f"prompt sets are not the same size: {counts}")
    return {"sets": sets, "items": item_rows, "per_subject": per_subject,
            "n_items": len(item_rows)}


# ---------------------------------------------------------------------------
# Build QA. Every check here is enforced by code, not by reading the output.
# ---------------------------------------------------------------------------

PROMPT_FIELDS = ("item_id", "canonical_id", "arm", "item_type", "donor_id",
                 "delta_bin", "prompt_sha256", "prompt_words",
                 "prompt_tokens_est", "max_output_tokens",
                 "grounding_speech_words", "prompt")


def build_qa(build: dict, ctx: dict) -> dict:
    """The build-summary QA block. Raises on anything that must never ship."""
    sets = build["sets"]
    all_rows = [r for rows in sets.values() for r in rows]

    # --- (1) the instruction tail is byte-identical across all 85 prompts ---
    tails = {r["instruction_tail_sha256"] for r in all_rows}
    if tails != {OE.INSTRUCTION_SHA256}:
        raise fatal(f"instruction tail is not byte-identical across arms: "
                    f"{len(tails)} distinct tails")
    bad_tail = [f"{r['arm']}:{r['item_id']}" for r in all_rows
                if not OE.has_instruction_tail(r["prompt"])]
    if bad_tail:
        raise fatal(f"{len(bad_tail)} prompts do not end with the frozen "
                    f"instruction (first: {bad_tail[0]})")

    # --- (2) no forced-choice residue anywhere ------------------------------
    # Keyed by arm AND item: the same item appears once per arm, so keying by
    # item id alone would let a clean arm overwrite a dirty one's finding.
    residue = {f"{r['arm']}:{r['item_id']}": OE.forced_choice_residue(r["prompt"])
               for r in all_rows}
    residue = {k: v for k, v in residue.items() if v}
    if residue:
        raise fatal(f"forced-choice residue survives in {len(residue)} "
                    f"prompts: {sorted(residue)[:3]}")

    # --- (3) the D6-v4.9 twin rule on every exported set --------------------
    twin_check = assert_no_cross_visible_twins(
        {f"prompts_{arm}": rows for arm, rows in sets.items()})

    # --- (4) grounding budget on every twin/imposter prompt -----------------
    grounded_rows = [r for r in all_rows if r["arm"] in OE.GROUNDED_ARMS]
    over = [r["item_id"] for r in grounded_rows
            if r["grounding_speech_words"] > OE.GROUNDING_BUDGET_WORDS]
    if over:
        raise fatal(f"{len(over)} grounded prompts exceed the "
                    f"{OE.GROUNDING_BUDGET_WORDS}-word grounding budget")
    per_arm_grounding = {
        arm: _mmm([r["grounding_speech_words"] for r in sets[arm]])
        for arm in OE.ARMS if arm in OE.GROUNDED_ARMS}

    # --- (5) zero-info prompts carry zero grounding excerpts ----------------
    zero_rows = [r for r in all_rows if r["arm"] not in OE.GROUNDED_ARMS]
    dirty = [r["item_id"] for r in zero_rows if OE.carries_excerpts(r["prompt"])]
    if dirty:
        raise fatal(f"{len(dirty)} zero-information prompts carry excerpts")

    # --- (6) S1 applied, and no subject name survives in the redacted arms --
    redacted_arms = [a for a in OE.ARMS if a.endswith("_redacted")]
    s1_hits = 0
    s1_prompts = 0
    survivors: dict[str, list] = {}
    for arm in redacted_arms:
        for row in sets[arm]:
            c = ctx[row["canonical_id"]]
            left = R.surviving_variants(row["prompt"], c["variants"])
            if arm == "imposter_redacted":
                left += R.surviving_variants(row["prompt"], c["donor_variants"])
            if left:
                survivors[f"{arm}:{row['item_id']}"] = left
            if OE.S1_PLACEHOLDER in row["prompt"]:
                s1_prompts += 1
                s1_hits += row["prompt"].count(OE.S1_PLACEHOLDER)
    if survivors:
        raise fatal(f"name variants survive in {len(survivors)} redacted "
                    f"prompts: {sorted(survivors)[:3]}")
    # S1 across every arm, for the record.
    s1_all = sum(r["prompt"].count(OE.S1_PLACEHOLDER) for r in all_rows)

    # --- (7) per-arm counts -------------------------------------------------
    counts = {arm: len(rows) for arm, rows in sets.items()}
    if set(counts.values()) != {build["n_items"]}:
        raise fatal(f"per-arm prompt counts are not all {build['n_items']}: "
                    f"{counts}")

    # --- (8) the imposter arm really is a different person's grounding ------
    same_block = []
    for row in sets["imposter_redacted"]:
        c = ctx[row["canonical_id"]]
        if c["donor_block"] == c["twin_block"]:
            same_block.append(row["item_id"])
    if same_block:
        raise fatal("imposter grounding equals the twin's grounding for "
                    f"{len(same_block)} items")

    return {
        "instruction_tail_byte_identical": True,
        "instruction_tail_sha256": OE.INSTRUCTION_SHA256,
        "instruction_tail_text": OE.OPEN_ANSWER_INSTRUCTION,
        "n_prompts_checked": len(all_rows),
        "forced_choice_residue": {"n_prompts_with_residue": 0,
                                  "checked_for": ["option_line", "choice_line",
                                                  "distribution_instruction"]},
        "twin_free_check": twin_check,
        "grounding_budget_words": OE.GROUNDING_BUDGET_WORDS,
        "grounding_speech_words_per_arm": per_arm_grounding,
        "grounding_speech_words_all_grounded": _mmm(
            [r["grounding_speech_words"] for r in grounded_rows]),
        "n_grounded_prompts_over_budget": 0,
        "zeroinfo_prompts_with_excerpts": 0,
        "n_zeroinfo_prompts": len(zero_rows),
        "s1_note": S1_NOTE,
        "s1_redacted_arms_prompts_changed": s1_prompts,
        "s1_redacted_arms_clauses_removed": s1_hits,
        "s1_all_arms_clauses_removed": s1_all,
        "surviving_name_variants_in_redacted_arms": 0,
        "per_arm_prompt_counts": counts,
        "imposter_block_differs_from_twin_block": True,
        "zeroinfo_preamble_note": ZEROINFO_PREAMBLE_NOTE,
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def _write_prompt_set(path: Path, rows: list[dict]) -> dict:
    out = []
    for idx, row in enumerate(rows):
        entry = {"idx": idx}
        for field in PROMPT_FIELDS:
            entry[field] = row.get(field)
        out.append(entry)
    S.write_jsonl(path, out)
    return {"file": path.name, "n_prompts": len(out),
            "sha256": P1.sha256_file(path),
            "max_prompt_words": max((r["prompt_words"] for r in rows), default=0),
            "total_prompt_words": sum(r["prompt_words"] for r in rows)}


def _write_leonardo_pair(prompts_path: Path, meta_path: Path,
                         rows: list[dict]) -> dict:
    """The node file (idx/prompt/max_output_tokens) and its join sidecar."""
    prompts, metas = [], []
    for idx, row in enumerate(rows):
        prompts.append({"idx": idx, "prompt": row["prompt"],
                        "max_output_tokens": row["max_output_tokens"]})
        metas.append({"idx": idx, "item_id": row["item_id"],
                      "canonical_id": row["canonical_id"], "arm": row["arm"],
                      "item_type": row["item_type"],
                      "prompt_sha256": row["prompt_sha256"],
                      "prompt_words": row["prompt_words"],
                      "prompt_tokens_est": row["prompt_tokens_est"]})
    S.write_jsonl(prompts_path, prompts)
    S.write_jsonl(meta_path, metas)
    return {"prompts_file": prompts_path.name, "meta_file": meta_path.name,
            "n_prompts": len(prompts),
            "prompts_sha256": P1.sha256_file(prompts_path),
            "meta_sha256": P1.sha256_file(meta_path),
            "max_output_tokens": OE.MAX_OUTPUT_TOKENS,
            "temperature": GEN_TEMPERATURE}


def projection(rows: list[dict]) -> dict:
    """Node-hours for the one Gemma job, on round 1's measured throughput."""
    eff = P1.MEASURED_TOKENS_PER_SECOND / P1.LONG_PROMPT_DERATE
    tin = sum(r["prompt_tokens_est"] for r in rows)
    tout = sum(r["max_output_tokens"] for r in rows)
    seconds = (tin + tout) / eff
    hours = round((seconds + P1.ENGINE_INIT_SECONDS) / 3600, 4)
    return {
        "n_calls": len(rows), "tokens_in_est": tin, "tokens_out_cap": tout,
        "generation_seconds": round(seconds, 1),
        "engine_init_seconds": P1.ENGINE_INIT_SECONDS,
        "projected_node_hours": hours,
        "walltime": GEN_WALLTIME, "qos": GEN_QOS,
        "effective_tokens_per_second": round(eff, 1),
        "budget_node_hours": NODE_HOUR_BUDGET,
        "walltime_bounded_worst_case_node_hours": round(
            P1._walltime_hours(GEN_WALLTIME), 4),
        "note": "One engine init dominates: 85 prompts against round 1's 639, "
                "same node, same model. Output tokens are counted at the "
                "256-token cap, so the generation term is an upper bound.",
    }


def write_sbatch(out_dir: Path, hours: float) -> Path:
    """The Gemma job, pattern-matched to results/stage2_pilot3/*_gate.sbatch.

    WRITTEN, NEVER SUBMITTED. The standing stop-before-GPU checkpoint applies:
    the owner reviews the rendered prompts and the projection first.
    """
    text = P3._sbatch(
        "gen", "OE-1: open-ended generations, all five arms, one file",
        [LEONARDO_SET], hours, GEN_WALLTIME, GEN_QOS,
        run="stage2_oe1", node_run=NODE_RUN)
    path = out_dir / "stage2_oe1_gen.sbatch"
    path.write_text(text, encoding="utf-8")
    return path


SAMPLE_HEADER = """# OE-1 rendered prompt samples — one per arm, owner review

{banner}

Contract: {contract}

**The same item in all five arms**, so the only differences you should see are
the ones the arms are for: the excerpt block (present / absent / a different
person's) and the single name line. The instruction tail is byte-identical in
all five and is the last block of every prompt.

- item: `{item_id}` (subject `{cid}`, item type: {item_type})
- imposter donor for this subject: `{donor_id}`
- instruction tail sha256: `{tail_sha}`
- generation settings, both scored models: temperature {temp}, \
max_output_tokens {max_tokens}
- S1 affiliation redaction: applied to all five arms (see build_summary.json)

Nothing below has been reflowed or trimmed: each block is the exact string that
would be sent, byte for byte.
"""


def write_prompt_samples(path: Path, build: dict, ctx: dict) -> str:
    """Exactly one full rendered prompt per arm, same item across all five."""
    by_arm_item = {(r["arm"], r["item_id"]): r
                   for rows in build["sets"].values() for r in rows}
    item_id = build["sets"][OE.ARMS[0]][0]["item_id"]
    first = by_arm_item[(OE.ARMS[0], item_id)]
    cid = first["canonical_id"]
    parts = [SAMPLE_HEADER.format(
        banner=PILOT_BANNER, contract=CONTRACT, item_id=item_id, cid=cid,
        item_type=first["item_type"], donor_id=ctx[cid]["donor_id"],
        tail_sha=OE.INSTRUCTION_SHA256, temp=GEN_TEMPERATURE,
        max_tokens=OE.MAX_OUTPUT_TOKENS)]
    for arm in OE.ARMS:
        row = by_arm_item[(arm, item_id)]
        parts.append(
            f"\n---\n\n## {arm}\n\n"
            f"{row['prompt_words']} words, ~{row['prompt_tokens_est']} tokens; "
            f"grounding speech {row['grounding_speech_words']} words "
            f"(budget {OE.GROUNDING_BUDGET_WORDS}); "
            f"prompt sha256 `{row['prompt_sha256']}`.\n\n"
            f"```text\n{row['prompt']}\n```\n")
    text = "".join(parts)
    path.write_text(text, encoding="utf-8")
    return text


def cmd_build(args) -> int:
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    pilot4_dir = Path(getattr(args, "pilot4_dir", None) or PILOT4_DIR)
    out_dir = Path(getattr(args, "out_dir", None) or OE_DIR)
    prompts_dir = out_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    ctx = subject_blocks(pilot1_dir)
    build = build_rows(pilot1_dir, pilot4_dir)
    qa = build_qa(build, ctx)

    files = {}
    for arm in OE.ARMS:
        files[f"prompts_{arm}"] = _write_prompt_set(
            prompts_dir / f"prompts_{arm}.jsonl", build["sets"][arm])
        print(f"[build] {arm:20s} {files['prompts_' + arm]['n_prompts']} prompts")

    node_rows = [r for arm in OE.ARMS for r in build["sets"][arm]]
    files["leonardo"] = _write_leonardo_pair(
        prompts_dir / f"prompts_{LEONARDO_SET}.jsonl",
        prompts_dir / f"meta_{LEONARDO_SET}.jsonl", node_rows)

    S.write_jsonl(out_dir / "items_oe1.jsonl", build["items"])

    proj = projection(node_rows)
    if proj["projected_node_hours"] > NODE_HOUR_BUDGET:
        raise fatal(f"projection {proj['projected_node_hours']} node-hours "
                    f"exceeds the {NODE_HOUR_BUDGET} cap; no sbatch written")
    sbatch = write_sbatch(out_dir, proj["projected_node_hours"])
    samples = out_dir / "prompt_samples.md"
    write_prompt_samples(samples, build, ctx)

    rubric = extract_rubric(Path(getattr(args, "spec", None) or SPEC_PATH))
    types = {}
    for row in build["items"]:
        types[row["item_type"]] = types.get(row["item_type"], 0) + 1
    bins = {}
    for row in build["items"]:
        bins[row["delta_bin"]] = bins.get(row["delta_bin"], 0) + 1

    summary = {
        "pilot": PILOT_BANNER,
        "contract": CONTRACT,
        "scored_claim": SCORED_CLAIM,
        "phase": "build",
        "built_utc": now(),
        "runtime_secs": round(time.time() - started, 2),
        "offline": True,
        "spend": {"api_calls": 0, "cost_usd": 0.0, "node_hours": 0.0},
        "n_items": build["n_items"],
        "n_arms": len(OE.ARMS),
        "n_prompts": len(node_rows),
        "arms": list(OE.ARMS),
        "item_types": types,
        "item_type_sources": {
            row["item_id"]: row["item_type_source"] for row in build["items"]},
        "delta_bins_smoke_check": bins,
        "generation": {
            "temperature": GEN_TEMPERATURE,
            "max_output_tokens": OE.MAX_OUTPUT_TOKENS,
            "answer_word_cap": OE.MAX_ANSWER_WORDS,
            "primary_model": PRIMARY_MODEL,
            "robustness_model": ROBUSTNESS_MODEL,
        },
        "judge": {"model": JUDGE_MODEL, "temperature": JUDGE_TEMPERATURE,
                  "rubric_file": "rubric_r1.txt (written by `judge`)",
                  "rubric_sha256": rubric["sha256"],
                  "rubric_chars": len(rubric["text"]),
                  "call_order_seed": JUDGE_ORDER_SEED},
        "embedding_candidates": [
            {"name": c["name"], "revision": c.get("revision")}
            for c in embed_candidates(out_dir)],
        "qa": qa,
        "per_subject": build["per_subject"],
        "projection": proj,
        "renderer": {
            "oe_render_template_sha256": OE.TEMPLATE_SHA256,
            "oe_render_instruction_sha256": OE.INSTRUCTION_SHA256,
            "oe_render_file_sha256": P1.sha256_file(
                _ROOT / "src/doppler/oe_render.py"),
            "stage2_render_template_sha256": R.TEMPLATE_SHA256,
            "stage2_render_file_sha256": P1.sha256_file(
                _ROOT / "src/doppler/stage2_render.py"),
        },
        "files": files,
        "sbatch": {"path": rel(sbatch), "submitted": False,
                   "node_outdir": NODE_RUN,
                   "note": "WRITTEN, NEVER SUBMITTED. Standing "
                           "stop-before-GPU checkpoint: owner reviews "
                           "prompt_samples.md and the projection first."},
        "prompt_samples": rel(samples),
        "twin_rule": TWIN_RULE,
    }
    S.write_json(out_dir / "build_summary.json", summary)

    print(f"[build] {build['n_items']} items x {len(OE.ARMS)} arms = "
          f"{len(node_rows)} prompts")
    print(f"[build] grounding speech words (twin/imposter): "
          f"{qa['grounding_speech_words_all_grounded']}")
    print(f"[build] instruction tail identical across all prompts: "
          f"{qa['instruction_tail_sha256'][:16]}")
    print(f"[build] projection {proj['projected_node_hours']} node-hours "
          f"(cap {NODE_HOUR_BUDGET}); sbatch -> {rel(sbatch)} (NOT submitted)")
    print(f"[build] samples -> {rel(samples)}")
    print(f"[build] summary -> {rel(out_dir / 'build_summary.json')}")
    return 0


# ---------------------------------------------------------------------------
# Phase 2: robustness generations on gemini-3.5-flash-lite
# ---------------------------------------------------------------------------


def load_prompt_sets(out_dir: Path) -> dict:
    sets = {}
    for arm in OE.ARMS:
        path = out_dir / "prompts" / f"prompts_{arm}.jsonl"
        if not path.exists():
            raise fatal(f"{rel(path)} not found; run `build` first")
        sets[arm] = S.read_jsonl(path)
    return sets


def load_items(out_dir: Path) -> dict:
    path = out_dir / "items_oe1.jsonl"
    if not path.exists():
        raise fatal(f"{rel(path)} not found; run `build` first")
    return {r["item_id"]: r for r in S.read_jsonl(path)}


def _make_client(model: str, *, temperature: float, max_output_tokens: int,
                 call_cap: int, thinking_budget: int | None = None):
    """A client for one phase. ``thinking_budget`` is opt-in per phase.

    ``None`` keeps the historic behaviour (no thinking_config at all), which is
    what the flash-lite GENERATION path was measured on and must keep. ``0``
    sends the explicit disable, which the judge path needs because
    gemini-3.5-flash thinks by default.
    """
    from doppler.gemini import GeminiClient
    client = GeminiClient(max_calls=call_cap, temperature=temperature,
                          max_output_tokens=max_output_tokens,
                          thinking_budget=thinking_budget)
    client.model_name = model
    return client


def looks_truncated(text: str, tokens_out: int) -> bool:
    """A generation that ran into the cap, or stopped mid-sentence.

    Both readings are kept because neither is sufficient on its own: the token
    count catches a reply that filled the budget, ``CF.looks_truncated`` catches
    one that ended mid-clause below it. The truncation RATE is reported per arm
    — a gap between arms biases channel 1 and is a red flag in itself (spec 2).
    """
    if tokens_out >= OE.MAX_OUTPUT_TOKENS:
        return True
    return CF.looks_truncated(text or "")


def cmd_gen_flashlite(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or OE_DIR)
    sets = load_prompt_sets(out_dir)
    items = load_items(out_dir)
    gen_dir = out_dir / "gen" / "flashlite"
    gen_dir.mkdir(parents=True, exist_ok=True)

    if ROBUSTNESS_MODEL == JUDGE_MODEL:
        raise fatal("the robustness scorer and the judge are the same model "
                    "version; C2.3 requires different versions")
    client = getattr(args, "client", None) or _make_client(
        ROBUSTNESS_MODEL, temperature=GEN_TEMPERATURE,
        max_output_tokens=OE.MAX_OUTPUT_TOKENS, call_cap=args.call_cap)

    spent = 0.0
    totals = {}
    for arm in OE.ARMS:
        path = gen_dir / f"completions_{arm}.jsonl"
        if path.exists() and not args.force:
            print(f"[gen-flashlite] {arm}: already on disk, skipping")
            continue
        rows, tin_sum, tout_sum = [], 0, 0
        for row in sets[arm]:
            text, tin, tout = client.generate(row["prompt"])
            tin_sum += tin
            tout_sum += tout
            item = items[row["item_id"]]
            rows.append({
                "item_id": row["item_id"], "canonical_id": row["canonical_id"],
                "arm": arm, "model": ROBUSTNESS_MODEL,
                "temperature": GEN_TEMPERATURE,
                "max_output_tokens": OE.MAX_OUTPUT_TOKENS,
                "prompt_sha256": row["prompt_sha256"],
                "text": text,
                "answer_words": R.word_count(text),
                "over_word_cap": R.word_count(text) > OE.MAX_ANSWER_WORDS,
                "truncated": looks_truncated(text, tout),
                "era_violations": CF.era_violations(text, item["test_date"]),
                "tokens_in": tin, "tokens_out": tout,
                "generated_utc": now(),
            })
        S.write_jsonl(path, rows)
        entry = build_cost_entry(
            run_id="stage2_oe1/gen_flashlite", model=ROBUSTNESS_MODEL,
            split="stage2_openended", variant=f"arm_{arm}",
            n_persons=len({r["canonical_id"] for r in rows}),
            n_calls=len(rows), n_retries=0, n_parse_failures=0,
            tokens_in=tin_sum, tokens_out=tout_sum, backend="gemini")
        if not args.skip_cost:
            append_cost_log(entry, COST_LOG)
        spent += entry["cost_usd"] or 0.0
        totals[arm] = {"n": len(rows), "tokens_in": tin_sum,
                       "tokens_out": tout_sum, "cost_usd": entry["cost_usd"],
                       "n_truncated": sum(1 for r in rows if r["truncated"]),
                       "n_era_violations": sum(1 for r in rows
                                               if r["era_violations"])}
        print(f"[gen-flashlite] {arm:20s} {len(rows)} gens, "
              f"{totals[arm]['n_truncated']} truncated, "
              f"${entry['cost_usd']}")
        if spent > API_BUDGET_USD:
            raise fatal(f"API spend ${spent:.4f} exceeded the "
                        f"${API_BUDGET_USD} cap; stopping")
    S.write_json(gen_dir / "gen_summary.json", {
        "pilot": PILOT_BANNER, "model": ROBUSTNESS_MODEL,
        "temperature": GEN_TEMPERATURE,
        "max_output_tokens": OE.MAX_OUTPUT_TOKENS,
        "run_id": "stage2_oe1/gen_flashlite",
        "per_arm": totals, "total_cost_usd": round(spent, 6),
        "api_budget_usd": API_BUDGET_USD, "generated_utc": now()})
    print(f"[gen-flashlite] total ${spent:.4f} (cap ${API_BUDGET_USD})")
    return 0


def cmd_ingest_gemma(args) -> int:
    """Join the node's completions back to their items (no GPU, no API)."""
    out_dir = Path(getattr(args, "out_dir", None) or OE_DIR)
    nodedir = Path(args.nodedir)
    items = load_items(out_dir)
    metas = S.read_jsonl(out_dir / "prompts" / f"meta_{LEONARDO_SET}.jsonl")
    by_idx = {int(r["idx"]): r
              for r in S.read_jsonl(nodedir / f"completions_{LEONARDO_SET}.jsonl")}
    gen_dir = out_dir / "gen" / "gemma"
    gen_dir.mkdir(parents=True, exist_ok=True)
    per_arm: dict[str, list] = {arm: [] for arm in OE.ARMS}
    for meta in metas:
        got = by_idx.get(int(meta["idx"])) or {}
        text = (P2._completion_text(got) or "").strip()
        tout = int(got.get("tokens_out") or got.get("n_tokens_out") or 0)
        item = items[meta["item_id"]]
        per_arm[meta["arm"]].append({
            "item_id": meta["item_id"], "canonical_id": meta["canonical_id"],
            "arm": meta["arm"], "model": PRIMARY_MODEL,
            "temperature": GEN_TEMPERATURE,
            "max_output_tokens": OE.MAX_OUTPUT_TOKENS,
            "prompt_sha256": meta["prompt_sha256"],
            "text": text, "answer_words": R.word_count(text),
            "over_word_cap": R.word_count(text) > OE.MAX_ANSWER_WORDS,
            "truncated": looks_truncated(text, tout),
            "era_violations": CF.era_violations(text, item["test_date"]),
            "tokens_out": tout,
        })
    for arm, rows in per_arm.items():
        S.write_jsonl(gen_dir / f"completions_{arm}.jsonl", rows)
        print(f"[ingest-gemma] {arm:20s} {len(rows)} generations, "
              f"{sum(1 for r in rows if r['truncated'])} truncated")
    return 0


# ---------------------------------------------------------------------------
# Phase 3: the stance judge (channel 2)
# ---------------------------------------------------------------------------

_RUBRIC_START = "STANCE JUDGE RUBRIC"
LABELS = ("SAME", "DIFFERENT", "UNCLEAR")
_LABEL_RE = re.compile(r"^\s*LABEL:\s*(SAME|DIFFERENT|UNCLEAR)\b",
                       re.IGNORECASE | re.MULTILINE)
_WHY_RE = re.compile(r"^\s*WHY:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def extract_rubric(spec_path: Path) -> dict:
    """The section-4 rubric, VERBATIM out of its fenced block, plus its sha256.

    Verbatim means verbatim: the fence lines go, nothing else is touched — no
    dedent, no rewrap, no stripping of interior blank lines. The hash is of the
    text that will actually be sent, so a silent edit to the spec changes it.
    """
    text = Path(spec_path).read_text(encoding="utf-8")
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("```") and i + 1 < len(lines) \
                and lines[i + 1].startswith(_RUBRIC_START):
            start = i + 1
            break
    if start is None:
        raise fatal(f"no fenced block starting {_RUBRIC_START!r} in "
                    f"{rel(Path(spec_path))}")
    end = None
    for j in range(start, len(lines)):
        if lines[j].strip() == "```":
            end = j
            break
    if end is None:
        raise fatal("the rubric's fenced block is never closed")
    body = "\n".join(lines[start:end]) + "\n"
    return {"text": body, "sha256": R.sha256(body),
            "source": rel(Path(spec_path)), "version": "r1"}


JUDGE_INPUT_TEMPLATE = """{rubric}
QUESTION:
{question}

REAL ANSWER:
{real}

CANDIDATE ANSWER:
{candidate}
"""


def judge_input(rubric_text: str, question: str, real: str, candidate: str,
                variants) -> str:
    """One judge call's full input: rubric + three texts, all GUEST-redacted.

    Every one of the three texts is scrubbed with the subject's name variants,
    not just the candidate: the QUESTION comes from the test interview, where
    the host says the guest's name out loud more often than not, and the REAL
    answer is the person's own speech. Nothing here names an arm or a model —
    the judge cannot tell a twin's reply from an imposter's or from Gemma's.
    """
    return JUDGE_INPUT_TEMPLATE.format(
        rubric=rubric_text,
        question=R._norm_ws(R.redact(question, variants)),
        real=R._norm_ws(R.redact(real, variants)),
        candidate=R._norm_ws(R.redact(candidate, variants)))


def parse_judge(completion: str):
    """``(label, why)`` from the required two-line format, or ``(None, None)``."""
    if not completion:
        return None, None
    m = _LABEL_RE.search(completion)
    if not m:
        return None, None
    why = _WHY_RE.search(completion)
    return m.group(1).upper(), (why.group(1) if why else None)


def judge_calls(out_dir: Path, models: list[str]) -> list[dict]:
    """Every (model, arm, item) candidate to judge, in a fixed-seed order."""
    items = load_items(out_dir)
    calls = []
    for model in models:
        gen_dir = out_dir / "gen" / model
        for arm in OE.ARMS:
            path = gen_dir / f"completions_{arm}.jsonl"
            if not path.exists():
                continue
            for row in S.read_jsonl(path):
                item = items[row["item_id"]]
                calls.append({
                    "scored_model_dir": model, "arm": arm,
                    "item_id": row["item_id"],
                    "canonical_id": row["canonical_id"],
                    "question": item["question"],
                    "real": item["real_answer_verbatim"],
                    "candidate": row["text"],
                    "item_type": item["item_type"],
                })
    random.Random(JUDGE_ORDER_SEED).shuffle(calls)
    return calls


JUDGE_CONFIG_NOTE = (
    "Owner decision 2026-07-27, after the v1 judge run: thinking EXPLICITLY "
    "disabled (thinking_budget=0) and max_output_tokens raised to 512; "
    "gemini-3.5-flash, temperature 0, rubric r1 verbatim, same blinding, same "
    "randomization seed -- everything else unchanged. The rubric asks for a "
    "mechanical classification with an auditable WHY line; hidden thinking is "
    "budget-unstable at temperature 0 (see judge/thinking_budget_probe.json, "
    "where the label moved between a 256 and a 1024 budget) and it defeats the "
    "owner's >=50-label spot-check by truncating every WHY. Both settings "
    "become PINNED judge parameters at bar-lock.")


#: A WHY line the owner's spot-check can actually audit: present, and not cut
#: off mid-phrase. The rubric asks for "one sentence quoting the decisive
#: phrase of each answer", so a WHY under this many words is a truncation
#: symptom, not a terse judge.
WHY_MIN_WORDS = 8


def why_is_intact(why, tokens_out: int) -> bool:
    """Did the WHY line survive, or did the output budget eat it?"""
    if not why:
        return False
    if tokens_out >= JUDGE_MAX_OUTPUT_TOKENS:
        return False
    return len(why.split()) >= WHY_MIN_WORDS


def _judge_names(tag):
    """(judgements file, summary file, run_id) for a judge pass.

    ``tag`` keeps a re-run from standing on top of an earlier one: the v1 files
    and the thinking-budget probe are the DEFECT RECORD and are never
    overwritten or deleted.
    """
    if not tag:
        return "judgements.jsonl", "judge_summary.json", "stage2_oe1/judge"
    return (f"judgements_{tag}.jsonl", f"judge_{tag}_summary.json",
            f"stage2_oe1/judge_{tag}")


def _determinism_probe(args, judge_dir: Path, tag, n: int, calls, ctx,
                       rubric, client) -> int:
    """Run the first ``n`` judge calls TWICE and compare. Spends 2n calls.

    The point is not that the API promises determinism -- it does not. The
    point is that with thinking off at temperature 0 the label must not move,
    because the v1 defect was exactly a label moving when the hidden-thinking
    budget changed. A disagreement here means the instrument is not stable
    enough to score with, and the batch must not run.
    """
    probe = []
    disagreements = []
    for order, call in enumerate(calls[:n]):
        variants = ctx[call["canonical_id"]]["variants"]
        prompt = judge_input(rubric["text"], call["question"], call["real"],
                             call["candidate"], variants)
        runs = []
        for attempt in (1, 2):
            text, tin, tout = client.generate(prompt)
            label, why = parse_judge(text)
            runs.append({"attempt": attempt, "label": label, "why": why,
                         "why_intact": why_is_intact(why, tout),
                         "why_words": len((why or "").split()),
                         "tokens_out": tout,
                         "output_hit_cap": tout >= JUDGE_MAX_OUTPUT_TOKENS,
                         "raw": text})
        same_label = runs[0]["label"] == runs[1]["label"]
        if not same_label:
            disagreements.append(call["item_id"])
        probe.append({"call_order": order, "arm": call["arm"],
                      "item_id": call["item_id"],
                      "labels_agree": same_label,
                      "both_why_intact": all(r["why_intact"] for r in runs),
                      "runs": runs})
    doc = {
        "pilot": PILOT_BANNER, "phase": "determinism_probe",
        "judge_model": JUDGE_MODEL, "temperature": JUDGE_TEMPERATURE,
        "thinking_budget": JUDGE_THINKING_BUDGET,
        "max_output_tokens": JUDGE_MAX_OUTPUT_TOKENS,
        "config_note": JUDGE_CONFIG_NOTE,
        "n_items_probed": len(probe), "n_calls": 2 * len(probe),
        "all_labels_agree": not disagreements,
        "all_why_intact": all(p["both_why_intact"] for p in probe),
        "disagreements": disagreements,
        "gate": "If any label disagrees at temperature 0 with thinking off, "
                "STOP and report; do not run the batch.",
        "probe": probe, "probed_utc": now(),
    }
    path = judge_dir / f"determinism_probe_{tag or 'v1'}.json"
    S.write_json(path, doc)
    for row in probe:
        print(f"[probe] {row['arm']:20s} {row['item_id']:22s} "
              f"labels={row['runs'][0]['label']}/{row['runs'][1]['label']} "
              f"agree={row['labels_agree']} why_intact={row['both_why_intact']}")
    print(f"[probe] labels all agree: {doc['all_labels_agree']}; "
          f"WHY intact both runs: {doc['all_why_intact']}")
    print(f"[probe] -> {rel(path)}")
    if disagreements:
        raise fatal(f"determinism probe FAILED on {len(disagreements)} item(s) "
                    f"({', '.join(disagreements)}); the batch was NOT run")
    return 0


def cmd_judge(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or OE_DIR)
    if JUDGE_MODEL in SCORED_MODELS:
        raise fatal(f"C2.2/C2.3 violation: the judge {JUDGE_MODEL} is a "
                    "scored model")
    rubric = extract_rubric(Path(getattr(args, "spec", None) or SPEC_PATH))
    rubric_path = out_dir / "rubric_r1.txt"
    rubric_path.parent.mkdir(parents=True, exist_ok=True)
    rubric_path.write_text(rubric["text"], encoding="utf-8")

    ctx = subject_blocks(Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR))
    calls = judge_calls(out_dir, list(args.models))
    if not calls:
        raise fatal("no generations on disk to judge; run gen-flashlite "
                    "and/or ingest-gemma first")

    client = getattr(args, "client", None) or _make_client(
        JUDGE_MODEL, temperature=JUDGE_TEMPERATURE,
        max_output_tokens=JUDGE_MAX_OUTPUT_TOKENS, call_cap=args.call_cap,
        thinking_budget=JUDGE_THINKING_BUDGET)

    judge_dir = out_dir / "judge"
    judge_dir.mkdir(parents=True, exist_ok=True)
    tag = getattr(args, "tag", None)
    jfile, sfile, run_id = _judge_names(tag)
    if (judge_dir / jfile).exists() and not getattr(args, "force", False):
        raise fatal(f"{rel(judge_dir / jfile)} already exists; pass a new "
                    "--tag (an earlier pass is a record, not scratch) or "
                    "--force")

    probe_n = int(getattr(args, "determinism_probe", 0) or 0)
    if probe_n:
        return _determinism_probe(args, judge_dir, tag, probe_n, calls, ctx,
                                  rubric, client)

    rows = []
    per_arm: dict[str, dict] = {}
    n_retries = n_unparsed = 0
    for order, call in enumerate(calls):
        variants = ctx[call["canonical_id"]]["variants"]
        prompt = judge_input(rubric["text"], call["question"], call["real"],
                             call["candidate"], variants)
        # D6-v4.9: one candidate per call, so a question is never in front of
        # the judge twice inside one visibility unit. Asserted, not assumed.
        assert_no_cross_visible_twins({f"judge_call_{order}": [call]})
        text, tin, tout = client.generate(prompt)
        label, why = parse_judge(text)
        retried = False
        if label is None:
            retried = True
            n_retries += 1
            text2, tin2, tout2 = client.generate(prompt)
            tin += tin2
            tout += tout2
            label, why = parse_judge(text2)
            text = text2
        if label is None:
            n_unparsed += 1
        rows.append({
            "call_order": order, "arm": call["arm"],
            "scored_model_dir": call["scored_model_dir"],
            "item_id": call["item_id"], "canonical_id": call["canonical_id"],
            "item_type": call["item_type"],
            "label": label, "why": why, "retried": retried,
            "why_intact": why_is_intact(why, tout),
            "why_words": len((why or "").split()),
            "output_hit_cap": tout >= JUDGE_MAX_OUTPUT_TOKENS,
            "raw": text, "judge_model": JUDGE_MODEL,
            "judge_thinking_budget": JUDGE_THINKING_BUDGET,
            "judge_max_output_tokens": JUDGE_MAX_OUTPUT_TOKENS,
            "judge_prompt_sha256": R.sha256(prompt),
            "tokens_in": tin, "tokens_out": tout,
        })
        stat = per_arm.setdefault(call["arm"], {
            "n": 0, "tokens_in": 0, "tokens_out": 0, "n_unparsed": 0,
            "n_why_intact": 0, "n_output_hit_cap": 0,
            **{lab: 0 for lab in LABELS}})
        stat["n"] += 1
        stat["tokens_in"] += tin
        stat["tokens_out"] += tout
        stat["n_why_intact"] += int(rows[-1]["why_intact"])
        stat["n_output_hit_cap"] += int(rows[-1]["output_hit_cap"])
        if label is None:
            stat["n_unparsed"] += 1
        else:
            stat[label] += 1

    S.write_jsonl(judge_dir / jfile, rows)

    spent = 0.0
    for arm, stat in per_arm.items():
        entry = build_cost_entry(
            run_id=run_id, model=JUDGE_MODEL,
            split="stage2_openended", variant=f"arm_{arm}",
            n_persons=len({r["canonical_id"] for r in rows
                           if r["arm"] == arm}),
            n_calls=stat["n"], n_retries=0,
            n_parse_failures=stat["n_unparsed"],
            tokens_in=stat["tokens_in"], tokens_out=stat["tokens_out"],
            backend="gemini")
        if not args.skip_cost:
            append_cost_log(entry, COST_LOG)
        stat["cost_usd"] = entry["cost_usd"]
        spent += entry["cost_usd"] or 0.0
        denom = stat["n"] - stat["UNCLEAR"] - stat["n_unparsed"]
        stat["stance_match_rate"] = (round(stat["SAME"] / denom, 4)
                                     if denom else None)
        stat["unclear_rate"] = (round(stat["UNCLEAR"] / stat["n"], 4)
                                if stat["n"] else None)
        stat["why_intact_rate"] = (round(stat["n_why_intact"] / stat["n"], 4)
                                   if stat["n"] else None)
    S.write_json(judge_dir / sfile, {
        "pilot": PILOT_BANNER, "judge_model": JUDGE_MODEL,
        "tag": tag, "run_id": run_id,
        "temperature": JUDGE_TEMPERATURE,
        "thinking_budget": JUDGE_THINKING_BUDGET,
        "max_output_tokens": JUDGE_MAX_OUTPUT_TOKENS,
        "config_note": JUDGE_CONFIG_NOTE,
        "rubric_version": rubric["version"],
        "rubric_sha256": rubric["sha256"],
        "rubric_file": rel(rubric_path),
        "call_order_seed": JUDGE_ORDER_SEED,
        "n_calls": len(rows), "n_malformed_retried": n_retries,
        "n_unparsed_after_retry": n_unparsed,
        "unclear_rule": "UNCLEAR is excluded from the stance-match "
                        "denominator; per-arm UNCLEAR rates are printed "
                        "beside every rate (C2.3).",
        "protocol": "One candidate per call. The judge never sees two "
                    "candidates together, never sees an arm or model label, "
                    "never sees a subject name (all three texts are "
                    "GUEST-redacted), and never sees both twins of a "
                    "duplicated question.",
        "why_intact_rate_overall": round(
            sum(1 for r in rows if r["why_intact"]) / len(rows), 4),
        "n_output_hit_cap": sum(1 for r in rows if r["output_hit_cap"]),
        "per_arm": per_arm, "total_cost_usd": round(spent, 6),
        "api_budget_usd": API_BUDGET_USD, "judged_utc": now()})
    if spent > API_BUDGET_USD:
        raise fatal(f"judge spend ${spent:.4f} exceeded the "
                    f"${API_BUDGET_USD} cap")
    for arm, stat in sorted(per_arm.items()):
        print(f"[judge] {arm:20s} n={stat['n']:3d} "
              f"SAME={stat['SAME']:3d} DIFFERENT={stat['DIFFERENT']:3d} "
              f"UNCLEAR={stat['UNCLEAR']:3d} "
              f"match={stat['stance_match_rate']} "
              f"why_intact={stat['why_intact_rate']}")
    print(f"[judge] rubric {rubric['sha256'][:16]} -> {rel(rubric_path)}")
    print(f"[judge] wrote {rel(judge_dir / jfile)} (thinking_budget="
          f"{JUDGE_THINKING_BUDGET}, max_output_tokens="
          f"{JUDGE_MAX_OUTPUT_TOKENS})")
    print(f"[judge] total ${spent:.4f} (cap ${API_BUDGET_USD})")
    return 0


# ---------------------------------------------------------------------------
# Phase 4: embeddings (channel 1). Local CPU only, never an API model.
# ---------------------------------------------------------------------------


def embed_candidates(out_dir: Path) -> list[dict]:
    """The four candidates, with their pinned HF revisions where recorded.

    ``housekeeping.json`` is the recon artifact that installed CPU-only torch +
    sentence-transformers and smoke-tested the four models; it records each
    one's revision hash under ``models``. Prefer it, because a candidate
    without a pinned revision is not reproducible. Fall back to the spec's
    section-3 list when the file is not there yet.
    """
    path = Path(out_dir) / "housekeeping.json"
    if path.exists():
        doc = json.loads(path.read_text(encoding="utf-8"))
        got = doc.get("models") or doc.get("embedding_candidates")
        if got:
            return [dict(c) if isinstance(c, dict) else {"name": c}
                    for c in got]
    return [dict(c) for c in EMBED_CANDIDATES]


def _cosine(a, b) -> float:
    import numpy as np
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(a.dot(b) / (na * nb))


def _encode(model, texts, name: str, kind: str = "query"):
    """Encode with the one prefix footgun the spec names, pinned down.

    ``kind`` is ``"query"`` for the text being scored (a generated answer, or
    the grounding block in the section-8 diagnostic) and ``"passage"`` for the
    reference text (the real verbatim answer). It only bites on e5; every other
    candidate is symmetric and takes the text as it is.
    """
    if name.startswith("intfloat/e5"):
        prefix = E5_QUERY_PREFIX if kind == "query" else E5_PASSAGE_PREFIX
        texts = [prefix + t for t in texts]
    return model.encode(list(texts), batch_size=8, show_progress_bar=False,
                        convert_to_numpy=True)


def cmd_embed(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or OE_DIR)
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    items = load_items(out_dir)
    ctx = subject_blocks(pilot1_dir)
    candidates = embed_candidates(out_dir)
    embed_dir = out_dir / "embed"
    embed_dir.mkdir(parents=True, exist_ok=True)

    gens = []
    for model_dir in list(args.models):
        for arm in OE.ARMS:
            path = out_dir / "gen" / model_dir / f"completions_{arm}.jsonl"
            if path.exists():
                gens += S.read_jsonl(path)
    if not gens:
        raise fatal("no generations on disk to embed")

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise fatal(
            "sentence-transformers is not installed. Spec section 3: channel 1 "
            "needs a one-time CPU-only torch + sentence-transformers install, "
            "and it is a NEW DEPENDENCY named in the report. "
            f"({exc})")

    results = {}
    for cand in candidates:
        name = cand["name"]
        revision = cand.get("revision")
        print(f"[embed] loading {name} (CPU, revision {revision or 'unpinned'})")
        model = SentenceTransformer(name, device="cpu", revision=revision)
        real_texts = {iid: it["real_answer_verbatim"] for iid, it in items.items()}
        real_ids = sorted(real_texts)
        real_vecs = dict(zip(real_ids,
                             _encode(model, [real_texts[i] for i in real_ids],
                                     name, "passage")))
        gen_vecs = _encode(model, [g["text"] for g in gens], name, "query")
        rows = []
        for g, vec in zip(gens, gen_vecs):
            rows.append({
                "item_id": g["item_id"], "canonical_id": g["canonical_id"],
                "arm": g["arm"], "model": g["model"],
                "embedding_model": name, "revision": revision,
                "cosine_to_real": round(_cosine(vec, real_vecs[g["item_id"]]), 6),
                "truncated": g.get("truncated"),
                "answer_words": g.get("answer_words"),
            })
        # Spec section 8 diagnostic: similarity between the OWN arm's grounding
        # text and the real answer, per item. If this alone tracks the own-arm
        # score, channel 1's separation is suspect.
        diag_ids = sorted({g["canonical_id"] for g in gens})
        diag_vecs = dict(zip(diag_ids,
                             _encode(model, [ctx[c]["twin_block"]
                                             for c in diag_ids], name,
                                     "query")))
        diagnostic = [{
            "item_id": iid, "canonical_id": items[iid]["canonical_id"],
            "embedding_model": name, "revision": revision,
            "cosine_grounding_to_real": round(
                _cosine(diag_vecs[items[iid]["canonical_id"]],
                        real_vecs[iid]), 6),
        } for iid in real_ids if items[iid]["canonical_id"] in diag_vecs]

        safe = name.replace("/", "__")
        S.write_jsonl(embed_dir / f"cosines_{safe}.jsonl", rows)
        S.write_jsonl(embed_dir / f"grounding_diagnostic_{safe}.jsonl",
                      diagnostic)
        per_arm = {}
        for arm in OE.ARMS:
            vals = [r["cosine_to_real"] for r in rows if r["arm"] == arm]
            per_arm[arm] = _mmm(vals, 6)
        own = {r["item_id"]: r["cosine_to_real"] for r in rows
               if r["arm"] == OWN_ARM}
        imp = {r["item_id"]: r["cosine_to_real"] for r in rows
               if r["arm"] == IMPOSTER_ARM}
        paired = [own[i] - imp[i] for i in sorted(set(own) & set(imp))]
        results[name] = {"revision": revision,
                         "per_arm": per_arm, "n_rows": len(rows),
                         "own_minus_imposter_paired": _mmm(paired, 6),
                         "n_items_own_gt_imposter":
                             f"{sum(1 for d in paired if d > 0)}/{len(paired)}",
                         "diagnostic": _mmm(
                             [d["cosine_grounding_to_real"] for d in diagnostic],
                             6)}
        print(f"[embed] {name}: {len(rows)} cosines")

    S.write_json(embed_dir / "embed_summary.json", {
        "pilot": PILOT_BANNER,
        "candidates": candidates,
        "selection_rule": "Score all four; pick the candidate with the "
                          "cleanest own-minus-imposter separation on the "
                          "primary model; ties break toward the smaller, more "
                          "standard model. Dev subjects are for tuning, so "
                          "this selection is legitimate and is recorded here.",
        "never_an_api_model": True, "device": "cpu",
        "results": results, "embedded_utc": now()})
    return 0


# ---------------------------------------------------------------------------
# Phase 5: the C4 validation-gate report (spec section 7 format)
# ---------------------------------------------------------------------------

OWN_ARM = "twin_redacted"
IMPOSTER_ARM = "imposter_redacted"
BOOTSTRAP_ITERS = 10000
BOOTSTRAP_SEED = 20260727


def _bootstrap_ci(pairs, iters: int = BOOTSTRAP_ITERS,
                  seed: int = BOOTSTRAP_SEED):
    """95% CI on a paired mean difference, resampling SUBJECTS, not items.

    ``pairs`` maps subject id -> list of per-item differences. Clustering by
    subject is the honest unit here: 17 items over 5 subjects, so item-level
    resampling would pretend to more independence than exists.
    """
    clusters = [v for v in pairs.values() if v]
    if len(clusters) < 2:
        return None, None
    rng = random.Random(seed)
    means = []
    for _ in range(iters):
        drawn = [rng.choice(clusters) for _ in clusters]
        flat = [x for c in drawn for x in c]
        if flat:
            means.append(sum(flat) / len(flat))
    if not means:
        return None, None
    means.sort()
    lo = means[int(0.025 * len(means))]
    hi = means[min(len(means) - 1, int(0.975 * len(means)))]
    return round(lo, 4), round(hi, 4)


def _tvd(a: dict, b: dict) -> float:
    """Total variation distance between two label distributions (B8)."""
    keys = set(a) | set(b)
    na, nb = sum(a.values()), sum(b.values())
    if not na or not nb:
        return float("nan")
    return round(0.5 * sum(abs(a.get(k, 0) / na - b.get(k, 0) / nb)
                           for k in keys), 4)


def channel1_table(out_dir: Path, embedding_model: str) -> list[dict]:
    safe = embedding_model.replace("/", "__")
    path = out_dir / "embed" / f"cosines_{safe}.jsonl"
    return S.read_jsonl(path) if path.exists() else []


def _score_rows_to_channel(rows, value_key: str) -> dict:
    """Per (model, arm) means plus the paired own-minus-imposter reading."""
    by_model: dict[str, dict] = {}
    for row in rows:
        model = row.get("model") or row.get("scored_model_dir")
        by_model.setdefault(model, {}).setdefault(row["arm"], []).append(row)
    out = {}
    for model, arms in by_model.items():
        means = {arm: (round(sum(r[value_key] for r in rs) / len(rs), 4)
                       if rs else None) for arm, rs in arms.items()}
        own = {r["item_id"]: r for r in arms.get(OWN_ARM, [])}
        imp = {r["item_id"]: r for r in arms.get(IMPOSTER_ARM, [])}
        pairs: dict[str, list] = {}
        for iid in sorted(set(own) & set(imp)):
            diff = own[iid][value_key] - imp[iid][value_key]
            pairs.setdefault(own[iid]["canonical_id"], []).append(diff)
        flat = [d for v in pairs.values() for d in v]
        lo, hi = _bootstrap_ci(pairs)
        signs = sum(1 for v in pairs.values() if sum(v) / len(v) > 0)
        out[model] = {
            "per_arm_mean": means,
            "n_paired_items": len(flat),
            "own_minus_imposter": (round(sum(flat) / len(flat), 4)
                                   if flat else None),
            "ci95": [lo, hi],
            "subjects_with_own_gt_imposter": f"{signs}/{len(pairs)}",
            "contamination_meter": (
                None if means.get("zeroinfo_named") is None
                or means.get("zeroinfo_redacted") is None
                else round(means["zeroinfo_named"]
                           - means["zeroinfo_redacted"], 4)),
        }
    return out


REPORT_HEADER = """# OE-1 — open-ended dev pilot report (Amendment 3 C4 gate)

{banner}

**Directional, not powered.** 17 items over 5 dev subjects, one of which
(C01677) contributes a single item. Subject-level readings for C01677 are
noise; that is said here, not discovered later. No magnitude number in this
report is a claim — magnitude bars are set only after these measurements (C5).

Contract: {contract}

Scored claim: {claim}

Generated {when}.
"""


def cmd_report(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or OE_DIR)
    summary = json.loads((out_dir / "build_summary.json").read_text(
        encoding="utf-8"))
    embedding_model = args.embedding_model or embed_candidates(out_dir)[0]["name"]

    c1_rows = channel1_table(out_dir, embedding_model)
    c1 = _score_rows_to_channel(c1_rows, "cosine_to_real")

    judgements = []
    jpath = out_dir / "judge" / "judgements.jsonl"
    if jpath.exists():
        judgements = S.read_jsonl(jpath)
    for row in judgements:
        row["model"] = row.get("scored_model_dir")
        row["stance_same"] = 1.0 if row.get("label") == "SAME" else 0.0
    judged = [r for r in judgements if r.get("label") in ("SAME", "DIFFERENT")]
    c2 = _score_rows_to_channel(judged, "stance_same")

    unclear = {}
    for row in judgements:
        stat = unclear.setdefault(row["arm"], {lab: 0 for lab in LABELS})
        if row.get("label"):
            stat[row["label"]] += 1
    unclear_rates = {
        arm: {"unclear_rate": (round(s["UNCLEAR"] / max(1, sum(s.values())), 4)),
              "counts": s}
        for arm, s in unclear.items()}
    tvd = {arm: _tvd(unclear.get(arm, {}), unclear.get(IMPOSTER_ARM, {}))
           for arm in unclear}

    truncation = {}
    for model_dir in list(args.models):
        for arm in OE.ARMS:
            path = out_dir / "gen" / model_dir / f"completions_{arm}.jsonl"
            if not path.exists():
                continue
            rows = S.read_jsonl(path)
            truncation.setdefault(model_dir, {})[arm] = {
                "n": len(rows),
                "truncation_rate": round(
                    sum(1 for r in rows if r.get("truncated")) / len(rows), 4),
                "over_word_cap": sum(1 for r in rows if r.get("over_word_cap")),
                "era_violations": sum(1 for r in rows
                                      if r.get("era_violations")),
            }

    def _direction(chan):
        vals = [v["own_minus_imposter"] for v in chan.values()
                if v["own_minus_imposter"] is not None]
        return bool(vals) and all(v > 0 for v in vals)

    primary_c1 = c1.get(PRIMARY_MODEL, {})
    primary_c2 = c2.get(PRIMARY_MODEL, {})
    both_positive = (primary_c1.get("own_minus_imposter") or 0) > 0 and \
                    (primary_c2.get("own_minus_imposter") or 0) > 0
    reading = "PASS" if both_positive else "PAUSE"

    lines = [REPORT_HEADER.format(
        banner=PILOT_BANNER, contract=CONTRACT, claim=SCORED_CLAIM,
        when=now())]
    lines.append("\n## Core table\n")
    lines.append("| channel | model | own mean | imposter mean | "
                 "own-imposter (95% CI) | zero-info mean | subjects own>imp |")
    lines.append("|---|---|---|---|---|---|---|")
    for label, chan in (("1 embedding", c1), ("2 stance", c2)):
        for model, v in sorted(chan.items()):
            m = v["per_arm_mean"]
            lines.append(
                f"| {label} | {model} | {m.get(OWN_ARM)} | "
                f"{m.get(IMPOSTER_ARM)} | {v['own_minus_imposter']} "
                f"({v['ci95'][0]}, {v['ci95'][1]}) | "
                f"{m.get('zeroinfo_redacted')} | "
                f"{v['subjects_with_own_gt_imposter']} |")
    lines.append("\n## Per-arm raw scores, both channels\n")
    lines.append("```json")
    lines.append(json.dumps({"channel1": c1, "channel2": c2}, indent=1))
    lines.append("```")
    lines.append("\n## UNCLEAR rates per arm (denominator excludes UNCLEAR)\n")
    lines.append("```json")
    lines.append(json.dumps({"per_arm": unclear_rates,
                             "tvd_vs_imposter": tvd}, indent=1))
    lines.append("```")
    lines.append("\n## Truncation, word cap and era violations per arm\n")
    lines.append("```json")
    lines.append(json.dumps(truncation, indent=1))
    lines.append("```")
    lines.append("\n## Reading\n")
    if reading == "PASS":
        lines.append(
            "**PASS (pre-written).** own > imposter in the pre-registered "
            "direction on the primary model in BOTH channels. Next: fill the "
            "bar-lock addendum's [TO FILL] slots and run the owner's "
            ">=50-label judge spot-check (precondition 6).")
    else:
        lines.append(
            "**PAUSE (pre-written).** The direction is absent on the primary "
            "model, or the two channels disagree on direction. **Stage 2 "
            "pauses for a design review** per C4.3. This report is the record; "
            "no new instrument is reached for without a new amendment. A pause "
            "is a finding about the instrument, reported with the same care as "
            "a pass.")
    lines.append(f"\nChannel directions agree across models: channel 1 "
                 f"{_direction(c1)}, channel 2 {_direction(c2)}.\n")
    lines.append("\n## Build and cost record\n")
    lines.append("```json")
    lines.append(json.dumps({
        "build": {k: summary.get(k) for k in
                  ("n_items", "n_prompts", "item_types",
                   "delta_bins_smoke_check", "generation", "judge")},
        "embedding_model_reported": embedding_model,
        "api_budget_usd": API_BUDGET_USD,
        "node_hour_budget": NODE_HOUR_BUDGET,
    }, indent=1))
    lines.append("```")
    path = out_dir / "PILOT_REPORT_OE1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[report] reading: {reading}")
    print(f"[report] -> {rel(path)}")
    return 0


# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pilot1-dir", default=None)
    ap.add_argument("--pilot4-dir", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--spec", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("build").set_defaults(fn=cmd_build)

    p_g = sub.add_parser("gen-flashlite")
    p_g.add_argument("--force", action="store_true")
    p_g.add_argument("--call-cap", type=int, default=DEFAULT_CALL_CAP)
    p_g.add_argument("--skip-cost", action="store_true")
    p_g.set_defaults(fn=cmd_gen_flashlite, client=None)

    p_i = sub.add_parser("ingest-gemma")
    p_i.add_argument("--nodedir", required=True)
    p_i.set_defaults(fn=cmd_ingest_gemma)

    p_j = sub.add_parser("judge")
    p_j.add_argument("--call-cap", type=int, default=DEFAULT_CALL_CAP)
    p_j.add_argument("--skip-cost", action="store_true")
    p_j.add_argument("--models", nargs="+", default=["gemma", "flashlite"],
                     help="generation directories under gen/ to judge")
    p_j.add_argument("--tag", default=None,
                     help="suffix for this pass's files and run_id, e.g. v2; "
                          "an earlier pass is a record and is never "
                          "overwritten")
    p_j.add_argument("--force", action="store_true")
    p_j.add_argument("--determinism-probe", type=int, default=0,
                     metavar="N",
                     help="run the first N calls twice, compare labels, write "
                          "the probe and exit WITHOUT running the batch")
    p_j.set_defaults(fn=cmd_judge, client=None)

    p_e = sub.add_parser("embed")
    p_e.add_argument("--models", nargs="+", default=["gemma", "flashlite"])
    p_e.set_defaults(fn=cmd_embed)

    p_r = sub.add_parser("report")
    p_r.add_argument("--models", nargs="+", default=["gemma", "flashlite"])
    p_r.add_argument("--embedding-model", default=None)
    p_r.set_defaults(fn=cmd_report)

    args = ap.parse_args(argv)
    if getattr(args, "out_dir", None) is None:
        args.out_dir = str(OE_DIR)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
