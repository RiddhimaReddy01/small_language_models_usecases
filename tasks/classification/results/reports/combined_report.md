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

# Part B - SDDF Analysis

- Benchmark: `classification`
- Run path: `classification\results`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred dominant dimension

- Inferred dominant difficulty dimension: `H`
- Basis: classification difficulty is dominated by lexical and semantic ambiguity, which aligns with entropy-style label uncertainty rather than structural output constraints.
- Caveat: inferred from historical task structure and aggregate benchmark behavior rather than recalculated from a fresh matched rerun.

## Difficulty Annotation + Binning

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred binning rule

- Low difficulty bucket: clear sentiment or topic labels with direct lexical cues
- Mid difficulty bucket: domain or emotion labels requiring mild pragmatic inference
- High difficulty bucket: sarcasm, adjacent emotions, and ambiguous pragmatic cues
- Caveat: bins are historical workload strata, not newly recomputed row-level bins.

## Matched SLM vs LLM Analysis

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Historical comparison

- Historical classification evidence suggests SLMs stay competitive on low-ambiguity labels and degrade on sarcasm, adjacent emotions, and pragmatic ambiguity.
- The saved artifact here is single-model, so this section stays benchmark-level rather than paired.
- Caveat: this comparison is aggregate and not example-matched, so it should not be treated as a strict paired test.

## Capability Curve + Tipping Point

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred transition point

- Historical tipping signal: historical evidence places the main break around IC≈2-style ambiguity, where pragmatic interpretation becomes necessary.
- Operational reading: simple single-hop labels stay SLM-friendly; ambiguity-heavy examples are better treated as escalation candidates.
- Caveat: tipping point is inferred from prior benchmark patterns, not estimated from a fresh ratio curve on matched rows.

## Uncertainty Analysis

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Historical uncertainty

- Historical sample size signal: latest saved run had `2` rows.
- Uncertainty source: saved classification runs are small and heterogeneous, so confidence around the inferred break is low-to-moderate.
- Caveat: no bootstrap confidence interval was available without matched rerun rows.

## Failure Taxonomy

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred failure modes

- semantic ambiguity between neighboring labels
- sarcasm or irony that flips surface polarity
- invalid label generation when the prompt-response contract is weak
- Caveat: taxonomy is inferred from benchmark-level failures and task design, not exhaustively labeled per example.

## Quality Gate

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Suggested gate

- accept SLM outputs when the label is in-vocabulary and confidence is high
- escalate examples containing ambiguity markers, sarcasm cues, or low-confidence normalization
- Caveat: gate thresholds are policy recommendations inferred from historical evidence, not learned from fresh matched supervision.

## Size-First Decision Matrix

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred size-first decision matrix

- Likely matrix outcome: SLM-preferred for routine classification, with escalation on ambiguity-heavy slices.
- Why: historical results show strong low-cost performance on easy labels, but notable degradation on ambiguity-heavy subsets.
- Caveat: this decision matrix is benchmark-level and should be revalidated after reruns.

## Two-Stage Routing Policy

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Two-Stage Routing Policy

- route clear single-label examples to the SLM path
- route ambiguous or pragmatic examples to an LLM or human review path
- Caveat: this is a hand-authored routing rule from historical evidence, not a learned router threshold.

