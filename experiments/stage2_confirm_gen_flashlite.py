#!/usr/bin/env python3
"""Confirmatory Stage 2 -- robustness generations on gemini-3.5-flash-lite.

This is the API half of the confirmatory generation step. The primary model
(Gemma on Leonardo) generates from the same prompts on the node; this driver
generates the secondary, absolute-score-only arm through Google AI Studio.

What is deliberately fixed here, and why:

  * **Model pinned in code.** ``MODEL`` is the literal string, never read from
    ``MODEL_NAME`` in ``.env``. ``GeminiClient`` needs that variable set to
    construct, but the model actually sent is overwritten with the pin and then
    asserted, so an edited ``.env`` cannot silently move the run to another
    model mid-tranche.
  * **Serial calls.** 641 sequential requests sit far under the 1,000 RPM
    client guard in ``doppler.gemini``, so there is nothing to gain from a
    thread pool and a real risk (a 429 storm mid-tranche) from adding one.
  * **One stateless call per prompt.** No chat history, no batching: the same
    shape the pilot was measured on.
  * **Resumable, and reconciled by hash.** Completions are appended as they
    arrive, so a crash at call 450 of 497 costs nothing to recover. Resume
    joins on ``prompt_sha256``, never on ``idx``: a re-render can put a
    different prompt at the same position, so position is not identity. A chunk
    is skipped without a single API call only when its sidecar exists *and*
    every completion still hashes to a prompt in the current file; anything
    else is stale, and stale rows are dropped and regenerated.
  * **Cost logged per chunk, never at the end.** A resumed chunk writes its own
    line with ``resumed=True`` counting only what that process spent, which is
    the cost-log convention: sum the lines sharing a ``run_id``.
  * **Truncation and era violations are reported, not repaired.** A
    truncation-rate gap between arms biases channel 1 and is a pre-written red
    flag in the launch plan's risk table. This script surfaces it loudly and
    changes nothing.

Chunk scope: this driver refuses to touch anything outside ``CHUNK_ALLOWLIST``,
which is every chunk of the confirmatory render (01-05, 1,911 prompts).

Usage::

    .venv/bin/python experiments/stage2_confirm_gen_flashlite.py
    .venv/bin/python experiments/stage2_confirm_gen_flashlite.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import stage2_oe1 as OE1  # noqa: E402  (the machinery this run reuses)

from doppler import counterfactuals as CF  # noqa: E402
from doppler import gemini as G  # noqa: E402
from doppler import oe_render as OE  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402
from doppler.costlog import (append_cost_log, build_cost_entry,  # noqa: E402
                             cost_usd_for)

RESULTS_DIR = _ROOT / "results"
CONFIRM_DIR = RESULTS_DIR / "stage2_confirm"
COST_LOG = RESULTS_DIR / "cost_log.jsonl"

RUN_ID = "stage2_confirm/gen_flashlite"
SPLIT = "stage2_confirm_openended"

#: Pinned in code on purpose. Never read from the environment. See module docs.
MODEL = "gemini-3.5-flash-lite"

#: Frozen open-ended generation parameters (PILOT_SPEC section 1/2, unchanged
#: for the confirmatory run). Every prompt row is checked against these.
TEMPERATURE = 0.0
MAX_OUTPUT_TOKENS = OE.MAX_OUTPUT_TOKENS   # 256, the frozen OE cap
MAX_ANSWER_WORDS = OE.MAX_ANSWER_WORDS     # 150

#: Every chunk of the confirmatory render. Chunks 03-05 were added by the
#: full-89 D7 donor re-fit (commit 334a155) after chunks 01-02 had started
#: generating; the same re-fit also moved 30 imposter_redacted donors inside
#: chunks 01-02. The committed prompt files are the truth, and the resume path
#: below reconciles against them by hash on every run.
CHUNK_ALLOWLIST = ("chunk_01", "chunk_02", "chunk_03", "chunk_04", "chunk_05")

#: Launch plan section c: $15 total confirmatory API cap. Reaching it stops
#: everything mid-chunk and reports; no overage without an owner decision.
CONFIRM_API_BUDGET_USD = 15.0

#: Run-id prefix that counts against that cap.
CONFIRM_RUN_PREFIX = "stage2_confirm"

#: Outer retries on a transient failure, on top of the 5 attempts
#: ``GeminiClient.generate`` already makes internally. Widened from 1x20s after
#: the 2026-07-28 block: the AI Studio account's prepayment credits ran out
#: mid-tranche and every inner attempt returned 429 RESOURCE_EXHAUSTED, so the
#: run needs to survive a longer credit/quota dip before declaring a block.
OUTER_RETRIES = 3
OUTER_BACKOFF_S = 60.0

#: Check the running spend against the cap this often inside a chunk.
BUDGET_CHECK_EVERY = 25

#: Prompt-row fields this driver relies on. A missing one is a stop, not a
#: guess: the constraint on this job is to report a surprising prompt format
#: rather than adapt to it.
REQUIRED_PROMPT_FIELDS = (
    "idx", "chunk", "canonical_id", "item_id", "arm", "prompt",
    "prompt_sha256", "max_output_tokens", "temperature", "model",
)


def now() -> str:
    return OE1.now()


def rel(path: Path) -> str:
    return OE1.rel(path)


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def load_chunk(prompts_dir: Path, chunk: str) -> list[dict]:
    """Read one prompt chunk and verify it is the file this driver expects.

    Every check here is a STOP, never a repair. If the render step ever emits a
    different shape, a different model pin, or a different token cap, that is an
    upstream change the owner has to see -- silently coercing it would put
    un-comparable rows in the same results directory.
    """
    path = prompts_dir / f"{chunk}.jsonl"
    if not path.exists():
        raise fatal(f"{rel(path)} not found")
    rows = S.read_jsonl(path)
    if not rows:
        raise fatal(f"{rel(path)} is empty")
    for i, row in enumerate(rows):
        missing = [f for f in REQUIRED_PROMPT_FIELDS if f not in row]
        if missing:
            raise fatal(f"{rel(path)} row {i}: missing field(s) {missing}; "
                        "the prompt format is not what this driver was written "
                        "against -- stopping instead of adapting")
        if row["chunk"] != chunk:
            raise fatal(f"{rel(path)} row {i}: chunk field {row['chunk']!r} "
                        f"does not match the file name {chunk!r}")
        if row["model"] != MODEL:
            raise fatal(f"{rel(path)} row {i}: prompt names model "
                        f"{row['model']!r}, this driver is pinned to {MODEL!r}")
        if float(row["temperature"]) != TEMPERATURE:
            raise fatal(f"{rel(path)} row {i}: prompt temperature "
                        f"{row['temperature']} != frozen {TEMPERATURE}")
        if int(row["max_output_tokens"]) != MAX_OUTPUT_TOKENS:
            raise fatal(f"{rel(path)} row {i}: prompt max_output_tokens "
                        f"{row['max_output_tokens']} != frozen "
                        f"{MAX_OUTPUT_TOKENS}")
        if R.sha256(row["prompt"]) != row["prompt_sha256"]:
            raise fatal(f"{rel(path)} row {i}: prompt text does not hash to its "
                        "recorded prompt_sha256; the file has been edited")
    idxs = [int(r["idx"]) for r in rows]
    if len(set(idxs)) != len(idxs):
        raise fatal(f"{rel(path)}: idx values are not unique")
    return rows


def load_items(out_dir: Path) -> dict:
    """item_id -> item row. ``test_date`` is what the era check needs."""
    path = out_dir / "items_confirm.jsonl"
    if not path.exists():
        raise fatal(f"{rel(path)} not found")
    items = {r["item_id"]: r for r in S.read_jsonl(path)}
    if not items:
        raise fatal(f"{rel(path)} is empty")
    return items


# ---------------------------------------------------------------------------
# Spend guard
# ---------------------------------------------------------------------------


def confirmatory_spend_so_far(cost_log: Path) -> float:
    """USD already logged against any ``stage2_confirm*`` run id."""
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


class BudgetExceeded(RuntimeError):
    """The $15 confirmatory API cap would be crossed. Stop and report."""


class SpendGuard:
    """Running total of confirmatory API spend, checked mid-chunk."""

    def __init__(self, prior_usd: float, budget_usd: float) -> None:
        self.prior_usd = float(prior_usd)
        self.budget_usd = float(budget_usd)
        self.this_run_usd = 0.0

    def total(self, pending_in: int = 0, pending_out: int = 0) -> float:
        pending = cost_usd_for(MODEL, pending_in, pending_out) or 0.0
        return self.prior_usd + self.this_run_usd + pending

    def check(self, pending_in: int = 0, pending_out: int = 0) -> None:
        total = self.total(pending_in, pending_out)
        if total > self.budget_usd:
            raise BudgetExceeded(
                f"confirmatory API spend ${total:.4f} would cross the "
                f"${self.budget_usd:.2f} cap "
                f"(${self.prior_usd:.4f} already logged, "
                f"${self.this_run_usd + (cost_usd_for(MODEL, pending_in, pending_out) or 0.0):.4f} "
                "this run); stopping mid-chunk")

    def bank(self, usd: float) -> None:
        self.this_run_usd += float(usd or 0.0)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def make_client(call_cap: int):
    """A flash-lite client with the model pinned in code, not in ``.env``.

    ``thinking_budget`` stays ``None`` -- omitted entirely -- because that is
    what the flash-lite generation path was built and measured on. Sending an
    explicit disable would be a different configuration from OE-1's.
    """
    client = OE1._make_client(MODEL, temperature=TEMPERATURE,
                              max_output_tokens=MAX_OUTPUT_TOKENS,
                              call_cap=call_cap, thinking_budget=None)
    if client.model_name != MODEL:
        raise fatal(f"client model is {client.model_name!r}, expected {MODEL!r}")
    if client.max_output_tokens != MAX_OUTPUT_TOKENS:
        raise fatal("client max_output_tokens is not the frozen OE cap")
    if client.temperature != TEMPERATURE:
        raise fatal("client temperature is not 0.0")
    return client


def _is_transient(err: Exception) -> bool:
    if isinstance(err, G.genai_errors.APIError):
        return G._is_retryable(err)
    return isinstance(err, G._RETRYABLE_CONN_ERRORS)


def generate_once(client, prompt: str) -> tuple[tuple[str, int, int], int]:
    """One generation. Returns ``((text, tin, tout), n_outer_retries)``.

    ``GeminiClient.generate`` already retries transient errors internally; this
    adds one more full attempt after a longer pause for the case where the whole
    internal ladder was exhausted by a bad minute on the API side. A
    non-transient error (bad key, wrong model, quota gone) is raised at once so
    the run stops fast rather than burning the tranche.
    """
    for attempt in range(OUTER_RETRIES + 1):
        try:
            return client.generate(prompt), attempt
        except G.CallCapExceeded:
            raise
        except Exception as err:  # noqa: BLE001 - re-raised unless transient
            if attempt < OUTER_RETRIES and _is_transient(err):
                print(f"[gen] transient error, outer retry in "
                      f"{OUTER_BACKOFF_S:.0f}s: {type(err).__name__}: {err}",
                      file=sys.stderr)
                time.sleep(OUTER_BACKOFF_S)
                continue
            raise
    raise AssertionError("unreachable")


def build_row(prompt_row: dict, item: dict, text: str, tin: int,
              tout: int) -> dict:
    """One completion row in the ``cmd_gen_flashlite`` schema.

    ``chunk`` and ``idx`` are carried through on top of that schema: the
    confirmatory run is chunked, and ``idx`` is the key the node-side
    completions join on. Everything else is field-for-field the pilot's.
    """
    words = R.word_count(text)
    return {
        "chunk": prompt_row["chunk"],
        "idx": int(prompt_row["idx"]),
        "item_id": prompt_row["item_id"],
        "canonical_id": prompt_row["canonical_id"],
        "arm": prompt_row["arm"],
        "model": MODEL,
        "temperature": TEMPERATURE,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "prompt_sha256": prompt_row["prompt_sha256"],
        "text": text,
        "answer_words": words,
        "over_word_cap": words > MAX_ANSWER_WORDS,
        "truncated": OE1.looks_truncated(text, tout),
        "era_violations": CF.era_violations(text, item["test_date"]),
        "tokens_in": tin,
        "tokens_out": tout,
        "generated_utc": now(),
    }


def reconcile_done(path: Path, by_sha: dict) -> tuple[list[dict], list[dict]]:
    """Split existing completions into (fresh, stale) against the prompt file.

    **The join key is ``prompt_sha256``, never ``idx``.** ``idx`` is a position
    in a rendered file, and a re-render can put a different prompt at the same
    position -- which is exactly what the full-89 D7 donor re-fit did to 30
    ``imposter_redacted`` rows in chunks 01-02, mid-run. The hash names the
    prompt that was actually sent, so a completion whose hash is absent from the
    current prompt file was generated from a prompt that no longer exists. That
    row is stale: it is dropped and regenerated, never joined by position.

    Self-healing on purpose: any future re-render is absorbed the same way, and
    a chunk that is already sha-clean costs nothing to re-check.
    """
    if not path.exists():
        return [], []
    rows = S.read_jsonl(path)
    fresh, stale, seen = [], [], set()
    for row in rows:
        sha = row.get("prompt_sha256")
        if sha in by_sha and sha not in seen:
            seen.add(sha)
            fresh.append(row)
        else:
            stale.append(row)
    return fresh, stale


def per_arm_stats(rows: list[dict]) -> dict:
    arms = sorted({r["arm"] for r in rows})
    out = {}
    for arm in arms:
        sub = [r for r in rows if r["arm"] == arm]
        out[arm] = {
            "n": len(sub),
            "n_truncated": sum(1 for r in sub if r["truncated"]),
            "n_era_violations": sum(1 for r in sub if r["era_violations"]),
            "n_over_word_cap": sum(1 for r in sub if r["over_word_cap"]),
            "n_empty": sum(1 for r in sub if not (r["text"] or "").strip()),
            "tokens_in": sum(int(r["tokens_in"]) for r in sub),
            "tokens_out": sum(int(r["tokens_out"]) for r in sub),
            "truncation_rate": round(
                sum(1 for r in sub if r["truncated"]) / len(sub), 4),
        }
    return out


def run_chunk(chunk: str, prompts_dir: Path, items: dict, gen_dir: Path,
              client, guard: SpendGuard, args) -> dict:
    """Generate one chunk. Returns its summary dict (also written as sidecar)."""
    prompt_rows = load_chunk(prompts_dir, chunk)
    by_sha = {r["prompt_sha256"]: r for r in prompt_rows}
    if len(by_sha) != len(prompt_rows):
        raise fatal(f"{chunk}: prompt_sha256 is not unique within the chunk; "
                    "the hash cannot be used as the join key -- stopping")
    out_path = gen_dir / f"completions_{chunk}.jsonl"
    sidecar = gen_dir / f"gen_summary_{chunk}.json"

    if args.force:
        out_path.unlink(missing_ok=True)
        sidecar.unlink(missing_ok=True)

    # Reconcile by hash BEFORE trusting the sidecar: a sidecar written before a
    # re-render says "complete" about prompts that have since changed.
    fresh, stale = reconcile_done(out_path, by_sha)
    if stale:
        print(f"[gen-flashlite] {chunk}: {len(stale)} STALE row(s) -- their "
              "prompt_sha256 is absent from the current prompt file; dropping "
              "and regenerating from the current prompts")
        S.write_jsonl(out_path, fresh)
        sidecar.unlink(missing_ok=True)

    done_sha = {r["prompt_sha256"] for r in fresh}
    todo = [r for r in prompt_rows if r["prompt_sha256"] not in done_sha]
    resumed = bool(done_sha)

    if not todo and sidecar.exists():
        summary = json.loads(sidecar.read_text(encoding="utf-8"))
        print(f"[gen-flashlite] {chunk}: complete and sha-clean on disk "
              f"({len(fresh)} rows), skipping -- no API calls")
        summary["skipped"] = True
        summary["n_stale_dropped"] = 0
        return summary
    if resumed:
        print(f"[gen-flashlite] {chunk}: resuming, {len(fresh)} sha-clean rows "
              f"already on disk, {len(todo)} to go")

    n_calls = n_retries = 0
    tin_sum = tout_sum = 0
    t0 = time.time()
    started_retries = client.n_retries
    try:
        with out_path.open("a", encoding="utf-8") as fh:
            for i, prompt_row in enumerate(todo, start=1):
                guard.check(tin_sum, tout_sum)
                (text, tin, tout), outer = generate_once(
                    client, prompt_row["prompt"])
                n_calls += 1
                n_retries += outer
                tin_sum += tin
                tout_sum += tout
                item = items.get(prompt_row["item_id"])
                if item is None:
                    raise fatal(f"item {prompt_row['item_id']} not in "
                                "items_confirm.jsonl")
                fh.write(json.dumps(
                    build_row(prompt_row, item, text, tin, tout)) + "\n")
                fh.flush()
                if i % BUDGET_CHECK_EVERY == 0:
                    guard.check(tin_sum, tout_sum)
                    rate = i / max(time.time() - t0, 1e-9) * 60.0
                    print(f"[gen-flashlite] {chunk}: {i}/{len(todo)} "
                          f"(~{rate:.0f}/min, "
                          f"${guard.total(tin_sum, tout_sum):.4f} confirm total)")
    finally:
        n_retries += max(client.n_retries - started_retries, 0)

    rows = S.read_jsonl(out_path)
    if len(rows) != len(prompt_rows):
        raise fatal(f"{rel(out_path)} has {len(rows)} rows, expected "
                    f"{len(prompt_rows)}")
    got = {r["prompt_sha256"] for r in rows}
    if got != set(by_sha):
        raise fatal(f"{rel(out_path)}: prompt_sha256 set does not match the "
                    f"chunk ({len(set(by_sha) - got)} prompts unanswered, "
                    f"{len(got - set(by_sha))} answers with no prompt)")

    entry = build_cost_entry(
        run_id=RUN_ID, model=MODEL, split=SPLIT, variant=chunk,
        n_persons=len({r["canonical_id"] for r in rows}),
        n_calls=n_calls, n_retries=n_retries,
        # No parsing happens in generation, so the analogue of a parse failure
        # is an empty reply -- the launch plan's risk-table row 1 counter.
        n_parse_failures=sum(1 for r in (rows[len(rows) - n_calls:]
                                         if n_calls else [])
                             if not (r["text"] or "").strip()),
        tokens_in=tin_sum, tokens_out=tout_sum,
        backend="gemini", resumed=resumed)
    if not args.skip_cost:
        append_cost_log(entry, COST_LOG)
    guard.bank(entry["cost_usd"])

    stats = per_arm_stats(rows)
    summary = {
        "banner": "CONFIRMATORY. Robustness (secondary) generations; absolute "
                  "scores from this model are secondary per C3.",
        "run_id": RUN_ID, "chunk": chunk, "model": MODEL,
        "temperature": TEMPERATURE, "max_output_tokens": MAX_OUTPUT_TOKENS,
        "max_answer_words": MAX_ANSWER_WORDS,
        "n_rows": len(rows), "n_calls_this_process": n_calls,
        "n_retries_this_process": n_retries, "resumed": resumed,
        "n_stale_dropped": len(stale),
        "sha_verified_against_prompt_file": True,
        "tokens_in": tin_sum, "tokens_out": tout_sum,
        "cost_usd_this_process": entry["cost_usd"],
        "cost_logged": not args.skip_cost,
        "confirmatory_spend_after_usd": round(guard.total(), 6),
        "confirmatory_budget_usd": guard.budget_usd,
        "n_truncated": sum(1 for r in rows if r["truncated"]),
        "n_era_violations": sum(1 for r in rows if r["era_violations"]),
        "n_over_word_cap": sum(1 for r in rows if r["over_word_cap"]),
        "n_empty": sum(1 for r in rows if not (r["text"] or "").strip()),
        "per_arm": stats,
        "runtime_secs": round(time.time() - t0, 1),
        "generated_utc": now(),
    }
    S.write_json(sidecar, summary)
    print(f"[gen-flashlite] {chunk}: {len(rows)} rows, "
          f"{summary['n_truncated']} truncated, "
          f"{summary['n_era_violations']} with era violations, "
          f"${entry['cost_usd']} this process")
    return summary


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


#: OE-1's flash-lite baseline: 85 generations, zero truncations, one era
#: violation (zeroinfo_named). Read from
#: results/stage2_openended/gen/flashlite/gen_summary.json.
OE1_BASELINE = {"n": 85, "n_truncated": 0, "n_era_violations": 1}


def report(summaries: list[dict]) -> None:
    rows: list[dict] = []
    for path in sorted({Path(s["_path"]) for s in summaries if "_path" in s}):
        rows.extend(S.read_jsonl(path))
    stats = per_arm_stats(rows)
    chunks = ", ".join(s["chunk"] for s in summaries)
    n_stale = sum(int(s.get("n_stale_dropped") or 0) for s in summaries)
    print(f"\n=== confirmatory robustness generations ({chunks}) ===")
    if n_stale:
        print(f"{n_stale} stale row(s) were dropped and regenerated after the "
              "full-89 D7 donor re-fit changed their prompts.")
    print(f"{'arm':22s} {'n':>5s} {'trunc':>6s} {'trunc%':>7s} "
          f"{'era':>5s} {'>150w':>6s} {'empty':>6s}")
    for arm, s in stats.items():
        print(f"{arm:22s} {s['n']:5d} {s['n_truncated']:6d} "
              f"{100 * s['truncation_rate']:6.1f}% {s['n_era_violations']:5d} "
              f"{s['n_over_word_cap']:6d} {s['n_empty']:6d}")
    tot_trunc = sum(s["n_truncated"] for s in stats.values())
    tot_era = sum(s["n_era_violations"] for s in stats.values())
    print(f"{'TOTAL':22s} {len(rows):5d} {tot_trunc:6d} "
          f"{100 * tot_trunc / max(len(rows), 1):6.1f}% {tot_era:5d} "
          f"{sum(s['n_over_word_cap'] for s in stats.values()):6d} "
          f"{sum(s['n_empty'] for s in stats.values()):6d}")
    print(f"\nOE-1 flash-lite baseline: {OE1_BASELINE['n']} gens, "
          f"{OE1_BASELINE['n_truncated']} truncated, "
          f"{OE1_BASELINE['n_era_violations']} era violation(s).")
    if stats:
        rates = {a: s["truncation_rate"] for a, s in stats.items()}
        gap = max(rates.values()) - min(rates.values())
        hi = max(rates, key=rates.get)
        lo = min(rates, key=rates.get)
        print(f"Per-arm truncation-rate gap: {gap:.4f} "
              f"({hi} {rates[hi]:.4f} vs {lo} {rates[lo]:.4f}).")
        if tot_trunc > 0:
            print("!! RED FLAG (launch plan risk table): truncation is "
                  "non-zero against an OE-1 baseline of 0. Reported, NOT "
                  "fixed -- an arm-level truncation gap biases channel 1 and "
                  "is an owner decision.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", default=str(CONFIRM_DIR))
    ap.add_argument("--chunks", nargs="+", default=list(CHUNK_ALLOWLIST),
                    help="chunks to generate; must be inside the allowlist")
    ap.add_argument("--budget-usd", type=float, default=CONFIRM_API_BUDGET_USD)
    ap.add_argument("--call-cap", type=int, default=0,
                    help="hard API-call ceiling; 0 = 3x the prompts to run")
    ap.add_argument("--force", action="store_true",
                    help="regenerate chunks that are already complete")
    ap.add_argument("--skip-cost", action="store_true",
                    help="do not append to the cost log (debugging only)")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate inputs, project cost, make no API call")
    args = ap.parse_args(argv)

    bad = [c for c in args.chunks if c not in CHUNK_ALLOWLIST]
    if bad:
        raise fatal(f"chunk(s) {bad} are outside this driver's allowlist "
                    f"{list(CHUNK_ALLOWLIST)}; later chunks belong to another "
                    "process and must not be touched from here")

    out_dir = Path(args.out_dir)
    prompts_dir = out_dir / "prompts"
    gen_dir = out_dir / "gen" / "flashlite"
    gen_dir.mkdir(parents=True, exist_ok=True)
    items = load_items(out_dir)

    chunks = {c: load_chunk(prompts_dir, c) for c in args.chunks}
    n_prompts = sum(len(v) for v in chunks.values())
    prior = confirmatory_spend_so_far(COST_LOG)
    guard = SpendGuard(prior, args.budget_usd)

    print(f"[gen-flashlite] {RUN_ID}")
    print(f"[gen-flashlite] model {MODEL} (pinned in code), temp "
          f"{TEMPERATURE}, max_output_tokens {MAX_OUTPUT_TOKENS}, serial")
    for c, v in chunks.items():
        print(f"[gen-flashlite]   {c}: {len(v)} prompts")
    print(f"[gen-flashlite] {n_prompts} prompts total; confirmatory spend so "
          f"far ${prior:.4f} of ${args.budget_usd:.2f}")

    # Projection: input from the prompts' own token estimates, output from
    # OE-1's measured per-call mean (12,751 out over 85 calls = 150/call).
    # Only an order-of-magnitude sanity check before spending anything.
    proj_in = sum(int(r.get("prompt_tokens_est") or 0)
                  for v in chunks.values() for r in v)
    proj_out = int(n_prompts * (12751 / 85))
    proj = cost_usd_for(MODEL, proj_in, proj_out) or 0.0
    print(f"[gen-flashlite] projected ~${proj:.2f} "
          f"({proj_in:,} in / {proj_out:,} out); cap ${args.budget_usd:.2f}")
    if prior + proj > args.budget_usd:
        raise fatal(f"projected total ${prior + proj:.2f} already exceeds the "
                    f"${args.budget_usd:.2f} confirmatory API cap; stopping "
                    "before the first call")

    if args.dry_run:
        print("[gen-flashlite] dry run: inputs validated, no API call made")
        return 0

    call_cap = args.call_cap or (n_prompts * 3 + 50)
    client = make_client(call_cap)

    summaries = []
    try:
        for chunk in args.chunks:
            summary = run_chunk(chunk, prompts_dir, items, gen_dir, client,
                                guard, args)
            summary["_path"] = str(gen_dir / f"completions_{chunk}.jsonl")
            summaries.append(summary)
    except BudgetExceeded as err:
        print(f"[fatal] {err}", file=sys.stderr)
        print("[gen-flashlite] partial completions are on disk and resumable; "
              "no chunk sidecar was written for the unfinished chunk.",
              file=sys.stderr)
        return 2

    report(summaries)
    spent = sum(float(s.get("cost_usd_this_process") or 0.0)
                for s in summaries if not s.get("skipped"))
    print(f"\n[gen-flashlite] this process spent ${spent:.4f}; confirmatory "
          f"total now ${guard.total():.4f} of ${args.budget_usd:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
