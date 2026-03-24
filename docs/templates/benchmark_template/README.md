# Benchmark Template

Canonical task layout:

- `README.md`
- `configs/`
- `data/`
- `scripts/dataset_sampling.py`
- `scripts/model_inference.py`
- `scripts/prediction_storage.py`
- `scripts/metric_computation.py`
- `scripts/benchmark_report.py`
- `outputs/runs/<run_id>/...`

Use the stage adapters as the stable public interface even when legacy internals remain task-specific.
