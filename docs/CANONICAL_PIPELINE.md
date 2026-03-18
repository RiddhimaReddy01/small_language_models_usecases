# Canonical Benchmark Pipeline

This repository now uses one canonical benchmark contract for every task:

1. `dataset_sampling`
2. `model_inference`
3. `prediction_storage`
4. `metric_computation`
5. `benchmark_report_generation`

## Why this is the right fit for the current codebase

The repo is already split into multiple benchmark packages with different maturity levels and different runtime dependencies. A full physical refactor into one shared package would create a lot of risk right now. The safer structure is:

- keep each benchmark in its own folder
- register each benchmark against the same five stages
- enforce that contract with lightweight tests

That gives us a single canonical shape without forcing a high-risk rewrite.

## Source of truth

`benchmark_pipeline_registry.json` is the canonical registry for benchmark structure.

Every benchmark entry must declare:

- the benchmark root
- the five stages in canonical order
- the file and symbol currently responsible for that stage

## CI rule

`tests/test_benchmark_pipeline_contract.py` validates the registry and fails if:

- a benchmark is missing a stage
- the stage order changes
- a referenced file does not exist
- a referenced symbol is missing from the mapped file

## Migration guideline

When adding or refactoring a benchmark:

1. Keep the five canonical stages.
2. If a stage moves to a new file or function, update `benchmark_pipeline_registry.json`.
3. Keep test modules self-bootstrapping so they can run independently from the repo root.
