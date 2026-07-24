"""Export the three pilot2 prompt sets (v0/v1/v2) for the Qwen HPC batch job.

Writes ``results/leonardo_pilot2/prompts_v{0,1,2}.jsonl`` (+ per-variant
manifests), 1000 tasks each, idx 0-999 per file, with the variant-correct
max_output_tokens (16/100/120).

Then verifies (read-only) against the live Gemini pilot2 runs:
  * v0 -> every prompt must byte-match the completed v0 run's records;
  * v1 -> compare against however many records exist right now in the in-flight
    v1 run (tolerant of a partial trailing line being written concurrently);
  * v2 -> no reference yet (covered by the determinism tests).

Any mismatch stops with a non-zero exit. Makes zero API calls and never writes
to the Gemini run dirs.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "experiments"))
sys.path.insert(0, str(_ROOT / "src"))

import run_replay  # noqa: E402
from doppler.backends import BatchFileBackend  # noqa: E402
from doppler.prompts import VARIANT_MAX_OUTPUT_TOKENS  # noqa: E402

RESULTS = _ROOT / "results"
OUT_DIR = RESULTS / "leonardo_pilot2"
SPLIT, K, SEED = "pilot2", 48, 42


def _gemini_run_dir(variant: str) -> Path | None:
    """The Gemini run dir for a pilot2 variant (pure-timestamp name, no backend)."""
    pat = re.compile(rf"pilot2_{variant}_k{K}_\d{{8}}-\d{{6}}$")
    dirs = [d for d in RESULTS.glob(f"pilot2_{variant}_k{K}_*")
            if pat.match(d.name) and (d / "records.jsonl").exists()]
    dirs.sort()
    return dirs[-1] if dirs else None


def _read_tolerant(path: Path) -> list[dict]:
    """Read JSONL, stopping at the first unparsable (partial) trailing line."""
    recs = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                break  # a line being appended right now; stop cleanly
    return recs


def _export(variant: str):
    tasks, ids, _ = run_replay._build_all_tasks(SPLIT, K, SEED, variant)
    out = OUT_DIR / f"prompts_{variant}.jsonl"
    mot = VARIANT_MAX_OUTPUT_TOKENS[variant]
    n = BatchFileBackend.export(tasks, variant, mot, out)
    (OUT_DIR / f"manifest_{variant}.json").write_text(json.dumps({
        "split": SPLIT, "k": K, "seed": SEED, "variant": variant,
        "backend": "batchfile", "n_prompts": n, "n_persons": len(ids),
        "max_output_tokens": mot, "prompts_file": str(out),
    }, indent=2), encoding="utf-8")
    print(f"[export] {variant}: {n} prompts -> {out} (max_output_tokens={mot})")
    return tasks


def _verify(variant: str, tasks, records: list[dict]) -> tuple[int, int]:
    """Compare exported task prompts against stored records by key. Returns
    (n_checked, n_match)."""
    stored = {(int(r["person_id"]), r["arm"], r["item"]): r["prompt"]
              for r in records}
    by_key = {(t.person_id, t.arm, t.tipi_code): t.prompt for t in tasks}
    checked = matches = 0
    mismatches = []
    for key, prompt in stored.items():
        if key not in by_key:
            mismatches.append((key, "key missing from export"))
            continue
        checked += 1
        if by_key[key] == prompt:
            matches += 1
        else:
            mismatches.append((key, "prompt bytes differ"))
    if mismatches:
        print(f"[verify:{variant}] MISMATCH ({len(mismatches)}):", file=sys.stderr)
        for key, why in mismatches[:10]:
            print(f"[verify:{variant}]   {key}: {why}", file=sys.stderr)
    return checked, matches


def _baseline_prompts(tasks) -> dict:
    return {(t.person_id, t.arm, t.tipi_code): t.prompt
            for t in tasks if t.arm == "baseline"}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tasks = {v: _export(v) for v in ("v0", "v1", "v2", "v3")}

    ok = True

    # v3's fix only touches the interests block, so its baseline must be
    # byte-identical to v0's baseline. Assert across all baseline tasks.
    v0_base = _baseline_prompts(tasks["v0"])
    v3_base = _baseline_prompts(tasks["v3"])
    assert set(v0_base) == set(v3_base), "v0/v3 baseline task keys differ"
    n_base = len(v0_base)
    base_matches = sum(1 for key in v0_base if v0_base[key] == v3_base[key])
    print(f"[verify:v3] {base_matches}/{n_base} baseline prompts byte-match v0")
    if base_matches != n_base:
        ok = False

    # v0: full byte-match against the completed run.
    v0_dir = _gemini_run_dir("v0")
    if v0_dir is None:
        print("[verify:v0] PENDING: no completed Gemini v0 run found.")
    else:
        recs = run_replay.read_records(v0_dir / "records.jsonl")
        checked, matches = _verify("v0", tasks["v0"], recs)
        print(f"[verify:v0] {matches}/{checked} prompts byte-match {v0_dir.name} "
              f"(stored records={len(recs)})")
        if matches != checked or checked != 1000:
            ok = False

    # v1: partial match against the in-flight run (read-only, tolerant).
    v1_dir = _gemini_run_dir("v1")
    if v1_dir is None:
        print("[verify:v1] PENDING: no in-flight Gemini v1 run found yet.")
    else:
        recs = _read_tolerant(v1_dir / "records.jsonl")
        checked, matches = _verify("v1", tasks["v1"], recs)
        print(f"[verify:v1] {matches}/{checked} prompts byte-match {v1_dir.name} "
              f"(in-flight; records read now={len(recs)})")
        if matches != checked:
            ok = False

    print("[verify:v2] no Gemini reference yet; covered by determinism tests.")

    if not ok:
        print("[verify] STOP: a prompt mismatch was found.", file=sys.stderr)
        return 1
    print("[verify] OK: all available references byte-match the export.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
