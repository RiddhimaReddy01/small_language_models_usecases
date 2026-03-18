# Part A - Benchmark Setup

- Benchmark: `text_generation`
- Run path: `text_generation\results\runs\gemini_fresh_2shot`

## Task Definition

```json
{
  "task": "text_generation",
  "task_type": "samples"
}
```

## Dataset and Sampling

```json
{
  "task_type": "samples",
  "seed": 42,
  "repeats": 1
}
```

## Experimental Setup

```json
{
  "model_name": "gemini-2.5-flash-fresh",
  "model_path": "gemini-2.5-flash",
  "model_type": "google",
  "temperature": 0.7,
  "workers": 1,
  "gguf_engine": "llama_cpp"
}
```

## Metrics

```json
{
  "benchmark_summary": [
    {
      "model": "gemini-2.5-flash-fresh",
      "total_tasks": 2,
      "successful_tasks": 2,
      "failed_tasks": 0,
      "success_rate": 1.0,
      "failure_rate": 0.0,
      "avg_constraint_satisfaction_rate": 0.25,
      "avg_format_compliance_rate": 1.0,
      "avg_rouge1": 0.0,
      "avg_rouge2": 0.0,
      "avg_rougeL": 0.0,
      "avg_bert_score_f1": 0.0,
      "avg_hallucination_rate": 0.0,
      "avg_unsupported_claim_count": 0.0,
      "avg_unsafe_response_rate": 0.0,
      "avg_refusal_rate": 0.0,
      "avg_ttft": 0.4606099367141724,
      "avg_total_time": 2.303049683570862,
      "avg_tokens_generated": 57.85000000000001,
      "avg_tps": 28.787453737852136,
      "avg_peak_ram_mb": 0.0,
      "avg_ram_delta_mb": 0.0,
      "avg_model_load_time": 0.001,
      "avg_cost_usd": 4.338750000000001e-06,
      "total_cost_usd": 8.677500000000001e-06,
      "source_files": [
        "results.json"
      ]
    }
  ],
  "metrics_tables_path": "C:\\Users\\riddh\\OneDrive\\Desktop\\SLM use cases\\text_generation\\results\\runs\\gemini_fresh_2shot\\metrics_tables.md"
}
```

## Raw Benchmark Results

```json
{
  "raw_files": [
    "C:\\Users\\riddh\\OneDrive\\Desktop\\SLM use cases\\text_generation\\results\\runs\\gemini_fresh_2shot\\results.json"
  ],
  "example_count_per_run": 2
}
```

# Part B - SDDF Analysis

- Benchmark: `text_generation`
- Run path: `text_generation\results\runs\gemini_fresh_2shot`

## SDDF: Dominant Difficulty Dimension

- Status: `available`
- Reason: Computed from SDDF archive.

### Summary

- `|Gamma|`: 2 examples

## Difficulty Annotation + Binning

- Status: `available`
- Reason: Computed from SDDF archive.

### Bin Counts

- Bin `nan` / `LLM`: 2 rows

## Matched SLM vs LLM Analysis

- Status: `partial`
- Reason: Archive exists, but no matched SLM and LLM rows were found.

Not enough evidence to render this section.

## Capability Curve + Tipping Point

- Status: `partial`
- Reason: Archive exists, but no matched SLM and LLM rows were found.

Not enough evidence to render this section.

## Uncertainty Analysis

- Status: `partial`
- Reason: Archive exists, but no matched SLM and LLM rows were found.

Not enough evidence to render this section.

## Failure Taxonomy

- Status: `available`
- Reason: Computed from SDDF archive.

- Heuristic structural failures: 0
- Heuristic fixable failures: 2
- Invalid outputs: 0
- Note: this taxonomy is heuristic and should be reviewed against task-specific failure labels.

## Quality Gate

- Status: `partial`
- Reason: Archive exists, but no matched SLM and LLM rows were found.

Not enough evidence to render this section.

## Deployment Zones

- Status: `partial`
- Reason: Archive exists, but no matched SLM and LLM rows were found.

Not enough evidence to render this section.

## Routing Policy

- Status: `partial`
- Reason: Archive exists, but no matched SLM and LLM rows were found.

Not enough evidence to render this section.

