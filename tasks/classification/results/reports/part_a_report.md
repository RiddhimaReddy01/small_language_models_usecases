# Part A - Benchmark Setup

- Benchmark: `classification`
- Run path: `classification\results`

## Task Definition

```json
{
  "task": "classification",
  "datasets": [
    "demo-upload"
  ]
}
```

## Dataset and Sampling

```json
{
  "model": "phi3:mini",
  "workers": 1,
  "profile": null,
  "input_file": "examples\\upload_example.csv",
  "dataset_name": "demo-upload",
  "test_mode": true,
  "seed": 42
}
```

## Experimental Setup

```json
{
  "model": "phi3:mini",
  "workers": 1
}
```

## Metrics

```json
{
  "capability": {
    "demo-upload": {
      "accuracy": 1.0,
      "macro_f1": 1.0,
      "weighted_f1": 1.0,
      "precision": 1.0,
      "recall": 1.0,
      "validity_rate": 1.0
    }
  },
  "operational": [
    {
      "dataset": "demo-upload",
      "total_samples": 2,
      "total_time": 2.3781471252441406,
      "throughput": 0.8409908616543983,
      "latency_mean": 1.1863574981689453,
      "latency_p95": 1.3456708431243896,
      "cpu_util_avg": 66.25,
      "mem_usage_delta_mb": -340.64453125,
      "parse_failure_rate": 0.0
    }
  ]
}
```

## Raw Benchmark Results

```json
{
  "raw_result_file_count": 15,
  "latest_row_count": 2,
  "columns": [
    "text",
    "true_label",
    "prediction",
    "latency",
    "is_valid",
    "dataset",
    "status"
  ]
}
```
