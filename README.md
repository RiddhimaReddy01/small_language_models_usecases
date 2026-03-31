# SLM Use Cases - Streamlined Pipeline

This repository now runs from a simplified benchmark layout:

- `data/01_processed/benchmark_output/` -> processed model outputs (`outputs.jsonl`, manifests, metadata)
- `model_runs/` -> tracked benchmark + SDDF artifacts by task
- `sddf/` -> shared SDDF math (difficulty, ingest, reporting, routing helpers)
- `tools/` -> end-to-end generation scripts

## Current End-to-End Flow

1. Ingest normalized benchmark outputs from:
   - `data/01_processed/benchmark_output/<task>/<model>/outputs.jsonl`
2. Run separate benchmarking track (comprehensive capability + operational metrics):
   - `tools/generate_comprehensive_benchmark_metrics.py`
3. Compute SDDF capability/risk by difficulty bin and routing thresholds:
   - `tools/generate_benchmark75_sddf.py`
4. Generate business dashboard and Pareto plots:
   - `tools/generate_business_dashboard.py`
5. Optional code-generation report plots:
   - `tools/plot_code_generation_sddf.py`
6. One-command orchestrator:
   - `tools/run_sddf_pipeline.py`

## Quick Run

```powershell
.\.venv\Scripts\python.exe tools\run_sddf_pipeline.py --ci-level 0.90 --cap-threshold 0.80 --risk-threshold 0.20
```

Optional weighted difficulty scoring:

```powershell
.\.venv\Scripts\python.exe tools\run_sddf_pipeline.py --difficulty-weights difficulty_weights.json
```

## Output Locations

- Task-level SDDF outputs:
  - `model_runs/<task>/benchmarking/comprehensive_metrics.json`
  - `model_runs/<task>/sddf/thresholds.json`
  - `model_runs/<task>/sddf/routing_policy.json`
  - `model_runs/<task>/sddf/canonical_rows.jsonl`
  - `model_runs/<task>/sddf/*.png`
- Global summary:
  - `model_runs/benchmarking/comprehensive_metrics_summary.json`
  - `model_runs/sddf_summary.json`
- Business dashboard:
  - `model_runs/business_analytics/dashboard.json`
  - `model_runs/business_analytics/dashboard.md`

## Notes

- Scripts auto-detect legacy layout (`model_runs/benchmark_75`) if present.
- Ground-truth/reference checks are loaded from `data/ground_truth/<task>.jsonl|json`.
