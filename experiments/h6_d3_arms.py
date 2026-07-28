#!/usr/bin/env python3
"""EXPLORATORY H6 arm: the rich arm rebuilt at D_min = 3.

**This is NOT the pre-committed sensitivity arm.** Appendix 4.3(c) pre-committed
a D_min = 3 arm *conditionally*, on the part-2 FOLLOW-UP overturn rate exceeding
20%. The measured rate is 18.33%, so the tripwire did NOT fire and the
pre-committed arm does not exist. This arm is **owner-ordered exploratory
diagnostic colour** (2026-07-28, stop point iii), reported in its own clearly
labelled section of ``results/stage2_confirm/H6_REPORT.md``. It changes no bar,
no branch and no verdict: H6's verdict stays "DESCRIPTIVE ONLY — neither reading
applied; UNRESOLVED at confirmatory scale".

Nothing here re-implements the H6 build. ``experiments/h6_arms.py`` is imported
and its module constant ``D_MIN`` is re-pointed from 2 to 3; every other rule --
the classifier labels, the segment and chain definitions, deepest-chain-first
selection, skip-not-stop, the newest-first top-up, the chronological render, the
redaction guards, the leakage asserts -- is that file's code executed unchanged.
The one substitution is printed at run time so it is never silent.

What changes at D_min = 3, and what does not:

* **rich arm** -- only chains of depth >= 3 qualify (root INCLUDED, as in the
  registered arm). Supply shrinks; that shrinkage is the diagnostic point.
* **poor arm** -- IDENTICAL. ``lone_new_topics`` excludes anything inside ANY
  chain, at any depth, so the poor arm does not depend on D_min at all. This
  arm is contrasted against the SAME poor arm as the registered contrast, and
  the build asserts the poor selection matches ``h6/arms.json`` word for word.
* **eligibility** -- a subject enters the exploratory contrast only if it is
  already eligible for the REGISTERED contrast at that budget AND its D_min = 3
  rich arm also fills to within +-5% of B. Same conjunction the root-excluded
  sensitivity arm used, so the two sensitivity-style arms are counted the same
  way and both are subsets of the registered pool.

**Primary model only** (Gemma-4-31B-it), consistent with the root-excluded
sensitivity arm's precedent and declared in the report.

Outputs, all under ``results/stage2_confirm/h6_d3/`` (the registered
``h6/`` directory is never written to)::

    arms_d3.json                  per-subject supply, fills, eligibility
    items_confirm.jsonl           the eligible subjects' items (H1's items)
    node/chunk_01.prompts.jsonl   node prompts (Gemma-4-31B-it, Leonardo)
    node/chunk_01.meta.jsonl      the join sidecar
    render_index.jsonl            every logical render -> (chunk, idx)
    render_manifest.json          the submission manifest
    grounding/<cid>.json          the rendered grounding block per arm

Run::

    .venv/bin/python experiments/h6_d3_arms.py measure
    .venv/bin/python experiments/h6_d3_arms.py render
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import h6_arms as A  # noqa: E402
import stage2_pilot as P1  # noqa: E402

from doppler import oe_render as OE  # noqa: E402
from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402

RESULTS_DIR = _ROOT / "results"
CONFIRM_DIR = RESULTS_DIR / "stage2_confirm"
H6_DIR = CONFIRM_DIR / "h6"
D3_DIR = CONFIRM_DIR / "h6_d3"

#: The one substituted parameter. Appendix parameter 2c freezes D_min = 2 for
#: the registered arm; 4.3(c) names 3 as the tripwire's arm.
D_MIN_EXPLORATORY = 3
D_MIN_REGISTERED = A.D_MIN

ARMS_D3 = {
    "h6_richd3_b1000": {"kind": "rich_d3", "budget": 1000, "roots": True},
    "h6_richd3_b400":  {"kind": "rich_d3", "budget": 400,  "roots": True},
}
CHUNK = "chunk_01"

BANNER = ("EXPLORATORY H6 D_min = 3 arm, owner-ordered 2026-07-28. The frozen "
          "tripwire did NOT fire (part-2 FOLLOW-UP overturn 18.33% against the "
          "> 20% line), so this is NOT the pre-committed sensitivity arm. It "
          "changes no bar, no branch and no verdict.")
NOT_PRECOMMITTED = (
    "Appendix 4.3(c) pre-committed a D_min = 3 arm CONDITIONALLY, on the "
    "part-2 FOLLOW-UP overturn rate exceeding 20%. The measured rate is "
    "18.33%, below the line, so the pre-committed arm does not exist. This "
    "arm is owner-ordered exploratory diagnostic colour and is labelled as "
    "such everywhere it appears.")
PRIMARY_ONLY = (
    "Generated and scored on the PRIMARY model (Gemma-4-31B-it) only, "
    "consistent with the root-excluded sensitivity arm's precedent. Declared "
    "in the report.")


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


def announce() -> None:
    print(f"[h6-d3] importing experiments/h6_arms.py and re-pointing ONE "
          f"module constant: D_MIN {D_MIN_REGISTERED} -> "
          f"{D_MIN_EXPLORATORY}. Nothing else is overridden.")


def registered() -> dict:
    """The registered build's own arms.json — the source of the poor arm."""
    return json.loads((H6_DIR / "arms.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Measure
# ---------------------------------------------------------------------------


def measure(write: bool = True) -> dict:
    announce()
    A.D_MIN = D_MIN_EXPLORATORY
    labels, drops, drop_stats = A.load_labels()
    with_items, items_by_subject = A.survivors_with_items()
    reg = registered()
    reg_by_subject = {r["canonical_id"]: r for r in reg["per_subject"]}
    reg_eligible = {str(b): set(reg["eligibility"][str(b)]["eligible_ids"])
                    for b in A.BUDGETS}

    rows = []
    for cid in with_items:
        row = A.build_subject(cid, labels, drops, drop_stats)
        row["n_items"] = len(items_by_subject[cid])
        # The poor arm cannot depend on D_min. Proved per subject rather than
        # argued: if this ever fires, the contrast is not against the same
        # poor arm the registered contrast used and the run must stop.
        for budget in A.BUDGETS:
            key = str(budget)
            want = reg_by_subject[cid]["budgets"][key]["poor_words"]
            got = row["budgets"][key]["poor_words"]
            if want != got:
                raise fatal(
                    f"{cid} B={budget}: poor arm changed under D_min = 3 "
                    f"({want} -> {got} words). The exploratory contrast must "
                    "run against the SAME poor arm as the registered one.")
        rows.append(row)

    summary = {
        "banner": BANNER,
        "not_precommitted": NOT_PRECOMMITTED,
        "primary_model_only": PRIMARY_ONLY,
        "contract": reg["contract"],
        "rich_arm_wording": A.RICH_WORDING,
        "d_min": D_MIN_EXPLORATORY,
        "d_min_registered": D_MIN_REGISTERED,
        "budgets": list(A.BUDGETS),
        "budget_tolerance": A.BUDGET_TOLERANCE,
        "n_with_items": len(with_items),
        "eligibility": {},
        "per_subject": [],
        "generated_utc": A.now(),
    }

    for budget in A.BUDGETS:
        key = str(budget)
        lo = (1.0 - A.BUDGET_TOLERANCE) * budget
        # Subjects whose D_min=3 rich arm fills on its own, ignoring the poor
        # arm. Printed beside the conjunction so the two causes of the
        # shrinkage (rich supply vs the registered pool) stay separable.
        fills = [r for r in rows if r["budgets"][key]["rich_words"] >= lo]
        elig = [r for r in fills if r["canonical_id"] in reg_eligible[key]]
        lost = sorted(reg_eligible[key] - {r["canonical_id"] for r in elig})
        shares = [r["budgets"][key]["root_share_of_rich"] for r in elig
                  if r["budgets"][key]["root_share_of_rich"] is not None]
        with_chain = [r for r in rows if r["n_chains_qualifying"] > 0]
        summary["eligibility"][key] = {
            "budget": budget,
            "n_registered_eligible": len(reg_eligible[key]),
            "n_rich_d3_fills": len(fills),
            "n_eligible": len(elig),
            "eligible_ids": [r["canonical_id"] for r in elig],
            "n_lost_vs_registered": len(lost),
            "lost_ids": lost,
            "n_items_eligible": sum(r["n_items"] for r in elig),
            "n_subjects_with_any_d3_chain": len(with_chain),
            "branch_if_it_were_registered": A.branch_for(len(elig)),
            "root_share_min": round(min(shares), 4) if shares else None,
            "root_share_median": (round(statistics.median(shares), 4)
                                  if shares else None),
            "root_share_max": round(max(shares), 4) if shares else None,
        }

    for r in rows:
        summary["per_subject"].append(
            {k: v for k, v in r.items() if k != "selections"})

    if write:
        D3_DIR.mkdir(parents=True, exist_ok=True)
        S.write_json(D3_DIR / "arms_d3.json", summary)
    return summary


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def render() -> dict:
    summary = measure(write=True)
    A.D_MIN = D_MIN_EXPLORATORY
    labels, drops, drop_stats = A.load_labels()
    _with_items, items_by_subject = A.survivors_with_items()
    pool = {r["canonical_id"]: r for r in S.load_pool()}

    # ``_guarded`` reads the arm spec out of ``A.ARMS``. Registering the two
    # exploratory arms there is an in-process addition only; the file on disk
    # and the registered manifest it produced are untouched.
    A.ARMS.update(ARMS_D3)

    elig_by_budget = {str(b): set(summary["eligibility"][str(b)]["eligible_ids"])
                      for b in A.BUDGETS}
    all_eligible = sorted(set().union(*elig_by_budget.values()))

    (D3_DIR / "node").mkdir(parents=True, exist_ok=True)
    (D3_DIR / "grounding").mkdir(parents=True, exist_ok=True)

    reg_ground = {}
    rendered: list[dict] = []
    failures: list[dict] = []
    per_subject: dict[str, dict] = {}
    items_out: list[dict] = []

    for cid in all_eligible:
        row = A.build_subject(cid, labels, drops, drop_stats)
        variants = P1.name_variants(pool[cid])
        items = items_by_subject[cid]
        items_out.extend(items)
        blocks: dict[str, dict] = {}

        reg_path = H6_DIR / "grounding" / f"{cid}.json"
        reg_ground[cid] = (json.loads(reg_path.read_text(encoding="utf-8"))
                           if reg_path.exists() else {"arms": {}})

        for arm, spec in ARMS_D3.items():
            budget = str(spec["budget"])
            if cid not in elig_by_budget[budget]:
                continue
            selection = row["selections"][budget]["rich"]
            block, words = A.render_block(selection)
            block = R.redact(block, variants)
            R.assert_redacted(block, variants)
            got = OE.grounding_speech_words(block)
            if got > words:
                raise fatal(f"{cid}/{arm}: rendered block carries {got} speech "
                            f"words, more than the {words} selected")
            if got > spec["budget"]:
                raise fatal(f"{cid}/{arm}: {got} words over the "
                            f"{spec['budget']}-word budget")
            sha = R.sha256(block)
            reg_arms = reg_ground[cid]["arms"]
            poor_arm = f"h6_poor_b{spec['budget']}"
            rich_arm = f"h6_rich_b{spec['budget']}"
            if poor_arm in reg_arms and reg_arms[poor_arm]["block_sha256"] == sha:
                raise fatal(f"{cid}: the D_min=3 rich block is identical to "
                            f"the poor block at B={spec['budget']}")
            blocks[arm] = {
                "block": block, "selection_words": words, "words": got,
                "n_segments": len(selection),
                "redaction_words_lost": words - got, "block_sha256": sha,
                # Whether D_min = 3 actually changed the arm for this subject:
                # if every qualifying chain was already depth >= 3, the block
                # is byte-identical to the registered rich arm and this
                # subject contributes no new information.
                "identical_to_registered_rich": bool(
                    rich_arm in reg_arms
                    and reg_arms[rich_arm]["block_sha256"] == sha),
            }

        for arm, built in blocks.items():
            for item in items:
                out = A._guarded(arm, item, cid, pool[cid]["canonical_name"],
                                 variants, built, failures)
                if out is not None:
                    rendered.append(out)

        per_subject[cid] = {
            "canonical_id": cid,
            "n_items": len(items),
            "arms": {a: {k: v for k, v in b.items() if k != "block"}
                     for a, b in blocks.items()},
            "budgets": {k: v for k, v in row["budgets"].items()},
        }
        S.write_json(D3_DIR / "grounding" / f"{cid}.json", {
            "canonical_id": cid,
            "arms": {a: {"words": b["words"], "n_segments": b["n_segments"],
                         "block_sha256": b["block_sha256"], "block": b["block"]}
                     for a, b in blocks.items()},
        })

    if failures:
        raise fatal(f"{len(failures)} render guard failure(s); first: "
                    f"{failures[0]}")

    return write_chunk(rendered, items_out, summary, per_subject)


def write_chunk(rendered: list[dict], items_out: list[dict], summary: dict,
                per_subject: dict) -> dict:
    """One chunk, deduped on prompt hash exactly as the registered build did."""
    index_rows: list[dict] = []
    unique: dict[str, dict] = {}
    n_dupes = 0
    rows = sorted(rendered, key=lambda r: (r["canonical_id"], r["arm"],
                                           r["item_id"]))
    for r in rows:
        sha = r["prompt_sha256"]
        if sha not in unique:
            unique[sha] = dict(r, chunk=CHUNK, idx=len(unique))
        else:
            n_dupes += 1
        index_rows.append({
            "chunk": CHUNK, "idx": unique[sha]["idx"],
            "canonical_id": r["canonical_id"], "item_id": r["item_id"],
            "arm": r["arm"], "h6_kind": r["h6_kind"],
            "h6_budget": r["h6_budget"], "h7_bin": None,
            "prompt_sha256": sha,
        })
    chunk_rows = list(unique.values())

    S.write_jsonl(D3_DIR / "node" / f"{CHUNK}.prompts.jsonl",
                  [{"idx": r["idx"], "prompt": r["prompt"],
                    "max_output_tokens": A.GEN_MAX_OUTPUT_TOKENS}
                   for r in chunk_rows])
    S.write_jsonl(D3_DIR / "node" / f"{CHUNK}.meta.jsonl",
                  [{k: r.get(k) for k in A.NODE_META_FIELDS}
                   for r in chunk_rows])
    S.write_jsonl(D3_DIR / "render_index.jsonl", index_rows)

    seen = {it["item_id"]: it for it in items_out}
    S.write_jsonl(D3_DIR / "items_confirm.jsonl", [seen[k] for k in sorted(seen)])

    manifest = {
        "banner": BANNER,
        "not_precommitted": NOT_PRECOMMITTED,
        "primary_model_only": PRIMARY_ONLY,
        "contract": summary["contract"],
        "rich_arm_wording": A.RICH_WORDING,
        "d_min": D_MIN_EXPLORATORY,
        "d_min_registered": D_MIN_REGISTERED,
        "arms": {a: dict(spec) for a, spec in ARMS_D3.items()},
        "poor_arm_source": (
            "results/stage2_confirm/h6/ — the SAME poor arm generations and "
            "scores the registered contrast used. No poor arm is rebuilt or "
            "regenerated here."),
        "base_arm": A.BASE_ARM,
        "chunks": {CHUNK: {"arms": sorted(ARMS_D3),
                           "n_prompts": len(chunk_rows),
                           "models": [A.PRIMARY_MODEL]}},
        "n_logical_renders": len(index_rows),
        "n_unique_prompts": len(chunk_rows),
        "n_duplicate_prompt_rows": n_dupes,
        "n_items": len(seen),
        "n_subjects": len(per_subject),
        "eligibility": summary["eligibility"],
        "per_subject": per_subject,
        "generation": {"primary_model": A.PRIMARY_MODEL,
                       "temperature": A.GEN_TEMPERATURE,
                       "max_output_tokens": A.GEN_MAX_OUTPUT_TOKENS,
                       "max_answer_words": OE.MAX_ANSWER_WORDS,
                       "instruction_tail_sha256": OE.INSTRUCTION_SHA256,
                       "template_sha256": OE.TEMPLATE_SHA256},
        "generated_utc": A.now(),
    }
    S.write_json(D3_DIR / "render_manifest.json", manifest)
    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_measure(summary: dict) -> None:
    print(f"\n=== H6 rich-arm supply at D_min = {D_MIN_EXPLORATORY} "
          f"(EXPLORATORY) ===")
    print(f"subjects carrying items: {summary['n_with_items']}")
    for budget in A.BUDGETS:
        e = summary["eligibility"][str(budget)]
        print(f"\nB = {budget}")
        print(f"  registered-eligible (D_min = 2):        "
              f"{e['n_registered_eligible']}")
        print(f"  D_min = 3 rich arm fills on its own:    "
              f"{e['n_rich_d3_fills']}")
        print(f"  EXPLORATORY eligible (both conditions): {e['n_eligible']}  "
              f"(lost {e['n_lost_vs_registered']} vs registered)")
        print(f"  items over eligible subjects:           "
              f"{e['n_items_eligible']}")
        print(f"  subjects with >=1 depth>=3 chain at all: "
              f"{e['n_subjects_with_any_d3_chain']}")
        print(f"  root share of rich-arm words: min {e['root_share_min']}, "
              f"median {e['root_share_median']}, max {e['root_share_max']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("measure", "render"))
    args = ap.parse_args(argv)

    if args.command == "measure":
        print_measure(measure(write=True))
        return 0

    manifest = render()
    print_measure(json.loads((D3_DIR / "arms_d3.json").read_text()))
    print(f"\n=== render ===")
    print(f"  {CHUNK}: {manifest['n_unique_prompts']} prompts, arms "
          f"{sorted(ARMS_D3)}, model {A.PRIMARY_MODEL}")
    print(f"  logical renders {manifest['n_logical_renders']}, duplicates "
          f"{manifest['n_duplicate_prompt_rows']}")
    print(f"  items {manifest['n_items']}, subjects {manifest['n_subjects']}")
    n_ident = sum(1 for r in manifest["per_subject"].values()
                  for a in r["arms"].values()
                  if a.get("identical_to_registered_rich"))
    print(f"  arm blocks byte-identical to the registered rich arm: {n_ident}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
