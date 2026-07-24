"""Stage-1E adaptive gym tests: leakage guards, split, policies, node loop.

Everything here runs offline. The node driver's round loop is exercised with a
stub generator, so the sequential adaptive policy is fully tested without vLLM.
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
from doppler.gym import PILOT2_N, TOTAL_N, pilot2_ids, pilot_and_gate_ids
from doppler.prompts import (
    INTRO,
    VARIANT_FINAL_INSTRUCTION,
    VARIANT_MAX_OUTPUT_TOKENS,
    build_profile,
    build_prompt,
)
from doppler.scoring import v2_probabilities

_ROOT = Path(__file__).resolve().parents[1]


def _load_driver():
    """Import experiments/adaptive_node_driver.py as a module."""
    path = _ROOT / "experiments" / "adaptive_node_driver.py"
    spec = importlib.util.spec_from_file_location("adaptive_node_driver", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["adaptive_node_driver"] = mod
    spec.loader.exec_module(mod)
    return mod


DRIVER = _load_driver()


# ---------------------------------------------------------------------------
# Renderer parity with the frozen gate prompts
# ---------------------------------------------------------------------------


def test_render_constants_match_prompts_module():
    assert R.INTRO == INTRO
    assert R.TIPI_INSTRUCTION == VARIANT_FINAL_INSTRUCTION["v2"]
    assert R.MAX_OUTPUT_TOKENS_TIPI == VARIANT_MAX_OUTPUT_TOKENS["v2"]


def test_full_reveal_prompt_matches_gate_prompt(synthetic_record, fake_codebook):
    """All 48 items revealed in canonical order == the gate's v2 twin prompt."""
    from doppler.prompts import _demographics_block, _format_anchors

    demo = _demographics_block(synthetic_record["demographics"])
    r_anchors = _format_anchors(fake_codebook.scales["riasec"]["anchors"])
    t_anchors = _format_anchors(fake_codebook.scales["tipi"]["anchors"])
    pairs = [(synthetic_record["interests"][c]["text"],
              synthetic_record["interests"][c]["answer"]) for c in RIASEC_ITEMS]

    for code in TIPI_ITEMS:
        mine = R.tipi_prompt(demo, pairs, r_anchors,
                             fake_codebook.tipi_items[code], t_anchors)
        theirs = build_prompt(
            build_profile(synthetic_record, fake_codebook, True, variant="v2"),
            code, fake_codebook, variant="v2")
        assert mine == theirs


def test_zero_reveal_profile_is_the_baseline_profile(synthetic_record, fake_codebook):
    from doppler.prompts import _demographics_block, _format_anchors

    demo = _demographics_block(synthetic_record["demographics"])
    r_anchors = _format_anchors(fake_codebook.scales["riasec"]["anchors"])
    assert R.profile(demo, [], r_anchors) == build_profile(
        synthetic_record, fake_codebook, False, variant="v2")


# ---------------------------------------------------------------------------
# Split
# ---------------------------------------------------------------------------


@pytest.fixture
def big_df():
    return pd.DataFrame({"person_id": np.arange(5000, dtype=np.int64)})


def test_train_split_size_deterministic_and_disjoint(big_df):
    a = A.train_ids(big_df)
    b = A.train_ids(big_df)
    assert a == b
    assert len(a) == A.TRAIN_N == 150
    assert len(set(a)) == 150

    pilot, gate = pilot_and_gate_ids(big_df)
    p2 = pilot2_ids(big_df)
    assert len(set(pilot) | set(gate)) == TOTAL_N
    assert len(p2) == PILOT2_N
    assert set(a).isdisjoint(pilot)
    assert set(a).isdisjoint(gate)
    assert set(a).isdisjoint(p2)


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


def test_random_order_is_a_seeded_permutation():
    order = A.random_order(1234)
    assert sorted(order) == sorted(RIASEC_ITEMS)
    assert order == A.random_order(1234)
    assert order != A.random_order(1235)


def test_imposter_pairing_never_self_and_is_deterministic():
    ids = list(range(100, 250))
    pairs = A.imposter_pairs(ids)
    assert pairs == A.imposter_pairs(ids)
    assert set(pairs) == set(ids)
    assert set(pairs.values()) == set(ids)  # a bijection
    assert all(k != v for k, v in pairs.items())


def test_imposter_pairing_rejects_singletons():
    with pytest.raises(ValueError):
        A.imposter_pairs([7])


# ---------------------------------------------------------------------------
# Leakage guards
# ---------------------------------------------------------------------------


def _mini_pack(record_factory, full_demographics, codebook, n=6):
    from doppler.prompts import _demographics_block

    pack = []
    for i in range(n):
        rec = record_factory(1000 + i, dict(full_demographics, age=20 + i))
        # vary answers so entropy/regression are not degenerate
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
def mini(record_factory, full_demographics, fake_codebook):
    pack = _mini_pack(record_factory, full_demographics, fake_codebook)
    meta = A.static_meta(pack, fake_codebook)
    return pack, meta, fake_codebook


def test_static_tasks_have_no_tipi_leak_and_right_shape(mini):
    pack, meta, cb = mini
    donors = A.imposter_pairs([p["person_id"] for p in pack])
    fixed = RIASEC_ITEMS[:A.MAX_REVEALS]
    tasks = A.build_static_tasks(pack, meta, fixed, donors)

    n = len(pack)
    expected = n * 10 + 3 * n * len(A.CHECKPOINTS) * 10
    assert len(tasks) == expected
    assert [t["idx"] for t in tasks] == list(range(len(tasks)))

    tipi_texts = [meta["tipi_texts"][c] for c in TIPI_ITEMS]
    for task in tasks:
        head = task["prompt"].split("\n\nYOUR TASK")[0]
        for text in tipi_texts:
            assert text not in head
        assert "I see myself as" not in head
        # the true TIPI answer never appears attached to the questioned item
        by_id = {p["person_id"]: p for p in pack}
        true = by_id[task["person_id"]]["tipi"][task["item"]]["answer"]
        assert f"{meta['tipi_texts'][task['item']]}: {true}" not in task["prompt"]


def test_baseline_tasks_carry_no_interest_content(mini):
    pack, meta, _ = mini
    donors = A.imposter_pairs([p["person_id"] for p in pack])
    tasks = A.build_static_tasks(pack, meta, RIASEC_ITEMS[:20], donors)
    base = [t for t in tasks if t["policy"] == "baseline"]
    assert len(base) == len(pack) * 10
    for task in base:
        assert task["k"] == 0
        assert R.INTERESTS_HEADER not in task["prompt"]
        for c in RIASEC_ITEMS:
            assert pack[0]["interests"][c]["text"] not in task["prompt"]


def test_revealed_items_follow_policy_order_exactly(mini):
    pack, meta, _ = mini
    donors = A.imposter_pairs([p["person_id"] for p in pack])
    fixed = RIASEC_ITEMS[:A.MAX_REVEALS]
    tasks = A.build_static_tasks(pack, meta, fixed, donors)
    by_id = {p["person_id"]: p for p in pack}

    for task in tasks:
        if task["policy"] == "baseline":
            continue
        k = task["k"]
        if task["policy"] == "fixed":
            codes, source = fixed[:k], by_id[task["person_id"]]
        elif task["policy"] == "random":
            codes, source = A.random_order(task["person_id"])[:k], \
                by_id[task["person_id"]]
        else:
            codes, source = A.random_order(task["person_id"])[:k], \
                by_id[task["donor_id"]]
        lines = [ln for ln in task["prompt"].splitlines() if ln.startswith("- ")]
        assert len(lines) == k
        for line, code in zip(lines, codes):
            entry = source["interests"][code]
            assert line == f"- {entry['text']}: {entry['answer']}"


def test_imposter_profile_is_the_donor_not_the_person(mini):
    pack, meta, _ = mini
    donors = A.imposter_pairs([p["person_id"] for p in pack])
    tasks = A.build_static_tasks(pack, meta, RIASEC_ITEMS[:20], donors)
    by_id = {p["person_id"]: p for p in pack}
    for task in (t for t in tasks if t["policy"] == "imposter"):
        assert task["donor_id"] != task["person_id"]
        donor = by_id[task["donor_id"]]
        assert donor["demographics_block"] in task["prompt"]


def test_reveal_order_guard_fires_on_shuffled_block():
    pairs = [("alpha activity", 3), ("beta activity", 5)]
    head = "MY PROFILE\nx\n\nHOW I RATED\n- beta activity: 5\n- alpha activity: 3"
    with pytest.raises(AssertionError):
        A._assert_reveal_order(head, pairs)


def test_uncertainty_guard_rejects_already_revealed_item(mini):
    pack, meta, _ = mini
    person = pack[0]
    codes = RIASEC_ITEMS[:3]
    pairs = [(person["interests"][c]["text"], person["interests"][c]["answer"])
             for c in codes]
    prompt = R.interest_prompt(person["demographics_block"], pairs,
                               meta["riasec_anchors"],
                               person["interests"][codes[0]]["text"])
    with pytest.raises(AssertionError):
        A.assert_uncertainty_prompt_clean(
            prompt, person["interests"][codes[0]]["text"],
            list(meta["tipi_texts"].values()), pairs)


def test_uncertainty_prompt_is_clean_for_unrevealed_item(mini):
    pack, meta, _ = mini
    person = pack[0]
    codes = RIASEC_ITEMS[:3]
    pairs = [(person["interests"][c]["text"], person["interests"][c]["answer"])
             for c in codes]
    text = person["interests"][RIASEC_ITEMS[10]]["text"]
    prompt = R.interest_prompt(person["demographics_block"], pairs,
                               meta["riasec_anchors"], text)
    A.assert_uncertainty_prompt_clean(prompt, text,
                                      list(meta["tipi_texts"].values()), pairs)


def test_node_pack_strips_tipi_answers(mini):
    pack, _, cb = mini
    node = A.node_pack(pack, cb)
    blob = str(node)
    assert "tipi_texts" in node["persons"][0]
    assert "tipi" not in node["persons"][0]
    for person in node["persons"]:
        assert set(person) == {"person_id", "demographics_block", "interests",
                               "tipi_texts"}
    assert "answer" not in str(node["persons"][0]["tipi_texts"])
    assert blob.count("TIPITEXT_TIPI1_trait") >= 1  # texts survive, answers do not


# ---------------------------------------------------------------------------
# Distribution parsing + entropy
# ---------------------------------------------------------------------------


def test_interest_distribution_parses_and_normalizes():
    dist = R.parse_interest_distribution("1:0.10 2:0.20 3:0.40 4:0.20 5:0.10")
    assert dist is not None
    assert pytest.approx(sum(dist.values()), abs=1e-9) == 1.0
    assert dist[3] == pytest.approx(0.4)


def test_interest_distribution_tolerates_reorder_and_whitespace():
    a = R.parse_interest_distribution("1:0.1 2:0.2 3:0.4 4:0.2 5:0.1")
    b = R.parse_interest_distribution("3 : 0.4\n5:0.1   1:0.1 4:0.2 2:0.2")
    assert a == pytest.approx(b)
    assert b[3] == pytest.approx(0.4)


@pytest.mark.parametrize("bad", [
    "", None, "1:0.5 2:0.5", "1:0.2 2:0.2 3:0.2 4:0.2 5:0.2 6:0.2",
    "1:0.2 1:0.2 3:0.2 4:0.2 5:0.2", "1:-0.2 2:0.4 3:0.4 4:0.2 5:0.2",
    "1:0 2:0 3:0 4:0 5:0", "no numbers here",
])
def test_interest_distribution_rejects_malformed(bad):
    assert R.parse_interest_distribution(bad) is None


def test_five_way_parser_agrees_with_scoring_on_seven_way_rules():
    """Same validation philosophy as the shipped v2 parser (normalization)."""
    seven = v2_probabilities("1:1 2:1 3:1 4:1 5:1 6:1 7:1")
    five = R.parse_interest_distribution("1:1 2:1 3:1 4:1 5:1")
    assert seven[1] == pytest.approx(1 / 7)
    assert five[1] == pytest.approx(1 / 5)


def test_entropy_ordering_and_failure_sentinel():
    uniform = R.parse_interest_distribution("1:0.2 2:0.2 3:0.2 4:0.2 5:0.2")
    peaked = R.parse_interest_distribution("1:0.96 2:0.01 3:0.01 4:0.01 5:0.01")
    assert R.entropy(uniform) > R.entropy(peaked) > 0
    assert R.entropy(None) == R.PARSE_FAILURE_ENTROPY
    assert R.entropy(None) < R.entropy(peaked)


# ---------------------------------------------------------------------------
# Greedy fixed order (ridge, no LLM)
# ---------------------------------------------------------------------------


def _regression_df(n=120, seed=3):
    rng = np.random.default_rng(seed)
    data = {"person_id": np.arange(n, dtype=np.int64),
            "age": rng.integers(18, 60, n), "familysize": rng.integers(1, 5, n)}
    for var in ["education", "urban", "gender", "engnat", "hand", "religion",
                "orientation", "race", "voted", "married"]:
        data[var] = rng.integers(1, 4, n)
    items = rng.integers(1, 6, size=(n, len(RIASEC_ITEMS)))
    for j, c in enumerate(RIASEC_ITEMS):
        data[c] = items[:, j]
    # Make TIPI a noisy function of a few specific items so greedy has signal.
    signal = items[:, 5] + items[:, 20] + items[:, 33]
    for j, c in enumerate(TIPI_ITEMS):
        noisy = signal + rng.normal(0, 0.5, n) + j
        data[c] = np.clip(np.round(noisy / 3 + 3), 1, 7).astype(int)
    return pd.DataFrame(data)


def test_greedy_fixed_order_is_valid_and_deterministic():
    df = _regression_df()
    ids = df["person_id"].tolist()
    a = A.greedy_fixed_order(df, ids, n_items=6)
    b = A.greedy_fixed_order(df, ids, n_items=6)
    assert a["order"] == b["order"]
    assert len(a["order"]) == 6
    assert len(set(a["order"])) == 6
    assert all(c in RIASEC_ITEMS for c in a["order"])
    assert a["lambda"] in A.RIDGE_LAMBDAS
    # greedy is monotone by construction in its own criterion
    maes = [t["oof_mae"] for t in a["trace"]]
    assert maes == sorted(maes, reverse=True) or maes[-1] <= a["base_oof_mae"]


def test_greedy_finds_the_planted_items_first():
    df = _regression_df()
    ids = df["person_id"].tolist()
    order = A.greedy_fixed_order(df, ids, n_items=3)["order"]
    planted = {RIASEC_ITEMS[5], RIASEC_ITEMS[20], RIASEC_ITEMS[33]}
    assert len(planted & set(order)) >= 2


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


def test_record_fields_match_the_batch_runner_record():
    sys.path.insert(0, str(_ROOT / "experiments"))
    import run_replay  # noqa: PLC0415

    class T:
        person_id, arm, tipi_code, true_answer, prompt = 1, "twin", "TIPI1", 4, "P"

    from doppler.scoring import parse_response  # noqa: PLC0415

    raw = "1:0.1 2:0.1 3:0.1 4:0.3 5:0.2 6:0.1 7:0.1"
    ref = run_replay._record_from_parse(
        T(), "v2", "P", raw, parse_response(raw, "v2"), False, 10, 5)
    task = {"person_id": 1, "arm": "twin", "item": "TIPI1", "policy": "random",
            "k": 4, "donor_id": None, "prompt": "P"}
    mine = A.record_from_completion(task, raw, 10, 5, 4)
    assert set(ref).issubset(set(mine))
    for key in ref:
        assert mine[key] == ref[key], key
    assert set(mine) - set(ref) == {"policy", "k", "donor_id"}


def test_missing_completion_becomes_a_parse_failure():
    task = {"person_id": 1, "arm": "twin", "item": "TIPI1", "policy": "random",
            "k": 4, "donor_id": None, "prompt": "P"}
    rec = A.record_from_completion(task, None, 0, 0, 4, error="missing idx 3")
    assert rec["parse_failure"] is True
    assert rec["parsed"] is None
    assert "no completion" in rec["raw_response"]


# ---------------------------------------------------------------------------
# Call accounting
# ---------------------------------------------------------------------------


def test_call_counts_match_the_amendment_arithmetic():
    counts = A.call_counts(150)
    assert counts["baseline"] == 1500
    assert counts["random"] == counts["fixed"] == counts["imposter"] == 10500
    assert counts["adaptive_predictions"] == 10500
    assert counts["adaptive_uncertainty"] == 150 * 770
    assert sum(counts.values()) == 159000


def test_projection_is_positive_and_scales():
    small = A.project_node_hours(10)["projected_node_hours"]
    big = A.project_node_hours(150)["projected_node_hours"]
    assert 0 < small < big


# ---------------------------------------------------------------------------
# The node driver's round loop, offline
# ---------------------------------------------------------------------------


class StubGenerator:
    """Deterministic fake model.

    Interest questions: entropy is keyed to the item's canonical index, so the
    expected reveal order is exactly known. TIPI questions: a fixed valid
    7-way distribution.
    """

    def __init__(self, item_texts):
        # rank 0 = most uncertain
        self.rank = {text: i for i, text in enumerate(item_texts)}
        self.calls = []

    def __call__(self, prompts, max_tokens):
        out = []
        for p in prompts:
            self.calls.append((p, max_tokens))
            if "I see myself as" in p:
                out.append({"text": "1:0.1 2:0.1 3:0.1 4:0.3 5:0.2 6:0.1 7:0.1",
                            "tokens_in": 100, "tokens_out": 40})
                continue
            asked = p.split('activity: "')[1].split('" on this scale')[0]
            r = self.rank[asked]
            # lower rank -> flatter distribution -> higher entropy
            peak = 0.20 + 0.015 * r
            rest = (1.0 - peak) / 4
            out.append({
                "text": f"1:{peak:.4f} 2:{rest:.4f} 3:{rest:.4f} "
                        f"4:{rest:.4f} 5:{rest:.4f}",
                "tokens_in": 100, "tokens_out": 40})
        return out


@pytest.fixture
def node_inputs(mini):
    pack, _, cb = mini
    node = A.node_pack(pack, cb)
    return pack, node["persons"], node["meta"]


def test_node_loop_reveals_max_entropy_items_in_order(node_inputs):
    pack, persons, meta = node_inputs
    texts = [persons[0]["interests"][c]["text"] for c in RIASEC_ITEMS]
    gen = StubGenerator(texts)
    preds, uncs = [], []
    revealed, stats = DRIVER.run_rounds(persons, meta, gen, preds.extend,
                                        uncs.extend, 4, log=lambda *_: None)

    # Stub entropy is highest for the lowest canonical index, so the reveal
    # order must be exactly the first 4 canonical items.
    for pid, order in revealed.items():
        assert order == RIASEC_ITEMS[:4]

    n = len(persons)
    assert stats["n_uncertainty_calls"] == n * (48 + 47 + 46 + 45)
    assert stats["uncertainty_parse_failures"] == 0
    # checkpoints at k=1,2,4 within 4 rounds -> 3 prediction batches
    assert stats["n_prediction_calls"] == n * 3 * 10
    assert sorted({r["k"] for r in preds}) == [1, 2, 4]
    assert len(uncs) == stats["n_uncertainty_calls"]
    assert sum(1 for u in uncs if u["selected"]) == n * 4


def test_node_loop_prompts_never_leak_tipi_or_reveal_the_query(node_inputs):
    pack, persons, meta = node_inputs
    texts = [persons[0]["interests"][c]["text"] for c in RIASEC_ITEMS]
    gen = StubGenerator(texts)
    preds, uncs = [], []
    DRIVER.run_rounds(persons, meta, gen, preds.extend, uncs.extend, 3,
                      log=lambda *_: None)

    tipi_texts = [persons[0]["tipi_texts"][c] for c in TIPI_ITEMS]
    for prompt, _ in gen.calls:
        head = prompt.split("\n\nYOUR TASK")[0]
        for text in tipi_texts:
            assert text not in head
        assert "I see myself as" not in head
        if 'activity: "' in prompt:
            asked = prompt.split('activity: "')[1].split('" on this scale')[0]
            assert asked not in head  # never ask about an already-revealed item

    # every prediction prompt's revealed block matches the policy's order
    by_id = {p["person_id"]: p for p in pack}
    for rec in preds:
        person = by_id[rec["person_id"]]
        codes = RIASEC_ITEMS[: rec["k"]]
        pairs = [(person["interests"][c]["text"], person["interests"][c]["answer"])
                 for c in codes]
        A.assert_prompt_clean(rec["prompt"], persons[0]["tipi_texts"][rec["item"]],
                              person["tipi"][rec["item"]]["answer"], tipi_texts,
                              pairs)


def test_node_loop_parse_failures_are_never_preferred(node_inputs):
    """An unparseable answer must not win the max-entropy selection."""
    pack, persons, meta = node_inputs
    texts = [persons[0]["interests"][c]["text"] for c in RIASEC_ITEMS]
    base = StubGenerator(texts)
    broken_text = persons[0]["interests"][RIASEC_ITEMS[0]]["text"]

    def gen(prompts, max_tokens):
        out = base(prompts, max_tokens)
        for i, p in enumerate(prompts):
            if 'activity: "' in p and broken_text in p.split("YOUR TASK")[1]:
                out[i] = {"text": "sorry, I cannot help",
                          "tokens_in": 10, "tokens_out": 5}
        return out

    revealed, stats = DRIVER.run_rounds(persons, meta, gen, lambda _: None,
                                        lambda _: None, 2, log=lambda *_: None)
    assert stats["uncertainty_parse_failures"] > 0
    for order in revealed.values():
        # RIASEC_ITEMS[0] would have been first on entropy, but it failed to
        # parse, so it must be pushed behind every parseable candidate.
        assert order[0] != RIASEC_ITEMS[0]
        assert order == [RIASEC_ITEMS[1], RIASEC_ITEMS[2]]


def _run(persons, meta, gen, rounds, **kw):
    preds, uncs = [], []
    revealed, stats = DRIVER.run_rounds(persons, meta, gen, preds.extend,
                                        uncs.extend, rounds,
                                        log=lambda *_: None, **kw)
    return revealed, stats, preds, uncs


def _write_state(tmp_path, uncs, preds):
    import json as _json

    for name, rows in (("uncertainty.jsonl", uncs),
                       ("completions_adaptive.jsonl", preds)):
        with (tmp_path / name).open("w") as fh:
            for row in rows:
                fh.write(_json.dumps(row) + "\n")


def test_resume_from_a_clean_stop_matches_an_uninterrupted_run(node_inputs, tmp_path):
    """Stopping after 2 rounds and resuming must reproduce the 4-round run."""
    pack, persons, meta = node_inputs
    texts = [persons[0]["interests"][c]["text"] for c in RIASEC_ITEMS]

    whole_rev, _, whole_preds, whole_uncs = _run(persons, meta,
                                                 StubGenerator(texts), 4)

    part_rev, _, part_preds, part_uncs = _run(persons, meta,
                                              StubGenerator(texts), 2)
    _write_state(tmp_path, part_uncs, part_preds)
    ids = [p["person_id"] for p in persons]
    revealed, done_ks, next_idx, unc_rows, pred_rows = DRIVER.load_resume_state(
        str(tmp_path), ids, len(meta["tipi_codes"]))
    assert done_ks == {1, 2}
    assert next_idx == len(part_preds)
    assert all(len(v) == 2 for v in revealed.values())

    rest_rev, _, rest_preds, rest_uncs = _run(
        persons, meta, StubGenerator(texts), 4,
        revealed=revealed, done_ks=done_ks, start_idx=next_idx)

    assert rest_rev == whole_rev
    joined = pred_rows + rest_preds
    assert len(joined) == len(whole_preds)
    assert [(r["person_id"], r["k"], r["item"], r["prompt"]) for r in joined] == \
           [(r["person_id"], r["k"], r["item"], r["prompt"]) for r in whole_preds]
    assert [r["idx"] for r in joined] == list(range(len(whole_preds)))
    assert len(unc_rows) + len(rest_uncs) == len(whole_uncs)


def test_resume_drops_a_partial_round_and_a_partial_checkpoint(node_inputs, tmp_path):
    pack, persons, meta = node_inputs
    texts = [persons[0]["interests"][c]["text"] for c in RIASEC_ITEMS]
    _, _, preds, uncs = _run(persons, meta, StubGenerator(texts), 2)
    ids = [p["person_id"] for p in persons]

    # Truncate: drop one person's selection in round 1, and half of k=2's preds.
    victim = ids[0]
    uncs = [u for u in uncs
            if not (u["round"] == 1 and u["person_id"] == victim and u["selected"])]
    k2 = [p for p in preds if p["k"] == 2]
    preds = [p for p in preds if p["k"] == 1] + k2[: len(k2) // 2]
    _write_state(tmp_path, uncs, preds)

    revealed, done_ks, next_idx, unc_rows, pred_rows = DRIVER.load_resume_state(
        str(tmp_path), ids, len(meta["tipi_codes"]))
    assert all(len(v) == 1 for v in revealed.values())  # round 1 dropped
    assert done_ks == {1}                                # k=2 dropped
    assert all(r["round"] == 0 for r in unc_rows)
    assert all(r["k"] == 1 for r in pred_rows)
    assert next_idx == len(pred_rows)


def test_resume_catches_up_a_checkpoint_the_prefix_already_passed(node_inputs):
    """Killed between the k=2 reveal and its predictions -> redo just those."""
    pack, persons, meta = node_inputs
    texts = [persons[0]["interests"][c]["text"] for c in RIASEC_ITEMS]
    revealed = {p["person_id"]: RIASEC_ITEMS[:2] for p in persons}
    _, stats, preds, uncs = _run(persons, meta, StubGenerator(texts), 2,
                                 revealed=revealed, done_ks={1}, start_idx=10)
    assert stats["n_uncertainty_calls"] == 0     # no rounds left to run
    assert stats["n_prediction_calls"] == len(persons) * 10
    assert {r["k"] for r in preds} == {2}
    assert [r["idx"] for r in preds] == list(range(10, 10 + len(preds)))


def test_resume_rejects_out_of_lockstep_reveal_prefixes(node_inputs):
    pack, persons, meta = node_inputs
    revealed = {p["person_id"]: RIASEC_ITEMS[:2] for p in persons}
    revealed[persons[0]["person_id"]] = RIASEC_ITEMS[:3]
    with pytest.raises(AssertionError):
        _run(persons, meta, lambda p, m: [], 4, revealed=revealed)


def test_load_resume_state_on_empty_dir(node_inputs, tmp_path):
    _, persons, meta = node_inputs
    ids = [p["person_id"] for p in persons]
    revealed, done_ks, next_idx, unc_rows, pred_rows = DRIVER.load_resume_state(
        str(tmp_path), ids, 10)
    assert revealed == {pid: [] for pid in ids}
    assert done_ks == set() and next_idx == 0
    assert unc_rows == [] and pred_rows == []


def test_node_loop_rejects_tipi_content_in_demographics(node_inputs):
    _, persons, meta = node_inputs
    persons = [dict(p) for p in persons]
    persons[0]["demographics_block"] += " " + persons[0]["tipi_texts"]["TIPI1"]
    with pytest.raises(AssertionError):
        DRIVER.run_rounds(persons, meta, lambda p, m: [], lambda _: None,
                          lambda _: None, 1, log=lambda *_: None)
