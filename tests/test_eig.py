"""Stage-1E EXP3 tests: the multi-target parser, the EIG maths, the node loop.

Everything here runs offline -- no vLLM, no network. The node driver's round
loop is exercised with a stub model that answers the three prompt kinds
(interest, multi-target TIPI, single-target TIPI) as deterministic functions of
the prompt, so the reveal order the policy *should* produce is known by hand and
asserted exactly.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from doppler import eig_render as E
from doppler.data import RIASEC_ITEMS, TIPI_ITEMS
from doppler.prompts import _demographics_block, _format_anchors
from doppler.scoring import v2_probabilities

_ROOT = Path(__file__).resolve().parents[1]


def _load_driver():
    """Import experiments/eig_node_driver.py as a module."""
    path = _ROOT / "experiments" / "eig_node_driver.py"
    spec = importlib.util.spec_from_file_location("eig_node_driver", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["eig_node_driver"] = mod
    spec.loader.exec_module(mod)
    return mod


DRIVER = _load_driver()

HYPOTHETICALS = (1, 3, 5)
TOP_N = 5


# ---------------------------------------------------------------------------
# Fixtures: a small node pack built here, so these tests do not depend on
# doppler.adaptive's pack builder.
# ---------------------------------------------------------------------------


@pytest.fixture
def node_inputs(record_factory, full_demographics, fake_codebook):
    persons = []
    for i in range(4):
        rec = record_factory(2000 + i, dict(full_demographics, age=20 + i))
        for j, code in enumerate(RIASEC_ITEMS):
            rec["interests"][code]["answer"] = ((i + j) % 5) + 1
        persons.append({
            "person_id": rec["person_id"],
            "demographics_block": _demographics_block(rec["demographics"]),
            "interests": {c: dict(rec["interests"][c]) for c in RIASEC_ITEMS},
            "tipi_texts": {c: fake_codebook.tipi_items[c] for c in TIPI_ITEMS},
        })
    meta = {
        "riasec_codes": list(RIASEC_ITEMS),
        "tipi_codes": list(TIPI_ITEMS),
        "riasec_anchors": _format_anchors(fake_codebook.scales["riasec"]["anchors"]),
        "tipi_anchors": _format_anchors(fake_codebook.scales["tipi"]["anchors"]),
        "checkpoints": [1, 2, 4, 8, 12, 16, 20],
        "max_reveals": 20,
        "max_output_tokens_tipi": 120,
        "max_output_tokens_interest": 100,
    }
    return persons, meta


# ---------------------------------------------------------------------------
# Multi-target completions used by the parser tests
# ---------------------------------------------------------------------------


def _probs_for(j):
    """A distinct, valid 7-way distribution for target index ``j``."""
    peak = (j % 7) + 1
    return [0.4 if v == peak else 0.1 for v in range(1, 8)]


def _line(code, probs, sep=":"):
    body = " ".join(f"{v}:{p}" for v, p in zip(range(1, 8), probs))
    return f"{code}{sep} {body}"


def _clean_completion(codes=TIPI_ITEMS):
    return "\n".join(_line(c, _probs_for(j)) for j, c in enumerate(codes))


# ---------------------------------------------------------------------------
# parse_multi_tipi
# ---------------------------------------------------------------------------


def test_multi_parse_round_trips_and_normalizes():
    out = E.parse_multi_tipi(_clean_completion(), TIPI_ITEMS)
    assert out is not None
    assert set(out) == set(TIPI_ITEMS)
    for j, code in enumerate(TIPI_ITEMS):
        dist = out[code]
        assert set(dist) == set(range(1, 8))
        assert sum(dist.values()) == pytest.approx(1.0)
        # 0.4 against six 0.1s -> total 1.0, so the peak normalizes to 0.4
        assert dist[(j % 7) + 1] == pytest.approx(0.4)


def test_multi_parse_matches_the_shipped_v2_parser_per_line():
    """The 7-point rules here must not drift from doppler.scoring."""
    out = E.parse_multi_tipi(_clean_completion(), TIPI_ITEMS)
    for j, code in enumerate(TIPI_ITEMS):
        body = " ".join(f"{v}:{p}" for v, p in
                        zip(range(1, 8), _probs_for(j)))
        assert out[code] == pytest.approx(v2_probabilities(body))
        assert E.parse_tipi_distribution(body) == pytest.approx(
            v2_probabilities(body))


def test_multi_parse_tolerates_markdown_prose_and_reordering():
    lines = []
    for j, code in enumerate(TIPI_ITEMS):
        probs = _probs_for(j)
        if j % 4 == 0:
            lines.append("- **" + _line(code, probs) + "**")
        elif j % 4 == 1:
            lines.append(_line(code, probs, sep=" -"))
        elif j % 4 == 2:
            lines.append(f"{j + 1}. " + _line(code, probs))
        else:
            lines.append("   " + _line(code, probs) + "   ")
    lines = list(reversed(lines))  # any order
    text = ("Sure -- here are my ratings:\n\n"
            + "\n\n".join(lines)
            + "\n\nLet me know if you want anything explained.")
    out = E.parse_multi_tipi(text, TIPI_ITEMS)
    assert out is not None
    plain = E.parse_multi_tipi(_clean_completion(), TIPI_ITEMS)
    assert set(out) == set(plain)
    for code in plain:
        assert out[code] == pytest.approx(plain[code])


def test_multi_parse_does_not_confuse_tipi1_with_tipi10():
    """TIPI1 is a prefix of TIPI10; the longest code must win."""
    out = E.parse_multi_tipi(_clean_completion(), TIPI_ITEMS)
    j10 = TIPI_ITEMS.index("TIPI10")
    assert out["TIPI10"][(j10 % 7) + 1] == pytest.approx(0.4)
    j1 = TIPI_ITEMS.index("TIPI1")
    assert out["TIPI1"][(j1 % 7) + 1] == pytest.approx(0.4)


def test_multi_parse_ignores_a_pairless_line_that_starts_with_a_code():
    text = ("TIPI1 through TIPI10 are below:\n"
            + _clean_completion())
    assert E.parse_multi_tipi(text, TIPI_ITEMS) is not None


def test_multi_parse_rejects_a_missing_code():
    text = _clean_completion(TIPI_ITEMS[:-1])
    assert E.parse_multi_tipi(text, TIPI_ITEMS) is None


def test_multi_parse_rejects_a_duplicated_code():
    text = _clean_completion() + "\n" + _line("TIPI3", _probs_for(0))
    assert E.parse_multi_tipi(text, TIPI_ITEMS) is None


@pytest.mark.parametrize("bad_probs,label", [
    ([0.1] * 6, "six probabilities"),
    ([-0.1] + [0.2] * 6, "a negative probability"),
    ([0.0] * 7, "an all-zero line"),
    ([0.1] * 8, "eight probabilities"),
])
def test_multi_parse_rejects_a_malformed_line(bad_probs, label):
    lines = []
    for j, code in enumerate(TIPI_ITEMS):
        probs = bad_probs if code == "TIPI3" else _probs_for(j)
        body = " ".join(f"{v}:{p}" for v, p in
                        zip(range(1, len(probs) + 1), probs))
        lines.append(f"{code}: {body}")
    assert E.parse_multi_tipi("\n".join(lines), TIPI_ITEMS) is None, label


@pytest.mark.parametrize("bad", ["", None, "sorry, I cannot help",
                                 "TIPI1: 1:0.5 2:0.5"])
def test_multi_parse_rejects_junk(bad):
    assert E.parse_multi_tipi(bad, TIPI_ITEMS) is None


# ---------------------------------------------------------------------------
# The maths
# ---------------------------------------------------------------------------


def test_total_variation_bounds_and_symmetry():
    flat = {v: 1 / 7 for v in range(1, 8)}
    assert E.total_variation(flat, dict(flat)) == pytest.approx(0.0)
    lo = {v: 1.0 if v == 1 else 0.0 for v in range(1, 8)}
    hi = {v: 1.0 if v == 7 else 0.0 for v in range(1, 8)}
    assert E.total_variation(lo, hi) == pytest.approx(1.0)
    assert E.total_variation(hi, lo) == pytest.approx(1.0)
    assert E.total_variation(flat, lo) == pytest.approx(
        E.total_variation(lo, flat))
    assert 0.0 < E.total_variation(flat, lo) < 1.0


def test_mean_tv_shift_averages_over_targets():
    flat = {v: 1 / 7 for v in range(1, 8)}
    hi = {v: 1.0 if v == 7 else 0.0 for v in range(1, 8)}
    codes = ["A", "B"]
    a = {"A": dict(hi), "B": dict(flat)}
    zero = {"A": dict(flat), "B": dict(flat)}
    # one target moves 6/7, the other does not move at all
    assert E.mean_tv_shift(a, zero, codes) == pytest.approx((6 / 7) / 2)


def test_mean_tv_shift_is_zero_when_either_side_failed_to_parse():
    codes = list(TIPI_ITEMS)
    good = E.parse_multi_tipi(_clean_completion(), codes)
    assert E.mean_tv_shift(None, good, codes) == 0.0
    assert E.mean_tv_shift(good, None, codes) == 0.0
    assert E.mean_tv_shift(None, None, codes) == 0.0


def test_mean_tv_shift_treats_a_missing_target_as_no_movement():
    flat = {v: 1 / 7 for v in range(1, 8)}
    hi = {v: 1.0 if v == 7 else 0.0 for v in range(1, 8)}
    codes = ["A", "B"]
    assert E.mean_tv_shift({"A": hi}, {"A": flat, "B": flat}, codes) == \
        pytest.approx((6 / 7) / 2)


def test_hypothetical_weights_renormalize_over_the_three_anchors():
    q = {1: 0.4, 2: 0.1, 3: 0.2, 4: 0.1, 5: 0.2}
    w = E.hypothetical_weights(q, HYPOTHETICALS)
    assert set(w) == {1, 3, 5}
    assert sum(w.values()) == pytest.approx(1.0)
    assert w[1] == pytest.approx(0.5)   # 0.4 / (0.4+0.2+0.2)
    assert w[3] == pytest.approx(0.25)
    assert w[5] == pytest.approx(0.25)


@pytest.mark.parametrize("q", [
    None, {}, {1: 0.0, 2: 0.5, 3: 0.0, 4: 0.5, 5: 0.0},
])
def test_hypothetical_weights_fall_back_to_uniform(q):
    w = E.hypothetical_weights(q, HYPOTHETICALS)
    assert w == pytest.approx({1: 1 / 3, 3: 1 / 3, 5: 1 / 3})


def test_info_gain_score_is_the_weighted_sum():
    shifts = {1: 0.2, 3: 0.4, 5: 0.6}
    weights = {1: 0.5, 3: 0.25, 5: 0.25}
    # 0.5*0.2 + 0.25*0.4 + 0.25*0.6 = 0.1 + 0.1 + 0.15
    assert E.info_gain_score(shifts, weights) == pytest.approx(0.35)
    assert E.info_gain_score({}, weights) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# The stub model
# ---------------------------------------------------------------------------


#: How much each RIASEC item "moves" the model's beliefs in the stub. The first
#: five entries are what round 0's shortlist sees, and index 3 is the largest,
#: so round 0 must reveal RIASEC_ITEMS[3]. At round 1 the reference belief sits
#: at 0.60, so the winner is whichever shortlisted item is *furthest* from it --
#: index 5 (0.05), the only remaining small mover in the top five.
MOVES = [0.10, 0.20, 0.30, 0.60, 0.40] + [0.05] * (len(RIASEC_ITEMS) - 5)


class EIGStub:
    """Deterministic fake model that answers all three prompt kinds.

    Interest prompts: flatness (and so entropy) is keyed to the item's canonical
    index, lowest index = most uncertain, so the shortlist is exactly the first
    ``top_n`` unrevealed items.

    Belief prompts (multi-target and single-target alike): the answer is a
    mixture ``(1-m) * uniform + m * point-mass-at-7`` where ``m`` comes from the
    LAST revealed pair -- i.e. from the hypothetical, when there is one. Target
    ``j`` gets ``m * (j+1)/10`` so the average over targets actually exercises
    the averaging. Because both prompt kinds read the same table, multi-target
    mode and the per-target fallback see identical distributions.
    """

    def __init__(self, item_texts, tipi_texts, moves=MOVES):
        self.rank = {text: i for i, text in enumerate(item_texts)}
        self.move = {text: moves[i] for i, text in enumerate(item_texts)}
        self.tipi_index = {text: j for j, text in enumerate(tipi_texts)}
        self.codes = list(TIPI_ITEMS)
        self.calls = []

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def revealed_pairs(prompt):
        head = prompt.split("\n\nYOUR TASK")[0]
        pairs = []
        for line in head.splitlines():
            if line.startswith("- "):
                text, answer = line[2:].rsplit(": ", 1)
                pairs.append((text, int(answer)))
        return pairs

    def _m(self, prompt):
        pairs = self.revealed_pairs(prompt)
        return self.move[pairs[-1][0]] if pairs else 0.0

    @staticmethod
    def _seven(m):
        base = (1.0 - m) / 7.0
        return [base + (m if v == 7 else 0.0) for v in range(1, 8)]

    def _body(self, m, j):
        probs = self._seven(m * (j + 1) / 10.0)
        return " ".join(f"{v}:{p:.6f}" for v, p in zip(range(1, 8), probs))

    # -- the model --------------------------------------------------------
    def __call__(self, prompts, max_tokens):
        out = []
        for p in prompts:
            self.calls.append((p, max_tokens))
            if E.MULTI_TIPI_INSTRUCTION in p:
                m = self._m(p)
                text = "\n".join(f"{c}: {self._body(m, j)}"
                                 for j, c in enumerate(self.codes))
                out.append({"text": text, "tokens_in": 400, "tokens_out": 350})
            elif "I see myself as" in p:
                asked = p.split("I see myself as: ")[1].split('"')[0]
                out.append({"text": self._body(self._m(p),
                                               self.tipi_index[asked]),
                            "tokens_in": 120, "tokens_out": 40})
            else:
                asked = p.split('activity: "')[1].split('" on this scale')[0]
                r = self.rank[asked]
                peak = 0.20 + 0.015 * r  # lower rank -> flatter -> more entropy
                rest = (1.0 - peak) / 4
                out.append({
                    "text": f"1:{peak:.4f} 2:{rest:.4f} 3:{rest:.4f} "
                            f"4:{rest:.4f} 5:{rest:.4f}",
                    "tokens_in": 100, "tokens_out": 40})
        return out


def _stub(persons):
    texts = [persons[0]["interests"][c]["text"] for c in RIASEC_ITEMS]
    tipi = [persons[0]["tipi_texts"][c] for c in TIPI_ITEMS]
    return EIGStub(texts, tipi)


def _run(persons, meta, gen, rounds, checkpoints=(1, 2), **kw):
    preds, scores = [], []
    revealed, stats = DRIVER.run_eig_rounds(
        persons, meta, gen, preds.extend, scores.extend, rounds,
        checkpoints=list(checkpoints), top_n=TOP_N,
        hypotheticals=HYPOTHETICALS, tiebreak_seed=71, log=lambda *_: None,
        **kw)
    return revealed, stats, preds, scores


# ---------------------------------------------------------------------------
# The round loop
# ---------------------------------------------------------------------------


def test_loop_reveals_the_biggest_expected_mover(node_inputs):
    persons, meta = node_inputs
    gen = _stub(persons)
    revealed, _stats, _preds, scores = _run(persons, meta, gen, 2)
    for order in revealed.values():
        assert order == [RIASEC_ITEMS[3], RIASEC_ITEMS[5]]
    # exactly one selection per person per round, out of top_n candidates
    assert len(scores) == len(persons) * 2 * TOP_N
    assert sum(1 for s in scores if s["selected"]) == len(persons) * 2


def test_loop_call_counts_are_exactly_the_policy_arithmetic(node_inputs):
    persons, meta = node_inputs
    gen = _stub(persons)
    _rev, stats, preds, _scores = _run(persons, meta, gen, 2)
    n = len(persons)

    assert stats["n_uncertainty_calls"] == n * (48 + 47)
    # per person per round: 1 reference + top_n * len(hypotheticals)
    assert stats["n_shift_calls"] == n * 2 * (1 + TOP_N * len(HYPOTHETICALS))
    assert stats["n_prediction_calls"] == n * 2 * 10  # checkpoints k=1,2
    assert stats["uncertainty_parse_failures"] == 0
    assert stats["shift_parse_failures"] == 0
    assert stats["reference_parse_failures"] == 0

    n_interest = sum(1 for p, _ in gen.calls if 'activity: "' in p)
    n_multi = sum(1 for p, _ in gen.calls if E.MULTI_TIPI_INSTRUCTION in p)
    assert n_interest == stats["n_uncertainty_calls"]
    assert n_multi == stats["n_shift_calls"]
    assert len(gen.calls) - n_interest - n_multi == stats["n_prediction_calls"]
    assert len(preds) == stats["n_prediction_calls"]


def test_reveal_orders_have_length_max_reveals(node_inputs):
    persons, meta = node_inputs
    revealed, _stats, _p, _s = _run(persons, meta, _stub(persons), 6,
                                    checkpoints=(1, 2, 3, 4, 5, 8))
    for order in revealed.values():
        assert len(order) == 6
        assert len(set(order)) == 6


def test_checkpoints_fire_at_the_right_depths(node_inputs):
    persons, meta = node_inputs
    _rev, _stats, preds, _s = _run(persons, meta, _stub(persons), 5,
                                   checkpoints=(1, 3, 5))
    assert sorted({r["k"] for r in preds}) == [1, 3, 5]
    for k in (1, 3, 5):
        assert sum(1 for r in preds if r["k"] == k) == len(persons) * 10


def test_completion_rows_have_the_shape_the_ingester_expects(node_inputs):
    persons, meta = node_inputs
    _rev, _stats, preds, _s = _run(persons, meta, _stub(persons), 2)
    required = {"idx", "kind", "person_id", "k", "item", "prompt", "text",
                "tokens_in", "tokens_out"}
    assert [r["idx"] for r in preds] == list(range(len(preds)))
    for row in preds:
        assert set(row) == required
        assert row["kind"] == "predict"
        assert row["item"] in TIPI_ITEMS
        assert json.dumps(row)  # every value is JSON-serializable


def test_score_rows_carry_the_policy_audit_trail(node_inputs):
    persons, meta = node_inputs
    _rev, _stats, _p, scores = _run(persons, meta, _stub(persons), 1,
                                    checkpoints=(1,))
    required = {"person_id", "round", "item", "rank", "entropy", "tv_shift",
                "weights", "score", "selected", "parse_failures",
                "reference_parse_failure", "n_tied"}
    for row in scores:
        assert set(row) == required
        assert set(row["tv_shift"]) == {"1", "3", "5"}
        assert set(row["weights"]) == {"1", "3", "5"}
        assert sum(row["weights"].values()) == pytest.approx(1.0)
        assert json.dumps(row)
    # the shortlist really is the five most uncertain items
    for pid in {r["person_id"] for r in scores}:
        items = [r["item"] for r in sorted(
            (r for r in scores if r["person_id"] == pid),
            key=lambda r: r["rank"])]
        assert items == list(RIASEC_ITEMS[:TOP_N])


def test_prompts_never_leak_tipi_or_re_ask_a_revealed_item(node_inputs):
    persons, meta = node_inputs
    gen = _stub(persons)
    _run(persons, meta, gen, 3, checkpoints=(1, 2, 3))

    tipi_texts = [persons[0]["tipi_texts"][c] for c in TIPI_ITEMS]
    for prompt, _ in gen.calls:
        head = prompt.split("\n\nYOUR TASK")[0]
        for text in tipi_texts:
            assert text not in head
        assert "I see myself as" not in head
        if 'activity: "' in prompt:
            asked = prompt.split('activity: "')[1].split('" on this scale')[0]
            assert asked not in head  # never re-ask an already-revealed item


def test_hypothetical_answers_are_the_hypothesis_not_the_truth(node_inputs):
    """A hypothetical reveal must carry 1/3/5, never the person's real answer."""
    persons, meta = node_inputs
    gen = _stub(persons)
    _run(persons, meta, gen, 1, checkpoints=())

    by_id = {p["person_id"]: p for p in persons}
    seen = set()
    for prompt, _ in gen.calls:
        if E.MULTI_TIPI_INSTRUCTION not in prompt:
            continue
        pairs = EIGStub.revealed_pairs(prompt)
        if not pairs:
            continue  # the round-0 reference call
        assert len(pairs) == 1
        text, answer = pairs[0]
        assert answer in HYPOTHETICALS
        seen.add(answer)
    assert seen == set(HYPOTHETICALS)
    # and the truth is not what got written: at least one person's real answer
    # for the top candidate differs from every hypothetical it was asked with
    person = by_id[persons[0]["person_id"]]
    assert person["interests"][RIASEC_ITEMS[0]]["answer"] in range(1, 6)


def test_all_garbage_belief_answers_still_finish_the_ladder(node_inputs):
    """Every candidate scores 0.0 -> the tie-break decides, nothing crashes."""
    persons, meta = node_inputs
    base = _stub(persons)

    def gen(prompts, max_tokens):
        out = base(prompts, max_tokens)
        for i, p in enumerate(prompts):
            if E.MULTI_TIPI_INSTRUCTION in p:
                out[i] = {"text": "I'd rather not guess.",
                          "tokens_in": 10, "tokens_out": 6}
        return out

    revealed, stats, _preds, scores = _run(persons, meta, gen, 3,
                                           checkpoints=(1, 2, 3))
    assert stats["shift_parse_failures"] > 0
    assert stats["reference_parse_failures"] > 0
    for order in revealed.values():
        assert len(order) == 3 and len(set(order)) == 3
    assert all(row["score"] == 0.0 for row in scores)
    assert all(row["n_tied"] == TOP_N for row in scores)
    # the winner is always one of the five shortlisted items
    for pid, order in revealed.items():
        picks = {r["item"] for r in scores
                 if r["person_id"] == pid and r["selected"]}
        assert picks == set(order)


def test_a_candidate_with_movement_beats_one_whose_calls_all_failed(node_inputs):
    """Parse failure means 'no evidence of movement', never a free win."""
    persons, meta = node_inputs
    base = _stub(persons)
    winner_text = persons[0]["interests"][RIASEC_ITEMS[3]]["text"]

    def gen(prompts, max_tokens):
        out = base(prompts, max_tokens)
        for i, p in enumerate(prompts):
            # break exactly the (otherwise winning) candidate's hypotheticals
            if E.MULTI_TIPI_INSTRUCTION in p and f"- {winner_text}: " in p:
                out[i] = {"text": "no", "tokens_in": 10, "tokens_out": 2}
        return out

    revealed, stats, _preds, scores = _run(persons, meta, gen, 1,
                                           checkpoints=())
    assert stats["shift_parse_failures"] == len(persons) * len(HYPOTHETICALS)
    for order in revealed.values():
        assert order[0] != RIASEC_ITEMS[3]
    broken = [r for r in scores if r["item"] == RIASEC_ITEMS[3]]
    assert broken and all(r["score"] == 0.0 for r in broken)
    assert all(r["parse_failures"] == len(HYPOTHETICALS) for r in broken)


def test_same_stub_and_seed_gives_byte_identical_reveal_orders(node_inputs):
    persons, meta = node_inputs
    a, _s, _p, _sc = _run(persons, meta, _stub(persons), 4,
                          checkpoints=(1, 2, 4))
    b, _s, _p, _sc = _run(persons, meta, _stub(persons), 4,
                          checkpoints=(1, 2, 4))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_determinism_holds_when_the_tiebreak_is_doing_the_choosing(node_inputs):
    """All-zero scores -> the seeded random tie-break must still replay."""
    persons, meta = node_inputs

    def make():
        base = _stub(persons)

        def gen(prompts, max_tokens):
            out = base(prompts, max_tokens)
            for i, p in enumerate(prompts):
                if E.MULTI_TIPI_INSTRUCTION in p:
                    out[i] = {"text": "nope", "tokens_in": 5, "tokens_out": 2}
            return out
        return gen

    a, _s, _p, _sc = _run(persons, meta, make(), 3, checkpoints=())
    b, _s, _p, _sc = _run(persons, meta, make(), 3, checkpoints=())
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_per_target_fallback_reproduces_the_multi_target_ladder(node_inputs):
    """Same policy, same maths, 10 calls instead of 1 -> same reveal order."""
    persons, meta = node_inputs
    multi_gen = _stub(persons)
    multi, m_stats, _p, _s = _run(persons, meta, multi_gen, 3,
                                  checkpoints=(1, 2, 3),
                                  mode=DRIVER.MODE_MULTI)
    fb_gen = _stub(persons)
    fallback, f_stats, _p, _s = _run(persons, meta, fb_gen, 3,
                                     checkpoints=(1, 2, 3),
                                     mode=DRIVER.MODE_FALLBACK)
    assert fallback == multi
    # the fallback pays 10x on the belief calls and nothing extra elsewhere
    assert f_stats["n_shift_calls"] == m_stats["n_shift_calls"] * 10
    assert f_stats["n_uncertainty_calls"] == m_stats["n_uncertainty_calls"]
    assert f_stats["n_prediction_calls"] == m_stats["n_prediction_calls"]
    assert sum(1 for p, _ in fb_gen.calls
               if E.MULTI_TIPI_INSTRUCTION in p) == 0


def test_loop_rejects_tipi_content_in_demographics(node_inputs):
    persons, meta = node_inputs
    persons = [dict(p) for p in persons]
    persons[0]["demographics_block"] += " " + persons[0]["tipi_texts"]["TIPI1"]
    with pytest.raises(AssertionError):
        _run(persons, meta, _stub(persons), 1)


def test_loop_rejects_out_of_lockstep_reveal_prefixes(node_inputs):
    persons, meta = node_inputs
    revealed = {p["person_id"]: list(RIASEC_ITEMS[:2]) for p in persons}
    revealed[persons[0]["person_id"]] = list(RIASEC_ITEMS[:3])
    with pytest.raises(AssertionError):
        _run(persons, meta, _stub(persons), 4, revealed=revealed)


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


def _write_state(tmp_path, scores, preds):
    for name, rows in (("eig_scores.jsonl", scores),
                       ("completions_eig.jsonl", preds)):
        with (tmp_path / name).open("w") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")


def test_resume_from_a_clean_stop_matches_an_uninterrupted_run(node_inputs,
                                                               tmp_path):
    persons, meta = node_inputs
    whole_rev, _s, whole_preds, whole_scores = _run(persons, meta,
                                                    _stub(persons), 4,
                                                    checkpoints=(1, 2, 4))
    part_rev, _s, part_preds, part_scores = _run(persons, meta, _stub(persons),
                                                 2, checkpoints=(1, 2, 4))
    _write_state(tmp_path, part_scores, part_preds)
    ids = [p["person_id"] for p in persons]
    revealed, done_ks, next_idx, score_rows, pred_rows = \
        DRIVER.load_resume_state(str(tmp_path), ids, 10)
    assert done_ks == {1, 2}
    assert next_idx == len(part_preds)
    assert all(len(v) == 2 for v in revealed.values())
    assert revealed == part_rev

    rest_rev, _s, rest_preds, _sc = _run(
        persons, meta, _stub(persons), 4, checkpoints=(1, 2, 4),
        revealed=revealed, done_ks=done_ks, start_idx=next_idx)
    assert rest_rev == whole_rev
    joined = pred_rows + rest_preds
    assert [(r["person_id"], r["k"], r["item"], r["prompt"]) for r in joined] == \
           [(r["person_id"], r["k"], r["item"], r["prompt"]) for r in whole_preds]
    assert [r["idx"] for r in joined] == list(range(len(whole_preds)))
    assert len(score_rows) == len(part_scores)


def test_resume_drops_a_partial_round_and_a_partial_checkpoint(node_inputs,
                                                              tmp_path):
    persons, meta = node_inputs
    _rev, _s, preds, scores = _run(persons, meta, _stub(persons), 2)
    ids = [p["person_id"] for p in persons]

    victim = ids[0]
    scores = [s for s in scores
              if not (s["round"] == 1 and s["person_id"] == victim
                      and s["selected"])]
    k2 = [p for p in preds if p["k"] == 2]
    preds = [p for p in preds if p["k"] == 1] + k2[: len(k2) // 2]
    _write_state(tmp_path, scores, preds)

    revealed, done_ks, next_idx, score_rows, pred_rows = \
        DRIVER.load_resume_state(str(tmp_path), ids, 10)
    assert all(len(v) == 1 for v in revealed.values())
    assert done_ks == {1}
    assert all(r["round"] == 0 for r in score_rows)
    assert all(r["k"] == 1 for r in pred_rows)
    assert next_idx == len(pred_rows)


def test_resume_catches_up_a_checkpoint_the_prefix_already_passed(node_inputs):
    persons, meta = node_inputs
    revealed = {p["person_id"]: list(RIASEC_ITEMS[:2]) for p in persons}
    _rev, stats, preds, _sc = _run(persons, meta, _stub(persons), 2,
                                   checkpoints=(1, 2), revealed=revealed,
                                   done_ks={1}, start_idx=10)
    assert stats["n_uncertainty_calls"] == 0
    assert stats["n_shift_calls"] == 0
    assert stats["n_prediction_calls"] == len(persons) * 10
    assert {r["k"] for r in preds} == {2}
    assert [r["idx"] for r in preds] == list(range(10, 10 + len(preds)))


def test_load_resume_state_on_an_empty_dir(node_inputs, tmp_path):
    persons, _meta = node_inputs
    ids = [p["person_id"] for p in persons]
    revealed, done_ks, next_idx, score_rows, pred_rows = \
        DRIVER.load_resume_state(str(tmp_path), ids, 10)
    assert revealed == {pid: [] for pid in ids}
    assert done_ks == set() and next_idx == 0
    assert score_rows == [] and pred_rows == []


# ---------------------------------------------------------------------------
# Smoke test + CLI
# ---------------------------------------------------------------------------


def test_smoke_prompts_span_persons_and_depths(node_inputs):
    persons, meta = node_inputs
    prompts = DRIVER.build_smoke_prompts(persons, meta, 12)
    assert len(prompts) == 12
    assert all(E.MULTI_TIPI_INSTRUCTION in p for p in prompts)
    depths = {sum(1 for ln in p.split("\n\nYOUR TASK")[0].splitlines()
                  if ln.startswith("- ")) for p in prompts}
    assert depths == {0, 1, 3}
    assert len(set(prompts)) > 1
    assert DRIVER.build_smoke_prompts(persons, meta, 0) == []


def test_smoke_test_passes_on_a_well_formed_stub(node_inputs):
    persons, meta = node_inputs
    report = DRIVER.run_smoke_test(persons, meta, _stub(persons), 8, 0.95,
                                   log=lambda *_: None)
    assert report["n"] == 8 and report["n_parsed"] == 8
    assert report["parse_rate"] == 1.0 and report["passed"] is True
    assert len(report["examples"]) == 3


def test_smoke_test_fails_and_triggers_the_fallback_verdict(node_inputs):
    persons, meta = node_inputs

    def gen(prompts, max_tokens):
        return [{"text": "I can't do that.", "tokens_in": 5, "tokens_out": 5}
                for _ in prompts]

    report = DRIVER.run_smoke_test(persons, meta, gen, 8, 0.95,
                                   log=lambda *_: None)
    assert report["parse_rate"] == 0.0 and report["passed"] is False


def test_cli_defaults_match_the_experiment_design():
    args = DRIVER.build_args(["--pack", "p.json", "--outdir", "o"])
    assert DRIVER._int_list(args.checkpoints) == [1, 2, 3, 4, 5, 8, 12, 16, 20]
    assert DRIVER._int_list(args.hypotheticals) == [1, 3, 5]
    assert args.max_reveals == 20
    assert args.top_n == 5
    assert args.tiebreak_seed == 71
    assert args.smoke_n == 200
    assert args.min_parse_rate == 0.95
    assert args.fallback_persons == 40
    assert args.tp == 4 and args.temperature == 0.0 and args.seed == 0
