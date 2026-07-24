# DOPPLER

DOPPLER is a research pipeline for building and evaluating "digital twin" agents:
LLM-based agents that predict a specific person's held-out survey answers using only
partial information about that person. The primary metric throughout is *lift* — how
much better a grounded twin does than an uninformed baseline on questions it never saw.

This repository holds the data loaders, experiment scaffolding, and evaluation code.

## Install

Requires [uv](https://docs.astral.sh/uv/):

    uv sync

## Run tests

    uv run pytest
