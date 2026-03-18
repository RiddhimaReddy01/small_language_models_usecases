# Part A - Benchmark Setup

- Benchmark: `information_extraction`
- Run path: `Information Extraction\outputs_hf_llama1b_smoke\20260317_191820`

## Task Definition

```json
{
  "task": "information_extraction",
  "benchmark_name": "sroie_ie_hf_llama1b_smoke"
}
```

## Dataset and Sampling

```json
{
  "sample_size": 4
}
```

## Experimental Setup

```json
{
  "models": [
    "Llama-3.2-1B-Instruct"
  ]
}
```

## Metrics

```json
[
  {
    "model": "Llama-3.2-1B-Instruct",
    "capability_metrics": {
      "Model": "Llama-3.2-1B-Instruct",
      "Macro F1": 0.18333333333333335,
      "Micro F1": 0.2,
      "Exact Match": 0.0,
      "Schema Valid Rate": 0.75,
      "Hallucination Rate": 0.75,
      "F1 Clean": 0.2,
      "F1 Noisy": null,
      "Robustness Drop": null
    },
    "operational_metrics": {
      "Model": "Llama-3.2-1B-Instruct",
      "Avg Latency / Doc (s)": 0.8845369000046048,
      "Throughput (docs/min)": 67.83210513850541,
      "Peak GPU Memory (MB)": null,
      "Avg Input Tokens": 137.75,
      "Avg Output Tokens": 2.75
    },
    "reliability_metrics": {
      "f1_variance": 0.0,
      "prediction_consistency": null,
      "invalid_output_rate": 0.25
    }
  }
]
```

## Raw Benchmark Results

```json
{
  "prediction_row_count": 4
}
```
