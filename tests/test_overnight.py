"""Tests for the overnight Stage-1E batch's new mechanisms (EXP1..EXP5).

Everything here runs offline. The pieces under test are the ones that would
silently corrupt a multi-node-hour job if they were wrong:

* the seeded random tie-break (EXP1) -- reproducible, unbiased, never picks a
  parse failure;
* the EV-variance scorer (EXP1b) -- a different notion of "uncertain";
* the finer 0.05 elicitation grid (EXP1c) -- a genuine one-factor change;
* nearest-neighbour imposter pairing (EXP5) -- deterministic, never self;
* permutation extension (EXP4) -- k>20 must EXTEND the pilot's prefix, not
  replace it, or the reused pilot completions would silently mismatch.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from doppler import adaptive as A
from doppler import adaptive_render as R
from doppler.data import RIASEC_ITEMS, TIPI_ITEMS

_ROOT = Path(__file__).resolve().parents[1]


def _load_driver():
    path = _ROOT / "experiments" / "adaptive_node_driver.py"
    spec = importlib.util.spec_from_file_location("adaptive_node_driver", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["adaptive_node_driver"] = mod
    spec.loader.exec_module(mod)
    return mod


DRIVER = _load_driver()


# ---------------------------------------------------------------------------
# EXP1: seeded random tie-break
# ---------------------------------------------------------------------------


def test_tiebreak_index_is_deterministic_across_processes():
    """Must not depend on hash randomization -- it is seeded from SHA-256."""
    a = [R.tiebreak_index(71, pid, rnd, 7)
         for pid in (1, 2, 12345) for rnd in range(5)]
    b = [R.tiebreak_index(71, pid, rnd, 7)
         for pid in (1, 2, 12345) for rnd in range(5)]
    assert a == b
    assert all(0 <= x < 7 for x in a)
    # Known-value lock: if the derivation ever changes, this fails loudly.
    assert R.tiebreak_index(71, 1000, 0, 5) == R.tiebreak_index(71, 1000, 0, 5)


def test_tiebreak_index_varies_with_seed_person_and_round():
    base = R.tiebreak_index(71, 1000, 0, 48)
    assert any(R.tiebreak_index(s, 1000, 0, 48) != base for s in range(72, 90))
    assert any(R.tiebreak_index(71, p, 0, 48) != base for p in range(1001, 1020))
    assert any(R.tiebreak_index(71, 1000, r, 48) != base for r in range(1, 20))


def test_tiebreak_index_is_roughly_uniform():
    """A biased tie-break is exactly the flaw EXP1 exists to remove."""
    counts = [0] * 5
    for pid in range(5000):
        counts[R.tiebreak_index(71, pid, 0, 5)] += 1
    assert min(counts) > 800 and max(counts) < 1200


def test_select_best_index_mode_reproduces_lowest_index_rule():
    scored = [("R1", 1.0), ("R2", 1.0), ("R3", 0.5)]
    code, score, n_tied = R.select_best(scored, "index")
    assert (code, score, n_tied) == ("R1", 1.0, 2)


def test_select_best_random_mode_stays_within_the_tied_set():
    scored = [("R1", 1.0), ("R2", 1.0), ("R3", 1.0), ("R4", 0.2)]
    for pid in range(200):
        code, score, n_tied = R.select_best(scored, "random", 71, pid, 0)
        assert code in {"R1", "R2", "R3"}
        assert score == 1.0 and n_tied == 3


def test_select_best_random_mode_actually_moves_off_the_first_item():
    scored = [("R1", 1.0), ("R2", 1.0), ("R3", 1.0)]
    picks = {R.select_best(scored, "random", 71, pid, 0)[0] for pid in range(50)}
    assert len(picks) == 3  # all three reachable -> not a disguised index rule


def test_select_best_is_unaffected_by_tiebreak_when_there_is_no_tie():
    scored = [("R1", 0.1), ("R2", 0.9), ("R3", 0.5)]
    for mode in ("index", "random"):
        assert R.select_best(scored, mode, 71, 5, 0) == ("R2", 0.9, 1)


def test_select_best_rejects_unknown_tiebreak_and_empty_input():
    with pytest.raises(ValueError):
        R.select_best([("R1", 1.0), ("R2", 1.0)], "coin-flip")
    with pytest.raises(ValueError):
        R.select_best([], "index")


def test_rank_candidates_returns_top_n_and_leads_with_the_greedy_pick():
    scored = [(c, float(i % 7)) for i, c in enumerate(RIASEC_ITEMS)]
    top = R.rank_candidates(scored, 5, "random", 71, 1000, 0)
    assert len(top) == 5
    assert len({c for c, _, _ in top}) == 5
    assert [s for _, s, _ in top] == sorted((s for _, s, _ in top), reverse=True)
    # first shortlisted == what pure greedy self-uncertainty would reveal
    assert top[0][0] == R.select_best(scored, "random", 71, 1000, 0)[0]


# ---------------------------------------------------------------------------
# EXP1b: the EV-variance scorer
# ---------------------------------------------------------------------------


def _dist(*ps):
    return R.parse_interest_distribution(
        " ".join(f"{i}:{p}" for i, p in enumerate(ps, start=1)))


def test_ev_variance_matches_hand_computation():
    d = _dist(0.5, 0, 0, 0, 0.5)  # mass at 1 and 5 -> mean 3, variance 4
    assert R.ev_variance(d) == pytest.approx(4.0)
    assert R.expected_value(d) == pytest.approx(3.0)
    assert R.ev_variance(_dist(0, 0, 1, 0, 0)) == pytest.approx(0.0)


def test_ev_variance_separates_cases_entropy_cannot():
    """Two answers, same entropy, very different spread."""
    far = _dist(0.5, 0, 0, 0, 0.5)     # 1 vs 5
    near = _dist(0, 0.5, 0.5, 0, 0)    # 2 vs 3
    assert R.entropy(far) == pytest.approx(R.entropy(near))
    assert R.ev_variance(far) > R.ev_variance(near)


def test_ev_variance_failure_sentinel_is_below_every_real_score():
    assert R.ev_variance(None) == R.PARSE_FAILURE_ENTROPY
    assert R.ev_variance(None) < R.ev_variance(_dist(0, 0, 1, 0, 0))


def test_scorer_registry_covers_both_and_shares_the_sentinel():
    assert set(R.SCORERS) == {"entropy", "ev_variance"}
    for fn in R.SCORERS.values():
        assert fn(None) == R.PARSE_FAILURE_ENTROPY


# ---------------------------------------------------------------------------
# EXP1c: the finer elicitation grid
# ---------------------------------------------------------------------------


def test_fine_grid_is_a_one_factor_change():
    """Only the 0.05 clause differs -- the worked example is identical."""
    std, fine = R.INTEREST_INSTRUCTION, R.INTEREST_INSTRUCTION_FINE
    assert std != fine
    assert "multiples of 0.05" in fine
    assert "multiples of 0.05" not in std
    example = "1:0.20 2:0.20 3:0.20 4:0.20 5:0.20"
    assert std.endswith(example) and fine.endswith(example)


def test_fine_grid_changes_only_the_task_block_of_the_prompt():
    demo = "MY PROFILE\nI am 30."
    pairs = [("activity one", 3)]
    a = R.interest_prompt(demo, pairs, "1=Dislike, 5=Enjoy", "activity two")
    b = R.interest_prompt(demo, pairs, "1=Dislike, 5=Enjoy", "activity two",
                          "fine")
    assert a != b
    assert a.split("\n\nYOUR TASK")[0] == b.split("\n\nYOUR TASK")[0]


def test_unknown_grid_is_rejected():
    with pytest.raises(ValueError):
        R.interest_task("activity", "1=Dislike, 5=Enjoy", "coarse")


# ---------------------------------------------------------------------------
# EXP4: permutation extension must agree with the pilot's prefixes
# ---------------------------------------------------------------------------


def test_random_order_covers_all_48_items():
    order = A.random_order(4242)
    assert len(order) == len(RIASEC_ITEMS) == 48
    assert sorted(order) == sorted(RIASEC_ITEMS)


def test_extended_checkpoints_extend_the_pilot_prefix_exactly():
    """k=28/36/48 must be a continuation of the pilot's k=20 prefix.

    If this ever failed, reusing the pilot's k in {8,12,16,20} completions
    alongside newly bought k in {28,36,48} would be comparing two different
    interviews.
    """
    for pid in (101, 5000, 123456):
        order = A.random_order(pid)
        for k_small in A.CHECKPOINTS:
            for k_big in A.CHECKPOINTS_EXT:
                if k_big >= k_small:
                    assert order[:k_big][:k_small] == order[:k_small]


def test_checkpoint_grids_are_consistent_with_each_other():
    assert set(A.CHECKPOINTS) <= set(A.CHECKPOINTS_EXT)
    assert set(A.CHECKPOINTS_K20) <= set(A.CHECKPOINTS_EXT)
    assert set(A.CHECKPOINTS_IMPOSTER) <= set(A.CHECKPOINTS_EXT)
    assert max(A.CHECKPOINTS_K20) == 20
    assert max(A.CHECKPOINTS_EXT) == 48 == len(RIASEC_ITEMS)
    # the random arm must buy exactly what the pilot did not already have
    assert set(A.CHECKPOINTS_RANDOM_NEW) == (set(A.CHECKPOINTS_EXT)
                                             - set(A.CHECKPOINTS))
    assert set(A.CHECKPOINTS_RANDOM_NEW).isdisjoint(A.CHECKPOINTS)


# ---------------------------------------------------------------------------
# EXP5: nearest-neighbour imposter
# ---------------------------------------------------------------------------


def _interest_df(n=40, seed=7):
    rng = np.random.default_rng(seed)
    data = {"person_id": np.arange(1000, 1000 + n, dtype=np.int64)}
    items = rng.integers(1, 6, size=(n, len(RIASEC_ITEMS)))
    for j, c in enumerate(RIASEC_ITEMS):
        data[c] = items[:, j]
    return pd.DataFrame(data)


def test_nn_imposter_never_self_pairs_and_is_deterministic():
    df = _interest_df()
    ids = df["person_id"].tolist()
    a = A.nn_imposter_pairs(df, ids)
    b = A.nn_imposter_pairs(df, ids)
    assert a["pairs"] == b["pairs"]
    assert a["similarity"] == b["similarity"]
    assert set(a["pairs"]) == set(ids)
    assert all(k != v for k, v in a["pairs"].items())
    assert all(v in set(ids) for v in a["pairs"].values())


def test_nn_imposter_finds_a_planted_twin():
    """A near-duplicate row must be chosen as that person's donor."""
    df = _interest_df(n=20)
    ids = df["person_id"].tolist()
    twin = df.iloc[0].copy()
    twin["person_id"] = 9999
    df = pd.concat([df, twin.to_frame().T], ignore_index=True)
    df["person_id"] = df["person_id"].astype(np.int64)
    ids = ids + [9999]

    out = A.nn_imposter_pairs(df, ids)
    assert out["pairs"][9999] == ids[0]
    assert out["pairs"][ids[0]] == 9999
    assert out["similarity"][9999] == pytest.approx(1.0)


def test_nn_imposter_is_more_similar_than_the_random_derangement():
    """The whole point of EXP5: the NN donor is a harder imposter."""
    df = _interest_df(n=60)
    ids = df["person_id"].tolist()
    nn = A.nn_imposter_pairs(df, ids)
    rand = A.imposter_pairs(ids)

    by_id = df.set_index("person_id")
    vecs = {pid: by_id.loc[pid, list(RIASEC_ITEMS)].to_numpy(dtype=float)
            for pid in ids}

    def cos(a, b):
        return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

    nn_mean = np.mean([cos(vecs[p], vecs[d]) for p, d in nn["pairs"].items()])
    rd_mean = np.mean([cos(vecs[p], vecs[d]) for p, d in rand.items()])
    assert nn_mean > rd_mean
    assert nn["mean_similarity"] == pytest.approx(nn_mean)


def test_nn_imposter_rejects_singletons():
    df = _interest_df(n=1)
    with pytest.raises(ValueError):
        A.nn_imposter_pairs(df, df["person_id"].tolist())


# ---------------------------------------------------------------------------
# Overnight static tasks (EXP2 + EXP4 + EXP5 in one job)
# ---------------------------------------------------------------------------


def _mini_pack(record_factory, full_demographics, n=6):
    from doppler.prompts import _demographics_block

    pack = []
    for i in range(n):
        rec = record_factory(2000 + i, dict(full_demographics, age=20 + i))
        for j, c in enumerate(RIASEC_ITEMS):
            rec["interests"][c]["answer"] = ((i + j) % 5) + 1
        for j, c in enumerate(TIPI_ITEMS):
            rec["tipi"][c]["answer"] = ((i + j) % 7) + 1
        pack.append({
            "person_id": rec["person_id"],
            "demographics_block": _demographics_block(rec["demographics"]),
            "interests": {c: dict(rec["interests"][c]) for c in RIASEC_ITEMS},
            "tipi": {c: dict(rec["tipi"][c]) for c in TIPI_ITEMS},
        })
    return pack


@pytest.fixture
def overnight(record_factory, full_demographics, fake_codebook):
    pack = _mini_pack(record_factory, full_demographics)
    meta = A.static_meta(pack, fake_codebook)
    ids = [p["person_id"] for p in pack]
    donors = {pid: ids[(i + 2) % len(ids)] for i, pid in enumerate(ids)}
    deriv_order = list(RIASEC_ITEMS)  # a full 48-item order
    return pack, meta, deriv_order, donors


def test_overnight_static_tasks_have_the_right_shape(overnight):
    pack, meta, deriv, donors = overnight
    tasks = A.build_overnight_static_tasks(pack, meta, deriv, donors)
    n = len(pack)
    expected = n * len(TIPI_ITEMS) * (
        len(A.CHECKPOINTS_EXT) + len(A.CHECKPOINTS_RANDOM_NEW)
        + len(A.CHECKPOINTS_IMPOSTER))
    assert len(tasks) == expected
    assert [t["idx"] for t in tasks] == list(range(len(tasks)))
    assert A.overnight_static_counts(n)["TOTAL"] == expected
    assert {t["policy"] for t in tasks} == set(A.OVERNIGHT_STATIC_POLICIES)


def test_overnight_static_tasks_never_leak_tipi(overnight):
    pack, meta, deriv, donors = overnight
    tasks = A.build_overnight_static_tasks(pack, meta, deriv, donors)
    by_id = {p["person_id"]: p for p in pack}
    tipi_texts = [meta["tipi_texts"][c] for c in TIPI_ITEMS]
    for task in tasks:
        head = task["prompt"].split("\n\nYOUR TASK")[0]
        for text in tipi_texts:
            assert text not in head
        assert "I see myself as" not in head
        true = by_id[task["person_id"]]["tipi"][task["item"]]["answer"]
        assert f"{meta['tipi_texts'][task['item']]}: {true}" not in task["prompt"]


def test_overnight_static_arms_use_the_right_source_and_order(overnight):
    pack, meta, deriv, donors = overnight
    tasks = A.build_overnight_static_tasks(pack, meta, deriv, donors)
    by_id = {p["person_id"]: p for p in pack}
    for task in tasks:
        pid, k = task["person_id"], task["k"]
        if task["policy"] == "fixed_deriv":
            codes, source = deriv[:k], by_id[pid]
        elif task["policy"] == "random_ext":
            codes, source = A.random_order(pid)[:k], by_id[pid]
        else:
            codes, source = A.random_order(pid)[:k], by_id[task["donor_id"]]
            assert task["donor_id"] != pid
        lines = [ln for ln in task["prompt"].splitlines() if ln.startswith("- ")]
        assert len(lines) == k
        for line, code in zip(lines, codes):
            entry = source["interests"][code]
            assert line == f"- {entry['text']}: {entry['answer']}"


def test_overnight_random_ext_buys_no_checkpoint_the_pilot_already_has(overnight):
    pack, meta, deriv, donors = overnight
    tasks = A.build_overnight_static_tasks(pack, meta, deriv, donors)
    ks = {t["k"] for t in tasks if t["policy"] == "random_ext"}
    assert ks == set(A.CHECKPOINTS_RANDOM_NEW)
    assert ks.isdisjoint(A.CHECKPOINTS)


def test_overnight_static_rejects_a_short_or_repeating_order(overnight):
    pack, meta, _, donors = overnight
    with pytest.raises(ValueError):
        A.build_overnight_static_tasks(pack, meta, list(RIASEC_ITEMS[:20]),
                                       donors)
    with pytest.raises(ValueError):
        A.build_overnight_static_tasks(pack, meta,
                                       list(RIASEC_ITEMS[:47]) + ["R1"], donors)


# ---------------------------------------------------------------------------
# Projections and the budget cap
# ---------------------------------------------------------------------------


def test_overnight_projection_respects_both_caps():
    proj = A.project_overnight()
    assert set(proj["jobs"]) == {
        "exp1a_entropy_random_k48", "exp1b_evvariance_k20",
        "exp1c_finegrid_k20", "exp245_static", "exp3_eig_ladder"}
    for name, job in proj["jobs"].items():
        assert 0 < job["projected_node_hours"] <= proj["per_job_cap"], name
    assert proj["total_projected_node_hours"] <= proj["batch_cap"]
    assert proj["total_projected_node_hours"] == pytest.approx(
        sum(j["projected_node_hours"] for j in proj["jobs"].values()), abs=1e-3)


def test_exp3_stays_inside_its_own_three_hour_cap():
    assert A.project_overnight()["jobs"]["exp3_eig_ladder"][
        "projected_node_hours"] <= 3.0


def test_adaptive_call_counts_match_the_arithmetic():
    unc, pred = A.adaptive_call_counts(150, 20, A.CHECKPOINTS)
    assert unc == 150 * 770        # 48+47+...+29
    assert pred == 150 * 7 * 10
    unc48, pred48 = A.adaptive_call_counts(150, 48, A.CHECKPOINTS_EXT)
    assert unc48 == 150 * (48 * 49 // 2)
    assert pred48 == 150 * 12 * 10


# ---------------------------------------------------------------------------
# The driver loop under the new policy knobs
# ---------------------------------------------------------------------------


class TieStub:
    """Every candidate returns the SAME flat distribution -> a 48-way tie.

    This is the worst case the pilot's diagnostic warned about, and it is
    exactly where the tie-break decides everything.
    """

    def __call__(self, prompts, max_tokens):
        out = []
        for p in prompts:
            if "I see myself as" in p:
                out.append({"text": "1:0.1 2:0.1 3:0.1 4:0.3 5:0.2 6:0.1 7:0.1",
                            "tokens_in": 100, "tokens_out": 40})
            else:
                out.append({"text": "1:0.2 2:0.2 3:0.2 4:0.2 5:0.2",
                            "tokens_in": 100, "tokens_out": 30})
        return out


class SpreadStub:
    """Interest answers keyed to item identity, with a controllable scorer.

    Mass sits on answers 1 and 5 for early items (high variance, moderate
    entropy) and is flat for late items (max entropy, lower variance), so
    entropy and ev_variance pick DIFFERENT items -- which is the point of
    EXP1(b).
    """

    def __init__(self, item_texts):
        self.rank = {text: i for i, text in enumerate(item_texts)}

    def __call__(self, prompts, max_tokens):
        out = []
        for p in prompts:
            if "I see myself as" in p:
                out.append({"text": "1:0.1 2:0.1 3:0.1 4:0.3 5:0.2 6:0.1 7:0.1",
                            "tokens_in": 100, "tokens_out": 40})
                continue
            asked = p.split('activity: "')[1].split('" on this scale')[0]
            if self.rank[asked] == 0:
                text = "1:0.5 2:0.0 3:0.0 4:0.0 5:0.5"   # var 4.0, ent 0.69
            else:
                text = "1:0.2 2:0.2 3:0.2 4:0.2 5:0.2"   # var 2.0, ent 1.61
            out.append({"text": text, "tokens_in": 100, "tokens_out": 30})
        return out


@pytest.fixture
def node_inputs(record_factory, full_demographics, fake_codebook):
    pack = _mini_pack(record_factory, full_demographics)
    node = A.node_pack(pack, fake_codebook)
    return pack, node["persons"], node["meta"]


def _run(persons, meta, gen, rounds, **kw):
    preds, uncs = [], []
    revealed, stats = DRIVER.run_rounds(persons, meta, gen, preds.extend,
                                        uncs.extend, rounds,
                                        log=lambda *_: None, **kw)
    return revealed, stats, preds, uncs


def test_index_tiebreak_still_reproduces_the_pilot_behaviour(node_inputs):
    _, persons, meta = node_inputs
    revealed, stats, _, _ = _run(persons, meta, TieStub(), 3, tiebreak="index")
    for order in revealed.values():
        assert order == list(RIASEC_ITEMS[:3])
    assert stats["n_decisions_with_tie_at_top"] == stats["n_decisions"]


def test_random_tiebreak_is_reproducible_and_breaks_the_index_pattern(node_inputs):
    _, persons, meta = node_inputs
    kw = dict(tiebreak="random", tiebreak_seed=71)
    first, stats, _, _ = _run(persons, meta, TieStub(), 3, **kw)
    second, _, _, _ = _run(persons, meta, TieStub(), 3, **kw)
    assert first == second                       # deterministic given the seed
    assert any(o != list(RIASEC_ITEMS[:3]) for o in first.values())
    assert all(len(set(o)) == 3 for o in first.values())
    assert stats["max_tied_at_top"] == len(RIASEC_ITEMS)


def test_random_tiebreak_seed_actually_matters(node_inputs):
    _, persons, meta = node_inputs
    a, _, _, _ = _run(persons, meta, TieStub(), 3, tiebreak="random",
                      tiebreak_seed=71)
    b, _, _, _ = _run(persons, meta, TieStub(), 3, tiebreak="random",
                      tiebreak_seed=72)
    assert a != b


def test_tie_statistics_are_recorded_for_the_report(node_inputs):
    _, persons, meta = node_inputs
    _, stats, _, uncs = _run(persons, meta, TieStub(), 2, tiebreak="random")
    assert stats["n_decisions"] == len(persons) * 2
    assert stats["sum_tied_at_top"] > 0
    assert all("n_tied_at_top" in row for row in uncs)
    assert all(row["scorer"] == "entropy" for row in uncs)
    assert all("score" in row for row in uncs)


def test_ev_variance_scorer_picks_a_different_item_than_entropy(node_inputs):
    _, persons, meta = node_inputs
    texts = [persons[0]["interests"][c]["text"] for c in RIASEC_ITEMS]
    ent, _, _, _ = _run(persons, meta, SpreadStub(texts), 1, scorer="entropy",
                        tiebreak="index")
    var, _, _, uncs = _run(persons, meta, SpreadStub(texts), 1,
                           scorer="ev_variance", tiebreak="index")
    # entropy prefers the flat items; variance prefers the 1-vs-5 split
    for order in var.values():
        assert order == [RIASEC_ITEMS[0]]
    for order in ent.values():
        assert order != [RIASEC_ITEMS[0]]
    assert all(row["scorer"] == "ev_variance" for row in uncs)


def test_fine_grid_reaches_every_uncertainty_prompt(node_inputs):
    _, persons, meta = node_inputs
    seen = []

    def gen(prompts, max_tokens):
        seen.extend(prompts)
        return TieStub()(prompts, max_tokens)

    _run(persons, meta, gen, 1, grid="fine")
    asked = [p for p in seen if "I see myself as" not in p]
    assert asked
    assert all("multiples of 0.05" in p for p in asked)


def test_checkpoint_override_controls_when_predictions_fire(node_inputs):
    _, persons, meta = node_inputs
    _, stats, preds, _ = _run(persons, meta, TieStub(), 5,
                              checkpoints=[3, 5], tiebreak="random")
    assert sorted({r["k"] for r in preds}) == [3, 5]
    assert stats["n_prediction_calls"] == len(persons) * 2 * len(TIPI_ITEMS)


def test_parse_checkpoints_helper():
    assert DRIVER.parse_checkpoints("1,2,3,4,5,8,12,16,20,28,36,48") == \
        list(A.CHECKPOINTS_EXT)
    assert DRIVER.parse_checkpoints(" 4 , 2 ,4 ") == [2, 4]
    assert DRIVER.parse_checkpoints("") is None
    with pytest.raises(ValueError):
        DRIVER.parse_checkpoints("0,3")


def test_parse_failures_still_lose_under_the_random_tiebreak(node_inputs):
    """A broken answer must not be rescued by winning a coin flip."""
    _, persons, meta = node_inputs
    broken = persons[0]["interests"][RIASEC_ITEMS[0]]["text"]

    def gen(prompts, max_tokens):
        out = TieStub()(prompts, max_tokens)
        for i, p in enumerate(prompts):
            if 'activity: "' in p and broken in p.split("YOUR TASK")[1]:
                out[i] = {"text": "I cannot help with that",
                          "tokens_in": 10, "tokens_out": 5}
        return out

    revealed, stats, _, _ = _run(persons, meta, gen, 2, tiebreak="random")
    assert stats["uncertainty_parse_failures"] > 0
    for order in revealed.values():
        assert RIASEC_ITEMS[0] not in order


def test_scorer_and_tiebreak_defaults_are_the_pilot_settings(node_inputs):
    """An unchanged call must still reproduce the pilot exactly."""
    _, persons, meta = node_inputs
    a, _, _, _ = _run(persons, meta, TieStub(), 3)
    b, _, _, _ = _run(persons, meta, TieStub(), 3, scorer="entropy",
                      tiebreak="index")
    assert a == b
