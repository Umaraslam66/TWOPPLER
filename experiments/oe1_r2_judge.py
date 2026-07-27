"""r2 judge run: regression on the D/E tranche + fresh labels on F/G.

Owner-directed 2026-07-28, after the parameter-5 FAIL and the owner's
approval of the r1->r2 rubric diff. Two passes, one pinned config:

- REGRESSION (D/E, 18 rows): the r2 judge re-labels the tranche the r1
  judge failed on. Branch rule, owner-set before this ran: if r2 breaks
  more than 2 of the 14 rows where r1 agreed with the auditor line, STOP
  — the fix is overfitted.
- F/G (18 rows): the r2 judge line for the parameter-5 re-measurement,
  scored against the rubric-briefed auditor line under the unchanged bar
  (raw >= 0.80 AND kappa >= 0.60).

Everything about the call is the pinned judge config, verbatim from
stage2_oe1.py: gemini-3.5-flash (MODEL_NAME in .env is the robustness
scored model and is deliberately ignored here), temperature 0.0,
thinking_budget=0, max_output_tokens=512, the same GUEST-redaction of
all three texts, one candidate per stateless call. The only change is
the rubric text (r2, sha asserted) and the widened parser (CENTRAL line
extracted; LABEL/WHY regexes untouched — they are MULTILINE and already
tolerate a leading CENTRAL line). The parser self-test runs before any
API call and hard-fails the run if the widening broke the old format.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import stage2_oe1 as O  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler.costlog import append_cost_log, build_cost_entry  # noqa: E402

BASE = _ROOT / "results" / "stage2_openended"
R2_SHA = "ad050d1a75b038fc63ee162fe74862fd8f99c895e2b39b3af56f24bdea102464"
DIR_OF_MODEL = {"gemini-3.5-flash-lite": "flashlite", "Gemma-4-31B-it": "gemma"}
CALL_CAP = 60  # 36 scheduled + retries + 2-row determinism probe, far under

_CENTRAL_RE = re.compile(r"^\s*CENTRAL:\s*(.+?)\s*$",
                         re.IGNORECASE | re.MULTILINE)


def parse_judge_r2(completion):
    """(label, why, central). Widened: CENTRAL extracted when present;
    LABEL/WHY exactly as the frozen parser read them."""
    if not completion:
        return None, None, None
    m = O._LABEL_RE.search(completion)
    if not m:
        return None, None, None
    why = O._WHY_RE.search(completion)
    central = _CENTRAL_RE.search(completion)
    return (m.group(1).upper(), why.group(1) if why else None,
            central.group(1) if central else None)


def parser_selftest():
    """Regression test for the widening. Runs before any API call."""
    lab, why, cen = parse_judge_r2("LABEL: SAME\nWHY: both answers land on X.")
    assert (lab, cen) == ("SAME", None) and why, "old format broke"
    lab, why, cen = parse_judge_r2(
        "CENTRAL: whether Brexit will be stopped\n"
        "LABEL: DIFFERENT\nWHY: one quotes A; the other quotes B.")
    assert lab == "DIFFERENT" and why and cen == "whether Brexit will be stopped"
    lab, _, _ = parse_judge_r2("preamble text\nCENTRAL: c\nLABEL: unclear\nWHY: w")
    assert lab == "UNCLEAR", "case/preamble tolerance broke"
    assert parse_judge_r2("no label anywhere") == (None, None, None)
    assert parse_judge_r2("") == (None, None, None)


def load_gen_text():
    text = {}
    for d in ("flashlite", "gemma"):
        for arm in ("twin_redacted", "twin_named", "zeroinfo_redacted",
                    "zeroinfo_named", "imposter_redacted"):
            for r in S.read_jsonl(BASE / "gen" / d / f"completions_{arm}.jsonl"):
                text[(r["item_id"], r["arm"], d)] = r["text"]
    return text


def main():
    parser_selftest()
    print("[r2-judge] parser self-test passed")

    rubric = (BASE / "rubric_r2_draft.txt").read_text()
    assert hashlib.sha256(rubric.encode()).hexdigest() == R2_SHA, \
        "rubric_r2_draft.txt does not match the pinned sha; refusing to run"

    items = {r["item_id"]: r for r in S.read_jsonl(BASE / "items_oe1.jsonl")}
    gen_text = load_gen_text()
    ctx = O.subject_blocks(O.PILOT1_DIR)

    tranches = []
    for keyfile, tag in (("fresh_tranche_key.json", "regression"),
                         ("fresh_tranche_r2_key.json", "fg")):
        entries = json.load(open(BASE / keyfile))["entries"]
        tranches.append((tag, entries))

    client = O._make_client(
        O.JUDGE_MODEL, temperature=O.JUDGE_TEMPERATURE,
        max_output_tokens=O.JUDGE_MAX_OUTPUT_TOKENS, call_cap=CALL_CAP,
        thinking_budget=O.JUDGE_THINKING_BUDGET)

    all_rows = {}
    for tag, entries in tranches:
        rows, tin_sum, tout_sum, n_retries, n_unparsed = [], 0, 0, 0, 0
        for e in sorted(entries, key=lambda e: (e["sheet"], e["position"])):
            item = items[e["item_id"]]
            cand = gen_text[(e["item_id"], e["arm"], DIR_OF_MODEL[e["model"]])]
            variants = ctx[e["canonical_id"]]["variants"]
            prompt = O.judge_input(rubric, item["question"],
                                   item["real_answer_verbatim"], cand, variants)
            text, tin, tout = client.generate(prompt)
            label, why, central = parse_judge_r2(text)
            retried = False
            if label is None:
                retried = True
                n_retries += 1
                text, tin2, tout2 = client.generate(prompt)
                tin += tin2
                tout += tout2
                label, why, central = parse_judge_r2(text)
            if label is None:
                n_unparsed += 1
            tin_sum += tin
            tout_sum += tout
            rows.append({
                "entry": e["entry"], "tranche": tag, "item_id": e["item_id"],
                "canonical_id": e["canonical_id"], "arm": e["arm"],
                "model": e["model"], "label": label, "central": central,
                "why": why, "why_intact": O.why_is_intact(why, tout),
                "retried": retried,
                "output_hit_cap": tout >= O.JUDGE_MAX_OUTPUT_TOKENS,
                "raw": text, "judge_model": O.JUDGE_MODEL,
                "judge_rubric_sha256": R2_SHA,
                "judge_thinking_budget": O.JUDGE_THINKING_BUDGET,
                "judge_max_output_tokens": O.JUDGE_MAX_OUTPUT_TOKENS,
                "tokens_in": tin, "tokens_out": tout,
            })
            print(f"[r2-judge] {tag:10s} {e['entry']:3s} {label} "
                  f"({'retry, ' if retried else ''}{tout} tok)")
        S.write_jsonl(BASE / "judge" / f"judgements_r2_{tag}.jsonl", rows)
        entry = build_cost_entry(
            run_id=f"stage2_oe1/judge_r2_{tag}", model=O.JUDGE_MODEL,
            split="stage2_openended", variant="r2_rerun",
            n_persons=len({r["canonical_id"] for r in rows}),
            n_calls=len(rows) + n_retries, n_retries=n_retries,
            n_parse_failures=n_unparsed,
            tokens_in=tin_sum, tokens_out=tout_sum, backend="gemini")
        append_cost_log(entry, O.COST_LOG)
        all_rows[tag] = {"rows": rows, "cost_usd": entry["cost_usd"],
                         "n_retries": n_retries, "n_unparsed": n_unparsed}

    # Mini determinism probe: the first two regression rows, called again.
    probe = []
    for e in sorted(tranches[0][1], key=lambda e: (e["sheet"], e["position"]))[:2]:
        item = items[e["item_id"]]
        cand = gen_text[(e["item_id"], e["arm"], DIR_OF_MODEL[e["model"]])]
        prompt = O.judge_input(rubric, item["question"],
                               item["real_answer_verbatim"], cand,
                               ctx[e["canonical_id"]]["variants"])
        text, _, _ = client.generate(prompt)
        label, _, _ = parse_judge_r2(text)
        first = next(r for r in all_rows["regression"]["rows"]
                     if r["entry"] == e["entry"])
        probe.append({"entry": e["entry"], "first": first["label"],
                      "second": label, "stable": label == first["label"]})

    summary = {
        "judge_model": O.JUDGE_MODEL, "temperature": O.JUDGE_TEMPERATURE,
        "thinking_budget": O.JUDGE_THINKING_BUDGET,
        "max_output_tokens": O.JUDGE_MAX_OUTPUT_TOKENS,
        "rubric": "rubric_r2_draft.txt", "rubric_sha256": R2_SHA,
        "model_name_env_note": "MODEL_NAME in .env is the robustness scored "
                               "model; ignored here, judge stays pinned",
        "per_tranche": {tag: {"n": len(d["rows"]),
                              "labels": {}, "cost_usd": d["cost_usd"],
                              "n_retries": d["n_retries"],
                              "n_unparsed": d["n_unparsed"],
                              "n_why_intact": sum(1 for r in d["rows"]
                                                  if r["why_intact"]),
                              "n_central_present": sum(1 for r in d["rows"]
                                                       if r["central"])}
                        for tag, d in all_rows.items()},
        "determinism_probe": probe,
    }
    for tag, d in all_rows.items():
        lab_ct = {}
        for r in d["rows"]:
            lab_ct[str(r["label"])] = lab_ct.get(str(r["label"]), 0) + 1
        summary["per_tranche"][tag]["labels"] = lab_ct
    S.write_json(BASE / "judge" / "judge_r2_summary.json", summary)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
