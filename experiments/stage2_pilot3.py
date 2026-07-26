"""Stage 2 pilot ROUND 3 driver — generated same-question counterfactuals.

PILOT. Pipeline validation only. Nothing here answers a pre-registered bar.

Binding design: PREREGISTRATION_AMENDMENT_2.md **B10** (commit 9949c9d). Where
this file and B10 differ, B10 wins. Implementation rules are documented in the
SPEC v1.9 section.

What changed and why. Rounds 1 and 2 both put the zero-information arm at 100%:
round 1 with other people's answers, round 2 with the same subject's other
answers. Round 2's decomposition found the mechanism — entity-stripping changed
nothing (10/10), removing the question collapsed accuracy to 1/10 — so the solve
rode entirely on the true answer being the only option RESPONSIVE to the
question shown. Any distractor taken from a real transcript is an answer to a
different question, so no sourcing rule can fix that.

B10's instrument generates the distractors as answers to the SAME question,
taking positions that conflict with the subject's. **What is scored changes with
it: the claim is that the twin identifies the person's actual POSITION among
plausible alternatives, not that it picks a verbatim transcript answer.** Every
artifact this driver writes carries that reframing.

Build pipeline, per item (every call logged to genlog/):

    1. GENERATE   4 conflicting answers to the same question   (temp 0.7)
    2. GUARD      era / name leak / grounding quote / copy-of-true  (offline)
    3. PARAPHRASE all survivors AND the true answer, one call each,
                  identical template, so the paraphraser cannot tell which
                  text is real                                  (temp 0.0)
    4. POSITION   is the paraphrased true answer still the same position?
    5. GUARD      re-run the offline guards on the paraphrases
    6. CONTRADICT each candidate distractor against the true position
    7. LADDER     record the tightest D6 rung the option set satisfies
    8. SHUFFLE    D6's item-id seed; correct_index read off after

Generator separation (B10.3) is enforced here: the generator is a Gemini model
that is NOT the robustness scorer, and its exact version string is recorded in
every artifact. Gemma never scores its own writing — pilot scoring is Gemma-only.

API generation is not seed-reproducible. The genlog IS the provenance: every
prompt and every raw completion is committed.

Subcommands
-----------
``build``        run the pipeline (spends API calls; resumable per item).
``sheet``        the B10.8 detectability sheet + its key.
``export-gate``  zero-information gate prompts for every candidate item.
``verify``       re-run guards and digests against what is ON DISK.
``plan``         node-hours for both GPU phases. Writes nothing.
``bootstrap``    config + both sbatch files + the run manifest.
``bill`` / ``record`` / ``ingest-gate`` / ``ingest-pred``  delegate to round 2.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import stage2_pilot as P1  # noqa: E402
import stage2_pilot2 as P2  # noqa: E402

from doppler import counterfactuals as CF  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402
from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402
from doppler.distractors import density_bucket, entity_density, strip_entities  # noqa: E402

RESULTS_DIR = _ROOT / "results"
PILOT1_DIR = RESULTS_DIR / "stage2_pilot"
PILOT3_DIR = RESULTS_DIR / "stage2_pilot3"
COST_LOG = RESULTS_DIR / "cost_log.jsonl"

PILOT_BANNER = ("PILOT -- pipeline validation on dev subjects; "
                "no research conclusions.")
CONTRACT = "SPEC.md v1.9 (Amendment 2 B10)"

#: The binding reframing (B10.2). Every artifact carries it.
SCORED_CLAIM = (
    "The claim scored is that the twin identifies the person's actual POSITION "
    "among plausible alternative positions on the same question -- NOT that it "
    "picks a verbatim transcript answer.")

# ---------------------------------------------------------------------------
# Generator (B10.3)
# ---------------------------------------------------------------------------

#: The robustness scorer named by Amendment 1 A3 / CLAUDE.md. The generator must
#: not be this model.
ROBUSTNESS_SCORER = "gemini-3.5-flash-lite"

#: The generator. Different family version AND different tier from the
#: robustness scorer, so B10.3 holds on the strict reading of "version".
#: Availability was checked against the key before selection; measured 12/12
#: calls in 53.9 s with no retries, which supports a build of this size.
GENERATOR = "gemini-3.1-pro-preview"

GEN_TEMPERATURE = 0.7      # counterfactuals need diversity
CHECK_TEMPERATURE = 0.0    # paraphrase and the checks must not wander

#: Token budgets, sized on MEASURED thinking cost, not guessed.
#:
#: gemini-3.1-pro-preview refuses thinking_budget=0 ("this model only works in
#: thinking mode"), and its hidden thinking is charged against
#: max_output_tokens. A 2048 budget was consumed 1963/2048 by thinking and the
#: visible answer was truncated at 81 tokens mid-sentence -- which is exactly
#: how the first trial item failed, with the generator appearing to return 2
#: blocks instead of 4. Measured at 8192: 3,205 thinking + 273 visible tokens,
#: finish_reason STOP, all 4 blocks present.
#: Measured again on a 228-word answer: the paraphrase spent ~3,900 tokens
#: thinking and returned 163 visible tokens ending mid-word under a 4,096
#: budget. Thinking cost scales with input, so the budgets are sized for the
#: longest real answer rather than the median one.
GEN_MAX_TOKENS = 16384
PARA_MAX_TOKENS = 16384
CHECK_MAX_TOKENS = 8192

#: Hard ceiling on API calls for one build invocation. A runaway loop costs
#: quota that the next day's work needs.
DEFAULT_CALL_CAP = 900

# ---------------------------------------------------------------------------
# GPU phases
# ---------------------------------------------------------------------------

NODE_RUN = f"{P2.NODE_ROOT}/runs/stage2_pilot3"
GATE_WALLTIME = "00:20:00"
PRED_WALLTIME = "00:30:00"
GATE_QOS = P2.GATE_QOS
#: The orchestrator's cap for round 3, across every attempt of both phases.
BUDGET_NODE_HOURS = 1.2
PROJECTION_ABORT_NODE_HOURS = 1.2

ARMS = P2.ARMS
VARIANTS = P2.VARIANTS
GATE_ARM = P2.GATE_ARM
GATE_VARIANT = P2.GATE_VARIANT

#: Seed for the B10.8 detectability sheet's shuffle. Presentation only.
SHEET_SEED = 53
SHEET_REAL = 10
SHEET_CONTROL = 10


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


def safe_id(item_id: str) -> str:
    return item_id.replace(":", "_")


def rel(path: Path) -> str:
    return P1.rel(path)


# ---------------------------------------------------------------------------
# Items and per-subject context
# ---------------------------------------------------------------------------


def all_items(pilot1_dir: Path) -> list[dict]:
    """Every D4-eligible test-interview item, all Q-A dev subjects.

    Round 3 is not supply-limited: the distractors are written, not harvested,
    so the whole round-1 extraction is in play rather than the 10 that had a
    big enough same-subject pool. C00292 stays burned_for_qa and is excluded.
    """
    out = []
    for subject in P1.prediction_subjects(P1.dev_subjects(pilot1_dir)):
        cid = subject["canonical_id"]
        for row in S.read_jsonl(pilot1_dir / "subjects" / cid
                                / "qa_items.jsonl"):
            if row["canonical_id"] != cid:
                raise fatal(f"{row['item_id']} claims {row['canonical_id']}")
            out.append(row)
    return out


def subject_context(pilot1_dir: Path) -> dict:
    """Per subject: name variants, rendered grounding (for the leak guard), date."""
    pool = P1.pool_rows()
    ctx = {}
    for subject in P1.prediction_subjects(P1.dev_subjects(pilot1_dir)):
        cid = subject["canonical_id"]
        variants = P1.name_variants(pool[cid])
        segments, _ = P1.subject_grounding(cid, pilot1_dir)
        raw = R.render_grounding(segments, P2.GROUNDING_BUDGET_WORDS)
        split = S.load_split(cid, pilot1_dir)
        ctx[cid] = {
            "variants": variants,
            "canonical_name": pool[cid]["canonical_name"],
            "grounding_raw": raw,
            "grounding_redacted": R.redact(raw, variants),
            "test_date": split["test"]["date"],
        }
    return ctx


# ---------------------------------------------------------------------------
# The generation pipeline
# ---------------------------------------------------------------------------


class GenLog:
    """Append-only record of every API call made for one item."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.rows: list[dict] = []

    def add(self, step: str, prompt: str, completion: str, tin: int, tout: int,
            **extra) -> None:
        self.rows.append({
            "utc": now(), "step": step, "model": GENERATOR,
            "temperature": extra.pop("temperature", CHECK_TEMPERATURE),
            "tokens_in": tin, "tokens_out": tout,
            "prompt": prompt, "completion": completion, **extra})

    def flush(self) -> None:
        S.write_jsonl(self.path, self.rows)

    @property
    def tokens(self) -> tuple[int, int]:
        return (sum(r["tokens_in"] for r in self.rows),
                sum(r["tokens_out"] for r in self.rows))


def _configure(client, temperature: float, max_output_tokens: int) -> None:
    """Retune the client between pipeline steps.

    Generation wants diversity and a long budget; the paraphrase and the two
    checks want neither. The config object is rebuilt rather than mutated in
    place, because it is a pydantic model on some SDK versions and a silently
    ignored mutation would leave every step running at the wrong temperature --
    exactly the kind of failure that would not show up until the outputs looked
    subtly wrong.
    """
    from google.genai import types

    client.temperature = float(temperature)
    client.max_output_tokens = int(max_output_tokens)
    client._config = types.GenerateContentConfig(
        temperature=float(temperature),
        max_output_tokens=int(max_output_tokens),
        candidate_count=1,
    )


def _guard_offline(text: str, *, item: dict, ctx: dict, stage: str) -> dict:
    """Every deterministic rejection reason for one generated option."""
    reasons = []
    era = CF.era_violations(text, ctx["test_date"])
    if era:
        reasons.append({"reason": "era_violation", "detail": era})
    named = CF.names_subject(text, ctx["variants"])
    if named:
        reasons.append({"reason": "names_subject", "detail": named})
    quote = CF.quotes_grounding(text, [ctx["grounding_raw"],
                                       ctx["grounding_redacted"]])
    if quote:
        reasons.append({"reason": "quotes_grounding", "detail": quote})
    if CF.copies_true(text, item["answer"]):
        reasons.append({"reason": "copies_true_answer", "detail": None})
    return {"stage": stage, "ok": not reasons, "reasons": reasons}


def build_item(client, item: dict, ctx: dict, log: GenLog) -> dict:
    """One item, end to end. Returns the build record (built True/False).

    Order matters and is not the order B10 lists the rules in. The true answer
    is paraphrased FIRST, and the counterfactuals are then generated against
    the paraphrase, because the paraphrase is what the option set actually
    shows. Generating against the verbatim answer produced 49-53 word options
    for a 42-word true option in the trial -- outside the length ladder before
    a single check had run.
    """
    question, true_answer = item["question"], item["answer"]
    rejections: list[dict] = []

    def paraphrase(text_in: str, tag: str) -> str:
        """One neutral paraphrase, refusing a truncated one.

        A truncated paraphrase is not a paraphrase -- it silently drops the
        answer's later claims, which the position check then correctly calls a
        changed position. Returning "" here makes the cause explicit in the log
        instead of blaming the checker.
        """
        _configure(client, CHECK_TEMPERATURE, PARA_MAX_TOKENS)
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
                **extra}

    # --- 1. paraphrase the true answer (B10.4) ------------------------------
    _configure(client, CHECK_TEMPERATURE, CHECK_MAX_TOKENS)
    para_true = paraphrase(true_answer, "true")
    if not para_true:
        para_true = paraphrase(true_answer, "true_retry_truncated")
    if not para_true:
        return fail("true answer paraphrase was empty or truncated twice")

    # --- 2. position preservation, one retry before dropping ----------------
    def check_position(candidate: str, tag: str) -> tuple[str | None, str | None]:
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

    # --- 3. generate, conditioned on the PARAPHRASED true answer ------------
    prompt = CF.gen_prompt(question, para_true, ctx["test_date"])
    _configure(client, GEN_TEMPERATURE, GEN_MAX_TOKENS)
    text, tin, tout = client.generate(prompt)
    log.add("generate", prompt, text, tin, tout, temperature=GEN_TEMPERATURE)
    raw = CF.parse_generated(text)
    if len(raw) < CF.N_DISTRACTORS:
        return fail(f"generator returned {len(raw)} blocks",
                    position_check=position)

    # --- 4. offline guards on the raw text ----------------------------------
    survivors = []
    for k, cand in enumerate(raw):
        verdict_g = _guard_offline(cand, item=item, ctx=ctx, stage="raw")
        if verdict_g["ok"]:
            survivors.append(cand)
        else:
            rejections.append({"slot": k, "text": cand, **verdict_g})

    # --- 5. paraphrase every generated option, identical template -----------
    _configure(client, CHECK_TEMPERATURE, CHECK_MAX_TOKENS)
    para_cands = []
    for k, cand in enumerate(survivors):
        out = paraphrase(cand, f"gen{k}")
        if not out:
            rejections.append({
                "slot": k, "text": cand, "stage": "paraphrase", "ok": False,
                "reasons": [{"reason": "empty_or_truncated_paraphrase"}]})
            continue
        # --- 6. guards again: paraphrase can reintroduce a violation --------
        verdict_g = _guard_offline(out, item=item, ctx=ctx, stage="paraphrased")
        if not verdict_g["ok"]:
            rejections.append({"slot": k, "text": out, **verdict_g})
            continue
        para_cands.append(out)

    # --- 7. contradiction check (B10.5) -------------------------------------
    accepted: list[dict] = []
    for cand in para_cands:
        if len(accepted) >= CF.N_DISTRACTORS:
            break
        cp = CF.contra_prompt(question, para_true, cand)
        got, a, b = client.generate(cp)
        log.add("contradiction_check", cp, got, a, b)
        v, w = CF.parse_verdict(got, ("CONFLICT", "AGREE", "UNRELATED"))
        if v == "CONFLICT":
            accepted.append({"text": cand, "why": w})
        else:
            rejections.append({
                "text": cand, "stage": "contradiction", "ok": False,
                "reasons": [{"reason":
                             f"contradiction_{(v or 'unparsed').lower()}",
                             "detail": w}]})

    spare = [c for c in para_cands if c not in [a["text"] for a in accepted]]
    if len(accepted) < CF.N_DISTRACTORS:
        return fail(f"only {len(accepted)} distractors survived the checks",
                    position_check=position, spare=spare)

    # --- 8. option set, ladder, shuffle -------------------------------------
    options = [{"text": para_true, "kind": "true", "origin": "paraphrased_real",
                "why": None}]
    for a in accepted[:CF.N_DISTRACTORS]:
        options.append({"text": a["text"], "kind": "distractor",
                        "origin": "generated", "why": a["why"]})
    for opt in options:
        opt["answer_words"] = R.word_count(opt["text"])
        opt["entity_density"] = entity_density(opt["text"])
        opt["bucket"] = density_bucket(opt["entity_density"])
    rung = CF.match_rung(para_true, [o["text"] for o in options
                                     if o["kind"] == "distractor"])

    random.Random(CF.shuffle_seed(item["item_id"])).shuffle(options)
    correct = [i for i, o in enumerate(options) if o["kind"] == "true"]
    if len(correct) != 1:
        raise fatal(f"{item['item_id']}: {len(correct)} true options")

    flags = [f"relax_rung_{rung}"] if rung is not None else ["ladder_exceeded"]
    return {
        "item_id": item["item_id"], "canonical_id": item["canonical_id"],
        "built": True,
        "question": question,
        "true_answer_verbatim": true_answer,
        "true_answer_paraphrased": para_true,
        "options": options,
        "options_stripped": [strip_entities(o["text"]) for o in options],
        "correct_index": correct[0],
        "relax_rung": rung, "flags": flags,
        "position_check": position,
        "rejections": rejections,
        "spare_generated": spare,
        "generator": GENERATOR,
        "scored_claim": SCORED_CLAIM,
    }


def cmd_build(args) -> int:
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    out_dir = Path(getattr(args, "out_dir", None) or PILOT3_DIR)
    items = all_items(pilot1_dir)
    ctx = subject_context(pilot1_dir)
    items_dir, genlog_dir = out_dir / "items", out_dir / "genlog"
    items_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    client = args.client
    if client is None:
        from doppler.gemini import GeminiClient
        client = GeminiClient(max_calls=args.call_cap,
                              temperature=CHECK_TEMPERATURE,
                              max_output_tokens=CHECK_MAX_TOKENS)
        if client.model_name == GENERATOR:
            raise fatal("MODEL_NAME already names the generator; the override "
                        "below is what documents B10.3, so this is ambiguous")
        # B10.3: the generator is NEVER the robustness scorer. Overriding the
        # attribute (rather than editing the shared client) keeps the module
        # other experiments import untouched.
        client.model_name = GENERATOR
    if getattr(client, "model_name", GENERATOR) == ROBUSTNESS_SCORER:
        raise fatal(f"B10.3 violation: generator is {ROBUSTNESS_SCORER}")

    built = skipped = failed = 0
    tin_total = tout_total = 0
    for item in items:
        path = items_dir / f"{safe_id(item['item_id'])}.json"
        if path.exists() and not args.force:
            skipped += 1
            continue
        log = GenLog(genlog_dir / f"{safe_id(item['item_id'])}.jsonl")
        try:
            record = build_item(client, item, ctx[item["canonical_id"]], log)
        finally:
            log.flush()
            a, b = log.tokens
            tin_total += a
            tout_total += b
        record["tokens_in"], record["tokens_out"] = log.tokens
        record["n_api_calls"] = len(log.rows)
        S.write_json(path, record)
        if record["built"]:
            built += 1
        else:
            failed += 1
        print(f"[build] {item['item_id']:28s} "
              f"{'BUILT' if record['built'] else 'DROPPED'} "
              f"({len(log.rows)} calls)"
              + ("" if record["built"] else f" -- {record['reason']}"))

    write_candidates(out_dir, pilot1_dir)
    summary = build_summary(out_dir, pilot1_dir)
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
            run_id="stage2_pilot3/build", model=GENERATOR, split="stage2_pilot3",
            variant="b10_generation", n_persons=len(ctx),
            n_calls=client.n_calls, n_retries=client.n_retries,
            n_parse_failures=0, tokens_in=tin_total, tokens_out=tout_total,
            backend="gemini"), COST_LOG)

    print(f"\n[build] {built} built, {failed} dropped, {skipped} skipped")
    print(f"[build] {client.n_calls} API calls, {tin_total} in / {tout_total} "
          f"out tokens, generator {GENERATOR}")
    return 0


def load_records(out_dir: Path) -> list[dict]:
    rows = []
    for path in sorted((out_dir / "items").glob("*.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    return rows


def write_candidates(out_dir: Path, pilot1_dir: Path) -> None:
    """Per-subject candidate files in the shape the exporters expect."""
    by_subject: dict[str, list[dict]] = {}
    for rec in load_records(out_dir):
        if not rec["built"]:
            continue
        by_subject.setdefault(rec["canonical_id"], []).append({
            "item_id": rec["item_id"], "canonical_id": rec["canonical_id"],
            "options": rec["options"],
            "options_stripped": rec["options_stripped"],
            "correct_index": rec["correct_index"],
            "relax_rung": rec["relax_rung"], "flags": rec["flags"],
            "true_answer_paraphrased": rec["true_answer_paraphrased"],
            "generator": rec["generator"],
        })
    for cid, rows in by_subject.items():
        rows.sort(key=lambda r: r["item_id"])
        S.write_jsonl(out_dir / "subjects" / cid / "candidates.jsonl", rows)


def build_summary(out_dir: Path, pilot1_dir: Path) -> dict:
    records = load_records(out_dir)
    per_subject: dict[str, dict] = {}
    reasons: dict[str, int] = {}
    rungs: dict[str, int] = {}
    n_rejected = 0
    for rec in records:
        cid = rec["canonical_id"]
        e = per_subject.setdefault(cid, {"canonical_id": cid, "attempted": 0,
                                         "built": 0, "dropped": 0})
        e["attempted"] += 1
        e["built" if rec["built"] else "dropped"] += 1
        for rej in rec.get("rejections", []):
            for r in rej.get("reasons", []):
                reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
                n_rejected += 1
        if rec["built"]:
            key = ("ladder_exceeded" if rec["relax_rung"] is None
                   else f"rung_{rec['relax_rung']}")
            rungs[key] = rungs.get(key, 0) + 1
    return {
        "pilot": PILOT_BANNER, "contract": CONTRACT,
        "scored_claim": SCORED_CLAIM,
        "built_utc": now(),
        "generator": GENERATOR,
        "robustness_scorer": ROBUSTNESS_SCORER,
        "generator_separation":
            "B10.3 holds: the generator is a different Gemini version AND a "
            "different tier from the robustness scorer, and pilot scoring is "
            "Gemma-only, so no scored model reads its own writing.",
        "gen_temperature": GEN_TEMPERATURE,
        "check_temperature": CHECK_TEMPERATURE,
        "template_sha256": CF.TEMPLATE_SHA256,
        "n_items_attempted": len(records),
        "n_items_built": sum(1 for r in records if r["built"]),
        "n_items_dropped": sum(1 for r in records if not r["built"]),
        "drop_reasons": sorted({r["reason"] for r in records
                                if not r["built"]}),
        "per_subject": sorted(per_subject.values(),
                              key=lambda e: e["canonical_id"]),
        "option_rejections_total": n_rejected,
        "option_rejections_by_reason": dict(sorted(reasons.items())),
        "relax_rungs": dict(sorted(rungs.items())),
        "position_check_retries": sum(
            1 for r in records if (r.get("position_check") or {}).get("retried")),
        "upstream_sha256": P2.upstream_provenance(pilot1_dir),
        "note": "API generation is not seed-reproducible. genlog/ holds every "
                "generator prompt and every raw completion.",
    }


# ---------------------------------------------------------------------------
# B10.8 detectability sheet
# ---------------------------------------------------------------------------


def sheet_plan(out_dir: Path, n_real: int = SHEET_REAL,
               n_control: int = SHEET_CONTROL, seed: int = SHEET_SEED) -> dict:
    """Which items become real entries and which become all-generated controls.

    A control needs four generated options and no real answer. Items are used
    for a control only when the build left an unused spare, so a control costs
    no extra generation. Real and control draws are disjoint wherever the item
    count allows; any overlap is recorded in the key, never hidden.
    """
    records = [r for r in load_records(out_dir) if r["built"]]
    usable_control = [r for r in records
                      if len(r.get("spare_generated") or []) >= 1]
    rng = random.Random(seed)
    order = sorted(records, key=lambda r: r["item_id"])
    rng.shuffle(order)
    real = order[:n_real]
    real_ids = {r["item_id"] for r in real}

    pool = [r for r in order if r["item_id"] not in real_ids
            and r in usable_control]
    extra = [r for r in order if r["item_id"] in real_ids and r in usable_control]
    control = (pool + extra)[:n_control]
    return {"real": real, "control": control,
            "overlap": sorted({r["item_id"] for r in control} & real_ids)}


def control_options(rec: dict) -> list[str] | None:
    """Four generated options for a control entry, or None if there are < 4.

    The three distractors the real item uses plus one unused spare. The real
    answer never appears, so a control has no correct answer at all — which is
    what makes it a control for "can you spot the real one" rather than a
    harder version of the same question.
    """
    generated = [o["text"] for o in rec["options"] if o["kind"] == "distractor"]
    spares = list(rec.get("spare_generated") or [])
    if len(generated) + len(spares) < 4:
        return None
    return generated + spares[:4 - len(generated)]


def cmd_sheet(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT3_DIR)
    plan = sheet_plan(out_dir)
    entries = []
    for rec in plan["real"]:
        entries.append({"kind": "real", "item_id": rec["item_id"],
                        "question": rec["question"],
                        "options": [o["text"] for o in rec["options"]],
                        "correct_index": rec["correct_index"]})
    for rec in plan["control"]:
        opts = control_options(rec)
        if opts is None:
            continue
        rng = random.Random(CF.shuffle_seed(rec["item_id"]) ^ SHEET_SEED)
        opts = list(opts)
        rng.shuffle(opts)
        entries.append({"kind": "control", "item_id": rec["item_id"],
                        "question": rec["question"], "options": opts,
                        "correct_index": None})
    random.Random(SHEET_SEED).shuffle(entries)

    labels = "ABCD"
    sheet = [
        "# Stage 2 pilot 3 — detectability sheet (Amendment 2 B10.8)",
        "",
        "**Do not read `DETECTABILITY_KEY.md` until you have finished.**",
        "",
        "Twenty questions. Each has four possible answers. In some of them one "
        "answer is what the person really said (rewritten in neutral English); "
        "in the others every answer was written by a model and none is real.",
        "",
        "For each question, write the letter you think is the real answer, or "
        "`none` if you think none of them is real. Guessing is fine — that is "
        "what the number is for.",
        "",
        "---", ""]
    for i, e in enumerate(entries, 1):
        sheet.append(f"## {i}.")
        sheet.append("")
        sheet.append(f"**Q.** {e['question']}")
        sheet.append("")
        for label, text in zip(labels, e["options"]):
            sheet.append(f"**{label}.** {text}")
            sheet.append("")
        sheet.append("Your answer: ______")
        sheet.append("")
        sheet.append("---")
        sheet.append("")
    (out_dir / "DETECTABILITY_SHEET.md").write_text("\n".join(sheet),
                                                    encoding="utf-8")

    key = [
        "# Detectability sheet — KEY (Amendment 2 B10.8)",
        "",
        f"Seed {SHEET_SEED}. {sum(1 for e in entries if e['kind']=='real')} real "
        f"entries, {sum(1 for e in entries if e['kind']=='control')} controls.",
        "",
        "A **real** entry has one paraphrased true answer among three generated "
        "distractors. A **control** entry is four generated answers with no "
        "real answer present; the correct response to a control is `none`.",
        "",
        "Chance on a real entry, if the owner always names a letter, is 0.25. "
        "The control entries measure the false-positive rate: naming any letter "
        "on a control is a false positive.",
        "",
        f"Item overlap between real and control draws: "
        f"{plan['overlap'] or 'none'}.",
        "",
        "| # | kind | item_id | real answer |",
        "|---|---|---|---|"]
    for i, e in enumerate(entries, 1):
        ans = labels[e["correct_index"]] if e["kind"] == "real" else "none"
        key.append(f"| {i} | {e['kind']} | `{e['item_id']}` | **{ans}** |")
    (out_dir / "DETECTABILITY_KEY.md").write_text("\n".join(key) + "\n",
                                                  encoding="utf-8")
    S.write_json(out_dir / "detectability_plan.json", {
        "seed": SHEET_SEED, "n_entries": len(entries),
        "n_real": sum(1 for e in entries if e["kind"] == "real"),
        "n_control": sum(1 for e in entries if e["kind"] == "control"),
        "overlap": plan["overlap"],
        "entries": [{"n": i, "kind": e["kind"], "item_id": e["item_id"],
                     "correct_index": e["correct_index"]}
                    for i, e in enumerate(entries, 1)]})
    print(f"[sheet] {len(entries)} entries -> "
          f"{rel(out_dir / 'DETECTABILITY_SHEET.md')}")
    print(f"[sheet] key -> {rel(out_dir / 'DETECTABILITY_KEY.md')}")
    return 0


# ---------------------------------------------------------------------------
# Prompt rendering (frozen D8 renderer, via round 1)
# ---------------------------------------------------------------------------


def load_candidate_items(cid: str, out_dir: Path, pilot1_dir: Path,
                         final: bool = False) -> list[dict]:
    """Candidate (or gate-surviving) items in the renderer's expected shape.

    Unlike rounds 1 and 2, the TRUE option is the PARAPHRASED answer, not the
    verbatim transcript text (B10.4). ``answer`` is therefore the paraphrase --
    it is what the model is shown and what the leak guards must be run against.
    """
    if final:
        rows = [r for r in S.read_jsonl(out_dir / "items_final.jsonl")
                if r["canonical_id"] == cid]
    else:
        path = out_dir / "subjects" / cid / "candidates.jsonl"
        rows = S.read_jsonl(path) if path.exists() else []
    base = {r["item_id"]: r for r in
            S.read_jsonl(pilot1_dir / "subjects" / cid / "qa_items.jsonl")}
    items = []
    for row in rows:
        src = base[row["item_id"]]
        texts = [o["text"] for o in row["options"]]
        correct = int(row["correct_index"])
        if row["options"][correct]["kind"] != "true":
            raise fatal(f"{row['item_id']}: correct_index is not the true option")
        if texts[correct] != row["true_answer_paraphrased"]:
            raise fatal(f"{row['item_id']}: true option is not the paraphrase")
        items.append({
            "item_id": row["item_id"], "canonical_id": cid,
            "transcript_id": src["transcript_id"],
            "q_turn_idx": src["q_turn_idx"], "question": src["question"],
            "answer": row["true_answer_paraphrased"],
            "answer_words": R.word_count(row["true_answer_paraphrased"]),
            "options": {"standard": texts,
                        "stripped": list(row["options_stripped"])},
            "correct_index": correct, "relax_rung": row.get("relax_rung"),
            "flags": row.get("flags", [])})
    return items


def build_phase(out_dir: Path, pilot1_dir: Path, *, arms, final: bool) -> dict:
    """Render every (arm, variant) prompt for the chosen item set, with guards."""
    subjects = P1.prediction_subjects(P1.dev_subjects(pilot1_dir))
    dev_ids = {s["canonical_id"] for s in P1.dev_subjects(pilot1_dir)}
    pool = P1.pool_rows()
    pairs = P1.imposter_pairs(pilot1_dir / "imposter_pairs.json")
    need_grounding = any(a in R.GROUNDED_ARMS for a in arms)

    sets = {(arm, v): [] for arm in arms for v in VARIANTS}
    per_subject: dict[str, dict] = {}
    for subject in subjects:
        cid = subject["canonical_id"]
        if subject.get("burned_for_qa"):
            raise fatal(f"{cid} is burned_for_qa")
        items = load_candidate_items(cid, out_dir, pilot1_dir, final=final)
        if not items:
            per_subject[cid] = {"canonical_id": cid, "n_items": 0,
                                "item_ids": []}
            continue
        row = pool[cid]
        variants = P1.name_variants(row)
        twin_block = donor_block = donor_variants = None
        donor_id = pairs.get(cid)
        if need_grounding:
            segments, _ = P1.subject_grounding(cid, pilot1_dir)
            twin_block = R.redact(
                R.render_grounding(segments, P2.GROUNDING_BUDGET_WORDS),
                variants)
            R.assert_redacted(twin_block, variants)
            donor_variants = P1.name_variants(pool[donor_id])
            dsegs, _ = P1.donor_grounding(donor_id, pilot1_dir)
            donor_block = R.redact(
                R.render_grounding(dsegs, P2.GROUNDING_BUDGET_WORDS),
                donor_variants)
            R.assert_redacted(donor_block, donor_variants)
        for item in items:
            for arm in arms:
                if arm == "imposter_redacted":
                    block, donor_check = donor_block, donor_variants
                elif arm in R.GROUNDED_ARMS:
                    block, donor_check = twin_block, None
                else:
                    block, donor_check = None, None
                for variant in VARIANTS:
                    built = P1.render_and_guard(
                        arm, variant, item,
                        subject_name=row["canonical_name"],
                        subject_variants=variants, grounding_block=block,
                        donor_variants=donor_check)
                    built.update({
                        "item_id": item["item_id"], "canonical_id": cid,
                        "arm": arm, "variant": variant,
                        "correct_index": item["correct_index"],
                        "n_options": len(item["options"][variant]),
                        "donor_id": donor_id if arm == "imposter_redacted"
                        else None})
                    sets[(arm, variant)].append(built)
        per_subject[cid] = {"canonical_id": cid,
                            "canonical_name": row["canonical_name"],
                            "n_items": len(items),
                            "item_ids": [i["item_id"] for i in items],
                            "donor_id": donor_id}
    n = {k: len(v) for k, v in sets.items()}
    if len(set(n.values())) != 1:
        raise fatal(f"prompt sets are not the same size: {n}")
    return {"sets": sets, "per_subject": per_subject,
            "n_items": sum(v["n_items"] for v in per_subject.values())}


def cmd_export_gate(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT3_DIR)
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    export_dir = out_dir / "exports"
    manifest_path = export_dir / "export_manifest_gate.json"
    if manifest_path.exists() and not args.force:
        raise fatal(f"{manifest_path} already exists; pass --force")
    build = build_phase(out_dir, pilot1_dir, arms=(GATE_ARM,), final=False)
    rows = build["sets"][(GATE_ARM, GATE_VARIANT)]
    if not rows:
        raise fatal("no candidate items; run build first")
    ctx = P2.context_check(rows)
    files = {"gate": P2._write_pair(export_dir / "prompts_gate.jsonl",
                                    export_dir / "meta_gate.jsonl",
                                    rows, P2.GATE_META_FIELDS)}
    S.write_json(manifest_path, {
        "pilot": PILOT_BANNER, "phase": "gate", "contract": CONTRACT,
        "scored_claim": SCORED_CLAIM, "exported_utc": now(),
        "arm": GATE_ARM, "variant": GATE_VARIANT,
        "n_candidate_items": build["n_items"],
        "generator": GENERATOR,
        "gate_rule": "B10.7. An item this arm argmax-solves never enters the "
                     "final set. PRE-gate accuracy on this file is the "
                     "instrument-difficulty number; post-gate zero-info "
                     "accuracy is ~0 by construction.",
        "per_subject": build["per_subject"], "context": ctx,
        "renderer": {
            "stage2_render_template_sha256": R.TEMPLATE_SHA256,
            "counterfactuals_template_sha256": CF.TEMPLATE_SHA256,
            "stage2_render_file_sha256": P2.sha256_file(
                _ROOT / "src/doppler/stage2_render.py"),
            "counterfactuals_file_sha256": P2.sha256_file(
                _ROOT / "src/doppler/counterfactuals.py")},
        "files": files})
    print(f"[export-gate] {len(rows)} {GATE_ARM}/{GATE_VARIANT} prompts for "
          f"{build['n_items']} candidate items")
    print(f"[export-gate] manifest -> {rel(manifest_path)}")
    return 0


def cmd_verify(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT3_DIR)
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    checks = {"items": 0, "options": 0, "era": 0, "leak": 0}
    ctx = subject_context(pilot1_dir)
    for rec in load_records(out_dir):
        if not rec["built"]:
            continue
        c = ctx[rec["canonical_id"]]
        texts = [o["text"] for o in rec["options"]]
        if len(set(texts)) != len(texts):
            raise fatal(f"{rec['item_id']}: duplicate option text")
        if rec["options"][rec["correct_index"]]["kind"] != "true":
            raise fatal(f"{rec['item_id']}: correct_index is not the true option")
        for opt in rec["options"]:
            if CF.era_violations(opt["text"], c["test_date"]):
                raise fatal(f"{rec['item_id']}: era violation on disk")
            checks["era"] += 1
            if CF.names_subject(opt["text"], c["variants"]):
                raise fatal(f"{rec['item_id']}: option names the subject")
            if CF.quotes_grounding(opt["text"], [c["grounding_raw"],
                                                 c["grounding_redacted"]]):
                raise fatal(f"{rec['item_id']}: option quotes the grounding")
            checks["leak"] += 1
            checks["options"] += 1
        checks["items"] += 1
    export_dir = out_dir / "exports"
    manifest = export_dir / "export_manifest_gate.json"
    if manifest.exists():
        P2._verify_manifest(export_dir,
                            json.loads(manifest.read_text(encoding="utf-8")),
                            pilot1_dir, {"files": 0, "prompts": 0,
                                         "guard_redacted": 0,
                                         "guard_answer_leak": 0,
                                         "zeroinfo_clean": 0})
    print(f"[verify] {PILOT_BANNER}")
    print(f"[verify] {checks['items']} items, {checks['options']} options: no "
          "era violation, no subject name, no grounding quote")
    if manifest.exists():
        print("[verify] gate export digests and D8 guards re-checked on disk")
    return 0


# ---------------------------------------------------------------------------
# GPU planning
# ---------------------------------------------------------------------------


def projection(gate_rows, pred_rows) -> dict:
    proj = P2.projection(gate_rows, pred_rows)
    proj["jobs"]["stage2_pilot3_gate"] = proj["jobs"].pop("stage2_pilot2_gate")
    proj["jobs"]["stage2_pilot3_pred"] = proj["jobs"].pop("stage2_pilot2_pred")
    proj["abort_above_node_hours"] = PROJECTION_ABORT_NODE_HOURS
    proj["budget_node_hours"] = BUDGET_NODE_HOURS
    return proj


def cmd_plan(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT3_DIR)
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    final = (out_dir / "items_final.jsonl").exists()
    gate = build_phase(out_dir, pilot1_dir, arms=(GATE_ARM,), final=False)
    gate_rows = gate["sets"][(GATE_ARM, GATE_VARIANT)]
    pred = build_phase(out_dir, pilot1_dir, arms=ARMS, final=final)
    pred_rows = [r for v in pred["sets"].values() for r in v]
    ctx = P2.context_check(gate_rows + pred_rows)
    proj = projection(gate_rows, pred_rows)
    print(f"=== Stage 2 pilot 3: projection ===   {PILOT_BANNER}")
    print(f"  candidate items      {gate['n_items']}")
    print(f"  gate prompts         {len(gate_rows)}")
    print(f"  prediction prompts   {pred['n_items']} x {len(ARMS)} arms x "
          f"{len(VARIANTS)} variants = {len(pred_rows)}")
    print(f"  longest prompt       {ctx['longest_prompt_words']} words -> "
          f"{ctx['worst_case_tokens_needed']} tokens "
          f"(headroom {ctx['headroom_tokens']})")
    for name, job in proj["jobs"].items():
        print(f"  {name:22s} {job['projected_node_hours']:7.4f}  "
              f"({job['n_calls']} calls, {job['walltime']})")
    print(f"  {'TOTAL':22s} {proj['total_projected_node_hours']:7.4f}  "
          f"(cap {BUDGET_NODE_HOURS})")
    if proj["total_projected_node_hours"] > PROJECTION_ABORT_NODE_HOURS:
        raise fatal("projection exceeds the cap")
    return 0


def _sbatch(name: str, title: str, files, hours: float, walltime: str,
            qos: str | None) -> str:
    head = P1.HEADER.format(
        job_name=f"dop-s2p3-{name}", account=P2.ACCOUNT,
        qos_line=f"#SBATCH --qos={qos}\n" if qos else "",
        walltime=walltime, node_root=P2.NODE_ROOT, title=title,
        banner=PILOT_BANNER, hours=hours, name=f"stage2_pilot3_{name}",
        out=NODE_RUN)
    listed = " ".join(f'"{f}"' for f in files)
    body = f"""
ARGS=()
for f in {listed}; do
  P="{NODE_RUN}/prompts_$f.jsonl"
  O="{NODE_RUN}/completions_$f.jsonl"
  if [[ -f "$O.summary.json" ]]; then
    echo "[skip] $f already complete"
  else
    ARGS+=(--prompts "$P" --out "$O")
  fi
done
if [[ ${{#ARGS[@]}} -eq 0 ]]; then
  echo "all prompt files complete; nothing to do."
  exit 0
fi
python jobs/batch_generate.py \\
    --model-dir "{P2.MODEL}" --tp {P2.TP} --max-model-len {P2.MAX_MODEL_LEN} \\
    --gpu-mem-util {P2.GPU_MEM_UTIL} --temperature {P2.TEMPERATURE} \\
    "${{ARGS[@]}}"
"""
    return head + body + P1.FOOTER.format(name=f"stage2_pilot3_{name}")


def cmd_bootstrap(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT3_DIR)
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    gate = build_phase(out_dir, pilot1_dir, arms=(GATE_ARM,), final=False)
    gate_rows = gate["sets"][(GATE_ARM, GATE_VARIANT)]
    final = (out_dir / "items_final.jsonl").exists()
    pred = build_phase(out_dir, pilot1_dir, arms=ARMS, final=final)
    pred_rows = [r for v in pred["sets"].values() for r in v]
    proj = projection(gate_rows, pred_rows)
    if proj["total_projected_node_hours"] > PROJECTION_ABORT_NODE_HOURS:
        raise fatal("projection exceeds the cap; no sbatch written")

    summary = json.loads((out_dir / "build_summary.json").read_text(
        encoding="utf-8"))
    S.write_json(out_dir / "config.json", {
        "run": "stage2_pilot3", "pilot": PILOT_BANNER, "confirmatory": False,
        "contract": CONTRACT, "scored_claim": SCORED_CLAIM,
        "model": "Gemma-4-31B-it", "model_label": P2.MODEL_LABEL,
        "temperature": P2.TEMPERATURE, "tp": P2.TP,
        "max_model_len": P2.MAX_MODEL_LEN, "gpu_mem_util": P2.GPU_MEM_UTIL,
        "arms": list(ARMS), "option_variants": list(VARIANTS),
        "grounding_budget_words": P2.GROUNDING_BUDGET_WORDS,
        "instrument": "B10 generated same-question counterfactuals",
        "generator": GENERATOR, "robustness_scorer": ROBUSTNESS_SCORER,
        "generator_separation": summary["generator_separation"],
        "counterfactuals_template_sha256": CF.TEMPLATE_SHA256,
        "n_candidate_items": gate["n_items"],
        "gate_prompts_total": len(gate_rows),
        "prediction_prompts_total": len(pred_rows),
        "projection": proj, "generated_utc": now()})

    man = P2.load_manifest(out_dir / "manifest.json")
    man.setdefault("run", "Stage 2 pilot 3 (Amendment 2 B10)")
    man["contract"] = CONTRACT
    for name, title, files, walltime, qos in (
            ("gate", "PHASE 1: build-time zero-information gate", ["gate"],
             GATE_WALLTIME, GATE_QOS),
            ("pred", "PHASE 2: the 10 prediction sets over gate survivors",
             P2.pred_set_names(), PRED_WALLTIME, None)):
        key = f"stage2_pilot3_{name}"
        hours = proj["jobs"][key]["projected_node_hours"]
        path = out_dir / f"{key}.sbatch"
        path.write_text(_sbatch(name, title, files, hours, walltime, qos),
                        encoding="utf-8")
        entry = man["jobs"].get(key, {})
        entry.update({"kind": name, "walltime": walltime, "qos": qos,
                      "prompt_files": files, "sbatch_local": rel(path),
                      "sbatch_node": f"{P2.NODE_JOBS}/{key}.sbatch",
                      "node_outdir": NODE_RUN,
                      "projected_node_hours": hours,
                      "status": entry.get("status", "bootstrapped"),
                      "slurm_job_ids": entry.get("slurm_job_ids", []),
                      "actual_node_hours": entry.get("actual_node_hours")})
        man["jobs"][key] = entry
        print(f"[bootstrap] {key}: sbatch -> {rel(path)}")
    man["updated_utc"] = now()
    S.write_json(out_dir / "manifest.json", man)
    print(f"[bootstrap] projected {proj['total_projected_node_hours']} "
          f"node-hours (cap {BUDGET_NODE_HOURS})")
    return 0


# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pilot1-dir", default=None)
    ap.add_argument("--out-dir", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_b = sub.add_parser("build")
    p_b.add_argument("--force", action="store_true",
                     help="rebuild items that already have a record")
    p_b.add_argument("--call-cap", type=int, default=DEFAULT_CALL_CAP)
    p_b.add_argument("--skip-cost", action="store_true")
    p_b.set_defaults(fn=cmd_build, client=None)

    sub.add_parser("sheet").set_defaults(fn=cmd_sheet)

    p_g = sub.add_parser("export-gate")
    p_g.add_argument("--force", action="store_true")
    p_g.set_defaults(fn=cmd_export_gate)

    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    sub.add_parser("plan").set_defaults(fn=cmd_plan)
    sub.add_parser("bootstrap").set_defaults(fn=cmd_bootstrap)

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
        args.out_dir = str(PILOT3_DIR)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
