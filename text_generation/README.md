# Text Generation Benchmark

This task is exposed through the standardized benchmark interface:

- `scripts/dataset_sampling.py`
- `scripts/model_inference.py`
- `scripts/prediction_storage.py`
- `scripts/metric_computation.py`
- `scripts/benchmark_report.py`

Legacy execution still routes through [`run_benchmark.py`](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/text_generation/run_benchmark.py) while standardized artifacts are written into `outputs/runs/<run_id>/`.
