# TWOPPLER

TWOPPLER (internal codename **DOPPLER** — the name used throughout the
pre-registration documents, the results record, and the `src/doppler`
package) is a research pipeline for building and evaluating "digital twin" agents:
LLM-based agents that predict a specific person's held-out answers using only
partial information about that person. The primary metric throughout is *lift* — how
much better a grounded twin does than an uninformed baseline on material it never saw.

Stage 1 used survey respondents and was development only. Stage 2 uses real
broadcast interview transcripts: ground a twin on a person's earlier interviews,
then have it answer questions from a later, held-out one.

This repository holds the data loaders, experiment scaffolding, evaluation code,
and the frozen record of what was pre-registered and what came out.

The pre-registration is registered on OSF as **TWOPPLER** (2026-07-28):
https://osf.io/qz28m — see `results/PROJECT_LOG.md` for which parts of the work
it precedes and which parts it postdates.

## Status

Stage 2's confirmatory run is complete. In one line each:

- **H1 (twin fidelity)** — passed its pre-registered bars.
- **H7 (twin staleness)** — exploratory, no headline: the two scoring channels
  disagree, and the disagreement is what gets reported.
- **H6 (follow-up-rich grounding)** — descriptive only and unresolved at
  confirmatory scale; too few subjects could supply both arms at the frozen
  budget for any hypothesis test.

The reports below are the source of truth for every number. This README
deliberately carries none.

## Where things live

| what | where |
|---|---|
| The pre-registration and its amendments (the governance chain, frozen) | `PREREGISTRATION*.md` in the repo root |
| Chronological map of the whole project, with links | `results/PROJECT_LOG.md` |
| Stage 2 confirmatory report (H1, H7, contamination) | `results/stage2_confirm/STAGE2_CONFIRM_REPORT.md` |
| H6 verdict report | `results/stage2_confirm/H6_REPORT.md` |
| H7 exploratory diagnostics | `results/stage2_confirm/h7_diagnostics.md` |
| Stage 1 and Stage 1E reports, dev pilots, notes | `results/` |
| Write-up drafts | `results/writeups/` |
| Per-run cost ledger | `results/cost_log.jsonl` |

Read `results/PROJECT_LOG.md` first if you are picking the project up cold. It
is a map, not a source of truth: where it disagrees with a report, the report
wins; where it disagrees with the pre-registration, the pre-registration wins.

`data/` is gitignored. `app/` holds the optional Stage 3 demo.

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

## Regenerate the Stage 2 reports

Every report has one driver, and the drivers are deterministic, CPU-only, and
make no API or GPU call — they read artifacts already committed under
`results/stage2_confirm/` and re-derive every number:

    uv run python experiments/stage2_confirm_report.py
    uv run python experiments/h6_report.py
    uv run python experiments/h7_diagnostics.py

Re-running the underlying experiments is a different matter: generation needs
either the Google AI Studio key in `.env` or a Leonardo allocation, and the
per-stage drivers (`experiments/stage2_confirm_*.py`, `experiments/h6_*.py`)
each document their own inputs. Each report names the exact script and file
hashes it was built from, so a regenerated report that differs from the
committed one means an input moved.
