"""Stage 2 pilot driver -- end to end on the six dev subjects (SPEC D10).

PILOT. Pipeline validation only. Nothing here answers a pre-registered bar and
nothing here is confirmatory; every artifact and table it writes is labelled
"PILOT -- pipeline validation on dev subjects; no research conclusions."

What it does, in one paragraph. It reads the five frozen upstream artifacts
(T1's dev subjects / splits / turns, T2's Q-A items and distractor option sets,
T3's imposter donors, T4's five-arm prompt renderer, T5's follow-up classifier),
renders every prompt the pilot needs, proves the leakage guards on each one,
exports them as BatchFileBackend prompt files with sha256s, runs them in one
Leonardo job, joins the completions back, and writes results/stage2_pilot/
PILOT_REPORT.md.

Hard constraints, asserted in code rather than remembered:

* **Zero API calls.** Nothing in this file talks to Gemini or any hosted model.
* **Dev subjects only.** Every ``canonical_id`` that reaches a prompt is checked
  against results/stage2_pilot/dev_subjects.json.
* **C00292 is burned for Q-A** (SPEC D1 / T1 round 2). It has a full option set
  on disk -- T2 built its artifacts either way -- so the exclusion is enforced
  here, by filtering on the ``burned_for_qa`` annotation, and asserted at
  export and again at verify. It IS included in the classifier prompts.
* **Budget.** ``plan`` projects node-hours before anything is submitted; the
  driver refuses to bootstrap sbatch files if its own projection exceeds
  :data:`PROJECTION_ABORT_NODE_HOURS`.

Redaction (binding, orchestrator adjudication). Every rendered field is
scrubbed, not just the excerpts: the question and all four option texts are
redacted with the SUBJECT's variants, twin grounding likewise, and imposter
grounding with the DONOR's variants. Six of the eighteen Q-A questions name
their subject out loud (T2 concern 3), so this is load-bearing rather than
theoretical. After rendering, both D8 guards run on the full string and the
export refuses to write anything if a single one trips.

Subcommands
-----------
``plan``       build every prompt in memory, prove the guards, project
               node-hours. Writes nothing.
``export``     the same build, written to results/stage2_pilot/exports/ with a
               sha256 export manifest.
``verify``     re-run every guard against the prompts ON DISK, without
               re-rendering them, and re-check the manifest digests.
``bootstrap``  run config + the two sbatch files (smoke, full) + the manifest.
``record``     write a slurm job id / status / anomaly into the manifest.
``ingest``     join returned completions by idx, score, write records,
               analysis.json and the per-job cost-log lines.
``report``     results/stage2_pilot/PILOT_REPORT.md from analysis.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from doppler import followup_render as F  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402
from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402

RESULTS_DIR = _ROOT / "results"
PILOT_DIR = RESULTS_DIR / "stage2_pilot"
EXPORT_DIR = PILOT_DIR / "exports"
RECORDS_DIR = PILOT_DIR / "records"
DONORS_DIR = PILOT_DIR / "donors"
MANIFEST = PILOT_DIR / "manifest.json"
EXPORT_MANIFEST = EXPORT_DIR / "export_manifest.json"
ANALYSIS = PILOT_DIR / "analysis.json"
REPORT = PILOT_DIR / "PILOT_REPORT.md"
IMPOSTER_PAIRS = PILOT_DIR / "imposter_pairs.json"

#: The banner that has to appear on anything this driver writes.
PILOT_BANNER = ("PILOT -- pipeline validation on dev subjects; "
                "no research conclusions.")

# ---------------------------------------------------------------------------
# Node / job configuration
# ---------------------------------------------------------------------------

REMOTE = "leonardo"
NODE_ROOT = "/leonardo_work/AIFAC_P02_548/DOPPLER"
NODE_RUN = f"{NODE_ROOT}/runs/stage2_pilot"
NODE_JOBS = f"{NODE_ROOT}/jobs"
ACCOUNT = "AIFAC_P02_548"
MODEL = f"{NODE_ROOT}/models/Gemma-4-31B-it"
MODEL_LABEL = "leonardo-gemma4-31b-it"
SPLIT_LABEL = "stage2_pilot"

TP = 4
TEMPERATURE = 0.0
GPU_MEM_UTIL = 0.92

#: Context window for the pilot job.
#:
#: Stage 1E ran at 2048, which is far too small here: a twin prompt carries a
#: 2,000-word grounding block (SPEC D8's B_pilot) plus up to a 1,135-word option
#: block (C02013's long Z-bucket items), so the longest prompt is ~3,300
#: whitespace words. The T6 brief named 4096; measurement says 4096 is not
#: enough either -- see :func:`context_check`, which recomputes the arithmetic at
#: export time from the real prompts and refuses to write if the longest one
#: would not fit. 8192 is the smallest power of two with headroom at the
#: measured worst-case token/word ratio.
MAX_MODEL_LEN = 8192

#: Words -> tokens. Measured on 1,501 Stage 1E prompts against this exact model
#: (Gemma-4-31B-it): mean 1.905, p95 1.952, max 2.041 tokens per whitespace
#: word. The mean drives the projection, the max drives the context check.
TOKENS_PER_WORD = 1.9
TOKENS_PER_WORD_MAX = 2.05

#: Combined (prompt + completion) token throughput, measured on the Stage 1E
#: confirm static job: (21,547,730 in + 2,695,006 out) / 1153.59 s = 21,015
#: tokens/s on one 4xA100 node. Stage 2's prompts are ~10x longer, which shifts
#: the job from decode-bound to prefill-bound, so the projection de-rates it.
MEASURED_TOKENS_PER_SECOND = 21000.0
LONG_PROMPT_DERATE = 3.0
ENGINE_INIT_SECONDS = 225.0

#: Stop and ask rather than submit, if our own projection lands above this.
PROJECTION_ABORT_NODE_HOURS = 1.5
#: The hard ceiling the brief sets for the whole pilot.
BUDGET_NODE_HOURS = 3.0

SMOKE_WALLTIME = "00:20:00"
FULL_WALLTIME = "01:00:00"
SMOKE_QOS = "boost_qos_dbg"

#: Two prompts from each of the ten prediction sets plus two classifier cases.
SMOKE_PER_SET = 2
SMOKE_CLASSIFY = 2

# ---------------------------------------------------------------------------
# Design constants
# ---------------------------------------------------------------------------

ARMS = R.ARMS                       # the five D8 arms, in SPEC order
VARIANTS = ("standard", "stripped")  # A4.2's entity-stripped option re-score
GROUNDING_BUDGET_WORDS = R.GROUNDING_BUDGET_WORDS   # 2000, SPEC D8

#: The subject the draw retired for Q-A. Named here so the exclusion is
#: greppable; the driver still reads the annotation rather than this constant.
BURNED_FOR_QA = "C00292"

#: Seed for the report's 20-case classifier sample. Report presentation only --
#: nothing scored depends on it.
SAMPLE_SEED = 49


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


def rel(path: Path) -> str:
    """Repo-relative path for printing, absolute when it is outside the repo."""
    try:
        return str(Path(path).relative_to(_ROOT))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# Subjects, donors, and the C00292 exclusion
# ---------------------------------------------------------------------------


def dev_subjects(pilot_dir=PILOT_DIR) -> list[dict]:
    """The committed draw. Never re-drawn, and never silently short."""
    doc = S.load_dev_subjects(pilot_dir)
    subjects = list(doc["subjects"])
    if len(subjects) != 6:
        raise fatal(f"expected 6 dev subjects, dev_subjects.json has "
                    f"{len(subjects)}")
    return subjects


def prediction_subjects(subjects: list[dict]) -> list[dict]:
    """The Q-A-capable dev subjects: everyone the draw did not burn for Q-A.

    SPEC D1 / T1 round 2 retired C00292 in place. T2 built its Q-A item and its
    full four-option set anyway (nothing in T2 filters on the annotation), so
    the exclusion has to happen HERE or a burned subject silently enters five
    prediction arms. The filter is on the annotation, not on the id.
    """
    keep = [s for s in subjects if not s.get("burned_for_qa")]
    burned = [s["canonical_id"] for s in subjects if s.get("burned_for_qa")]
    if not burned:
        raise fatal("no dev subject carries burned_for_qa; the draw that this "
                    "driver was written against retired C00292 in place, so "
                    "either dev_subjects.json changed or it is the wrong file")
    if len(keep) + len(burned) != len(subjects):
        raise fatal("burned_for_qa partition does not cover the draw")
    return keep


def classifier_subjects(subjects: list[dict]) -> list[dict]:
    """All six. The burned subject is a full participant in the classifier."""
    return list(subjects)


def pool_rows() -> dict:
    return {r["canonical_id"]: r for r in S.load_pool()}


def name_variants(row: dict) -> list[str]:
    """Every string the redactor must be able to reach for one person.

    The pool's ``variants`` column plus ``canonical_name``. T4's ``redact``
    expands each of these to its bare name tokens by default, which is what
    catches the surnames the transcripts actually use.
    """
    out = list(row.get("variants") or [])
    canonical = (row.get("canonical_name") or "").strip()
    if canonical and canonical not in out:
        out.append(canonical)
    variants = sorted({v.strip() for v in out if v and v.strip()})
    if not variants:
        raise fatal(f"{row.get('canonical_id')} has no name variants at all; "
                    "redaction would be a no-op")
    return variants


def assert_label_coverage(cid: str, turns: list[dict], variants: list[str],
                          where: str) -> list[str]:
    """Every name form the corpus uses for this person must be reachable.

    The pool's ``variants`` column is usually just the full name, while a
    transcript's own speaker label sometimes carries a first name that is not in
    it (C00292 is labelled ``AFSANE BASSIR POUR`` against a pool variant of
    ``Bassir Pour``). T4's guard is exactly as strong as its scrubber, so a name
    form outside the variant list is a leak the guard cannot see. Returns the
    uncovered forms; the caller decides whether that is fatal.
    """
    uncovered: list[str] = []
    seen: set[str] = set()
    for turn in turns:
        if turn.get("role") != "guest":
            continue
        label = turn.get("speaker_label") or ""
        if label in seen:
            continue
        seen.add(label)
        tokens = S.label_tokens(label)
        for token in tokens:
            if len(token) < 2:
                continue
            if not R.surviving_variants(token, variants):
                uncovered.append(f"{cid} {where}: {label!r} -> {token!r}")
    return sorted(set(uncovered))


def imposter_pairs(path=IMPOSTER_PAIRS) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return dict(doc["pairs"])


# ---------------------------------------------------------------------------
# Grounding segments (SPEC D8 shape, built from D3 turn files)
# ---------------------------------------------------------------------------


def build_exchanges(turns: list[dict]) -> list[dict]:
    """One transcript's turns -> T4's ``exchanges`` list.

    An exchange is a maximal run of consecutive guest turns, joined with single
    spaces, plus the host turn immediately before the run when the turn
    immediately before the run IS a host turn. When an "other" speaker
    intervened, the host side is empty and the exchange renders one line. A run
    whose joined guest text is empty is dropped -- an exchange with no guest
    speech is not evidence about the guest.

    ``turns`` is a SPEC D3 list for ONE transcript, in any order; it is sorted
    by ``turn_idx`` here so the caller cannot pass an accidental ordering.
    """
    ordered = sorted(turns, key=lambda t: t["turn_idx"])
    exchanges: list[dict] = []
    run: list[str] = []
    run_host = ""
    for pos, turn in enumerate(ordered):
        if turn.get("role") == "guest":
            if not run:
                prev = ordered[pos - 1] if pos else None
                run_host = (prev.get("text") or "").strip() \
                    if prev is not None and prev.get("role") == "host" else ""
            run.append((turn.get("text") or "").strip())
            continue
        if run:
            _flush_exchange(exchanges, run_host, run)
            run = []
    if run:
        _flush_exchange(exchanges, run_host, run)
    return exchanges


def _flush_exchange(exchanges: list[dict], host: str, run: list[str]) -> None:
    guest = " ".join(part for part in run if part).strip()
    if not guest:
        return
    exchanges.append({"host_text": host, "guest_text": guest})


def build_segments(turns: list[dict], split: dict) -> list[dict]:
    """T4's segment list for one person's grounding side.

    One segment per grounding transcript that yields at least one exchange,
    carrying the date and program the split recorded, ordered by (date,
    transcript_id) so the input order is deterministic. ``render_grounding``
    re-sorts by date itself; the tie-break it falls back on is input position,
    which is why the order is pinned here rather than left to dict iteration.
    """
    meta = {g["transcript_id"]: g for g in split.get("grounding", [])}
    test_tid = (split.get("test") or {}).get("transcript_id")
    by_tid: dict[str, list[dict]] = {}
    for turn in turns:
        by_tid.setdefault(turn["transcript_id"], []).append(turn)
    if test_tid and test_tid in by_tid:
        # D8 guard (b). T1 asserts this when it writes the split; asserting it
        # again here costs nothing and this is the file that would carry the
        # damage.
        raise fatal(f"test transcript {test_tid} appears in the grounding turn "
                    "file -- the test interview must never enter grounding")
    segments = []
    for tid in sorted(by_tid, key=lambda t: (meta.get(t, {}).get("date", ""), t)):
        exchanges = build_exchanges(by_tid[tid])
        if not exchanges:
            continue
        entry = meta.get(tid, {})
        segments.append({
            "transcript_id": tid,
            "date": entry.get("date", ""),
            "program": entry.get("program", ""),
            "title": entry.get("title", ""),
            "exchanges": exchanges,
        })
    if not segments:
        raise fatal("no grounding segments could be built")
    return segments


def subject_grounding(cid: str, pilot_dir=PILOT_DIR) -> tuple[list[dict], list[dict]]:
    turns = S.read_jsonl(S.subject_dir(cid, pilot_dir) / "grounding_turns.jsonl")
    split = S.load_split(cid, pilot_dir)
    return build_segments(turns, split), turns


def donor_grounding(donor_id: str, pilot_dir=PILOT_DIR) -> tuple[list[dict], list[dict]]:
    base = Path(pilot_dir) / "donors" / donor_id
    turns = S.read_jsonl(base / "grounding_turns.jsonl")
    split = json.loads((base / "split.json").read_text(encoding="utf-8"))
    return build_segments(turns, split), turns


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


def load_items(cid: str, pilot_dir=PILOT_DIR) -> list[dict]:
    """T2's Q-A items joined to their option sets, in file order."""
    base = S.subject_dir(cid, pilot_dir)
    qa = S.read_jsonl(base / "qa_items.jsonl")
    opts = {row["item_id"]: row for row in
            S.read_jsonl(base / "distractors.jsonl")}
    items = []
    for row in qa:
        options = opts.get(row["item_id"])
        if options is None:
            raise fatal(f"{row['item_id']} has no distractors.jsonl row")
        texts = [o["text"] for o in options["options"]]
        stripped = list(options["options_stripped"])
        if len(texts) != len(stripped):
            raise fatal(f"{row['item_id']}: option/stripped length mismatch")
        correct = int(options["correct_index"])
        if not 0 <= correct < len(texts):
            raise fatal(f"{row['item_id']}: correct_index out of range")
        if options["options"][correct]["kind"] != "true":
            raise fatal(f"{row['item_id']}: correct_index does not point at "
                        "the true option")
        items.append({
            "item_id": row["item_id"],
            "canonical_id": row["canonical_id"],
            "transcript_id": row["transcript_id"],
            "q_turn_idx": row["q_turn_idx"],
            "question": row["question"],
            "answer": row["answer"],
            "answer_words": row["answer_words"],
            "options": {"standard": texts, "stripped": stripped},
            "correct_index": correct,
            "relax_rung": options.get("relax_rung"),
            "flags": row.get("flags", []),
        })
    return items


# ---------------------------------------------------------------------------
# Rendering + guards
# ---------------------------------------------------------------------------


def _name_line(arm: str, name: str) -> str:
    if arm == "twin_named":
        return R.TWIN_NAME_LINE.format(name=name)
    if arm == "zeroinfo_named":
        return R.ZEROINFO_NAME_LINE.format(name=name)
    raise fatal(f"{arm} is not a named arm")


_REDACTED_TWIN = {"twin_named": "twin_redacted",
                  "zeroinfo_named": "zeroinfo_redacted"}


def render_and_guard(arm: str, variant: str, item: dict, *,
                     subject_name: str, subject_variants: list[str],
                     grounding_block: str | None,
                     donor_variants: list[str] | None = None) -> dict:
    """Render one prompt and prove both D8 guards on it. Raises on any trip.

    ``grounding_block`` is already rendered AND already redacted (with the
    donor's variants for the imposter arm, the subject's for the twin arms).
    The question and every option are redacted here, with the SUBJECT's
    variants, for every arm including the imposter one -- they come from the
    subject's test interview and the distractor bank either way.
    """
    question = R.redact(item["question"], subject_variants)
    options = [R.redact(text, subject_variants)
               for text in item["options"][variant]]
    grounded = arm in R.GROUNDED_ARMS
    named = arm in R.NAMED_ARMS

    rendered = R.render_prompt(
        arm, question, options,
        grounding_block=grounding_block if grounded else None,
        name=subject_name if named else None,
    )

    # --- guard (c): no name may survive in the rendered string ---------------
    # A named arm reveals the name on purpose, on exactly one line. Strip that
    # line and assert on the rest -- and check while we are there that removing
    # it reproduces the redacted arm byte for byte, which is T4's own
    # one-factor invariant and catches template drift for free.
    guarded = rendered
    if named:
        line = _name_line(arm, subject_name)
        marker = f"{line}\n\n"
        if marker not in rendered:
            raise fatal(f"{arm} {item['item_id']}: the name line is not where "
                        "the template says it is")
        guarded = rendered.replace(marker, "", 1)
        twin = R.render_prompt(
            _REDACTED_TWIN[arm], question, options,
            grounding_block=grounding_block if grounded else None,
        )
        if guarded != twin:
            raise fatal(f"{arm} {item['item_id']}: differs from its redacted "
                        "counterpart by more than the name line")
    R.assert_redacted(guarded, subject_variants)
    if donor_variants is not None:
        # The imposter arm has two identities and neither list covers the
        # other. Asserting only the donor's would let the subject's name
        # through the question, which is the leak that makes an imposter prompt
        # look like a twin (T4 section 9.2).
        R.assert_redacted(rendered, donor_variants)

    # --- guard (a): the true answer must not sit in the excerpts -------------
    if grounded:
        true_raw = item["answer"]
        true_shown = options[item["correct_index"]]
        R.assert_no_answer_leak(grounding_block, true_raw)
        R.assert_no_answer_leak(grounding_block, true_shown)

    # --- zero-information arms carry no excerpts, program or date ------------
    if not grounded:
        if R.EXCERPTS_HEADER in rendered or "[Interview," in rendered:
            raise fatal(f"{arm} {item['item_id']}: a zero-information prompt "
                        "carries an excerpt block")

    words = R.word_count(rendered)
    return {
        "prompt": rendered,
        "prompt_sha256": R.sha256(rendered),
        "prompt_words": words,
        "prompt_tokens_est": int(round(words * TOKENS_PER_WORD)),
        "max_output_tokens": R.MAX_OUTPUT_TOKENS,
    }


# ---------------------------------------------------------------------------
# The build: everything in memory, guards proven, before a byte is written
# ---------------------------------------------------------------------------


def build_prediction(pilot_dir=PILOT_DIR) -> dict:
    """Every prediction prompt for every arm and both option variants."""
    subjects = dev_subjects(pilot_dir)
    dev_ids = {s["canonical_id"] for s in subjects}
    qa_subjects = prediction_subjects(subjects)
    pool = pool_rows()
    pairs = imposter_pairs(Path(pilot_dir) / "imposter_pairs.json")

    sets: dict[tuple[str, str], list[dict]] = {
        (arm, variant): [] for arm in ARMS for variant in VARIANTS}
    per_subject: dict[str, dict] = {}
    coverage_warnings: list[str] = []

    for subject in qa_subjects:
        cid = subject["canonical_id"]
        if cid not in dev_ids:
            raise fatal(f"{cid} is not in dev_subjects.json")
        if subject.get("burned_for_qa"):
            raise fatal(f"{cid} is burned_for_qa and must not reach a "
                        "prediction arm")
        row = pool[cid]
        variants = name_variants(row)
        name = row["canonical_name"]

        segments, turns = subject_grounding(cid, pilot_dir)
        coverage_warnings += assert_label_coverage(cid, turns, variants,
                                                   "grounding")
        twin_raw = R.render_grounding(segments, GROUNDING_BUDGET_WORDS)
        twin_block = R.redact(twin_raw, variants)
        R.assert_redacted(twin_block, variants)

        donor_id = pairs.get(cid)
        if donor_id is None:
            raise fatal(f"{cid} has no imposter donor in imposter_pairs.json")
        if donor_id in dev_ids:
            raise fatal(f"donor {donor_id} for {cid} is itself a dev subject")
        donor_row = pool[donor_id]
        donor_variants = name_variants(donor_row)
        donor_segments, donor_turns = donor_grounding(donor_id, pilot_dir)
        coverage_warnings += assert_label_coverage(
            donor_id, donor_turns, donor_variants, f"donor of {cid}")
        donor_raw = R.render_grounding(donor_segments, GROUNDING_BUDGET_WORDS)
        donor_block = R.redact(donor_raw, donor_variants)
        R.assert_redacted(donor_block, donor_variants)

        items = load_items(cid, pilot_dir)
        for item in items:
            if item["canonical_id"] != cid:
                raise fatal(f"{item['item_id']} claims subject "
                            f"{item['canonical_id']} in {cid}'s file")
            for arm in ARMS:
                if arm == "imposter_redacted":
                    block, donor_check = donor_block, donor_variants
                elif arm in R.GROUNDED_ARMS:
                    block, donor_check = twin_block, None
                else:
                    block, donor_check = None, None
                for variant in VARIANTS:
                    built = render_and_guard(
                        arm, variant, item,
                        subject_name=name, subject_variants=variants,
                        grounding_block=block, donor_variants=donor_check)
                    built.update({
                        "item_id": item["item_id"],
                        "canonical_id": cid,
                        "arm": arm,
                        "variant": variant,
                        "correct_index": item["correct_index"],
                        "n_options": len(item["options"][variant]),
                        "donor_id": donor_id if arm == "imposter_redacted"
                        else None,
                    })
                    sets[(arm, variant)].append(built)

        per_subject[cid] = {
            "canonical_id": cid,
            "canonical_name": name,
            "wiki_status": subject.get("wiki_status"),
            "n_items": len(items),
            "item_ids": [i["item_id"] for i in items],
            "donor_id": donor_id,
            "donor_name": donor_row["canonical_name"],
            "n_grounding_segments": len(segments),
            "n_grounding_exchanges": sum(len(s["exchanges"]) for s in segments),
            "grounding_words_available": sum(
                R.word_count(e["host_text"]) + R.word_count(e["guest_text"])
                for s in segments for e in s["exchanges"]),
            "grounding_words_rendered": R.word_count(twin_block),
            "donor_grounding_words_rendered": R.word_count(donor_block),
            "grounding_budget_words": GROUNDING_BUDGET_WORDS,
            "variants_used": variants,
            "donor_variants_used": donor_variants,
        }

    n = {key: len(rows) for key, rows in sets.items()}
    if len(set(n.values())) != 1:
        raise fatal(f"prompt sets are not the same size: {n}")
    return {
        "sets": sets,
        "per_subject": per_subject,
        "n_items": sum(v["n_items"] for v in per_subject.values()),
        "n_subjects": len(per_subject),
        "coverage_warnings": coverage_warnings,
        "excluded_burned_for_qa": sorted(
            s["canonical_id"] for s in subjects if s.get("burned_for_qa")),
    }


def build_classifier(pilot_dir=PILOT_DIR) -> dict:
    """Every follow-up classifier case, over all six subjects' grounding."""
    subjects = classifier_subjects(dev_subjects(pilot_dir))
    dev_ids = {s["canonical_id"] for s in subjects}
    cases: list[dict] = []
    rule_labels: list[dict] = []
    per_subject: dict[str, dict] = {}

    for subject in subjects:
        cid = subject["canonical_id"]
        if cid not in dev_ids:
            raise fatal(f"{cid} is not in dev_subjects.json")
        turns = S.read_jsonl(
            S.subject_dir(cid, pilot_dir) / "grounding_turns.jsonl")
        by_tid: dict[str, list[dict]] = {}
        for turn in turns:
            by_tid.setdefault(turn["transcript_id"], []).append(turn)
        n_model = n_rule = 0
        for tid in sorted(by_tid):
            ordered = sorted(by_tid[tid], key=lambda t: t["turn_idx"])
            for case in F.classifiable_turns(ordered):
                if case.get("source") == "rule":
                    rule_labels.append({
                        "canonical_id": cid, "transcript_id": tid,
                        "turn_idx": case["turn_idx"], "label": case["label"],
                        "source": "rule",
                    })
                    n_rule += 1
                    continue
                prompt = F.classify_prompt(
                    prev_host=case["prev_host"],
                    guest_answer=case["guest_answer"],
                    target_host=case["target_host"])
                cases.append({
                    "canonical_id": cid,
                    "transcript_id": tid,
                    "turn_idx": case["turn_idx"],
                    "target_host": case["target_host"],
                    "prompt": prompt,
                    "prompt_sha256": F.sha256(prompt),
                    "prompt_words": R.word_count(prompt),
                    "prompt_tokens_est": int(round(
                        R.word_count(prompt) * TOKENS_PER_WORD)),
                    "max_output_tokens": F.MAX_OUTPUT_TOKENS,
                })
                n_model += 1
        per_subject[cid] = {
            "canonical_id": cid,
            "canonical_name": subject.get("canonical_name"),
            "n_transcripts": len(by_tid),
            "n_model_cases": n_model,
            "n_rule_labels": n_rule,
            "burned_for_qa": bool(subject.get("burned_for_qa")),
        }
    return {
        "cases": cases,
        "rule_labels": rule_labels,
        "per_subject": per_subject,
        "rubric_sha256": F.RUBRIC_SHA256,
    }


def build_all(pilot_dir=PILOT_DIR) -> dict:
    pred = build_prediction(pilot_dir)
    clf = build_classifier(pilot_dir)
    return {"prediction": pred, "classifier": clf}


def context_check(build: dict) -> dict:
    """Prove the longest prompt fits the configured context window.

    A prompt longer than ``--max-model-len`` is refused by vLLM at generation
    time, on the node, after the engine has been paid for. Cheaper to fail here.
    """
    rows = [r for rows in build["prediction"]["sets"].values() for r in rows]
    rows += build["classifier"]["cases"]
    worst = max(rows, key=lambda r: r["prompt_words"])
    need = int(round(worst["prompt_words"] * TOKENS_PER_WORD_MAX)) \
        + worst["max_output_tokens"]
    out = {
        "longest_prompt_words": worst["prompt_words"],
        "longest_prompt_sha256": worst["prompt_sha256"],
        "longest_prompt_item": worst.get("item_id") or worst.get("transcript_id"),
        "longest_prompt_arm": worst.get("arm", "classifier"),
        "tokens_per_word_max": TOKENS_PER_WORD_MAX,
        "worst_case_tokens_needed": need,
        "max_model_len": MAX_MODEL_LEN,
        "headroom_tokens": MAX_MODEL_LEN - need,
    }
    if need > MAX_MODEL_LEN:
        raise fatal(
            f"longest prompt is {worst['prompt_words']} words -> up to {need} "
            f"tokens with its {worst['max_output_tokens']}-token reply, which "
            f"does not fit MAX_MODEL_LEN={MAX_MODEL_LEN}")
    return out


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def projection(build: dict) -> dict:
    """Node-hours, from the real prompts and Stage 1E's measured throughput."""
    pred_rows = [r for rows in build["prediction"]["sets"].values() for r in rows]
    clf_rows = build["classifier"]["cases"]
    eff = MEASURED_TOKENS_PER_SECOND / LONG_PROMPT_DERATE

    def block(rows: list[dict]) -> dict:
        tin = sum(r["prompt_tokens_est"] for r in rows)
        tout = sum(r["max_output_tokens"] for r in rows)
        return {"n_calls": len(rows), "tokens_in_est": tin,
                "tokens_out_cap": tout, "seconds": (tin + tout) / eff}

    pred, clf = block(pred_rows), block(clf_rows)
    smoke_rows = smoke_slice(build)
    smoke = block(smoke_rows)

    full_seconds = pred["seconds"] + clf["seconds"] + ENGINE_INIT_SECONDS
    smoke_seconds = smoke["seconds"] + ENGINE_INIT_SECONDS
    jobs = {
        "stage2_pilot_smoke": {
            "n_calls": smoke["n_calls"],
            "generation_seconds": round(smoke["seconds"], 1),
            "engine_init_seconds": ENGINE_INIT_SECONDS,
            "projected_node_hours": round(smoke_seconds / 3600, 4),
            "walltime": SMOKE_WALLTIME, "qos": SMOKE_QOS,
        },
        "stage2_pilot_full": {
            "n_calls": pred["n_calls"] + clf["n_calls"],
            "generation_seconds": round(pred["seconds"] + clf["seconds"], 1),
            "engine_init_seconds": ENGINE_INIT_SECONDS,
            "projected_node_hours": round(full_seconds / 3600, 4),
            "walltime": FULL_WALLTIME, "qos": "boost_usr_prod (normal)",
        },
    }
    total = round(sum(j["projected_node_hours"] for j in jobs.values()), 4)
    walltime_bound = round(_walltime_hours(SMOKE_WALLTIME)
                           + _walltime_hours(FULL_WALLTIME), 4)
    return {
        "prediction": pred, "classifier": clf, "smoke": smoke,
        "effective_tokens_per_second": round(eff, 1),
        "measured_tokens_per_second": MEASURED_TOKENS_PER_SECOND,
        "long_prompt_derate": LONG_PROMPT_DERATE,
        "tokens_per_word": TOKENS_PER_WORD,
        "jobs": jobs,
        "total_projected_node_hours": total,
        "walltime_bounded_worst_case_node_hours": walltime_bound,
        "abort_above_node_hours": PROJECTION_ABORT_NODE_HOURS,
        "budget_node_hours": BUDGET_NODE_HOURS,
        "note": "Output tokens are counted at their per-prompt CAP (120 for a "
                "prediction prompt, 80 for a classifier case), so the "
                "generation term is an upper bound. Throughput is Stage 1E's "
                "measured 21,015 combined tokens/s on one 4xA100 node, "
                f"de-rated by {LONG_PROMPT_DERATE}x because Stage 2's prompts "
                "are roughly ten times longer and shift the job from "
                "decode-bound to prefill-bound.",
    }


def _walltime_hours(walltime: str) -> float:
    hh, mm, ss = (int(p) for p in walltime.split(":"))
    return hh + mm / 60 + ss / 3600


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def set_name(arm: str, variant: str) -> str:
    return f"pred_{arm}_{variant}"


def smoke_slice(build: dict) -> list[dict]:
    """~20 prompts spanning every prompt set, in a stable order."""
    rows: list[dict] = []
    for arm in ARMS:
        for variant in VARIANTS:
            src = build["prediction"]["sets"][(arm, variant)]
            for row in src[:SMOKE_PER_SET]:
                rows.append(dict(row, source_set=set_name(arm, variant)))
    for row in build["classifier"]["cases"][:SMOKE_CLASSIFY]:
        rows.append(dict(row, source_set="classify"))
    return rows


def _write_pair(prompts_path: Path, meta_path: Path, rows: list[dict],
                meta_fields: tuple[str, ...]) -> dict:
    """Write one prompts/sidecar pair. ``idx`` is the row's position in the file.

    Per-file 0-based idx, because ``batch_generate.py`` echoes ``idx`` back per
    output file and each prompt set is its own file. The sidecar carries
    everything needed to join a completion to its item; the prompt file carries
    only what the node needs.
    """
    prompts, metas = [], []
    for idx, row in enumerate(rows):
        prompts.append({"idx": idx, "prompt": row["prompt"],
                        "max_output_tokens": row["max_output_tokens"]})
        meta = {"idx": idx}
        for field in meta_fields:
            meta[field] = row.get(field)
        metas.append(meta)
    S.write_jsonl(prompts_path, prompts)
    S.write_jsonl(meta_path, metas)
    return {
        "prompts_file": prompts_path.name,
        "meta_file": meta_path.name,
        "n_prompts": len(rows),
        "prompts_sha256": sha256_file(prompts_path),
        "meta_sha256": sha256_file(meta_path),
        "total_prompt_words": sum(r["prompt_words"] for r in rows),
        "max_prompt_words": max((r["prompt_words"] for r in rows), default=0),
    }


PRED_META_FIELDS = ("item_id", "canonical_id", "arm", "variant",
                    "correct_index", "n_options", "donor_id",
                    "prompt_sha256", "prompt_words")
CLF_META_FIELDS = ("canonical_id", "transcript_id", "turn_idx",
                   "prompt_sha256", "prompt_words")
SMOKE_META_FIELDS = ("source_set", "item_id", "canonical_id", "arm", "variant",
                     "transcript_id", "turn_idx", "prompt_sha256",
                     "prompt_words")


def cmd_export(args) -> int:
    pilot_dir = Path(getattr(args, "pilot_dir", None) or PILOT_DIR)
    export_dir = pilot_dir / "exports"
    manifest_path = export_dir / "export_manifest.json"
    if manifest_path.exists() and not args.force:
        raise fatal(f"{manifest_path} already exists; pass --force to rebuild")

    build = build_all(pilot_dir)
    ctx = context_check(build)
    proj = projection(build)
    pred, clf = build["prediction"], build["classifier"]

    print(f"[export] {PILOT_BANNER}")
    print(f"[export] {pred['n_subjects']} Q-A subjects, {pred['n_items']} items, "
          f"{len(ARMS)} arms x {len(VARIANTS)} option variants")
    print(f"[export] excluded from every prediction arm (burned_for_qa): "
          f"{', '.join(pred['excluded_burned_for_qa'])}")
    if pred["coverage_warnings"]:
        for line in pred["coverage_warnings"]:
            print(f"[warn] name form outside the variant list: {line}",
                  file=sys.stderr)

    files: dict[str, dict] = {}
    for arm in ARMS:
        for variant in VARIANTS:
            name = set_name(arm, variant)
            rows = pred["sets"][(arm, variant)]
            files[name] = _write_pair(export_dir / f"prompts_{name}.jsonl",
                                      export_dir / f"meta_{name}.jsonl",
                                      rows, PRED_META_FIELDS)
            print(f"[export] {name}: {len(rows)} prompts")

    files["classify"] = _write_pair(export_dir / "prompts_classify.jsonl",
                                    export_dir / "meta_classify.jsonl",
                                    clf["cases"], CLF_META_FIELDS)
    print(f"[export] classify: {len(clf['cases'])} model prompts")

    smoke_rows = smoke_slice(build)
    files["smoke"] = _write_pair(export_dir / "prompts_smoke.jsonl",
                                 export_dir / "meta_smoke.jsonl",
                                 smoke_rows, SMOKE_META_FIELDS)
    print(f"[export] smoke: {len(smoke_rows)} prompts spanning "
          f"{len(ARMS) * len(VARIANTS) + 1} sets")

    rule_path = export_dir / "labels_rule.jsonl"
    S.write_jsonl(rule_path, clf["rule_labels"])
    files["labels_rule"] = {
        "prompts_file": None, "meta_file": rule_path.name,
        "n_prompts": 0, "n_rows": len(clf["rule_labels"]),
        "meta_sha256": sha256_file(rule_path),
    }
    print(f"[export] labels_rule: {len(clf['rule_labels'])} rule-labelled turns "
          "(NEW-TOPIC by definition, no model call)")

    doc = {
        "pilot": PILOT_BANNER,
        "exported_utc": now(),
        "contract": "SPEC.md v1.6 (D1-D10)",
        "n_qa_subjects": pred["n_subjects"],
        "n_items": pred["n_items"],
        "arms": list(ARMS),
        "option_variants": list(VARIANTS),
        "prediction_prompts_total": sum(
            files[set_name(a, v)]["n_prompts"] for a in ARMS for v in VARIANTS),
        "classifier_prompts_total": files["classify"]["n_prompts"],
        "rule_labels_total": len(clf["rule_labels"]),
        "excluded_burned_for_qa": pred["excluded_burned_for_qa"],
        "coverage_warnings": pred["coverage_warnings"],
        "grounding_budget_words": GROUNDING_BUDGET_WORDS,
        "renderer": {
            "stage2_render_template_sha256": R.TEMPLATE_SHA256,
            "followup_rubric_sha256": F.RUBRIC_SHA256,
            "stage2_render_file_sha256": sha256_file(
                _ROOT / "src/doppler/stage2_render.py"),
            "followup_render_file_sha256": sha256_file(
                _ROOT / "src/doppler/followup_render.py"),
        },
        "per_subject": pred["per_subject"],
        "classifier_per_subject": clf["per_subject"],
        "context": ctx,
        "projection": proj,
        "files": files,
    }
    S.write_json(manifest_path, doc)
    print(f"[export] manifest -> {manifest_path}")
    print(f"[export] projected {proj['total_projected_node_hours']} node-hours "
          f"(abort above {PROJECTION_ABORT_NODE_HOURS})")
    return 0


# ---------------------------------------------------------------------------
# Verify: re-run every guard against what is ON DISK
# ---------------------------------------------------------------------------


def cmd_verify(args) -> int:
    pilot_dir = Path(getattr(args, "pilot_dir", None) or PILOT_DIR)
    export_dir = pilot_dir / "exports"
    manifest_path = export_dir / "export_manifest.json"
    if not manifest_path.exists():
        raise fatal(f"{manifest_path} not found; run export first")
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))

    subjects = dev_subjects(pilot_dir)
    dev_ids = {s["canonical_id"] for s in subjects}
    burned = {s["canonical_id"] for s in subjects if s.get("burned_for_qa")}
    pool = pool_rows()
    variants_of = {cid: name_variants(pool[cid]) for cid in dev_ids}
    checks = {"files": 0, "prompts": 0, "guard_redacted": 0,
              "guard_answer_leak": 0, "zeroinfo_clean": 0}

    # --- file digests --------------------------------------------------------
    for name, info in doc["files"].items():
        if info.get("prompts_file"):
            path = export_dir / info["prompts_file"]
            got = sha256_file(path)
            if got != info["prompts_sha256"]:
                raise fatal(f"{path.name} sha256 {got} != manifest "
                            f"{info['prompts_sha256']}")
            checks["files"] += 1
        meta_path = export_dir / info["meta_file"]
        got = sha256_file(meta_path)
        if got != info["meta_sha256"]:
            raise fatal(f"{meta_path.name} sha256 {got} != manifest "
                        f"{info['meta_sha256']}")
        checks["files"] += 1

    # --- true answers, for guard (a) ----------------------------------------
    answers: dict[str, dict] = {}
    for cid in dev_ids:
        for item in load_items(cid, pilot_dir):
            answers[item["item_id"]] = item

    donor_variants_of = {}
    for cid, donor_id in imposter_pairs(pilot_dir / "imposter_pairs.json").items():
        donor_variants_of[cid] = name_variants(pool[donor_id])

    for arm in ARMS:
        for variant in VARIANTS:
            name = set_name(arm, variant)
            prompts = S.read_jsonl(export_dir / f"prompts_{name}.jsonl")
            metas = S.read_jsonl(export_dir / f"meta_{name}.jsonl")
            joined = join_by_idx(prompts, metas)
            if len(joined) != len(prompts) or len(prompts) != len(metas):
                raise fatal(f"{name}: prompts/meta do not join 1:1 on idx")
            if len(joined) != doc["n_items"]:
                raise fatal(f"{name}: {len(joined)} prompts, expected "
                            f"{doc['n_items']}")
            for row in joined:
                cid = row["canonical_id"]
                if cid not in dev_ids:
                    raise fatal(f"{name} idx {row['idx']}: {cid} is not a dev "
                                "subject")
                if cid in burned:
                    raise fatal(f"{name} idx {row['idx']}: {cid} is "
                                "burned_for_qa and must not be in a "
                                "prediction prompt set")
                if row["arm"] != arm or row["variant"] != variant:
                    raise fatal(f"{name} idx {row['idx']}: sidecar says "
                                f"{row['arm']}/{row['variant']}")
                text = row["prompt"]
                if R.sha256(text) != row["prompt_sha256"]:
                    raise fatal(f"{name} idx {row['idx']}: prompt digest moved")
                guarded = text
                if arm in R.NAMED_ARMS:
                    line = _name_line(arm, pool[cid]["canonical_name"])
                    marker = f"{line}\n\n"
                    if marker not in text:
                        raise fatal(f"{name} idx {row['idx']}: named arm has "
                                    "no name line")
                    guarded = text.replace(marker, "", 1)
                R.assert_redacted(guarded, variants_of[cid])
                checks["guard_redacted"] += 1
                if arm == "imposter_redacted":
                    R.assert_redacted(text, donor_variants_of[cid])
                    checks["guard_redacted"] += 1
                if arm in R.GROUNDED_ARMS:
                    block = excerpt_block(text)
                    R.assert_no_answer_leak(block, answers[row["item_id"]]["answer"])
                    checks["guard_answer_leak"] += 1
                else:
                    if R.EXCERPTS_HEADER in text or "[Interview," in text:
                        raise fatal(f"{name} idx {row['idx']}: zero-information "
                                    "prompt carries excerpts")
                    checks["zeroinfo_clean"] += 1
                checks["prompts"] += 1

    prompts = S.read_jsonl(export_dir / "prompts_classify.jsonl")
    metas = S.read_jsonl(export_dir / "meta_classify.jsonl")
    joined = join_by_idx(prompts, metas)
    if len(joined) != len(prompts) or len(prompts) != len(metas):
        raise fatal("classify: prompts/meta do not join 1:1 on idx")
    for row in joined:
        if row["canonical_id"] not in dev_ids:
            raise fatal(f"classify idx {row['idx']}: "
                        f"{row['canonical_id']} is not a dev subject")
        if F.sha256(row["prompt"]) != row["prompt_sha256"]:
            raise fatal(f"classify idx {row['idx']}: prompt digest moved")
        if not row["prompt"].startswith(F.RUBRIC_V1):
            raise fatal(f"classify idx {row['idx']}: prompt does not open on "
                        "the frozen rubric")
        checks["prompts"] += 1

    print(f"[verify] {PILOT_BANNER}")
    print(f"[verify] {checks['files']} file digests match the manifest")
    print(f"[verify] {checks['prompts']} prompts re-checked on disk")
    print(f"[verify] {checks['guard_redacted']} redaction assertions passed "
          f"({checks['guard_answer_leak']} answer-leak, "
          f"{checks['zeroinfo_clean']} zero-information cleanliness)")
    print(f"[verify] burned_for_qa {sorted(burned)} absent from all "
          f"{len(ARMS) * len(VARIANTS)} prediction sets")
    return 0


def join_by_idx(prompts: list[dict], metas: list[dict]) -> list[dict]:
    """Join a prompts file to its sidecar on ``idx``. Missing/extra idx is fatal."""
    by_idx = {}
    for row in metas:
        idx = int(row["idx"])
        if idx in by_idx:
            raise fatal(f"sidecar has duplicate idx {idx}")
        by_idx[idx] = row
    out = []
    for row in prompts:
        idx = int(row["idx"])
        meta = by_idx.pop(idx, None)
        if meta is None:
            raise fatal(f"prompt idx {idx} has no sidecar row")
        out.append({**meta, **row, "idx": idx})
    if by_idx:
        raise fatal(f"sidecar has {len(by_idx)} rows with no prompt: "
                    f"{sorted(by_idx)[:5]}")
    return out


def excerpt_block(rendered: str) -> str:
    """The PAST INTERVIEWS block of a rendered twin/imposter prompt."""
    start = rendered.find(R.EXCERPTS_HEADER)
    if start < 0:
        return ""
    start += len(R.EXCERPTS_HEADER)
    end = rendered.find(R.LATER_HEADER, start)
    return rendered[start:end if end >= 0 else None].strip()


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


def cmd_plan(args) -> int:
    pilot_dir = Path(getattr(args, "pilot_dir", None) or PILOT_DIR)
    build = build_all(pilot_dir)
    ctx = context_check(build)
    proj = projection(build)
    pred, clf = build["prediction"], build["classifier"]

    print(f"=== Stage 2 pilot: projection ===   {PILOT_BANNER}")
    print(f"  dev subjects            6 ({pred['n_subjects']} Q-A capable; "
          f"burned_for_qa {', '.join(pred['excluded_burned_for_qa'])} excluded "
          "from every prediction arm)")
    print(f"  Q-A items               {pred['n_items']}")
    print(f"  prediction prompts      {pred['n_items']} items x {len(ARMS)} arms "
          f"x {len(VARIANTS)} variants = "
          f"{pred['n_items'] * len(ARMS) * len(VARIANTS)}")
    print(f"  classifier prompts      {len(clf['cases'])} model cases "
          f"(+ {len(clf['rule_labels'])} rule-labelled, no model call)")
    print(f"  longest prompt          {ctx['longest_prompt_words']} words "
          f"-> up to {ctx['worst_case_tokens_needed']} tokens; "
          f"max-model-len {ctx['max_model_len']} "
          f"(headroom {ctx['headroom_tokens']})")
    print(f"  throughput              {proj['measured_tokens_per_second']:.0f} "
          f"tok/s measured / {proj['long_prompt_derate']}x de-rate = "
          f"{proj['effective_tokens_per_second']:.0f} tok/s")
    print("  --- node-hours ---")
    for name, job in proj["jobs"].items():
        print(f"  {name:22s} {job['projected_node_hours']:7.4f}  "
              f"({job['n_calls']:,} calls, {job['walltime']} walltime)")
    print(f"  {'TOTAL':22s} {proj['total_projected_node_hours']:7.4f}  "
          f"(abort above {PROJECTION_ABORT_NODE_HOURS}; brief's cap "
          f"{BUDGET_NODE_HOURS})")
    print(f"  walltime-bounded worst case {proj['walltime_bounded_worst_case_node_hours']} "
          "node-hours if both jobs run to their limit")
    if proj["total_projected_node_hours"] > PROJECTION_ABORT_NODE_HOURS:
        raise fatal(f"projection {proj['total_projected_node_hours']} exceeds "
                    f"{PROJECTION_ABORT_NODE_HOURS} node-hours -- STOP and "
                    "report BLOCKED rather than submitting")
    return 0


# ---------------------------------------------------------------------------
# sbatch + manifest
# ---------------------------------------------------------------------------


HEADER = """#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --partition=boost_usr_prod
#SBATCH --account={account}
{qos_line}#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time={walltime}
#SBATCH --output={node_root}/logs/%x-%j.out
#
# Stage 2 PILOT -- {title}
# {banner}
# Projected {hours:.4f} node-hours. One engine init; every prompt file runs
# through it in sequence. Re-submitting skips any file that already has output.
set -euo pipefail
D={node_root}
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
mkdir -p "{out}"
echo "[{name}] node=$(hostname) start=$(date -u +%FT%TZ)"
"""

FOOTER = '\necho "[{name}] DONE $(date -u +%FT%TZ)"\n'


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


def full_set_names() -> list[str]:
    return [set_name(a, v) for a in ARMS for v in VARIANTS] + ["classify"]


def smoke_sbatch(hours: float) -> str:
    head = HEADER.format(
        job_name="dop-s2pilot-smoke", account=ACCOUNT,
        qos_line=f"#SBATCH --qos={SMOKE_QOS}\n",
        walltime=SMOKE_WALLTIME, node_root=NODE_ROOT,
        title="smoke slice spanning every prompt set (debug QOS)",
        banner=PILOT_BANNER, hours=hours, name="stage2_pilot_smoke",
        out=NODE_RUN)
    return head + _pairs_loop(["smoke"]) + FOOTER.format(
        name="stage2_pilot_smoke")


def full_sbatch(hours: float) -> str:
    head = HEADER.format(
        job_name="dop-s2pilot-full", account=ACCOUNT, qos_line="",
        walltime=FULL_WALLTIME, node_root=NODE_ROOT,
        title="all 10 prediction sets + the follow-up classifier",
        banner=PILOT_BANNER, hours=hours, name="stage2_pilot_full",
        out=NODE_RUN)
    return head + _pairs_loop(full_set_names()) + FOOTER.format(
        name="stage2_pilot_full")


def load_manifest(path=MANIFEST) -> dict:
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "created_utc": now(),
        "run": "Stage 2 pilot (SPEC D10)",
        "confirmatory": False,
        "pilot": PILOT_BANNER,
        "contract": "SPEC.md v1.6",
        "jobs": {}, "anomalies": [], "notes": [],
    }


def save_manifest(man: dict, path=MANIFEST) -> None:
    man["updated_utc"] = now()
    S.write_json(path, man)


def cmd_bootstrap(args) -> int:
    pilot_dir = Path(getattr(args, "pilot_dir", None) or PILOT_DIR)
    manifest_path = pilot_dir / "manifest.json"
    export_manifest = pilot_dir / "exports/export_manifest.json"
    if not export_manifest.exists():
        raise fatal(f"{export_manifest} not found; run export first")
    doc = json.loads(export_manifest.read_text(encoding="utf-8"))
    proj = doc["projection"]
    if proj["total_projected_node_hours"] > PROJECTION_ABORT_NODE_HOURS:
        raise fatal(f"projection {proj['total_projected_node_hours']} exceeds "
                    f"{PROJECTION_ABORT_NODE_HOURS} node-hours; not writing "
                    "sbatch files")

    config = {
        "run": SPLIT_LABEL,
        "pilot": PILOT_BANNER,
        "confirmatory": False,
        "contract": "SPEC.md v1.6 (D1-D10)",
        "model": "Gemma-4-31B-it", "model_label": MODEL_LABEL,
        "temperature": TEMPERATURE, "tp": TP,
        "max_model_len": MAX_MODEL_LEN,
        "max_model_len_note":
            "Stage 1E ran at 2048 and the T6 brief named 4096. Neither fits: "
            f"the longest pilot prompt is {doc['context']['longest_prompt_words']} "
            "words (a 2,000-word grounding block plus C02013's 1,135-word "
            "option block), which needs up to "
            f"{doc['context']['worst_case_tokens_needed']} tokens at the "
            "measured worst-case 2.05 tokens/word. DEVIATION, flagged for "
            "sign-off.",
        "gpu_mem_util": GPU_MEM_UTIL,
        "arms": list(ARMS),
        "option_variants": list(VARIANTS),
        "grounding_budget_words": GROUNDING_BUDGET_WORDS,
        "n_qa_subjects": doc["n_qa_subjects"],
        "n_items": doc["n_items"],
        "excluded_burned_for_qa": doc["excluded_burned_for_qa"],
        "prediction_prompts_total": doc["prediction_prompts_total"],
        "classifier_prompts_total": doc["classifier_prompts_total"],
        "retry_policy":
            "jobs/batch_generate.py has no re-ask mechanism (checked on the "
            "node: it is one vLLM pass per prompt file, no parse hook), so a "
            "parse failure is RECORDED, not retried. SPEC D9's 'up to 2 "
            "re-asks' is unreachable in batch mode; the pilot measures the "
            "resulting parse-failure rate instead.",
        "renderer": doc["renderer"],
        "projection": proj,
        "generated_utc": now(),
    }
    S.write_json(pilot_dir / "config.json", config)

    jobs = {
        "stage2_pilot_smoke": {
            "kind": "smoke", "walltime": SMOKE_WALLTIME, "qos": SMOKE_QOS,
            "files": ["smoke"],
            "text": smoke_sbatch(
                proj["jobs"]["stage2_pilot_smoke"]["projected_node_hours"]),
        },
        "stage2_pilot_full": {
            "kind": "full", "walltime": FULL_WALLTIME, "qos": None,
            "files": full_set_names(),
            "text": full_sbatch(
                proj["jobs"]["stage2_pilot_full"]["projected_node_hours"]),
        },
    }
    man = load_manifest(manifest_path)
    for name, spec in jobs.items():
        path = pilot_dir / f"{name}.sbatch"
        path.write_text(spec.pop("text"), encoding="utf-8")
        entry = man["jobs"].get(name, {})
        entry.update({
            "kind": spec["kind"], "walltime": spec["walltime"],
            "qos": spec["qos"], "prompt_files": spec["files"],
            "sbatch_local": rel(path),
            "sbatch_node": f"{NODE_JOBS}/{name}.sbatch",
            "node_outdir": NODE_RUN,
            "projected_node_hours":
                proj["jobs"][name]["projected_node_hours"],
            "status": entry.get("status", "bootstrapped"),
            "slurm_job_ids": entry.get("slurm_job_ids", []),
            "actual_node_hours": entry.get("actual_node_hours"),
        })
        man["jobs"][name] = entry
        print(f"[bootstrap] {name}: sbatch -> {rel(path)}")
    save_manifest(man, manifest_path)
    print(f"[bootstrap] config -> {pilot_dir / 'config.json'}")
    return 0


def cmd_record(args) -> int:
    man = load_manifest()
    if args.anomaly:
        man["anomalies"].append({"utc": now(), "job": args.name,
                                 "note": args.anomaly})
        print(f"[record] anomaly logged for {args.name}")
    entry = man["jobs"].setdefault(args.name, {})
    if args.job_id:
        entry.setdefault("slurm_job_ids", []).append(args.job_id)
    if args.status:
        entry["status"] = args.status
    if args.node_hours is not None:
        entry["actual_node_hours"] = float(args.node_hours)
    if args.note:
        entry.setdefault("notes", []).append({"utc": now(), "note": args.note})
    save_manifest(man)
    print(f"[record] {args.name}: {entry.get('status')} "
          f"jobs={entry.get('slurm_job_ids')}")
    return 0


# ---------------------------------------------------------------------------
# The thin ssh/rsync/sacct layer (argv construction only; tests monkeypatch run)
# ---------------------------------------------------------------------------


def run(argv: list[str], check: bool = True) -> str:
    """Run a command and return stdout. The single seam tests replace."""
    proc = subprocess.run(argv, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise fatal(f"{' '.join(argv)} failed ({proc.returncode}): "
                    f"{proc.stderr.strip()[:400]}")
    return proc.stdout


def ssh_argv(command: str) -> list[str]:
    return ["ssh", "-o", "BatchMode=yes", REMOTE, command]


def rsync_argv(local: Path, remote_path: str) -> list[str]:
    return ["rsync", "-az", str(local), f"{REMOTE}:{remote_path}"]


def ssh_ok() -> bool:
    return run(ssh_argv("echo ok"), check=False).strip().endswith("ok")


def sacct_argv(job_id: str) -> list[str]:
    return ["ssh", "-o", "BatchMode=yes", REMOTE,
            f"sacct -j {job_id} -X -P -n "
            "--format=JobID,State,Elapsed,AllocNodes,ExitCode"]


def parse_sacct(text: str) -> dict | None:
    """One ``sacct -X -P -n`` line -> ``{job_id, state, elapsed, nodes, hours}``."""
    for line in (text or "").splitlines():
        parts = line.strip().split("|")
        if len(parts) < 5 or not parts[0]:
            continue
        elapsed = parts[2]
        days, _, rest = elapsed.rpartition("-")
        chunks = [int(c) for c in rest.split(":")]
        while len(chunks) < 3:
            chunks.insert(0, 0)
        secs = chunks[0] * 3600 + chunks[1] * 60 + chunks[2]
        if days:
            secs += int(days) * 86400
        nodes = int(parts[3] or 1)
        return {"job_id": parts[0], "state": parts[1], "elapsed": elapsed,
                "alloc_nodes": nodes,
                "node_hours": round(secs * nodes / 3600, 4)}
    return None


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_record(meta: dict, completion: str | None) -> dict:
    """One prediction completion -> a scored record."""
    dist = R.parse_distribution(completion, n_options=int(meta["n_options"]))
    correct = int(meta["correct_index"])
    rec = {
        "item_id": meta["item_id"], "canonical_id": meta["canonical_id"],
        "arm": meta["arm"], "variant": meta["variant"],
        "correct_index": correct, "donor_id": meta.get("donor_id"),
        "raw_response": (completion or "")[:600],
        "parse_failure": dist is None,
        "distribution": dist,
        "argmax_index": None, "argmax_correct": None, "prob_mass_correct": None,
    }
    if dist is not None:
        best = max(range(len(dist)), key=lambda i: dist[i])
        rec["argmax_index"] = best
        rec["argmax_correct"] = bool(best == correct)
        rec["prob_mass_correct"] = float(dist[correct])
    return rec


def accuracy(records: list[dict]) -> dict:
    """Argmax accuracy and probability-mass-on-correct over PARSED records.

    Parse failures are excluded from both denominators and reported separately;
    ``n`` is the number of scored records, never the number attempted.
    """
    parsed = [r for r in records if not r["parse_failure"]]
    n = len(parsed)
    return {
        "n_attempted": len(records),
        "n": n,
        "n_parse_failures": len(records) - n,
        "argmax_accuracy": round(sum(1 for r in parsed if r["argmax_correct"])
                                 / n, 6) if n else None,
        "prob_mass_correct": round(sum(r["prob_mass_correct"] for r in parsed)
                                   / n, 6) if n else None,
    }


def adversarial_keep(records: list[dict], variant: str) -> set[str]:
    """Amendment A4.3's filter: drop items the zero-information arm got right.

    Returns the item_ids to KEEP. Computed within one option variant, because
    the entity-stripped re-score is a different forced choice and can flip which
    items the floor arm solves.
    """
    solved = {r["item_id"] for r in records
              if r["arm"] == "zeroinfo_redacted" and r["variant"] == variant
              and not r["parse_failure"] and r["argmax_correct"]}
    everything = {r["item_id"] for r in records if r["variant"] == variant}
    return everything - solved


def contamination_meter(records: list[dict]) -> dict:
    """Per subject: acc(zeroinfo_named) - acc(zeroinfo_redacted), both reads."""
    out: dict[str, dict] = {}
    subjects = sorted({r["canonical_id"] for r in records})
    for cid in subjects:
        entry: dict = {}
        for variant in VARIANTS:
            named = [r for r in records if r["canonical_id"] == cid
                     and r["arm"] == "zeroinfo_named" and r["variant"] == variant]
            plain = [r for r in records if r["canonical_id"] == cid
                     and r["arm"] == "zeroinfo_redacted"
                     and r["variant"] == variant]
            a, b = accuracy(named), accuracy(plain)
            entry[variant] = {
                "zeroinfo_named": a, "zeroinfo_redacted": b,
                "delta_argmax": _sub(a["argmax_accuracy"], b["argmax_accuracy"]),
                "delta_prob_mass": _sub(a["prob_mass_correct"],
                                        b["prob_mass_correct"]),
            }
        out[cid] = entry
    return out


def _sub(a, b):
    if a is None or b is None:
        return None
    return round(a - b, 6)


def paired_lift(records: list[dict], better: str, worse: str,
                variant: str, keep: set[str] | None = None) -> dict:
    """Subject-paired mean difference between two arms. NO significance test.

    With ~17 items over 5 subjects the pilot is not powered for one, and a
    p-value here would invite exactly the reading the pilot must not support.
    """
    per_subject = []
    subjects = sorted({r["canonical_id"] for r in records})
    for cid in subjects:
        def sel(arm: str) -> list[dict]:
            return [r for r in records
                    if r["canonical_id"] == cid and r["arm"] == arm
                    and r["variant"] == variant
                    and (keep is None or r["item_id"] in keep)]
        a, b = accuracy(sel(better)), accuracy(sel(worse))
        if a["n"] == 0 or b["n"] == 0:
            continue
        per_subject.append({
            "canonical_id": cid, "n_better": a["n"], "n_worse": b["n"],
            "argmax_delta": _sub(a["argmax_accuracy"], b["argmax_accuracy"]),
            "prob_mass_delta": _sub(a["prob_mass_correct"],
                                    b["prob_mass_correct"]),
        })
    def mean(field: str):
        vals = [p[field] for p in per_subject if p[field] is not None]
        return round(sum(vals) / len(vals), 6) if vals else None
    return {
        "better_arm": better, "worse_arm": worse, "variant": variant,
        "n_subjects": len(per_subject),
        "mean_argmax_delta": mean("argmax_delta"),
        "mean_prob_mass_delta": mean("prob_mass_delta"),
        "per_subject": per_subject,
        "note": "Subject-paired mean. No significance test: the pilot is not "
                "powered for one.",
    }


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


def _node_hours(summary: dict | None) -> float | None:
    if not summary:
        return None
    secs = (summary.get("engine_init_seconds", 0.0)
            + summary.get("generation_wall_seconds", 0.0))
    return round(secs / 3600, 4) if secs else None


def cmd_ingest(args) -> int:
    pilot_dir = Path(getattr(args, "pilot_dir", None) or PILOT_DIR)
    export_dir = pilot_dir / "exports"
    nodedir = Path(args.nodedir)
    records_dir = pilot_dir / "records"
    doc = json.loads((export_dir / "export_manifest.json").read_text(
        encoding="utf-8"))

    all_records: list[dict] = []
    summaries: list[dict] = []
    missing_total = 0
    for arm in ARMS:
        for variant in VARIANTS:
            name = set_name(arm, variant)
            metas = S.read_jsonl(export_dir / f"meta_{name}.jsonl")
            comp_path = nodedir / f"completions_{name}.jsonl"
            comps = {}
            if comp_path.exists():
                comps = {int(r["idx"]): r for r in S.read_jsonl(comp_path)}
                side = nodedir / f"completions_{name}.jsonl.summary.json"
                if side.exists():
                    summaries.append(json.loads(side.read_text()))
            else:
                print(f"[warn] no completions for {name}", file=sys.stderr)
            rows = []
            for meta in metas:
                comp = comps.get(int(meta["idx"]))
                if comp is None:
                    missing_total += 1
                rec = score_record(meta, comp.get("text") if comp else None)
                rec.update({
                    "idx": int(meta["idx"]),
                    "tokens_in": int((comp or {}).get("tokens_in", 0) or 0),
                    "tokens_out": int((comp or {}).get("tokens_out", 0) or 0),
                    "missing_completion": comp is None,
                })
                rows.append(rec)
            S.write_jsonl(records_dir / f"{name}.jsonl", rows)
            all_records += rows
            print(f"[ingest] {name}: {len(rows)} records, "
                  f"{sum(1 for r in rows if r['parse_failure'])} parse failures")

    # --- classifier ----------------------------------------------------------
    clf_metas = S.read_jsonl(export_dir / "meta_classify.jsonl")
    comp_path = nodedir / "completions_classify.jsonl"
    comps = {}
    if comp_path.exists():
        comps = {int(r["idx"]): r for r in S.read_jsonl(comp_path)}
        side = nodedir / "completions_classify.jsonl.summary.json"
        if side.exists():
            summaries.append(json.loads(side.read_text()))
    else:
        print("[warn] no completions for classify", file=sys.stderr)
    clf_rows = []
    for meta in clf_metas:
        comp = comps.get(int(meta["idx"]))
        text = comp.get("text") if comp else None
        label = F.parse_label(text)
        clf_rows.append({
            "idx": int(meta["idx"]),
            "canonical_id": meta["canonical_id"],
            "transcript_id": meta["transcript_id"],
            "turn_idx": meta["turn_idx"],
            "label": label, "source": "model",
            "parse_failure": label is None,
            "raw_response": (text or "")[:600],
            "tokens_in": int((comp or {}).get("tokens_in", 0) or 0),
            "tokens_out": int((comp or {}).get("tokens_out", 0) or 0),
            "missing_completion": comp is None,
        })
    rule_rows = S.read_jsonl(export_dir / "labels_rule.jsonl")
    S.write_jsonl(records_dir / "classify.jsonl", clf_rows + rule_rows)
    print(f"[ingest] classify: {len(clf_rows)} model + {len(rule_rows)} rule "
          f"labels, {sum(1 for r in clf_rows if r['parse_failure'])} parse "
          "failures")

    node_hours = _sum_node_hours(summaries)
    analysis = analyse(all_records, clf_rows, rule_rows, doc, node_hours,
                       missing_total, summaries)
    S.write_json(pilot_dir / "analysis.json", analysis)
    print(f"[ingest] analysis -> {pilot_dir / 'analysis.json'}")

    if node_hours:
        _log_cost(all_records, clf_rows, node_hours)
    else:
        print("[cost] no node summaries found; no cost-log line written "
              "(entries are only written when node time was actually spent)")
    return 0


def _sum_node_hours(summaries: list[dict]) -> float | None:
    if not summaries:
        return None
    init = max((s.get("engine_init_seconds", 0.0) for s in summaries),
               default=0.0)
    gen = sum(s.get("generation_wall_seconds", 0.0) for s in summaries)
    total = init + gen
    return round(total / 3600, 4) if total else None


def _log_cost(pred: list[dict], clf: list[dict], node_hours: float) -> None:
    total_out = sum(r["tokens_out"] for r in pred + clf) or 1
    for label, rows in (("prediction", pred), ("classifier", clf)):
        share = sum(r["tokens_out"] for r in rows) / total_out
        append_cost_log(build_cost_entry(
            run_id=f"stage2_pilot/{label}", model=MODEL_LABEL,
            split=SPLIT_LABEL, variant="stage2_d8" if label == "prediction"
            else "stage2_d9",
            n_persons=len({r["canonical_id"] for r in rows}),
            n_calls=len(rows), n_retries=0,
            n_parse_failures=sum(1 for r in rows if r["parse_failure"]),
            tokens_in=sum(r["tokens_in"] for r in rows),
            tokens_out=sum(r["tokens_out"] for r in rows),
            backend="leonardo-batch",
            node_hours=round(node_hours * share, 4),
        ), RESULTS_DIR / "cost_log.jsonl")
        print(f"[cost] {label}: {round(node_hours * share, 4)} node-hours, "
              f"{len(rows):,} calls, $0.00 API")


def analyse(pred: list[dict], clf: list[dict], rule: list[dict],
            export_doc: dict, node_hours: float | None, missing: int,
            summaries: list[dict]) -> dict:
    out: dict = {
        "pilot": PILOT_BANNER, "confirmatory": False,
        "generated_utc": now(),
        "n_items": export_doc["n_items"],
        "n_qa_subjects": export_doc["n_qa_subjects"],
        "excluded_burned_for_qa": export_doc["excluded_burned_for_qa"],
        "n_missing_completions": missing,
        "node_hours_total": node_hours,
        "node_summaries": summaries,
        "accuracy": {}, "lift": {}, "contamination_meter": {},
        "classifier": {}, "per_subject_cost": {},
    }
    for variant in VARIANTS:
        keep = adversarial_keep(pred, variant)
        out["accuracy"][variant] = {}
        for filt, items in (("unfiltered", None), ("adversarial_filtered", keep)):
            block = {}
            for arm in ARMS:
                rows = [r for r in pred if r["arm"] == arm
                        and r["variant"] == variant
                        and (items is None or r["item_id"] in items)]
                block[arm] = accuracy(rows)
            out["accuracy"][variant][filt] = block
        out["accuracy"][variant]["adversarial_filter"] = {
            "rule": "A4.3: drop items zeroinfo_redacted got argmax-correct",
            "n_items_kept": len(keep),
            "items_kept": sorted(keep),
        }
        out["lift"][variant] = {
            "unfiltered": [
                paired_lift(pred, "twin_redacted", "zeroinfo_redacted", variant),
                paired_lift(pred, "twin_redacted", "imposter_redacted", variant),
            ],
            "adversarial_filtered": [
                paired_lift(pred, "twin_redacted", "zeroinfo_redacted", variant,
                            keep),
                paired_lift(pred, "twin_redacted", "imposter_redacted", variant,
                            keep),
            ],
        }
    out["contamination_meter"] = contamination_meter(pred)

    by_subject: dict[str, dict] = {}
    for row in clf:
        entry = by_subject.setdefault(row["canonical_id"],
                                      {"FOLLOW-UP": 0, "NEW-TOPIC": 0,
                                       "parse_failures": 0, "rule": 0})
        if row["label"] is None:
            entry["parse_failures"] += 1
        else:
            entry[row["label"]] += 1
    for row in rule:
        entry = by_subject.setdefault(row["canonical_id"],
                                      {"FOLLOW-UP": 0, "NEW-TOPIC": 0,
                                       "parse_failures": 0, "rule": 0})
        entry["rule"] += 1
    n_clf = len(clf)
    out["classifier"] = {
        "rubric_sha256": export_doc["renderer"]["followup_rubric_sha256"],
        "n_model_cases": n_clf,
        "n_rule_labels": len(rule),
        "parse_failures": sum(1 for r in clf if r["parse_failure"]),
        "parse_failure_rate": round(
            sum(1 for r in clf if r["parse_failure"]) / n_clf, 6)
        if n_clf else None,
        "per_subject": by_subject,
        "sample": classifier_sample(clf),
    }

    total_out = sum(r["tokens_out"] for r in pred + clf) or 1
    for cid in sorted({r["canonical_id"] for r in pred + clf}):
        rows = [r for r in pred + clf if r["canonical_id"] == cid]
        share = sum(r["tokens_out"] for r in rows) / total_out
        out["per_subject_cost"][cid] = {
            "n_calls": len(rows),
            "tokens_in": sum(r["tokens_in"] for r in rows),
            "tokens_out": sum(r["tokens_out"] for r in rows),
            "node_seconds_share": round((node_hours or 0.0) * 3600 * share, 1),
            "cost_usd": 0.0,
        }
    out["total_cost"] = {
        "node_hours": node_hours, "cost_usd": 0.0,
        "n_calls": len(pred) + len(clf),
        "api_calls": 0,
    }
    return out


def classifier_sample(clf: list[dict], n_each: int = 10) -> list[dict]:
    """A seeded 10/10 sample spanning as many subjects as the data allows."""
    rng = random.Random(SAMPLE_SEED)
    picked: list[dict] = []
    for label in (F.FOLLOW_UP, F.NEW_TOPIC):
        pool = sorted([r for r in clf if r["label"] == label],
                      key=lambda r: (r["canonical_id"], r["transcript_id"],
                                     r["turn_idx"]))
        rng.shuffle(pool)
        # Spread across subjects first, then fill.
        seen: set[str] = set()
        chosen: list[dict] = []
        for row in pool:
            if row["canonical_id"] not in seen:
                seen.add(row["canonical_id"])
                chosen.append(row)
            if len(chosen) >= n_each:
                break
        for row in pool:
            if len(chosen) >= n_each:
                break
            if row not in chosen:
                chosen.append(row)
        picked += chosen
    return [{"canonical_id": r["canonical_id"],
             "transcript_id": r["transcript_id"], "turn_idx": r["turn_idx"],
             "label": r["label"], "raw_response": r["raw_response"][:300]}
            for r in picked]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join("" if c is None else str(c)
                                     for c in row) + " |")
    return "\n".join(out)


def _fmt(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


def cmd_report(args) -> int:
    pilot_dir = Path(getattr(args, "pilot_dir", None) or PILOT_DIR)
    analysis = json.loads((pilot_dir / "analysis.json").read_text(
        encoding="utf-8"))
    export_doc = json.loads(
        (pilot_dir / "exports/export_manifest.json").read_text(encoding="utf-8"))
    man = load_manifest(pilot_dir / "manifest.json")
    dev = S.load_dev_subjects(pilot_dir)

    parts = [
        "# Stage 2 pilot report",
        "",
        f"**{PILOT_BANNER}**",
        "",
        f"Generated {analysis['generated_utc']}. "
        f"Contract: SPEC.md v1.6. Not confirmatory; nothing here answers a "
        "pre-registered bar.",
        "",
        "## 1. Dev subjects",
        "",
        _table(["canonical_id", "name", "wiki_status", "shuffle_pos",
                "burned_for_qa", "items", "donor"],
               [[s["canonical_id"], s["canonical_name"], s["wiki_status"],
                 s["shuffle_pos"], "yes" if s.get("burned_for_qa") else "",
                 export_doc["per_subject"].get(s["canonical_id"], {})
                 .get("n_items", 0),
                 export_doc["per_subject"].get(s["canonical_id"], {})
                 .get("donor_name", "")]
                for s in dev["subjects"]]),
        "",
        f"Draw rule (seed {dev['seed']}, drawn {dev['drawn_at']}): "
        f"{dev['rule']}",
        "",
        "### The C00292 burn and replacement",
        "",
    ]
    for rep in dev.get("replacements", []):
        parts += [f"- **{rep['burned_canonical_id']}** ({rep['mode']}): "
                  f"{rep['reason']} Replaced by / joined by "
                  f"**{rep['replaced_by']}**.", ""]
    parts += ["C00292 is excluded from all "
              f"{len(ARMS) * len(VARIANTS)} prediction prompt sets by filtering "
              "on the `burned_for_qa` annotation, and included in the "
              "classifier prompts.", ""]

    parts += ["## 5. Accuracy per arm", ""]
    for variant in VARIANTS:
        for filt in ("unfiltered", "adversarial_filtered"):
            block = analysis["accuracy"][variant][filt]
            parts += [f"### options: {variant}, {filt.replace('_', ' ')}", "",
                      _table(["arm", "N scored", "parse fails",
                              "argmax accuracy", "prob-mass on correct"],
                             [[arm, block[arm]["n"],
                               block[arm]["n_parse_failures"],
                               _fmt(block[arm]["argmax_accuracy"]),
                               _fmt(block[arm]["prob_mass_correct"])]
                              for arm in ARMS]),
                      "",
                      "Note: N is items x subjects that PARSED. With ~"
                      f"{analysis['n_items']} items over "
                      f"{analysis['n_qa_subjects']} subjects this pilot is not "
                      "powered; lift rows below are subject-paired means with "
                      "no significance test, deliberately.", ""]
        for filt in ("unfiltered", "adversarial_filtered"):
            parts += [f"#### lift ({variant}, {filt.replace('_', ' ')})", "",
                      _table(["contrast", "subjects", "mean argmax delta",
                              "mean prob-mass delta"],
                             [[f"{l['better_arm']} - {l['worse_arm']}",
                               l["n_subjects"], _fmt(l["mean_argmax_delta"]),
                               _fmt(l["mean_prob_mass_delta"])]
                              for l in analysis["lift"][variant][filt]]), ""]

    parts += ["## 6. Contamination meter", "",
              "acc(zeroinfo_named) - acc(zeroinfo_redacted), per subject.", ""]
    for variant in VARIANTS:
        parts += [f"### options: {variant}", "",
                  _table(["subject", "delta argmax", "delta prob-mass"],
                         [[cid, _fmt(v[variant]["delta_argmax"]),
                           _fmt(v[variant]["delta_prob_mass"])]
                          for cid, v in
                          sorted(analysis["contamination_meter"].items())]), ""]

    clf = analysis["classifier"]
    parts += ["## 4. Follow-up classifier", "",
              f"Rubric sha256 `{clf['rubric_sha256']}`. "
              f"{clf['n_model_cases']} model cases, {clf['n_rule_labels']} "
              f"rule-labelled turns, parse-failure rate "
              f"{_fmt(clf['parse_failure_rate'], 4)}.", "",
              _table(["subject", "FOLLOW-UP", "NEW-TOPIC", "parse fails",
                      "rule labels"],
                     [[cid, v["FOLLOW-UP"], v["NEW-TOPIC"],
                       v["parse_failures"], v["rule"]]
                      for cid, v in sorted(clf["per_subject"].items())]), ""]

    parts += ["## 7. Cost", "",
              _table(["subject", "calls", "tokens in", "tokens out",
                      "node-seconds share", "$"],
                     [[cid, v["n_calls"], v["tokens_in"], v["tokens_out"],
                       v["node_seconds_share"], "0.00"]
                      for cid, v in
                      sorted(analysis["per_subject_cost"].items())]),
              "",
              f"**Total: {analysis['total_cost']['node_hours']} node-hours, "
              f"{analysis['total_cost']['n_calls']} model calls, "
              f"{analysis['total_cost']['api_calls']} API calls, $0.00.**", ""]

    parts += ["## 9. Provenance", "",
              f"- stage2_render template sha256: "
              f"`{export_doc['renderer']['stage2_render_template_sha256']}`",
              f"- follow-up rubric sha256: "
              f"`{export_doc['renderer']['followup_rubric_sha256']}`",
              f"- max_model_len {MAX_MODEL_LEN}, tp {TP}, temperature "
              f"{TEMPERATURE}, model {MODEL_LABEL}", ""]
    for name, entry in sorted(man.get("jobs", {}).items()):
        parts.append(f"- job `{name}`: slurm "
                     f"{entry.get('slurm_job_ids')}, status "
                     f"{entry.get('status')}, "
                     f"{entry.get('actual_node_hours')} node-hours")
    parts += ["", "### Export manifest digests", "",
              _table(["file", "prompts", "sha256"],
                     [[info.get("prompts_file") or info["meta_file"],
                       info.get("n_prompts"),
                       (info.get("prompts_sha256") or info["meta_sha256"])[:16]]
                      for _, info in sorted(export_doc["files"].items())]), ""]

    parts += ["## 8. Findings for bar-lock (stubs — orchestrator to edit)", "",
              "- Test-interview Q-A eligibility floor: TODO",
              "- Items/subject yield vs H1 power: TODO",
              "- Parse-failure rates: TODO",
              "- Grounding words vs the 2,000-word budget per subject: TODO",
              ""]

    REPORT_PATH = pilot_dir / "PILOT_REPORT.md"
    REPORT_PATH.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"[report] -> {REPORT_PATH}")
    return 0


# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pilot-dir", default=None,
                    help="override results/stage2_pilot (tests only)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("plan").set_defaults(fn=cmd_plan)
    p_exp = sub.add_parser("export")
    p_exp.add_argument("--force", action="store_true")
    p_exp.set_defaults(fn=cmd_export)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    sub.add_parser("bootstrap").set_defaults(fn=cmd_bootstrap)

    p_rec = sub.add_parser("record")
    p_rec.add_argument("--name", required=True)
    p_rec.add_argument("--job-id", default=None)
    p_rec.add_argument("--status", default=None)
    p_rec.add_argument("--node-hours", type=float, default=None)
    p_rec.add_argument("--note", default=None)
    p_rec.add_argument("--anomaly", default=None)
    p_rec.set_defaults(fn=cmd_record)

    p_in = sub.add_parser("ingest")
    p_in.add_argument("--nodedir", required=True)
    p_in.set_defaults(fn=cmd_ingest)

    sub.add_parser("report").set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
