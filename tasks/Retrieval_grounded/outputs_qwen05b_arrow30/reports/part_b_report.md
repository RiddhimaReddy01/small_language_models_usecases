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

