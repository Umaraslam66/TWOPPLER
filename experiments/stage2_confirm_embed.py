#!/usr/bin/env python3
"""Confirmatory Stage 2 -- channel 1, the embedding score. Local, CPU, no API.

One number per generated answer: the cosine between it and what the person
actually said. The model is pinned by name AND by HuggingFace commit, per
``PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md`` instrument parameter 1:

    sentence-transformers/all-mpnet-base-v2
    revision e8c3b32edf5434bc2275fc9bab85f82640a19130

The pin is asserted, not trusted. ``huggingface_hub`` resolves the revision to
a cache directory whose *name is the commit sha*, that name is compared to the
pin, and the model is then loaded from that resolved path. If the resolution
does not land on the pinned commit, this driver refuses to run rather than
score with a different model -- an unpinned embedding is not a reproducible
instrument, and channel 1's whole number depends on it.

Scope and non-scope
-------------------
This driver produces cosines and RAW PER-ARM MEANS. It produces no contrast, no
confidence interval, and no verdict. The pre-registered bars are judged once,
in the final report, against the frozen text -- not here. The per-arm means are
here for the standing "watch which arm moves" rule: an arm that moves in an odd
direction is a leakage signal worth chasing before anything is celebrated.

Both scored models are handled the same way and scored by the same instrument;
absolute numbers from the flash-lite side stay secondary per Amendment 3 C3.

Resumable and chunk-safe
------------------------
Work is per (generation directory, chunk). A chunk is scored only when its
completions file is *complete and sha-clean* against the committed join
sidecar -- so a file another process is still appending to is skipped with a
message instead of being half-scored. Re-running costs nothing for chunks
already done.

Usage::

    .venv/bin/python experiments/stage2_confirm_embed.py
    .venv/bin/python experiments/stage2_confirm_embed.py --models gemma
    .venv/bin/python experiments/stage2_confirm_embed.py --status
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments"))

from doppler import stage2_data as S  # noqa: E402
from doppler import stage2_render as R  # noqa: E402

RESULTS_DIR = _ROOT / "results"
CONFIRM_DIR = RESULTS_DIR / "stage2_confirm"
GEN_ROOT = CONFIRM_DIR / "gen"
EMBED_DIR = CONFIRM_DIR / "embed"

#: Addendum A instrument parameter 1. Both values are load-bearing.
PINNED_EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"
PINNED_EMBED_REVISION = "e8c3b32edf5434bc2275fc9bab85f82640a19130"

#: The scoring direction, also frozen: cosine(generated answer, real verbatim
#: answer). mpnet is a symmetric encoder, so no query/passage prefix applies --
#: that footgun belongs to e5, which is not the pinned model.
SCORE_DESCRIPTION = ("cosine between the generated answer and the real "
                     "verbatim answer, both encoded by the pinned model")

#: gen/<dir> -> the model version string that produced it.
GEN_DIRS = {"gemma": "Gemma-4-31B-it", "flashlite": "gemini-3.5-flash-lite"}

CHUNK_ALLOWLIST = ("chunk_01", "chunk_02", "chunk_03", "chunk_04", "chunk_05")

#: Fixed so a re-run reproduces the numbers bit for bit.
BATCH_SIZE = 8
DEFAULT_THREADS = 4
TORCH_SEED = 20260728

BANNER = ("CONFIRMATORY. Channel 1 (embedding) scores. Raw per-arm means only "
          "-- no contrasts, no confidence intervals, no hypothesis verdicts. "
          "Bars are judged once, in the final report.")


def now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(_ROOT))
    except ValueError:
        return str(path)


def fatal(msg: str) -> "SystemExit":
    return SystemExit(f"[fatal] {msg}")


# ---------------------------------------------------------------------------
# The pinned model
# ---------------------------------------------------------------------------


def resolve_pinned_model(offline_first: bool = True) -> dict:
    """Resolve the pin to a local path and PROVE it is the pinned commit.

    ``snapshot_download`` lays the cache out as
    ``models--<org>--<name>/snapshots/<commit sha>/``, so the resolved
    directory's own name is the commit that was materialised. Comparing that
    name to the pin is a direct check on the bytes about to be loaded, not a
    restatement of the argument that was passed in.
    """
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise fatal(f"huggingface_hub is not installed ({exc})")

    path = None
    errors = []
    for local_only in ((True, False) if offline_first else (False,)):
        try:
            path = snapshot_download(repo_id=PINNED_EMBED_MODEL,
                                     revision=PINNED_EMBED_REVISION,
                                     local_files_only=local_only)
            break
        except Exception as exc:  # noqa: BLE001 - reported, then retried online
            errors.append(f"local_files_only={local_only}: "
                          f"{type(exc).__name__}: {exc}")
    if path is None:
        raise fatal("could not resolve "
                    f"{PINNED_EMBED_MODEL}@{PINNED_EMBED_REVISION}: "
                    + " | ".join(errors))

    resolved = Path(path).resolve()
    if resolved.name != PINNED_EMBED_REVISION:
        raise fatal(
            f"the pinned revision resolved to {resolved.name!r}, not "
            f"{PINNED_EMBED_REVISION!r}. Addendum A parameter 1 pins channel 1 "
            "to one commit; refusing to score with anything else.")
    weights = resolved / "model.safetensors"
    if not weights.exists():
        weights = resolved / "pytorch_model.bin"
    if not weights.exists():
        raise fatal(f"no model weights under {resolved}")
    return {
        "name": PINNED_EMBED_MODEL,
        "revision": PINNED_EMBED_REVISION,
        "resolved_snapshot_dir": str(resolved),
        "resolved_dir_name": resolved.name,
        "revision_assertion": "resolved snapshot directory name == pinned "
                              "revision",
        "revision_asserted": True,
        "weights_file": weights.name,
        "weights_bytes": weights.stat().st_size,
        "device": "cpu",
    }


def load_model(pin: dict, threads: int):
    try:
        import torch
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise fatal("channel 1 needs CPU-only torch + sentence-transformers "
                    f"({exc})")
    torch.manual_seed(TORCH_SEED)
    torch.set_grad_enabled(False)
    torch.set_num_threads(int(threads))
    model = SentenceTransformer(pin["resolved_snapshot_dir"], device="cpu")
    model.eval()
    # A second, independent read of what actually got loaded.
    loaded = getattr(getattr(model, "_first_module", lambda: None)(),
                     "auto_model", None)
    pin["loaded_hidden_size"] = (
        int(loaded.config.hidden_size) if loaded is not None else None)
    pin["torch_version"] = torch.__version__
    pin["torch_threads"] = int(threads)
    return model


def encode(model, texts: list[str]):
    """Encode with the frozen batch size. mpnet takes text as it is."""
    return model.encode(list(texts), batch_size=BATCH_SIZE,
                        show_progress_bar=False, convert_to_numpy=True,
                        normalize_embeddings=False)


def cosine(a, b) -> float:
    import numpy as np
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(a.dot(b) / (na * nb))


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def load_items() -> dict:
    path = CONFIRM_DIR / "items_confirm.jsonl"
    if not path.exists():
        raise fatal(f"{rel(path)} not found")
    return {r["item_id"]: r for r in S.read_jsonl(path)}


def chunk_sha_sets() -> dict[str, set]:
    """chunk -> the set of prompt_sha256 that chunk is supposed to contain."""
    out = {}
    for chunk in CHUNK_ALLOWLIST:
        path = CONFIRM_DIR / "node" / f"{chunk}.meta.jsonl"
        if path.exists():
            out[chunk] = {r["prompt_sha256"] for r in S.read_jsonl(path)}
    return out


def completions_state(gen_dir: str, expected: dict[str, set]) -> dict:
    """Per chunk: present / complete / sha-clean, and why not when not."""
    state = {}
    for chunk, shas in expected.items():
        path = GEN_ROOT / gen_dir / f"completions_{chunk}.jsonl"
        rec = {"path": rel(path), "present": path.exists(),
               "n_rows": 0, "n_expected": len(shas), "ready": False,
               "reason": None}
        if not path.exists():
            rec["reason"] = "not generated yet"
            state[chunk] = rec
            continue
        try:
            rows = S.read_jsonl(path)
        except json.JSONDecodeError:
            rec["reason"] = ("file is mid-write (a line is not valid JSON); "
                             "leaving it for a later pass")
            state[chunk] = rec
            continue
        rec["n_rows"] = len(rows)
        got = {r.get("prompt_sha256") for r in rows}
        if got == shas and len(rows) == len(shas):
            rec["ready"] = True
        elif len(rows) < len(shas):
            rec["reason"] = (f"incomplete: {len(rows)} of {len(shas)} rows "
                             "(still generating?)")
        else:
            rec["reason"] = (
                f"sha mismatch: {len(shas - got)} prompts unanswered, "
                f"{len(got - shas)} answers with no prompt in this chunk")
        state[chunk] = rec
    return state


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_chunk(model, gen_dir: str, chunk: str, items: dict,
                pin: dict) -> list[dict]:
    """Cosines for one (generation dir, chunk). One row per completion."""
    rows = S.read_jsonl(GEN_ROOT / gen_dir / f"completions_{chunk}.jsonl")
    rows.sort(key=lambda r: r["prompt_sha256"])  # deterministic encode order

    item_ids = sorted({r["item_id"] for r in rows})
    for iid in item_ids:
        if iid not in items:
            raise fatal(f"item {iid} is not in items_confirm.jsonl")
    real_vecs = dict(zip(item_ids,
                         encode(model, [items[i]["real_answer_verbatim"]
                                        for i in item_ids])))
    gen_vecs = encode(model, [r["text"] or "" for r in rows])

    out = []
    for row, vec in zip(rows, gen_vecs):
        out.append({
            "chunk": chunk,
            "item_id": row["item_id"],
            "canonical_id": row["canonical_id"],
            "arm": row["arm"],
            "h7_bin": row.get("h7_bin"),
            "delta_days": row.get("delta_days"),
            "item_type": row.get("item_type"),
            "model": row["model"],
            "gen_dir": gen_dir,
            "prompt_sha256": row["prompt_sha256"],
            "embedding_model": pin["name"],
            "embedding_revision": pin["revision"],
            "cosine_to_real": round(cosine(vec, real_vecs[row["item_id"]]), 6),
            "answer_words": row.get("answer_words"),
            "truncated": row.get("truncated"),
            "over_word_cap": row.get("over_word_cap"),
            "empty_text": not (row.get("text") or "").strip(),
        })
    return out


def describe(values: list[float]) -> dict:
    """Raw descriptive statistics. Nothing here is a contrast or a verdict."""
    if not values:
        return {"n": 0, "mean": None, "median": None, "sd": None,
                "min": None, "max": None}
    return {
        "n": len(values),
        "mean": round(statistics.fmean(values), 6),
        "median": round(statistics.median(values), 6),
        "sd": round(statistics.stdev(values), 6) if len(values) > 1 else 0.0,
        "min": round(min(values), 6),
        "max": round(max(values), 6),
    }


def per_arm(rows: list[dict]) -> dict:
    out = {}
    for arm in sorted({r["arm"] for r in rows}):
        sub = [r for r in rows if r["arm"] == arm]
        block = describe([r["cosine_to_real"] for r in sub])
        block["n_subjects"] = len({r["canonical_id"] for r in sub})
        block["n_truncated"] = sum(1 for r in sub if r["truncated"])
        block["n_empty_text"] = sum(1 for r in sub if r["empty_text"])
        block["n_over_word_cap"] = sum(1 for r in sub if r["over_word_cap"])
        out[arm] = block
    return out


def per_logical_arm(rows: list[dict]) -> dict:
    """The same cosines, expanded to the LOGICAL renders.

    A prompt that is byte-identical across two logical rows (the H7-R5/R7
    dedup: 2,164 logical renders collapse to 1,911 unique prompts) is generated
    once and scored once, but it stands for more than one logical row. This
    block re-attaches those rows via ``render_index.jsonl``, joined on
    ``prompt_sha256``, so ``h7_imposter_fresh`` -- which has no unique prompt of
    its own -- is visible at all. Still descriptive only.
    """
    path = CONFIRM_DIR / "render_index.jsonl"
    if not path.exists():
        return {}
    by_sha = {}
    for row in rows:
        by_sha.setdefault(row["prompt_sha256"], row)
    expanded = []
    for logical in S.read_jsonl(path):
        scored = by_sha.get(logical.get("prompt_sha256"))
        if scored is None:
            continue
        expanded.append({**scored, "arm": logical["arm"],
                         "h7_bin": logical.get("h7_bin")})
    return per_arm(expanded) if expanded else {}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", nargs="*", default=sorted(GEN_DIRS),
                    help=f"generation dirs to score (default: all of "
                         f"{sorted(GEN_DIRS)})")
    ap.add_argument("--chunks", nargs="*", default=None,
                    help="chunks to score (default: every ready chunk)")
    ap.add_argument("--status", action="store_true",
                    help="report what is ready to score, score nothing")
    ap.add_argument("--threads", type=int, default=DEFAULT_THREADS,
                    help=f"torch CPU threads (default {DEFAULT_THREADS}); "
                         "recorded in the summary because it is part of the "
                         "reproduction recipe")
    ap.add_argument("--allow-download", action="store_true",
                    help="permit a network fetch if the pinned revision is "
                         "not already in the local HF cache")
    ap.add_argument("--force", action="store_true",
                    help="re-score chunks that already have cosines")
    args = ap.parse_args(argv)

    for name in args.models:
        if name not in GEN_DIRS:
            raise fatal(f"{name!r} is not a known generation dir "
                        f"{sorted(GEN_DIRS)}")
    for chunk in args.chunks or ():
        if chunk not in CHUNK_ALLOWLIST:
            raise fatal(f"{chunk!r} is not in the chunk allowlist")

    expected = chunk_sha_sets()
    if not expected:
        raise fatal("no join sidecars under results/stage2_confirm/node/")

    states = {d: completions_state(d, expected) for d in args.models}
    print("=== what is ready to score ===")
    for gen_dir in args.models:
        for chunk in CHUNK_ALLOWLIST:
            rec = states[gen_dir].get(chunk)
            if rec is None:
                continue
            flag = "READY" if rec["ready"] else "skip "
            note = "" if rec["ready"] else f"  ({rec['reason']})"
            print(f"{flag} {gen_dir:10s} {chunk} "
                  f"{rec['n_rows']}/{rec['n_expected']}{note}")
    if args.status:
        return 0

    pin = resolve_pinned_model(offline_first=not args.allow_download)
    print(f"[embed] pinned model resolved to {pin['resolved_snapshot_dir']}")
    print(f"[embed] revision assertion: directory name "
          f"{pin['resolved_dir_name']} == pin {PINNED_EMBED_REVISION} -> OK")

    EMBED_DIR.mkdir(parents=True, exist_ok=True)
    items = load_items()
    model = None
    t0 = time.time()
    scored_now, skipped = [], []

    for gen_dir in args.models:
        for chunk in (args.chunks or CHUNK_ALLOWLIST):
            rec = states[gen_dir].get(chunk)
            if rec is None or not rec["ready"]:
                skipped.append({"gen_dir": gen_dir, "chunk": chunk,
                                "reason": (rec or {}).get(
                                    "reason", "no sidecar")})
                continue
            out_path = EMBED_DIR / f"cosines_{gen_dir}_{chunk}.jsonl"
            if out_path.exists() and not args.force:
                have = S.read_jsonl(out_path)
                if {r["prompt_sha256"] for r in have} == expected[chunk]:
                    print(f"[embed] {gen_dir}/{chunk}: already scored "
                          f"({len(have)} rows), skipping")
                    continue
            if model is None:
                model = load_model(pin, args.threads)
            print(f"[embed] {gen_dir}/{chunk}: encoding "
                  f"{rec['n_rows']} generations")
            rows = score_chunk(model, gen_dir, chunk, items, pin)
            S.write_jsonl(out_path, rows)
            scored_now.append({"gen_dir": gen_dir, "chunk": chunk,
                               "n_rows": len(rows)})

    # ---- summary over everything on disk, not just what this process did ----
    results = {}
    for gen_dir in sorted(GEN_DIRS):
        rows = []
        chunks_present = []
        for chunk in CHUNK_ALLOWLIST:
            path = EMBED_DIR / f"cosines_{gen_dir}_{chunk}.jsonl"
            if path.exists():
                rows.extend(S.read_jsonl(path))
                chunks_present.append(chunk)
        if not rows:
            continue
        results[gen_dir] = {
            "model": GEN_DIRS[gen_dir],
            "chunks_scored": chunks_present,
            "chunks_missing": [c for c in CHUNK_ALLOWLIST
                               if c not in chunks_present],
            "n_rows": len(rows),
            "n_subjects": len({r["canonical_id"] for r in rows}),
            "n_items": len({r["item_id"] for r in rows}),
            "overall": describe([r["cosine_to_real"] for r in rows]),
            "per_arm_generated": per_arm(rows),
            "per_arm_logical_renders": per_logical_arm(rows),
        }

    summary = {
        "banner": BANNER,
        "channel": "1 (embedding)",
        "score": SCORE_DESCRIPTION,
        "instrument": pin,
        "contract": "PREREGISTRATION_AMENDMENT_2_ADDENDUM_A.md instrument "
                    "parameter 1 (pinned embedding model and revision)",
        "batch_size": BATCH_SIZE,
        "torch_seed": TORCH_SEED,
        "never_an_api_model": True,
        "no_verdicts_note": "Per-arm means below are raw descriptives for the "
                            "watch-which-arm-moves rule. No contrast, no CI "
                            "and no pass/fail is computed here; the frozen "
                            "bars are judged once, in the final report.",
        "results": results,
        "scored_this_run": scored_now,
        "skipped_this_run": skipped,
        "runtime_secs": round(time.time() - t0, 1),
        "embedded_utc": now(),
    }
    S.write_json(EMBED_DIR / "embed_summary.json", summary)

    print(f"\n=== channel 1 coverage (pinned {PINNED_EMBED_MODEL} "
          f"@ {PINNED_EMBED_REVISION[:12]}) ===")
    for gen_dir, res in results.items():
        print(f"\n{gen_dir} ({res['model']}): {res['n_rows']} rows over "
              f"{len(res['chunks_scored'])} chunk(s), "
              f"{res['n_subjects']} subjects")
        print(f"  {'arm':22s} {'n':>5s} {'mean':>9s} {'median':>9s} {'sd':>8s}")
        for arm, st in res["per_arm_generated"].items():
            print(f"  {arm:22s} {st['n']:5d} {st['mean']:9.4f} "
                  f"{st['median']:9.4f} {st['sd']:8.4f}")
        if res["chunks_missing"]:
            print(f"  not scored yet: {', '.join(res['chunks_missing'])}")
    for s in skipped:
        print(f"[embed] skipped {s['gen_dir']}/{s['chunk']}: {s['reason']}")
    print(f"\nwrote {rel(EMBED_DIR / 'embed_summary.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
