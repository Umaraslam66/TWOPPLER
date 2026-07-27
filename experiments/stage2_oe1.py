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
    """Join the node's completions back to their items (no GPU, no API).

    Also bills the GPU job: ``--node-hours`` comes from ``sacct`` ElapsedRaw on
    a whole node (Leonardo bills per node regardless of how many of its 4 GPUs
    a job uses), and every attempt is accumulated, not just the one that
    worked.
    """
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
            "tokens_in": int(got.get("tokens_in") or 0), "tokens_out": tout,
        })
    for arm, rows in per_arm.items():
        S.write_jsonl(gen_dir / f"completions_{arm}.jsonl", rows)
        print(f"[ingest-gemma] {arm:20s} {len(rows)} generations, "
              f"{sum(1 for r in rows if r['truncated'])} truncated")

    node_hours = getattr(args, "node_hours", None)
    if node_hours is not None:
        if node_hours > NODE_HOUR_BUDGET:
            raise fatal(f"billed {node_hours} node-hours exceeds the "
                        f"{NODE_HOUR_BUDGET} cap")
        n_rows = sum(len(v) for v in per_arm.values())
        append_cost_log(build_cost_entry(
            run_id="stage2_oe1/gen_gemma", model=P2.MODEL_LABEL,
            split="stage2_openended", variant="oe1_gemma_generation",
            n_persons=len({r["canonical_id"] for v in per_arm.values()
                           for r in v}),
            n_calls=n_rows, n_retries=0, n_parse_failures=0,
            tokens_in=sum(int(r.get("tokens_in") or 0)
                          for v in per_arm.values() for r in v),
            tokens_out=sum(int(r.get("tokens_out") or 0)
                           for v in per_arm.values() for r in v),
            backend="leonardo-batch", node_hours=node_hours), COST_LOG)
        print(f"[ingest-gemma] billed {node_hours} node-hours "
              f"(cap {NODE_HOUR_BUDGET}), job {getattr(args,'job_id',None)}")
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
ZERO_RED = "zeroinfo_redacted"
ZERO_NAMED = "zeroinfo_named"
BOOTSTRAP_ITERS = 10000
BOOTSTRAP_SEED = 20260727

#: gen/<dir> -> the model version string that produced it.
GEN_DIR_MODEL = {"gemma": PRIMARY_MODEL, "flashlite": ROBUSTNESS_MODEL}
#: judge tag -> the gen dir it judged.
JUDGE_TAG_DIR = {"v2": "flashlite", "gemma": "gemma"}


def _bootstrap_ci(pairs, iters: int = BOOTSTRAP_ITERS,
                  seed: int = BOOTSTRAP_SEED):
    """95% CI on a paired mean difference, resampling SUBJECTS, not items.

    ``pairs`` maps subject id -> list of per-item differences. Clustering by
    subject is the honest unit here: 17 items over 5 subjects, so item-level
    resampling would pretend to more independence than exists. With 5 clusters
    the interval is coarse by construction and is reported as directional.
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
    return (round(means[int(0.025 * len(means))], 4),
            round(means[min(len(means) - 1, int(0.975 * len(means)))], 4))


def _tvd(a: dict, b: dict) -> float:
    """Total variation distance between two label distributions (B8)."""
    keys = set(a) | set(b)
    na, nb = sum(a.values()), sum(b.values())
    if not na or not nb:
        return None
    return round(0.5 * sum(abs(a.get(k, 0) / na - b.get(k, 0) / nb)
                           for k in keys), 4)


def _paired_block(per_arm_values: dict, own: dict, imposter: dict,
                  subject_of: dict) -> dict:
    """One channel x model row: per-arm means, the paired contrast, its CI."""
    pairs: dict = {}
    for iid in sorted(set(own) & set(imposter)):
        pairs.setdefault(subject_of[iid], []).append(own[iid] - imposter[iid])
    flat = [d for v in pairs.values() for d in v]
    lo, hi = _bootstrap_ci(pairs)
    signs = sum(1 for v in pairs.values() if sum(v) / len(v) > 0)
    means = {arm: (round(sum(v) / len(v), 4) if v else None)
             for arm, v in per_arm_values.items()}
    return {
        "per_arm_mean": means,
        "n_paired_items": len(flat),
        "n_subject_clusters": len(pairs),
        "own_minus_imposter": round(sum(flat) / len(flat), 4) if flat else None,
        "ci95": [lo, hi],
        "subjects_own_gt_imposter": f"{signs}/{len(pairs)}",
        "contamination_meter": (
            None if means.get(ZERO_NAMED) is None
            or means.get(ZERO_RED) is None
            else round(means[ZERO_NAMED] - means[ZERO_RED], 4)),
    }


def load_cosines(out_dir: Path, candidate: str) -> list:
    safe = candidate.replace("/", "__")
    path = out_dir / "embed" / f"cosines_{safe}.jsonl"
    return S.read_jsonl(path) if path.exists() else []


def load_diagnostic(out_dir: Path, candidate: str) -> list:
    safe = candidate.replace("/", "__")
    path = out_dir / "embed" / f"grounding_diagnostic_{safe}.jsonl"
    return S.read_jsonl(path) if path.exists() else []


def _pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return round(num / den, 3) if den else None


def channel1_all(out_dir: Path, items: dict) -> dict:
    """Channel 1 for every candidate x model, plus the section-8 diagnostic."""
    subject_of = {iid: it["canonical_id"] for iid, it in items.items()}
    out = {}
    for cand in embed_candidates(out_dir):
        name = cand["name"]
        rows = load_cosines(out_dir, name)
        diag = {d["item_id"]: d["cosine_grounding_to_real"]
                for d in load_diagnostic(out_dir, name)}
        per_model = {}
        for model in (PRIMARY_MODEL, ROBUSTNESS_MODEL):
            rs = [r for r in rows if r["model"] == model]
            if not rs:
                continue
            per_arm = {arm: [r["cosine_to_real"] for r in rs if r["arm"] == arm]
                       for arm in OE.ARMS}
            own = {r["item_id"]: r["cosine_to_real"] for r in rs
                   if r["arm"] == OWN_ARM}
            imp = {r["item_id"]: r["cosine_to_real"] for r in rs
                   if r["arm"] == IMPOSTER_ARM}
            block = _paired_block(per_arm, own, imp, subject_of)
            ids = sorted(set(own) & set(diag))
            block["diagnostic_pearson_vs_own_arm"] = _pearson(
                [diag[i] for i in ids], [own[i] for i in ids])
            per_model[model] = block
        out[name] = {"revision": cand.get("revision"),
                     "diagnostic": _mmm(list(diag.values()), 6),
                     "per_model": per_model}
    return out


#: PILOT_SPEC section 3, the selection rule stated before any run.
SELECTION_RULE_TEXT = (
    "Score all four on the pilot; pick the candidate with the cleanest "
    "own-minus-imposter separation on the primary model; ties break toward "
    "the smaller, more standard model. Dev subjects are for tuning, so this "
    "selection is legitimate -- it is recorded in the pilot report and the "
    "winner is pinned in the addendum.")


def select_embedding_candidate(c1: dict) -> dict:
    """Spec section 3 selection rule, applied in the open.

    "Score all four on the pilot; pick the candidate with the cleanest
    own-minus-imposter separation on the primary model; ties break toward the
    smaller, more standard model." Absolute cosine LEVEL is not comparable
    across models (each has its own similarity scale), so the rule is read on
    the separation, exactly as written. The sanity-check candidate
    (all-MiniLM-L6-v2) is excluded from selection by the spec: "never the
    pinned channel".
    """
    ranked = []
    for name, doc in c1.items():
        block = doc["per_model"].get(PRIMARY_MODEL)
        if not block or block["own_minus_imposter"] is None:
            continue
        eligible = "MiniLM" not in name
        ranked.append({
            "candidate": name, "revision": doc.get("revision"),
            "eligible": eligible,
            "own_minus_imposter": block["own_minus_imposter"],
            "ci95": block["ci95"],
            "subjects_own_gt_imposter": block["subjects_own_gt_imposter"],
            "diagnostic_pearson": block["diagnostic_pearson_vs_own_arm"],
        })
    ranked.sort(key=lambda r: (-r["own_minus_imposter"], r["candidate"]))
    winners = [r for r in ranked if r["eligible"]]
    return {
        "rule": SELECTION_RULE_TEXT,
        "ranked_on_primary_model": ranked,
        "excluded_from_selection": [r["candidate"] for r in ranked
                                    if not r["eligible"]],
        "exclusion_reason": "PILOT_SPEC section 3 names all-MiniLM-L6-v2 a "
                            "sanity check only -- 'never the pinned channel'.",
        "selected": winners[0]["candidate"] if winners else None,
        "selected_revision": winners[0]["revision"] if winners else None,
    }


def channel2_all(out_dir: Path, items: dict) -> dict:
    """Channel 2 per model: stance match, UNCLEAR rates, paired contrast, TVD."""
    subject_of = {iid: it["canonical_id"] for iid, it in items.items()}
    out = {}
    for tag, gen_dir in JUDGE_TAG_DIR.items():
        path = out_dir / "judge" / f"judgements_{tag}.jsonl"
        if not path.exists():
            continue
        rows = S.read_jsonl(path)
        model = GEN_DIR_MODEL[gen_dir]
        label = {(r["arm"], r["item_id"]): r["label"] for r in rows}
        counts = {arm: {lab: sum(1 for r in rows
                                 if r["arm"] == arm and r["label"] == lab)
                        for lab in LABELS} for arm in OE.ARMS}
        # C2.3: UNCLEAR is excluded from the match denominator; its rate is
        # printed beside every rate rather than folded into one.
        scored = {arm: [1.0 if label[(arm, i)] == "SAME" else 0.0
                        for i in items
                        if label.get((arm, i)) in ("SAME", "DIFFERENT")]
                  for arm in OE.ARMS}
        own = {i: (1.0 if label[(OWN_ARM, i)] == "SAME" else 0.0)
               for i in items if label.get((OWN_ARM, i)) in ("SAME", "DIFFERENT")}
        imp = {i: (1.0 if label[(IMPOSTER_ARM, i)] == "SAME" else 0.0)
               for i in items
               if label.get((IMPOSTER_ARM, i)) in ("SAME", "DIFFERENT")}
        block = _paired_block(scored, own, imp, subject_of)
        block["label_counts"] = counts
        block["unclear_rate"] = {
            arm: round(counts[arm]["UNCLEAR"] / max(1, sum(counts[arm].values())), 4)
            for arm in OE.ARMS}
        block["match_denominator"] = {arm: len(v) for arm, v in scored.items()}
        # B8: TVD is BETWEEN ARMS -- the real answer carries no label of its
        # own, so there is no reference distribution to compare an arm to.
        block["tvd_vs_own_arm"] = {
            arm: _tvd(counts[arm], counts[OWN_ARM]) for arm in OE.ARMS}
        block["judge_tag"] = tag
        out[model] = block
    return out


def generation_stats(out_dir: Path) -> dict:
    stats = {}
    for gen_dir, model in GEN_DIR_MODEL.items():
        per_arm = {}
        for arm in OE.ARMS:
            path = out_dir / "gen" / gen_dir / f"completions_{arm}.jsonl"
            if not path.exists():
                continue
            rows = S.read_jsonl(path)
            words = [r["answer_words"] for r in rows]
            per_arm[arm] = {
                "n": len(rows),
                "words": _mmm(words),
                "n_over_word_cap": sum(1 for r in rows if r.get("over_word_cap")),
                "truncation_rate": round(
                    sum(1 for r in rows if r.get("truncated")) / len(rows), 4),
                "n_empty": sum(1 for r in rows if not (r.get("text") or "").strip()),
                "n_era_violations": sum(1 for r in rows if r.get("era_violations")),
                "max_tokens_out": max(int(r.get("tokens_out") or 0) for r in rows),
            }
        if per_arm:
            stats[model] = per_arm
    return stats


def cost_table(cost_log: Path) -> dict:
    rows = [r for r in S.read_jsonl(cost_log)
            if str(r.get("run_id", "")).startswith("stage2_oe1/")] \
        if Path(cost_log).exists() else []
    per_run: dict = {}
    for r in rows:
        entry = per_run.setdefault(r["run_id"], {
            "model": r["model"], "backend": r["backend"], "n_calls": 0,
            "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
            "node_hours": 0.0, "per_arm": {}})
        entry["n_calls"] += r["n_calls"]
        entry["tokens_in"] += r["tokens_in"]
        entry["tokens_out"] += r["tokens_out"]
        entry["cost_usd"] += r["cost_usd"] or 0.0
        entry["node_hours"] += r["node_hours"] or 0.0
        entry["per_arm"][r["variant"]] = {
            "n_calls": r["n_calls"], "cost_usd": r["cost_usd"],
            "node_hours": r["node_hours"]}
    for e in per_run.values():
        e["cost_usd"] = round(e["cost_usd"], 6)
        e["node_hours"] = round(e["node_hours"], 5)
    return {
        "per_run": per_run,
        "total_cost_usd": round(sum(e["cost_usd"] for e in per_run.values()), 6),
        "total_node_hours": round(sum(e["node_hours"] for e in per_run.values()), 5),
        "api_budget_usd": API_BUDGET_USD,
        "node_hour_budget": NODE_HOUR_BUDGET,
    }


def extract_spec_readings(spec_path: Path) -> dict:
    """The two pre-written C4 readings from PILOT_SPEC section 7, VERBATIM."""
    lines = Path(spec_path).read_text(encoding="utf-8").splitlines()
    out = {}
    for key, marker in (("pass", "- **PASS reading"),
                        ("pause", "- **PAUSE reading")):
        start = next((i for i, l in enumerate(lines)
                      if l.startswith(marker)), None)
        if start is None:
            raise fatal(f"PILOT_SPEC section 7 has no {marker!r} bullet")
        end = start + 1
        while end < len(lines) and lines[end].startswith("  "):
            end += 1
        out[key] = "\n".join(lines[start:end])
    return out


# ---------------------------------------------------------------------------
# The C4 validation-gate report (PILOT_SPEC section 7 format)
# ---------------------------------------------------------------------------

#: Items quoted in full in the report. Five DIFFERENT items, one per Q-A dev
#: subject, so the reader sees every subject once.
EXAMPLE_ITEMS = (
    "C00792:NPR-19884:6",
    "C01677:NPR-8791:77",
    "C02006:NPR-14829:29",
    "C02013:NPR-9480:45",
    "C02124:NPR-12184:4",
)

VERDICT_PLACEHOLDER = """## C4 verdict — [ORCHESTRATOR APPLIES]

*This section is deliberately empty. The two readings above are the
pre-written ones from PILOT_SPEC section 7, quoted verbatim, with the gate
inputs laid beside them. Choosing between them is the orchestrator's call
against the pre-registered bar, not this driver's and not the implementer's.*
"""


def _fmt(x, nd=4):
    return "—" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def _core_table(c1: dict, c2: dict, pinned: str) -> list:
    rows = ["| channel | model | own mean | imposter mean | own−imposter "
            "(95% CI) | subj own>imp | zeroinfo_red | zeroinfo_named | "
            "contamination |",
            "|---|---|---|---|---|---|---|---|---|"]
    for model in (PRIMARY_MODEL, ROBUSTNESS_MODEL):
        b = c1.get(pinned, {}).get("per_model", {}).get(model)
        if not b:
            continue
        m = b["per_arm_mean"]
        rows.append(
            f"| 1 embedding | {model} | {_fmt(m[OWN_ARM])} | "
            f"{_fmt(m[IMPOSTER_ARM])} | {_fmt(b['own_minus_imposter'])} "
            f"({_fmt(b['ci95'][0])}, {_fmt(b['ci95'][1])}) | "
            f"{b['subjects_own_gt_imposter']} | {_fmt(m[ZERO_RED])} | "
            f"{_fmt(m[ZERO_NAMED])} | {_fmt(b['contamination_meter'])} |")
    for model in (PRIMARY_MODEL, ROBUSTNESS_MODEL):
        b = c2.get(model)
        if not b:
            continue
        m = b["per_arm_mean"]
        rows.append(
            f"| 2 stance | {model} | {_fmt(m[OWN_ARM])} | "
            f"{_fmt(m[IMPOSTER_ARM])} | {_fmt(b['own_minus_imposter'])} "
            f"({_fmt(b['ci95'][0])}, {_fmt(b['ci95'][1])}) | "
            f"{b['subjects_own_gt_imposter']} | {_fmt(m[ZERO_RED])} | "
            f"{_fmt(m[ZERO_NAMED])} | {_fmt(b['contamination_meter'])} |")
    return rows


def cmd_report(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or OE_DIR)
    summary = json.loads((out_dir / "build_summary.json").read_text(
        encoding="utf-8"))
    items = load_items(out_dir)
    c1 = channel1_all(out_dir, items)
    c2 = channel2_all(out_dir, items)
    selection = select_embedding_candidate(c1)
    pinned = args.embedding_model or selection["selected"] \
        or embed_candidates(out_dir)[0]["name"]
    gens = generation_stats(out_dir)
    costs = cost_table(COST_LOG)
    readings = extract_spec_readings(Path(getattr(args, "spec", None) or SPEC_PATH))
    jsum = {}
    for tag in JUDGE_TAG_DIR:
        p = out_dir / "judge" / f"judge_{tag}_summary.json"
        if p.exists():
            jsum[tag] = json.loads(p.read_text(encoding="utf-8"))

    L = []
    A = L.append
    A("# OE-1 — open-ended dev pilot, measurement report")
    A("")
    A(f"**{PILOT_BANNER}**")
    A("")
    A("**Directional, not powered.** 17 items over 5 Q–A dev subjects, one of "
      "which (C01677) contributes a single item — subject-level readings for "
      "it are noise, and that is said here rather than discovered later. No "
      "magnitude number in this report is a claim: magnitude bars are set only "
      "after these measurements (Amendment 3 C5). Stage 1/dev-subject work is "
      "for development and tuning; nothing here answers a pre-registered bar.")
    A("")
    A(f"- Contract: {CONTRACT}")
    A(f"- Scored claim: {SCORED_CLAIM}")
    A(f"- Generated {now()}")
    A("")
    A("## 1. Instrument and configuration")
    A("")
    A("| item | value |")
    A("|---|---|")
    A(f"| primary scored model | `{PRIMARY_MODEL}` (vLLM TP=4, "
      f"max_model_len {P2.MAX_MODEL_LEN}, seed 0) |")
    A(f"| robustness scored model | `{ROBUSTNESS_MODEL}` (Google AI Studio) |")
    A(f"| generation settings, both | temperature {GEN_TEMPERATURE}, "
      f"max_output_tokens {OE.MAX_OUTPUT_TOKENS}, answer cap "
      f"{OE.MAX_ANSWER_WORDS} words |")
    A(f"| instruction tail | byte-identical across all five arms, sha256 "
      f"`{OE.INSTRUCTION_SHA256}` |")
    A(f"| judge | `{JUDGE_MODEL}`, temperature {JUDGE_TEMPERATURE}, "
      f"**thinking_budget {JUDGE_THINKING_BUDGET}**, max_output_tokens "
      f"{JUDGE_MAX_OUTPUT_TOKENS} |")
    A(f"| rubric | r1 verbatim from PILOT_SPEC section 4, sha256 "
      f"`{summary['judge']['rubric_sha256']}` |")
    A(f"| judge call order | randomized, seed {JUDGE_ORDER_SEED}; one "
      "candidate per call; blind to arm and model; all three texts "
      "GUEST-redacted |")
    A(f"| grounding budget | {OE.GROUNDING_BUDGET_WORDS} words, "
      "most-recent-first fill, rendered chronologically |")
    A(f"| items | {summary['n_items']} over 5 subjects; "
      + ", ".join(f"{v} {k.replace('_', ' ')}"
                  for k, v in sorted(summary["item_types"].items())) + " |")
    A("")
    A("Embedding candidates, pinned by HF revision (local CPU, never an API "
      "model, never a scored model):")
    A("")
    A("| candidate | revision |")
    A("|---|---|")
    for cand in embed_candidates(out_dir):
        A(f"| `{cand['name']}` | `{cand.get('revision')}` |")
    A("")
    A("## 2. Generation behaviour, per arm, both models")
    A("")
    A("| model | arm | n | words min/mean/max | >150w | truncation rate | "
      "empty | era violations | max tokens_out |")
    A("|---|---|---|---|---|---|---|---|---|")
    for model, per_arm in gens.items():
        for arm in OE.ARMS:
            s = per_arm.get(arm)
            if not s:
                continue
            w = s["words"]
            A(f"| {model} | {arm} | {s['n']} | "
              f"{w['min']}/{w['mean']}/{w['max']} | {s['n_over_word_cap']} | "
              f"{s['truncation_rate']} | {s['n_empty']} | "
              f"{s['n_era_violations']} | {s['max_tokens_out']} |")
    A("")
    A("## 3. C4 core table — per channel × model")
    A("")
    A(f"Channel 1 is reported on the pinned candidate `{pinned}` (selection in "
      "section 4). Channel 2 excludes UNCLEAR from the match denominator "
      "(C2.3); per-arm UNCLEAR rates are in section 5. Differences are paired "
      "per item, own vs imposter on the same item; the CI is a bootstrap over "
      "**subjects** (5 clusters), so it is coarse by construction.")
    A("")
    L.extend(_core_table(c1, c2, pinned))
    A("")
    A("Paired-item N per row:")
    A("")
    for model in (PRIMARY_MODEL, ROBUSTNESS_MODEL):
        b1 = c1.get(pinned, {}).get("per_model", {}).get(model)
        b2 = c2.get(model)
        if b1:
            A(f"- channel 1, {model}: {b1['n_paired_items']} items over "
              f"{b1['n_subject_clusters']} subjects")
        if b2:
            A(f"- channel 2, {model}: {b2['n_paired_items']} items over "
              f"{b2['n_subject_clusters']} subjects — an item enters only when "
              "BOTH its own and its imposter generation got a non-UNCLEAR "
              "label, which is why this N and the subject-cluster count are "
              "below channel 1's")
    A("")
    A("## 4. Channel 1 — all four candidates, and the section-3 selection")
    A("")
    A("Absolute cosine LEVEL is not comparable across these models (each has "
      "its own similarity scale), so the selection rule reads the "
      "own−imposter SEPARATION, exactly as the spec words it.")
    A("")
    A("| candidate | model | own | imposter | own−imposter (95% CI) | "
      "subj own>imp | zeroinfo_red | contamination |")
    A("|---|---|---|---|---|---|---|---|")
    for name, doc in c1.items():
        for model in (PRIMARY_MODEL, ROBUSTNESS_MODEL):
            b = doc["per_model"].get(model)
            if not b:
                continue
            m = b["per_arm_mean"]
            A(f"| `{name.split('/')[-1]}` | {model} | {_fmt(m[OWN_ARM])} | "
              f"{_fmt(m[IMPOSTER_ARM])} | {_fmt(b['own_minus_imposter'])} "
              f"({_fmt(b['ci95'][0])}, {_fmt(b['ci95'][1])}) | "
              f"{b['subjects_own_gt_imposter']} | {_fmt(m[ZERO_RED])} | "
              f"{_fmt(b['contamination_meter'])} |")
    A("")
    A("**Selection rule applied, on the primary model:**")
    A("")
    A(f"> {selection['rule']}")
    A("")
    A("| rank | candidate | own−imposter on primary | eligible |")
    A("|---|---|---|---|")
    for i, r in enumerate(selection["ranked_on_primary_model"], 1):
        A(f"| {i} | `{r['candidate'].split('/')[-1]}` | "
          f"{_fmt(r['own_minus_imposter'])} | "
          f"{'yes' if r['eligible'] else 'NO — sanity check only'} |")
    A("")
    A(f"Excluded: {selection['exclusion_reason']}")
    A("")
    A(f"**Candidate the rule selects: `{selection['selected']}` "
      f"(revision `{selection['selected_revision']}`).** Recorded here as the "
      "pilot measurement that feeds the addendum; the pin itself happens at "
      "bar-lock, after owner review.")
    A("")
    A("### Section-8 diagnostic — does grounding-to-answer similarity alone "
      "explain the own-arm score?")
    A("")
    A("Declared risk 1: the own twin's grounding shares the subject's "
      "recurring topics and vocabulary with the real answer, and some of that "
      "is trivial topic recurrence rather than person signal. The diagnostic "
      "is cosine(own-arm grounding text, real answer) per item, reported as a "
      "covariate.")
    A("")
    A("| candidate | diagnostic mean | min | max | Pearson r vs own-arm score "
      "(primary model) |")
    A("|---|---|---|---|---|")
    for name, doc in c1.items():
        d = doc["diagnostic"]
        b = doc["per_model"].get(PRIMARY_MODEL, {})
        A(f"| `{name.split('/')[-1]}` | {_fmt(d['mean'])} | {_fmt(d['min'])} | "
          f"{_fmt(d['max'])} | {_fmt(b.get('diagnostic_pearson_vs_own_arm'), 3)} |")
    A("")
    A("Caveat on this diagnostic, stated rather than buried: the grounding "
      f"block is ~{OE.GROUNDING_BUDGET_WORDS} words and every candidate "
      "encoder has a 512-token window, so the grounding is truncated to its "
      "opening excerpts before encoding. The number describes the head of the "
      "grounding, not all of it.")
    A("")
    A("## 5. Channel 2 — stance labels, UNCLEAR rates, and B8 divergence")
    A("")
    A("| model | arm | SAME | DIFFERENT | UNCLEAR | match rate (UNCLEAR "
      "excluded) | denominator | UNCLEAR rate |")
    A("|---|---|---|---|---|---|---|---|")
    for model in (PRIMARY_MODEL, ROBUSTNESS_MODEL):
        b = c2.get(model)
        if not b:
            continue
        for arm in OE.ARMS:
            c = b["label_counts"][arm]
            A(f"| {model} | {arm} | {c['SAME']} | {c['DIFFERENT']} | "
              f"{c['UNCLEAR']} | {_fmt(b['per_arm_mean'][arm])} | "
              f"{b['match_denominator'][arm]} | {b['unclear_rate'][arm]} |")
    A("")
    A("**Material between-arm UNCLEAR differences, flagged per C2.3.** " +
      _unclear_flag(c2))
    A("")
    A("**B8 — population-level divergence over stance categories.** The real "
      "answer carries no stance label of its own, so there is no reference "
      "distribution to score an arm against; the divergence that exists to be "
      "measured is **between arms**. TVD below is each arm's "
      "SAME/DIFFERENT/UNCLEAR distribution against the own-twin arm's.")
    A("")
    A("| model | arm | TVD vs twin_redacted |")
    A("|---|---|---|")
    for model in (PRIMARY_MODEL, ROBUSTNESS_MODEL):
        b = c2.get(model)
        if not b:
            continue
        for arm in OE.ARMS:
            if arm == OWN_ARM:
                continue
            A(f"| {model} | {arm} | {_fmt(b['tvd_vs_own_arm'][arm])} |")
    A("")
    A("## 6. Contamination meter")
    A("")
    A("`zeroinfo_named − zeroinfo_redacted`, per channel and model — what the "
      "name alone buys a model with no excerpts.")
    A("")
    A("| channel | model | zeroinfo_named | zeroinfo_redacted | meter |")
    A("|---|---|---|---|---|")
    for label, src in (("1 embedding",
                        {m: c1.get(pinned, {}).get("per_model", {}).get(m)
                         for m in (PRIMARY_MODEL, ROBUSTNESS_MODEL)}),
                       ("2 stance", c2)):
        for model, b in src.items():
            if not b:
                continue
            m = b["per_arm_mean"]
            A(f"| {label} | {model} | {_fmt(m[ZERO_NAMED])} | "
              f"{_fmt(m[ZERO_RED])} | {_fmt(b['contamination_meter'])} |")
    A("")
    A("## 7. Verbatim examples")
    A("")
    A("Five different items, one per Q–A dev subject. Each shows the question, "
      "the real held-out answer, and what the own twin and the imposter twin "
      "said, with the judge's label for each.")
    A("")
    gen_cache = {}
    for gd in GEN_DIR_MODEL:
        for arm in OE.ARMS:
            p = out_dir / "gen" / gd / f"completions_{arm}.jsonl"
            if p.exists():
                for r in S.read_jsonl(p):
                    gen_cache[(gd, arm, r["item_id"])] = r
    lab_cache = {}
    for tag, gd in JUDGE_TAG_DIR.items():
        p = out_dir / "judge" / f"judgements_{tag}.jsonl"
        if p.exists():
            for r in S.read_jsonl(p):
                lab_cache[(gd, r["arm"], r["item_id"])] = r
    for n, iid in enumerate(EXAMPLE_ITEMS, 1):
        it = items.get(iid)
        if not it:
            continue
        A(f"### Example {n} — `{iid}` ({it['canonical_id']}, "
          f"{it['item_type']}, donor `{it['donor_id']}`, Δ {it['delta_days']} "
          f"days / bin {it['delta_bin']})")
        A("")
        A(f"**Question.** {R._norm_ws(it['question'])}")
        A("")
        A(f"**Real answer ({it['answer_words']} words).** "
          f"{R._norm_ws(it['real_answer_verbatim'])}")
        A("")
        show = [(OWN_ARM, "own twin"), (IMPOSTER_ARM, "imposter twin")]
        if n == 1:
            show.append((ZERO_RED, "zero-information"))
        for arm, human in show:
            for gd, model in GEN_DIR_MODEL.items():
                g = gen_cache.get((gd, arm, iid))
                if not g:
                    continue
                j = lab_cache.get((gd, arm, iid))
                A(f"**{human} — {model} — judge: "
                  f"{(j or {}).get('label', 'n/a')}** "
                  f"({g['answer_words']} words)")
                A("")
                A(f"> {R._norm_ws(g['text'])}")
                A("")
                if j and j.get("why"):
                    A(f"*Judge WHY:* {j['why']}")
                    A("")
    A("## 8. Carries and anomalies")
    A("")
    A("1. **Era violations.** " + _era_note(gens))
    A("2. **S1 leaves a free-standing intro clause standing, and in one "
      "imposter prompt that clause describes the DONOR.** S1 removes the "
      "clause attached to GUEST; it does not remove a third party's résumé in "
      "the same line, and its pattern misses `GUEST, who ...` when an "
      "abbreviation's full stop truncates the clause before the role word. "
      "Measured: 1 of 17 `imposter_redacted` prompts (subject C01677, donor "
      "C01650) still carries, verbatim, *\"GUEST, who served two tours as "
      "U.S. ambassador to Israel, now at the Brookings Institution\"* and "
      "*\"GUEST, who used to be U.S. ambassador there, as well as assistant "
      "secretary of state for the region and who now directs foreign policy "
      "programs at the Brookings Institution\"*. No NAME survives — the name "
      "guard passes — but that is a donor-identifying résumé sitting in the "
      "arm whose entire job is to withhold identity. Separately, twin prompts "
      "retain co-panellist résumés (*\"Eugene Rivers, a Pentecostal minister, "
      "community activist and co-founder of the city's 10-point Coalition, "
      "and GUEST, [DESCRIPTION REMOVED]\"*), which is a co-occurrence "
      "fingerprint on the subject. Both are scope questions for bar-lock, not "
      "things to patch mid-pilot.")
    A("3. **The zero-information preamble still reads \"Predict which answer "
      "they gave.\"** — forced-choice wording carried over from v1.10, kept "
      "because PILOT_SPEC section 2 freezes every arm's preamble so the "
      "instruction tail stays byte-identical. Measured effect: none visible. "
      "All 34 zero-information generations on both models are fluent "
      "first-person spoken replies; none names an option, restates the task, "
      "or asks which answer to choose.")
    A("4. **S1 was not applied by rounds 1–4.** OE-1 applies it to all five "
      "arms (so a named arm still differs from its redacted counterpart by "
      "exactly one line). OE-1 prompts are therefore not byte-comparable to "
      "round 4's on this dimension.")
    A("5. **Two of the 17 items have no hand-final type.** "
      "`results/stage2_pilot4/item_types.json` covers the 15 items round 3 "
      "built; `C02124:NPR-12184:2` and `C02124:NPR-12184:8` fell to the "
      "documented cue rule and both landed factual_explanation, so the split "
      "reported here is 10 subjective / 7 factual, not the spec's 10 / 5.")
    A("")
    A("## 9. The judge defect, and what was pinned because of it")
    A("")
    A("The first judge pass (v1, `judge/judgements.jsonl`) ran "
      f"`{JUDGE_MODEL}` at max_output_tokens 256 with no thinking setting. "
      "82 of 85 replies came back with the `WHY:` line cut mid-phrase while "
      "`LABEL:` survived. A two-budget probe "
      "(`judge/thinking_budget_probe.json`) found the cause: the model charges "
      "hidden thinking against `max_output_tokens` and did not finish "
      "thinking at either budget — 243 of 256, then 980 of 1024 tokens went "
      "to thoughts, both ending `MAX_TOKENS`. **The label itself moved between "
      "the two budgets at temperature 0** (DIFFERENT → UNCLEAR), so the v1 "
      "labels were a function of the truncation, not only of the rubric.")
    A("")
    A("Owner decision, taken before any re-run: thinking explicitly disabled "
      f"(`thinking_budget={JUDGE_THINKING_BUDGET}`) and "
      f"`max_output_tokens={JUDGE_MAX_OUTPUT_TOKENS}`, everything else "
      "unchanged — same model, temperature 0, rubric r1 verbatim, same "
      "blinding, same randomization seed. **Both settings are pinned judge "
      "parameters at bar-lock.**")
    A("")
    A("A determinism probe ran first "
      "(`judge/determinism_probe_v2.json`): 3 items × 2 runs under the new "
      "config, 3/3 identical labels, WHY intact on all 6. Only then did the "
      "batches run.")
    A("")
    A("| pass | file | thinking | max out | parse failures | WHY intact |")
    A("|---|---|---|---|---|---|")
    A("| v1 (defect record, retained) | `judge/judgements.jsonl` | default "
      "(on) | 256 | 2 / 85 | 3 / 85 |")
    for tag in ("v2", "gemma"):
        s = jsum.get(tag)
        if not s:
            continue
        A(f"| {tag} ({GEN_DIR_MODEL[JUDGE_TAG_DIR[tag]]}) | "
          f"`judge/judgements_{tag}.jsonl` | disabled | "
          f"{s['max_output_tokens']} | {s['n_unparsed_after_retry']} / "
          f"{s['n_calls']} | {int(s['why_intact_rate_overall'] * s['n_calls'])}"
          f" / {s['n_calls']} |")
    A("")
    A("v1 and v2 agree on 72 of 85 labels (84.7%) on the same flash-lite "
      "generations. v1 is retained as the defect record and is used for "
      "nothing else.")
    A("")
    A("## 10. Cost")
    A("")
    A("| run | model | backend | calls | tokens in | tokens out | USD | "
      "node-hours |")
    A("|---|---|---|---|---|---|---|---|")
    for run, e in sorted(costs["per_run"].items()):
        A(f"| `{run}` | {e['model']} | {e['backend']} | {e['n_calls']} | "
          f"{e['tokens_in']} | {e['tokens_out']} | "
          f"{e['cost_usd'] if e['cost_usd'] else '—'} | "
          f"{e['node_hours'] if e['node_hours'] else '—'} |")
    A(f"| **total** | | | | | | **${costs['total_cost_usd']}** | "
      f"**{costs['total_node_hours']}** |")
    A("")
    A("Per-arm breakdown lives in `cost_log.jsonl` under each run's `variant` "
      "field. The primary-model generation is billed per whole node "
      "(1 node-hour = 4 GPU-hours = 32 core-hours), from `sacct` ElapsedRaw.")
    A("")
    A("## 11. The two pre-written C4 readings, quoted verbatim")
    A("")
    A("From `results/stage2_openended/PILOT_SPEC.md` section 7, written before "
      "any of these numbers existed:")
    A("")
    A(readings["pass"])
    A("")
    A(readings["pause"])
    A("")
    A("### The gate inputs, laid beside them")
    A("")
    A(f"Primary model (`{PRIMARY_MODEL}`), pinned embedding candidate "
      f"`{pinned}`:")
    A("")
    A("| channel | own | imposter | own−imposter | 95% CI (subject-clustered) "
      "| subjects own>imp | paired N |")
    A("|---|---|---|---|---|---|---|")
    b1 = c1.get(pinned, {}).get("per_model", {}).get(PRIMARY_MODEL)
    b2 = c2.get(PRIMARY_MODEL)
    if b1:
        A(f"| 1 embedding | {_fmt(b1['per_arm_mean'][OWN_ARM])} | "
          f"{_fmt(b1['per_arm_mean'][IMPOSTER_ARM])} | "
          f"{_fmt(b1['own_minus_imposter'])} | ({_fmt(b1['ci95'][0])}, "
          f"{_fmt(b1['ci95'][1])}) | {b1['subjects_own_gt_imposter']} | "
          f"{b1['n_paired_items']} |")
    if b2:
        A(f"| 2 stance | {_fmt(b2['per_arm_mean'][OWN_ARM])} | "
          f"{_fmt(b2['per_arm_mean'][IMPOSTER_ARM])} | "
          f"{_fmt(b2['own_minus_imposter'])} | ({_fmt(b2['ci95'][0])}, "
          f"{_fmt(b2['ci95'][1])}) | {b2['subjects_own_gt_imposter']} | "
          f"{b2['n_paired_items']} |")
    A("")
    A(f"Robustness model (`{ROBUSTNESS_MODEL}`) — per Amendment 3 C3 its "
      "absolute scores are secondary and only its own-minus-imposter contrast "
      "carries robustness weight:")
    A("")
    A("| channel | own−imposter | 95% CI | subjects own>imp | paired N |")
    A("|---|---|---|---|---|")
    r1 = c1.get(pinned, {}).get("per_model", {}).get(ROBUSTNESS_MODEL)
    r2 = c2.get(ROBUSTNESS_MODEL)
    if r1:
        A(f"| 1 embedding | {_fmt(r1['own_minus_imposter'])} | "
          f"({_fmt(r1['ci95'][0])}, {_fmt(r1['ci95'][1])}) | "
          f"{r1['subjects_own_gt_imposter']} | {r1['n_paired_items']} |")
    if r2:
        A(f"| 2 stance | {_fmt(r2['own_minus_imposter'])} | "
          f"({_fmt(r2['ci95'][0])}, {_fmt(r2['ci95'][1])}) | "
          f"{r2['subjects_own_gt_imposter']} | {r2['n_paired_items']} |")
    A("")
    A(VERDICT_PLACEHOLDER)

    path = out_dir / "OE1_PILOT_REPORT.md"
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    S.write_json(out_dir / "oe1_numbers.json", {
        "pilot": PILOT_BANNER, "contract": CONTRACT,
        "pinned_embedding_candidate": pinned,
        "embedding_selection": selection,
        "channel1": c1, "channel2": c2,
        "generation": gens, "cost": costs, "computed_utc": now()})
    print(f"[report] -> {rel(path)}")
    print(f"[report] numbers -> {rel(out_dir / 'oe1_numbers.json')}")
    return 0


def _unclear_flag(c2: dict) -> str:
    """Name any arm whose UNCLEAR rate is far from the own arm's (C2.3)."""
    bits = []
    for model, b in c2.items():
        own = b["unclear_rate"][OWN_ARM]
        worst = max(OE.ARMS, key=lambda a: b["unclear_rate"][a])
        gap = round(b["unclear_rate"][worst] - own, 4)
        bits.append(
            f"{model}: highest is `{worst}` at {b['unclear_rate'][worst]} "
            f"against `{OWN_ARM}`'s {own} (gap {gap}, denominator falls to "
            f"{b['match_denominator'][worst]} of 17)")
    return (
        "Declared risk 2 was UNCLEAR flooding shrinking the judged "
        "denominator, and it is present. " + "; ".join(bits) + ". This is not "
        "cosmetic: an arm that loses more items to UNCLEAR is scored on a "
        "different, smaller subset than the arm it is compared with, and the "
        "paired contrast in section 3 drops any item where EITHER side is "
        "UNCLEAR. It is measured here and reported; the UNCLEAR rule freezes "
        "in the addendum, not mid-pilot. Note separately that `twin_named` "
        "and `twin_redacted` produce identical label counts on both models "
        "(TVD 0.0000) -- on stance, the name line changes nothing.")


def _era_note(gens: dict) -> str:
    bits = []
    for model, per_arm in gens.items():
        n = sum(s["n_era_violations"] for s in per_arm.values())
        bits.append(f"{model}: {n}")
    return ("Generated answers must not reference events after the test "
            "interview's date. Counts by model — " + "; ".join(bits) +
            ". The single flash-lite violation is `C02006:NPR-14829:26` "
            "(zeroinfo_named), which mentions \"2019\". It is flagged, kept in "
            "the tables, and named here rather than dropped.")


# ---------------------------------------------------------------------------
# Owner spot-check sheet (precondition 6)
# ---------------------------------------------------------------------------

SPOTCHECK_SEED = 610
SPOTCHECK_SHEETS = ("A", "B", "C")
SPOTCHECK_TARGET = {"SAME": 25, "DIFFERENT": 25}

SPOTCHECK_HEADER = """# OE-1 judge spot-check — sheet {sheet} of {n_sheets}

{banner}

**What you are doing.** For each entry below you see a QUESTION from a
broadcast interview, the REAL answer the person gave, and a CANDIDATE answer.
Decide whether the CANDIDATE takes the same position as the REAL answer on the
central issue the question asks about, and write SAME, DIFFERENT or UNCLEAR
next to the entry number on your own sheet. The rubric you are applying is
`results/stage2_openended/rubric_r1.txt` — read it first.

**What you are NOT told, on purpose.** Which condition each candidate came
from, which model wrote it, and what the automated judge said. That mapping is
in
`judge_spotcheck_key.json`, which you should not open until your labels are
written down.

**Standing twin rule (D6-v4.9).** Within this sheet every question appears at
most once, so no entry can be reasoned about from its neighbour. That is why
the sample is split across {n_sheets} sheets rather than presented as one list.

Every name is replaced by GUEST, exactly as the automated judge saw it.

---
"""


def _spotcheck_pool(out_dir: Path, items: dict) -> list:
    """Every judged candidate, with the texts a human rater needs."""
    pool = []
    for tag, gen_dir in JUDGE_TAG_DIR.items():
        jpath = out_dir / "judge" / f"judgements_{tag}.jsonl"
        if not jpath.exists():
            continue
        gens = {}
        for arm in OE.ARMS:
            gp = out_dir / "gen" / gen_dir / f"completions_{arm}.jsonl"
            if gp.exists():
                for g in S.read_jsonl(gp):
                    gens[(arm, g["item_id"])] = g["text"]
        for j in S.read_jsonl(jpath):
            key = (j["arm"], j["item_id"])
            if key not in gens or not j.get("label"):
                continue
            it = items[j["item_id"]]
            pool.append({
                "item_id": j["item_id"], "canonical_id": j["canonical_id"],
                "arm": j["arm"], "model": GEN_DIR_MODEL[gen_dir],
                "judge_label": j["label"], "judge_why": j.get("why"),
                "item_type": it["item_type"],
                "question": it["question"],
                "real": it["real_answer_verbatim"],
                "candidate": gens[key],
            })
    return pool


def _balanced_sample(pool: list, n_sheets: int, target: dict, seed: int):
    """One row per item per sheet, pushed toward the label balance.

    Constraint first, balance second: the twin rule caps the sample at
    ``n_sheets`` rows per item, so the achievable number of DIFFERENT rows is
    bounded by how many DIFFERENT labels the item set actually contains. The
    shortfall is filled with UNCLEAR and reported, exactly as PILOT_SPEC
    section 7 says to.
    """
    rng = random.Random(seed)
    by_item: dict = {}
    for row in pool:
        by_item.setdefault(row["item_id"], []).append(row)
    for rows in by_item.values():
        rng.shuffle(rows)

    quota = {lab: target.get(lab, 0) for lab in LABELS}
    chosen: dict = {item_id: [] for item_id in by_item}
    # Scarcest label first, so DIFFERENT is not crowded out by SAME.
    for lab in ("DIFFERENT", "SAME", "UNCLEAR"):
        for _ in range(n_sheets):
            for item_id, rows in sorted(by_item.items()):
                if quota.get(lab, 0) <= 0:
                    break
                if len(chosen[item_id]) >= n_sheets:
                    continue
                taken = {id(r) for r in chosen[item_id]}
                pick = next((r for r in rows if r["judge_label"] == lab
                             and id(r) not in taken), None)
                if pick is None:
                    continue
                chosen[item_id].append(pick)
                quota[lab] -= 1
    # Fill every remaining slot with whatever that item still has.
    for item_id, rows in sorted(by_item.items()):
        while len(chosen[item_id]) < n_sheets:
            taken = {id(r) for r in chosen[item_id]}
            pick = next((r for r in rows if id(r) not in taken), None)
            if pick is None:
                break
            chosen[item_id].append(pick)

    sheets = {name: [] for name in SPOTCHECK_SHEETS[:n_sheets]}
    for item_id, rows in sorted(chosen.items()):
        for i, row in enumerate(rows):
            sheets[SPOTCHECK_SHEETS[i]].append(row)
    for name in sheets:
        rng.shuffle(sheets[name])
    return sheets


def cmd_spotcheck(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or OE_DIR)
    items = load_items(out_dir)
    pool = _spotcheck_pool(out_dir, items)
    if not pool:
        raise fatal("no judged generations on disk; run judge first")
    n_sheets = int(args.sheets)
    sheets = _balanced_sample(pool, n_sheets, SPOTCHECK_SAMPLE_TARGET := dict(
        SPOTCHECK_TARGET), SPOTCHECK_SEED)

    ctx = subject_blocks(Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR))
    key_rows = []
    total = 0
    counts = {lab: 0 for lab in LABELS}
    for name in SPOTCHECK_SHEETS[:n_sheets]:
        rows = sheets[name]
        # The standing rule, asserted rather than assumed.
        assert_no_cross_visible_twins({f"spotcheck_sheet_{name}": rows})
        body = [SPOTCHECK_HEADER.format(sheet=name, n_sheets=n_sheets,
                                        banner=PILOT_BANNER)]
        for i, row in enumerate(rows, 1):
            variants = ctx[row["canonical_id"]]["variants"]
            q = R._norm_ws(R.redact(row["question"], variants))
            real = R._norm_ws(R.redact(row["real"], variants))
            cand = R._norm_ws(R.redact(row["candidate"], variants))
            body.append(f"## {name}{i}")
            body.append("")
            body.append(f"**QUESTION.** {q}")
            body.append("")
            body.append(f"**REAL ANSWER.** {real}")
            body.append("")
            body.append(f"**CANDIDATE ANSWER.** {cand}")
            body.append("")
            body.append("`SAME / DIFFERENT / UNCLEAR:` ______")
            body.append("")
            body.append("---")
            body.append("")
            key_rows.append({
                "entry": f"{name}{i}", "sheet": name, "position": i,
                "item_id": row["item_id"], "canonical_id": row["canonical_id"],
                "arm": row["arm"], "model": row["model"],
                "item_type": row["item_type"],
                "judge_label": row["judge_label"],
                "judge_why": row["judge_why"],
            })
            counts[row["judge_label"]] += 1
            total += 1
        path = out_dir / f"judge_spotcheck_sheet_{name}.md"
        path.write_text("\n".join(body), encoding="utf-8")
        print(f"[spotcheck] sheet {name}: {len(rows)} entries -> {rel(path)}")

    shortfall = {lab: SPOTCHECK_TARGET[lab] - counts[lab]
                 for lab in SPOTCHECK_TARGET if counts[lab] < SPOTCHECK_TARGET[lab]}
    key = {
        "pilot": PILOT_BANNER,
        "purpose": "Owner >=50-label judge spot-check (PILOT_SPEC section 7, "
                   "precondition 6). Do not open until the labels are written.",
        "n_entries": total, "n_sheets": n_sheets,
        "sample_seed": SPOTCHECK_SEED,
        "target_balance": SPOTCHECK_TARGET,
        "achieved_balance": counts,
        "shortfall_vs_target": shortfall,
        "shortfall_note":
            "PILOT_SPEC section 7 asks for 50 calls balanced 25 SAME / 25 "
            "DIFFERENT 'where supply allows (shortfall filled with UNCLEAR and "
            "said so)'. Supply does not allow 25 DIFFERENT here. Across both "
            "scored models and all five arms the item set yields 37 DIFFERENT "
            "labels in total, and 9 of the 17 items have ZERO DIFFERENT "
            "labels anywhere. The standing twin rule caps the sample at one "
            "row per item per sheet, so the ceiling on DIFFERENT rows is 23. "
            "The remainder is filled with UNCLEAR and is named here rather "
            "than quietly rebalanced.",
        "blinding": "Sheets carry no arm, no model and no judge label. The "
                    "mapping lives only in this file.",
        "twin_rule": TWIN_RULE,
        "subjects_covered": sorted({r["canonical_id"] for r in key_rows}),
        "models_covered": sorted({r["model"] for r in key_rows}),
        "arms_covered": sorted({r["arm"] for r in key_rows}),
        "rubric_file": "rubric_r1.txt",
        "entries": key_rows,
        "generated_utc": now(),
    }
    kpath = out_dir / "judge_spotcheck_key.json"
    S.write_json(kpath, key)
    print(f"[spotcheck] {total} entries, balance {counts}")
    if shortfall:
        print(f"[spotcheck] shortfall vs target {shortfall} -- filled with "
              "UNCLEAR, documented in the key")
    print(f"[spotcheck] key -> {rel(kpath)}")
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
    p_i.add_argument("--node-hours", type=float, default=None,
                     help="sacct ElapsedRaw/3600 for the whole node, "
                          "accumulated over every attempt")
    p_i.add_argument("--job-id", default=None)
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

    p_s = sub.add_parser("spotcheck")
    p_s.add_argument("--sheets", type=int, default=3)
    p_s.set_defaults(fn=cmd_spotcheck)

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
