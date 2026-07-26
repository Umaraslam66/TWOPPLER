"""Stage 2 pilot ROUND 2 driver -- same-subject distractors (SPEC v1.8 D6-v2).

PILOT. Pipeline validation only. Nothing here answers a pre-registered bar.

Why there is a round 2. Round 1's forced choice was solved by the
zero-information arm on 17 items out of 17 (pilot report finding 8.0): the three
wrong options were other people's answers to unrelated questions, so picking the
topically coherent option won every item without knowing anything about the
person. The owner's fix (decision D-B) rebuilds the option sets so that **every
distractor is a real answer the SAME subject gave in one of their other
interviews**, adds an anti-leak rule against the twin's own context, records a
question-similarity number for every distractor so an admission floor can be
frozen later, and gates the set on the zero-information arm at BUILD time.

Same six dev subjects, same draw, same splits, same imposter donors, same
renderer. Only the wrong options change.

What is reused, unchanged, by import
------------------------------------
- the draw, splits and turn files, and the test-interview Q-A items
  (results/stage2_pilot/, read-only -- this driver never writes there);
- D8's five-arm renderer and both leakage guards (src/doppler/stage2_render.py);
- round 1's grounding assembly, nickname supplement, redaction plumbing and
  imposter pairing (experiments/stage2_pilot.py, imported as ``P1``).

New here: src/doppler/distractors_v2.py, and the two-phase prompt export.

The two phases
--------------
Phase 1 (gate). One prompt per candidate item: the ``zeroinfo_redacted``
standard-variant prompt, rendered by the frozen D8 renderer. The rule the
orchestrator applies afterwards: an item the zero-information arm argmax-solves
NEVER enters the final set.

Phase 2 (prediction). The ten prompt sets (5 arms x 2 option variants) over the
items that SURVIVED the gate.

Reporting note that must travel with the numbers: gate and scoring use the same
model at temperature 0, so post-gate zero-information accuracy is ~0 BY
CONSTRUCTION. The honest instrument-difficulty number is PRE-GATE zero-info
accuracy on the candidate set, which is why the gate results are kept as their
own artifact and the candidate set is never overwritten.

Subcommands
-----------
``build``        harvest pools, filter, select, write results/stage2_pilot2/.
``export-gate``  phase-1 prompts + a sha256 export manifest.
``ingest-gate``  join gate completions by idx, score, write gate_results.json.
``finalize``     apply the gate rule, write items_final.jsonl.
``export-pred``  phase-2 prompts (final items; falls back to candidates with
                 --pre-gate, for projection and code-path checks only).
``verify``       re-run guards and digests against what is ON DISK.
``plan``         node-hours for both phases. Writes nothing.
``bootstrap``    config.json + both sbatch files + the run manifest.
``record``       write a slurm job id / status / anomaly into the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import stage2_pilot as P1  # noqa: E402

from doppler import distractors_v2 as D2  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402
from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402
from doppler.distractors import RELAX_LADDER  # noqa: E402

RESULTS_DIR = _ROOT / "results"
PILOT1_DIR = RESULTS_DIR / "stage2_pilot"
PILOT2_DIR = RESULTS_DIR / "stage2_pilot2"
COST_LOG = RESULTS_DIR / "cost_log.jsonl"

PILOT_BANNER = ("PILOT -- pipeline validation on dev subjects; "
                "no research conclusions.")
CONTRACT = "SPEC.md v1.8 (D6-v2 same-subject distractors)"

# ---------------------------------------------------------------------------
# Node / job configuration. Same node, same model, same throughput evidence as
# round 1; only the job names, walltimes and prompt counts move.
# ---------------------------------------------------------------------------

NODE_ROOT = P1.NODE_ROOT
NODE_RUN = f"{NODE_ROOT}/runs/stage2_pilot2"
NODE_JOBS = P1.NODE_JOBS
ACCOUNT = P1.ACCOUNT
MODEL = P1.MODEL
MODEL_LABEL = P1.MODEL_LABEL
SPLIT_LABEL = "stage2_pilot2"

TP = P1.TP
TEMPERATURE = P1.TEMPERATURE
GPU_MEM_UTIL = P1.GPU_MEM_UTIL
MAX_MODEL_LEN = P1.MAX_MODEL_LEN
TOKENS_PER_WORD = P1.TOKENS_PER_WORD
TOKENS_PER_WORD_MAX = P1.TOKENS_PER_WORD_MAX
MEASURED_TOKENS_PER_SECOND = P1.MEASURED_TOKENS_PER_SECOND
LONG_PROMPT_DERATE = P1.LONG_PROMPT_DERATE
PREDICTION_MAX_OUTPUT_TOKENS = P1.PREDICTION_MAX_OUTPUT_TOKENS

#: Engine init dominates both of these jobs (round 1 measured 201.6 s of init
#: against 87.8 s of generation for 639 prompts; round 2 has 110). Round 1's
#: 225 s allowance is kept.
ENGINE_INIT_SECONDS = P1.ENGINE_INIT_SECONDS

#: Both phases together must land well under this. The brief's ceiling is 1.5
#: node-hours for the pair; the walltimes below bound the worst case at 0.83.
PROJECTION_ABORT_NODE_HOURS = 1.5
BUDGET_NODE_HOURS = 1.5

GATE_WALLTIME = "00:20:00"
GATE_QOS = "boost_qos_dbg"
PRED_WALLTIME = "00:30:00"

ARMS = P1.ARMS
VARIANTS = P1.VARIANTS
GROUNDING_BUDGET_WORDS = P1.GROUNDING_BUDGET_WORDS

#: The one arm the build-time gate runs, and the option variant it runs it on.
GATE_ARM = "zeroinfo_redacted"
GATE_VARIANT = "standard"

PRED_META_FIELDS = P1.PRED_META_FIELDS
GATE_META_FIELDS = ("item_id", "canonical_id", "arm", "variant",
                    "correct_index", "n_options", "prompt_sha256",
                    "prompt_words")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return P1.sha256_file(path)


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


def rel(path: Path) -> str:
    return P1.rel(path)


# ---------------------------------------------------------------------------
# Upstream: everything round 1 froze, read-only
# ---------------------------------------------------------------------------


def upstream_provenance(pilot1_dir: Path) -> dict:
    """sha256 of every round-1 artifact this run consumes.

    Round 2 reuses round 1's draw, splits, turn files, Q-A items and imposter
    pairing. Recording their digests is what lets a later reader prove the two
    rounds ran on the same subjects and the same test interviews.
    """
    out: dict[str, str] = {}
    for name in ("dev_subjects.json", "imposter_pairs.json"):
        path = pilot1_dir / name
        if path.exists():
            out[name] = sha256_file(path)
    for sub in sorted((pilot1_dir / "subjects").glob("*")):
        for name in ("split.json", "qa_items.jsonl", "grounding_turns.jsonl"):
            path = sub / name
            if path.exists():
                out[f"subjects/{sub.name}/{name}"] = sha256_file(path)
    return out


def test_items(cid: str, pilot1_dir: Path) -> list[dict]:
    """Round 1's D4 items for this subject's test interview, unchanged.

    Only the OPTIONS are rebuilt in round 2; the questions and true answers are
    the same test interview and must stay byte-identical, so they are read from
    round 1's committed artifact rather than re-extracted.
    """
    rows = S.read_jsonl(pilot1_dir / "subjects" / cid / "qa_items.jsonl")
    for row in rows:
        if row["canonical_id"] != cid:
            raise fatal(f"{row['item_id']} claims {row['canonical_id']} in "
                        f"{cid}'s qa_items.jsonl")
    return rows


def excluded_cluster_ids(split: dict) -> list[str]:
    """Clusters the answer pool may not touch: the test cluster, plus every
    cluster D2 already threw out for sharing the test date.

    The same-date exclusions are the ones most likely to BE the test event under
    another transcript id, so an answer harvested from one could be a second
    correct answer wearing a different transcript number.
    """
    out = {split["test"]["cluster_id"]}
    for entry in split.get("excluded_same_date", []):
        if entry.get("cluster_id"):
            out.add(entry["cluster_id"])
    return sorted(out)


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


def harvest_all(pilot1_dir: Path, *, fetch_fn=None, verbose: bool = True) -> dict:
    """Pools, anti-leak split and per-subject bookkeeping for every subject.

    One streaming pass over the corpus for every transcript any subject needs,
    then D4 extraction per transcript. ``fetch_fn(ids) -> {tid: record}`` is
    injected by the tests so this runs without the 4.45 GB file.
    """
    subjects = P1.prediction_subjects(P1.dev_subjects(pilot1_dir))
    pool_rows = P1.pool_rows()

    wanted: set[str] = set()
    plan: dict[str, dict] = {}
    for subject in subjects:
        cid = subject["canonical_id"]
        row = pool_rows[cid]
        split = S.load_split(cid, pilot1_dir)
        blocked = excluded_cluster_ids(split)
        sources = D2.pool_sources(row, blocked)
        wanted.update(t["transcript_id"] for t in sources)
        plan[cid] = {"row": row, "split": split, "blocked": blocked,
                     "sources": sources, "subject": subject}

    fetch_fn = fetch_fn or (lambda ids: S.fetch_records(ids))
    if verbose:
        print(f"[build] fetching {len(wanted)} non-test transcripts")
    records = fetch_fn(sorted(wanted))

    out: dict[str, dict] = {}
    for cid, spec in plan.items():
        row = spec["row"]
        variants = P1.name_variants(row)
        segments, _turns = P1.subject_grounding(cid, pilot1_dir)
        twin_raw = R.render_grounding(segments, GROUNDING_BUDGET_WORDS)
        twin_block = R.redact(twin_raw, variants)
        R.assert_redacted(twin_block, variants)

        per_transcript: list[dict] = []

        def note(tid, substantive, n_items, msg, _acc=per_transcript):
            _acc.append({"transcript_id": tid, "substantive": bool(substantive),
                         "n_items": n_items, "note": msg})

        raw_pool = D2.harvest_answer_pool(row, records, spec["blocked"],
                                          on_transcript=note)
        deduped, dup_dropped = D2.dedupe_pool(raw_pool)
        clean, leaked = D2.anti_leak_split(deduped, twin_raw, twin_block,
                                           variants)
        out[cid] = {
            "canonical_id": cid,
            "canonical_name": row["canonical_name"],
            "wiki_status": spec["subject"].get("wiki_status"),
            "variants": variants,
            "blocked_cluster_ids": spec["blocked"],
            "n_source_transcripts": len(spec["sources"]),
            "n_source_transcripts_substantive": sum(
                1 for t in spec["sources"] if t["substantive"]),
            "per_transcript": per_transcript,
            "pool": clean,
            "pool_raw_size": len(raw_pool),
            "pool_duplicate_dropped": dup_dropped,
            "pool_anti_leak_excluded": leaked,
            "grounding_words_rendered": R.word_count(twin_block),
            "test_items": test_items(cid, pilot1_dir),
        }
        if verbose:
            print(f"[build] {cid} {row['canonical_name']}: "
                  f"pool {len(raw_pool)} raw -> {len(deduped)} deduped -> "
                  f"{len(clean)} usable "
                  f"({len(leaked)} anti-leak, {len(dup_dropped)} duplicate)")
    return out


def build_candidates(harvest: dict, floor: float = 0.0) -> dict:
    """Candidate option sets + the similarity-floor sweep.

    The similarity yardstick is ONE vectorizer fitted on every subject's pool
    questions plus every test question, so the numbers in the sweep table mean
    the same thing in every row (see :class:`distractors_v2.QuestionSimilarity`).
    """
    corpus = [p["question"] for h in harvest.values() for p in h["pool"]]
    corpus += [i["question"] for h in harvest.values() for i in h["test_items"]]
    sim = D2.QuestionSimilarity(corpus)

    sims_by_item: dict[str, list[float]] = {}
    items_by_subject: dict[str, list[dict]] = {}
    pools: dict[str, list[dict]] = {}
    for cid, h in harvest.items():
        pools[cid] = h["pool"]
        items_by_subject[cid] = h["test_items"]
        questions = [p["question"] for p in h["pool"]]
        for item in h["test_items"]:
            sims_by_item[item["item_id"]] = sim.cosines(item["question"],
                                                        questions)

    built: dict[str, list[dict]] = {}
    unfillable: dict[str, list[dict]] = {}
    for cid, h in harvest.items():
        built[cid], unfillable[cid] = [], []
        for item in h["test_items"]:
            res = D2.select_same_subject(item, pools[cid],
                                         sims_by_item[item["item_id"]],
                                         floor=floor)
            (built[cid] if res["built"] else unfillable[cid]).append(res)

    sweep = D2.similarity_floor_sweep(items_by_subject, pools, sims_by_item)
    return {
        "candidates": built,
        "unfillable": unfillable,
        "sweep": sweep,
        "similarity": {
            "corpus_questions": len(sim.corpus),
            "corpus_sha256": sim.corpus_sha256,
            "vocab_size": sim.vocab_size,
            "vectorizer": "TfidfVectorizer(analyzer='word', ngram_range=(1,2), "
                          "lowercase=True) fitted once on all dev pool "
                          "questions + all test questions",
            "build_floor": floor,
        },
    }


def yield_table(harvest: dict, result: dict) -> list[dict]:
    rows = []
    for cid in sorted(harvest):
        h = harvest[cid]
        rows.append({
            "canonical_id": cid,
            "canonical_name": h["canonical_name"],
            "source_transcripts": h["n_source_transcripts"],
            "answer_pool_raw": h["pool_raw_size"],
            "duplicate_dropped": len(h["pool_duplicate_dropped"]),
            "anti_leak_excluded": len(h["pool_anti_leak_excluded"]),
            "answer_pool_usable": len(h["pool"]),
            "test_items": len(h["test_items"]),
            "items_built": len(result["candidates"][cid]),
            "items_unfillable": len(result["unfillable"][cid]),
        })
    return rows


def cmd_build(args) -> int:
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    out_dir = Path(getattr(args, "out_dir", None) or PILOT2_DIR)
    started = time.time()

    harvest = harvest_all(pilot1_dir, fetch_fn=getattr(args, "fetch_fn", None))
    result = build_candidates(harvest, floor=args.floor)

    for cid in sorted(harvest):
        base = out_dir / "subjects" / cid
        base.mkdir(parents=True, exist_ok=True)
        S.write_jsonl(base / "answer_pool.jsonl", harvest[cid]["pool"])
        S.write_jsonl(base / "pool_excluded.jsonl",
                      harvest[cid]["pool_anti_leak_excluded"]
                      + harvest[cid]["pool_duplicate_dropped"])
        S.write_jsonl(base / "candidates.jsonl", result["candidates"][cid])
        S.write_jsonl(base / "unfillable.jsonl", result["unfillable"][cid])

    rows = yield_table(harvest, result)
    summary = {
        "pilot": PILOT_BANNER,
        "contract": CONTRACT,
        "built_utc": now(),
        "runtime_secs": round(time.time() - started, 1),
        "cost_usd": 0.0,
        "rules": {
            "pool": D2.POOL_RULE,
            "anti_leak": D2.ANTI_LEAK_RULE,
            "duplicate": D2.DUP_RULE,
            "controls": "A4: length within +-20% of the true answer, matching "
                        "entity-density bucket, then D6's relaxation ladder "
                        f"(tolerance, adjacent-bucket) = {RELAX_LADDER}; the "
                        "rung used is recorded per item.",
            "no_fallback": "An item that cannot fill 3 distractors from the "
                           "subject's own pool is NOT built. There is no "
                           "cross-person fallback.",
            "gate": "Phase 1 exports the zeroinfo_redacted standard prompt for "
                    "every candidate. An item the zero-information arm "
                    "argmax-solves never enters the final set. PRE-gate "
                    "zero-info accuracy is the instrument-difficulty number; "
                    "post-gate accuracy is ~0 by construction.",
        },
        "per_subject": rows,
        "totals": {
            "subjects": len(rows),
            "answer_pool_usable": sum(r["answer_pool_usable"] for r in rows),
            "test_items": sum(r["test_items"] for r in rows),
            "items_built": sum(r["items_built"] for r in rows),
            "items_unfillable": sum(r["items_unfillable"] for r in rows),
        },
        "similarity": result["similarity"],
        "similarity_floor_sweep": result["sweep"],
        "per_subject_detail": {
            cid: {
                "per_transcript": harvest[cid]["per_transcript"],
                "blocked_cluster_ids": harvest[cid]["blocked_cluster_ids"],
                "grounding_words_rendered": harvest[cid]["grounding_words_rendered"],
            } for cid in sorted(harvest)},
        "upstream_sha256": upstream_provenance(pilot1_dir),
    }
    S.write_json(out_dir / "build_summary.json", summary)

    print(f"\n[build] {PILOT_BANNER}")
    print(f"[build] {'subject':10s} {'pool':>6s} {'dup':>5s} {'leak':>5s} "
          f"{'usable':>7s} {'items':>6s} {'built':>6s} {'unfill':>7s}")
    for r in rows:
        print(f"[build] {r['canonical_id']:10s} {r['answer_pool_raw']:6d} "
              f"{r['duplicate_dropped']:5d} {r['anti_leak_excluded']:5d} "
              f"{r['answer_pool_usable']:7d} {r['test_items']:6d} "
              f"{r['items_built']:6d} {r['items_unfillable']:7d}")
    t = summary["totals"]
    print(f"[build] TOTAL candidate items {t['items_built']} of "
          f"{t['test_items']} ({t['items_unfillable']} unfillable)")
    print(f"[build] summary -> {rel(out_dir / 'build_summary.json')}")
    return 0


# ---------------------------------------------------------------------------
# Item loading + rendering
# ---------------------------------------------------------------------------


def load_candidate_items(cid: str, out_dir: Path, pilot1_dir: Path,
                         final: bool = False) -> list[dict]:
    """Candidate (or final) items joined to their questions and true answers.

    Shaped exactly like round 1's ``load_items`` output, so the frozen renderer
    and its guards take it unchanged.
    """
    if final:
        rows = [r for r in S.read_jsonl(out_dir / "items_final.jsonl")
                if r["canonical_id"] == cid]
    else:
        path = out_dir / "subjects" / cid / "candidates.jsonl"
        rows = S.read_jsonl(path) if path.exists() else []
    qa = {r["item_id"]: r for r in test_items(cid, pilot1_dir)}
    items = []
    for row in rows:
        base = qa.get(row["item_id"])
        if base is None:
            raise fatal(f"{row['item_id']} has no round-1 qa_items row")
        texts = [o["text"] for o in row["options"]]
        stripped = list(row["options_stripped"])
        if len(texts) != len(stripped):
            raise fatal(f"{row['item_id']}: option/stripped length mismatch")
        correct = int(row["correct_index"])
        if row["options"][correct]["kind"] != "true":
            raise fatal(f"{row['item_id']}: correct_index does not point at "
                        "the true option")
        if texts[correct] != base["answer"]:
            raise fatal(f"{row['item_id']}: the true option is not the round-1 "
                        "answer text")
        items.append({
            "item_id": row["item_id"],
            "canonical_id": cid,
            "transcript_id": base["transcript_id"],
            "q_turn_idx": base["q_turn_idx"],
            "question": base["question"],
            "answer": base["answer"],
            "answer_words": base["answer_words"],
            "options": {"standard": texts, "stripped": stripped},
            "correct_index": correct,
            "relax_rung": row.get("relax_rung"),
            "flags": row.get("flags", []),
        })
    return items


def build_phase(out_dir: Path, pilot1_dir: Path, *, arms, final: bool) -> dict:
    """Render every (arm, variant) prompt for the chosen item set, with guards."""
    subjects = P1.prediction_subjects(P1.dev_subjects(pilot1_dir))
    dev_ids = {s["canonical_id"] for s in P1.dev_subjects(pilot1_dir)}
    pool = P1.pool_rows()
    pairs = P1.imposter_pairs(pilot1_dir / "imposter_pairs.json")
    need_grounding = any(a in R.GROUNDED_ARMS for a in arms)

    sets: dict[tuple[str, str], list[dict]] = {
        (arm, variant): [] for arm in arms for variant in VARIANTS}
    per_subject: dict[str, dict] = {}

    for subject in subjects:
        cid = subject["canonical_id"]
        if subject.get("burned_for_qa"):
            raise fatal(f"{cid} is burned_for_qa and must not reach a "
                        "prediction arm")
        items = load_candidate_items(cid, out_dir, pilot1_dir, final=final)
        if not items:
            per_subject[cid] = {"canonical_id": cid, "n_items": 0,
                                "item_ids": [], "donor_id": pairs.get(cid)}
            continue
        row = pool[cid]
        variants = P1.name_variants(row)
        name = row["canonical_name"]

        twin_block = donor_block = None
        donor_variants = None
        donor_id = pairs.get(cid)
        if need_grounding:
            segments, _ = P1.subject_grounding(cid, pilot1_dir)
            twin_block = R.redact(
                R.render_grounding(segments, GROUNDING_BUDGET_WORDS), variants)
            R.assert_redacted(twin_block, variants)
            if donor_id is None:
                raise fatal(f"{cid} has no imposter donor")
            if donor_id in dev_ids:
                raise fatal(f"donor {donor_id} for {cid} is a dev subject")
            donor_variants = P1.name_variants(pool[donor_id])
            dsegs, _ = P1.donor_grounding(donor_id, pilot1_dir)
            donor_block = R.redact(
                R.render_grounding(dsegs, GROUNDING_BUDGET_WORDS),
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
                        subject_name=name, subject_variants=variants,
                        grounding_block=block, donor_variants=donor_check)
                    built.update({
                        "item_id": item["item_id"], "canonical_id": cid,
                        "arm": arm, "variant": variant,
                        "correct_index": item["correct_index"],
                        "n_options": len(item["options"][variant]),
                        "donor_id": donor_id if arm == "imposter_redacted"
                        else None,
                    })
                    sets[(arm, variant)].append(built)
        per_subject[cid] = {
            "canonical_id": cid, "canonical_name": name,
            "n_items": len(items),
            "item_ids": [i["item_id"] for i in items],
            "donor_id": donor_id,
            "relax_rungs": [i["relax_rung"] for i in items],
        }

    n = {k: len(v) for k, v in sets.items()}
    if len(set(n.values())) != 1:
        raise fatal(f"prompt sets are not the same size: {n}")
    return {"sets": sets, "per_subject": per_subject,
            "n_items": sum(v["n_items"] for v in per_subject.values())}


def context_check(rows: list[dict]) -> dict:
    worst = max(rows, key=lambda r: r["prompt_words"])
    need = int(round(worst["prompt_words"] * TOKENS_PER_WORD_MAX)) \
        + worst["max_output_tokens"]
    if need > MAX_MODEL_LEN:
        raise fatal(f"longest prompt is {worst['prompt_words']} words -> up to "
                    f"{need} tokens, which does not fit "
                    f"MAX_MODEL_LEN={MAX_MODEL_LEN}")
    return {"longest_prompt_words": worst["prompt_words"],
            "longest_prompt_item": worst.get("item_id"),
            "longest_prompt_arm": worst.get("arm"),
            "worst_case_tokens_needed": need,
            "max_model_len": MAX_MODEL_LEN,
            "headroom_tokens": MAX_MODEL_LEN - need}


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def _block(rows: list[dict]) -> dict:
    eff = MEASURED_TOKENS_PER_SECOND / LONG_PROMPT_DERATE
    tin = sum(r["prompt_tokens_est"] for r in rows)
    tout = sum(r["max_output_tokens"] for r in rows)
    return {"n_calls": len(rows), "tokens_in_est": tin, "tokens_out_cap": tout,
            "seconds": (tin + tout) / eff}


def projection(gate_rows: list[dict], pred_rows: list[dict]) -> dict:
    gate, pred = _block(gate_rows), _block(pred_rows)
    jobs = {
        "stage2_pilot2_gate": {
            "n_calls": gate["n_calls"],
            "generation_seconds": round(gate["seconds"], 1),
            "engine_init_seconds": ENGINE_INIT_SECONDS,
            "projected_node_hours": round(
                (gate["seconds"] + ENGINE_INIT_SECONDS) / 3600, 4),
            "walltime": GATE_WALLTIME, "qos": GATE_QOS,
        },
        "stage2_pilot2_pred": {
            "n_calls": pred["n_calls"],
            "generation_seconds": round(pred["seconds"], 1),
            "engine_init_seconds": ENGINE_INIT_SECONDS,
            "projected_node_hours": round(
                (pred["seconds"] + ENGINE_INIT_SECONDS) / 3600, 4),
            "walltime": PRED_WALLTIME, "qos": "boost_usr_prod (normal)",
        },
    }
    total = round(sum(j["projected_node_hours"] for j in jobs.values()), 4)
    bound = round(P1._walltime_hours(GATE_WALLTIME)
                  + P1._walltime_hours(PRED_WALLTIME), 4)
    return {
        "gate": gate, "prediction": pred, "jobs": jobs,
        "effective_tokens_per_second": round(
            MEASURED_TOKENS_PER_SECOND / LONG_PROMPT_DERATE, 1),
        "measured_tokens_per_second": MEASURED_TOKENS_PER_SECOND,
        "long_prompt_derate": LONG_PROMPT_DERATE,
        "tokens_per_word": TOKENS_PER_WORD,
        "total_projected_node_hours": total,
        "walltime_bounded_worst_case_node_hours": bound,
        "abort_above_node_hours": PROJECTION_ABORT_NODE_HOURS,
        "budget_node_hours": BUDGET_NODE_HOURS,
        "note": "Both jobs are dominated by engine init: 110 prompts against "
                "round 1's 639, on the same node and the same model. Output "
                "tokens are counted at the 512-token cap, so the generation "
                "term is an upper bound.",
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def set_name(arm: str, variant: str) -> str:
    return f"pred_{arm}_{variant}"


def _write_pair(prompts_path: Path, meta_path: Path, rows: list[dict],
                meta_fields) -> dict:
    prompts_path.parent.mkdir(parents=True, exist_ok=True)
    return P1._write_pair(prompts_path, meta_path, rows, tuple(meta_fields))


def cmd_export_gate(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT2_DIR)
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    export_dir = out_dir / "exports"
    manifest_path = export_dir / "export_manifest_gate.json"
    if manifest_path.exists() and not args.force:
        raise fatal(f"{manifest_path} already exists; pass --force to rebuild")

    build = build_phase(out_dir, pilot1_dir, arms=(GATE_ARM,), final=False)
    rows = build["sets"][(GATE_ARM, GATE_VARIANT)]
    if not rows:
        raise fatal("no candidate items; run build first")
    ctx = context_check(rows)

    files = {"gate": _write_pair(export_dir / "prompts_gate.jsonl",
                                 export_dir / "meta_gate.jsonl",
                                 rows, GATE_META_FIELDS)}
    doc = {
        "pilot": PILOT_BANNER, "phase": "gate", "contract": CONTRACT,
        "exported_utc": now(),
        "arm": GATE_ARM, "variant": GATE_VARIANT,
        "n_candidate_items": build["n_items"],
        "gate_rule": "An item this arm argmax-solves NEVER enters the final "
                     "set. Rejection counts are logged. PRE-gate accuracy on "
                     "this file is the instrument-difficulty number; post-gate "
                     "zero-info accuracy is ~0 by construction (same model, "
                     "temperature 0).",
        "per_subject": build["per_subject"],
        "context": ctx,
        "renderer": {
            "stage2_render_template_sha256": R.TEMPLATE_SHA256,
            "stage2_render_file_sha256": sha256_file(
                _ROOT / "src/doppler/stage2_render.py"),
            "distractors_v2_file_sha256": sha256_file(
                _ROOT / "src/doppler/distractors_v2.py"),
        },
        "files": files,
    }
    S.write_json(manifest_path, doc)
    print(f"[export-gate] {PILOT_BANNER}")
    print(f"[export-gate] {len(rows)} {GATE_ARM}/{GATE_VARIANT} prompts "
          f"for {build['n_items']} candidate items")
    print(f"[export-gate] manifest -> {rel(manifest_path)}")
    return 0


def cmd_export_pred(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT2_DIR)
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    export_dir = out_dir / "exports"
    manifest_path = export_dir / "export_manifest_pred.json"
    final = not args.pre_gate
    if final and not (out_dir / "items_final.jsonl").exists():
        raise fatal("items_final.jsonl not found; run ingest-gate + finalize "
                    "first, or pass --pre-gate for a projection-only export")
    if manifest_path.exists() and not args.force:
        raise fatal(f"{manifest_path} already exists; pass --force to rebuild")

    build = build_phase(out_dir, pilot1_dir, arms=ARMS, final=final)
    rows = [r for v in build["sets"].values() for r in v]
    if not rows:
        raise fatal("no items to export")
    ctx = context_check(rows)

    files = {}
    for arm in ARMS:
        for variant in VARIANTS:
            name = set_name(arm, variant)
            files[name] = _write_pair(export_dir / f"prompts_{name}.jsonl",
                                      export_dir / f"meta_{name}.jsonl",
                                      build["sets"][(arm, variant)],
                                      PRED_META_FIELDS)
            print(f"[export-pred] {name}: "
                  f"{files[name]['n_prompts']} prompts")
    doc = {
        "pilot": PILOT_BANNER, "phase": "prediction", "contract": CONTRACT,
        "exported_utc": now(),
        "item_source": "items_final.jsonl" if final
                       else "candidates.jsonl (PRE-GATE, projection only)",
        "n_items": build["n_items"],
        "arms": list(ARMS), "option_variants": list(VARIANTS),
        "per_subject": build["per_subject"],
        "context": ctx,
        "renderer": {
            "stage2_render_template_sha256": R.TEMPLATE_SHA256,
            "stage2_render_file_sha256": sha256_file(
                _ROOT / "src/doppler/stage2_render.py"),
            "distractors_v2_file_sha256": sha256_file(
                _ROOT / "src/doppler/distractors_v2.py"),
        },
        "files": files,
    }
    S.write_json(manifest_path, doc)
    print(f"[export-pred] manifest -> {rel(manifest_path)}")
    return 0


# ---------------------------------------------------------------------------
# Gate ingest + finalize
# ---------------------------------------------------------------------------


def score_gate(meta: dict, completion: str | None) -> dict:
    """One gate completion -> argmax + probability mass on the true option."""
    n = int(meta.get("n_options") or 4)
    dist = R.parse_distribution(completion, n) if completion else None
    correct = int(meta["correct_index"])
    if dist is None:
        return {"item_id": meta["item_id"], "canonical_id": meta["canonical_id"],
                "parsed": False, "argmax_correct": None, "p_correct": None}
    argmax = max(range(n), key=lambda i: (dist[i], -i))
    return {"item_id": meta["item_id"], "canonical_id": meta["canonical_id"],
            "parsed": True, "argmax_correct": bool(argmax == correct),
            "p_correct": float(dist[correct]), "argmax_index": argmax,
            "distribution": [float(p) for p in dist]}


def cmd_ingest_gate(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT2_DIR)
    export_dir = out_dir / "exports"
    nodedir = Path(args.nodedir)
    metas = S.read_jsonl(export_dir / "meta_gate.jsonl")
    prompts = S.read_jsonl(export_dir / "prompts_gate.jsonl")
    completions = S.read_jsonl(nodedir / "completions_gate.jsonl")
    by_idx = {int(r["idx"]): r for r in completions}
    if len(by_idx) != len(completions):
        raise fatal("duplicate idx in completions_gate.jsonl")

    records = []
    for meta in metas:
        row = by_idx.get(int(meta["idx"]))
        records.append(score_gate(meta, (row or {}).get("completion")))
    parsed = [r for r in records if r["parsed"]]
    solved = [r for r in parsed if r["argmax_correct"]]

    summary_path = nodedir / "completions_gate.jsonl.summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) \
        if summary_path.exists() else {}
    node_hours = P1._node_hours(summary)

    doc = {
        "pilot": PILOT_BANNER, "phase": "gate", "ingested_utc": now(),
        "arm": GATE_ARM, "variant": GATE_VARIANT,
        "n_candidates": len(records),
        "n_parsed": len(parsed),
        "n_parse_failures": len(records) - len(parsed),
        "pre_gate_zeroinfo_argmax_accuracy":
            round(len(solved) / len(parsed), 4) if parsed else None,
        "pre_gate_note": "This is the instrument-difficulty number. Post-gate "
                         "zero-info accuracy is ~0 by construction.",
        "n_rejected": len(solved),
        "rejected_item_ids": sorted(r["item_id"] for r in solved),
        "records": records,
        "node_hours": node_hours,
        "n_prompts": len(prompts),
    }
    S.write_json(out_dir / "gate_results.json", doc)

    if not args.skip_cost:
        tokens_in = sum(int(round(m["prompt_words"] * TOKENS_PER_WORD))
                        for m in metas)
        append_cost_log(build_cost_entry(
            run_id="stage2_pilot2_gate", model=MODEL_LABEL, split=SPLIT_LABEL,
            n_persons=len({m["canonical_id"] for m in metas}),
            n_calls=len(records), n_retries=0,
            n_parse_failures=len(records) - len(parsed),
            tokens_in=tokens_in,
            tokens_out=len(records) * PREDICTION_MAX_OUTPUT_TOKENS,
            variant="v2", backend="leonardo-batch",
            node_hours=node_hours), COST_LOG)

    print(f"[ingest-gate] {len(records)} candidates, {len(parsed)} parsed")
    print(f"[ingest-gate] PRE-gate zero-info argmax accuracy "
          f"{doc['pre_gate_zeroinfo_argmax_accuracy']}")
    print(f"[ingest-gate] {len(solved)} items rejected by the gate")
    return 0


def cmd_finalize(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT2_DIR)
    gate = json.loads((out_dir / "gate_results.json").read_text(encoding="utf-8"))
    rejected = set(gate["rejected_item_ids"])
    unparsed = {r["item_id"] for r in gate["records"] if not r["parsed"]}

    kept, dropped = [], []
    per_subject: dict[str, dict] = {}
    for sub in sorted((out_dir / "subjects").glob("*")):
        cid = sub.name
        rows = S.read_jsonl(sub / "candidates.jsonl")
        k = [r for r in rows if r["item_id"] not in rejected
             and r["item_id"] not in unparsed]
        d = [r["item_id"] for r in rows if r["item_id"] in rejected]
        u = [r["item_id"] for r in rows if r["item_id"] in unparsed]
        kept += k
        dropped += d
        per_subject[cid] = {"candidates": len(rows), "kept": len(k),
                            "gate_rejected": len(d), "parse_failed": len(u)}
    S.write_jsonl(out_dir / "items_final.jsonl", kept)
    S.write_json(out_dir / "finalize_summary.json", {
        "pilot": PILOT_BANNER, "finalized_utc": now(),
        "rule": "An item the zero-information arm argmax-solved at build time "
                "never enters the final set. An item whose gate reply did not "
                "parse is also held out (the gate could not clear it).",
        "n_candidates": sum(v["candidates"] for v in per_subject.values()),
        "n_final": len(kept),
        "n_gate_rejected": len(dropped),
        "per_subject": per_subject,
        "pre_gate_zeroinfo_argmax_accuracy":
            gate["pre_gate_zeroinfo_argmax_accuracy"],
    })
    print(f"[finalize] {len(kept)} items survive the gate "
          f"({len(dropped)} rejected)")
    return 0


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


def _verify_manifest(export_dir: Path, doc: dict, pilot1_dir: Path,
                     checks: dict) -> None:
    pool = P1.pool_rows()
    subjects = P1.dev_subjects(pilot1_dir)
    dev_ids = {s["canonical_id"] for s in subjects}
    burned = {s["canonical_id"] for s in subjects if s.get("burned_for_qa")}
    variants_of = {cid: P1.name_variants(pool[cid]) for cid in dev_ids}
    donor_variants_of = {
        cid: P1.name_variants(pool[d])
        for cid, d in P1.imposter_pairs(pilot1_dir / "imposter_pairs.json").items()}
    answers = {i["item_id"]: i for cid in dev_ids
               for i in test_items(cid, pilot1_dir)}

    for name, info in doc["files"].items():
        for key, fname in (("prompts_sha256", info.get("prompts_file")),
                           ("meta_sha256", info.get("meta_file"))):
            if not fname:
                continue
            got = sha256_file(export_dir / fname)
            if got != info[key]:
                raise fatal(f"{fname} sha256 {got} != manifest {info[key]}")
            checks["files"] += 1

        prompts = S.read_jsonl(export_dir / info["prompts_file"])
        metas = S.read_jsonl(export_dir / info["meta_file"])
        joined = P1.join_by_idx(prompts, metas)
        for row in joined:
            cid = row["canonical_id"]
            if cid not in dev_ids:
                raise fatal(f"{name} idx {row['idx']}: {cid} is not a dev "
                            "subject")
            if cid in burned:
                raise fatal(f"{name} idx {row['idx']}: {cid} is burned_for_qa")
            if R.sha256(row["prompt"]) != row["prompt_sha256"]:
                raise fatal(f"{name} idx {row['idx']}: prompt digest moved")
            arm = row["arm"]
            guarded = row["prompt"]
            if arm in R.NAMED_ARMS:
                marker = P1._name_line(arm, pool[cid]["canonical_name"]) + "\n\n"
                if marker not in guarded:
                    raise fatal(f"{name} idx {row['idx']}: no name line")
                guarded = guarded.replace(marker, "", 1)
            R.assert_redacted(guarded, variants_of[cid])
            checks["guard_redacted"] += 1
            if arm == "imposter_redacted":
                R.assert_redacted(row["prompt"], donor_variants_of[cid])
                checks["guard_redacted"] += 1
            if arm in R.GROUNDED_ARMS:
                R.assert_no_answer_leak(P1.excerpt_block(row["prompt"]),
                                        answers[row["item_id"]]["answer"])
                checks["guard_answer_leak"] += 1
            else:
                if R.EXCERPTS_HEADER in row["prompt"] \
                        or "[Interview," in row["prompt"]:
                    raise fatal(f"{name} idx {row['idx']}: zero-information "
                                "prompt carries excerpts")
                checks["zeroinfo_clean"] += 1
            checks["prompts"] += 1


def verify_same_subject(out_dir: Path, checks: dict) -> None:
    """Every option of every candidate came from the subject, not the test."""
    for sub in sorted((out_dir / "subjects").glob("*")):
        cid = sub.name
        for row in S.read_jsonl(sub / "candidates.jsonl"):
            tids = set()
            for opt in row["options"]:
                if opt["source_canonical_id"] != cid:
                    raise fatal(f"{row['item_id']}: option from "
                                f"{opt['source_canonical_id']}")
                tids.add((opt["source_transcript_id"], opt["source_q_turn_idx"]))
            if len(tids) != len(row["options"]):
                raise fatal(f"{row['item_id']}: an option is used twice")
            true_tid = row["options"][row["correct_index"]]["source_transcript_id"]
            for opt in row["options"]:
                if opt["kind"] == "distractor" \
                        and opt["source_transcript_id"] == true_tid:
                    raise fatal(f"{row['item_id']}: distractor from the test "
                                "transcript")
            checks["same_subject_items"] += 1


def verify_anti_leak(out_dir: Path, pilot1_dir: Path, checks: dict) -> None:
    """No distractor may be quotable from the subject's rendered grounding."""
    pool = P1.pool_rows()
    for sub in sorted((out_dir / "subjects").glob("*")):
        cid = sub.name
        rows = S.read_jsonl(sub / "candidates.jsonl")
        if not rows:
            continue
        variants = P1.name_variants(pool[cid])
        segments, _ = P1.subject_grounding(cid, pilot1_dir)
        raw = R.render_grounding(segments, GROUNDING_BUDGET_WORDS)
        block = R.redact(raw, variants)
        for row in rows:
            for opt in row["options"]:
                if opt["kind"] != "distractor":
                    continue
                if D2.leak_against(opt["text"], [raw]) or \
                        D2.leak_against(R.redact(opt["text"], variants), [block]):
                    raise fatal(f"{row['item_id']}: a distractor is quotable "
                                "from the rendered grounding")
                checks["anti_leak_options"] += 1


def cmd_verify(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT2_DIR)
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    export_dir = out_dir / "exports"
    checks = {"files": 0, "prompts": 0, "guard_redacted": 0,
              "guard_answer_leak": 0, "zeroinfo_clean": 0,
              "same_subject_items": 0, "anti_leak_options": 0, "manifests": 0}

    verify_same_subject(out_dir, checks)
    verify_anti_leak(out_dir, pilot1_dir, checks)

    for name in ("export_manifest_gate.json", "export_manifest_pred.json"):
        path = export_dir / name
        if not path.exists():
            continue
        _verify_manifest(export_dir,
                         json.loads(path.read_text(encoding="utf-8")),
                         pilot1_dir, checks)
        checks["manifests"] += 1
    if checks["manifests"] == 0:
        raise fatal(f"no export manifest under {export_dir}; run export-gate "
                    "first")

    print(f"[verify] {PILOT_BANNER}")
    print(f"[verify] {checks['same_subject_items']} candidate items: every "
          "option is the subject's own answer, none from the test interview")
    print(f"[verify] {checks['anti_leak_options']} distractors are not quotable "
          "from the rendered grounding")
    print(f"[verify] {checks['manifests']} export manifests, "
          f"{checks['files']} file digests, {checks['prompts']} prompts")
    print(f"[verify] {checks['guard_redacted']} redaction assertions, "
          f"{checks['guard_answer_leak']} answer-leak, "
          f"{checks['zeroinfo_clean']} zero-information cleanliness")
    return 0


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


def cmd_plan(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT2_DIR)
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    final = (out_dir / "items_final.jsonl").exists()

    gate_build = build_phase(out_dir, pilot1_dir, arms=(GATE_ARM,), final=False)
    gate_rows = gate_build["sets"][(GATE_ARM, GATE_VARIANT)]
    pred_build = build_phase(out_dir, pilot1_dir, arms=ARMS, final=final)
    pred_rows = [r for v in pred_build["sets"].values() for r in v]
    ctx = context_check(gate_rows + pred_rows)
    proj = projection(gate_rows, pred_rows)

    print(f"=== Stage 2 pilot ROUND 2: projection ===   {PILOT_BANNER}")
    print(f"  candidate items        {gate_build['n_items']}")
    print(f"  phase-2 item source    "
          f"{'items_final.jsonl' if final else 'candidates (PRE-GATE)'}")
    print(f"  gate prompts           {len(gate_rows)} "
          f"({GATE_ARM}/{GATE_VARIANT})")
    print(f"  prediction prompts     {pred_build['n_items']} items x "
          f"{len(ARMS)} arms x {len(VARIANTS)} variants = {len(pred_rows)}")
    print(f"  longest prompt         {ctx['longest_prompt_words']} words -> "
          f"{ctx['worst_case_tokens_needed']} tokens "
          f"(headroom {ctx['headroom_tokens']})")
    print("  --- node-hours ---")
    for name, job in proj["jobs"].items():
        print(f"  {name:22s} {job['projected_node_hours']:7.4f}  "
              f"({job['n_calls']:,} calls, {job['walltime']} walltime)")
    print(f"  {'TOTAL':22s} {proj['total_projected_node_hours']:7.4f}  "
          f"(abort above {PROJECTION_ABORT_NODE_HOURS})")
    print(f"  walltime-bounded worst case "
          f"{proj['walltime_bounded_worst_case_node_hours']} node-hours")
    if proj["total_projected_node_hours"] > PROJECTION_ABORT_NODE_HOURS:
        raise fatal("projection exceeds the abort threshold")
    return 0


# ---------------------------------------------------------------------------
# sbatch + manifest
# ---------------------------------------------------------------------------


def _pairs_loop(names: list[str]) -> str:
    listed = " ".join(f'"{n}"' for n in names)
    return f"""
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
    --model-dir "{MODEL}" --tp {TP} --max-model-len {MAX_MODEL_LEN} \\
    --gpu-mem-util {GPU_MEM_UTIL} --temperature {TEMPERATURE} \\
    "${{ARGS[@]}}"
"""


def pred_set_names() -> list[str]:
    return [set_name(a, v) for a in ARMS for v in VARIANTS]


def gate_sbatch(hours: float) -> str:
    head = P1.HEADER.format(
        job_name="dop-s2p2-gate", account=ACCOUNT,
        qos_line=f"#SBATCH --qos={GATE_QOS}\n",
        walltime=GATE_WALLTIME, node_root=NODE_ROOT,
        title="PHASE 1: build-time zero-information gate over candidate items",
        banner=PILOT_BANNER, hours=hours, name="stage2_pilot2_gate",
        out=NODE_RUN)
    return head + _pairs_loop(["gate"]) + P1.FOOTER.format(
        name="stage2_pilot2_gate")


def pred_sbatch(hours: float) -> str:
    head = P1.HEADER.format(
        job_name="dop-s2p2-pred", account=ACCOUNT, qos_line="",
        walltime=PRED_WALLTIME, node_root=NODE_ROOT,
        title="PHASE 2: the 10 prediction sets over gate-surviving items",
        banner=PILOT_BANNER, hours=hours, name="stage2_pilot2_pred",
        out=NODE_RUN)
    return head + _pairs_loop(pred_set_names()) + P1.FOOTER.format(
        name="stage2_pilot2_pred")


def load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"created_utc": now(), "run": "Stage 2 pilot round 2 (SPEC v1.8)",
            "confirmatory": False, "pilot": PILOT_BANNER, "contract": CONTRACT,
            "jobs": {}, "anomalies": [], "notes": []}


def cmd_bootstrap(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT2_DIR)
    pilot1_dir = Path(getattr(args, "pilot1_dir", None) or PILOT1_DIR)
    gate_build = build_phase(out_dir, pilot1_dir, arms=(GATE_ARM,), final=False)
    gate_rows = gate_build["sets"][(GATE_ARM, GATE_VARIANT)]
    final = (out_dir / "items_final.jsonl").exists()
    pred_build = build_phase(out_dir, pilot1_dir, arms=ARMS, final=final)
    pred_rows = [r for v in pred_build["sets"].values() for r in v]
    proj = projection(gate_rows, pred_rows)
    if proj["total_projected_node_hours"] > PROJECTION_ABORT_NODE_HOURS:
        raise fatal("projection exceeds the abort threshold; no sbatch written")

    summary = json.loads(
        (out_dir / "build_summary.json").read_text(encoding="utf-8"))
    S.write_json(out_dir / "config.json", {
        "run": SPLIT_LABEL, "pilot": PILOT_BANNER, "confirmatory": False,
        "contract": CONTRACT,
        "model": "Gemma-4-31B-it", "model_label": MODEL_LABEL,
        "temperature": TEMPERATURE, "tp": TP, "max_model_len": MAX_MODEL_LEN,
        "gpu_mem_util": GPU_MEM_UTIL,
        "arms": list(ARMS), "option_variants": list(VARIANTS),
        "grounding_budget_words": GROUNDING_BUDGET_WORDS,
        "distractor_rule": "SPEC v1.8 D6-v2: every distractor is an answer the "
                           "SAME subject gave in another interview.",
        "similarity_floor_applied_at_build": summary["similarity"]["build_floor"],
        "similarity_floor_note": "Recorded per distractor; the admission "
                                 "threshold is frozen by the owner at bar-lock.",
        "n_candidate_items": gate_build["n_items"],
        "n_final_items": pred_build["n_items"] if final else None,
        "gate_prompts_total": len(gate_rows),
        "prediction_prompts_total": len(pred_rows),
        "phases": {"gate": "zeroinfo_redacted standard over every candidate; "
                           "argmax-solved items never enter the final set",
                   "prediction": "5 arms x 2 option variants over survivors"},
        "renderer": {
            "stage2_render_template_sha256": R.TEMPLATE_SHA256,
            "stage2_render_file_sha256": sha256_file(
                _ROOT / "src/doppler/stage2_render.py"),
            "distractors_v2_file_sha256": sha256_file(
                _ROOT / "src/doppler/distractors_v2.py"),
        },
        "projection": proj,
        "generated_utc": now(),
    })

    man = load_manifest(out_dir / "manifest.json")
    for name, text, files in (
            ("stage2_pilot2_gate",
             gate_sbatch(proj["jobs"]["stage2_pilot2_gate"]["projected_node_hours"]),
             ["gate"]),
            ("stage2_pilot2_pred",
             pred_sbatch(proj["jobs"]["stage2_pilot2_pred"]["projected_node_hours"]),
             pred_set_names())):
        path = out_dir / f"{name}.sbatch"
        path.write_text(text, encoding="utf-8")
        entry = man["jobs"].get(name, {})
        entry.update({
            "kind": "gate" if name.endswith("gate") else "prediction",
            "walltime": GATE_WALLTIME if name.endswith("gate") else PRED_WALLTIME,
            "qos": GATE_QOS if name.endswith("gate") else None,
            "prompt_files": files,
            "sbatch_local": rel(path),
            "sbatch_node": f"{NODE_JOBS}/{name}.sbatch",
            "node_outdir": NODE_RUN,
            "projected_node_hours": proj["jobs"][name]["projected_node_hours"],
            "status": entry.get("status", "bootstrapped"),
            "slurm_job_ids": entry.get("slurm_job_ids", []),
            "actual_node_hours": entry.get("actual_node_hours"),
        })
        man["jobs"][name] = entry
        print(f"[bootstrap] {name}: sbatch -> {rel(path)}")
    man["updated_utc"] = now()
    S.write_json(out_dir / "manifest.json", man)
    print(f"[bootstrap] config -> {rel(out_dir / 'config.json')}")
    print(f"[bootstrap] projected {proj['total_projected_node_hours']} "
          f"node-hours across both phases")
    return 0


def cmd_record(args) -> int:
    out_dir = Path(getattr(args, "out_dir", None) or PILOT2_DIR)
    path = out_dir / "manifest.json"
    man = load_manifest(path)
    if args.anomaly:
        man["anomalies"].append({"utc": now(), "job": args.name,
                                 "note": args.anomaly})
    entry = man["jobs"].setdefault(args.name, {})
    if args.job_id:
        entry.setdefault("slurm_job_ids", []).append(args.job_id)
    if args.status:
        entry["status"] = args.status
    if args.node_hours is not None:
        entry["actual_node_hours"] = float(args.node_hours)
    if args.note:
        entry.setdefault("notes", []).append({"utc": now(), "note": args.note})
    man["updated_utc"] = now()
    S.write_json(path, man)
    print(f"[record] {args.name}: {entry.get('status')} "
          f"jobs={entry.get('slurm_job_ids')}")
    return 0


# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pilot1-dir", default=None,
                    help="override results/stage2_pilot (tests only)")
    ap.add_argument("--out-dir", default=None,
                    help="override results/stage2_pilot2 (tests only)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build")
    p_build.add_argument("--floor", type=float, default=0.0,
                         help="similarity admission floor; the frozen build "
                              "runs at 0.0 and records every similarity")
    p_build.set_defaults(fn=cmd_build)

    p_gate = sub.add_parser("export-gate")
    p_gate.add_argument("--force", action="store_true")
    p_gate.set_defaults(fn=cmd_export_gate)

    p_pred = sub.add_parser("export-pred")
    p_pred.add_argument("--force", action="store_true")
    p_pred.add_argument("--pre-gate", action="store_true",
                        help="export from the CANDIDATE set (projection / "
                             "code-path check only; never for scoring)")
    p_pred.set_defaults(fn=cmd_export_pred)

    p_ing = sub.add_parser("ingest-gate")
    p_ing.add_argument("--nodedir", required=True)
    p_ing.add_argument("--skip-cost", action="store_true")
    p_ing.set_defaults(fn=cmd_ingest_gate)

    sub.add_parser("finalize").set_defaults(fn=cmd_finalize)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    sub.add_parser("plan").set_defaults(fn=cmd_plan)
    sub.add_parser("bootstrap").set_defaults(fn=cmd_bootstrap)

    p_rec = sub.add_parser("record")
    p_rec.add_argument("--name", required=True)
    p_rec.add_argument("--job-id", default=None)
    p_rec.add_argument("--status", default=None)
    p_rec.add_argument("--node-hours", type=float, default=None)
    p_rec.add_argument("--note", default=None)
    p_rec.add_argument("--anomaly", default=None)
    p_rec.set_defaults(fn=cmd_record)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
