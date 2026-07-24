"""On-node driver for the Stage-1E ADAPTIVE arm (Leonardo, vLLM in-process).

The adaptive policy is sequential -- round r+1's prompts depend on round r's
answers -- so it cannot be a pre-exported prompt file. This script builds the
vLLM engine **once** and loops the rounds in-process, batching all persons per
round in lockstep. One job, one engine init.

Per round r (0-based, 20 rounds):
  1. one batch of ``n_persons * (48 - r)`` uncertainty prompts -- for every
     person, a 1-5 probability distribution for every item not yet revealed;
  2. reveal each person's max-entropy item (ties -> lowest canonical index);
  3. if the new reveal count is a checkpoint, one batch of ``n_persons * 10``
     TIPI prediction prompts.

Output (appended and fsynced after every round, so a walltime cut loses at most
the round in flight):

  completions_adaptive.jsonl : {idx, kind:"predict", person_id, k, item,
                                prompt, text, tokens_in, tokens_out}
  uncertainty.jsonl          : {person_id, round, item, entropy, selected,
                                parse_failure, prompt_sha256, tokens_in,
                                tokens_out}
  reveal_orders.json         : {person_id: [item codes in reveal order]}
  node_summary.json          : timings, counts, throughput

The input pack carries **no TIPI answers** (they are stripped when the pack is
built locally), so this node cannot leak a held-out answer into any prompt even
in principle. Prompt text comes from ``adaptive_render.py`` -- the same file the
local exporter uses, rsynced next to this script.

:func:`run_rounds` takes the generation function as an argument, so the whole
loop is exercised offline by tests/test_adaptive.py with a stub generator.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:  # on the node: adaptive_render.py sits next to this file
    import adaptive_render as R
except ImportError:  # locally (tests): it lives in the doppler package
    from doppler import adaptive_render as R

DEFAULT_MODEL = "/leonardo_work/AIFAC_P02_548/DOPPLER/models/Gemma-4-31B-it"


def build_args(argv=None):
    p = argparse.ArgumentParser(description="DOPPLER Stage-1E adaptive arm driver.")
    p.add_argument("--pack", required=True, help="node pack JSON (no TIPI answers)")
    p.add_argument("--outdir", required=True)
    p.add_argument("--model-dir", default=DEFAULT_MODEL)
    p.add_argument("--tp", type=int, default=4)
    p.add_argument("--max-model-len", type=int, default=2048)
    p.add_argument("--gpu-mem-util", type=float, default=0.92)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--limit-persons", type=int, default=0,
                   help="smoke mode: use only the first N persons")
    p.add_argument("--limit-rounds", type=int, default=0,
                   help="smoke mode: stop after N reveal rounds")
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def make_engine(args):
    from vllm import LLM
    t0 = time.time()
    llm = LLM(model=args.model_dir, tensor_parallel_size=args.tp,
              max_model_len=args.max_model_len,
              gpu_memory_utilization=args.gpu_mem_util, seed=args.seed)
    init_s = time.time() - t0
    print(f"[engine] init {init_s:.1f}s model={args.model_dir} tp={args.tp}",
          flush=True)
    return llm, init_s


def make_generate(llm, tok, args):
    """Return ``generate(prompts, max_tokens) -> [{text, tokens_in, tokens_out}]``."""
    from vllm import SamplingParams

    def generate(prompts, max_tokens):
        texts = [
            tok.apply_chat_template([{"role": "user", "content": p}],
                                    tokenize=False, add_generation_prompt=True,
                                    enable_thinking=False)
            for p in prompts
        ]
        sps = [SamplingParams(temperature=args.temperature, seed=args.seed,
                              max_tokens=max_tokens) for _ in texts]
        outs = llm.generate(texts, sps)
        return [{"text": o.outputs[0].text,
                 "tokens_in": len(o.prompt_token_ids),
                 "tokens_out": len(o.outputs[0].token_ids)} for o in outs]

    return generate


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


class Sink:
    """Append-and-fsync JSONL writer (durable across a walltime kill)."""

    def __init__(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.fh = open(path, "w")

    def __call__(self, rows):
        for row in rows:
            self.fh.write(json.dumps(row) + "\n")
        self.fh.flush()
        os.fsync(self.fh.fileno())

    def close(self):
        self.fh.close()


def check_no_tipi_in_demographics(persons, tipi_codes):
    """Fail loudly if any demographics block carries TIPI content."""
    for person in persons:
        head = person["demographics_block"]
        for code in tipi_codes:
            text = person["tipi_texts"][code]
            if text and text in head:
                raise AssertionError(
                    f"TIPI text in demographics of person {person['person_id']}")
        if "I see myself as" in head:
            raise AssertionError("TIPI framing in a demographics block")


# ---------------------------------------------------------------------------
# The round loop (pure: generation is injected)
# ---------------------------------------------------------------------------


def run_rounds(persons, meta, generate, pred_sink, unc_sink, max_reveals,
               log=print, revealed=None, done_ks=(), start_idx=0):
    """Run the adaptive reveal loop. Returns ``(reveal_orders, stats)``.

    ``generate(prompts, max_tokens)`` must return one dict per prompt with
    ``text``/``tokens_in``/``tokens_out``, in order.

    Resume: pass ``revealed`` (a complete, equal-length reveal prefix for every
    person), the set of checkpoints already fully predicted as ``done_ks``, and
    the next free record index. Any checkpoint that the prefix has already
    passed but that is not in ``done_ks`` is predicted first, so a job killed
    between a reveal and its checkpoint loses nothing.
    """
    riasec_codes = meta["riasec_codes"]
    tipi_codes = meta["tipi_codes"]
    r_anchors = meta["riasec_anchors"]
    t_anchors = meta["tipi_anchors"]
    checkpoints = set(meta["checkpoints"])

    check_no_tipi_in_demographics(persons, tipi_codes)

    revealed = revealed if revealed is not None else {p["person_id"]: []
                                                      for p in persons}
    depths = {len(v) for v in revealed.values()}
    if len(depths) != 1:
        raise AssertionError(f"reveal prefixes are not in lockstep: {sorted(depths)}")
    done_ks = set(done_ks)
    stats = {"n_uncertainty_calls": 0, "n_prediction_calls": 0,
             "uncertainty_parse_failures": 0, "tokens_in": 0, "tokens_out": 0}
    idx = start_idx

    def predict_at(k):
        """One checkpoint batch: 10 TIPI predictions per person at depth k."""
        nonlocal idx
        prompts, keys = [], []
        for person in persons:
            pid = person["person_id"]
            pairs = [(person["interests"][c]["text"],
                      person["interests"][c]["answer"]) for c in revealed[pid][:k]]
            for code in tipi_codes:
                prompts.append(R.tipi_prompt(person["demographics_block"], pairs,
                                             r_anchors,
                                             person["tipi_texts"][code], t_anchors))
                keys.append((pid, code))
        t0 = time.time()
        res = generate(prompts, meta["max_output_tokens_tipi"])
        stats["n_prediction_calls"] += len(res)
        rows = []
        for (pid, code), r in zip(keys, res):
            stats["tokens_in"] += r["tokens_in"]
            stats["tokens_out"] += r["tokens_out"]
            rows.append({"idx": idx, "kind": "predict", "person_id": pid, "k": k,
                         "item": code, "prompt": prompts[len(rows)],
                         "text": r["text"], "tokens_in": r["tokens_in"],
                         "tokens_out": r["tokens_out"]})
            idx += 1
        pred_sink(rows)
        done_ks.add(k)
        log(f"[checkpoint k={k}] {len(res)} predictions in {time.time() - t0:.1f}s")

    start_round = depths.pop()
    for k in sorted(checkpoints):  # catch up anything the prefix already passed
        if k <= start_round and k not in done_ks:
            log(f"[resume] catching up checkpoint k={k}")
            predict_at(k)

    for rnd in range(start_round, max_reveals):
        # ---- 1. uncertainty over every remaining candidate -----------------
        prompts, keys = [], []
        for person in persons:
            pid = person["person_id"]
            done = set(revealed[pid])
            pairs = [(person["interests"][c]["text"],
                      person["interests"][c]["answer"]) for c in revealed[pid]]
            for code in riasec_codes:  # canonical order -> lowest-index tie-break
                if code in done:
                    continue
                text = person["interests"][code]["text"]
                prompts.append(R.interest_prompt(person["demographics_block"],
                                                 pairs, r_anchors, text))
                keys.append((pid, code))

        t0 = time.time()
        res = generate(prompts, meta["max_output_tokens_interest"])
        unc_s = time.time() - t0
        stats["n_uncertainty_calls"] += len(res)

        by_person = {p["person_id"]: [] for p in persons}
        rows = []
        for (pid, code), r, prompt in zip(keys, res, prompts):
            dist = R.parse_interest_distribution(r["text"])
            ent = R.entropy(dist)
            failed = dist is None
            stats["uncertainty_parse_failures"] += int(failed)
            stats["tokens_in"] += r["tokens_in"]
            stats["tokens_out"] += r["tokens_out"]
            by_person[pid].append((code, ent))
            rows.append({"person_id": pid, "round": rnd, "item": code,
                         "entropy": ent, "selected": False,
                         "parse_failure": failed,
                         "prompt_sha256": R.sha256(prompt),
                         "tokens_in": r["tokens_in"],
                         "tokens_out": r["tokens_out"]})

        # ---- 2. reveal the max-entropy item --------------------------------
        chosen = {}
        for pid, cands in by_person.items():
            best_code, best_ent = None, None
            for code, ent in cands:
                if best_ent is None or ent > best_ent:  # strict '>' keeps first
                    best_code, best_ent = code, ent
            chosen[pid] = best_code
            revealed[pid].append(best_code)
        for row in rows:
            if chosen[row["person_id"]] == row["item"]:
                row["selected"] = True
        unc_sink(rows)

        k = rnd + 1
        log(f"[round {k}/{max_reveals}] {len(res)} uncertainty calls in "
            f"{unc_s:.1f}s")

        # ---- 3. checkpoint predictions -------------------------------------
        if k in checkpoints and k not in done_ks:
            predict_at(k)

    return revealed, stats


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


def _read_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_resume_state(outdir, person_ids, n_tipi):
    """Recover a clean, lockstep state from a previous job's partial output.

    Only *complete* units survive: a reveal round counts only if every person
    selected an item in it, and a checkpoint counts only if all
    ``n_persons * n_tipi`` predictions are present. Partial rounds and partial
    checkpoints are dropped and redone, so nothing is double-counted and
    nothing is silently missing.

    Returns ``(revealed, done_ks, next_idx, unc_rows, pred_rows)`` where the two
    row lists are exactly what should be rewritten before appending.
    """
    unc_rows = _read_jsonl(os.path.join(outdir, "uncertainty.jsonl"))
    pred_rows = _read_jsonl(os.path.join(outdir, "completions_adaptive.jsonl"))
    ids = list(person_ids)
    if not unc_rows:
        return {pid: [] for pid in ids}, set(), 0, [], []

    selected = {}
    for row in unc_rows:
        if row.get("selected"):
            selected[(row["person_id"], row["round"])] = row["item"]
    depth = 0
    while all((pid, depth) in selected for pid in ids):
        depth += 1
    revealed = {pid: [selected[(pid, r)] for r in range(depth)] for pid in ids}
    unc_rows = [r for r in unc_rows if r["round"] < depth]

    by_k = {}
    for row in pred_rows:
        by_k.setdefault(row["k"], []).append(row)
    done_ks = {k for k, rows in by_k.items()
               if len(rows) == len(ids) * n_tipi and k <= depth}
    pred_rows = [r for r in pred_rows if r["k"] in done_ks]
    next_idx = max((r["idx"] for r in pred_rows), default=-1) + 1
    return revealed, done_ks, next_idx, unc_rows, pred_rows


def main():
    args = build_args()
    with open(args.pack) as fh:
        pack = json.load(fh)
    meta = pack["meta"]
    persons = pack["persons"]
    if args.limit_persons:
        persons = persons[: args.limit_persons]
    max_reveals = args.limit_rounds or meta["max_reveals"]

    # Recover whatever a previous job left behind (complete units only).
    ids = [p["person_id"] for p in persons]
    revealed, done_ks, next_idx, unc_rows, pred_rows = load_resume_state(
        args.outdir, ids, len(meta["tipi_codes"]))
    resumed = bool(unc_rows) or bool(pred_rows)
    if resumed:
        print(f"[resume] {len(revealed[ids[0]])} reveal rounds intact, "
              f"checkpoints done: {sorted(done_ks)}, next idx {next_idx}",
              flush=True)
    # Nothing left to do -> exit BEFORE paying a ~3 min engine init. This is
    # what makes a chain of short jobs cheap: the tail jobs cost seconds.
    if (len(revealed[ids[0]]) >= max_reveals
            and set(meta["checkpoints"]) <= done_ks):
        print("[done] already complete; no engine init needed.", flush=True)
        with open(os.path.join(args.outdir, "reveal_orders.json"), "w") as fh:
            json.dump({str(k): v for k, v in revealed.items()}, fh, indent=2)
        sys.stdout.flush()
        os._exit(0)

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.model_dir)
    llm, init_s = make_engine(args)
    generate = make_generate(llm, tok, args)

    # Rewrite the kept rows, then append from there.
    pred_sink = Sink(os.path.join(args.outdir, "completions_adaptive.jsonl"))
    unc_sink = Sink(os.path.join(args.outdir, "uncertainty.jsonl"))
    if pred_rows:
        pred_sink(pred_rows)
    if unc_rows:
        unc_sink(unc_rows)
    t_start = time.time()
    try:
        revealed, stats = run_rounds(persons, meta, generate, pred_sink, unc_sink,
                                     max_reveals, revealed=revealed,
                                     done_ks=done_ks, start_idx=next_idx)
    finally:
        pred_sink.close()
        unc_sink.close()
    wall = time.time() - t_start

    with open(os.path.join(args.outdir, "reveal_orders.json"), "w") as fh:
        json.dump({str(k): v for k, v in revealed.items()}, fh, indent=2)
    summary = {
        "model_dir": args.model_dir, "tp": args.tp,
        "max_model_len": args.max_model_len, "gpu_mem_util": args.gpu_mem_util,
        "temperature": args.temperature, "seed": args.seed,
        "n_persons": len(persons), "rounds": max_reveals, "resumed": resumed,
        "engine_init_seconds": round(init_s, 2),
        "generation_wall_seconds": round(wall, 2),
        "total_tokens_in": stats["tokens_in"],
        "total_tokens_out": stats["tokens_out"],
        "output_tokens_per_second":
            round(stats["tokens_out"] / wall, 1) if wall > 0 else None,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    summary.update({k: stats[k] for k in
                    ("n_uncertainty_calls", "n_prediction_calls",
                     "uncertainty_parse_failures")})
    with open(os.path.join(args.outdir, "node_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    # One line per job, so a chained run keeps every leg's cost visible.
    with open(os.path.join(args.outdir, "node_runs.jsonl"), "a") as fh:
        fh.write(json.dumps(summary) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    print("[summary] " + json.dumps(summary), flush=True)
    sys.stdout.flush()
    os._exit(0)  # dodge the GPU-less teardown hang (Leonardo how-to)


if __name__ == "__main__":
    main()
