# TWOPPLER

TWOPPLER (internal codename **DOPPLER** — the name used throughout the
pre-registration documents, the results record, and the `src/doppler`
package) is a research pipeline for building and evaluating "digital twin" agents:
LLM-based agents that predict a specific person's held-out survey answers using only
partial information about that person. The primary metric throughout is *lift* — how
much better a grounded twin does than an uninformed baseline on questions it never saw.

This repository holds the data loaders, experiment scaffolding, and evaluation code.

## Install

Requires [uv](https://docs.astral.sh/uv/):

    uv sync

## Run tests

    uv run pytest

## Replay gym (Stage 1)

The Stage-1 gym replays real survey respondents: each person is seeded with
their demographics (and, in the twin arm, their interest ratings), and the
model predicts each of their 10 held-out personality items. The primary metric
is *lift* — twin accuracy minus the demographics-only baseline, per person.

Build every prompt without making any API call:

    uv run python experiments/run_replay.py --split pilot --dry-run

Run the pilot for real (needs `GOOGLE_AI_STUDIO` and `MODEL_NAME` in a local
`.env`):

    uv run python experiments/run_replay.py --split pilot

Each run writes its records, summary, example prompts, and a human-review file
to `results/<run_id>/`, and appends one line to `results/cost_log.jsonl`.
