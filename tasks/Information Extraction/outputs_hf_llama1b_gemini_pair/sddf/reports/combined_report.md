# Part A - Benchmark Setup

- Benchmark: `information_extraction`
- Run path: `Information Extraction\outputs_hf_llama1b_gemini_pair`

## Task Definition

```json
{
  "task": "information_extraction",
  "benchmark_name": "sroie_ie_hf_llama1b_gemini_pair"
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
    "Llama-3.2-1B-Instruct",
    "gemini-2.5-flash-lite"
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
  },
  {
    "model": "gemini-2.5-flash-lite",
    "capability_metrics": {
      "Model": "gemini-2.5-flash-lite",
      "Macro F1": 0.625,
      "Micro F1": 0.625,
      "Exact Match": 0.0,
      "Schema Valid Rate": 1.0,
      "Hallucination Rate": 0.25,
      "F1 Clean": 0.625,
      "F1 Noisy": null,
      "Robustness Drop": null
    },
    "operational_metrics": {
      "Model": "gemini-2.5-flash-lite",
      "Avg Latency / Doc (s)": 0.6694906999910017,
      "Throughput (docs/min)": 89.62036365972885,
      "Peak GPU Memory (MB)": null,
      "Avg Input Tokens": 494.75,
      "Avg Output Tokens": 64.5
    },
    "reliability_metrics": {
      "f1_variance": 0.0,
      "prediction_consistency": null,
      "invalid_output_rate": 0.0
    }
  }
]
```

## Raw Benchmark Results

```json
{
  "prediction_row_count": 8
}
```

# Part B - SDDF Analysis

- Benchmark: `information_extraction`
- Run path: `Information Extraction\outputs_hf_llama1b_gemini_pair`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `available`
- Reason: Computed from SDDF archive.

### Summary

- `|Gamma|`: 8 examples

## Difficulty Annotation + Binning

- Status: `available`
- Reason: Computed from SDDF archive.

### Bin Counts

- Bin `nan` / `LLM`: 4 rows
- Bin `nan` / `SLM`: 4 rows

## Matched SLM vs LLM Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### Pairs

- `Llama-3.2-1B-Instruct` vs `gemini-2.5-flash-lite` on `clean`: 4 matched examples

## Capability Curve + Tipping Point

- Status: `available`
- Reason: Computed from SDDF archive.

### Llama-3.2-1B-Instruct vs gemini-2.5-flash-lite

- Tipping point: `None`
- Tipping sensitivity: `{'0.90': None, '0.93': None, '0.95': None, '0.97': None}`
- Plot file: `Information Extraction\outputs_hf_llama1b_gemini_pair\sddf\reports\clean_llama_3_2_1b_instruct_vs_gemini_2_5_flash_lite.png`

![Capability curve](clean_llama_3_2_1b_instruct_vs_gemini_2_5_flash_lite.png)


## Uncertainty Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### Llama-3.2-1B-Instruct vs gemini-2.5-flash-lite

- Tipping median: `None`
- 95% CI: `None` to `None`
- Threshold sweep: `{'0.90': None, '0.93': None, '0.95': None, '0.97': None}`


## Failure Taxonomy

- Status: `available`
- Reason: Computed from SDDF archive.

- Heuristic structural failures: 0
- Heuristic fixable failures: 8
- Invalid outputs: 1
- Validity note: partial or invalid runs should be excluded from strict cross-model comparison.
- Note: this taxonomy is heuristic and should be reviewed against task-specific failure labels.

## Quality Gate

- Status: `available`
- Reason: Computed from SDDF archive.

### Llama-3.2-1B-Instruct vs gemini-2.5-flash-lite



## Deployment Zones

- Status: `available`
- Reason: Computed from SDDF archive.

### Llama-3.2-1B-Instruct vs gemini-2.5-flash-lite

- Bin `0` at difficulty `5.000` -> Zone `C`


## Routing Policy

- Status: `available`
- Reason: Computed from SDDF archive.

### Llama-3.2-1B-Instruct vs gemini-2.5-flash-lite

- No routing threshold learned.


