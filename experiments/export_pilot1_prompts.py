"""Export the exact pilot-1 prompt set for the Leonardo offline benchmark.

Rebuilds the 400 pilot-1 prompts (split=pilot, k=48, seed=42, variant v0, both
arms) with the normal task builder, writes them to
``results/leonardo_bench/prompts.jsonl``, and verifies them against the stored
pilot-1 records: all 400 (person, arm, item) keys must match, and each prompt
must be byte-identical to the stored prompt EXCEPT where the later familysize
fix (omitting implausible familysize < 1) legitimately changed one line.

Makes zero API calls.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "experiments"))
sys.path.insert(0, str(_ROOT / "src"))

import run_replay  # noqa: E402
from doppler.backends import BatchFileBackend  # noqa: E402

PILOT1_RECORDS = _ROOT / "results" / "pilot_k48_20260724-030332" / "records.jsonl"
OUT = _ROOT / "results" / "leonardo_bench" / "prompts.jsonl"

_FAMILYSIZE_RE = re.compile(
    r"Number of children my parents had, including me: -?\d+\.\s*"
)


def _familysize_only_diff(stored: str, rebuilt: str) -> bool:
    """True if stripping the familysize sentence from ``stored`` yields ``rebuilt``."""
    stripped = _FAMILYSIZE_RE.sub("", stored)
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    return norm(stripped) == norm(rebuilt)


def main() -> int:
    tasks, ids, _ = run_replay._build_all_tasks("pilot", 48, 42, "v0")
    n = BatchFileBackend.export(tasks, "v0", 16, OUT)
    (OUT.parent / "export_manifest.json").write_text(
        '{"split": "pilot", "k": 48, "seed": 42, "variant": "v0", '
        f'"backend": "batchfile", "n_prompts": {n}, "n_persons": {len(ids)}, '
        '"max_output_tokens": 16}\n',
        encoding="utf-8",
    )
    print(f"[export] wrote {n} prompts to {OUT}")

    if not PILOT1_RECORDS.exists():
        print(f"[warn] stored records not found at {PILOT1_RECORDS}; skipped verify.")
        return 0

    stored = {
        (int(r["person_id"]), r["arm"], r["item"]): r["prompt"]
        for r in run_replay.read_records(PILOT1_RECORDS)
    }
    task_keys = {(t.person_id, t.arm, t.tipi_code) for t in tasks}

    keys_match = task_keys == set(stored)
    exact = 0
    familysize_only = 0
    other = []
    for t in tasks:
        key = (t.person_id, t.arm, t.tipi_code)
        if key not in stored:
            other.append((key, "missing in stored"))
            continue
        if t.prompt == stored[key]:
            exact += 1
        elif _familysize_only_diff(stored[key], t.prompt):
            familysize_only += 1
        else:
            other.append((key, "non-familysize diff"))

    print(f"[verify] n_tasks={len(tasks)}  keys_match={keys_match}")
    print(f"[verify] exact_prompt_matches={exact}/{len(tasks)}")
    print(f"[verify] familysize_only_diffs={familysize_only}")
    print(f"[verify] other_diffs={len(other)}")
    if other:
        for key, why in other[:10]:
            print(f"[verify]   {key}: {why}")
        return 1
    print("[verify] OK: every prompt matches the stored set except the "
          "familysize fix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
