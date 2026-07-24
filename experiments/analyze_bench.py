"""Analyze an offline benchmark completions file (Leonardo batch model output).

Given a ``completions.jsonl`` (idx, text, optional gen_meta), report:
  * n, format-compliance under the v0 parser (single integer 1-7),
  * up to 5 parse-failure examples, and the answer histogram,
  * throughput (prompts/min) and token totals if gen_meta carries timing/tokens,
  * a purely descriptive model-vs-model comparison against the Gemini answers
    for the same (person, arm, item): answer distributions and agreement rate.

Joins completions to metadata by ``idx`` via the exported ``prompts.jsonl``.
Makes zero API calls.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "experiments"))
sys.path.insert(0, str(_ROOT / "src"))

import run_replay  # noqa: E402
from doppler.backends import read_completions  # noqa: E402
from doppler.scoring import parse_answer  # noqa: E402

DEFAULT_PROMPTS = _ROOT / "results" / "leonardo_bench" / "prompts.jsonl"
DEFAULT_RECORDS = _ROOT / "results" / "pilot_k48_20260724-030332" / "records.jsonl"


def _hist_line(counter: Counter) -> str:
    return "  ".join(f"{k}:{counter.get(k, 0)}" for k in range(1, 8))


def analyze(completions_path, prompts_path, records_path) -> dict:
    comps = read_completions(completions_path)
    prompts = {int(json_line["idx"]): json_line
               for json_line in run_replay.read_records(prompts_path)}
    gemini = {
        (int(r["person_id"]), r["arm"], r["item"]): r.get("parsed")
        for r in run_replay.read_records(records_path)
    } if Path(records_path).exists() else {}

    n = len(comps)
    batch_ans = Counter()
    gemini_ans = Counter()
    failures = []
    agree = 0
    comparable = 0
    tokens_in = tokens_out = 0
    total_ms = 0.0
    have_timing = False

    for idx, obj in sorted(comps.items()):
        text = obj.get("text") or ""
        parsed = parse_answer(text)
        if parsed is None:
            if len(failures) < 5:
                failures.append((idx, text[:80]))
        else:
            batch_ans[parsed] += 1

        meta = obj.get("gen_meta") or {}
        tokens_in += int(meta.get("tokens_in", 0) or 0)
        tokens_out += int(meta.get("tokens_out", 0) or 0)
        if meta.get("gen_ms") is not None:
            have_timing = True
            total_ms += float(meta["gen_ms"])

        pmeta = prompts.get(idx)
        if pmeta:
            key = (int(pmeta["person_id"]), pmeta["arm"], pmeta["item"])
            g = gemini.get(key)
            if g is not None:
                gemini_ans[g] += 1
                if parsed is not None:
                    comparable += 1
                    if parsed == g:
                        agree += 1

    n_parsed = sum(batch_ans.values())
    throughput = (n / (total_ms / 60000.0)) if (have_timing and total_ms > 0) else None

    return {
        "n": n,
        "format_compliance": (n_parsed / n) if n else 0.0,
        "n_parse_failures": n - n_parsed,
        "failure_examples": failures,
        "batch_hist": batch_ans,
        "gemini_hist": gemini_ans,
        "agreement_rate": (agree / comparable) if comparable else None,
        "n_comparable": comparable,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "throughput_per_min": throughput,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze Leonardo benchmark completions.")
    ap.add_argument("--completions", required=True)
    ap.add_argument("--prompts", default=str(DEFAULT_PROMPTS))
    ap.add_argument("--records", default=str(DEFAULT_RECORDS))
    args = ap.parse_args()

    r = analyze(args.completions, args.prompts, args.records)
    print(f"n = {r['n']}")
    print(f"format-compliance (v0 single-int) = {r['format_compliance']:.3f} "
          f"({r['n_parse_failures']} failures)")
    if r["failure_examples"]:
        print("parse-failure examples:")
        for idx, text in r["failure_examples"]:
            print(f"  idx {idx}: {text!r}")
    print(f"batch answer histogram   : {_hist_line(r['batch_hist'])}")
    print(f"gemini answer histogram  : {_hist_line(r['gemini_hist'])}")
    if r["agreement_rate"] is not None:
        print(f"model-vs-model agreement = {r['agreement_rate']:.3f} "
              f"(over {r['n_comparable']} comparable items, descriptive only)")
    if r["throughput_per_min"] is not None:
        print(f"throughput = {r['throughput_per_min']:.1f} prompts/min")
    if r["tokens_in"] or r["tokens_out"]:
        print(f"tokens: in={r['tokens_in']} out={r['tokens_out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
