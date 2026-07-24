"""Generation backends for the twin pipeline.

The pipeline talks to a generation service only through :class:`Backend`, so the
same task/parse/score code can run against the live Gemini API or an offline HPC
batch model without changing anything downstream.

Two backends ship here:

* :class:`GeminiBackend` wraps the existing live client. It is a thin,
  order-preserving pass-through: one ``client.generate`` per prompt, fatal
  errors propagate exactly as before (so the runner's abort path is unchanged),
  and no retry/cap/pacing behaviour is altered.
* :class:`BatchFileBackend` is two-phase for HPC queues that cannot do per-call
  round trips: **export** writes ``prompts.jsonl`` (one deterministic line per
  task), the batch job produces ``completions.jsonl`` offline, and **ingest**
  joins completions back onto prompts by ``idx`` so the normal parse/score path
  runs unchanged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class BackendResult:
    """One generation result. ``error`` is set only when a result is missing or
    failed (e.g. an absent completion); a normal success has ``error=None``."""

    text: str
    tokens_in: int
    tokens_out: int
    error: str | None = None


@runtime_checkable
class Backend(Protocol):
    name: str

    def batch_generate(
        self, prompts: list[str], *, max_output_tokens: int
    ) -> list[BackendResult]:
        """Return one result per prompt, in the same order and length."""
        ...


# ---------------------------------------------------------------------------
# Live Gemini backend (thin pass-through over the existing client)
# ---------------------------------------------------------------------------


class GeminiBackend:
    """Order-preserving wrapper over the existing :class:`GeminiClient`.

    The client is already configured (temperature, per-variant output-token
    budget, retry/cap/pacing), so ``max_output_tokens`` here is accepted for
    protocol conformance but the client's own configuration governs. Errors
    from ``client.generate`` (cap reached, fatal API error) are allowed to
    propagate unchanged so the runner's existing abort handling still fires.
    """

    name = "gemini"

    def __init__(self, client):
        self.client = client

    def batch_generate(
        self, prompts: list[str], *, max_output_tokens: int
    ) -> list[BackendResult]:
        results: list[BackendResult] = []
        for prompt in prompts:
            text, tokens_in, tokens_out = self.client.generate(prompt)
            results.append(BackendResult(text=text, tokens_in=tokens_in,
                                         tokens_out=tokens_out, error=None))
        return results


# ---------------------------------------------------------------------------
# Offline batch-file backend (export / ingest)
# ---------------------------------------------------------------------------


def write_prompts_jsonl(records: list[dict], out_path: str | Path) -> int:
    """Write export records as JSON lines (deterministic order). Returns count."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    return len(records)


def read_completions(path: str | Path) -> dict[int, dict]:
    """Load a completions.jsonl into ``{idx: record}`` (last write per idx wins)."""
    comps: dict[int, dict] = {}
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            comps[int(obj["idx"])] = obj
    return comps


class BatchFileBackend:
    """Offline backend backed by a pre-computed ``completions.jsonl``.

    Ingest usage: build the same deterministic task list, then
    ``batch_generate([t.prompt for t in tasks])`` returns the completion for
    each position (``idx == position``). A missing completion yields a
    ``BackendResult`` with ``error`` set (scored as a parse failure downstream).
    """

    name = "batchfile"

    #: Fields written per prompt line at export time.
    EXPORT_FIELDS = ("idx", "prompt", "max_output_tokens",
                     "person_id", "arm", "item", "variant")

    def __init__(self, completions: dict[int, dict] | None = None):
        self._completions = completions or {}

    @classmethod
    def from_completions(cls, path: str | Path) -> "BatchFileBackend":
        return cls(read_completions(path))

    @staticmethod
    def export(tasks, variant: str, max_output_tokens: int,
               out_path: str | Path) -> int:
        """Write ``prompts.jsonl`` for ``tasks`` (idx = task order). Returns count."""
        records = [
            {
                "idx": idx,
                "prompt": task.prompt,
                "max_output_tokens": max_output_tokens,
                "person_id": task.person_id,
                "arm": task.arm,
                "item": task.tipi_code,
                "variant": variant,
            }
            for idx, task in enumerate(tasks)
        ]
        return write_prompts_jsonl(records, out_path)

    def batch_generate(
        self, prompts: list[str], *, max_output_tokens: int
    ) -> list[BackendResult]:
        results: list[BackendResult] = []
        for idx in range(len(prompts)):
            obj = self._completions.get(idx)
            if obj is None:
                results.append(BackendResult("", 0, 0,
                                             error=f"missing completion idx {idx}"))
                continue
            meta = obj.get("gen_meta") or {}
            results.append(BackendResult(
                text=obj.get("text") or "",
                tokens_in=int(meta.get("tokens_in", 0) or 0),
                tokens_out=int(meta.get("tokens_out", 0) or 0),
                error=None,
            ))
        return results
