"""Cost-log tests: cost_usd from tokens (gemini) and null for batch models."""

from __future__ import annotations

import pytest

from doppler.costlog import PRICE_IN, PRICE_OUT, build_cost_entry, cost_usd_for


def test_cost_usd_gemini_from_tokens():
    # 1M in + 1M out = PRICE_IN + PRICE_OUT dollars.
    assert cost_usd_for("gemini-3.5-flash-lite", 1_000_000, 1_000_000) \
        == pytest.approx(PRICE_IN + PRICE_OUT)
    entry = build_cost_entry("run", "gemini-3.5-flash-lite", "pilot",
                             n_persons=20, n_calls=400, n_retries=0,
                             n_parse_failures=0, tokens_in=195_980, tokens_out=400)
    expected = 195_980 / 1e6 * PRICE_IN + 400 / 1e6 * PRICE_OUT
    assert entry["cost_usd"] == pytest.approx(expected)


def test_cost_usd_null_for_batch_model():
    assert cost_usd_for("leonardo-batch", 1000, 1000) is None
    entry = build_cost_entry("run", "leonardo-batch", "pilot2",
                             n_persons=50, n_calls=0, n_retries=0,
                             n_parse_failures=0, tokens_in=1000, tokens_out=1000,
                             backend="leonardo-batch", node_hours=0.203)
    assert entry["cost_usd"] is None
    assert entry["node_hours"] == 0.203
