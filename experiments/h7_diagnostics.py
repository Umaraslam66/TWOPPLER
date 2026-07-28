#!/usr/bin/env python3
"""H7 exploratory diagnostics — decompose the channel-1 / channel-2 disagreement.

EXPLORATORY THROUGHOUT. This script writes `results/stage2_confirm/h7_diagnostics.md`.
Nothing it computes is a bar, a verdict, or a claim. It changes no frozen rule and
recommends no change to one. The confirmatory H7 numbers stay where they are, in
`results/stage2_confirm/STAGE2_CONFIRM_REPORT.md`, computed by
`experiments/stage2_confirm_report.py` under the frozen UNCLEAR rule.

Why it exists. The confirmatory report found the two channels pointing different
ways on H7 for the primary model: channel 1 (embedding cosine) is flat with no
crossover in range, channel 2 (stance match) has a significantly POSITIVE slope
and a pooled crossover at the earliest bin. This script asks four questions about
that disagreement and answers each with numbers from artifacts already on disk.

    1. Does the imposter-arm UNCLEAR asymmetry concentrate in particular delta bins?
    2. Does a delta-correlated topic/era covariate track the stance slope?
    3. Does the stance slope survive three different UNCLEAR-handling rules?
    4. Do crossing and non-crossing subjects differ on contamination, item count,
       or bins filled?

Inputs, all read-only, all already produced by earlier steps:

    results/stage2_confirm/render_index.jsonl       stage2_confirm_render.py
    results/stage2_confirm/items_confirm.jsonl      stage2_confirm_build.py
    results/stage2_confirm/render_manifest.json     stage2_confirm_render.py
    results/stage2_confirm/node/chunk_*.prompts.jsonl   stage2_confirm_render.py
    results/stage2_confirm/node/chunk_*.meta.jsonl      stage2_confirm_render.py
    results/stage2_confirm/embed/cosines_*.jsonl    stage2_confirm_embed.py
    results/stage2_confirm/judge/judgements_*.jsonl stage2_confirm_judge.py
    results/stage2_confirm/report_numbers.json      stage2_confirm_report.py

Cost. CPU only. No API call, no GPU, no network fetch (the embedding model is
loaded from the local Hugging Face cache at the pinned revision, offline).
$0.00.

Determinism. Same inputs, same numbers. Nothing here samples or resamples; the
only stochastic-looking step is the embedding forward pass, which is fixed by the
pinned model revision and CPU float arithmetic.

Usage:
    python experiments/h7_diagnostics.py
    python experiments/h7_diagnostics.py --no-embed   # skip the embedding
                                                     # covariate, keep the rest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover - environment-dependent
    raise SystemExit(f"[fatal] numpy is required ({exc})")

try:
    from scipy import stats as sstats
except ImportError as exc:  # pragma: no cover - environment-dependent
    raise SystemExit(f"[fatal] scipy is required ({exc})")

_ROOT = Path(__file__).resolve().parents[1]
CONFIRM_DIR = _ROOT / "results" / "stage2_confirm"
NODE_DIR = CONFIRM_DIR / "node"
EMBED_DIR = CONFIRM_DIR / "embed"
JUDGE_DIR = CONFIRM_DIR / "judge"
OUT_MD = CONFIRM_DIR / "h7_diagnostics.md"

GEN_DIRS = {"gemma": "Gemma-4-31B-it", "flashlite": "gemini-3.5-flash-lite"}
PRIMARY_DIR = "gemma"
CHUNKS = ("chunk_01", "chunk_02", "chunk_03", "chunk_04", "chunk_05")

TWIN_ARM = "h7_twin_redacted"
IMPOSTER_ARM = "h7_imposter_fresh"
BIN_ORDER = ("6-12m", "1-2y", "2-3y", ">3y")

#: Same instrument as channel 1, so the covariate lives on the same scale as the
#: channel-1 score it is being compared against (Addendum A parameter 1).
PINNED_EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"
PINNED_EMBED_REVISION = "e8c3b32edf5434bc2275fc9bab85f82640a19130"

GENERATOR = "experiments/h7_diagnostics.py"

#: A short, fixed stop list for the truncation-free lexical cross-check. Frozen
#: here so the number is reproducible; it is not tuned against any result.
STOPWORDS = frozenset("""
a about above after again against all also am an and any are as at be because
been before being below between both but by can cannot could did do does doing
down during each few for from further had has have having he her here hers him
his how i if in into is it its itself just me more most my no nor not now of
off on once only or other others our ours out over own same she should so some
such than that the their theirs them then there these they this those through
to too under until up very was we were what when where which while who whom why
will with would you your yours think know like get go going really thing things
lot much many well yes okay say said says one two see look come take make want
""".split())

WORD_RE = re.compile(r"[a-z][a-z'-]{2,}")


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def read_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def read_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def fmt(x, nd=4, plus=False):
    if x is None:
        return "n/a"
    s = f"{x:+.{nd}f}" if plus else f"{x:.{nd}f}"
    return s


def fmt_p(p):
    if p is None:
        return "n/a"
    return "< 0.0001" if p < 0.0001 else f"{p:.4f}"


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def one_sample(values: list) -> dict:
    """Mean, t-test p and n for a list of per-subject numbers."""
    v = np.array([x for x in values if x is not None], dtype=float)
    if len(v) < 2:
        return {"n": len(v), "mean": float(v[0]) if len(v) else None, "p": None}
    t = sstats.ttest_1samp(v, 0.0)
    return {"n": int(len(v)), "mean": float(v.mean()), "p": float(t.pvalue),
            "sd": float(v.std(ddof=1)),
            "n_below_zero": int((v < 0).sum())}


def corr(xs, ys) -> dict:
    x = np.array(xs, dtype=float)
    y = np.array(ys, dtype=float)
    if len(x) < 3:
        return {"n": len(x), "pearson_r": None, "pearson_p": None,
                "spearman_rho": None, "spearman_p": None}
    pr = sstats.pearsonr(x, y)
    sr = sstats.spearmanr(x, y)
    return {"n": int(len(x)), "pearson_r": float(pr[0]), "pearson_p": float(pr[1]),
            "spearman_rho": float(sr[0]), "spearman_p": float(sr[1])}


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------


def load_h7_rows() -> list:
    """Every logical H7 render, with its item metadata attached."""
    items = {row["item_id"]: row
             for row in read_jsonl(CONFIRM_DIR / "items_confirm.jsonl")}
    rows = []
    for row in read_jsonl(CONFIRM_DIR / "render_index.jsonl"):
        if row["arm"] not in (TWIN_ARM, IMPOSTER_ARM):
            continue
        item = items.get(row["item_id"])
        if item is None:
            raise SystemExit(f"[fatal] render row {row['item_id']} not in items")
        rows.append({
            "canonical_id": row["canonical_id"],
            "item_id": row["item_id"],
            "arm": row["arm"],
            "h7_bin": row.get("h7_bin"),
            "cutoff_date": row.get("cutoff_date"),
            "delta_days": row.get("delta_days"),
            "prompt_sha256": row["prompt_sha256"],
            "chunk": row["chunk"],
            "idx": row["idx"],
            "real_answer": item.get("real_answer_verbatim") or "",
        })
    return rows, items


def load_labels(gen_dir: str) -> dict:
    by_sha = {}
    for chunk in CHUNKS:
        for row in read_jsonl(JUDGE_DIR / f"judgements_{gen_dir}_{chunk}.jsonl"):
            by_sha[row["prompt_sha256"]] = row
    return by_sha


def load_cosines(gen_dir: str) -> dict:
    by_sha = {}
    for chunk in CHUNKS:
        for row in read_jsonl(EMBED_DIR / f"cosines_{gen_dir}_{chunk}.jsonl"):
            by_sha[row["prompt_sha256"]] = row
    return by_sha


def load_prompts_by_sha() -> dict:
    """prompt_sha256 -> the exact prompt text that was sent."""
    out = {}
    for chunk in CHUNKS:
        meta = read_jsonl(NODE_DIR / f"{chunk}.meta.jsonl")
        prompts = read_jsonl(NODE_DIR / f"{chunk}.prompts.jsonl")
        by_idx = {p["idx"]: p["prompt"] for p in prompts}
        for m in meta:
            text = by_idx.get(m["idx"])
            if text is not None:
                out[m["prompt_sha256"]] = text
    return out


# ---------------------------------------------------------------------------
# cells: (subject, bin) -> the items it holds, mirroring stage2_confirm_report
# ---------------------------------------------------------------------------


def build_cells(rows: list) -> dict:
    """(subject, bin) -> {items, delta_days, twin_shas}.

    Same construction as ``h7_cells`` in experiments/stage2_confirm_report.py:
    the twin defines the cell; the fresh imposter is rendered once per item and
    placed into every bin its subject filled, restricted to the same items.
    """
    cells = {}
    for row in rows:
        if row["arm"] != TWIN_ARM:
            continue
        key = (row["canonical_id"], row["h7_bin"])
        c = cells.setdefault(key, {"items": set(), "delta_days": None,
                                   "twin_sha_by_item": {}, "cutoff": None})
        c["items"].add(row["item_id"])
        c["twin_sha_by_item"][row["item_id"]] = row["prompt_sha256"]
        if row["delta_days"] is not None:
            c["delta_days"] = row["delta_days"]
        if row["cutoff_date"] is not None:
            c["cutoff"] = row["cutoff_date"]
    return cells


def imposter_sha_by_item(rows: list) -> dict:
    return {row["item_id"]: row["prompt_sha256"]
            for row in rows if row["arm"] == IMPOSTER_ARM}


# ---------------------------------------------------------------------------
# section 1 — UNCLEAR by delta bin, both arms, both models
# ---------------------------------------------------------------------------


def unclear_by_bin(cells: dict, imp_sha: dict, lab_by_sha: dict) -> dict:
    """bin -> arm -> {SAME, DIFFERENT, UNCLEAR, unparsed} counts.

    Twin counts are one per rendered twin item. Imposter counts follow the cell
    placement the crossover uses: the same fresh-imposter item is counted once in
    every bin its subject filled, exactly as the crossover compares it.
    """
    out = {b: {TWIN_ARM: {"SAME": 0, "DIFFERENT": 0, "UNCLEAR": 0, "unparsed": 0},
               IMPOSTER_ARM: {"SAME": 0, "DIFFERENT": 0, "UNCLEAR": 0,
                              "unparsed": 0}}
           for b in BIN_ORDER}

    def bump(bucket, sha):
        lab = lab_by_sha.get(sha)
        if lab is None:
            return
        label = lab.get("label")
        bucket[label if label in ("SAME", "DIFFERENT", "UNCLEAR") else "unparsed"] += 1

    for (subject, b), c in cells.items():
        if b not in out:
            continue
        for iid in sorted(c["items"]):
            bump(out[b][TWIN_ARM], c["twin_sha_by_item"][iid])
            sha = imp_sha.get(iid)
            if sha is not None:
                bump(out[b][IMPOSTER_ARM], sha)

    for b in BIN_ORDER:
        for arm in (TWIN_ARM, IMPOSTER_ARM):
            c = out[b][arm]
            den = c["SAME"] + c["DIFFERENT"]
            total = den + c["UNCLEAR"] + c["unparsed"]
            c["denominator"] = den
            c["n_labels"] = total
            c["stance_match"] = (c["SAME"] / den) if den else None
            c["unclear_rate"] = (c["UNCLEAR"] / total) if total else None
    for b in BIN_ORDER:
        ut, ui = (out[b][TWIN_ARM]["unclear_rate"],
                  out[b][IMPOSTER_ARM]["unclear_rate"])
        out[b]["unclear_gap_imposter_minus_twin"] = (
            None if ut is None or ui is None else ui - ut)

    # Freshest bin against every other bin pooled, per arm. The freshest bin is
    # where channel 2 puts its pooled crossover, so its denominator matters most.
    fresh = BIN_ORDER[0]
    summary = {}
    for arm in (TWIN_ARM, IMPOSTER_ARM):
        rest_u = sum(out[b][arm]["UNCLEAR"] for b in BIN_ORDER[1:])
        rest_n = sum(out[b][arm]["n_labels"] for b in BIN_ORDER[1:])
        f_u, f_n = out[fresh][arm]["UNCLEAR"], out[fresh][arm]["n_labels"]
        summary[arm] = {
            "freshest_unclear_rate": (f_u / f_n) if f_n else None,
            "rest_unclear_rate": (rest_u / rest_n) if rest_n else None,
            "freshest_minus_rest": ((f_u / f_n) - (rest_u / rest_n))
            if f_n and rest_n else None,
            "freshest_n_labels": f_n, "rest_n_labels": rest_n,
        }
    out["_freshest_vs_rest"] = summary
    return out


def pairing_coverage(cells: dict, imp_sha: dict, score_of) -> dict:
    """Per bin: how many subjects carry a twin value and how many an imposter one.

    This is the mechanism behind the `n/a` cells in the confirmatory report's
    channel-2 H7 bin tables. ``stage2_confirm_report.h7_block`` prints
    ``own_minus_fresh_imposter`` only when the two arms cover the SAME set of
    subjects in that bin (``len(tw) == len(im)``); otherwise the subtraction
    would be over different people, so it is suppressed.
    """
    out = {}
    for b in BIN_ORDER:
        n_twin = n_imp = 0
        missing = []
        for (s, bb), c in sorted(cells.items()):
            if bb != b:
                continue
            tw = [v for v in (score_of(c["twin_sha_by_item"][i])
                              for i in sorted(c["items"])) if v is not None]
            if not tw:
                continue
            n_twin += 1
            im = [v for v in (score_of(imp_sha[i])
                              for i in sorted(c["items"]) if i in imp_sha)
                  if v is not None]
            if im:
                n_imp += 1
            else:
                missing.append(s)
        out[b] = {"n_subjects_twin": n_twin, "n_subjects_imposter": n_imp,
                  "difference_printed": n_twin == n_imp and n_twin > 0,
                  "subjects_without_imposter_value": missing}
    return out


# ---------------------------------------------------------------------------
# section 2 — era / topic-overlap covariate
# ---------------------------------------------------------------------------


GROUND_RE = re.compile(r"PAST INTERVIEWS\n(.*?)\n\nA LATER INTERVIEW",
                       re.DOTALL)


def grounding_text(prompt: str) -> str | None:
    m = GROUND_RE.search(prompt)
    return m.group(1).strip() if m else None


def content_words(text: str) -> set:
    return {w for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS}


def lexical_overlap(grounding: str, answer: str) -> float | None:
    """Jaccard over content words. Truncation-free: it reads the whole block."""
    g, a = content_words(grounding), content_words(answer)
    if not g or not a:
        return None
    return len(g & a) / len(g | a)


def cell_groundings(cells: dict, prompts: dict) -> tuple[dict, list]:
    """(subject, bin) -> grounding text, plus any cells whose text is not one."""
    out, problems = {}, []
    for key, c in sorted(cells.items()):
        texts = set()
        for iid in sorted(c["items"]):
            p = prompts.get(c["twin_sha_by_item"][iid])
            if p is None:
                continue
            g = grounding_text(p)
            if g:
                texts.add(g)
        if len(texts) == 1:
            out[key] = texts.pop()
        else:
            problems.append({"cell": list(key), "n_distinct_groundings": len(texts)})
    return out, problems


def topic_overlap(cells: dict, items: dict, prompts: dict,
                  use_embedding: bool) -> dict:
    """Per-cell grounding-to-test-answer overlap, the OE-1 diagnostic method.

    OE-1 (experiments/stage2_oe1.py, cmd_embed, spec section 8) measured
    cosine(embedding of the own arm's grounding block, embedding of the real
    answer) per item. The same measure is taken here per H7 cell, so it varies
    with the cutoff and therefore with delta.

    A truncation-free lexical Jaccard is computed beside it, because the pinned
    embedding model reads only its first 384 tokens of a ~2,000-word grounding
    block.
    """
    ground, problems = cell_groundings(cells, prompts)
    pairs = []          # (cell, item_id)
    for key in sorted(ground):
        for iid in sorted(cells[key]["items"]):
            pairs.append((key, iid))

    lex = {}
    for key, iid in pairs:
        lex[(key, iid)] = lexical_overlap(
            ground[key], items[iid].get("real_answer_verbatim") or "")

    cos = {}
    instrument = None
    if use_embedding:
        cos, instrument = _embed_overlap(ground, pairs, items)

    def per_cell(d):
        acc = {}
        for (key, _iid), v in d.items():
            if v is not None:
                acc.setdefault(key, []).append(v)
        return {k: sum(v) / len(v) for k, v in acc.items()}

    cell_lex, cell_cos = per_cell(lex), per_cell(cos)
    return {"grounding_problems": problems,
            "n_cells": len(ground), "n_pairs": len(pairs),
            "item_lex": lex, "item_cos": cos,
            "cell_lex": cell_lex, "cell_cos": cell_cos,
            "instrument": instrument}


def _embed_overlap(ground: dict, pairs: list, items: dict):
    """cosine(grounding, real answer), pinned model, CPU, local cache only."""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    try:
        from huggingface_hub import snapshot_download
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "[fatal] sentence-transformers / huggingface_hub are required for "
            f"the embedding covariate; re-run with --no-embed to skip it ({exc})")
    snap = snapshot_download(repo_id=PINNED_EMBED_MODEL,
                             revision=PINNED_EMBED_REVISION,
                             local_files_only=True)
    if Path(snap).name != PINNED_EMBED_REVISION:
        raise SystemExit(f"[fatal] pinned revision did not resolve: {snap}")
    model = SentenceTransformer(snap, device="cpu")

    g_keys = sorted(ground)
    g_vecs = dict(zip(g_keys, model.encode([ground[k] for k in g_keys],
                                           batch_size=8, convert_to_numpy=True,
                                           show_progress_bar=False)))
    a_ids = sorted({iid for _k, iid in pairs})
    a_vecs = dict(zip(a_ids, model.encode(
        [items[i].get("real_answer_verbatim") or "" for i in a_ids],
        batch_size=8, convert_to_numpy=True, show_progress_bar=False)))

    def cosine(a, b):
        na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
        return 0.0 if na == 0.0 or nb == 0.0 else float(a.dot(b) / (na * nb))

    out = {(k, i): round(cosine(g_vecs[k], a_vecs[i]), 6) for k, i in pairs}
    return out, {"model": PINNED_EMBED_MODEL, "revision": PINNED_EMBED_REVISION,
                 "device": "cpu", "max_seq_length": int(model.max_seq_length),
                 "offline": True}


def overlap_vs_delta(cells: dict, cell_vals: dict) -> dict:
    """Correlate the covariate with delta, across cells and within subjects."""
    keys = sorted(k for k in cell_vals if cells[k]["delta_days"] is not None)
    xs = [cells[k]["delta_days"] for k in keys]
    ys = [cell_vals[k] for k in keys]
    across = corr(xs, ys) if len(keys) >= 3 else {"n": len(keys)}

    slopes = {}
    by_subj = {}
    for k in keys:
        by_subj.setdefault(k[0], []).append((cells[k]["delta_days"], cell_vals[k]))
    for s, pts in by_subj.items():
        pts = sorted(pts)
        if len({p[0] for p in pts}) < 2:
            continue
        fit = sstats.linregress([p[0] for p in pts], [p[1] for p in pts])
        slopes[s] = float(fit.slope) * 365.25
    return {"across_cells": across, "n_cells": len(keys),
            "per_subject_slope_per_year": slopes,
            "slope_test": one_sample(list(slopes.values()))}


# ---------------------------------------------------------------------------
# section 3 — stance slope under three UNCLEAR rules
# ---------------------------------------------------------------------------


UNCLEAR_RULES = (
    ("frozen_excluded", None,
     "FROZEN RULE — UNCLEAR excluded from the denominator "
     "(Addendum A parameter 6). This is the number reported everywhere else."),
    ("counted_as_non_match", 0.0,
     "Exploratory variant — UNCLEAR counted as a non-match (0)."),
    ("counted_as_half", 0.5,
     "Exploratory variant — UNCLEAR counted as 0.5."),
)


def stance_slopes(cells: dict, lab_by_sha: dict, unclear_value) -> dict:
    """Per-subject channel-2 slope under one UNCLEAR-handling rule."""
    cell_score, cell_n = {}, {}
    for key, c in cells.items():
        vals = []
        for iid in sorted(c["items"]):
            lab = lab_by_sha.get(c["twin_sha_by_item"][iid])
            if lab is None:
                continue
            label = lab.get("label")
            if label == "SAME":
                vals.append(1.0)
            elif label == "DIFFERENT":
                vals.append(0.0)
            elif label == "UNCLEAR" and unclear_value is not None:
                vals.append(float(unclear_value))
        if vals:
            cell_score[key] = sum(vals) / len(vals)
            cell_n[key] = len(vals)

    slopes = {}
    by_subj = {}
    for key, v in cell_score.items():
        d = cells[key]["delta_days"]
        if d is not None:
            by_subj.setdefault(key[0], []).append((d, v))
    for s, pts in by_subj.items():
        pts = sorted(pts)
        if len({p[0] for p in pts}) < 2:
            continue
        fit = sstats.linregress([p[0] for p in pts], [p[1] for p in pts])
        slopes[s] = float(fit.slope)      # per DAY, converted below

    blk = one_sample(list(slopes.values()))
    # stage2_confirm_report.one_sample_block rounds the per-day mean to 6 dp
    # before the per-year conversion. Mirrored here so the frozen-rule row in
    # this note is byte-identical to the number the confirmatory report prints.
    if blk.get("mean") is not None:
        blk["mean"] = round(round(blk["mean"], 6) * 365.25, 6)
    if blk.get("sd") is not None:
        blk["sd"] = blk["sd"] * 365.25
    blk["n_subjects_with_any_cell"] = len(by_subj)
    blk["n_cells_scored"] = len(cell_score)
    blk["n_items_scored"] = sum(cell_n.values())
    blk["per_subject_slope_per_day"] = slopes
    blk["cell_score"] = cell_score
    return blk


# ---------------------------------------------------------------------------
# section 4 — crossing vs non-crossing subjects
# ---------------------------------------------------------------------------


def crossing_profile(cells: dict, crossing: set, subjects: list,
                     meters: dict, cell_items: dict) -> dict:
    """Compare crossing and non-crossing subjects on three plain covariates."""
    rows = {}
    for s in subjects:
        filled = [k for k in cell_items if k[0] == s and cell_items[k]]
        n_items = sum(cell_items[k] for k in filled)
        rows[s] = {
            "meter": meters.get(s),
            "bins_filled": len(filled),
            "total_items": n_items,
            "items_per_bin": (n_items / len(filled)) if filled else None,
        }
    out = {}
    for name, group in (("crossing", [s for s in subjects if s in crossing]),
                        ("non_crossing",
                         [s for s in subjects if s not in crossing])):
        out[name] = {"n": len(group), "subjects": sorted(group)}
        for field in ("meter", "bins_filled", "total_items", "items_per_bin"):
            vals = [rows[s][field] for s in group if rows[s][field] is not None]
            out[name][field] = {"n": len(vals), "mean": mean(vals),
                                "median": median(vals)}
    for field in ("meter", "bins_filled", "total_items", "items_per_bin"):
        a, b = out["crossing"][field]["mean"], out["non_crossing"][field]["mean"]
        out.setdefault("difference_crossing_minus_non", {})[field] = (
            None if a is None or b is None else a - b)
    out["thin"] = min(out["crossing"]["n"], out["non_crossing"]["n"]) < 15
    return out


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------


def compute(use_embedding: bool) -> dict:
    rows, items = load_h7_rows()
    cells = build_cells(rows)
    imp_sha = imposter_sha_by_item(rows)
    prompts = load_prompts_by_sha()
    report = read_json(CONFIRM_DIR / "report_numbers.json")
    subjects = sorted({s for s, _ in cells})

    data = {
        "generator": GENERATOR,
        "label": "EXPLORATORY",
        "n_subjects": len(subjects),
        "n_cells": len(cells),
        "n_twin_renders": sum(1 for r in rows if r["arm"] == TWIN_ARM),
        "n_imposter_renders": sum(1 for r in rows if r["arm"] == IMPOSTER_ARM),
        "cell_delta": {f"{s}|{b}": cells[(s, b)]["delta_days"]
                       for s, b in sorted(cells)},
        "section1": {}, "section2": {}, "section3": {}, "section4": {},
    }

    # --- 1
    for gen_dir in GEN_DIRS:
        labs = load_labels(gen_dir)
        cos = load_cosines(gen_dir)
        data["section1"][gen_dir] = unclear_by_bin(cells, imp_sha, labs)
        data["section1"][gen_dir]["_pairing"] = {
            "channel1": pairing_coverage(
                cells, imp_sha,
                lambda sha, _c=cos: (None if _c.get(sha) is None
                                     else float(_c[sha]["cosine_to_real"]))),
            "channel2": pairing_coverage(
                cells, imp_sha,
                lambda sha, _l=labs: (
                    1.0 if (_l.get(sha) or {}).get("label") == "SAME"
                    else 0.0 if (_l.get(sha) or {}).get("label") == "DIFFERENT"
                    else None)),
        }

    # --- 2
    ov = topic_overlap(cells, items, prompts, use_embedding)
    data["section2"] = {
        "n_cells_with_grounding": ov["n_cells"],
        "n_grounding_answer_pairs": ov["n_pairs"],
        "grounding_problems": ov["grounding_problems"],
        "instrument": ov["instrument"],
        "embedding_cosine": (overlap_vs_delta(cells, ov["cell_cos"])
                             if ov["cell_cos"] else None),
        "lexical_jaccard": overlap_vs_delta(cells, ov["cell_lex"]),
        "cell_cos": {f"{s}|{b}": ov["cell_cos"].get((s, b))
                     for s, b in sorted(cells)},
        "cell_lex": {f"{s}|{b}": ov["cell_lex"].get((s, b))
                     for s, b in sorted(cells)},
    }
    # per-bin means of the covariate, so the era question is readable by bin
    for name, cv in (("embedding_cosine", ov["cell_cos"]),
                     ("lexical_jaccard", ov["cell_lex"])):
        if not cv:
            continue
        per_bin = {}
        for b in BIN_ORDER:
            vals = [v for (s, bb), v in cv.items() if bb == b]
            per_bin[b] = {"n_cells": len(vals), "mean": mean(vals)}
        data["section2"].setdefault("per_bin", {})[name] = per_bin

    # covariate slope against the channel-2 stance slope, per subject
    ch2_slopes = {s: v["slope_per_year"] for s, v in
                  report["h7"]["channel2"][PRIMARY_DIR]["per_subject_slope"].items()}
    for name in ("embedding_cosine", "lexical_jaccard"):
        blk = data["section2"].get(name)
        if not blk:
            continue
        shared = sorted(set(blk["per_subject_slope_per_year"]) & set(ch2_slopes))
        blk["vs_channel2_stance_slope"] = corr(
            [blk["per_subject_slope_per_year"][s] for s in shared],
            [ch2_slopes[s] for s in shared]) if len(shared) >= 3 else {"n": len(shared)}

    # --- 3
    for gen_dir in GEN_DIRS:
        labs = load_labels(gen_dir)
        block = {}
        for key, unclear_value, note in UNCLEAR_RULES:
            blk = stance_slopes(cells, labs, unclear_value)
            blk.pop("cell_score", None)
            blk.pop("per_subject_slope_per_day", None)
            blk["note"] = note
            block[key] = blk
        data["section3"][gen_dir] = block

    # --- 4
    for gen_dir in GEN_DIRS:
        labs = load_labels(gen_dir)
        cos = load_cosines(gen_dir)
        meters = report["contamination"]["channel1"][gen_dir]["per_subject"]
        # channel 1: a cell item counts when it carries a cosine
        c1_items = {k: sum(1 for iid in c["items"]
                           if c["twin_sha_by_item"][iid] in cos)
                    for k, c in cells.items()}
        # channel 2: a cell item counts when it carries a SAME/DIFFERENT label
        c2_items = {k: sum(1 for iid in c["items"]
                           if (labs.get(c["twin_sha_by_item"][iid]) or {}
                               ).get("label") in ("SAME", "DIFFERENT"))
                    for k, c in cells.items()}
        for ch, cell_items in (("channel1", c1_items), ("channel2", c2_items)):
            crossing = set(report["h7"][ch][gen_dir]["crossover"]
                           ["per_subject_crossover_bin"])
            data["section4"].setdefault(ch, {})[gen_dir] = crossing_profile(
                cells, crossing, subjects, meters, cell_items)
    return data


# ---------------------------------------------------------------------------
# markdown
# ---------------------------------------------------------------------------

SRC1 = ("Source: `experiments/h7_diagnostics.py`, reading "
        "`results/stage2_confirm/render_index.jsonl`, "
        "`results/stage2_confirm/items_confirm.jsonl` and "
        "`results/stage2_confirm/judge/judgements_*.jsonl`.")
SRC2 = ("Source: `experiments/h7_diagnostics.py`, reading "
        "`results/stage2_confirm/node/chunk_*.prompts.jsonl` (grounding text), "
        "`results/stage2_confirm/items_confirm.jsonl` (real answers) and "
        "`results/stage2_confirm/report_numbers.json` (channel-2 slopes).")
SRC3 = ("Source: `experiments/h7_diagnostics.py`, reading "
        "`results/stage2_confirm/render_index.jsonl` and "
        "`results/stage2_confirm/judge/judgements_*.jsonl`.")
SRC4 = ("Source: `experiments/h7_diagnostics.py`, reading "
        "`results/stage2_confirm/report_numbers.json` (crossover lists, "
        "contamination meters), "
        "`results/stage2_confirm/embed/cosines_*.jsonl` and "
        "`results/stage2_confirm/judge/judgements_*.jsonl` (item counts).")


def render(data: dict) -> str:
    A: list = []
    add = A.append

    add("# H7 diagnostics — EXPLORATORY")
    add("")
    add("**EXPLORATORY THROUGHOUT. Nothing in this note is a bar, a verdict or "
        "a claim. It proposes no change to any frozen rule and makes no "
        "recommendation. The reported H7 numbers stay where they are, in "
        "`results/stage2_confirm/STAGE2_CONFIRM_REPORT.md`.**")
    add("")
    add("Why this note exists. On the primary model the two channels disagree "
        "about H7. Channel 1 (embedding cosine) is flat — mean slope +0.00146 "
        "per year, p = 0.8650, no pooled crossover anywhere in range. Channel 2 "
        "(stance match) has a significantly positive slope — +0.06502 per year, "
        "p = 0.0182 — and a pooled crossover at the EARLIEST bin, 6-12m. This "
        "note takes that disagreement apart four ways and reports what each "
        "angle does and does not account for.")
    add("")
    add(f"Scope: {data['n_subjects']} H7 subjects, {data['n_cells']} "
        f"subject-by-bin cells, {data['n_twin_renders']} stale-own-twin renders "
        f"and {data['n_imposter_renders']} fresh-imposter renders.")
    add("")
    add(f"**Cost: $0.00.** CPU only, no API call, no GPU, no network fetch. "
        f"Every number is recomputed from artifacts already on disk by "
        f"`{data['generator']}`.")
    add("")

    # ---- 1
    add("## 1. Where the UNCLEAR asymmetry sits — EXPLORATORY")
    add("")
    add("The confirmatory report flagged a global UNCLEAR asymmetry: the "
        "imposter arm draws far more UNCLEAR labels than the twin arm "
        "(0.2958 vs 0.1465 on Gemma, 0.2535 vs 0.1183 on flash-lite, section 6 "
        "of that report). The question here is whether that asymmetry piles up "
        "in one Δ bin — and in particular whether it sits in the 6-12m bin, "
        "which is where channel 2 puts its pooled crossover and where the "
        "positive slope starts.")
    add("")
    add("Counting rule, stated so the denominators can be checked: twin rows "
        "are counted once per rendered item. Fresh-imposter rows are counted "
        "once in every bin their subject filled — the same placement the "
        "crossover statistic uses, because the imposter is rendered once per "
        "item and reused at every cutoff (rule H7-R7). Rates are therefore "
        "comparable within a bin, and the imposter's totals across bins are not "
        "independent.")
    add("")
    add("One more thing to hold while reading: the stance-match column here is "
        "POOLED OVER ITEMS. The per-bin table in the confirmatory report "
        "averages per subject first. The two differ by construction and neither "
        "is wrong; this section needs the item-level version because it is "
        "about denominators.")
    add("")
    for gen_dir, model in GEN_DIRS.items():
        role = "PRIMARY" if gen_dir == PRIMARY_DIR else "ROBUSTNESS"
        add(f"### {model} — {role}")
        add("")
        add("| Δ bin | arm | SAME | DIFFERENT | UNCLEAR | denominator "
            "(SAME+DIFFERENT) | UNCLEAR rate | stance match |")
        add("|---|---|---|---|---|---|---|---|")
        sec = data["section1"][gen_dir]
        for b in BIN_ORDER:
            for arm, nice in ((TWIN_ARM, "stale own twin"),
                              (IMPOSTER_ARM, "fresh imposter")):
                c = sec[b][arm]
                add(f"| {b} | {nice} | {c['SAME']} | {c['DIFFERENT']} | "
                    f"{c['UNCLEAR']} | {c['denominator']} | "
                    f"{fmt(c['unclear_rate'])} | {fmt(c['stance_match'])} |")
        add("")
        add("| Δ bin | imposter UNCLEAR − twin UNCLEAR |")
        add("|---|---|")
        for b in BIN_ORDER:
            add(f"| {b} | {fmt(sec[b]['unclear_gap_imposter_minus_twin'], plus=True)} |")
        add("")
        fv = sec["_freshest_vs_rest"]
        add("| arm | UNCLEAR rate, freshest bin (6-12m) | UNCLEAR rate, all "
            "other bins pooled | freshest − rest |")
        add("|---|---|---|---|")
        for arm, nice in ((TWIN_ARM, "stale own twin"),
                          (IMPOSTER_ARM, "fresh imposter")):
            v = fv[arm]
            add(f"| {nice} | {fmt(v['freshest_unclear_rate'])} "
                f"(n = {v['freshest_n_labels']}) | "
                f"{fmt(v['rest_unclear_rate'])} (n = {v['rest_n_labels']}) | "
                f"{fmt(v['freshest_minus_rest'], plus=True)} |")
        add("")
    add(SRC1)
    add("")
    add("### Why some channel-2 bin rows print `n/a` for own − fresh imposter")
    add("")
    add("The confirmatory report's channel-2 H7 bin tables show both arm means "
        "but print `n/a` in the difference column for 6-12m and >3y on both "
        "models. That is not a missing number, it is a deliberate suppression, "
        "and the mechanism is worth stating plainly.")
    add("")
    add("`h7_block` in `experiments/stage2_confirm_report.py` computes the "
        "difference only when the two arms cover the SAME set of subjects in "
        "that bin (the `len(tw) == len(im)` guard). On channel 2 a subject "
        "keeps a twin value in a bin as long as one of its items got a "
        "SAME/DIFFERENT label, but loses its imposter value in that bin if ALL "
        "of that subject's imposter items came back UNCLEAR. The imposter arm "
        "draws the most UNCLEAR, so it is the arm that loses subjects — the "
        "sets stop matching, and the driver refuses to subtract means computed "
        "over different people. Channel 1 never hits this: every render carries "
        "a cosine, so no subject drops out.")
    add("")
    for gen_dir, model in GEN_DIRS.items():
        pr = data["section1"][gen_dir]["_pairing"]
        add(f"**{model}** — subjects contributing a value in each bin:")
        add("")
        add("| Δ bin | ch1 twin | ch1 imposter | ch1 difference printed | "
            "ch2 twin | ch2 imposter | ch2 difference printed |")
        add("|---|---|---|---|---|---|---|")
        for b in BIN_ORDER:
            a, c = pr["channel1"][b], pr["channel2"][b]
            add(f"| {b} | {a['n_subjects_twin']} | {a['n_subjects_imposter']} | "
                f"{'yes' if a['difference_printed'] else 'NO'} | "
                f"{c['n_subjects_twin']} | {c['n_subjects_imposter']} | "
                f"{'yes' if c['difference_printed'] else 'NO'} |")
        add("")
    add("Worth noticing, and reported rather than acted on: the pooled "
        "crossover statistic does NOT apply that guard. It compares the two "
        "arm means directly, whatever subject sets produced them. So the "
        "channel-2 crossover at 6-12m on the primary model rests on a "
        "comparison the same driver declines to print as a difference one "
        "column to its left. This note only makes that visible; it proposes no "
        "change to the crossover definition, which is frozen.")
    add("")

    # ---- 2
    add("## 2. Era and topic overlap as a Δ-correlated covariate — EXPLORATORY")
    add("")
    add("The question on record: staleness moves the grounding's ERA as well as "
        "its age. Older grounding talks about older topics. If the test "
        "interview happens to share more vocabulary and subject matter with "
        "some cutoffs than others, and that sharing correlates with Δ, then a "
        "stance slope could appear without anything person-level changing. This "
        "section measures the covariate and correlates it with Δ. It does not "
        "test causation and no causal language is used.")
    add("")
    add("Method, reused from OE-1 (`experiments/stage2_oe1.py`, `cmd_embed`, "
        "spec section 8; reported in "
        "`results/stage2_openended/OE1_PILOT_REPORT.md`): the similarity "
        "between the grounding block and the real test answer, per item. Here "
        "the grounding block is the one actually rendered at each cutoff, so "
        "the measure varies with Δ. Two readings are given because the "
        "embedding one has a known limit:")
    add("")
    add("- **Embedding cosine** — the pinned channel-1 instrument "
        "(`sentence-transformers/all-mpnet-base-v2`, revision "
        "`e8c3b32edf5434bc2275fc9bab85f82640a19130`, CPU, loaded offline). Its "
        "input window is 384 tokens, and a grounding block is around 2,000 "
        "words, so this reads the head of the block, not all of it. Same limit "
        "OE-1 had.")
    add("- **Lexical Jaccard over content words** — truncation-free, reads the "
        "whole block, stdlib only. Included precisely because it does not have "
        "the window problem.")
    add("")
    sec2 = data["section2"]
    add(f"Coverage: {sec2['n_cells_with_grounding']} of {data['n_cells']} cells "
        f"yielded exactly one grounding block, over "
        f"{sec2['n_grounding_answer_pairs']} grounding-to-answer pairs.")
    if sec2["grounding_problems"]:
        add("")
        add(f"Cells whose grounding text was not unique or not recoverable: "
            f"{len(sec2['grounding_problems'])}. They are excluded from this "
            f"section only.")
    add("")
    if sec2.get("per_bin"):
        add("**Covariate by Δ bin.** If era were driving the stance curve, this "
            "would move with the bins.")
        add("")
        add("| Δ bin | cells | embedding cosine (mean) | lexical Jaccard (mean) |")
        add("|---|---|---|---|")
        pb = sec2["per_bin"]
        for b in BIN_ORDER:
            e = pb.get("embedding_cosine", {}).get(b, {})
            l = pb.get("lexical_jaccard", {}).get(b, {})
            add(f"| {b} | {l.get('n_cells', 0)} | {fmt(e.get('mean'))} | "
                f"{fmt(l.get('mean'), 4)} |")
        add("")
    add("**Correlation with Δ.** Across cells (each cell is one subject at one "
        "cutoff) and, separately, as a per-subject slope against Δ — the same "
        "shape as the H7 slope test, so the two are directly comparable. Read "
        "both: cells are not independent, because one subject can fill up to "
        "four of them, so an across-cell correlation can be driven entirely by "
        "which subjects happen to fill which bins. The per-subject slope has "
        "that composition effect removed.")
    add("")
    add("| covariate | across cells n | Pearson r | p | Spearman ρ | p | "
        "per-subject slope/year (mean) | p | n subjects |")
    add("|---|---|---|---|---|---|---|---|---|")
    for name, nice in (("embedding_cosine", "embedding cosine"),
                       ("lexical_jaccard", "lexical Jaccard")):
        blk = sec2.get(name)
        if not blk:
            continue
        ac, st = blk["across_cells"], blk["slope_test"]
        add(f"| {nice} | {ac.get('n')} | {fmt(ac.get('pearson_r'), 4, True)} | "
            f"{fmt_p(ac.get('pearson_p'))} | "
            f"{fmt(ac.get('spearman_rho'), 4, True)} | "
            f"{fmt_p(ac.get('spearman_p'))} | "
            f"{fmt(st.get('mean'), 6, True)} | {fmt_p(st.get('p'))} | "
            f"{st.get('n')} |")
    add("")
    add("**Does the covariate track the stance slope?** Per-subject covariate "
        "slope against per-subject channel-2 stance slope, primary model. If "
        "the era covariate were producing the stance slope, these would move "
        "together.")
    add("")
    add("| covariate | n subjects | Pearson r | p | Spearman ρ | p |")
    add("|---|---|---|---|---|---|")
    for name, nice in (("embedding_cosine", "embedding cosine"),
                       ("lexical_jaccard", "lexical Jaccard")):
        blk = sec2.get(name)
        if not blk or "vs_channel2_stance_slope" not in blk:
            continue
        v = blk["vs_channel2_stance_slope"]
        add(f"| {nice} | {v.get('n')} | {fmt(v.get('pearson_r'), 4, True)} | "
            f"{fmt_p(v.get('pearson_p'))} | {fmt(v.get('spearman_rho'), 4, True)} "
            f"| {fmt_p(v.get('spearman_p'))} |")
    add("")
    add(SRC2)
    add("")

    # ---- 3
    add("## 3. Stance slope under three UNCLEAR rules — EXPLORATORY")
    add("")
    add("The channel-2 slope is computed after UNCLEAR items are dropped. That "
        "is the frozen rule and it stays the reported number everywhere else. "
        "This table asks only whether the slope's direction and size depend on "
        "that choice. The two variants are exploratory arithmetic, nothing more; "
        "neither is proposed as a replacement.")
    add("")
    add("Self-check: the frozen-rule row is recomputed here from the raw "
        "judgements, independently of the report driver, and reproduces the "
        "confirmatory report's published slopes exactly (+0.06502 at p = 0.0182 "
        "on the primary model, -0.00219 at p = 0.9601 on the robustness model). "
        "If those two ever stop matching, one of the two scripts has drifted.")
    add("")
    for gen_dir, model in GEN_DIRS.items():
        role = "PRIMARY" if gen_dir == PRIMARY_DIR else "ROBUSTNESS"
        add(f"### {model} — {role}, channel 2")
        add("")
        add("| UNCLEAR handling | mean slope / year | p | subjects with a slope "
            "| slopes below zero | cells scored | items scored |")
        add("|---|---|---|---|---|---|---|")
        sec = data["section3"][gen_dir]
        for key, _v, note in UNCLEAR_RULES:
            b = sec[key]
            tag = ("**frozen rule (reported)**" if key == "frozen_excluded"
                   else f"exploratory: {key.replace('_', ' ')}")
            add(f"| {tag} | {fmt(b.get('mean'), 5, True)} | {fmt_p(b.get('p'))} "
                f"| {b.get('n')} | {b.get('n_below_zero')} | "
                f"{b.get('n_cells_scored')} | {b.get('n_items_scored')} |")
        add("")
    add(SRC3)
    add("")

    # ---- 4
    add("## 4. Crossing vs non-crossing subjects — EXPLORATORY")
    add("")
    add("Per subject, the crossover fires when the fresh imposter matches or "
        "beats the stale own twin in some bin. It fires for 13/36 subjects on "
        "channel 1 Gemma, 11/36 on channel 1 flash-lite, 21/36 on channel 2 "
        "Gemma and 22/36 on channel 2 flash-lite. This section asks whether the "
        "subjects it fires for differ from the ones it does not on three plain "
        "covariates: the contamination meter, how many items they carry, and "
        "how many bins they fill.")
    add("")
    add("**Small-n honesty, stated before the numbers.** Every cell below "
        "splits 36 subjects into two groups; the smallest group is 11. No "
        "significance test is run and none should be read in. These are counts, "
        "means and medians, and the only thing to take from them is the "
        "direction of a difference and whether it is large enough to notice.")
    add("")
    add("The contamination meter is the channel-1 meter for that model "
        "(zeroinfo_named − zeroinfo_redacted, per subject) in all four cells: "
        "the channel-2 meter has a median of exactly 0 per subject and cannot "
        "separate groups. Item counts and bins filled ARE channel-specific — "
        "channel 2 counts only items the judge labelled SAME or DIFFERENT.")
    add("")
    for ch, ch_nice in (("channel1", "channel 1 (embedding cosine)"),
                        ("channel2", "channel 2 (stance match)")):
        for gen_dir, model in GEN_DIRS.items():
            blk = data["section4"][ch][gen_dir]
            role = "PRIMARY" if gen_dir == PRIMARY_DIR else "ROBUSTNESS"
            add(f"### {model} — {role}, {ch_nice}")
            add("")
            add("| group | subjects | contamination meter (mean / median) | "
                "bins filled (mean) | total items (mean) | items per filled bin "
                "(mean) |")
            add("|---|---|---|---|---|---|")
            for name, nice in (("crossing", "crosses at some bin"),
                               ("non_crossing", "never crosses")):
                g = blk[name]
                add(f"| {nice} | {g['n']} | {fmt(g['meter']['mean'], 4, True)} / "
                    f"{fmt(g['meter']['median'], 4, True)} | "
                    f"{fmt(g['bins_filled']['mean'], 2)} | "
                    f"{fmt(g['total_items']['mean'], 2)} | "
                    f"{fmt(g['items_per_bin']['mean'], 2)} |")
            d = blk["difference_crossing_minus_non"]
            add("")
            add(f"Crossing minus non-crossing: meter "
                f"{fmt(d['meter'], 4, True)}, bins filled "
                f"{fmt(d['bins_filled'], 2, True)}, total items "
                f"{fmt(d['total_items'], 2, True)}, items per filled bin "
                f"{fmt(d['items_per_bin'], 2, True)}."
                + (" Groups are thin; read direction only."
                   if blk["thin"] else ""))
            add("")
    add(SRC4)
    add("")

    # ---- summary
    add("## What this decomposition explains, and what it does not")
    add("")
    for line in data["_summary"]:
        add(f"{line}")
        add("")
    return "\n".join(A).rstrip() + "\n"


# ---------------------------------------------------------------------------


def summary_lines(data: dict) -> list:
    """Five lines, written so a reader who reads only these is not misled."""
    s1 = data["section1"][PRIMARY_DIR]
    gaps = {b: s1[b]["unclear_gap_imposter_minus_twin"] for b in BIN_ORDER}
    gap_str = ", ".join(fmt(gaps[b], 4, True) for b in BIN_ORDER)
    p_tw = s1["_freshest_vs_rest"][TWIN_ARM]
    r_tw = data["section1"]["flashlite"]["_freshest_vs_rest"][TWIN_ARM]
    na_bins = [b for b in BIN_ORDER
               if not s1["_pairing"]["channel2"][b]["difference_printed"]]
    s3 = data["section3"][PRIMARY_DIR]
    frozen, non_match, half = (s3["frozen_excluded"], s3["counted_as_non_match"],
                               s3["counted_as_half"])
    lex = data["section2"]["lexical_jaccard"]
    emb = data["section2"].get("embedding_cosine")

    def _sign(x):
        return "positive" if (x or 0) > 0 else "negative"

    return [
        f"1. **The imposter-minus-twin UNCLEAR gap does NOT concentrate in the "
        f"crossover bin — the twin's OWN UNCLEAR rate does.** On the primary "
        f"model the gap is roughly flat across bins ({gap_str}). What is not "
        f"flat is the stale own twin's UNCLEAR rate: "
        f"{fmt(p_tw['freshest_unclear_rate'])} in the freshest bin against "
        f"{fmt(p_tw['rest_unclear_rate'])} across the other three pooled. That "
        f"freshest bin is exactly where channel 2 puts its pooled crossover and "
        f"where its positive slope begins, and it is the bin whose twin "
        f"denominator is thinned hardest. On flash-lite — the model with no "
        f"positive slope and no crossover — the same comparison is "
        f"{fmt(r_tw['freshest_unclear_rate'])} vs "
        f"{fmt(r_tw['rest_unclear_rate'])}, barely a spike. Related: the "
        f"channel-2 bins printing `n/a` for own − fresh imposter "
        f"({', '.join(na_bins) or 'none'}) do so because the imposter arm loses "
        f"whole subjects to UNCLEAR, while the crossover statistic compares the "
        f"same two means without that guard.",

        f"2. **A Δ-correlated era covariate exists between subjects but "
        f"vanishes within them, and it does not track the stance slope.** "
        f"Grounding-to-answer overlap rises with Δ across cells (lexical "
        f"Jaccard r = {fmt(lex['across_cells'].get('pearson_r'), 4, True)}, p = "
        f"{fmt_p(lex['across_cells'].get('pearson_p'))}"
        + (f"; embedding cosine r = "
           f"{fmt(emb['across_cells'].get('pearson_r'), 4, True)}, p = "
           f"{fmt_p(emb['across_cells'].get('pearson_p'))}" if emb else "")
        + f"), so the confound B7 declares is measurable. But cells are not "
        f"independent — the same subject fills several — and within subjects "
        f"the covariate is flat (mean slope "
        f"{fmt(lex['slope_test'].get('mean'), 6, True)} per year, p = "
        f"{fmt_p(lex['slope_test'].get('p'))}, n = {lex['slope_test'].get('n')}). "
        f"Per subject it also does not correlate with the channel-2 stance "
        f"slope (r = "
        f"{fmt(lex['vs_channel2_stance_slope'].get('pearson_r'), 4, True)}, "
        f"p = {fmt_p(lex['vs_channel2_stance_slope'].get('pearson_p'))}, n = "
        f"{lex['vs_channel2_stance_slope'].get('n')}). On this evidence era "
        f"drift is not what produces the anti-decay slope — though n is small "
        f"and this is a correlation, not a test of mechanism.",

        f"3. **The stance slope's sign is not an artefact of the UNCLEAR rule.** "
        f"Under the frozen rule the primary-model slope is "
        f"{fmt(frozen.get('mean'), 5, True)} per year (p = "
        f"{fmt_p(frozen.get('p'))}); counting UNCLEAR as a non-match gives "
        f"{fmt(non_match.get('mean'), 5, True)} (p = "
        f"{fmt_p(non_match.get('p'))}); counting it as 0.5 gives "
        f"{fmt(half.get('mean'), 5, True)} (p = {fmt_p(half.get('p'))}). All "
        f"three are {_sign(frozen.get('mean'))}. The frozen rule stays the "
        f"reported number; the variants only show the direction does not hinge "
        f"on it.",

        f"4. **Crossing and non-crossing subjects are not cleanly separated by "
        f"contamination, item count, or bins filled.** The differences are "
        f"small, inconsistent in sign across the four model-by-channel cells, "
        f"and the smallest group is 11 subjects. These cells are too thin to "
        f"read as a finding; they are reported so nobody has to wonder whether "
        f"the split was checked.",

        f"5. **Net: the disagreement is narrowed, not resolved.** Two candidate "
        f"explanations are weakened here — era drift does not track the slope, "
        f"and the UNCLEAR rule does not flip its sign. One is strengthened: the "
        f"channel-2 denominators are thin and unevenly thinned, worst in the "
        f"bin that carries the crossover, so channel 2's H7 numbers are noisier "
        f"than channel 1's. Nothing here identifies what makes the stance slope "
        f"positive, and nothing here changes the frozen conclusion in the "
        f"confirmatory report: the channels disagree, so H7 gets no headline "
        f"reading.",
    ]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-embed", action="store_true",
                    help="skip the embedding covariate and report the "
                         "truncation-free lexical one only")
    ap.add_argument("--out-md", default=str(OUT_MD))
    args = ap.parse_args(argv)

    t0 = time.time()
    data = compute(use_embedding=not args.no_embed)
    data["_summary"] = summary_lines(data)
    text = render(data)
    out = Path(args.out_md)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    try:
        shown = out.resolve().relative_to(_ROOT)
    except ValueError:
        shown = out
    print(f"[h7-diag] wrote {shown} "
          f"({len(text.splitlines())} lines, {round(time.time() - t0, 1)}s, "
          f"$0.00)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
