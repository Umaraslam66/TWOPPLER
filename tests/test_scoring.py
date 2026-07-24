"""Scoring tests: v0/v1/v2 parsers, the exclusion rule, and the MAE summary."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from doppler.scoring import (
    parse_answer,
    parse_response,
    parse_v1,
    parse_v2,
    summarize,
)


# --- v0 parser (unchanged) ------------------------------------------------


@pytest.mark.parametrize("text,expected",
                         [("5", 5), (" 5 ", 5), ("5.", 5), ("Answer: 5", 5),
                          ("1", 1), ("7", 7)])
def test_v0_parser_happy(text, expected):
    assert parse_answer(text) == expected


@pytest.mark.parametrize("text",
                         ["57", "I'd say 5 or 6", "", "0", "8", "10", None, "3.5"])
def test_v0_parser_rejects(text):
    assert parse_answer(text) is None


# --- v1 parser: LAST standalone digit 1-7 ---------------------------------


@pytest.mark.parametrize("text,expected", [
    ("This person is outgoing.\n6", 6),          # sentence + digit
    ("6", 6),                                     # digit only
    ("6.", 6),                                    # trailing period
    ("Probably around 4, but I'd say 5", 5),      # take the LAST standalone
    ("They would strongly agree.\n7", 7),
])
def test_v1_parser_happy(text, expected):
    assert parse_v1(text) == expected


@pytest.mark.parametrize("text", ["", None, "no digit here", "10", "88"])
def test_v1_parser_rejects(text):
    assert parse_v1(text) is None


# --- v2 parser: seven d:p pairs -------------------------------------------


def test_v2_well_formed():
    out = parse_v2("1:0.05 2:0.10 3:0.15 4:0.30 5:0.20 6:0.15 7:0.05")
    assert out is not None
    assert out["ev"] == pytest.approx(4.15)
    assert out["argmax"] == 4
    assert out["renorm_offset"] == pytest.approx(0.0)


def test_v2_reordered_matches():
    ordered = parse_v2("1:0.05 2:0.10 3:0.15 4:0.30 5:0.20 6:0.15 7:0.05")
    shuffled = parse_v2("4:0.30 7:0.05 1:0.05 6:0.15 2:0.10 5:0.20 3:0.15")
    assert shuffled["ev"] == pytest.approx(ordered["ev"])
    assert shuffled["argmax"] == ordered["argmax"]


def test_v2_unnormalized_renormalizes():
    out = parse_v2("1:0.1 2:0.1 3:0.1 4:0.1 5:0.1 6:0.1 7:0.1")
    assert out["renorm_offset"] == pytest.approx(0.3)
    assert out["ev"] == pytest.approx(4.0)  # uniform after renorm


@pytest.mark.parametrize("text", [
    "1:0.5 2:0.5",                                        # missing digits
    "1:-0.1 2:0.2 3:0.2 4:0.2 5:0.2 6:0.2 7:0.3",         # negative prob
    "1:0 2:0 3:0 4:0 5:0 6:0 7:0",                        # sum <= 0
    "0:0.1 1:0.1 2:0.1 3:0.1 4:0.1 5:0.1 6:0.1 7:0.1",    # extra digit (0)
    "8:0.1 1:0.1 2:0.1 3:0.1 4:0.1 5:0.1 6:0.1 7:0.1",    # extra digit (8)
    "1:0.1 1:0.9 2:0.1 3:0.1 4:0.1 5:0.1 6:0.1 7:0.1",    # duplicate key
    "", None,
])
def test_v2_malformed(text):
    assert parse_v2(text) is None


def test_parse_response_dispatch():
    assert parse_response("5", "v0")["parsed"] == 5
    assert parse_response("5", "v3")["parsed"] == 5           # v3 uses the v0 parser
    assert parse_response("5 or 6", "v3")["parse_failure"]    # strict, like v0
    assert parse_response("sentence\n6", "v1")["parsed"] == 6
    v2 = parse_response("1:0.05 2:0.10 3:0.15 4:0.30 5:0.20 6:0.15 7:0.05", "v2")
    assert v2["prediction_argmax"] == 4
    assert v2["prediction_ev"] == pytest.approx(4.15)
    assert v2["mae_point"] == pytest.approx(4.15)
    fail = parse_response("gibberish", "v0")
    assert fail["parse_failure"] and fail["parsed"] is None


# --- summarize: MAE lift, exclusion rule ----------------------------------


def _rec(pid, arm, item, pred, true, *, pf=False, ev=None, argmax=None):
    disc = None if pf else (argmax if argmax is not None else pred)
    return {
        "person_id": pid, "arm": arm, "item": item, "variant": "v0",
        "parsed": None if pf else pred,
        "prediction_ev": ev,
        "prediction_argmax": disc,
        "true_answer": true,
        "parse_failure": pf,
    }


def _example_records():
    r = []
    # Person 1: twin MAE 1.0, baseline MAE 2.5  -> lift 1.5
    r += [_rec(1, "twin", "TIPI1", 5, 5), _rec(1, "twin", "TIPI2", 4, 6)]
    r += [_rec(1, "baseline", "TIPI1", 3, 5), _rec(1, "baseline", "TIPI2", 3, 6)]
    # Person 2: twin MAE 0.5, baseline MAE 3.0  -> lift 2.5
    r += [_rec(2, "twin", "TIPI1", 7, 7), _rec(2, "twin", "TIPI2", 2, 1)]
    r += [_rec(2, "baseline", "TIPI1", 4, 7), _rec(2, "baseline", "TIPI2", 4, 1)]
    return r


def test_summarize_mae_lift_primary():
    out = summarize(_example_records())
    assert out["n_persons"] == 2
    assert out["n_excluded_pairs"] == 0
    mae = out["mae"]
    assert mae["twin"]["mean"] == pytest.approx(0.75)
    assert mae["baseline"]["mean"] == pytest.approx(2.75)
    assert mae["lift"]["mean"] == pytest.approx(2.0)  # baseline - twin, twin better

    # CI matches an independent scipy computation on the per-person lift vector.
    lift = np.array([1.5, 2.5])
    lo, hi = stats.t.interval(0.95, df=1, loc=lift.mean(), scale=stats.sem(lift))
    assert mae["lift"]["ci_low"] == pytest.approx(lo)
    assert mae["lift"]["ci_high"] == pytest.approx(hi)


def test_summarize_key_order_mae_first():
    out = summarize(_example_records())
    keys = [k for k in out if k in ("mae", "within1", "exact", "spearman")]
    assert keys == ["mae", "within1", "exact", "spearman"]


def test_summarize_is_record_order_independent():
    # Concurrency writes records in completion order; scoring keys on
    # (person, arm, item) so the result must not depend on record order.
    import random
    recs = _example_records()
    shuffled = recs[:]
    random.Random(0).shuffle(shuffled)
    a = summarize(recs)
    b = summarize(shuffled)
    assert a["mae"]["lift"]["mean"] == b["mae"]["lift"]["mean"]
    assert a["n_persons"] == b["n_persons"]
    assert a["histograms"] == b["histograms"]
    assert a["per_item"] == b["per_item"]


def test_exclusion_rule_drops_pair_from_both_arms():
    r = _example_records()
    # Make person 1's TIPI2 baseline a parse failure -> that pair excluded
    # from BOTH arms, so person 1 is scored on TIPI1 only.
    for rec in r:
        if rec["person_id"] == 1 and rec["arm"] == "baseline" and rec["item"] == "TIPI2":
            rec.update(parsed=None, prediction_argmax=None, parse_failure=True)
    out = summarize(r)
    assert out["n_excluded_pairs"] == 1
    # Person 1 now: twin TIPI1 ae=0, baseline TIPI1 ae=2 -> lift 2.0
    # Person 2 unchanged: lift 2.5 ; mean lift = 2.25
    assert out["mae"]["lift"]["mean"] == pytest.approx(2.25)
    # Per-item table only has TIPI1 for the excluded person; TIPI2 keeps person 2.
    per_item = {row["item"]: row for row in out["per_item"]}
    assert per_item["TIPI1"]["n"] == 2
    assert per_item["TIPI2"]["n"] == 1


def test_histograms_and_spearman_present():
    out = summarize(_example_records())
    hist = out["histograms"]
    assert set(hist) == {"twin", "baseline"}
    assert sum(hist["twin"]["predicted"].values()) == 4   # 2 persons x 2 items
    assert sum(hist["twin"]["true"].values()) == 4
    assert "twin_mean" in out["spearman"]
    assert "twin_n_none" in out["spearman"]


def test_v2_records_use_ev_for_mae_and_argmax_for_exact():
    # One person, one item, both arms; v2 twin EV 4.15 argmax 4, true 4.
    r = [
        _rec(1, "twin", "TIPI1", 4, 4, ev=4.15, argmax=4),
        _rec(1, "baseline", "TIPI1", 2, 4, ev=2.0, argmax=2),
    ]
    for rec in r:
        rec["variant"] = "v2"
    out = summarize(r)
    # twin MAE uses EV: |4.15 - 4| = 0.15 ; baseline |2.0 - 4| = 2.0
    assert out["mae"]["twin"]["mean"] == pytest.approx(0.15)
    assert out["mae"]["baseline"]["mean"] == pytest.approx(2.0)
    # exact uses argmax: twin 4==4 correct, baseline 2!=4
    assert out["exact"]["twin"]["mean"] == pytest.approx(1.0)
    assert out["exact"]["baseline"]["mean"] == pytest.approx(0.0)
