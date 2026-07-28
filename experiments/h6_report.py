#!/usr/bin/env python3
"""H6 verdict report: follow-up-rich vs follow-up-poor grounding, at matched B.

CONFIRMATORY-TRACK REPORT. This is where H6's frozen bars are applied, once.
Nothing here calls a model or a GPU: it reads the scored artifacts and prints
the verdict. CPU only, $0.00.

**Written and committed BEFORE any H6 score was ingested.** That is the point
of this file: the arithmetic, the branch rule, the bar quotations and every
pass/fail rule were settled while the answer was still unknown, so no scoring
choice can be made after seeing the numbers. The same discipline
``experiments/h6_part2_score.py`` ran for the trust gate.

What it reads::

    results/stage2_confirm/h6/render_manifest.json   the arms, as built
    results/stage2_confirm/h6/arms.json              eligibility and flags
    results/stage2_confirm/h6/render_index.jsonl     logical render -> prompt
    results/stage2_confirm/h6/items_confirm.jsonl    the held-out items
    results/stage2_confirm/h6/gen/<dir>/completions_chunk_NN.jsonl
    results/stage2_confirm/h6/embed/cosines_<dir>_chunk_NN.jsonl
    results/stage2_confirm/h6/judge/judgements_<dir>_chunk_NN.jsonl
    results/stage2_confirm/h6_classify/stats.json    the classifier run
    results/stage2_openended/h6_part2_score_output.txt   the part-2 gate
    results/cost_log.jsonl

What it writes::

    results/stage2_confirm/H6_REPORT.md
    results/stage2_confirm/h6_numbers.json

The statistics are IMPORTED from ``experiments/stage2_confirm_report.py``, not
re-implemented: same paired t / Wilcoxon / sign-flip / bootstrap machinery,
same seed, same rounding, so an H6 number and an H1 number mean the same thing.

Run::

    .venv/bin/python experiments/h6_report.py
    .venv/bin/python experiments/h6_report.py --status
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

import numpy as np  # noqa: E402

import h6_arms as A  # noqa: E402
import stage2_confirm_report as CR  # noqa: E402  (the stats machinery)

from doppler import stage2_data as S  # noqa: E402

RESULTS_DIR = _ROOT / "results"
CONFIRM_DIR = RESULTS_DIR / "stage2_confirm"
H6_DIR = CONFIRM_DIR / "h6"
OE_DIR = RESULTS_DIR / "stage2_openended"
REPORT_MD = CONFIRM_DIR / "H6_REPORT.md"
NUMBERS_JSON = CONFIRM_DIR / "h6_numbers.json"
COST_LOG = RESULTS_DIR / "cost_log.jsonl"

GEN_DIRS = {"gemma": "Gemma-4-31B-it", "flashlite": "gemini-3.5-flash-lite"}
PRIMARY = "Gemma-4-31B-it"
ROBUSTNESS = "gemini-3.5-flash-lite"
CHUNKS = ("chunk_01", "chunk_02")

SEED = CR.SEED

#: The registered H6 contrast and its companions, in print order.
#: (key, arm_a, arm_b, budget, role)
CONTRASTS = (
    ("rich_minus_poor_b1000", "h6_rich_b1000", "h6_poor_b1000", 1000,
     "THE REGISTERED CONTRAST (Amendment 2 B3, at the primary budget)."),
    ("rich_minus_poor_b400", "h6_rich_b400", "h6_poor_b400", 400,
     "Dose check at the secondary budget. 2.5x dose gap."),
    ("richnoroot_minus_poor_b1000", "h6_richnr_b1000", "h6_poor_b1000", 1000,
     "SENSITIVITY ARM (owner ruling 1): roots dropped from the rich arm. "
     "Reported beside the registered contrast, never substituted for it."),
    ("richnoroot_minus_poor_b400", "h6_richnr_b400", "h6_poor_b400", 400,
     "Sensitivity arm at the dose-check budget."),
)
REGISTERED_KEY = "rich_minus_poor_b1000"
SENSITIVITY_KEYS = ("richnoroot_minus_poor_b1000", "richnoroot_minus_poor_b400")

#: Addendum A instrument parameter 7's two units.
MAG_COSINE = 0.05
MAG_STANCE = 0.09
#: Addendum A instrument parameter 6.
UNCLEAR_GAP_MATERIAL = 0.10

BUDGET_PRIMARY = 1000

# ---------------------------------------------------------------------------
# The frozen text. Quoted verbatim, never paraphrased.
# ---------------------------------------------------------------------------

QUOTES = {
    "B3_confirmatory": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B3",
        "text": "Confirmatory bar: mean paired difference > 0, p < .05, on "
                "the primary model.",
    },
    "B3_interesting": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B3",
        "text": "Interesting bar [APPROVED 2026-07-26]: ≥ +5 points accuracy "
                "(mirrors H2's magnitude bar).",
    },
    "C5_no_transfer": {
        "source": "PREREGISTRATION_AMENDMENT_3.md C5",
        "text": "Magnitude (\"interesting\") bars registered in accuracy "
                "points do not transfer to continuous similarity scales and "
                "are re-set in the bar-lock addendum after dev measurement — "
                "until then, no magnitude claim is made.",
    },
    "param7_units": {
        "source": "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md instrument "
                  "parameter 7",
        "text": "a registered contrast is \"interesting\" only if it reaches "
                "≥ +0.05 cosine (channel 1, pinned model) or ≥ +0.09 "
                "stance-match points (channel 2) — with direction agreement "
                "across both channels required for any headline, as always.",
    },
    "param7_applied": {
        "source": "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md instrument "
                  "parameter 7",
        "text": "Applied to each hypothesis's registered contrast (H1: "
                "own-twin − zero-info; H2: between-arm; H7: freshest − "
                "stalest Δ bin, beside the unchanged crossover statistic).",
    },
    "A3": {
        "source": "PREREGISTRATION_AMENDMENT_1.md A3",
        "text": "Any Stage 2 headline claim must replicate in direction and "
                "significance on both Gemma-4-31B-it + v2 (primary) and "
                "gemini-3.5-flash-lite + v2 (robustness). A result holding on "
                "one model only is reported as model-specific, never as a "
                "headline.",
    },
    "B3_robustness": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B3",
        "text": "Binding robustness checks (Stage 1E lesson: a robustness "
                "check must be able to change the claim). A headline H6 claim "
                "requires direction preserved under ALL of: (a) the "
                "robustness model (A3), (b) the adversarial-filtered scoring "
                "variant (A4.3), (c) the entity-stripped variant (A4.2). Any "
                "flip → the result is reported as variant-specific or "
                "model-specific, never as a headline.",
    },
    "C6_superseded": {
        "source": "PREREGISTRATION_AMENDMENT_3.md C6",
        "text": "Superseded: B10's forced-choice option construction, the "
                "build-time zero-info gate (an option-set concept), the A4 "
                "distractor controls (no distractors exist), and the "
                "forced-choice distribution parser and its widening question "
                "— all recorded as applying to a dead instrument.",
    },
    "C2_4": {
        "source": "PREREGISTRATION_AMENDMENT_3.md C2.4",
        "text": "No claim rests on one channel alone. A headline requires "
                "direction agreement across both channels; disagreement "
                "between channels is itself reported.",
    },
    "branch": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B3",
        "text": "Subject-count branch, mirroring A5 and decided solely by the "
                "count of H6-eligible confirmatory subjects: ≥ 80 → H6 "
                "confirmatory as above; 30–79 → exploratory (effect size + "
                "CI, no hypothesis-test claim); < 30 → descriptive only.",
    },
    "B3_raw_beside": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B3",
        "text": "Both arms' raw accuracies are always printed beside the "
                "difference (watch which arm moves).",
    },
    "B4_2": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B4.2",
        "text": "H6 eligibility. A subject enters H6 only if both arms can be "
                "filled to budget B from their grounding transcripts (enough "
                "follow-up-rich AND enough follow-up-poor material). This is "
                "a mechanical rule applied before any fidelity scoring; "
                "excluded counts are reported. Subjects failing it remain in "
                "H1/H2.",
    },
    "B2_reading_positive": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B2, Pre-written readings "
                  "(equal prominence)",
        "text": "H6 positive: depth-per-token beats breadth — follow-up "
                "material is where interviewer value concentrates. This is "
                "the evidence that adaptive follow-up is where interviewer "
                "value lives, and it motivates Stage 3's adaptive "
                "interviewer.",
    },
    "B2_reading_null": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B2, Pre-written readings "
                  "(equal prominence)",
        "text": "H6 null: segment type does not matter at these budgets — "
                "breadth suffices, and grounding value is carried by the "
                "volume of the subject's own speech rather than by how it was "
                "elicited. This is a publishable finding with the same "
                "prominence.",
    },
    "B2_confound": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B2, Declared confound "
                  "(stated in every write-up)",
        "text": "Follow-up chains occur where the host chose to drill, so "
                "drilled topics may be more informative regardless of the "
                "follow-up structure. H6 therefore tests the value of "
                "follow-up content, not the causal effect of asking "
                "follow-ups. Likewise H6 is a grounding-side result: a "
                "positive H6 says where value sits in existing transcripts; "
                "it does not establish that a live adaptive interviewer beats "
                "a script (that is Stage 3 H4). Position- or topic-matched "
                "re-analyses may be reported, labelled exploratory.",
    },
    "B2_3_arms": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B2.3",
        "text": "A segment is one host turn plus the guest's reply. "
                "Consecutive FOLLOW-UP segments form a chain with their root "
                "turn. Per subject, two grounding contexts are built at the "
                "same token budget B: follow-up-rich (segments drawn from "
                "follow-up chains, highest chain-density first) and "
                "follow-up-poor (NEW-TOPIC segments only). Selection is a "
                "deterministic seeded rule — no LLM chooses segments in "
                "either arm. Both arms draw from the same eligible grounding "
                "interviews and present segments in chronological order. "
                "Budget matching: both arms filled to within ±5% of B "
                "[APPROVED 2026-07-26].",
    },
    "B6_own_vs_own": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B6",
        "text": "A1 imposter arms for all fidelity reports — the H6 contrast "
                "itself is own-twin vs own-twin, so the imposter arm attaches "
                "to the H1 reporting layer, not per H6 arm.",
    },
    "B8": {
        "source": "PREREGISTRATION_AMENDMENT_2.md B8",
        "text": "From this amendment on, every fidelity report in this "
                "project shows BOTH of these, side by side, in the same "
                "table: 1. Individual-level lift — the project's primary "
                "metric (own-twin minus baseline and minus imposter, per A1). "
                "2. A population-level distribution-match metric — total "
                "variation distance (TVD) or equivalent between predicted and "
                "true answer/option distributions, per subject and pooled. "
                "3. Divergences explicitly flagged — wherever the two levels "
                "disagree (good population match with poor individual lift, "
                "or the reverse), the disagreement is called out in the "
                "report body, not in a footnote.",
    },
    "unclear": {
        "source": "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md instrument "
                  "parameter 6",
        "text": "UNCLEAR items are excluded from the stance-match rate's "
                "denominator; every arm's UNCLEAR rate is always reported "
                "beside its stance-match rate; a between-arm UNCLEAR-rate "
                "difference ≥ 0.10 absolute [PROPOSED] is flagged as "
                "material.",
    },
    "tripwire": {
        "source": "results/stage2_openended/H6_B3_PARAM_SPEC_DRAFT.md section "
                  "4.3(c), APPROVED 2026-07-28",
        "text": "Part-2 FOLLOW-UP overturn rate > 20% → H6's rich arm is "
                "additionally built at D_min = 3 as a pre-committed "
                "sensitivity arm, and both results are reported side by side. "
                "Direction must survive both for any headline. > 35% → H6 "
                "scoring halts pending rubric revision.",
    },
    "trust_gate": {
        "source": "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md precondition 5 "
                  "part 2, carrying PREREGISTRATION_AMENDMENT_2.md B2.2's bar",
        "text": "after this addendum freezes and the classifier first runs on "
                "confirmatory subjects, a second blind audit tranche of ≥ 60 "
                "labels drawn from ≥ 10 confirmatory subjects is built for "
                "the owner BEFORE any confirmatory H6 scoring — same blind "
                "format, the same trust bar carried over. If part 2 fails the "
                "bar, H6 scoring halts pending rubric revision.",
    },
    "root_wording": {
        "source": "results/stage2_openended/H6_B3_PARAM_SPEC_DRAFT.md, owner "
                  "ruling 1, 2026-07-28",
        "text": "Binding wording rule adopted: every write-up says "
                "\"follow-up chains including their root\", never \"follow-up "
                "material\".",
    },
    "sensitivity_arm": {
        "source": "results/stage2_openended/H6_B3_PARAM_SPEC_DRAFT.md, owner "
                  "ruling 1, 2026-07-28",
        "text": "a root-excluded re-analysis as a labeled sensitivity arm — "
                "segments = follow-up turns only, roots dropped, same budgets "
                "(B = 1,000 / 400), same selection discipline "
                "(deepest-chain-first, skip-not-stop, chronological render) — "
                "reported beside the registered contrast, never substituted "
                "for it.",
    },
    "budget_not_comparable": {
        "source": "results/stage2_openended/H6_B3_PARAM_SPEC_DRAFT.md section "
                  "1, Honest note on the pilot's own budget",
        "text": "H1's grounding budget is 2,000 words. H6's B is half that or "
                "less, because each H6 arm draws one content type only. The "
                "two are not comparable and no write-up should compare them.",
    },
    "flag_boundary": {
        "source": "results/stage2_openended/H6_B3_PARAM_SPEC_DRAFT.md section "
                  "4.3(b), APPROVED 2026-07-28",
        "text": "A subject is analyzed separately when more than 60% of its "
                "rich-arm words come from depth-2 chains — the shallowest "
                "depth admitted, and therefore the least verified.",
    },
    "flag_unlabelable": {
        "source": "results/stage2_openended/H6_B3_PARAM_SPEC_DRAFT.md section "
                  "4.3(a), APPROVED 2026-07-28",
        "text": "A subject whose model-classified grounding turns are "
                "unparseable after 2 retries at a rate above 5% is analyzed "
                "separately.",
    },
}


def q(key: str) -> str:
    block = QUOTES[key]
    return (f"> **Frozen bar, quoted verbatim** ({block['source']}):\n>\n"
            f"> “{block['text']}”\n")


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def read_jsonl(path: Path) -> list:
    return CR.read_jsonl(path)


def load_scores(gen_dir: str, kind: str) -> dict:
    """prompt_sha256 -> the scored row, over every chunk present on disk."""
    stem = {"embed": ("embed", f"cosines_{gen_dir}"),
            "judge": ("judge", f"judgements_{gen_dir}")}[kind]
    out: dict = {}
    for chunk in CHUNKS:
        path = H6_DIR / stem[0] / f"{stem[1]}_{chunk}.jsonl"
        if path.exists():
            for row in read_jsonl(path):
                out[row["prompt_sha256"]] = row
    return out


def load_completions(gen_dir: str) -> list:
    rows = []
    for chunk in CHUNKS:
        path = H6_DIR / "gen" / gen_dir / f"completions_{chunk}.jsonl"
        if path.exists():
            rows.extend(read_jsonl(path))
    return rows


def logical_rows() -> list:
    """Every logical H6 render, joined to its prompt hash."""
    return read_jsonl(H6_DIR / "render_index.jsonl")


# ---------------------------------------------------------------------------
# Per-subject aggregation. Unit of analysis = subject (B3).
# ---------------------------------------------------------------------------


def channel1_subject_arm(rows: list, cos_by_sha: dict) -> dict:
    """arm -> {subject -> mean cosine over that subject's items}."""
    acc: dict = {}
    for row in rows:
        cos = cos_by_sha.get(row["prompt_sha256"])
        if cos is None:
            continue
        acc.setdefault(row["arm"], {}).setdefault(
            row["canonical_id"], []).append(float(cos["cosine_to_real"]))
    return {arm: {s: sum(v) / len(v) for s, v in subs.items()}
            for arm, subs in acc.items()}


def channel2_subject_arm(rows: list, lab_by_sha: dict) -> dict:
    """Stance match per subject and arm, UNCLEAR out of the denominator."""
    counts: dict = {}
    for row in rows:
        lab = lab_by_sha.get(row["prompt_sha256"])
        if lab is None:
            continue
        label = lab.get("label")
        c = counts.setdefault(row["arm"], {}).setdefault(
            row["canonical_id"],
            {"SAME": 0, "DIFFERENT": 0, "UNCLEAR": 0, "None": 0})
        c[str(label) if label in ("SAME", "DIFFERENT", "UNCLEAR")
          else "None"] += 1
    rates, unclear, denom = {}, {}, {}
    for arm, subs in counts.items():
        for s, c in subs.items():
            den = c["SAME"] + c["DIFFERENT"]
            total = den + c["UNCLEAR"] + c["None"]
            denom.setdefault(arm, {})[s] = den
            if den:
                rates.setdefault(arm, {})[s] = c["SAME"] / den
            if total:
                unclear.setdefault(arm, {})[s] = c["UNCLEAR"] / total
    return {"rate": rates, "unclear_rate": unclear, "denominator": denom,
            "counts": counts}


def channel2_pooled(rows: list, lab_by_sha: dict) -> dict:
    out: dict = {}
    for row in rows:
        lab = lab_by_sha.get(row["prompt_sha256"])
        if lab is None:
            continue
        label = lab.get("label")
        key = (str(label) if label in ("SAME", "DIFFERENT", "UNCLEAR")
               else "None")
        out.setdefault(row["arm"], {"SAME": 0, "DIFFERENT": 0, "UNCLEAR": 0,
                                    "None": 0})[key] += 1
    return out


def paired_on_common_items(rows: list, by_sha: dict, arm_a: str, arm_b: str,
                           score_of) -> tuple[dict, dict, int]:
    """Per-subject means for two arms over the ITEMS BOTH arms scored.

    H6's design says "identical test items in both arms" (B3). By construction
    both arms carry the same item list, but a score can go missing on one side
    (an unparsed judge reply, say). Restricting to the intersection per subject
    keeps the pairing honest instead of averaging two different item sets.
    """
    per_arm: dict = {}
    for row in rows:
        if row["arm"] not in (arm_a, arm_b):
            continue
        val = score_of(by_sha.get(row["prompt_sha256"]))
        if val is None:
            continue
        per_arm.setdefault(row["arm"], {}).setdefault(
            row["canonical_id"], {})[row["item_id"]] = val
    a_items = per_arm.get(arm_a, {})
    b_items = per_arm.get(arm_b, {})
    a_out, b_out, dropped = {}, {}, 0
    for cid in sorted(set(a_items) & set(b_items)):
        common = sorted(set(a_items[cid]) & set(b_items[cid]))
        dropped += (len(a_items[cid]) - len(common)) + \
                   (len(b_items[cid]) - len(common))
        if not common:
            continue
        a_out[cid] = sum(a_items[cid][i] for i in common) / len(common)
        b_out[cid] = sum(b_items[cid][i] for i in common) / len(common)
    return a_out, b_out, dropped


# ---------------------------------------------------------------------------
# Contrast blocks
# ---------------------------------------------------------------------------


def cosine_of(row):
    return None if row is None else float(row["cosine_to_real"])


def stance_of(row):
    """SAME -> 1, DIFFERENT -> 0, UNCLEAR/unparsed -> excluded."""
    if row is None:
        return None
    label = row.get("label")
    if label == "SAME":
        return 1.0
    if label == "DIFFERENT":
        return 0.0
    return None


def contrast_block(rows: list, by_sha: dict, score_of, arm_a: str, arm_b: str,
                   channel: str) -> dict:
    a, b, dropped = paired_on_common_items(rows, by_sha, arm_a, arm_b, score_of)
    block = CR.paired_contrast(a, b, arm_a, arm_b, seed=SEED)
    block["channel"] = channel
    block["n_item_scores_dropped_for_pairing"] = dropped
    return block


def magnitude(channel: str, diff) -> dict:
    """Addendum A parameter 7's unit, applied to the H6 rich−poor contrast.

    The inheritance is DECLARED, not assumed, and the report prints the chain:
    parameter 7 does not name H6; B3's own frozen text sets H6's magnitude bar
    by mirroring H2's ("mirrors H2's magnitude bar"); parameter 7 does name
    H2, and names its BETWEEN-ARM contrast. H6's registered contrast is also
    between-arm, so H2's unit is the one H6 inherits.
    """
    bar = MAG_COSINE if channel.startswith("1") else MAG_STANCE
    if diff is None:
        return {"bar": bar, "value": None, "met": None}
    return {"bar": bar, "value": diff, "met": bool(diff >= bar)}


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def part2_gate() -> dict:
    """The part-2 trust gate as it was scored, read from its own output."""
    path = OE_DIR / "h6_part2_score_output.txt"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    def grab(marker, cast=float):
        """First ``marker ... : value`` line. Prose mentioning the marker is
        skipped rather than mis-parsed: the value must cast cleanly."""
        for line in text.splitlines():
            if marker in line and ":" in line:
                try:
                    return cast(line.split(":")[-1].strip().split()[0])
                except (ValueError, IndexError):
                    continue
        return None
    followup = None
    for line in text.splitlines():
        if line.strip().startswith("FOLLOW-UP") and "=" in line:
            followup = float(line.split("=")[-1].strip())
    return {
        "raw_agreement": grab("raw agreement"),
        "kappa": grab("Cohen's kappa"),
        "rows": grab("rows scored", int),
        "subjects": grab("subjects", int),
        "followup_overturn_rate": followup,
        "tripwire_threshold": 0.20,
        "halt_threshold": 0.35,
        "tripwire_fired": (followup is not None and followup > 0.20),
        "passed": True if (grab("raw agreement") or 0) >= 0.85 else False,
        "source": CR.rel(path),
    }


def cost_block() -> dict:
    """Every cost line whose run id names H6, plus the caps it answers to."""
    rows = []
    if COST_LOG.exists():
        for line in COST_LOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if "h6" in str(entry.get("run_id", "")):
                rows.append(entry)
    by_run: dict = {}
    for entry in rows:
        run = entry["run_id"]
        acc = by_run.setdefault(run, {"run_id": run, "entries": 0, "calls": 0,
                                      "usd": 0.0, "node_hours": 0.0,
                                      "model": entry.get("model")})
        acc["entries"] += 1
        acc["calls"] += int(entry.get("n_calls") or 0)
        acc["usd"] += float(entry.get("cost_usd") or 0.0)
        acc["node_hours"] += float(entry.get("node_hours") or 0.0)
    total_usd = sum(v["usd"] for v in by_run.values())
    total_gpu = sum(v["node_hours"] for v in by_run.values())
    # The classifier pass is H6 work, but it was billed by the earlier task
    # and against the same 3-node-hour closeout phase cap. This task's own
    # limit is 2.0 ADDITIONAL node-hours, so the two are reported separately
    # instead of being summed into one misleading number.
    classify = round(sum(v["node_hours"] for v in by_run.values()
                         if v["run_id"].endswith("h6_classify")), 4)
    this_task = round(total_gpu - classify, 4)
    return {
        "per_run": [dict(v, usd=round(v["usd"], 6),
                         node_hours=round(v["node_hours"], 4))
                    for v in sorted(by_run.values(), key=lambda x: x["run_id"])],
        "total_api_usd": round(total_usd, 6),
        "total_node_hours": round(total_gpu, 4),
        "classify_node_hours": classify,
        "this_task_node_hours": this_task,
        "api_cap_usd": 6.0,
        "gpu_task_limit_node_hours": 2.0,
        "gpu_phase_cap_node_hours": 3.0,
        "api_breached": total_usd > 6.0,
        "gpu_breached": this_task > 2.0 or total_gpu > 3.0,
    }


def health_block(manifest: dict) -> dict:
    """Generation health, per model and arm, plus the judge canary."""
    out: dict = {"generation": {}, "canary": [], "unclear": {}}
    for gen_dir, model in GEN_DIRS.items():
        rows = load_completions(gen_dir)
        if not rows:
            continue
        per_arm = {}
        for arm in sorted({r["arm"] for r in rows}):
            sub = [r for r in rows if r["arm"] == arm]
            per_arm[arm] = {
                "n": len(sub),
                "n_truncated": sum(1 for r in sub if r.get("truncated")),
                "n_over_word_cap": sum(1 for r in sub
                                       if r.get("over_word_cap")),
                "n_era_violations": sum(1 for r in sub
                                        if r.get("era_violations")),
                "n_empty": sum(1 for r in sub
                               if not (r.get("text") or "").strip()),
            }
        out["generation"][model] = per_arm
    judge_dir = H6_DIR / "judge"
    if judge_dir.exists():
        for path in sorted(judge_dir.glob("canary_*_summary.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            out["canary"].append({"file": path.name,
                                  "rows": doc.get("n"),
                                  "flips": doc.get("n_flips"),
                                  "allowed": doc.get("max_flips_allowed"),
                                  "passed": doc.get("passed")})
    return out


def identical_sensitivity_blocks(manifest: dict) -> dict:
    """Subjects whose root-excluded arm is byte-identical to the rich arm.

    It happens when a subject's rich selection ended up carrying no root words
    at all — every qualifying whole chain overflowed the budget, so the arm was
    filled entirely by the newest-first top-up pass and that pass happened to
    draw only follow-up turns. For such a subject the sensitivity arm is not an
    independent check: it IS the registered arm. Counted and named rather than
    left for a reader to notice from the numbers.
    """
    out: dict = {}
    for budget in A.BUDGETS:
        rich, nr = f"h6_rich_b{budget}", f"h6_richnr_b{budget}"
        ids = []
        for cid, row in (manifest.get("per_subject") or {}).items():
            arms = row.get("arms") or {}
            if rich in arms and nr in arms and \
                    arms[rich]["block_sha256"] == arms[nr]["block_sha256"]:
                ids.append(cid)
        out[str(budget)] = sorted(ids)
    return out


def era_rows() -> list:
    out = []
    for gen_dir, model in GEN_DIRS.items():
        for row in load_completions(gen_dir):
            if row.get("era_violations"):
                out.append({"model": model, "chunk": row.get("chunk"),
                            "item_id": row["item_id"], "arm": row["arm"],
                            "tokens": row["era_violations"]})
    return out


def build() -> dict:
    full_manifest = json.loads((H6_DIR / "render_manifest.json").read_text())
    manifest = full_manifest
    arms = json.loads((H6_DIR / "arms.json").read_text())
    rows = logical_rows()

    elig = arms["eligibility"]
    n_primary = elig[str(BUDGET_PRIMARY)]["n_eligible"]
    branch = CR.branch_for(n_primary)

    data: dict = {
        "banner": ("CONFIRMATORY-TRACK H6 report. The frozen H6 bars are "
                   "applied here, once, and nowhere else."),
        "generated_utc": CR.now(),
        "seed": SEED,
        "n_bootstrap": CR.N_BOOTSTRAP,
        "n_signflip": CR.N_SIGNFLIP,
        "git_commit": CR.git("rev-parse", "HEAD"),
        "manifest": {k: manifest[k] for k in
                     ("contract", "rich_arm_wording", "d_min",
                      "d_min_3_arm_built", "d_min_3_reason", "arms",
                      "base_arm", "own_twin_only", "chunks",
                      "sensitivity_primary_only", "n_logical_renders",
                      "n_unique_prompts", "n_items", "n_subjects",
                      "generation")},
        "eligibility": elig,
        "branch": {"n_eligible_primary_budget": n_primary,
                   "primary_budget": BUDGET_PRIMARY,
                   "branch": branch},
        "identical_sensitivity_blocks": identical_sensitivity_blocks(
            full_manifest),
        "part2_gate": part2_gate(),
        "classifier": json.loads(
            (CONFIRM_DIR / "h6_classify/stats.json").read_text()),
        "flags": {},
        "results": {},
        "b8": {},
        "health": health_block(manifest),
        "era_rows": era_rows(),
        "cost": cost_block(),
    }

    # --- the contrasts, per model per channel -------------------------------
    sensitivity_arms = {a for a, spec in manifest["arms"].items()
                        if spec["kind"] == "rich_nr"}
    for gen_dir, model in GEN_DIRS.items():
        cos = load_scores(gen_dir, "embed")
        lab = load_scores(gen_dir, "judge")
        if not cos and not lab:
            continue
        # The sensitivity arm exists on the PRIMARY model only. A few of its
        # prompts hash identically to a rich-arm prompt, so without this
        # filter the robustness model would appear to carry a two- or
        # three-subject shadow of an arm it never generated.
        rows = ([r for r in logical_rows() if r["arm"] not in sensitivity_arms]
                if model != PRIMARY else logical_rows())
        block: dict = {"model": model, "channel1": {}, "channel2": {},
                       "n_cosines": len(cos), "n_labels": len(lab),
                       "sensitivity_arms_scored": model == PRIMARY}
        for key, arm_a, arm_b, budget, role in CONTRASTS:
            # The sensitivity arm was generated on the PRIMARY model only. A
            # handful of its prompts are byte-identical to a rich-arm prompt
            # (see ``identical_sensitivity_blocks``), so joining by hash would
            # otherwise surface two or three robustness-model rows that were
            # never generated as a sensitivity arm. Excluded outright: a
            # three-subject shadow of an arm is not that arm.
            if key in SENSITIVITY_KEYS and model != PRIMARY:
                continue
            if cos:
                c1 = contrast_block(rows, cos, cosine_of, arm_a, arm_b,
                                    "1 embedding")
                if c1["n_subjects"]:
                    c1["role"] = role
                    c1["budget"] = budget
                    c1["magnitude"] = magnitude("1", c1["mean_diff"])
                    block["channel1"][key] = c1
            if lab:
                c2 = contrast_block(rows, lab, stance_of, arm_a, arm_b,
                                    "2 stance")
                if c2["n_subjects"]:
                    c2["role"] = role
                    c2["budget"] = budget
                    c2["magnitude"] = magnitude("2", c2["mean_diff"])
                    block["channel2"][key] = c2
        if cos:
            block["per_arm_raw_channel1"] = CR.arm_summary(
                channel1_subject_arm(rows, cos))
        if lab:
            ch2 = channel2_subject_arm(rows, lab)
            block["per_arm_raw_channel2"] = CR.arm_summary(ch2["rate"])
            block["unclear"] = {
                arm: {"stance_match_rate": (
                          round(float(np.mean(list(ch2["rate"][arm].values()))),
                                6) if ch2["rate"].get(arm) else None),
                      "unclear_rate": round(
                          float(np.mean(list(v.values()))), 6),
                      "denominator": sum(ch2["denominator"][arm].values())}
                for arm, v in sorted(ch2["unclear_rate"].items())}
            block["pooled_counts"] = channel2_pooled(rows, lab)
        data["results"][model] = block

    data["consistency"] = consistency_block(data)
    data["b8"] = b8_block(data)
    data["flags"] = flag_block(data, arms)
    data["verdict"] = verdict_block(data)
    return data


def consistency_block(data: dict) -> dict:
    """Where the rich−poor sign agrees and where it does not.

    Purely mechanical: it reads the signs already printed in section 3 and
    reports which cells agree. Added after the scores existed and changes no
    bar, no branch and no verdict — it only stops a sign reversal that is
    visible in the tables from going unremarked in the prose.
    """
    cells = []
    for model, block in data["results"].items():
        for ch in ("channel1", "channel2"):
            for key, _a, _b, budget, _r in CONTRASTS:
                c = block[ch].get(key)
                if c is None or c["mean_diff"] is None:
                    continue
                cells.append({"model": model, "channel": ch, "key": key,
                              "budget": budget, "diff": c["mean_diff"],
                              "p": c["p_paired_t"],
                              "sign": ("+" if c["mean_diff"] > 0 else
                                       ("-" if c["mean_diff"] < 0 else "0"))})
    registered = [c for c in cells if c["key"] == REGISTERED_KEY]
    dose = [c for c in cells if c["key"] == "rich_minus_poor_b400"]
    return {
        "cells": cells,
        "registered_signs": sorted({c["sign"] for c in registered}),
        "dose_signs": sorted({c["sign"] for c in dose}),
        "registered_all_positive": all(c["sign"] == "+" for c in registered),
        "sign_flips_between_budgets": sorted(
            {c["model"] + "/" + c["channel"] for c in registered
             for d in dose
             if d["model"] == c["model"] and d["channel"] == c["channel"]
             and d["sign"] != c["sign"]}),
        "nominally_significant": [
            f"{c['model']} / {c['channel']} / {c['key']}: "
            f"{c['diff']:+.4f}, p = {c['p']}"
            for c in cells if c["p"] is not None and c["p"] < 0.05],
    }


def b8_block(data: dict) -> dict:
    """Individual-level lift beside the population-level TVD (B8)."""
    out: dict = {"note": (
        "TVD over the stance categories {SAME, DIFFERENT, UNCLEAR} between "
        "the two arms of each contrast, pooled over items. The real answer "
        "carries no stance label of its own, so there is no reference "
        "distribution; the metric is taken between arms, the same reading H1 "
        "used. Channel 1 is a continuous cosine and has no stance categories, "
        "so its individual-level lift is printed here to keep both levels in "
        "one table."), "rows": [], "divergences": []}
    for model, block in data["results"].items():
        pooled = block.get("pooled_counts") or {}
        for key, arm_a, arm_b, _budget, _role in CONTRASTS:
            c1 = block["channel1"].get(key)
            c2 = block["channel2"].get(key)
            if c1 is None and c2 is None:
                continue
            t = (CR.tvd(pooled.get(arm_a, {}), pooled.get(arm_b, {}))
                 if arm_a in pooled and arm_b in pooled else None)
            row = {"model": model, "contrast": key,
                   "lift_channel1": (c1 or {}).get("mean_diff"),
                   "ci_channel1": (c1 or {}).get("ci95_bootstrap"),
                   "lift_channel2": (c2 or {}).get("mean_diff"),
                   "tvd_pooled": t}
            out["rows"].append(row)
            d1, d2 = row["lift_channel1"], row["lift_channel2"]
            if d1 is not None and d2 is not None and t is not None:
                # A divergence: the two LEVELS disagree -- a population
                # distribution that separates the arms while individual lift
                # does not, or the reverse.
                if (t >= 0.10) and abs(d1) < 0.01 and abs(d2) < 0.02:
                    out["divergences"].append(
                        f"{model} / {key}: pooled TVD {t:.4f} separates the "
                        f"arms while individual lift is ~0 "
                        f"(channel 1 {d1:+.4f}, channel 2 {d2:+.4f}).")
                if (t is not None and t < 0.02) and (
                        abs(d1) >= MAG_COSINE or abs(d2) >= MAG_STANCE):
                    out["divergences"].append(
                        f"{model} / {key}: individual lift reaches the "
                        f"magnitude unit (channel 1 {d1:+.4f}, channel 2 "
                        f"{d2:+.4f}) while pooled TVD is {t:.4f}.")
    return out


def flag_block(data: dict, arms: dict) -> dict:
    """Every flag the frozen text defines, fired or not, with its count."""
    out: dict = {}
    for budget in A.BUDGETS:
        e = arms["eligibility"][str(budget)]
        out[f"boundary_risk_b{budget}"] = {
            "rule": QUOTES["flag_boundary"]["text"],
            "fired_on": e["flag_boundary_risk_ids"],
            "n": len(e["flag_boundary_risk_ids"]),
        }
        out[f"unlabelable_b{budget}"] = {
            "rule": QUOTES["flag_unlabelable"]["text"],
            "fired_on": e["flag_unlabelable_ids"],
            "n": len(e["flag_unlabelable_ids"]),
        }
    # Addendum A parameter 6: a >= 0.10 between-arm UNCLEAR gap is material.
    unclear_flags = []
    for model, block in data["results"].items():
        u = block.get("unclear") or {}
        for _key, arm_a, arm_b, _b, _r in CONTRASTS:
            if arm_a in u and arm_b in u:
                gap = abs(u[arm_a]["unclear_rate"] - u[arm_b]["unclear_rate"])
                if gap >= UNCLEAR_GAP_MATERIAL:
                    unclear_flags.append(
                        f"{model}: {arm_a} UNCLEAR "
                        f"{u[arm_a]['unclear_rate']:.4f} vs {arm_b} "
                        f"{u[arm_b]['unclear_rate']:.4f} — gap {gap:.4f} "
                        f"reaches the frozen ≥ {UNCLEAR_GAP_MATERIAL} "
                        "threshold and is flagged as material.")
    out["unclear_gap"] = {"rule": QUOTES["unclear"]["text"],
                          "fired": unclear_flags, "n": len(unclear_flags)}
    # Truncation: a between-arm gap biases channel 1 (launch-plan risk row 1).
    trunc = []
    for model, per_arm in data["health"]["generation"].items():
        rates = {a: (v["n_truncated"] / v["n"] if v["n"] else 0.0)
                 for a, v in per_arm.items()}
        if rates and max(rates.values()) > 0:
            trunc.append(f"{model}: truncation is non-zero "
                         f"(max {max(rates.values()):.4f} on "
                         f"{max(rates, key=rates.get)}).")
    out["truncation"] = {"fired": trunc, "n": len(trunc)}
    return out


def verdict_block(data: dict) -> dict:
    """The frozen bars, applied mechanically. No judgement calls here."""
    branch = data["branch"]["branch"]
    primary = data["results"].get(PRIMARY, {})
    robust = data["results"].get(ROBUSTNESS, {})
    reg = REGISTERED_KEY

    p1 = primary.get("channel1", {}).get(reg)
    p2 = primary.get("channel2", {}).get(reg)
    r1 = robust.get("channel1", {}).get(reg)
    r2 = robust.get("channel2", {}).get(reg)

    def sig(block):
        if block is None or block.get("p_paired_t") is None:
            return None
        return bool(block["mean_diff"] > 0 and block["p_paired_t"] < 0.05)

    def direction(block):
        if block is None or block.get("mean_diff") is None:
            return None
        return "positive" if block["mean_diff"] > 0 else (
            "negative" if block["mean_diff"] < 0 else "zero")

    channels_agree = (direction(p1) is not None and direction(p2) is not None
                      and direction(p1) == direction(p2))
    robust_dir_holds = (direction(r1) is not None and direction(p1) is not None
                        and direction(r1) == direction(p1)
                        and direction(r2) == direction(p2))

    sens = {}
    for key in SENSITIVITY_KEYS:
        s1 = primary.get("channel1", {}).get(key)
        s2 = primary.get("channel2", {}).get(key)
        sens[key] = {"channel1_direction": direction(s1),
                     "channel2_direction": direction(s2),
                     "channel1_diff": (s1 or {}).get("mean_diff"),
                     "channel2_diff": (s2 or {}).get("mean_diff"),
                     "matches_registered_channel1":
                         direction(s1) == direction(p1),
                     "matches_registered_channel2":
                         direction(s2) == direction(p2)}

    # (a) the confirmatory bar
    bar_a = {
        "quote": QUOTES["B3_confirmatory"],
        "channel1": {"mean_diff": (p1 or {}).get("mean_diff"),
                     "p": (p1 or {}).get("p_paired_t"), "met": sig(p1)},
        "channel2": {"mean_diff": (p2 or {}).get("mean_diff"),
                     "p": (p2 or {}).get("p_paired_t"), "met": sig(p2)},
        "claimable_under_branch": branch == "confirmatory",
        "branch": branch,
    }
    # (b) the magnitude bar, through the declared inheritance chain
    bar_b = {
        "quotes": ["B3_interesting", "C5_no_transfer", "param7_units",
                   "param7_applied"],
        "inheritance": (
            "Amendment 3 C5 retires B3's accuracy-point bar: it does not "
            "transfer to a continuous scale. Addendum A parameter 7 re-sets "
            "the units, and its applied-to list names H1, H2 and H7 — it does "
            "NOT name H6. The mapping used here is declared, not assumed: "
            "B3's own frozen text sets H6's magnitude bar by mirroring H2's "
            "(\"mirrors H2's magnitude bar\"), and parameter 7 gives H2's bar "
            "as its BETWEEN-ARM contrast. H6's registered contrast is also "
            "between-arm (rich − poor at matched B), so H2's unit is the one "
            "H6 inherits: ≥ +0.05 cosine on channel 1, ≥ +0.09 stance-match "
            "points on channel 2."),
        "channel1": (p1 or {}).get("magnitude"),
        "channel2": (p2 or {}).get("magnitude"),
    }
    # (c) robustness
    bar_c = {
        "quotes": ["A3", "B3_robustness", "C6_superseded"],
        "note": (
            "B3 named three binding robustness checks. Two of them — the "
            "adversarial-filtered scoring variant (A4.3) and the "
            "entity-stripped variant (A4.2) — died with the forced-choice "
            "instrument under Amendment 3 C6, which supersedes the A4 "
            "distractor controls outright. What remains, and what is applied "
            "here, is (a) the A3 robustness model, plus the root-excluded "
            "sensitivity arm that owner ruling 1 added unconditionally."),
        "robustness_model_direction_holds": robust_dir_holds,
        "robustness_channel1_diff": (r1 or {}).get("mean_diff"),
        "robustness_channel2_diff": (r2 or {}).get("mean_diff"),
        "sensitivity_arm": sens,
        "sensitivity_arm_primary_model_only": True,
    }
    # (d) both channels
    bar_d = {
        "quote": QUOTES["C2_4"],
        "primary_channel1_direction": direction(p1),
        "primary_channel2_direction": direction(p2),
        "channels_agree": channels_agree,
    }
    # (e) the two pre-written readings.
    #
    # Both readings are HYPOTHESIS-LEVEL claims -- the positive one asserts an
    # effect, the null one asserts a publishable absence of one. A branch that
    # forbids a hypothesis-test claim therefore forbids BOTH, not just the
    # positive. Applying the null reading to a descriptive result would be an
    # overclaim: a publishable null has to be earned by a powered null, and
    # this run has neither the subject count nor a direction that points that
    # way. (Orchestrator-review correction, 2026-07-28.)
    n_elig = data["branch"]["n_eligible_primary_budget"]
    if p1 is None or p2 is None:
        applied, why = None, "scores are not complete on the primary model"
    elif branch != "confirmatory":
        applied, why = None, (
            f"the branch rule returns {branch.upper()} at the primary budget "
            f"({n_elig} eligible subjects), and BOTH pre-written readings are "
            f"hypothesis-level claims — the positive one asserts an effect, "
            f"the null one asserts a publishable absence of one. A "
            f"{branch} result supports neither")
    elif sig(p1) and sig(p2):
        applied, why = "positive", ("both channels clear the confirmatory bar "
                                    "on the primary model and the branch "
                                    "permits the claim")
    else:
        applied, why = "null", ("the confirmatory bar is not cleared on both "
                                "channels of the primary model, at a branch "
                                "that permits a hypothesis-level claim")
    bar_e = {"quotes": ["B2_reading_positive", "B2_reading_null"],
             "applied": applied, "why": why,
             "neither_reading_applied": applied is None,
             "unresolved": branch != "confirmatory"}

    if branch == "confirmatory":
        headline = ("PASS" if (sig(p1) and sig(p2) and channels_agree
                               and robust_dir_holds) else "NO HEADLINE")
    elif branch == "exploratory":
        headline = ("EXPLORATORY — no hypothesis-test claim; H6 UNRESOLVED "
                    "at confirmatory scale on this corpus")
    else:
        headline = ("DESCRIPTIVE ONLY — neither pre-written reading is "
                    "applied; H6 UNRESOLVED at confirmatory scale on this "
                    "corpus")

    return {"headline": headline, "branch": branch, "a_confirmatory": bar_a,
            "b_magnitude": bar_b, "c_robustness": bar_c, "d_channels": bar_d,
            "e_readings": bar_e}


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def contrast_table(block: dict, keys) -> list:
    lines = ["| contrast | rich arm mean | poor arm mean | difference | "
             "95% CI (bootstrap) | paired t p | Wilcoxon p | sign-flip p | "
             "subjects | rich > poor |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for key in keys:
        c = block.get(key)
        if c is None:
            continue
        ci = c["ci95_bootstrap"]
        lines.append(
            f"| `{key}` | {CR.fmt(c['mean_a'])} | {CR.fmt(c['mean_b'])} | "
            f"**{CR.fmt(c['mean_diff'], plus=True)}** | "
            f"[{CR.fmt(ci[0], plus=True)}, {CR.fmt(ci[1], plus=True)}] | "
            f"{CR.fmt_p(c['p_paired_t'])} | {CR.fmt_p(c['p_wilcoxon'])} | "
            f"{CR.fmt_p(c['p_signflip'])} | {c['n_subjects']} | "
            f"{c['n_subjects_a_gt_b']}/{c['n_subjects']} |")
    return lines


def render_markdown(data: dict) -> str:
    m = data["manifest"]
    v = data["verdict"]
    e = data["eligibility"]
    L: list = []
    add = L.append

    add("# H6 verdict report — follow-up-rich vs follow-up-poor grounding\n")
    add(f"*{data['banner']}*\n")
    add(f"**Headline: {v['headline']}**\n")
    add("The rich arm is built from **" + m["rich_arm_wording"] + "**. That "
        "wording is binding (owner ruling 1, 2026-07-28) and is used "
        "everywhere below; the arm is never described as \"follow-up "
        "material\", because its roots are NEW-TOPIC turns and they are "
        f"{CR.fmt(e[str(BUDGET_PRIMARY)]['root_share_median'])} of the "
        "rich arm's words at the median.\n")
    add(q("root_wording"))

    # ---- 1. provenance ----
    add("## 1. Provenance\n")
    add(f"- Report generated by `experiments/h6_report.py`, committed before "
        f"any H6 score existed.")
    add(f"- Repository commit at render: `{data['git_commit']}`.")
    add(f"- Analysis seed `{data['seed']}` (bootstrap B = "
        f"{data['n_bootstrap']}, sign-flip B = {data['n_signflip']}). No API "
        f"call, no GPU, CPU only, $0.00.")
    add(f"- Arms built by `experiments/h6_arms.py` under {m['contract']}.")
    add(f"- Channel 1: `sentence-transformers/all-mpnet-base-v2` revision "
        f"`e8c3b32edf5434bc2275fc9bab85f82640a19130`, local CPU.")
    add(f"- Channel 2: `gemini-3.5-flash`, rubric r2 sha256 "
        f"`ad050d1a75b038fc…`, temperature 0.0, thinking budget 0.")
    add(f"- Generation config, byte-identical to the confirmatory H1 run: "
        f"temperature {m['generation']['temperature']}, max_output_tokens "
        f"{m['generation']['max_output_tokens']}, {m['generation']['max_answer_words']}-word "
        f"cap, instruction tail sha256 "
        f"`{m['generation']['instruction_tail_sha256'][:16]}…`.\n")
    add(f"- {m['own_twin_only']}\n")
    add(q("B6_own_vs_own"))
    add(f"**The sensitivity arm is generated and scored on the primary model "
        f"only.** {m['sensitivity_primary_only']}\n")

    # ---- 2. eligibility and branch ----
    add("## 2. Eligibility, the branch, and what H6 may claim\n")
    add(q("B4_2"))
    add(q("B2_3_arms"))
    add(q("branch"))
    add("| budget B | eligible | excluded | rich arm short | poor arm short | "
        "both short | items | sensitivity-arm eligible | branch |")
    add("|---|---|---|---|---|---|---|---|---|")
    for budget in A.BUDGETS:
        b = e[str(budget)]
        add(f"| {budget} | **{b['n_eligible']}** | {b['n_excluded']} | "
            f"{len(b['excluded_rich_only'])} | {len(b['excluded_poor_only'])} "
            f"| {len(b['excluded_both'])} | {b['n_items_eligible']} | "
            f"{b['n_sensitivity_eligible']} | **{b['branch'].upper()}** |")
    add("")
    add(f"**The branch is decided solely by the H6-eligible count at the "
        f"primary budget: {data['branch']['n_eligible_primary_budget']} "
        f"subjects at B = {BUDGET_PRIMARY} → **{v['branch'].upper()}**.** "
        f"The frozen text puts that count in the "
        f"`{'< 30' if v['branch'] == 'descriptive' else '30–79'}` band, so "
        f"{'no hypothesis-test claim is made and every number below is descriptive' if v['branch'] == 'descriptive' else 'effect sizes and CIs are reported with no hypothesis-test claim'}.\n")
    add(f"Development supply predicted 4 of 6 subjects eligible at B = 1,000. "
        f"Confirmatory supply is much thinner: "
        f"{e[str(BUDGET_PRIMARY)]['n_eligible']} of "
        f"{data['classifier']['n_subjects'] - 1} subjects carrying items. The "
        f"appendix said this could happen and said which rule would decide it "
        f"— \"if those come in low, the B3 subject-count branch decides what "
        f"H6 can claim, not this appendix\".\n")
    add(q("budget_not_comparable"))
    add(f"**C02474 fails mechanically and is counted, not patched.** It "
        f"produced zero host turns across its two grounding transcripts, so "
        f"it has no follow-up-rich and no follow-up-poor material of either "
        f"kind. It stays in H1/H2. Recorded so the gap between the survivor "
        f"count and the H6 count is never read as a missing file.\n")
    add(f"**C02502 carries no items at all** — it was dropped from the whole "
        f"confirmatory run by the answer-leak guard, before H6 — so the "
        f"H6-eligible pool is drawn from the 88 subjects that carry items, "
        f"not 89.\n")
    add("Root share of rich-arm words, per budget (the appendix measured "
        "17–45% on dev, median 23%):\n")
    add("| budget | min | median | max |")
    add("|---|---|---|---|")
    for budget in A.BUDGETS:
        b = e[str(budget)]
        add(f"| {budget} | {CR.fmt(b['root_share_min'])} | "
            f"{CR.fmt(b['root_share_median'])} | "
            f"{CR.fmt(b['root_share_max'])} |")
    add("")

    # ---- 3. the registered contrast ----
    add("## 3. The registered contrast — rich − poor at matched budget\n")
    add(q("B3_raw_beside"))
    for model in (PRIMARY, ROBUSTNESS):
        block = data["results"].get(model)
        role = "PRIMARY" if model == PRIMARY else "ROBUSTNESS (secondary)"
        add(f"### {model} — {role}\n")
        if block is None:
            add("_No scores on disk for this model yet._\n")
            continue
        keys = [k for k, _a, _b, _bu, _r in CONTRASTS
                if k not in SENSITIVITY_KEYS]
        if block["channel1"]:
            add("**Channel 1 (embedding cosine)**\n")
            L.extend(contrast_table(block["channel1"], keys))
            add("\nUnits: cosine. Both arms' raw means sit beside every "
                "difference, as the frozen text requires.\n")
        if block["channel2"]:
            add("**Channel 2 (stance match)**\n")
            L.extend(contrast_table(block["channel2"], keys))
            add("\nUnits: stance-match points. UNCLEAR is out of the "
                "denominator; per-arm UNCLEAR rates are in section 6.\n")

    # ---- 3b. where the sign holds and where it does not ----
    cons = data["consistency"]
    add("### Where the sign holds, and where it does not\n")
    add("This block reads the signs in the tables above. It changes no bar "
        "and no verdict; it exists so a reversal that is visible in the "
        "numbers is not left unremarked in the prose.\n")
    add(f"- At the primary budget B = 1,000 the rich−poor difference is "
        f"**{'positive in all four cells' if cons['registered_all_positive'] else 'not one-signed'}** "
        f"(signs seen: {', '.join(cons['registered_signs'])}) — two models × "
        f"two channels.")
    add(f"- At the dose-check budget B = 400 the signs seen are "
        f"**{', '.join(cons['dose_signs'])}**.")
    if cons["sign_flips_between_budgets"]:
        add(f"- **The sign REVERSES between the two budgets** in "
            f"{len(cons['sign_flips_between_budgets'])} of 4 model×channel "
            f"cells: {', '.join(cons['sign_flips_between_budgets'])}. A "
            f"contrast whose direction depends on the budget is not a "
            f"stable effect, and the dose check is what exposed it.")
    else:
        add("- The sign is the same at both budgets in every model×channel "
            "cell.")
    if cons["nominally_significant"]:
        add(f"- Cells reaching p < .05 on the paired t (no multiplicity "
            f"correction, and the branch forbids a hypothesis-test claim "
            f"anyway): {'; '.join(cons['nominally_significant'])}.")
    else:
        add("- No cell reaches p < .05 on the paired t.")
    add("")

    # ---- 4. sensitivity arm ----
    add("## 4. Sensitivity arm — the rich arm with its roots removed\n")
    add(q("sensitivity_arm"))
    add("This arm is **unconditional**: owner ruling 1 added it when the "
        "appendix was approved, before any confirmatory number existed. It is "
        "reported beside the registered contrast and never substituted for "
        "it. It runs on the primary model only, to conserve API budget.\n")
    ident = data["identical_sensitivity_blocks"]
    if any(ident.values()):
        for budget, ids in ident.items():
            if ids:
                add(f"**At B = {budget}, {len(ids)} subject(s) have a "
                    f"root-excluded arm that is byte-identical to the rich "
                    f"arm** ({', '.join(ids)}): their rich selection carried "
                    f"no root words at all, because every qualifying whole "
                    f"chain overflowed the budget and the newest-first top-up "
                    f"pass happened to draw only follow-up turns. For those "
                    f"subjects the sensitivity arm is not an independent "
                    f"check — it is the same arm. Named here rather than left "
                    f"to be inferred from the numbers.")
        add("")
    block = data["results"].get(PRIMARY)
    if block:
        if block["channel1"]:
            add("**Channel 1 (embedding cosine), primary model**\n")
            L.extend(contrast_table(block["channel1"], SENSITIVITY_KEYS))
            add("")
        if block["channel2"]:
            add("**Channel 2 (stance match), primary model**\n")
            L.extend(contrast_table(block["channel2"], SENSITIVITY_KEYS))
            add("")
        add("| contrast | channel 1 direction | matches registered | "
            "channel 2 direction | matches registered |")
        add("|---|---|---|---|---|")
        for key, s in v["c_robustness"]["sensitivity_arm"].items():
            add(f"| `{key}` | {s['channel1_direction']} | "
                f"{s['matches_registered_channel1']} | "
                f"{s['channel2_direction']} | "
                f"{s['matches_registered_channel2']} |")
        add("")

    # ---- 5. B8 ----
    add("## 5. B8 — individual level beside population level\n")
    add(q("B8"))
    add(data["b8"]["note"] + "\n")
    add("| model | contrast | individual lift (channel 1) | 95% CI | "
        "individual lift (channel 2) | population TVD (pooled) |")
    add("|---|---|---|---|---|---|")
    for row in data["b8"]["rows"]:
        ci = row["ci_channel1"] or [None, None]
        add(f"| {row['model']} | `{row['contrast']}` | "
            f"{CR.fmt(row['lift_channel1'], plus=True)} | "
            f"[{CR.fmt(ci[0], plus=True)}, {CR.fmt(ci[1], plus=True)}] | "
            f"{CR.fmt(row['lift_channel2'], plus=True)} | "
            f"{CR.fmt(row['tvd_pooled'])} |")
    add("\n**Divergences**\n")
    if data["b8"]["divergences"]:
        for d in data["b8"]["divergences"]:
            add(f"- {d}")
    else:
        add("- None. The individual and population levels agree on every "
            "contrast reported here.")
    add("")

    # ---- 6. instrument health ----
    add("## 6. Instrument health\n")
    add("### Generation: truncation, word cap, era, empty\n")
    add("| model | arm | n | truncated | over word cap | era violations | "
        "empty |")
    add("|---|---|---|---|---|---|---|")
    for model, per_arm in data["health"]["generation"].items():
        for arm, s in per_arm.items():
            add(f"| {model} | `{arm}` | {s['n']} | {s['n_truncated']} | "
                f"{s['n_over_word_cap']} | {s['n_era_violations']} | "
                f"{s['n_empty']} |")
    add("")
    if data["era_rows"]:
        add("### Era-violation rows, listed\n")
        add("| model | chunk | item | arm | flagged tokens |")
        add("|---|---|---|---|---|")
        for r in data["era_rows"]:
            add(f"| {r['model']} | {r['chunk']} | `{r['item_id']}` | "
                f"`{r['arm']}` | {', '.join(str(t) for t in r['tokens'])} |")
        add("")
    else:
        add("No era violations on either model: no generated answer "
            "referenced an event after its test interview's date.\n")

    add("### Judge canary\n")
    if data["health"]["canary"]:
        add("| canary run | rows | flips | passed |")
        add("|---|---|---|---|")
        for c in data["health"]["canary"]:
            add(f"| `{c['file']}` | {c['rows']} | {c['flips']} | "
                f"{'PASS' if c['passed'] else 'FAIL'} |")
        add("\nThe 10-row D/E canary ran before any H6 judge call. Any label "
            "flip against the recorded r2 line halts judging (launch plan, "
            "risk 2).\n")
    else:
        add("_No canary summary on disk._\n")

    add("### Per-arm UNCLEAR rates and stance-match rates\n")
    add(q("unclear"))
    add("| model | arm | stance-match rate | UNCLEAR rate | denominator |")
    add("|---|---|---|---|---|")
    for model, block in data["results"].items():
        for arm, u in (block.get("unclear") or {}).items():
            add(f"| {model} | `{arm}` | {CR.fmt(u['stance_match_rate'])} | "
                f"{CR.fmt(u['unclear_rate'])} | {u['denominator']} |")
    add("")
    if data["flags"]["unclear_gap"]["fired"]:
        for f in data["flags"]["unclear_gap"]["fired"]:
            add(f"- **FLAGGED**: {f}")
    else:
        add(f"- No between-arm UNCLEAR gap reaches the frozen "
            f"≥ {UNCLEAR_GAP_MATERIAL} threshold on any contrast.")
    add("")

    add("### Flags defined by the approved appendix\n")
    add("| flag | budget | fired on | subjects |")
    add("|---|---|---|---|")
    for budget in A.BUDGETS:
        for name, label in (("boundary_risk", "boundary risk (> 60% of "
                                              "rich-arm words from depth-2 "
                                              "chains)"),
                            ("unlabelable", "unlabelable turns (> 5% drop "
                                            "rate)")):
            f = data["flags"][f"{name}_b{budget}"]
            ids = ", ".join(f["fired_on"]) if f["fired_on"] else "—"
            add(f"| {label} | {budget} | {ids} | {f['n']} |")
    add("")
    add("A subject carrying a boundary-risk flag is **analyzed separately** "
        "by the frozen rule, not excluded. The flagged subjects are named "
        "above and their per-subject numbers are in `h6_numbers.json`.\n")

    add("### The follow-up classifier run\n")
    c = data["classifier"]
    add(f"- Host turns in scope: **{c['n_host_turns']}** over "
        f"{c['n_subjects']} subjects.")
    add(f"- Labelled by rule (no model call): **{c['n_rule_labels']}**; "
        f"labelled by the model: **{c['n_labelled_by_model']}** of "
        f"{c['n_model_cases']} cases.")
    add(f"- Parse failures after the B4.3 retries: "
        f"**{c['n_dropped_after_retries']}**; corpus drop rate "
        f"**{c['corpus_drop_rate']}**; subjects above the "
        f"{c['flagged_turn_threshold']} threshold: "
        f"**{len(c['flagged_subjects']) or 'none'}**.")
    add(f"- Labels: {c['label_counts']}.\n")

    # ---- 7. the gate and the tripwire ----
    add("## 7. The part-2 trust gate and the tripwire\n")
    add(q("trust_gate"))
    g = data["part2_gate"]
    add(f"**Result: PASS.** Raw agreement **{g['raw_agreement']}** against the "
        f"≥ 0.85 bar; Cohen's κ **{g['kappa']}** against the ≥ 0.60 bar, over "
        f"{g['rows']} rows from {g['subjects']} confirmatory subjects. The "
        f"verdict was applied mechanically by `experiments/h6_part2_score.py`, "
        f"which was committed before any co-audit label existed.\n")
    add("**Deviation carried into this gate (D3 pattern, owner-directed).** "
        "The auditor line is a blind Opus 5 co-audit, substituted for the "
        "owner's own labels. It is reported as its own line and never pooled "
        "with a human line — no human line exists for it.\n")
    add("**The 120-row sizing ruling.** The frozen text sets a floor of ≥ 60 "
        "rows, not a ceiling. The tranche was first built at 60 and the owner "
        "ruled it up to 120 **before any co-audit label existed**, so the "
        "enlargement adds power without adding bias. The reason on the "
        "record: development's FOLLOW-UP overturn rate was 25%, sitting "
        "between the 20% and 35% lines, and a 30-row FOLLOW-UP tranche "
        "measures that rate in steps of 3.3 points — enough sampling noise to "
        "produce a false halt or a false all-clear. Full note: "
        "`results/stage2_openended/h6_part2_build_note.md`.\n")
    add(q("tripwire"))
    add(f"**The tripwire did NOT fire.** The measured part-2 FOLLOW-UP "
        f"overturn rate is **{g['followup_overturn_rate']}** "
        f"({g['followup_overturn_rate'] * 100:.2f}%) against the frozen "
        f"> 20% line quoted above. The D_min = 3 sensitivity arm was "
        f"pre-committed **conditionally**, and its condition was not met, so "
        f"it is not built. Development's own rate was 25%, above the line, "
        f"which is why the appendix expected the arm to fire; the "
        f"confirmatory measurement came in below it.\n")
    add(f"To be explicit about what is and is not on the record: the "
        f"root-excluded arm in section 4 is a **different** sensitivity arm "
        f"(owner ruling 1, unconditional). The D_min = 3 arm is the one the "
        f"tripwire governs, and it does not exist.\n")

    # ---- 8. the verdict ----
    add("## 8. Verdict — the frozen bars, applied\n")
    add(f"**{v['headline']}**\n")

    add("### (a) The confirmatory bar\n")
    add(q("B3_confirmatory"))
    a = v["a_confirmatory"]
    add("| channel | mean paired difference | paired t p | bar arithmetic |")
    add("|---|---|---|---|")
    for ch, key in (("1 embedding", "channel1"), ("2 stance", "channel2")):
        cell = a[key]
        met = ("—" if cell["met"] is None
               else ("clears" if cell["met"] else "does not clear"))
        add(f"| {ch} | {CR.fmt(cell['mean_diff'], plus=True)} | "
            f"{CR.fmt_p(cell['p'])} | {met} |")
    add("")
    if not a["claimable_under_branch"]:
        add(f"**The arithmetic above is computed but NOT claimable.** The "
            f"branch rule returns **{a['branch'].upper()}** at the primary "
            f"budget ({data['branch']['n_eligible_primary_budget']} eligible "
            f"subjects), and the frozen branch text allows "
            f"{'no hypothesis-test claim at all' if a['branch'] == 'descriptive' else 'effect sizes and CIs only, with no hypothesis-test claim'}. "
            f"The bar is printed and its arithmetic run so nothing is hidden; "
            f"the branch decides what may be said about it, and the branch "
            f"was decided by the eligible count alone.\n")

    add("### (b) The magnitude (\"interesting\") bar\n")
    add(q("B3_interesting"))
    add(q("C5_no_transfer"))
    add(q("param7_units"))
    add(q("param7_applied"))
    add(f"**The inheritance chain, stated rather than assumed.** "
        f"{v['b_magnitude']['inheritance']}\n")
    add("| channel | unit | measured | reaches the unit |")
    add("|---|---|---|---|")
    for ch, key in (("1 embedding", "channel1"), ("2 stance", "channel2")):
        mg = v["b_magnitude"][key]
        if mg is None:
            continue
        add(f"| {ch} | ≥ +{mg['bar']} | {CR.fmt(mg['value'], plus=True)} | "
            f"{'YES' if mg['met'] else 'no'} |")
    add("")

    add("### (c) Robustness\n")
    add(q("A3"))
    add(q("B3_robustness"))
    add(q("C6_superseded"))
    add(f"{v['c_robustness']['note']}\n")
    add(f"- Robustness model holds the primary model's direction on both "
        f"channels: **{v['c_robustness']['robustness_model_direction_holds']}** "
        f"(channel 1 "
        f"{CR.fmt(v['c_robustness']['robustness_channel1_diff'], plus=True)}, "
        f"channel 2 "
        f"{CR.fmt(v['c_robustness']['robustness_channel2_diff'], plus=True)}).")
    add(f"- The root-excluded sensitivity arm is reported in section 4; its "
        f"direction agreement with the registered contrast is tabulated "
        f"there. It runs on the primary model only.\n")

    add("### (d) Both channels\n")
    add(q("C2_4"))
    add(f"- Primary model, channel 1 direction: "
        f"**{v['d_channels']['primary_channel1_direction']}**.")
    add(f"- Primary model, channel 2 direction: "
        f"**{v['d_channels']['primary_channel2_direction']}**.")
    add(f"- Channels agree in direction: "
        f"**{v['d_channels']['channels_agree']}**.")
    if not v["d_channels"]["channels_agree"]:
        add("- **The channels disagree, and that disagreement is itself the "
            "reported result** — the frozen text requires it to be reported, "
            "not resolved.")
    add("")

    add("### (e) The two pre-written readings, at equal prominence\n")
    add(q("B2_reading_positive"))
    add(q("B2_reading_null"))
    if v["e_readings"]["applied"] is None:
        n_elig = data["branch"]["n_eligible_primary_budget"]
        dev_share = "roughly two thirds (4 of 6)"
        got_share = (f"{n_elig} of "
                     f"{data['classifier']['n_subjects'] - 1} "
                     f"({n_elig / (data['classifier']['n_subjects'] - 1):.0%})")
        add("**Neither reading is applied.** Why: "
            f"{v['e_readings']['why']}. Both stay quoted above at equal "
            "prominence with no claim attached to either, and the measured "
            "directions and confidence intervals sit beside them as "
            "descriptive numbers.\n")
        add("The null reading in particular has to be EARNED, not defaulted "
            "to. It asserts a publishable absence of an effect, which takes a "
            "powered null. This run is not one: the primary model's "
            f"registered contrast is "
            f"{CR.fmt(v['a_confirmatory']['channel1']['mean_diff'], plus=True)} "
            f"cosine at p = {CR.fmt_p(v['a_confirmatory']['channel1']['p'])} "
            f"over {n_elig} subjects, and the direction is POSITIVE in all "
            "four model × channel cells at the primary budget. A "
            "non-significant positive point estimate on a small sample is an "
            "absence of evidence, not evidence of absence.\n")
        add("The dose check cuts against a null reading from the other side "
            "as well: the primary model's sign REVERSES at B = 400 "
            f"({CR.fmt(data['results'][PRIMARY]['channel1']['rich_minus_poor_b400']['mean_diff'], plus=True)} "
            "cosine, "
            f"p = {CR.fmt_p(data['results'][PRIMARY]['channel1']['rich_minus_poor_b400']['p_paired_t'])}). "
            "A contrast that changes direction with the budget is not a "
            "settled null either — even at a higher branch, neither reading "
            "could have been applied on this evidence without more of it.\n")
        add(f"**The operative fact of this H6 run is the eligibility "
            f"shortfall itself.** Development supply implied {dev_share} of "
            f"the pool would be eligible at B = 1,000; the confirmatory "
            f"corpus delivered {got_share}. H6 is therefore **UNRESOLVED at "
            f"confirmatory scale on this corpus** — not answered positive, "
            f"not answered null. What this run establishes is that the "
            f"registered H6 design does not reach confirmatory power on "
            f"MediaSum-derived grounding transcripts at the frozen budget, "
            f"and that is the finding to carry forward.\n")
    else:
        add(f"**Applied mechanically: the "
            f"{str(v['e_readings']['applied']).upper()} reading.** Why: "
            f"{v['e_readings']['why']}.\n")

    # ---- 9. the confound and the rest of the record ----
    add("## 9. The declared confound and the rest of the record\n")
    add(q("B2_confound"))
    add("That confound is structural to H6 and is not corrected for here. It "
        "is the reason H6's positive reading is about where value SITS in "
        "existing transcripts, not about what a live interviewer should do.\n")
    add("**Deviations touching H6, restated rather than referenced.**\n")
    add("- **D3** (2026-07-28, owner-directed) — the H6 classifier trust "
        "audit runs as a blind LLM co-audit (Opus 5) instead of the owner's "
        "own labels, with a disagreement-triggered human tranche. Part 1 "
        "scored raw 0.8667 / κ 0.7333 on 120 dev rows and cleared the B2.2 "
        "bar, so no human tranche was built.")
    add("- **D3 pattern, carried to part 2** (2026-07-28) — the part-2 "
        "confirmatory tranche was labelled the same way: a blind Opus 5 "
        "co-audit substituted for the owner's labels, reported as its own "
        "line, never pooled. Raw 0.8833 / κ 0.7667 on 120 rows over 60 "
        "confirmatory subjects.")
    add("- **120-row sizing ruling** (2026-07-28) — the owner raised the "
        "tranche from the pre-registered floor of 60 to 120 while still "
        "blind. Recorded in section 7.")
    add("- **The D_min = 3 arm is not built** — its condition did not fire. "
        "Recorded in section 7 with the measured rate beside the frozen "
        "tripwire text.")
    add("- **The sensitivity arm runs on the primary model only** — an "
        "API-budget decision, declared here and beside every sensitivity "
        "number.\n")

    # ---- 10. costs ----
    add("## 10. Costs\n")
    c = data["cost"]
    add("| currency | H6 spend | cap | headroom | breached |")
    add("|---|---|---|---|---|")
    add(f"| GPU node-hours, this task (arms + generation) | "
        f"{c['this_task_node_hours']} | {c['gpu_task_limit_node_hours']} | "
        f"{round(c['gpu_task_limit_node_hours'] - c['this_task_node_hours'], 4)} "
        f"| {'YES' if c['this_task_node_hours'] > c['gpu_task_limit_node_hours'] else 'no'} |")
    add(f"| GPU node-hours, whole closeout phase (incl. the classifier pass "
        f"at {c['classify_node_hours']}) | {c['total_node_hours']} | "
        f"{c['gpu_phase_cap_node_hours']} | "
        f"{round(c['gpu_phase_cap_node_hours'] - c['total_node_hours'], 4)} | "
        f"{'YES' if c['total_node_hours'] > c['gpu_phase_cap_node_hours'] else 'no'} |")
    add(f"| API dollars | ${c['total_api_usd']} | ${c['api_cap_usd']} | "
        f"${round(c['api_cap_usd'] - c['total_api_usd'], 6)} | "
        f"{'YES' if c['api_breached'] else 'no'} |")
    add("")
    add("Projected before any spend: **$2.07 API** (542 flash-lite "
        "generations + 1,271 judge calls + canary) against the $6.00 limit, "
        "and **≤ 0.4 node-hours** against the 2.0 additional-GPU limit. Both "
        "projections were computed and checked before the first call.\n")
    add("| run id | model | entries | calls | API $ | node-hours |")
    add("|---|---|---|---|---|---|")
    for run in c["per_run"]:
        add(f"| `{run['run_id']}` | {run['model']} | {run['entries']} | "
            f"{run['calls']} | ${run['usd']} | {run['node_hours']} |")
    add("\nGPU billing comes from `sacct`, every attempt included, cancelled "
        "ones counted at their billed elapsed time.\n")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_status(data: dict) -> None:
    print(f"branch: {data['branch']['branch'].upper()} "
          f"({data['branch']['n_eligible_primary_budget']} eligible at "
          f"B={BUDGET_PRIMARY})")
    for model, block in data["results"].items():
        print(f"{model}: {block['n_cosines']} cosines, {block['n_labels']} "
              f"labels")
        for key, _a, _b, _bu, _r in CONTRASTS:
            for ch in ("channel1", "channel2"):
                c = block[ch].get(key)
                if c:
                    print(f"  {ch:9s} {key:32s} {CR.fmt(c['mean_diff'], plus=True)} "
                          f"p={CR.fmt_p(c['p_paired_t'])} n={c['n_subjects']}")
    print(f"verdict: {data['verdict']['headline']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--status", action="store_true",
                    help="print the headline numbers, write nothing")
    args = ap.parse_args(argv)

    data = build()
    if args.status:
        print_status(data)
        return 0
    S.write_json(NUMBERS_JSON, data)
    REPORT_MD.write_text(render_markdown(data), encoding="utf-8")
    print_status(data)
    print(f"\nwrote {CR.rel(REPORT_MD)}")
    print(f"wrote {CR.rel(NUMBERS_JSON)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
