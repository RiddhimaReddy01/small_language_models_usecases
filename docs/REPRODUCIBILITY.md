# Reproducibility Quickstart

Run the full SDDF reproducibility bundle with one command:

```powershell
.\.venv\Scripts\python.exe tools\run_reproducibility_bundle.py
```

This executes, in order:

1. Validation generation and validation phase report.
2. Per-task utility coefficient tuning from validation candidates.
3. Frozen test generation using tuned per-task coefficients.
4. Test phase report.
5. Separate error-taxonomy report.
6. Separate deployment tradeoff report.

## Output Layout

All reproducibility outputs are under `model_runs/benchmarking/`:

- `configs/task_utility_coeffs.json`
- `phase_reports/val_phase_report.json|csv|md`
- `phase_reports/test_phase_report.json|csv|md`
- `error_taxonomy/error_taxonomy_by_task_model.json|csv|md`
- `deployment/deployment_tradeoffs.json|csv|md`

This keeps scientific train/val/test reporting separate from operational deployment framing.

