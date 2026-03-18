# Benchmark Governance

This repository should store benchmark metadata in one canonical run artifact folder per run:

```text
results/
  <benchmark>/
    <run_id>/
      run_manifest.json
      config_snapshot.json
      dataset_manifest.json
      hardware.json
      predictions.jsonl
      metrics.json
      report.md
      logs.txt
```

## Canonical storage model

`run_manifest.json` is the top-level source of truth for one benchmark run.

It should contain:

- `run_id`
- `benchmark`
- `started_at`
- `finished_at`
- `status`
- `model`
- `run_config`
- `dataset`
- `hardware`
- `artifacts`

## Required model metadata

Every run must record:

- `name`
- `params`
- `quantization`
- `inference_backend`
- `device`
- `temperature`
- `max_tokens`
- `seed`

Example:

```json
{
  "model": {
    "name": "phi3-mini",
    "params": "3.8B",
    "quantization": "4bit",
    "inference_backend": "ollama",
    "device": "cpu"
  },
  "run_config": {
    "temperature": 0.0,
    "max_tokens": 128,
    "seed": 42,
    "backend": "ollama"
  }
}
```

## Required dataset metadata

`dataset_manifest.json` should contain:

- `name`
- `source`
- `license`
- `split`
- `sampling.seed`
- `sampling.sample_size`
- `sampling.selection_method`

Example:

```json
{
  "name": "GSM8K",
  "source": "OpenAI",
  "license": "MIT",
  "split": "test",
  "sampling": {
    "seed": 42,
    "sample_size": 30,
    "selection_method": "random"
  }
}
```

## Required hardware metadata

`hardware.json` should contain:

- `cpu`
- `ram_gb`
- `gpu`
- `os`
- `python_version`
- `inference_backend`

## Determinism

All benchmarks should use fixed seeds where applicable:

```python
random.seed(42)
numpy.random.seed(42)
torch.manual_seed(42)
```

## What the audit means

The governance audit in `audit_benchmark_governance.py` reports whether each benchmark currently has:

- working stage coverage
- model specification metadata
- run configuration metadata
- dataset governance metadata
- hardware metadata logging
- deterministic seed handling
- per-run artifact folders

`pass` means the evidence is clearly present in code or config.

`partial` means some of the requirement exists, but not the full canonical form yet.

`missing` means the requirement is not visible in the current implementation.
