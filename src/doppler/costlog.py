"""Append-only cost log: one JSON line per run under results/cost_log.jsonl."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

COST_LOG_FIELDS = (
    "run_id",
    "timestamp",
    "model",
    "split",
    "n_persons",
    "n_calls",
    "n_retries",
    "n_parse_failures",
    "tokens_in",
    "tokens_out",
)

# Token prices in USD per 1,000,000 tokens, keyed by model. Trivially editable
# per model; a model absent from this table gets cost_usd = null.
#   gemini-3.5-flash-lite: input 0.30, output 2.50
#   (source: openrouter.ai/google/gemini-3.5-flash-lite and pricepertoken.com,
#    fetched 2026-07-24)
#   gemini-3.5-flash: input 0.75, output 4.50
#   (source: pricepertoken.com/pricing-page/model/google-gemini-3.5-flash,
#    fetched 2026-07-27. That page lists three providers for the one model:
#    Google AI Studio at 0.75/4.50, and Google (Vertex) and OpenRouter both at
#    1.50/9.00. We record the Google AI Studio row because that is the endpoint
#    doppler actually calls -- src/doppler/gemini.py wraps the google-genai AI
#    Studio SDK. Anything routed elsewhere costs 2x this and must be repriced.)
PRICE_IN = 0.30
PRICE_OUT = 2.50
MODEL_PRICES = {
    "gemini-3.5-flash-lite": {"in": PRICE_IN, "out": PRICE_OUT},
    "gemini-3.5-flash": {"in": 0.75, "out": 4.50},
}


def cost_usd_for(model: str, tokens_in: int, tokens_out: int) -> float | None:
    """USD cost from tokens, or None if the model has no price (e.g. batch runs).

    Batch/HPC runs (backend leonardo-batch) name a non-priced model, so their
    cost_usd stays null -- node_hours records their GPU cost instead.
    """
    price = MODEL_PRICES.get(model)
    if price is None:
        return None
    return round(tokens_in / 1e6 * price["in"] + tokens_out / 1e6 * price["out"], 6)


def build_cost_entry(
    run_id: str,
    model: str,
    split: str,
    n_persons: int,
    n_calls: int,
    n_retries: int,
    n_parse_failures: int,
    tokens_in: int,
    tokens_out: int,
    variant: str = "v0",
    resumed: bool = False,
    backend: str = "gemini",
    node_hours: float | None = None,
) -> dict:
    """Assemble one cost-log record with an ISO-8601 UTC timestamp.

    A resume writes its own line (same ``run_id``, ``resumed=True``) counting
    only the calls/tokens spent by the resuming process; summing all lines with
    a given ``run_id`` gives that run's true totals. ``backend`` names the
    generation backend; ``node_hours`` records batch-job GPU cost (None for the
    live Gemini backend, which has no GPU cost).
    """
    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "split": split,
        "variant": variant,
        "backend": backend,
        "resumed": bool(resumed),
        "n_persons": int(n_persons),
        "n_calls": int(n_calls),
        "n_retries": int(n_retries),
        "n_parse_failures": int(n_parse_failures),
        "tokens_in": int(tokens_in),
        "tokens_out": int(tokens_out),
        "cost_usd": cost_usd_for(model, int(tokens_in), int(tokens_out)),
        "node_hours": (None if node_hours is None else float(node_hours)),
    }


def append_cost_log(entry: dict, path: str | Path) -> None:
    """Append ``entry`` as one JSON line, creating the file/dir if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
