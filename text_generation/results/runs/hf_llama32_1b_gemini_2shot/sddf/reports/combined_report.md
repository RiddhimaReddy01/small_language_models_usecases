# Part A - Benchmark Setup

- Benchmark: `text_generation`
- Run path: `text_generation\results\runs\hf_llama32_1b_gemini_2shot`

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
  "model_name": "hf_llama32_1b + gemini-2.5-flash-fresh",
  "model_path": "multi-run",
  "model_type": "huggingface+google",
  "temperature": null,
  "workers": 1,
  "gguf_engine": null
}
```

## Metrics

```json
{
  "benchmark_summary": null,
  "metrics_tables_path": null
}
```

## Raw Benchmark Results

```json
{
  "raw_files": [
    "C:\\Users\\riddh\\OneDrive\\Desktop\\SLM use cases\\text_generation\\results\\runs\\hf_llama32_1b_gemini_2shot\\results.json"
  ],
  "example_count_per_run": 4
}
```

# Part B - SDDF Analysis

- Benchmark: `text_generation`
- Run path: `text_generation\results\runs\hf_llama32_1b_gemini_2shot`
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

- Bin `nan` / `LLM`: 2 rows
- Bin `nan` / `SLM`: 2 rows

## Matched SLM vs LLM Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### Historical comparison

- Historical text-generation evidence indicates local SLMs are competitive on open-ended generation quality but fall behind on heavy multi-constraint adherence.
- Caveat: this comparison is aggregate and not example-matched, so it should not be treated as a strict paired test.

## Capability Curve + Tipping Point

- Status: `available`
- Reason: Computed from SDDF archive.

### Inferred transition point

- Historical tipping signal: historical evidence suggests the main break occurs once MC-style constraint burden reaches roughly 3 simultaneous requirements.
- Operational reading: generation quality remains acceptable, but compliance deteriorates quickly once multiple hard constraints stack up.
- Caveat: tipping point is inferred from prior benchmark patterns, not estimated from a fresh ratio curve on matched rows.

## Uncertainty Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### Historical uncertainty

- Historical sample size signal: `4` examples per run.
- Uncertainty source: the saved matched rerun is tiny, so the inferred transition is directional only.
- Caveat: no bootstrap confidence interval was available without matched rerun rows.

## Failure Taxonomy

- Status: `available`
- Reason: Computed from SDDF archive.

- Heuristic structural failures: 0
- Heuristic fixable failures: 4
- Invalid outputs: 0
- Note: this taxonomy is heuristic and should be reviewed against task-specific failure labels.

## Quality Gate

- Status: `available`
- Reason: Computed from SDDF archive.

### Suggested gate

- accept SLM outputs on unconstrained or lightly constrained prompts
- apply validators or constrained decoding before accepting multi-constraint generations
- Caveat: gate thresholds are policy recommendations inferred from historical evidence, not learned from fresh matched supervision.

## Deployment Zones

- Status: `available`
- Reason: Computed from SDDF archive.

### Inferred deployment stance

- Likely SDDF stance: Hybrid or SLM-with-mitigation depending on constraint burden.
- Why: local SLMs are competitive on free-form generation, but constraint-heavy prompts benefit from a gate or escalation.
- Caveat: zone assignment is a benchmark-level recommendation and should be revalidated after reruns.

## Routing Policy

- Status: `available`
- Reason: Computed from SDDF archive.

### Suggested routing policy

- send simple prompts to the SLM path
- use constrained decoding for moderate constraint bundles
- escalate high-constraint prompts to an LLM path when exact compliance matters
- Caveat: this is a hand-authored routing rule from historical evidence, not a learned router threshold.

