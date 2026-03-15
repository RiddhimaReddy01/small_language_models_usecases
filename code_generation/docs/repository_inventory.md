# Repository Inventory

This file records the cleanup classification used to reshape the repository into a GitHub-ready evaluation pipeline.

## Keep In Main Surface

- `src/codegen_eval/`
- `README.md`
- `pyproject.toml`
- `configs/examples/`
- `configs/experiments/`
- `benchmarks/`
- `docs/`
- `scripts/`
- `tests/`

## Archived Instead Of Deleted

- old root experiment presets moved to `archive/configs/`
- historical raw runs moved to `archive/runs/`
- parser replay/debug output moved to `archive/debug/`

## Raw Vs Curated Artifacts

- `runs/` contains the current raw run workspace
- `benchmarks/` contains curated tables and manifests intended for publication or sharing
