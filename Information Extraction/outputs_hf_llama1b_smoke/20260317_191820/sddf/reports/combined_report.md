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

# Part B - SDDF Analysis

- Benchmark: `information_extraction`
- Run path: `Information Extraction\outputs_hf_llama1b_smoke\20260317_191820`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `available`
- Reason: Computed from SDDF archive.

### Summary

- `|Gamma|`: 4 examples

## Difficulty Annotation + Binning

- Status: `available`
- Reason: Computed from SDDF archive.

### Bin Counts

- Bin `nan` / `SLM`: 4 rows

## Matched SLM vs LLM Analysis

- Status: `partial`
- Reason: Inferred from aggregate historical evidence because matched SLM and LLM rows were not available.

### Historical comparison

- Historical extraction results indicate local SLMs are strong on field-copy and schema adherence, while normalization-heavy fields degrade.
- The comparison signal is directional because older runs were not stored as matched row-level archives.
- Caveat: this comparison is aggregate and not example-matched, so it should not be treated as a strict paired test.

## Capability Curve + Tipping Point

- Status: `partial`
- Reason: Inferred from aggregate historical evidence because matched SLM and LLM rows were not available.

### Inferred transition point

- Historical tipping signal: historical evidence places the cliff around normalization-heavy fields where parsing demand rises above simple copy behavior.
- Operational reading: schema adherence is manageable locally; parsing and normalization are the real failure point.
- Caveat: tipping point is inferred from prior benchmark patterns, not estimated from a fresh ratio curve on matched rows.

## Uncertainty Analysis

- Status: `partial`
- Reason: Inferred from aggregate historical evidence because matched SLM and LLM rows were not available.

### Historical uncertainty

- Historical sample size signal: `4` prediction rows were saved.
- Uncertainty source: older extraction runs are sparse, so inferred thresholds should be treated as directional.
- Caveat: no bootstrap confidence interval was available without matched rerun rows.

## Failure Taxonomy

- Status: `available`
- Reason: Computed from SDDF archive.

- Heuristic structural failures: 0
- Heuristic fixable failures: 4
- Invalid outputs: 1
- Note: this taxonomy is heuristic and should be reviewed against task-specific failure labels.

## Quality Gate

- Status: `partial`
- Reason: Inferred from aggregate historical evidence because matched SLM and LLM rows were not available.

### Suggested gate

- accept SLM outputs when schema validity is high and fields are copy-like
- route normalization-heavy fields through deterministic post-processing or escalation
- Caveat: gate thresholds are policy recommendations inferred from historical evidence, not learned from fresh matched supervision.

## Deployment Zones

- Status: `partial`
- Reason: Inferred from aggregate historical evidence because matched SLM and LLM rows were not available.

### Inferred deployment stance

- Likely SDDF stance: SLM-with-mitigation for structured extraction, escalating only normalization-heavy edge cases.
- Why: historical results favor local models on structured extraction while showing a clear drop on normalization subtasks.
- Caveat: zone assignment is a benchmark-level recommendation and should be revalidated after reruns.

## Routing Policy

- Status: `partial`
- Reason: Inferred from aggregate historical evidence because matched SLM and LLM rows were not available.

### Suggested routing policy

- keep straightforward field extraction on the SLM path
- add deterministic cleanup for normalization steps
- escalate noisy or ambiguous normalization cases
- Caveat: this is a hand-authored routing rule from historical evidence, not a learned router threshold.

