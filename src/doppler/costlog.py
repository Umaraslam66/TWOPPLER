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
) -> dict:
    """Assemble one cost-log record with an ISO-8601 UTC timestamp.

    A resume writes its own line (same ``run_id``, ``resumed=True``) counting
    only the calls/tokens spent by the resuming process; summing all lines with
    a given ``run_id`` gives that run's true totals.
    """
    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "split": split,
        "variant": variant,
        "resumed": bool(resumed),
        "n_persons": int(n_persons),
        "n_calls": int(n_calls),
        "n_retries": int(n_retries),
        "n_parse_failures": int(n_parse_failures),
        "tokens_in": int(tokens_in),
        "tokens_out": int(tokens_out),
    }


def append_cost_log(entry: dict, path: str | Path) -> None:
    """Append ``entry`` as one JSON line, creating the file/dir if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
