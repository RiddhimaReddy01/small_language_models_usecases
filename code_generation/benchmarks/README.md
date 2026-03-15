# Benchmarks

This directory stores the curated, publishable benchmark layer for the repository.

## Structure

- `tables/`: latest benchmark tables and copied summary/report artifacts
- `manifests/`: provenance for each curated export, including the source run and config

## Regenerate

```bash
python -m codegen_eval export-tables --run-dir runs/run_YYYYMMDD_HHMMSS --output-dir benchmarks --source-config configs/experiments/transformers_codegen_top3_under15.json
```

The export command rebuilds the tracked tables from a raw run instead of copying values by hand.
