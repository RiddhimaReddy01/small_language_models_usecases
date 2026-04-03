# Repository Structure

## data/
- `01_processed/`: persistent benchmark outputs.
- `ground_truth/`: task-level references used for capability/risk evaluation.

## model_runs/
- `<task>/sddf/`: canonical task artifacts (`thresholds.json`, `routing_policy.json`, `canonical_rows.jsonl`).
- `sddf_summary.json`: global SDDF summary.
- `benchmarking/configs/`: tuned reproducibility configs (for example `task_utility_coeffs.json`).
- `benchmarking/phase_reports/`: validation/test headline reports (`val_phase_report.*`, `test_phase_report.*`).
- `benchmarking/error_taxonomy/`: failure taxonomy summaries by task/model.
- `benchmarking/deployment/`: cost/latency/safety tradeoff reports.

## tools/
- `generate_benchmark75_sddf.py`: train/val/test SDDF generation.
- `evaluate_test_phase.py`: split report evaluation with CIs/significance.
- `tune_task_utility_coeffs.py`: per-task utility tuning from validation candidates.
- `summarize_error_taxonomy.py`: task/model failure taxonomy analysis.
- `summarize_deployment_tradeoffs.py`: separate deployment framing.
- `run_reproducibility_bundle.py`: one-command end-to-end reproducibility run.
