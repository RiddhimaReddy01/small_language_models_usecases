# SLM Use Cases

Reproducible SDDF routing pipeline with strict `train/val/test` separation, frozen-policy test evaluation, and separate deployment tradeoff reporting.

## Core Paths

- `data/` -> benchmarks and ground truth
- `tools/` -> generation/evaluation scripts
- `sddf/` -> shared difficulty/routing utilities
- `model_runs/` -> generated artifacts

## One-Command Reproducibility

```powershell
.\.venv\Scripts\python.exe tools\run_reproducibility_bundle.py
```

This runs:

1. validation generation and validation report
2. per-task utility tuning
3. frozen test generation and test report
4. separate error-taxonomy report
5. separate deployment tradeoff report

## Canonical Outputs

- Task-level:
  - `model_runs/<task>/sddf/thresholds.json`
  - `model_runs/<task>/sddf/routing_policy.json`
  - `model_runs/<task>/sddf/canonical_rows.jsonl`
- Global:
  - `model_runs/sddf_summary.json`
  - `model_runs/benchmarking/configs/task_utility_coeffs.json`
  - `model_runs/benchmarking/phase_reports/val_phase_report.json|csv|md`
  - `model_runs/benchmarking/phase_reports/test_phase_report.json|csv|md`
  - `model_runs/benchmarking/error_taxonomy/error_taxonomy_by_task_model.json|csv|md`
  - `model_runs/benchmarking/deployment/deployment_tradeoffs.json|csv|md`

## Notes

- No graph artifacts are produced in the SDDF reproducibility flow.
- Ground truth is loaded from `data/ground_truth/<task>.jsonl|json`.
