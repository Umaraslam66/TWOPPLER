#!/usr/bin/env python3
"""Confirmatory Stage 2 -- channel 2, the stance judge. WRITTEN, NEVER RUN.

Status at the time of writing (2026-07-28): the API account is out of credits,
so **this file has never been executed**. It is the prepared driver, not a
record of a run. Nothing under ``results/stage2_confirm/judge/`` exists yet.

The pinned configuration, from ``PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md``
instrument parameters 2 and 3, asserted here rather than assumed:

  * ``gemini-3.5-flash`` (AI Studio), temperature 0.0
  * ``thinking_budget=0`` -- the explicit disable. Load-bearing: with hidden
    thinking on, labels were budget-dependent at temperature 0 (the OE-1
    judge-v1 defect). This is not the same as omitting the setting.
  * ``max_output_tokens=512``
  * rubric r2, ``results/stage2_openended/rubric_r2_draft.txt``, sha256
    ``ad050d1a...02464``, checked before a single call is made
  * reply format CENTRAL / LABEL / WHY, read by the exact widened parser from
    ``experiments/oe1_r2_judge.py`` -- imported, not re-implemented, so the two
    can never drift
  * one candidate per stateless call; blind to arm, model and subject. All
    three texts (question, real answer, candidate) go through the same
    GUEST-redaction as OE-1's, via ``stage2_oe1.judge_input``.

The canary
----------
Every judging session starts with a 10-row canary: entries D1-D9 and E1 -- the
first ten rows of the D/E tranche in ``(sheet, position)`` order -- re-judged
and compared label-for-label against the recorded r2 line in
``results/stage2_openended/judge/judgements_r2_regression.jsonl``.

  * **Any** flip halts the session before a single confirmatory row is judged.
    The judge is supposed to be deterministic at temperature 0 with thinking
    off; a flip means the instrument moved under us, and confirmatory labels
    scored by a moved instrument are worthless.
  * If the canary cannot COMPLETE -- a missing file, an unparseable reply, an
    API error, a cost cap reached mid-canary -- the run **refuses to start**.
    An unverified judge is treated exactly like a failed one.
  * The canary runs on OE-1 DEV artefacts. It costs ~10 calls and touches no
    confirmatory row.

Budget
------
One cost-log line per (generation dir, chunk), against the same $15
confirmatory API cap the flash-lite generation half spends from -- the cap is
on ``run_id`` prefix ``stage2_confirm``, so both halves are counted together.
The guard is checked before the canary, between chunks, and periodically inside
a chunk; crossing it stops the run mid-chunk with the partial file intact.

Resumable
---------
Per (generation dir, chunk), joined on ``prompt_sha256`` -- never on ``idx``.
A crash costs only the rows not yet written.

Usage (deliberately not the default)::

    .venv/bin/python experiments/stage2_confirm_judge.py --canary-only
    .venv/bin/python experiments/stage2_confirm_judge.py --go --models gemma
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import oe1_r2_judge as R2  # noqa: E402  (the exact widened CENTRAL parser)
import stage2_oe1 as OE1  # noqa: E402
import stage2_pilot as P1  # noqa: E402

from doppler import stage2_data as S  # noqa: E402
from doppler.costlog import (append_cost_log, build_cost_entry,  # noqa: E402
                             cost_usd_for)

RESULTS_DIR = _ROOT / "results"
CONFIRM_DIR = RESULTS_DIR / "stage2_confirm"
OE_DIR = RESULTS_DIR / "stage2_openended"
JUDGE_DIR = CONFIRM_DIR / "judge"
COST_LOG = RESULTS_DIR / "cost_log.jsonl"

RUN_ID = "stage2_confirm/judge_r2"
CANARY_RUN_ID = "stage2_confirm/judge_r2_canary"
SPLIT = "stage2_confirm_openended"

#: Addendum A parameter 2. Pinned in code; MODEL_NAME in .env is the
#: robustness SCORED model and is deliberately ignored here.
JUDGE_MODEL = OE1.JUDGE_MODEL                      # gemini-3.5-flash
JUDGE_TEMPERATURE = OE1.JUDGE_TEMPERATURE          # 0.0
JUDGE_THINKING_BUDGET = OE1.JUDGE_THINKING_BUDGET  # 0, explicit disable
JUDGE_MAX_OUTPUT_TOKENS = OE1.JUDGE_MAX_OUTPUT_TOKENS  # 512

#: Addendum A parameter 3. The sha is the contract; the file is checked.
RUBRIC_PATH = OE_DIR / "rubric_r2_draft.txt"
RUBRIC_SHA256 = R2.R2_SHA

#: Channel 2 must not be a scored model version (Amendment 3 C2.2/C3).
SCORED_MODELS = ("Gemma-4-31B-it", "gemini-3.5-flash-lite")

GEN_DIRS = {"gemma": "Gemma-4-31B-it", "flashlite": "gemini-3.5-flash-lite"}
CHUNK_ALLOWLIST = ("chunk_01", "chunk_02", "chunk_03", "chunk_04", "chunk_05")

#: Launch plan section c: $15 for the whole confirmatory run, generation and
#: judging together. Anything with this run-id prefix counts against it.
CONFIRM_API_BUDGET_USD = 15.0
CONFIRM_RUN_PREFIX = "stage2_confirm"
BUDGET_CHECK_EVERY = 25

#: The canary. First ten rows of the D/E tranche in (sheet, position) order:
#: D1-D9 then E1.
CANARY_N = 10
CANARY_KEY = OE_DIR / "fresh_tranche_key.json"
CANARY_BASELINE = OE_DIR / "judge" / "judgements_r2_regression.jsonl"
#: Zero tolerance. The judge is deterministic by configuration; one flip is a
#: changed instrument, not noise.
CANARY_MAX_FLIPS = 0

#: One outer retry per call for an unparseable reply, matching OE-1.
PARSE_RETRIES = 1

#: Judge call order: fixed-seed shuffle so arms and models are interleaved and
#: no drift can align with a block of one arm.
JUDGE_ORDER_SEED = OE1.JUDGE_ORDER_SEED

BANNER = ("CONFIRMATORY. Channel 2 (stance judge) labels. Labels only -- no "
          "contrast and no hypothesis verdict is computed here.")


def now() -> str:
    return OE1.now()


def rel(path: Path) -> str:
    return OE1.rel(path)


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


class CanaryFailure(RuntimeError):
    """The judge did not reproduce its recorded labels. Nothing else runs."""


class BudgetExceeded(RuntimeError):
    """The $15 confirmatory cap would be crossed."""


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------


def load_rubric() -> str:
    if not RUBRIC_PATH.exists():
        raise fatal(f"{rel(RUBRIC_PATH)} not found")
    text = RUBRIC_PATH.read_text(encoding="utf-8")
    got = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if got != RUBRIC_SHA256:
        raise fatal(f"{rel(RUBRIC_PATH)} hashes to {got}, Addendum A parameter "
                    f"3 pins {RUBRIC_SHA256}; refusing to run")
    return text


def preflight() -> dict:
    """Every check that costs nothing, before anything that costs money."""
    R2.parser_selftest()
    rubric = load_rubric()
    if JUDGE_MODEL in SCORED_MODELS:
        raise fatal(f"the judge ({JUDGE_MODEL}) is also a scored model; "
                    "C2.2 forbids it")
    if JUDGE_THINKING_BUDGET != 0:
        raise fatal("thinking_budget must be the explicit 0; see the OE-1 "
                    "judge-v1 defect record")
    if JUDGE_TEMPERATURE != 0.0:
        raise fatal("judge temperature must be 0.0")
    for path in (CANARY_KEY, CANARY_BASELINE):
        if not path.exists():
            raise fatal(f"{rel(path)} not found -- the canary cannot run, so "
                        "neither can the judge")
    print("[judge] preflight OK: parser self-test, rubric sha, pinned config, "
          "canary inputs present")
    return {"rubric": rubric}


# ---------------------------------------------------------------------------
# Spend guard (same shape as stage2_confirm_gen_flashlite.SpendGuard)
# ---------------------------------------------------------------------------


def confirmatory_spend_so_far(cost_log: Path = COST_LOG) -> float:
    if not cost_log.exists():
        return 0.0
    total = 0.0
    with cost_log.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if str(entry.get("run_id", "")).startswith(CONFIRM_RUN_PREFIX):
                total += float(entry.get("cost_usd") or 0.0)
    return total


class SpendGuard:
    def __init__(self, prior_usd: float,
                 budget_usd: float = CONFIRM_API_BUDGET_USD) -> None:
        self.prior_usd = float(prior_usd)
        self.budget_usd = float(budget_usd)
        self.this_run_usd = 0.0

    def total(self, pending_in: int = 0, pending_out: int = 0) -> float:
        pending = cost_usd_for(JUDGE_MODEL, pending_in, pending_out) or 0.0
        return self.prior_usd + self.this_run_usd + pending

    def check(self, pending_in: int = 0, pending_out: int = 0) -> None:
        total = self.total(pending_in, pending_out)
        if total > self.budget_usd:
            raise BudgetExceeded(
                f"confirmatory API spend ${total:.4f} would cross the "
                f"${self.budget_usd:.2f} cap (${self.prior_usd:.4f} already "
                "logged); stopping")

    def bank(self, usd) -> None:
        self.this_run_usd += float(usd or 0.0)


# ---------------------------------------------------------------------------
# One judge call
# ---------------------------------------------------------------------------


def make_client(call_cap: int):
    client = OE1._make_client(JUDGE_MODEL, temperature=JUDGE_TEMPERATURE,
                              max_output_tokens=JUDGE_MAX_OUTPUT_TOKENS,
                              call_cap=call_cap,
                              thinking_budget=JUDGE_THINKING_BUDGET)
    if client.model_name != JUDGE_MODEL:
        raise fatal(f"client model is {client.model_name!r}, expected "
                    f"{JUDGE_MODEL!r}")
    if client.temperature != JUDGE_TEMPERATURE:
        raise fatal("client temperature is not 0.0")
    if client.max_output_tokens != JUDGE_MAX_OUTPUT_TOKENS:
        raise fatal("client max_output_tokens is not 512")
    return client


def judge_one(client, rubric: str, question: str, real: str, candidate: str,
              variants) -> dict:
    """One stateless, blind call. Retries once on an unparseable reply."""
    prompt = OE1.judge_input(rubric, question, real, candidate, variants)
    tin_sum = tout_sum = 0
    retried = False
    label = why = central = None
    raw = None
    for attempt in range(PARSE_RETRIES + 1):
        raw, tin, tout = client.generate(prompt)
        tin_sum += tin
        tout_sum += tout
        label, why, central = R2.parse_judge_r2(raw)
        if label is not None:
            break
        retried = attempt < PARSE_RETRIES
    return {
        "label": label, "why": why, "central": central, "raw": raw,
        "retried": retried,
        "why_intact": OE1.why_is_intact(why, tout_sum),
        "output_hit_cap": tout_sum >= JUDGE_MAX_OUTPUT_TOKENS,
        "tokens_in": tin_sum, "tokens_out": tout_sum,
    }


# ---------------------------------------------------------------------------
# The canary
# ---------------------------------------------------------------------------


def canary_entries() -> list[dict]:
    """D1-D9 + E1: the first ten of the D/E tranche in (sheet, position) order."""
    doc = json.loads(CANARY_KEY.read_text(encoding="utf-8"))
    entries = sorted(doc["entries"], key=lambda e: (e["sheet"], e["position"]))
    if len(entries) < CANARY_N:
        raise fatal(f"{rel(CANARY_KEY)} has {len(entries)} entries, the canary "
                    f"needs {CANARY_N}")
    return entries[:CANARY_N]


def canary_baseline() -> dict:
    """entry -> the recorded r2 label this session must reproduce."""
    rows = S.read_jsonl(CANARY_BASELINE)
    baseline = {r["entry"]: r for r in rows}
    for row in rows:
        if row.get("judge_rubric_sha256") not in (None, RUBRIC_SHA256):
            raise fatal(f"{rel(CANARY_BASELINE)} entry {row['entry']} was "
                        "judged under a different rubric sha; it cannot be the "
                        "canary baseline")
    return baseline


def oe1_dev_texts() -> tuple[dict, dict, dict]:
    """The OE-1 dev artefacts the canary re-judges. Dev only; no confirm row."""
    items = {r["item_id"]: r
             for r in S.read_jsonl(OE_DIR / "items_oe1.jsonl")}
    text = {}
    for gen_dir in ("flashlite", "gemma"):
        for arm in OE1.OE.ARMS:
            path = OE_DIR / "gen" / gen_dir / f"completions_{arm}.jsonl"
            if not path.exists():
                continue
            for row in S.read_jsonl(path):
                text[(row["item_id"], row["arm"], gen_dir)] = row["text"]
    ctx = OE1.subject_blocks(OE1.PILOT1_DIR)
    return items, text, ctx


def run_canary(client, rubric: str, guard: SpendGuard) -> dict:
    """Re-judge the ten rows and compare. Any flip, or any failure, halts."""
    entries = canary_entries()
    baseline = canary_baseline()
    items, gen_text, ctx = oe1_dev_texts()
    dir_of_model = {v: k for k, v in GEN_DIRS.items()}

    rows, flips, tin_sum, tout_sum, n_unparsed = [], [], 0, 0, 0
    for entry in entries:
        name = entry["entry"]
        if name not in baseline:
            raise CanaryFailure(
                f"{name} has no recorded r2 label in {rel(CANARY_BASELINE)}; "
                "the canary cannot complete, so the session does not start")
        gen_dir = dir_of_model.get(entry["model"])
        key = (entry["item_id"], entry["arm"], gen_dir)
        if key not in gen_text:
            raise CanaryFailure(
                f"{name}: no OE-1 generation on disk for {key}; the canary "
                "cannot complete")
        try:
            guard.check(tin_sum, tout_sum)
        except BudgetExceeded as exc:
            raise CanaryFailure(f"the budget cap was reached during the "
                                f"canary: {exc}") from exc
        try:
            got = judge_one(client, rubric, items[entry["item_id"]]["question"],
                            items[entry["item_id"]]["real_answer_verbatim"],
                            gen_text[key],
                            ctx[entry["canonical_id"]]["variants"])
        except Exception as exc:  # noqa: BLE001 - any failure fails the canary
            raise CanaryFailure(
                f"{name}: the judge call failed ({type(exc).__name__}: {exc}); "
                "an unverified judge is treated as a failed one") from exc
        tin_sum += got["tokens_in"]
        tout_sum += got["tokens_out"]
        if got["label"] is None:
            n_unparsed += 1
            raise CanaryFailure(
                f"{name}: the reply could not be parsed after a retry; the "
                "canary cannot complete")
        was = baseline[name]["label"]
        stable = got["label"] == was
        if not stable:
            flips.append({"entry": name, "recorded": was,
                          "now": got["label"], "why_now": got["why"]})
        rows.append({"entry": name, "item_id": entry["item_id"],
                     "canonical_id": entry["canonical_id"],
                     "arm": entry["arm"], "model": entry["model"],
                     "recorded_label": was, "label": got["label"],
                     "stable": stable, "central": got["central"],
                     "why": got["why"], "why_intact": got["why_intact"],
                     "retried": got["retried"], "raw": got["raw"],
                     "judge_model": JUDGE_MODEL,
                     "judge_rubric_sha256": RUBRIC_SHA256,
                     "judge_thinking_budget": JUDGE_THINKING_BUDGET,
                     "judge_max_output_tokens": JUDGE_MAX_OUTPUT_TOKENS,
                     "tokens_in": got["tokens_in"],
                     "tokens_out": got["tokens_out"]})
        print(f"[canary] {name:3s} recorded={was:9s} now={got['label']:9s} "
              f"{'OK' if stable else 'FLIP'}")

    JUDGE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    S.write_jsonl(JUDGE_DIR / f"canary_{stamp}.jsonl", rows)
    entry = build_cost_entry(
        run_id=CANARY_RUN_ID, model=JUDGE_MODEL, split=SPLIT,
        variant=f"canary_{stamp}",
        n_persons=len({r["canonical_id"] for r in rows}),
        n_calls=len(rows), n_retries=sum(1 for r in rows if r["retried"]),
        n_parse_failures=n_unparsed, tokens_in=tin_sum, tokens_out=tout_sum,
        backend="gemini")
    append_cost_log(entry, COST_LOG)
    guard.bank(entry["cost_usd"])

    result = {"n": len(rows), "n_flips": len(flips), "flips": flips,
              "passed": len(flips) <= CANARY_MAX_FLIPS,
              "max_flips_allowed": CANARY_MAX_FLIPS,
              "file": rel(JUDGE_DIR / f"canary_{stamp}.jsonl"),
              "cost_usd": entry["cost_usd"], "checked_utc": now()}
    S.write_json(JUDGE_DIR / f"canary_{stamp}_summary.json",
                 {"banner": "Judge canary. Halt-on-flip.", **result})
    if not result["passed"]:
        raise CanaryFailure(
            f"{len(flips)} of {len(rows)} canary rows flipped "
            f"({', '.join(f['entry'] for f in flips)}). The judge is not "
            "reproducing its recorded labels, so confirmatory labels scored "
            "now would be scored by a different instrument. HALTED before any "
            "confirmatory row was judged.")
    print(f"[canary] PASSED: {len(rows)}/{len(rows)} labels reproduced "
          f"(${entry['cost_usd']})")
    return result


# ---------------------------------------------------------------------------
# Confirmatory judging
# ---------------------------------------------------------------------------


def confirm_variants() -> dict:
    """canonical_id -> name variants, for the GUEST redaction of all texts.

    Built from the same pool rows and the same ``name_variants`` the render
    used, so the redaction here is identical to the one the prompts got.
    """
    pool = P1.pool_rows()
    return {cid: P1.name_variants(row) for cid, row in pool.items()}


def chunk_calls(gen_dir: str, chunk: str, items: dict) -> list[dict]:
    path = CONFIRM_DIR / "gen" / gen_dir / f"completions_{chunk}.jsonl"
    if not path.exists():
        return []
    calls = []
    for row in S.read_jsonl(path):
        item = items.get(row["item_id"])
        if item is None:
            raise fatal(f"item {row['item_id']} is not in items_confirm.jsonl")
        calls.append({
            "gen_dir": gen_dir, "chunk": chunk,
            "prompt_sha256": row["prompt_sha256"],
            "item_id": row["item_id"], "canonical_id": row["canonical_id"],
            "arm": row["arm"], "h7_bin": row.get("h7_bin"),
            "model": row["model"], "question": item["question"],
            "real": item["real_answer_verbatim"], "candidate": row["text"],
            "item_type": item.get("item_type"),
        })
    # Interleave arms and items under a fixed seed. The judge never sees the
    # arm, but a block-ordered run would let any drift align with one arm.
    random.Random(JUDGE_ORDER_SEED).shuffle(calls)
    return calls


def judge_chunk(client, rubric: str, gen_dir: str, chunk: str, items: dict,
                variants: dict, guard: SpendGuard, args) -> dict | None:
    calls = chunk_calls(gen_dir, chunk, items)
    if not calls:
        print(f"[judge] {gen_dir}/{chunk}: no generations on disk, skipping")
        return None

    out_path = JUDGE_DIR / f"judgements_{gen_dir}_{chunk}.jsonl"
    sidecar = JUDGE_DIR / f"judge_summary_{gen_dir}_{chunk}.json"
    JUDGE_DIR.mkdir(parents=True, exist_ok=True)
    if args.force:
        out_path.unlink(missing_ok=True)
        sidecar.unlink(missing_ok=True)

    # Resume on prompt_sha256, never on position.
    done = set()
    if out_path.exists():
        want = {c["prompt_sha256"] for c in calls}
        fresh = [r for r in S.read_jsonl(out_path)
                 if r.get("prompt_sha256") in want]
        if len(fresh) != len(S.read_jsonl(out_path)):
            print(f"[judge] {gen_dir}/{chunk}: dropping rows whose "
                  "prompt_sha256 is not in the current completions file")
            S.write_jsonl(out_path, fresh)
        done = {r["prompt_sha256"] for r in fresh}
    todo = [c for c in calls if c["prompt_sha256"] not in done]
    if not todo and sidecar.exists():
        print(f"[judge] {gen_dir}/{chunk}: complete on disk, skipping")
        return json.loads(sidecar.read_text(encoding="utf-8"))
    if done:
        print(f"[judge] {gen_dir}/{chunk}: resuming, {len(done)} done, "
              f"{len(todo)} to go")

    t0 = time.time()
    n_calls = n_retries = n_unparsed = 0
    tin_sum = tout_sum = 0
    with out_path.open("a", encoding="utf-8") as fh:
        for i, call in enumerate(todo, start=1):
            guard.check(tin_sum, tout_sum)
            got = judge_one(client, rubric, call["question"], call["real"],
                            call["candidate"],
                            variants[call["canonical_id"]])
            n_calls += 1
            n_retries += int(got["retried"])
            n_unparsed += int(got["label"] is None)
            tin_sum += got["tokens_in"]
            tout_sum += got["tokens_out"]
            fh.write(json.dumps({
                "gen_dir": gen_dir, "chunk": chunk,
                "prompt_sha256": call["prompt_sha256"],
                "item_id": call["item_id"],
                "canonical_id": call["canonical_id"], "arm": call["arm"],
                "h7_bin": call["h7_bin"], "item_type": call["item_type"],
                "model": call["model"], "label": got["label"],
                "central": got["central"], "why": got["why"],
                "why_intact": got["why_intact"], "retried": got["retried"],
                "output_hit_cap": got["output_hit_cap"], "raw": got["raw"],
                "judge_model": JUDGE_MODEL,
                "judge_rubric_sha256": RUBRIC_SHA256,
                "judge_thinking_budget": JUDGE_THINKING_BUDGET,
                "judge_max_output_tokens": JUDGE_MAX_OUTPUT_TOKENS,
                "tokens_in": got["tokens_in"],
                "tokens_out": got["tokens_out"],
                "judged_utc": now(),
            }) + "\n")
            fh.flush()
            if i % BUDGET_CHECK_EVERY == 0:
                guard.check(tin_sum, tout_sum)
                print(f"[judge] {gen_dir}/{chunk}: {i}/{len(todo)} "
                      f"(${guard.total(tin_sum, tout_sum):.4f} confirm total)")

    rows = S.read_jsonl(out_path)
    entry = build_cost_entry(
        run_id=RUN_ID, model=JUDGE_MODEL, split=SPLIT,
        variant=f"{gen_dir}_{chunk}",
        n_persons=len({r["canonical_id"] for r in rows}),
        n_calls=n_calls + n_retries, n_retries=n_retries,
        n_parse_failures=n_unparsed, tokens_in=tin_sum, tokens_out=tout_sum,
        backend="gemini", resumed=bool(done))
    append_cost_log(entry, COST_LOG)
    guard.bank(entry["cost_usd"])

    labels = {}
    for row in rows:
        labels[str(row["label"])] = labels.get(str(row["label"]), 0) + 1
    per_arm = {}
    for arm in sorted({r["arm"] for r in rows}):
        sub = [r for r in rows if r["arm"] == arm]
        counts = {}
        for row in sub:
            counts[str(row["label"])] = counts.get(str(row["label"]), 0) + 1
        per_arm[arm] = {"n": len(sub), "labels": counts}
    summary = {
        "banner": BANNER, "run_id": RUN_ID, "gen_dir": gen_dir,
        "chunk": chunk, "scored_model": GEN_DIRS[gen_dir],
        "judge_model": JUDGE_MODEL, "temperature": JUDGE_TEMPERATURE,
        "thinking_budget": JUDGE_THINKING_BUDGET,
        "max_output_tokens": JUDGE_MAX_OUTPUT_TOKENS,
        "rubric": rel(RUBRIC_PATH), "rubric_sha256": RUBRIC_SHA256,
        "call_order_seed": JUDGE_ORDER_SEED,
        "blind": "judge sees rubric + question + real + candidate only, all "
                 "GUEST-redacted; never the arm, the model or the subject",
        "n_rows": len(rows), "n_calls_this_process": n_calls,
        "n_retries_this_process": n_retries,
        "n_parse_failures_this_process": n_unparsed,
        "n_why_intact": sum(1 for r in rows if r["why_intact"]),
        "n_central_present": sum(1 for r in rows if r["central"]),
        "n_output_hit_cap": sum(1 for r in rows if r["output_hit_cap"]),
        "labels": labels, "per_arm_labels": per_arm,
        "tokens_in": tin_sum, "tokens_out": tout_sum,
        "cost_usd_this_process": entry["cost_usd"],
        "confirmatory_spend_after_usd": round(guard.total(), 6),
        "confirmatory_budget_usd": guard.budget_usd,
        "no_verdicts_note": "Label counts only. No agreement statistic, no "
                            "contrast and no bar is evaluated here.",
        "runtime_secs": round(time.time() - t0, 1),
        "judged_utc": now(),
    }
    S.write_json(sidecar, summary)
    print(f"[judge] {gen_dir}/{chunk}: {len(rows)} labels, "
          f"${entry['cost_usd']} this process")
    return summary


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--go", action="store_true",
                    help="required. Without it this driver does the free "
                         "preflight and exits without spending anything.")
    ap.add_argument("--canary-only", action="store_true",
                    help="run the 10-row canary and stop")
    ap.add_argument("--models", nargs="*", default=sorted(GEN_DIRS))
    ap.add_argument("--chunks", nargs="*", default=list(CHUNK_ALLOWLIST))
    ap.add_argument("--call-cap", type=int, default=4200,
                    help="hard client-side ceiling on API calls this process")
    ap.add_argument("--force", action="store_true",
                    help="re-judge chunks that already have labels")
    args = ap.parse_args(argv)

    for name in args.models:
        if name not in GEN_DIRS:
            raise fatal(f"{name!r} is not a known generation dir")
    for chunk in args.chunks:
        if chunk not in CHUNK_ALLOWLIST:
            raise fatal(f"{chunk!r} is not in the chunk allowlist")

    ctx = preflight()
    if not (args.go or args.canary_only):
        print("[judge] preflight only. Pass --go to judge, or --canary-only "
              "to verify the judge without judging anything.")
        return 0

    prior = confirmatory_spend_so_far()
    guard = SpendGuard(prior)
    print(f"[judge] confirmatory API spend so far ${prior:.4f} of "
          f"${CONFIRM_API_BUDGET_USD:.2f}")
    guard.check()

    client = make_client(args.call_cap)

    # The canary runs FIRST, every session, without exception.
    try:
        canary = run_canary(client, ctx["rubric"], guard)
    except CanaryFailure as exc:
        print(f"[fatal] CANARY FAILED -- nothing confirmatory was judged.\n"
              f"{exc}", file=sys.stderr)
        return 2
    if args.canary_only:
        print("[judge] --canary-only: stopping after a passed canary.")
        return 0

    items = {r["item_id"]: r
             for r in S.read_jsonl(CONFIRM_DIR / "items_confirm.jsonl")}
    variants = confirm_variants()

    summaries = []
    try:
        for gen_dir in args.models:
            for chunk in args.chunks:
                got = judge_chunk(client, ctx["rubric"], gen_dir, chunk, items,
                                  variants, guard, args)
                if got:
                    summaries.append(got)
    except BudgetExceeded as exc:
        print(f"[fatal] {exc}", file=sys.stderr)
        return 3

    S.write_json(JUDGE_DIR / "judge_run_summary.json", {
        "banner": BANNER, "canary": canary,
        "judge_model": JUDGE_MODEL, "rubric_sha256": RUBRIC_SHA256,
        "chunks": [{"gen_dir": s["gen_dir"], "chunk": s["chunk"],
                    "n_rows": s["n_rows"], "labels": s["labels"]}
                   for s in summaries],
        "confirmatory_spend_usd": round(guard.total(), 6),
        "confirmatory_budget_usd": CONFIRM_API_BUDGET_USD,
        "finished_utc": now()})
    print(f"\n[judge] done. Confirmatory API spend now "
          f"${guard.total():.4f} of ${CONFIRM_API_BUDGET_USD:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
