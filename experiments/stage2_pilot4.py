"""Stage 2 pilot ROUND 4 driver — hedged, plausible, deixis-free counterfactuals.

PILOT. Pipeline validation on dev subjects. Nothing here answers a
pre-registered bar.

Binding design: PREREGISTRATION_AMENDMENT_2.md **B10**, as amended for round 4
by the owner-approved design of 2026-07-27. Implementation rules are documented
in SPEC v1.10 (D6-v4). Round 3 is frozen: this driver writes only to
results/stage2_pilot4/ and reads rounds 1-3 read-only.

Why round 4 exists. Round 3 built B10's generated same-question counterfactuals
and the zero-information arm still solved 15 of 15, mean margin +0.69. Its gate
completions named three mechanisms and round 4 attacks all three at once:

  1. SPEAKER PLAUSIBILITY -- "options A, B, and C read more like an op-ed than a
     natural response from an academic guest". The generator writes confident
     advocacy; interviewees hedge. -> generation is now few-shot conditioned on
     the subject's OWN real answers as style exemplars, and the register rule is
     the most heavily weighted instruction in the prompt.
  2. WORLD TRUTH -- where the true position is simply correct about the world,
     every genuinely conflicting alternative is wrong about it and a scorer wins
     on general knowledge. -> an explicit plausibility instruction AND a
     separate plausibility check call; FALSE and FRINGE options are rejected.
  3. CONVERSATIONAL DEIXIS -- the paraphrased true answer kept the host's first
     name and the model cited it. -> host names and interviewer address are
     stripped from ALL FOUR options, or uniformly retained, recorded per item.

Plus a supply decision: round 3's widest margins sat on factual-explanation
questions, so the candidates are split by question type and round 4 builds the
subjective-leaning subset first.

**KILL RULE (pre-committed, before any round-4 data exists).** If round 4's
zero-information argmax accuracy is >= 0.9, four-way forced choice is DEAD on
this corpus and there is no round 5 on any axis. The landing zone is already
written: results/stage2_pilot3/FALLBACK_OPENENDED_SKETCH.md.

**The gate is NOT relaxed for round 4.** Strict argmax, unchanged. A kill rule
only means something if the bar does not move in the same round that the rule
is tested. See B10_7_MARGIN_CONSIDERATION.

**Two parsers, one contract.** Every round-4 number is reported under the
FROZEN parser (the contract) and the WIDENED reading side by side, with N for
each. The frozen parser is not changed mid-pilot.

Subcommands
-----------
``classify``     the item-type split. Reads only; spends nothing.
``build``        the round-4 pipeline (spends API; resumable per item).
``export-gate``  zero-information gate prompts for the candidate items.
``verify`` / ``plan`` / ``bootstrap``   as round 3.
``ingest-gate`` / ``finalize`` / ``export-pred`` / ``ingest-pred``
``bill`` / ``record``
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import stage2_pilot as P1  # noqa: E402
import stage2_pilot2 as P2  # noqa: E402
import stage2_pilot3 as P3  # noqa: E402

from doppler import counterfactuals as CF  # noqa: E402
from doppler import counterfactuals4 as C4  # noqa: E402
from doppler import dual_parse as DP  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402
from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402
from doppler.distractors import density_bucket, entity_density, strip_entities  # noqa: E402

RESULTS_DIR = _ROOT / "results"
PILOT1_DIR = RESULTS_DIR / "stage2_pilot"
PILOT2_DIR = RESULTS_DIR / "stage2_pilot2"
PILOT3_DIR = RESULTS_DIR / "stage2_pilot3"
PILOT4_DIR = RESULTS_DIR / "stage2_pilot4"
COST_LOG = RESULTS_DIR / "cost_log.jsonl"

PILOT_BANNER = P3.PILOT_BANNER
CONTRACT = "SPEC.md v1.10 (D6-v4, Amendment 2 B10 as amended 2026-07-27)"
SCORED_CLAIM = P3.SCORED_CLAIM

GENERATOR = P3.GENERATOR
ROBUSTNESS_SCORER = P3.ROBUSTNESS_SCORER
SCORED_MODELS = P3.SCORED_MODELS
GENERATOR_IS_ROBUSTNESS_SCORER = P3.GENERATOR_IS_ROBUSTNESS_SCORER
B10_3_OVERLAP_DECLARATION = P3.B10_3_OVERLAP_DECLARATION

GEN_TEMPERATURE = P3.GEN_TEMPERATURE
CHECK_TEMPERATURE = P3.CHECK_TEMPERATURE
#: Round 4's prompt carries three style exemplars, so generation input is
#: bigger; output is unchanged in shape. Round 3's measured budgets stand with
#: their headroom (worst measured generate was 1,555 tokens against 8,192).
GEN_MAX_TOKENS = P3.GEN_MAX_TOKENS
PARA_MAX_TOKENS = P3.PARA_MAX_TOKENS
CHECK_MAX_TOKENS = P3.CHECK_MAX_TOKENS
DEFAULT_CALL_CAP = 900

# ---------------------------------------------------------------------------
# Pre-committed decisions. Written before any round-4 data exists.
# ---------------------------------------------------------------------------

KILL_RULE_THRESHOLD = 0.9

KILL_RULE = (
    "KILL RULE, pre-committed before any round-4 data existed: if round 4's "
    "zero-information argmax accuracy is >= 0.90, four-way forced choice is "
    "DEAD on this corpus and there is no round 5 on any axis. Rounds 1, 2 and "
    "3 solved 17/17, 10/10 and 15/15 by three different mechanisms; a fourth "
    "instrument that also fails is evidence about the format, not about the "
    "next patch. The fallback landing zone is already written and committed: "
    "results/stage2_pilot3/FALLBACK_OPENENDED_SKETCH.md (commit 71ae352).")

B10_7_MARGIN_CONSIDERATION = (
    "B10.7 CONSIDERATION, documented and NOT adopted for round 4. A "
    "margin-relaxed gate -- rejecting an item only when the zero-information "
    "arm solves it by more than some margin, rather than on argmax alone -- "
    "would keep items the current gate discards, and round 3's tightest item "
    "sat at +0.30. It is NOT adopted here for one reason: round 4 is the round "
    "that tests a pre-committed kill rule, and a kill rule means nothing if the "
    "bar moves in the same round it is tested. Loosening the gate and then "
    "reporting that fewer items were rejected would be unfalsifiable. This "
    "consideration is available at BAR-LOCK, and only if round 4 lands in the "
    "gray zone -- zero-information accuracy clearly below 0.90 but clearly "
    "above the 0.25 chance line. The owner decides; the implementer does not.")

# ---------------------------------------------------------------------------
# D6-v4.4 Item type. Rule + hand call, disagreements reported.
# ---------------------------------------------------------------------------
#
# The cue rule in counterfactuals4 was written while looking at these very
# questions, so it is tuned on the set it scores. That is allowed on dev
# subjects and is stated rather than hidden -- and it is why the BUILD uses a
# recorded hand classification with a per-item reason, exactly as round 3's
# polar split did, and reports every place the two disagree.

HAND_ITEM_TYPE: dict[str, tuple[str, str]] = {
    "C00792:NPR-19884:2": (
        "factual_explanation",
        "whether these groups would align with IS is a claim about the world, "
        "checkable after the fact"),
    "C00792:NPR-19884:6": (
        "subjective",
        "'to what extent is this an American responsibility' is an "
        "apportionment of blame, not a fact"),
    "C00792:NPR-19884:10": (
        "subjective",
        "whether there is 'an opportunity to change course' is an assessment "
        "of a situation, not a fact about it"),
    "C00792:NPR-19884:13": (
        "subjective",
        "'is there still ENOUGH of a movement to back' is a judgement of "
        "sufficiency"),
    "C00792:NPR-19884:15": (
        "subjective",
        "'who has lost most' is a comparative judgement; no fact settles it"),
    "C01677:NPR-8791:77": (
        "factual_explanation",
        "the enrichment timeline is a matter of record and inspection, and the "
        "true answer recites specific verifiable facts"),
    "C02006:NPR-14829:19": (
        "subjective",
        "asks the guest to confirm the reading of their own tweet"),
    "C02006:NPR-14829:26": (
        "subjective",
        "'does anybody in power SERIOUSLY want' is a read of other people's "
        "intentions"),
    "C02006:NPR-14829:29": (
        "subjective",
        "'could this turn out to be good, better, less bad' is explicitly a "
        "forecast from the guest's perspective"),
    "C02013:NPR-9480:45": (
        "subjective",
        "'what stuck out of that speech FOR YOU' names the guest's own view"),
    "C02013:NPR-9480:49": (
        "factual_explanation",
        "chicken-and-egg causal ordering between poverty and violence is an "
        "empirical question the guest answers from research"),
    "C02013:NPR-9480:70": (
        "factual_explanation",
        "'do we know that early education works' asks what the evidence shows; "
        "this is the +0.96 item and the clearest case of the world-truth tell"),
    "C02013:NPR-9480:82": (
        "factual_explanation",
        "asks about the prevalence of exposure to violence, answered with a "
        "figure"),
    "C02124:NPR-12184:4": (
        "subjective",
        "'any doubt IN YOUR MIND' names the guest's own judgement"),
    "C02124:NPR-12184:6": (
        "subjective",
        "how concerned a government WOULD BE is a prediction about intentions"),
}


TWIN_RULE = (
    "STANDING EVAL RULE (D6-v4.9), added 2026-07-27 after the frontier rater "
    "named TWIN-PAIR STANCE INFERENCE as one of six tells on round 3's "
    "detectability sheet: no rater and no scorer may ever see both twins of a "
    "duplicated question. Round 3's sheet showed five questions twice, once as "
    "a real entry and once as a control; the option sets shared nothing, so "
    "elimination was impossible, but a reader could still reason across the "
    "two stance sets. The rule generalises that: within any single prompt file "
    "or rating sheet a question appears AT MOST ONCE. Asserted at export, not "
    "assumed.")


def assert_no_cross_visible_twins(sets: dict) -> dict:
    """D6-v4.9 — refuse any prompt set that shows one question twice.

    ``sets`` maps a set name to its rows. A batch file is what one scoring pass
    consumes, so that is the unit of visibility. Raises rather than warns: a
    duplicated question inside a scored file is not a thing to note in a
    report, it is a reason not to run the file.
    """
    checked = {}
    for name, rows in sets.items():
        seen: dict[str, int] = {}
        for row in rows:
            item_id = row.get("item_id")
            seen[item_id] = seen.get(item_id, 0) + 1
        repeats = sorted(k for k, v in seen.items() if v > 1)
        if repeats:
            raise fatal(
                f"cross-visible twin in prompt set '{name}': "
                f"{', '.join(repeats)} appears more than once. {TWIN_RULE}")
        checked[name] = {"n_rows": len(rows), "n_distinct_items": len(seen)}
    return {"ok": True, "rule": TWIN_RULE, "n_sets_checked": len(sets),
            "per_set": checked}


def fatal(msg: str) -> "SystemExit":
    return P3.fatal(msg)


def classify_candidates(pilot3_dir: Path) -> dict:
    """Split round 3's built items by question type. Reads only; spends nothing."""
    rows = []
    for rec in P3.records_built(pilot3_dir):
        rule = C4.classify_question(rec["question"])
        hand, why = HAND_ITEM_TYPE.get(rec["item_id"], (None, None))
        rows.append({
            "item_id": rec["item_id"], "canonical_id": rec["canonical_id"],
            "question": " ".join(rec["question"].split()),
            "rule_kind": rule["kind"], "rule": rule,
            "hand_kind": hand, "hand_reason": why,
            "agree": (hand == rule["kind"]),
            "kind": hand or rule["kind"],
        })
    rows.sort(key=lambda r: r["item_id"])
    kinds = [r["kind"] for r in rows]
    return {
        "pilot": PILOT_BANNER, "contract": CONTRACT,
        "method": "Documented cue rule (counterfactuals4.classify_question) "
                  "cross-checked against a recorded hand call with a per-item "
                  "reason. The BUILD uses the hand call. The rule's cue lists "
                  "were written against these same dev questions, so the rule "
                  "is tuned on the set it scores; it is reported as a "
                  "cross-check, not as independent evidence.",
        "n_items": len(rows),
        "n_subjective": kinds.count("subjective"),
        "n_factual_explanation": kinds.count("factual_explanation"),
        "n_rule_unclear": sum(1 for r in rows if r["rule_kind"] == "unclear"),
        "n_disagreements": sum(1 for r in rows if not r["agree"]),
        "disagreements": [
            {"item_id": r["item_id"], "rule": r["rule_kind"],
             "hand": r["hand_kind"], "hand_reason": r["hand_reason"]}
            for r in rows if not r["agree"]],
        "build_order": "subjective first; factual_explanation items are built "
                       "only if supply demands and are labelled SECONDARY in "
                       "every table",
        "items": rows,
    }


def cmd_classify(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT4_DIR)
    pilot3_dir = Path(getattr(args, "pilot3_dir", None) or PILOT3_DIR)
    doc = classify_candidates(pilot3_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    S.write_json(out_dir / "item_types.json", doc)
    print(f"[classify] {doc['n_items']} items: "
          f"{doc['n_subjective']} subjective, "
          f"{doc['n_factual_explanation']} factual-explanation")
    print(f"[classify] rule said 'unclear' on {doc['n_rule_unclear']}; "
          f"rule and hand disagree on {doc['n_disagreements']}")
    for d in doc["disagreements"]:
        print(f"  disagree {d['item_id']:22s} rule={d['rule']:20s} "
              f"hand={d['hand']}")
    print(f"[classify] -> {P3.rel(out_dir / 'item_types.json')}")
    return 0


# ---------------------------------------------------------------------------
# Per-subject context: style exemplars and host name forms
# ---------------------------------------------------------------------------


def style_exemplars(cid: str, item_id: str, *, pilot1_dir: Path,
                    pilot2_dir: Path, n: int = C4.N_STYLE_EXEMPLARS) -> dict:
    """Real answers by the SAME subject, to condition the generator's register.

    Preference order matters. Round 2's ``answer_pool.jsonl`` is first because
    it holds the subject's answers from OTHER interviews and was already
    filtered against the twin's rendered grounding by D6-v2.2, so nothing in it
    is text the twin arm will also be shown. When a subject has too few of
    those (C02013 has one), the shortfall is topped up from the subject's OTHER
    answers in the SAME test interview, which are real speech by the same
    person and are never shown to a scorer as an option for THIS item.

    Both sources are recorded per item. The caller must still guard generated
    text against copying an exemplar -- a model handed three real answers can
    reach for their content as well as their rhythm.
    """
    used: list[str] = []
    sources: list[str] = []
    pool_path = pilot2_dir / "subjects" / cid / "answer_pool.jsonl"
    if pool_path.exists():
        for row in S.read_jsonl(pool_path):
            if len(used) >= n:
                break
            text = " ".join(str(row.get("answer", "")).split())
            if text and text not in used:
                used.append(text)
                sources.append(f"answer_pool:{row.get('source_transcript_id')}")
    if len(used) < n:
        for row in S.read_jsonl(pilot1_dir / "subjects" / cid
                                / "qa_items.jsonl"):
            if len(used) >= n:
                break
            if row["item_id"] == item_id:
                continue
            text = " ".join(str(row.get("answer", "")).split())
            if text and text not in used:
                used.append(text)
                sources.append(f"same_test_interview:{row['item_id']}")
    return {"texts": used, "sources": sources, "n": len(used),
            "shortfall": max(0, n - len(used))}


def host_forms_for(cid: str, pilot1_dir: Path) -> list[str]:
    """Host name forms to strip, from the subject's own transcripts."""
    labels = set()
    for name in ("test_turns.jsonl", "grounding_turns.jsonl"):
        path = pilot1_dir / "subjects" / cid / name
        if not path.exists():
            continue
        for row in S.read_jsonl(path):
            if row.get("role") == "host" and row.get("speaker_label"):
                labels.add(row["speaker_label"])
    return C4.host_name_forms(labels)


def subject_context4(pilot1_dir: Path) -> dict:
    """Round 3's context plus round 4's host name forms."""
    ctx = P3.subject_context(pilot1_dir)
    for cid, entry in ctx.items():
        entry["host_forms"] = host_forms_for(cid, pilot1_dir)
    return ctx


# ---------------------------------------------------------------------------
# The round-4 build
# ---------------------------------------------------------------------------


def build_item_v4(client, item: dict, ctx: dict, log: P3.GenLog,
                  exemplars: dict) -> dict:
    """One round-4 item, end to end.

    Order is round 3's, with two additions and one reordering:
      1. paraphrase the true answer, refuse a truncated one
      2. position-preservation check
      3. GENERATE against the paraphrase, few-shot conditioned on the
         subject's own answers                            [NEW: register]
      4. offline guards on raw text, now including copy/quote of an exemplar
      5. paraphrase every survivor, guards again
      6. contradiction check   (CONFLICT only)
      7. PLAUSIBILITY check    (PLAUSIBLE only)           [NEW: world truth]
      8. assemble, then strip deixis across ALL FOUR      [NEW: deixis]
      9. ladder rung recomputed AFTER stripping, then the seeded shuffle

    The deixis rule runs on the assembled set rather than per option because
    uniformity across the four IS the rule; and the ladder is recomputed after
    it because stripping changes word counts and a rung measured on pre-strip
    text would describe an option set that no longer exists.
    """
    question, true_answer = item["question"], item["answer"]
    rejections: list[dict] = []
    exemplar_texts = exemplars["texts"]

    def paraphrase(text_in: str, tag: str) -> str:
        P3._configure(client, CHECK_TEMPERATURE, PARA_MAX_TOKENS)
        p = CF.para_prompt(text_in)
        got, a, b = client.generate(p)
        log.add(f"paraphrase:{tag}", p, got, a, b,
                truncated=CF.looks_truncated(got))
        if CF.looks_truncated(got):
            return ""
        return CF.parse_paraphrase(got)

    def fail(reason: str, **extra) -> dict:
        return {"item_id": item["item_id"], "canonical_id": item["canonical_id"],
                "built": False, "reason": reason, "rejections": rejections,
                "style_exemplars": exemplars, **extra}

    def guards(text: str, stage: str) -> dict:
        """Round 3's offline guards plus round 4's exemplar-leak guards."""
        verdict = P3._guard_offline(text, item=item, ctx=ctx, stage=stage)
        reasons = list(verdict["reasons"])
        if C4.copies_any(text, exemplar_texts):
            reasons.append({"reason": "copies_style_exemplar", "detail": None})
        quote = C4.quotes_any(text, exemplar_texts)
        if quote:
            reasons.append({"reason": "quotes_style_exemplar", "detail": quote})
        return {"stage": stage, "ok": not reasons, "reasons": reasons}

    # --- 1-2. paraphrase the true answer and check the position -------------
    P3._configure(client, CHECK_TEMPERATURE, CHECK_MAX_TOKENS)
    para_true = paraphrase(true_answer, "true")
    if not para_true:
        para_true = paraphrase(true_answer, "true_retry_truncated")
    if not para_true:
        return fail("true answer paraphrase was empty or truncated twice")

    def check_position(candidate: str, tag: str):
        pp = CF.position_prompt(true_answer, candidate)
        got, a, b = client.generate(pp)
        log.add(tag, pp, got, a, b)
        return CF.parse_verdict(got, ("SAME", "CHANGED"))

    verdict, why = check_position(para_true, "position_check")
    position = {"verdict": verdict, "why": why, "retried": False}
    if verdict != "SAME":
        para_true = paraphrase(true_answer, "true_retry")
        verdict, why = check_position(para_true, "position_check_retry")
        position = {"verdict": verdict, "why": why, "retried": True}
        if verdict != "SAME":
            return fail("paraphrase did not preserve the true position",
                        position_check=position)

    # --- 3. generate, register-conditioned ----------------------------------
    prompt = C4.gen_prompt_v4(question, para_true, ctx["test_date"],
                              exemplar_texts)
    P3._configure(client, GEN_TEMPERATURE, GEN_MAX_TOKENS)
    text, tin, tout = client.generate(prompt)
    log.add("generate_v4", prompt, text, tin, tout, temperature=GEN_TEMPERATURE,
            n_exemplars=len(exemplar_texts))
    raw = CF.parse_generated(text)
    if len(raw) < CF.N_DISTRACTORS:
        return fail(f"generator returned {len(raw)} blocks",
                    position_check=position)

    # --- 4. offline guards on the raw text ----------------------------------
    survivors = []
    for k, cand in enumerate(raw):
        verdict_g = guards(cand, "raw")
        if verdict_g["ok"]:
            survivors.append(cand)
        else:
            rejections.append({"slot": k, "text": cand, **verdict_g})

    # --- 5. paraphrase every survivor, guards again -------------------------
    P3._configure(client, CHECK_TEMPERATURE, CHECK_MAX_TOKENS)
    para_cands = []
    for k, cand in enumerate(survivors):
        out = paraphrase(cand, f"gen{k}")
        if not out:
            rejections.append({
                "slot": k, "text": cand, "stage": "paraphrase", "ok": False,
                "reasons": [{"reason": "empty_or_truncated_paraphrase"}]})
            continue
        verdict_g = guards(out, "paraphrased")
        if not verdict_g["ok"]:
            rejections.append({"slot": k, "text": out, **verdict_g})
            continue
        para_cands.append(out)

    # --- 6-7. contradiction, then plausibility ------------------------------
    accepted: list[dict] = []
    for cand in para_cands:
        if len(accepted) >= CF.N_DISTRACTORS:
            break
        cp = CF.contra_prompt(question, para_true, cand)
        got, a, b = client.generate(cp)
        log.add("contradiction_check", cp, got, a, b)
        v, w = CF.parse_verdict(got, ("CONFLICT", "AGREE", "UNRELATED"))
        if v != "CONFLICT":
            rejections.append({
                "text": cand, "stage": "contradiction", "ok": False,
                "reasons": [{"reason":
                             f"contradiction_{(v or 'unparsed').lower()}",
                             "detail": w}]})
            continue

        pp = C4.plausibility_prompt(question, cand, ctx["test_date"])
        got, a, b = client.generate(pp)
        log.add("plausibility_check", pp, got, a, b)
        pv, pw = C4.parse_plausibility(got)
        if pv != "PLAUSIBLE":
            rejections.append({
                "text": cand, "stage": "plausibility", "ok": False,
                "reasons": [{"reason":
                             f"plausibility_{(pv or 'unparsed').lower()}",
                             "detail": pw}]})
            continue
        accepted.append({"text": cand, "why": w, "plausibility_why": pw})

    spare = [c for c in para_cands if c not in [a["text"] for a in accepted]]
    if len(accepted) < CF.N_DISTRACTORS:
        return fail(f"only {len(accepted)} distractors survived the checks",
                    position_check=position, spare=spare)

    # --- 8. assemble, then strip deixis across ALL FOUR ---------------------
    texts = [para_true] + [a["text"] for a in accepted[:CF.N_DISTRACTORS]]
    stripped, deixis = C4.apply_deixis_rule(texts, ctx.get("host_forms") or [])
    para_true_final, distractor_texts = stripped[0], stripped[1:]
    if len(set(stripped)) != len(stripped):
        return fail("deixis stripping collapsed two options into one text",
                    position_check=position, deixis=deixis)

    options = [{"text": para_true_final, "kind": "true",
                "origin": "paraphrased_real", "why": None,
                "plausibility_why": None}]
    for a, text_out in zip(accepted[:CF.N_DISTRACTORS], distractor_texts):
        options.append({"text": text_out, "kind": "distractor",
                        "origin": "generated", "why": a["why"],
                        "plausibility_why": a["plausibility_why"]})
    for opt in options:
        opt["answer_words"] = R.word_count(opt["text"])
        opt["entity_density"] = entity_density(opt["text"])
        opt["bucket"] = density_bucket(opt["entity_density"])

    # --- 9. ladder AFTER stripping, then the seeded shuffle -----------------
    rung = CF.match_rung(para_true_final,
                         [o["text"] for o in options if o["kind"] == "distractor"])
    random.Random(CF.shuffle_seed(item["item_id"])).shuffle(options)
    correct = [i for i, o in enumerate(options) if o["kind"] == "true"]
    if len(correct) != 1:
        raise P3.fatal(f"{item['item_id']}: {len(correct)} true options")

    flags = [f"relax_rung_{rung}"] if rung is not None else ["ladder_exceeded"]
    flags.append(f"deixis_{deixis['mode']}")
    return {
        "item_id": item["item_id"], "canonical_id": item["canonical_id"],
        "built": True,
        "question": question,
        "true_answer_verbatim": true_answer,
        "true_answer_paraphrased": para_true_final,
        "true_answer_paraphrased_pre_deixis": para_true,
        "options": options,
        "options_stripped": [strip_entities(o["text"]) for o in options],
        "correct_index": correct[0],
        "relax_rung": rung, "flags": flags,
        "position_check": position,
        "deixis": deixis,
        "style_exemplars": exemplars,
        "rejections": rejections,
        "spare_generated": spare,
        "generator": GENERATOR,
        "template_sha256_v4": C4.TEMPLATE_SHA256_V4,
        "template_sha256_v3_reused": C4.TEMPLATE_SHA256_V3_REUSED,
        "scored_claim": SCORED_CLAIM,
    }


def items_in_build_order(pilot3_dir: Path, out_dir: Path, *,
                         include_factual: bool, pilot1_dir: Path) -> list[dict]:
    """Candidate items, subjective first (D6-v4.4)."""
    types = {r["item_id"]: r["kind"] for r in
             classify_candidates(pilot3_dir)["items"]}
    by_id = {i["item_id"]: i for i in P3.all_items(pilot1_dir)}
    subj = [by_id[i] for i in sorted(types) if types[i] == "subjective"
            and i in by_id]
    fact = [by_id[i] for i in sorted(types)
            if types[i] == "factual_explanation" and i in by_id]
    return subj + (fact if include_factual else [])


def cmd_build(args) -> int:
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    pilot3_dir = Path(getattr(args, "pilot3_dir", None) or PILOT3_DIR)
    out_dir = Path(getattr(args, "out_dir", None) or PILOT4_DIR)
    items = items_in_build_order(pilot3_dir, out_dir,
                                 include_factual=args.include_factual,
                                 pilot1_dir=pilot1_dir)
    ctx = subject_context4(pilot1_dir)
    types = {r["item_id"]: r["kind"] for r in
             classify_candidates(pilot3_dir)["items"]}
    items_dir, genlog_dir = out_dir / "items", out_dir / "genlog"
    items_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    client = args.client
    if client is None:
        from doppler.gemini import GeminiClient
        client = GeminiClient(max_calls=args.call_cap,
                              temperature=CHECK_TEMPERATURE,
                              max_output_tokens=CHECK_MAX_TOKENS)
        client.model_name = GENERATOR
    if getattr(client, "model_name", GENERATOR) in SCORED_MODELS:
        raise P3.fatal(f"B10.3 violation: the generator is a scored model "
                       f"({client.model_name})")

    built = skipped = failed = 0
    tin_total = tout_total = 0
    for item in items:
        path = items_dir / f"{P3.safe_id(item['item_id'])}.json"
        if path.exists() and not args.force:
            skipped += 1
            continue
        cid = item["canonical_id"]
        exemplars = style_exemplars(cid, item["item_id"],
                                    pilot1_dir=pilot1_dir,
                                    pilot2_dir=PILOT2_DIR)
        log = P3.GenLog(genlog_dir / f"{P3.safe_id(item['item_id'])}.jsonl")
        try:
            record = build_item_v4(client, item, ctx[cid], log, exemplars)
        finally:
            log.flush()
            a, b = log.tokens
            tin_total += a
            tout_total += b
        record["item_type"] = types.get(item["item_id"])
        record["secondary"] = types.get(item["item_id"]) != "subjective"
        record["tokens_in"], record["tokens_out"] = log.tokens
        record["n_api_calls"] = len(log.rows)
        S.write_json(path, record)
        built += int(record["built"])
        failed += int(not record["built"])
        print(f"[build] {item['item_id']:24s} "
              f"{types.get(item['item_id'], '?')[:4]:4s} "
              f"{'BUILT' if record['built'] else 'DROPPED'} "
              f"({len(log.rows)} calls)"
              + ("" if record["built"] else f" -- {record['reason']}"))

    P3.write_candidates(out_dir, pilot1_dir)
    summary = build_summary4(out_dir, pilot1_dir, pilot3_dir)
    summary.update({
        "runtime_secs": round(time.time() - started, 1),
        "api_calls_this_run": client.n_calls,
        "api_retries_this_run": client.n_retries,
        "tokens_in_this_run": tin_total, "tokens_out_this_run": tout_total,
        "items_skipped_already_built": skipped,
    })
    S.write_json(out_dir / "build_summary.json", summary)

    if not args.skip_cost and client.n_calls:
        append_cost_log(build_cost_entry(
            run_id="stage2_pilot4/build", model=GENERATOR,
            split="stage2_pilot4", variant="b10_v4_generation",
            n_persons=len({i["canonical_id"] for i in items}),
            n_calls=client.n_calls, n_retries=client.n_retries,
            n_parse_failures=0, tokens_in=tin_total, tokens_out=tout_total,
            backend="gemini"), COST_LOG)

    print(f"\n[build] {built} built, {failed} dropped, {skipped} skipped")
    print(f"[build] {client.n_calls} API calls, {tin_total} in / {tout_total} "
          f"out tokens, generator {GENERATOR}")
    return 0


def build_summary4(out_dir: Path, pilot1_dir: Path, pilot3_dir: Path) -> dict:
    records = P3.load_records(out_dir)
    summary = P3.build_summary(out_dir, pilot1_dir)
    deixis = {}
    plaus = {}
    for rec in records:
        if rec.get("built"):
            mode = (rec.get("deixis") or {}).get("mode", "unknown")
            deixis[mode] = deixis.get(mode, 0) + 1
        for rej in rec.get("rejections", []):
            for r in rej.get("reasons", []):
                if r["reason"].startswith("plausibility_"):
                    plaus[r["reason"]] = plaus.get(r["reason"], 0) + 1
    summary.update({
        "contract": CONTRACT,
        "round": 4,
        "kill_rule": KILL_RULE,
        "kill_rule_threshold": KILL_RULE_THRESHOLD,
        "b10_7_margin_consideration": B10_7_MARGIN_CONSIDERATION,
        "template_sha256_v4": C4.TEMPLATE_SHA256_V4,
        "template_sha256_v3_reused": C4.TEMPLATE_SHA256_V3_REUSED,
        "deixis_modes": dict(sorted(deixis.items())),
        "plausibility_rejections": dict(sorted(plaus.items())),
        "style_exemplar_shortfalls": {
            rec["item_id"]: (rec.get("style_exemplars") or {}).get("shortfall")
            for rec in records
            if (rec.get("style_exemplars") or {}).get("shortfall")},
        "item_types": {rec["item_id"]: rec.get("item_type")
                       for rec in records},
        "n_secondary_factual_items": sum(1 for rec in records
                                         if rec.get("secondary")),
        "parser_policy":
            "Every round-4 number is reported under the FROZEN parser (the "
            "contract) and the WIDENED reading side by side, with N for each. "
            "The frozen parser is not changed mid-pilot.",
    })
    return summary


# ---------------------------------------------------------------------------
# Dual-parser gate ingest
# ---------------------------------------------------------------------------


def _exported_sets(out_dir: Path) -> dict:
    """Every exported prompt set on disk, by name, from its meta file."""
    export_dir = out_dir / "exports"
    sets = {}
    for meta in sorted(export_dir.glob("meta_*.jsonl")):
        sets[meta.stem.replace("meta_", "", 1)] = S.read_jsonl(meta)
    return sets


def cmd_export_gate_checked(args) -> int:
    """Round 3's gate export, then the D6-v4.9 twin assertion on what it wrote."""
    rc = P3.cmd_export_gate(args)
    if rc != 0:
        return rc
    out_dir = Path(getattr(args, "out_dir", None) or PILOT4_DIR)
    got = assert_no_cross_visible_twins(_exported_sets(out_dir))
    S.write_json(out_dir / "twin_check.json",
                 {"checked_utc": P3.now(), "phase": "gate", **got})
    print(f"[export-gate] D6-v4.9 twin check passed on "
          f"{got['n_sets_checked']} prompt set(s)")
    return 0


def cmd_export_pred_checked(args) -> int:
    """Round 2's prediction export, then the D6-v4.9 twin assertion."""
    rc = P2.cmd_export_pred(args)
    if rc != 0:
        return rc
    out_dir = Path(getattr(args, "out_dir", None) or PILOT4_DIR)
    got = assert_no_cross_visible_twins(_exported_sets(out_dir))
    S.write_json(out_dir / "twin_check.json",
                 {"checked_utc": P3.now(), "phase": "prediction", **got})
    print(f"[export-pred] D6-v4.9 twin check passed on "
          f"{got['n_sets_checked']} prompt set(s)")
    return 0


def cmd_ingest_gate_dual(args) -> int:
    """Round 3's gate ingest, plus the both-parser tables (D6-v4.5).

    The frozen ingest runs first and unchanged, so ``gate_results.json`` is
    exactly what round 3 would have written and the gate decision is made on
    the contract parser. The dual tables are written beside it.
    """
    out_dir = Path(getattr(args, "out_dir", None) or PILOT4_DIR)
    rc = P2.cmd_ingest_gate(args)
    if rc != 0:
        return rc
    nodedir = Path(args.nodedir)
    metas = S.read_jsonl(out_dir / "exports" / "meta_gate.jsonl")
    by_idx = {int(r["idx"]): r for r in
              S.read_jsonl(nodedir / "completions_gate.jsonl")}
    records = [DP.dual_score(m, P2._completion_text(by_idx.get(int(m["idx"]))))
               for m in metas]
    both = DP.both_readings(records)
    frozen_acc = both["frozen"]["argmax_accuracy"]
    widened_acc = both["widened"]["argmax_accuracy"]
    fired = [a for a in (frozen_acc, widened_acc)
             if a is not None and a >= KILL_RULE_THRESHOLD]
    doc = {
        "pilot": PILOT_BANNER, "contract": CONTRACT, "phase": "gate",
        "ingested_utc": P3.now(),
        "kill_rule": KILL_RULE, "kill_rule_threshold": KILL_RULE_THRESHOLD,
        "kill_rule_fires": bool(fired),
        "kill_rule_note":
            "The FROZEN reading is the contract number and is what the rule is "
            "read on. The widened accuracy is reported beside it; if the two "
            "straddle the threshold that is itself the finding and the owner "
            "decides.",
        "b10_7_margin_consideration": B10_7_MARGIN_CONSIDERATION,
        "both_readings": both,
        "records": records,
    }
    S.write_json(out_dir / "gate_results_dual.json", doc)
    print(f"[ingest-gate] FROZEN  acc {frozen_acc} "
          f"(n_parsed {both['frozen']['n_parsed']}/{both['frozen']['n_prompts']})")
    print(f"[ingest-gate] WIDENED acc {widened_acc} "
          f"(n_parsed {both['widened']['n_parsed']}/"
          f"{both['widened']['n_prompts']}, "
          f"{both['n_recovered_by_widening']} recovered)")
    verdict = ("FIRES -- forced choice is dead on this corpus; STOP, no pred, "
               "no round 5" if fired else "does not fire")
    print(f"[ingest-gate] KILL RULE (>= {KILL_RULE_THRESHOLD}): {verdict}")
    return 0


# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pilot1-dir", default=None)
    ap.add_argument("--pilot3-dir", default=None)
    ap.add_argument("--out-dir", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("classify").set_defaults(fn=cmd_classify)

    p_b = sub.add_parser("build")
    p_b.add_argument("--force", action="store_true")
    p_b.add_argument("--call-cap", type=int, default=DEFAULT_CALL_CAP)
    p_b.add_argument("--skip-cost", action="store_true")
    p_b.add_argument("--include-factual", action="store_true",
                     help="also build the factual-explanation items, labelled "
                          "SECONDARY in every table")
    p_b.set_defaults(fn=cmd_build, client=None)

    # export-gate / plan / bootstrap are round 3's, unchanged: the gate arm,
    # the frozen D8 renderer and the node-hour model must be identical across
    # rounds or the gate numbers are not comparable. Only the LABELS differ.
    p_g = sub.add_parser("export-gate")
    p_g.add_argument("--force", action="store_true")
    p_g.set_defaults(fn=cmd_export_gate_checked, banner=PILOT_BANNER,
                     contract=CONTRACT)

    sub.add_parser("verify").set_defaults(fn=P3.cmd_verify)
    sub.add_parser("plan").set_defaults(fn=P3.cmd_plan)
    sub.add_parser("bootstrap").set_defaults(
        fn=P3.cmd_bootstrap, banner=PILOT_BANNER, contract=CONTRACT,
        run_name="stage2_pilot4",
        node_run=f"{P2.NODE_ROOT}/runs/stage2_pilot4")

    p_ig = sub.add_parser("ingest-gate")
    p_ig.add_argument("--nodedir", required=True)
    p_ig.add_argument("--skip-cost", action="store_true")
    p_ig.set_defaults(fn=cmd_ingest_gate_dual, job_name="stage2_pilot4_gate",
                      run_id="stage2_pilot4/gate", variant="stage2_b10v4_gate",
                      split_label="stage2_pilot4", banner=PILOT_BANNER,
                      contract=CONTRACT)

    sub.add_parser("finalize").set_defaults(fn=P2.cmd_finalize,
                                            banner=PILOT_BANNER)

    p_ep = sub.add_parser("export-pred")
    p_ep.add_argument("--force", action="store_true")
    p_ep.add_argument("--pre-gate", action="store_true")
    p_ep.set_defaults(fn=cmd_export_pred_checked, banner=PILOT_BANNER,
                      contract=CONTRACT,
                      extra_renderer={
                          "counterfactuals4_template_sha256":
                              C4.TEMPLATE_SHA256_V4,
                          "counterfactuals4_file_sha256": P2.sha256_file(
                              _ROOT / "src/doppler/counterfactuals4.py"),
                          "dual_parse_file_sha256": P2.sha256_file(
                              _ROOT / "src/doppler/dual_parse.py")})

    p_ip = sub.add_parser("ingest-pred")
    p_ip.add_argument("--nodedir", required=True)
    p_ip.add_argument("--skip-cost", action="store_true")
    p_ip.set_defaults(fn=P2.cmd_ingest_pred, job_name="stage2_pilot4_pred",
                      run_id="stage2_pilot4/prediction",
                      variant="stage2_b10v4_pred", split_label="stage2_pilot4",
                      banner=PILOT_BANNER, contract=CONTRACT)

    for name, fn in (("bill", P2.cmd_bill), ("record", P2.cmd_record)):
        p = sub.add_parser(name)
        p.add_argument("--name", required=True)
        p.add_argument("--job-id", required=(name == "bill"), default=None)
        if name == "record":
            p.add_argument("--status", default=None)
            p.add_argument("--node-hours", type=float, default=None)
            p.add_argument("--note", default=None)
            p.add_argument("--anomaly", default=None)
        p.set_defaults(fn=fn)

    args = ap.parse_args(argv)
    if getattr(args, "out_dir", None) is None:
        args.out_dir = str(PILOT4_DIR)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
