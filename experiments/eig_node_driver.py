"""On-node driver for the Stage-1E EXP3 EIG arm (Leonardo, vLLM in-process).

EXP3 asks a simple question: is it better to ask the question the model is most
unsure about (greedy self-uncertainty, run by the adaptive driver), or the
question whose answer would most change what the model believes about the
person's personality? This script runs the second policy, the
expected-information-gain ladder.

Per person, per round r:

  1. one 1-5 distribution for every item not yet revealed -> entropy -> keep the
     top ``--top-n`` most uncertain items as the shortlist. (Cheap filter: we
     cannot afford the step-3 sweep over all 48 items.)
  2. one reference call: what do I believe about all 10 TIPI targets *right
     now*? Call it P0.
  3. for each shortlisted item c and each hypothetical answer a in
     ``--hypotheticals``: one call asking the same 10 targets, but with the pair
     (c's text, a) appended to the revealed block. Call it P[c][a].
  4. shift(c, a) = average over the 10 targets of the total-variation distance
     between P[c][a] and P0 -- "how far would my belief move".
  5. weight each hypothetical by how likely the person is to give that answer,
     taken from c's own step-1 distribution (uniform if that failed to parse).
  6. reveal the item with the biggest weighted shift. Ties -> seeded random.

Step 7 of the design, spelled out because it matters: an unparseable
hypothetical completion contributes a shift of **0.0**, not a failure sentinel.
"No evidence of movement" is the honest reading, and it means a candidate whose
calls all failed loses to any candidate with real movement instead of winning by
accident.

Steps 2-3 use a **multi-target** prompt (all 10 TIPI distributions in one
completion) purely to afford the sweep. Those completions are policy machinery
and are never scored. Checkpoint predictions -- the actual outcome -- use the
single-target ``adaptive_render.tipi_prompt``, identical to every other arm, so
the ladder is comparable across experiments.

Because the multi-target format is new, the driver **smoke-tests it on the node
before committing the run** (``--smoke-n`` prompts, ``--min-parse-rate``). If the
model cannot reliably produce 10 clean lines, the driver falls back to 10
single-target calls per hypothetical -- same policy, same maths, 10x the cost --
and cuts the person list to ``--fallback-persons`` so the job still fits. It
never aborts: a smaller ladder beats no ladder.

Output (appended and fsynced after every round, so a walltime cut loses at most
the round in flight):

  completions_eig.jsonl : {idx, kind:"predict", person_id, k, item, prompt,
                           text, tokens_in, tokens_out}   <- the local ingester
                           depends on this exact shape
  eig_scores.jsonl      : {person_id, round, item, rank, entropy, tv_shift,
                           weights, score, selected, parse_failures,
                           reference_parse_failure, n_tied}
  reveal_orders.json    : {person_id: [item codes in reveal order]}
  multi_target_smoke.json : the format smoke test's verdict
  node_summary.json     : mode, timings, counts, throughput
  node_runs.jsonl       : one summary line per job leg

The input pack carries **no TIPI answers** (they are stripped when the pack is
built locally), so this node cannot leak a held-out answer into any prompt even
in principle.

:func:`run_eig_rounds` takes the generation function as an argument, so the
whole loop is exercised offline by tests/test_eig.py with a stub generator.
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
try:  # same story for the EIG renderer
    import eig_render as E
except ImportError:
    from doppler import eig_render as E

DEFAULT_MODEL = "/leonardo_work/AIFAC_P02_548/DOPPLER/models/Gemma-4-31B-it"

MODE_MULTI = "multi_target"
MODE_FALLBACK = "per_target_fallback"


def _int_list(text):
    """Parse ``"1,2,4"`` (or whitespace-separated) into ``[1, 2, 4]``."""
    return [int(part) for part in str(text).replace(",", " ").split() if part]


def build_args(argv=None):
    p = argparse.ArgumentParser(description="DOPPLER Stage-1E EXP3 EIG driver.")
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
    p.add_argument("--checkpoints", default="1,2,3,4,5,8,12,16,20",
                   help="reveal depths at which to predict the TIPI targets")
    p.add_argument("--max-reveals", type=int, default=20)
    p.add_argument("--top-n", type=int, default=5,
                   help="how many max-entropy items get the full EIG sweep")
    p.add_argument("--hypotheticals", default="1,3,5",
                   help="answers simulated for each shortlisted item")
    p.add_argument("--tiebreak-seed", type=int, default=71)
    p.add_argument("--smoke-n", type=int, default=200,
                   help="multi-target prompts used to test the answer format")
    p.add_argument("--min-parse-rate", type=float, default=0.95,
                   help="below this, fall back to per-target calls")
    p.add_argument("--fallback-persons", type=int, default=40,
                   help="person budget when the per-target fallback kicks in")
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
# One "evaluation unit": what do you believe about all 10 targets, given this
# profile? Multi-target mode answers it in one call; the fallback needs ten.
# ---------------------------------------------------------------------------


def _pairs_for(person, codes):
    """The ordered ``(item_text, answer)`` list for a reveal prefix."""
    return [(person["interests"][c]["text"], person["interests"][c]["answer"])
            for c in codes]


def unit_prompts(person, meta, base_pairs, cand_code, answer, mode):
    """Prompts for one evaluation unit.

    ``cand_code is None`` means the reference unit (current profile, nothing
    hypothetical). Otherwise the pair ``(candidate item text, answer)`` is
    appended to the revealed block -- deliberately built by the same renderer as
    a real reveal, so the model cannot tell a hypothesis from a fact.
    """
    pairs = list(base_pairs)
    if cand_code is not None:
        pairs.append((person["interests"][cand_code]["text"], answer))
    demo = person["demographics_block"]
    r_anchors = meta["riasec_anchors"]
    t_anchors = meta["tipi_anchors"]
    codes = meta["tipi_codes"]
    if mode == MODE_MULTI:
        return [E.multi_tipi_prompt(demo, pairs, r_anchors, codes,
                                    person["tipi_texts"], t_anchors)]
    return [R.tipi_prompt(demo, pairs, r_anchors, person["tipi_texts"][c],
                          t_anchors) for c in codes]


def unit_distributions(texts, tipi_codes, mode):
    """Completions for one evaluation unit -> ``{code: {1..7: prob}}`` or None.

    Multi-target mode is all-or-nothing (see ``eig_render.parse_multi_tipi``).
    The fallback keeps whatever parsed and returns ``None`` only when all ten
    failed; a target missing from the dict later contributes zero movement, so
    a single bad line costs that target's vote rather than the whole candidate.
    """
    if mode == MODE_MULTI:
        return E.parse_multi_tipi(texts[0], tipi_codes)
    out = {}
    for code, text in zip(tipi_codes, texts):
        dist = E.parse_tipi_distribution(text)
        if dist is not None:
            out[code] = dist
    return out or None


# ---------------------------------------------------------------------------
# Node-side format smoke test
# ---------------------------------------------------------------------------


def build_smoke_prompts(persons, meta, n, depths=(0, 1, 3)):
    """A spread of multi-target prompts to test the answer format with.

    Depth 0 is what round 0 actually sends; the shallow synthetic depths make
    sure a populated revealed block does not tip the model out of the 10-line
    format. Prefixes are offset per prompt so we are not measuring the parse
    rate of one repeated string.
    """
    if n <= 0 or not persons:
        return []
    riasec = meta["riasec_codes"]
    out = []
    i = 0
    while len(out) < n and i < 4 * n:
        person = persons[i % len(persons)]
        depth = depths[(i // len(persons)) % len(depths)]
        span = max(1, len(riasec) - depth)
        off = (i * 7) % span
        pairs = _pairs_for(person, riasec[off:off + depth])
        out.append(E.multi_tipi_prompt(
            person["demographics_block"], pairs, meta["riasec_anchors"],
            meta["tipi_codes"], person["tipi_texts"], meta["tipi_anchors"]))
        i += 1
    return out[:n]


def run_smoke_test(persons, meta, generate, n, min_rate, log=print):
    """Generate the smoke prompts and report the multi-target parse rate."""
    prompts = build_smoke_prompts(persons, meta, n)
    max_tokens = meta.get("max_output_tokens_multi_tipi",
                          E.MAX_OUTPUT_TOKENS_MULTI_TIPI)
    t0 = time.time()
    res = generate(prompts, max_tokens) if prompts else []
    parsed = [E.parse_multi_tipi(r["text"], meta["tipi_codes"]) is not None
              for r in res]
    n_parsed = sum(parsed)
    rate = (n_parsed / len(res)) if res else 0.0
    report = {
        "n": len(res),
        "n_parsed": n_parsed,
        "parse_rate": round(rate, 4),
        "min_parse_rate": min_rate,
        "passed": bool(res) and rate >= min_rate,
        "max_output_tokens": max_tokens,
        "seconds": round(time.time() - t0, 2),
        "examples": [r["text"] for r in res[:3]],
    }
    log("=" * 70)
    log(f"[smoke] multi-target format: {n_parsed}/{len(res)} parsed "
        f"(rate {rate:.3f}, bar {min_rate:.3f}) -> "
        f"{'PASS' if report['passed'] else 'FAIL'}")
    log("=" * 70)
    return report


# ---------------------------------------------------------------------------
# The round loop (pure: generation is injected)
# ---------------------------------------------------------------------------


def run_eig_rounds(persons, meta, generate, pred_sink, score_sink, max_reveals,
                   checkpoints=None, top_n=5, hypotheticals=(1, 3, 5),
                   tiebreak_seed=71, mode=MODE_MULTI, log=print,
                   revealed=None, done_ks=(), start_idx=0):
    """Run the EIG reveal loop. Returns ``(reveal_orders, stats)``.

    ``generate(prompts, max_tokens)`` must return one dict per prompt with
    ``text``/``tokens_in``/``tokens_out``, in order.

    Resume: pass ``revealed`` (a complete, equal-length reveal prefix for every
    person), the set of checkpoints already fully predicted as ``done_ks``, and
    the next free record index. Any checkpoint the prefix has already passed but
    that is not in ``done_ks`` is predicted first, so a job killed between a
    reveal and its checkpoint loses nothing.
    """
    riasec_codes = meta["riasec_codes"]
    tipi_codes = meta["tipi_codes"]
    r_anchors = meta["riasec_anchors"]
    t_anchors = meta["tipi_anchors"]
    checkpoints = set(meta["checkpoints"] if checkpoints is None else checkpoints)
    hypotheticals = tuple(hypotheticals)
    canonical = {code: i for i, code in enumerate(riasec_codes)}
    unit_tokens = (meta.get("max_output_tokens_multi_tipi",
                            E.MAX_OUTPUT_TOKENS_MULTI_TIPI)
                   if mode == MODE_MULTI else meta["max_output_tokens_tipi"])

    check_no_tipi_in_demographics(persons, tipi_codes)

    revealed = revealed if revealed is not None else {p["person_id"]: []
                                                      for p in persons}
    depths = {len(v) for v in revealed.values()}
    if len(depths) != 1:
        raise AssertionError(f"reveal prefixes are not in lockstep: {sorted(depths)}")
    done_ks = set(done_ks)
    stats = {"n_uncertainty_calls": 0, "n_shift_calls": 0,
             "n_prediction_calls": 0, "uncertainty_parse_failures": 0,
             "shift_parse_failures": 0, "reference_parse_failures": 0,
             "n_score_ties": 0, "tokens_in": 0, "tokens_out": 0}
    idx = start_idx

    def predict_at(k):
        """One checkpoint batch: 10 single-target TIPI predictions per person.

        Single target on purpose -- this is the outcome the ladder is measured
        on, so it must be the same call every other arm makes.
        """
        nonlocal idx
        prompts, keys = [], []
        for person in persons:
            pid = person["person_id"]
            pairs = _pairs_for(person, revealed[pid][:k])
            for code in tipi_codes:
                prompts.append(R.tipi_prompt(person["demographics_block"], pairs,
                                             r_anchors,
                                             person["tipi_texts"][code], t_anchors))
                keys.append((pid, code))
        t0 = time.time()
        res = generate(prompts, meta["max_output_tokens_tipi"])
        stats["n_prediction_calls"] += len(res)
        rows = []
        for (pid, code), r, prompt in zip(keys, res, prompts):
            stats["tokens_in"] += r["tokens_in"]
            stats["tokens_out"] += r["tokens_out"]
            rows.append({"idx": idx, "kind": "predict", "person_id": pid, "k": k,
                         "item": code, "prompt": prompt, "text": r["text"],
                         "tokens_in": r["tokens_in"],
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
        # ---- 1. self-uncertainty over every remaining candidate ------------
        prompts, keys = [], []
        for person in persons:
            pid = person["person_id"]
            done = set(revealed[pid])
            pairs = _pairs_for(person, revealed[pid])
            for code in riasec_codes:  # canonical order -> stable shortlist
                if code in done:
                    continue
                prompts.append(R.interest_prompt(
                    person["demographics_block"], pairs, r_anchors,
                    person["interests"][code]["text"]))
                keys.append((pid, code))

        t0 = time.time()
        res = generate(prompts, meta["max_output_tokens_interest"])
        unc_s = time.time() - t0
        n_unc = len(res)
        stats["n_uncertainty_calls"] += n_unc

        entropies = {p["person_id"]: [] for p in persons}
        answer_dists = {}
        for (pid, code), r in zip(keys, res):
            dist = R.parse_interest_distribution(r["text"])
            stats["uncertainty_parse_failures"] += int(dist is None)
            stats["tokens_in"] += r["tokens_in"]
            stats["tokens_out"] += r["tokens_out"]
            entropies[pid].append((code, R.entropy(dist)))
            answer_dists[(pid, code)] = dist

        # ---- 2. shortlist the most uncertain items -------------------------
        shortlist = {}
        for person in persons:
            pid = person["person_id"]
            shortlist[pid] = R.rank_candidates(
                entropies[pid], top_n, tiebreak="random", seed=tiebreak_seed,
                person_id=pid, round_index=rnd)

        # ---- 3. reference + hypothetical belief calls, one batch ------------
        prompts, units = [], []
        for person in persons:
            pid = person["person_id"]
            pairs = _pairs_for(person, revealed[pid])
            ps = unit_prompts(person, meta, pairs, None, None, mode)
            units.append((pid, None, None, len(ps)))
            prompts.extend(ps)
            for code, _ent, _nt in shortlist[pid]:
                for answer in hypotheticals:
                    ps = unit_prompts(person, meta, pairs, code, answer, mode)
                    units.append((pid, code, answer, len(ps)))
                    prompts.extend(ps)

        t1 = time.time()
        res = generate(prompts, unit_tokens)
        shift_s = time.time() - t1
        stats["n_shift_calls"] += len(res)

        beliefs = {}
        pos = 0
        for pid, code, answer, n_prompts in units:
            chunk = res[pos:pos + n_prompts]
            pos += n_prompts
            for r in chunk:
                stats["tokens_in"] += r["tokens_in"]
                stats["tokens_out"] += r["tokens_out"]
            beliefs[(pid, code, answer)] = unit_distributions(
                [r["text"] for r in chunk], tipi_codes, mode)

        # ---- 4-6. score, reveal the biggest expected movement ---------------
        rows = []
        for person in persons:
            pid = person["person_id"]
            p0 = beliefs[(pid, None, None)]
            ref_failed = p0 is None
            stats["reference_parse_failures"] += int(ref_failed)

            cand_rows = []
            for rank, (code, ent, _nt) in enumerate(shortlist[pid]):
                shifts, fails = {}, 0
                for answer in hypotheticals:
                    dist = beliefs[(pid, code, answer)]
                    if dist is None:
                        fails += 1
                        stats["shift_parse_failures"] += 1
                    shifts[answer] = E.mean_tv_shift(dist, p0, tipi_codes)
                weights = E.hypothetical_weights(answer_dists[(pid, code)],
                                                 hypotheticals)
                score = E.info_gain_score(shifts, weights)
                cand_rows.append({
                    "person_id": pid, "round": rnd, "item": code, "rank": rank,
                    "entropy": ent,
                    "tv_shift": {str(a): shifts[a] for a in hypotheticals},
                    "weights": {str(a): weights[a] for a in hypotheticals},
                    "score": score, "selected": False, "parse_failures": fails,
                    "reference_parse_failure": ref_failed, "n_tied": 1,
                })

            scored = sorted(((r["item"], r["score"]) for r in cand_rows),
                            key=lambda t: canonical[t[0]])
            best, _best_score, n_tied = R.select_best(
                scored, tiebreak="random", seed=tiebreak_seed, person_id=pid,
                round_index=rnd)
            stats["n_score_ties"] += int(n_tied > 1)
            for row in cand_rows:
                row["n_tied"] = n_tied
                row["selected"] = row["item"] == best
            rows.extend(cand_rows)
            revealed[pid].append(best)

        score_sink(rows)

        k = rnd + 1
        log(f"[round {k}/{max_reveals}] {n_unc} uncertainty calls in "
            f"{unc_s:.1f}s, {len(res)} belief calls in {shift_s:.1f}s")

        # ---- 7. checkpoint predictions --------------------------------------
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


def _read_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path) as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return None


def load_resume_state(outdir, person_ids, n_tipi):
    """Recover a clean, lockstep state from a previous job's partial output.

    Only *complete* units survive: a reveal round counts only if every person
    selected an item in it, and a checkpoint counts only if all
    ``n_persons * n_tipi`` predictions are present. Partial rounds and partial
    checkpoints are dropped and redone, so nothing is double-counted and nothing
    is silently missing.

    Returns ``(revealed, done_ks, next_idx, score_rows, pred_rows)`` where the
    two row lists are exactly what should be rewritten before appending.
    """
    score_rows = _read_jsonl(os.path.join(outdir, "eig_scores.jsonl"))
    pred_rows = _read_jsonl(os.path.join(outdir, "completions_eig.jsonl"))
    ids = list(person_ids)
    if not score_rows:
        return {pid: [] for pid in ids}, set(), 0, [], []

    selected = {}
    for row in score_rows:
        if row.get("selected"):
            selected[(row["person_id"], row["round"])] = row["item"]
    depth = 0
    while all((pid, depth) in selected for pid in ids):
        depth += 1
    revealed = {pid: [selected[(pid, r)] for r in range(depth)] for pid in ids}
    score_rows = [r for r in score_rows if r["round"] < depth]

    by_k = {}
    for row in pred_rows:
        by_k.setdefault(row["k"], []).append(row)
    done_ks = {k for k, rows in by_k.items()
               if len(rows) == len(ids) * n_tipi and k <= depth}
    pred_rows = [r for r in pred_rows if r["k"] in done_ks]
    next_idx = max((r["idx"] for r in pred_rows), default=-1) + 1
    return revealed, done_ks, next_idx, score_rows, pred_rows


def main():
    args = build_args()
    with open(args.pack) as fh:
        pack = json.load(fh)
    meta = pack["meta"]
    persons_all = pack["persons"]
    if args.limit_persons:
        persons_all = persons_all[: args.limit_persons]
    max_reveals = args.limit_rounds or args.max_reveals
    checkpoints = [k for k in _int_list(args.checkpoints) if 1 <= k <= max_reveals]
    hypotheticals = tuple(_int_list(args.hypotheticals))
    n_tipi = len(meta["tipi_codes"])
    os.makedirs(os.path.abspath(args.outdir), exist_ok=True)

    # A previous leg of this job already picked a mode. Stick to it: flipping
    # mode mid-run would change the person list and break the lockstep prefix.
    prior = _read_json(os.path.join(args.outdir, "node_summary.json")) or {}
    prior_mode = prior.get("mode")
    persons = (persons_all[: args.fallback_persons]
               if prior_mode == MODE_FALLBACK else persons_all)

    ids = [p["person_id"] for p in persons]
    revealed, done_ks, next_idx, score_rows, pred_rows = load_resume_state(
        args.outdir, ids, n_tipi)
    resumed = bool(score_rows) or bool(pred_rows)
    if resumed:
        print(f"[resume] mode={prior_mode} {len(revealed[ids[0]])} reveal rounds "
              f"intact, checkpoints done: {sorted(done_ks)}, next idx {next_idx}",
              flush=True)
    # Nothing left to do -> exit BEFORE paying a ~3 min engine init. This is
    # what makes a chain of short jobs cheap: the tail jobs cost seconds.
    if (len(revealed[ids[0]]) >= max_reveals and set(checkpoints) <= done_ks):
        print("[done] already complete; no engine init needed.", flush=True)
        with open(os.path.join(args.outdir, "reveal_orders.json"), "w") as fh:
            json.dump({str(k): v for k, v in revealed.items()}, fh, indent=2)
        sys.stdout.flush()
        os._exit(0)

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.model_dir)
    llm, init_s = make_engine(args)
    generate = make_generate(llm, tok, args)

    # ---- format smoke test, then commit to a mode --------------------------
    smoke = run_smoke_test(persons_all, meta, generate, args.smoke_n,
                           args.min_parse_rate)
    with open(os.path.join(args.outdir, "multi_target_smoke.json"), "w") as fh:
        json.dump(smoke, fh, indent=2)

    if resumed and prior_mode:
        mode = prior_mode
        reason = f"resumed a leg already running in {prior_mode}"
    elif smoke["passed"]:
        mode = MODE_MULTI
        reason = (f"multi-target parse rate {smoke['parse_rate']:.3f} >= "
                  f"{args.min_parse_rate:.3f}")
    else:
        mode = MODE_FALLBACK
        reason = (f"multi-target parse rate {smoke['parse_rate']:.3f} < "
                  f"{args.min_parse_rate:.3f}; 10 single-target calls per "
                  f"hypothetical instead, person budget cut to "
                  f"{args.fallback_persons}")
        # The person set just changed, so any recovered prefix is no longer a
        # lockstep prefix of THIS run. Throw it away and start clean rather
        # than mix two person sets in one ladder.
        persons = persons_all[: args.fallback_persons]
        ids = [p["person_id"] for p in persons]
        revealed, done_ks, next_idx, score_rows, pred_rows = \
            {pid: [] for pid in ids}, set(), 0, [], []
        resumed = False
    print(f"[mode] {mode}: {reason}", flush=True)

    # Record the mode before generating anything: if this leg is killed, the
    # next one reads it back and stays in the same mode instead of re-deciding
    # off a fresh smoke test and changing the person set mid-ladder.
    with open(os.path.join(args.outdir, "node_summary.json"), "w") as fh:
        json.dump({"arm": "eig", "mode": mode, "mode_reason": reason,
                   "status": "running", "n_persons": len(persons),
                   "smoke_parse_rate": smoke["parse_rate"]}, fh, indent=2)

    # Rewrite the kept rows, then append from there.
    pred_sink = Sink(os.path.join(args.outdir, "completions_eig.jsonl"))
    score_sink = Sink(os.path.join(args.outdir, "eig_scores.jsonl"))
    if pred_rows:
        pred_sink(pred_rows)
    if score_rows:
        score_sink(score_rows)
    t_start = time.time()
    try:
        revealed, stats = run_eig_rounds(
            persons, meta, generate, pred_sink, score_sink, max_reveals,
            checkpoints=checkpoints, top_n=args.top_n,
            hypotheticals=hypotheticals, tiebreak_seed=args.tiebreak_seed,
            mode=mode, revealed=revealed, done_ks=done_ks, start_idx=next_idx)
    finally:
        pred_sink.close()
        score_sink.close()
    wall = time.time() - t_start

    with open(os.path.join(args.outdir, "reveal_orders.json"), "w") as fh:
        json.dump({str(k): v for k, v in revealed.items()}, fh, indent=2)
    summary = {
        "arm": "eig", "mode": mode, "mode_reason": reason, "status": "complete",
        "smoke_parse_rate": smoke["parse_rate"], "smoke_n": smoke["n"],
        "min_parse_rate": args.min_parse_rate,
        "model_dir": args.model_dir, "tp": args.tp,
        "max_model_len": args.max_model_len, "gpu_mem_util": args.gpu_mem_util,
        "temperature": args.temperature, "seed": args.seed,
        "tiebreak_seed": args.tiebreak_seed, "top_n": args.top_n,
        "hypotheticals": list(hypotheticals), "checkpoints": checkpoints,
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
                    ("n_uncertainty_calls", "n_shift_calls",
                     "n_prediction_calls", "uncertainty_parse_failures",
                     "shift_parse_failures", "reference_parse_failures",
                     "n_score_ties")})
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
