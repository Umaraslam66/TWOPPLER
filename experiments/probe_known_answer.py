"""KNOWN-ANSWER PROBE (declared DIAGNOSTIC, PREREGISTRATION_AMENDMENT_1.md A7).

NOT a confirmatory experiment and NOT an outcome claim. Within-scale prediction
stays disallowed as an outcome under the original registration; this run exists
only to bound the constructor: if a twin seeded with five of a person's own TIPI
answers still cannot predict the other five, the small cross-domain gate lift
(+0.085 primary / +0.095 secondary) reflects a weak constructor rather than an
unusually hard task.

Design (fixed by A7 + the run spec):

* Persons: the frozen GATE set (positions 21-520 of the seed-42 draw of 520),
  reused verbatim from ``doppler.gym.pilot_and_gate_ids``.
* Twin prompt: the SAME demographics rendering as the gate baseline, plus a
  block of five TIPI items presented as already-answered questions (the
  person's true 1-7 answers), then the v2 probability-distribution elicitation
  for one held-out TIPI item. No interest items ever enter a probe prompt.
* Counterbalanced folds, both directions run for every person:
    - fold ``A2B``: seed TIPI1-5  -> predict TIPI6-10
    - fold ``B2A``: seed TIPI6-10 -> predict TIPI1-5
  TIPI's same-trait pairs are (1,6) (2,7) (3,8) (4,9) (5,10), so every predicted
  item has its own trait partner sitting in the seed. Each person therefore
  contributes exactly one prediction per TIPI item: 10 per person, 5,000 total.
* Baseline: demographics-only, identical items, identical v2 elicitation. That
  is byte-for-byte the gate's baseline arm, so the gate's Gemma-4 baseline
  records are reused (verified byte-identical by ``--verify-baseline``).

Everything downstream (parser, MAE-by-expected-value, exclusion rule, paired
statistics) is the untouched v2 machinery imported from ``src/doppler``.

Usage:
    uv run python experiments/probe_known_answer.py --verify-ids
    uv run python experiments/probe_known_answer.py --verify-baseline results/<gate_dir>
    uv run python experiments/probe_known_answer.py --export results/probe_known_answer/prompts_v2.jsonl
    uv run python experiments/probe_known_answer.py --ingest <completions.jsonl> \\
        --baseline-from results/<gate_dir> --node-hours 0.09
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402
from doppler.data import (  # noqa: E402
    TIPI_ITEMS,
    Codebook,
    clean_riasec,
    load_codebook,
    load_riasec,
    person_record,
)
from doppler.gym import pilot_and_gate_ids  # noqa: E402
from doppler.prompts import (  # noqa: E402
    VARIANT_MAX_OUTPUT_TOKENS,
    build_profile,
    build_prompt,
)
from doppler.scoring import parse_response, summarize  # noqa: E402

DATA_DIR = _ROOT / "data"
RESULTS_DIR = _ROOT / "results"

VARIANT = "v2"
PROBE_K = 0  # no interest items ever enter a probe prompt

#: TIPI same-trait pairs (each Big-Five trait is one normal + one reversed item).
TIPI_PAIRS: tuple[tuple[str, str], ...] = tuple(
    (f"TIPI{i}", f"TIPI{i + 5}") for i in range(1, 6)
)

FOLD_A_ITEMS: tuple[str, ...] = tuple(f"TIPI{i}" for i in range(1, 6))
FOLD_B_ITEMS: tuple[str, ...] = tuple(f"TIPI{i}" for i in range(6, 11))

#: fold name -> (seed items, predicted items). Both directions always run.
FOLDS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "A2B": (FOLD_A_ITEMS, FOLD_B_ITEMS),
    "B2A": (FOLD_B_ITEMS, FOLD_A_ITEMS),
}

SEED_BLOCK_HEADER = "HOW I RATED MYSELF ON SOME PERSONALITY STATEMENTS"


@dataclass(frozen=True)
class ProbeTask:
    """One held-out within-scale prediction under one fold direction.

    Field names match :class:`doppler.gym.Task` (``tipi_code`` etc.) so the
    existing export/record helpers work unchanged.
    """

    person_id: int
    arm: str
    fold: str
    tipi_code: str
    tipi_text: str
    true_answer: int
    seed_codes: tuple[str, ...]
    prompt: str


# ---------------------------------------------------------------------------
# Fold construction
# ---------------------------------------------------------------------------


def fold_spec(fold: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return ``(seed_codes, predict_codes)`` for a fold name."""
    if fold not in FOLDS:
        raise ValueError(f"fold must be one of {sorted(FOLDS)}, got {fold!r}")
    return FOLDS[fold]


def assert_folds_wellformed() -> None:
    """Structural guarantees A7 demands of the fold design.

    1. Seed and predicted sets are disjoint (no item predicts itself).
    2. Together they cover all 10 TIPI items exactly once.
    3. Every predicted item's same-trait partner is in the seed.
    4. The two directions together predict each item exactly once per person.
    """
    predicted_counts: dict[str, int] = {code: 0 for code in TIPI_ITEMS}
    partner = {}
    for a, b in TIPI_PAIRS:
        partner[a] = b
        partner[b] = a

    for fold, (seed, predict) in FOLDS.items():
        seed_set, predict_set = set(seed), set(predict)
        if seed_set & predict_set:
            raise AssertionError(f"fold {fold}: seed and predicted sets overlap")
        if seed_set | predict_set != set(TIPI_ITEMS):
            raise AssertionError(f"fold {fold}: seed+predicted != all 10 TIPI items")
        if len(seed) != 5 or len(predict) != 5:
            raise AssertionError(f"fold {fold}: folds must be 5/5")
        for code in predict:
            if partner[code] not in seed_set:
                raise AssertionError(
                    f"fold {fold}: predicted {code} has no same-trait pair in the seed"
                )
            predicted_counts[code] += 1

    bad = {c: n for c, n in predicted_counts.items() if n != 1}
    if bad:
        raise AssertionError(
            f"across both directions each item must be predicted exactly once; got {bad}"
        )


# ---------------------------------------------------------------------------
# Leakage guards (probe-specific; gym's guards assume NO TIPI in the profile)
# ---------------------------------------------------------------------------


def assert_no_self_leak(
    prompt: str, seed_codes: tuple[str, ...], tipi_code: str,
    tipi_text: str, true_answer: int, codebook: Codebook,
) -> None:
    """The predicted item never appears in its own seed set, in any form."""
    if tipi_code in seed_codes:
        raise AssertionError(f"{tipi_code} is in its own seed set {seed_codes}")
    for code in seed_codes:
        if codebook.tipi_items[code] == tipi_text:
            raise AssertionError(f"seed item {code} has the predicted item's text")
    # The questioned statement appears exactly once in the whole prompt (in
    # YOUR TASK), and its recorded answer is never attached to it.
    if prompt.count(tipi_text) != 1:
        raise AssertionError(
            f"predicted item {tipi_code} text appears {prompt.count(tipi_text)} "
            "times in the prompt; must be exactly once"
        )
    for attached in (f"{tipi_text} -> {true_answer}",
                     f'{tipi_text}" -> {true_answer}',
                     f"{tipi_text}: {true_answer}"):
        if attached in prompt:
            raise AssertionError(
                "predicted item's answer is attached to it in the prompt")


def assert_no_interest_leak(prompt: str, record: dict) -> None:
    """No interest item text or interests block ever enters a probe prompt."""
    if "HOW I RATED MY INTEREST" in prompt or "HOW I FEEL ABOUT" in prompt:
        raise AssertionError("interest block present in a probe prompt")
    for entry in record["interests"].values():
        if entry["text"] and entry["text"] in prompt:
            raise AssertionError("interest item text leaked into a probe prompt")


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _tipi_scale_line(codebook: Codebook) -> str:
    anchors = codebook.scales["tipi"]["anchors"]
    return ", ".join(f"{code}={anchors[code]}" for code in sorted(anchors))


def build_seed_block(
    record: dict, codebook: Codebook, seed_codes: tuple[str, ...]
) -> str:
    """Render five already-answered TIPI items with the person's true answers."""
    lines = [SEED_BLOCK_HEADER, f"(Scale: {_tipi_scale_line(codebook)})"]
    for code in seed_codes:
        text = codebook.tipi_items[code]
        answer = int(record["tipi"][code]["answer"])
        lines.append(f'- "I see myself as: {text}" -> {answer}')
    return "\n".join(lines)


def build_probe_tasks(
    record: dict, codebook: Codebook, arm: str = "twin", variant: str = VARIANT
) -> list[ProbeTask]:
    """All 10 probe predictions for one person (5 per fold direction).

    ``arm="baseline"`` builds the demographics-only counterpart of exactly the
    same 10 (person, item) predictions -- byte-identical to the gate's baseline
    prompts, which is what makes the gate baseline reusable here.
    """
    if arm not in ("twin", "baseline"):
        raise ValueError(f"arm must be twin/baseline, got {arm!r}")

    demographics = build_profile(record, codebook, include_interests=False)
    tasks: list[ProbeTask] = []

    for fold in ("A2B", "B2A"):
        seed_codes, predict_codes = fold_spec(fold)
        if arm == "twin":
            profile = demographics + "\n\n" + build_seed_block(
                record, codebook, seed_codes)
        else:
            profile = demographics

        for code in predict_codes:
            text = codebook.tipi_items[code]
            true_answer = int(record["tipi"][code]["answer"])
            prompt = build_prompt(profile, code, codebook, variant=variant)
            if arm == "twin":
                assert_no_self_leak(prompt, seed_codes, code, text, true_answer,
                                    codebook)
            assert_no_interest_leak(prompt, record)
            tasks.append(ProbeTask(
                person_id=int(record["person_id"]),
                arm=arm,
                fold=fold,
                tipi_code=code,
                tipi_text=text,
                true_answer=true_answer,
                seed_codes=seed_codes,
                prompt=prompt,
            ))
    return tasks


# ---------------------------------------------------------------------------
# Data / task assembly
# ---------------------------------------------------------------------------


def load_gate_people() -> tuple[list[dict], Codebook, list[int]]:
    """Person records for the frozen 500 gate persons, in the frozen order."""
    df = clean_riasec(load_riasec(DATA_DIR))
    codebook = load_codebook(DATA_DIR)
    _, gate_ids = pilot_and_gate_ids(df)
    by_id = df.set_index("person_id", drop=False)
    records = [person_record(by_id.loc[pid], codebook) for pid in gate_ids]
    return records, codebook, gate_ids


def build_all_tasks(arm: str = "twin") -> tuple[list[ProbeTask], Codebook, list[int]]:
    assert_folds_wellformed()
    records, codebook, gate_ids = load_gate_people()
    tasks: list[ProbeTask] = []
    for record in records:
        tasks.extend(build_probe_tasks(record, codebook, arm=arm))
    return tasks, codebook, gate_ids


# ---------------------------------------------------------------------------
# Verification steps
# ---------------------------------------------------------------------------


def verify_ids(reference_dir: Path | None) -> int:
    """Check our 500 person ids equal the ids in a reference gate run dir."""
    _, _, gate_ids = load_gate_people()
    print(f"[ids] built {len(gate_ids)} gate ids "
          f"(first 3 {gate_ids[:3]}, last 3 {gate_ids[-3:]})")
    if reference_dir is None:
        return 0
    ref = {int(json.loads(line)["person_id"])
           for line in (Path(reference_dir) / "records.jsonl").open(encoding="utf-8")
           if line.strip()}
    ours = set(gate_ids)
    if ours != ref:
        print(f"[ids] MISMATCH: {len(ours - ref)} only-ours, {len(ref - ours)} only-ref",
              file=sys.stderr)
        return 1
    print(f"[ids] OK: identical to {Path(reference_dir).name} ({len(ref)} persons)")
    return 0


def verify_baseline(gate_dir: Path) -> int:
    """Byte-identity check: our baseline prompts vs the gate run's baseline prompts.

    Passing this is the sole justification for reusing the gate's Gemma-4
    baseline completions instead of spending another 5,000 generations.
    """
    tasks, _, _ = build_all_tasks(arm="baseline")
    ours = {(t.person_id, t.tipi_code): t.prompt for t in tasks}

    theirs: dict[tuple[int, str], str] = {}
    with (Path(gate_dir) / "records.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec["arm"] != "baseline":
                continue
            theirs[(int(rec["person_id"]), rec["item"])] = rec["prompt"]

    missing = sorted(set(ours) - set(theirs))
    extra = sorted(set(theirs) - set(ours))
    diff = [key for key in ours if key in theirs and ours[key] != theirs[key]]

    print(f"[baseline] ours={len(ours)} gate={len(theirs)} "
          f"missing={len(missing)} extra={len(extra)} byte-diff={len(diff)}")
    if missing or extra or diff:
        if diff:
            key = diff[0]
            print(f"[baseline] first differing key {key}", file=sys.stderr)
            print("--- ours ---\n" + ours[key], file=sys.stderr)
            print("--- gate ---\n" + theirs[key], file=sys.stderr)
        print("[baseline] NOT byte-identical -> the baseline must be rerun.",
              file=sys.stderr)
        return 1
    print(f"[baseline] OK: all {len(ours)} baseline prompts are byte-identical to "
          f"{Path(gate_dir).name}; gate baseline completions are reusable.")
    return 0


# ---------------------------------------------------------------------------
# Export / ingest
# ---------------------------------------------------------------------------


def run_export(out_path: Path, arm: str = "twin") -> int:
    tasks, _, gate_ids = build_all_tasks(arm=arm)
    max_tok = VARIANT_MAX_OUTPUT_TOKENS[VARIANT]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for idx, task in enumerate(tasks):
            fh.write(json.dumps({
                "idx": idx,
                "prompt": task.prompt,
                "max_output_tokens": max_tok,
                "person_id": task.person_id,
                "arm": task.arm,
                "fold": task.fold,
                "item": task.tipi_code,
                "seed_items": list(task.seed_codes),
                "variant": VARIANT,
            }) + "\n")

    manifest = {
        "probe": "known_answer",
        "status": "DIAGNOSTIC (PREREGISTRATION_AMENDMENT_1.md A7)",
        "split": "gate", "k": PROBE_K, "seed": 42, "variant": VARIANT,
        "arm": arm, "backend": "batchfile",
        "n_prompts": len(tasks), "n_persons": len(gate_ids),
        "folds": {f: {"seed": list(s), "predict": list(p)}
                  for f, (s, p) in FOLDS.items()},
        "max_output_tokens": max_tok,
        "prompts_file": str(out_path),
    }
    (out_path.parent / "export_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    example = next(t for t in tasks if t.fold == "A2B")
    (out_path.parent / f"example_prompt_{arm}.txt").write_text(
        example.prompt, encoding="utf-8")
    print(f"[export] wrote {len(tasks)} {arm} prompts to {out_path} "
          f"({len(gate_ids)} persons x 10 items). No API calls.")
    return 0


def _record_from_task(task: ProbeTask, raw: str, parsed: dict,
                      tokens_in: int, tokens_out: int) -> dict:
    """Same record shape as run_replay, plus the probe's fold/seed fields."""
    true = task.true_answer
    disc = parsed["prediction_argmax"]
    mae_pt = parsed["mae_point"]
    return {
        "person_id": task.person_id,
        "arm": task.arm,
        "item": task.tipi_code,
        "fold": task.fold,
        "seed_items": list(task.seed_codes),
        "variant": VARIANT,
        "prompt": task.prompt,
        "raw_response": raw,
        "parsed": parsed["parsed"],
        "prediction_ev": parsed["prediction_ev"],
        "prediction_argmax": parsed["prediction_argmax"],
        "renorm_offset": parsed["renorm_offset"],
        "true_answer": true,
        "correct": None if disc is None else (disc == true),
        "within1": None if disc is None else (abs(disc - true) <= 1),
        "abs_error": None if mae_pt is None else abs(mae_pt - true),
        "parse_failure": parsed["parse_failure"],
        "parse_retry": False,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }


def _load_gate_baseline_records(gate_dir: Path) -> list[dict]:
    """The gate run's baseline records, retagged with this probe's fold labels.

    A baseline record is demographics-only, so it is fold-independent: the SAME
    record serves as the control for whichever direction predicted that item.
    The fold tag mirrors the twin side (fold A2B predicts TIPI6-10).
    """
    fold_of_item = {code: fold for fold, (_, predict) in FOLDS.items()
                    for code in predict}
    out: list[dict] = []
    with (Path(gate_dir) / "records.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec["arm"] != "baseline":
                continue
            rec = dict(rec)
            rec["fold"] = fold_of_item[rec["item"]]
            rec["seed_items"] = []
            rec["baseline_source"] = str(Path(gate_dir).name)
            out.append(rec)
    return out


def run_ingest(completions_path: Path, gate_dir: Path,
               node_hours: float | None, out_dir: Path | None) -> int:
    tasks, _, gate_ids = build_all_tasks(arm="twin")

    completions: dict[int, dict] = {}
    with Path(completions_path).open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                obj = json.loads(line)
                completions[int(obj["idx"])] = obj

    twin_records: list[dict] = []
    n_missing = 0
    for idx, task in enumerate(tasks):
        obj = completions.get(idx)
        if obj is None:
            n_missing += 1
            parsed = parse_response("", VARIANT)
            twin_records.append(_record_from_task(
                task, f"<no completion: missing idx {idx}>", parsed, 0, 0))
            continue
        text = obj.get("text") or ""
        parsed = parse_response(text, VARIANT)
        twin_records.append(_record_from_task(
            task, text, parsed,
            int(obj.get("tokens_in", 0) or 0), int(obj.get("tokens_out", 0) or 0)))

    baseline_records = _load_gate_baseline_records(gate_dir)
    all_records = twin_records + baseline_records

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = Path(out_dir) if out_dir else (
        RESULTS_DIR / f"probe_knownanswer_v2_{timestamp}_leonardo-batch")
    outdir.mkdir(parents=True, exist_ok=True)

    with (outdir / "records.jsonl").open("w", encoding="utf-8") as fh:
        for rec in all_records:
            fh.write(json.dumps(rec) + "\n")

    example = next(t for t in tasks if t.fold == "A2B")
    (outdir / "example_prompt_twin.txt").write_text(example.prompt, encoding="utf-8")
    (outdir / "example_prompt_baseline.txt").write_text(
        baseline_records[0]["prompt"], encoding="utf-8")

    pooled = summarize(all_records)
    per_fold = {}
    for fold, (_, predict) in FOLDS.items():
        subset = [r for r in all_records if r["item"] in predict]
        per_fold[fold] = summarize(subset)

    summary = {
        "config": {
            "probe": "known_answer",
            "status": "DIAGNOSTIC (PREREGISTRATION_AMENDMENT_1.md A7) - not confirmatory",
            "split": "gate", "k": PROBE_K, "seed": 42, "variant": VARIANT,
            "n_persons": len(gate_ids),
            "model": "leonardo-batch", "backend": "leonardo-batch",
            "model_label": "leonardo-gemma4-31b-it",
            "folds": {f: {"seed": list(s), "predict": list(p)}
                      for f, (s, p) in FOLDS.items()},
            "baseline_source_run": str(Path(gate_dir).name),
            "baseline_reused": True,
            "completions_file": str(completions_path),
        },
        "scoring": pooled,
        "scoring_by_fold": per_fold,
        "totals": {
            "n_records": len(all_records),
            "n_twin_records": len(twin_records),
            "n_baseline_records": len(baseline_records),
            "n_parse_failures": sum(1 for r in all_records if r["parse_failure"]),
            "n_missing_completions": n_missing,
            "tokens_in": sum(r["tokens_in"] for r in all_records),
            "tokens_out": sum(r["tokens_out"] for r in all_records),
            "twin_tokens_in": sum(r["tokens_in"] for r in twin_records),
            "twin_tokens_out": sum(r["tokens_out"] for r in twin_records),
            "node_hours": node_hours,
        },
        "aborted": None,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2),
                                         encoding="utf-8")

    append_cost_log(build_cost_entry(
        run_id=outdir.name, model="leonardo-batch", split="gate", variant=VARIANT,
        n_persons=len(gate_ids), n_calls=0, n_retries=0,
        n_parse_failures=sum(1 for r in twin_records if r["parse_failure"]),
        tokens_in=summary["totals"]["twin_tokens_in"],
        tokens_out=summary["totals"]["twin_tokens_out"],
        backend="leonardo-batch", node_hours=node_hours,
    ), RESULTS_DIR / "cost_log.jsonl")

    mae = pooled["mae"]
    print(f"[probe] {outdir.name}: {len(twin_records)} twin + "
          f"{len(baseline_records)} reused baseline records, "
          f"{summary['totals']['n_parse_failures']} parse failures, "
          f"{pooled['n_excluded_pairs']} excluded pairs")
    print(f"[probe] MAE twin={mae['twin']['mean']:.4f} "
          f"base={mae['baseline']['mean']:.4f} "
          f"lift={mae['lift']['mean']:+.4f} "
          f"[{mae['lift']['ci_low']:.4f}, {mae['lift']['ci_high']:.4f}] "
          f"t p={mae['tests']['t_p']:.4g}")
    for fold in ("A2B", "B2A"):
        f_mae = per_fold[fold]["mae"]
        print(f"[probe] fold {fold}: lift={f_mae['lift']['mean']:+.4f} "
              f"t p={f_mae['tests']['t_p']:.4g}")
    print(f"[probe] results in {outdir}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(
        description="DOPPLER known-answer probe (DIAGNOSTIC, amendment A7).")
    ap.add_argument("--verify-ids", action="store_true",
                    help="print the 500 gate ids; with --gate-dir, diff against it")
    ap.add_argument("--verify-baseline", metavar="GATE_DIR", default=None,
                    help="byte-compare our baseline prompts against a gate run dir")
    ap.add_argument("--gate-dir", default=None,
                    help="reference gate run dir for --verify-ids")
    ap.add_argument("--export", metavar="PATH", default=None,
                    help="write the probe prompts.jsonl + manifest and exit")
    ap.add_argument("--arm", choices=["twin", "baseline"], default="twin",
                    help="which arm to export (baseline only if reuse fails)")
    ap.add_argument("--ingest", metavar="COMPLETIONS", default=None,
                    help="score a completions.jsonl into a run dir")
    ap.add_argument("--baseline-from", metavar="GATE_DIR", default=None,
                    help="gate run dir supplying the reused baseline records")
    ap.add_argument("--node-hours", type=float, default=None)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    assert_folds_wellformed()

    if args.verify_ids:
        return verify_ids(Path(args.gate_dir) if args.gate_dir else None)
    if args.verify_baseline:
        return verify_baseline(Path(args.verify_baseline))
    if args.export:
        return run_export(Path(args.export), arm=args.arm)
    if args.ingest:
        if not args.baseline_from:
            ap.error("--ingest requires --baseline-from <gate run dir>")
        return run_ingest(Path(args.ingest), Path(args.baseline_from),
                          args.node_hours,
                          Path(args.out_dir) if args.out_dir else None)
    ap.error("pick one of --verify-ids / --verify-baseline / --export / --ingest")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
