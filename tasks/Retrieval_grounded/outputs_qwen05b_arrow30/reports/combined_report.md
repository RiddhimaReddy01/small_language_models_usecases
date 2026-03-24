# Part A - Benchmark Setup

- Benchmark: `retrieval_grounded`
- Run path: `Retrieval_grounded\outputs_qwen05b_arrow30`

## Task Definition

```json
{
  "task": "retrieval_grounded",
  "dataset": "squad"
}
```

## Dataset and Sampling

```json
{
  "num_questions": 30,
  "dataset_split": "validation"
}
```

## Experimental Setup

```json
{
  "config": {
    "dataset_name": "squad",
    "dataset_split": "validation",
    "num_questions": 30,
    "max_context_tokens": 300,
    "max_answer_tokens": 10,
    "models": [
      "Qwen/Qwen2.5-Coder-0.5B-Instruct"
    ],
    "temperature": 0.0,
    "top_p": 1.0,
    "max_new_tokens": 30,
    "do_sample": false,
    "device": "cpu",
    "output_dir": "Retrieval_grounded/outputs_qwen05b_arrow30",
    "save_per_model": true
  },
  "environment": {
    "platform": "Windows-11-10.0.26200-SP0",
    "python_version": "3.12.7",
    "cuda_available": false
  }
}
```

## Metrics

```json
{
  "Qwen/Qwen2.5-Coder-0.5B-Instruct": {
    "model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
    "capability": {
      "exact_match": 66.66666666666667,
      "f1_score": 71.25763125763125,
      "context_utilization_rate": 96.66666666666667,
      "answer_length_accuracy": 86.66666666666667
    },
    "reliability": {
      "hallucination_rate": 3.3333333333333335,
      "unsupported_answer_rate": 3.3333333333333335,
      "partial_answer_rate": 13.333333333333334
    },
    "operational": {
      "latency_ms": 5534.117009999075,
      "latency_p50_ms": 6442.271899999469,
      "latency_p95_ms": 8078.817800007528,
      "tokens_per_sec": 4.228316813273146,
      "output_tokens_total": 702,
      "input_tokens_avg": 196.83333333333334,
      "memory_mb": 0.0,
      "wall_time_sec": 166.3784999847412,
      "questions": 30
    }
  }
}
```

## Raw Benchmark Results

```json
{
  "prediction_files": [
    "C:\\Users\\riddh\\OneDrive\\Desktop\\SLM use cases\\Retrieval_grounded\\outputs_qwen05b_arrow30\\predictions\\predictions_Qwen_Qwen2.5-Coder-0.5B-Instruct.json"
  ],
  "example_count_per_prediction_file": 30
}
```

# Part B - SDDF Analysis

- Benchmark: `retrieval_grounded`
- Run path: `Retrieval_grounded\outputs_qwen05b_arrow30`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred dominant dimension

- Inferred dominant difficulty dimension: `n_in`
- Basis: historical retrieval-grounded QA performance is strongest when all required evidence is present in context, making context size and evidence localization the main burden.
- Caveat: inferred from historical task structure and aggregate benchmark behavior rather than recalculated from a fresh matched rerun.

## Difficulty Annotation + Binning

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred binning rule

- Low difficulty bucket: verbatim span extraction from short contexts
- Mid difficulty bucket: short factual answers requiring light paraphrase
- High difficulty bucket: paraphrastic or multi-hop reasoning across context
- Caveat: bins are historical workload strata, not newly recomputed row-level bins.

## Matched SLM vs LLM Analysis

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Historical comparison

- Saved retrieval run: `Qwen/Qwen2.5-Coder-0.5B-Instruct` reached `66.67` EM and `71.26` F1.
- Caveat: this comparison is aggregate and not example-matched, so it should not be treated as a strict paired test.

## Capability Curve + Tipping Point

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred transition point

- Historical tipping signal: historical evidence suggests the main degradation begins once the answer is no longer a direct span and paraphrasing or composition is required.
- Operational reading: RAG helps most when it reduces the task to copying from context; once synthesis is needed, higher-capability models help more.
- Caveat: tipping point is inferred from prior benchmark patterns, not estimated from a fresh ratio curve on matched rows.

## Uncertainty Analysis

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Historical uncertainty

- Historical sample size signal: `30` prediction examples per file.
- Uncertainty source: saved artifacts are single-model for some runs, so exact comparative uncertainty remains high.
- Caveat: no bootstrap confidence interval was available without matched rerun rows.

## Failure Taxonomy

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred failure modes

- partial answers when paraphrasing is needed
- unsupported answers when context does not map cleanly to output
- hallucinations when retrieval grounding is weak
- Caveat: taxonomy is inferred from benchmark-level failures and task design, not exhaustively labeled per example.

## Quality Gate

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Suggested gate

- accept SLM outputs when answer spans are short and context-grounded
- escalate no-answer, paraphrastic, or multi-hop cases
- Caveat: gate thresholds are policy recommendations inferred from historical evidence, not learned from fresh matched supervision.

## Size-First Decision Matrix

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred size-first decision matrix

- Likely matrix outcome: SLM-preferred for span-like RAG QA; hybrid for paraphrastic or compositional QA.
- Why: historical local results are strong on direct grounding but weaken as synthesis pressure increases.
- Caveat: this decision matrix is benchmark-level and should be revalidated after reruns.

## Two-Stage Routing Policy

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Two-Stage Routing Policy

- route direct span or short factual answers to the SLM path
- route paraphrastic, uncertain, or multi-hop questions to an LLM path
- Caveat: this is a hand-authored routing rule from historical evidence, not a learned router threshold.

