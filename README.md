# SLM Use Cases

This repository captures the Sample Difficulty Distribution Framework (SDDF) pipeline for analyzing model capability and risk across domains.

- `docs/` holds the canonical pipeline overviews (`SDDF_PIPELINE.md`) and the repository structure (`README_STRUCTURE.md`).
- `data/01_processed`, `data/02_sampling`, and `data/03_complexity` mirror the ingest → stratified sampling → task complexity stages.
- `sddf/` provides the reusable scoring, matching, gating, tipping, and decision-matrix utilities.
- `src/` contains routing helpers and tooling for production analysis and monitoring.
- `tasks/`, `framework/benchmarking/`, and `tools/` hold the per-task scaffolding, benchmarking orchestration, and helper scripts.

See `docs/SDDF_PIPELINE.md` for the exact formulas, learned tau logic, and Pareto reasoning that govern routing decisions.
