# Part B - SDDF Analysis

- Benchmark: `maths`
- Run path: `maths\benchmark_metrics.json`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred dominant dimension

- Inferred dominant difficulty dimension: `R_hat`
- Basis: historical maths performance is dominated by reasoning depth, intermediate-state tracking, and multi-step dependency chains.
- Caveat: inferred from historical task structure and aggregate benchmark behavior rather than recalculated from a fresh matched rerun.

## Difficulty Annotation + Binning

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred binning rule

- Low difficulty bucket: single-step arithmetic or direct conversion
- Mid difficulty bucket: short reasoning chains with limited intermediate state
- High difficulty bucket: multi-step word problems with dependent calculations
- Caveat: bins are historical workload strata, not newly recomputed row-level bins.

## Matched SLM vs LLM Analysis

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Historical comparison

- Historical top model on primary metric: `gemini_2_5_flash_real` at `38.3%` final-answer accuracy.
- Best spread observed in saved artifacts: `gemini_2_5_flash_real` exceeds `mistral_7b` by `28.3` points.
- Caveat: this comparison is aggregate and not example-matched, so it should not be treated as a strict paired test.

## Capability Curve + Tipping Point

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred transition point

- Historical tipping signal: historical evidence suggests a clear break once tasks require more than one straightforward reasoning step.
- Operational reading: simple arithmetic remains viable locally, but multi-step reasoning pushes quality toward stronger models quickly.
- Caveat: tipping point is inferred from prior benchmark patterns, not estimated from a fresh ratio curve on matched rows.

## Uncertainty Analysis

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Historical uncertainty

- Historical sample size signal: aggregate-only artifacts were available.
- Uncertainty source: sample sizes vary by model and some historical runs mix datasets, so inferred thresholds are moderate-confidence only.
- Caveat: no bootstrap confidence interval was available without matched rerun rows.

## Failure Taxonomy

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred failure modes

- incorrect intermediate reasoning despite well-formed output
- confident wrong answers on multi-step problems
- low perturbation robustness on paraphrased questions
- Caveat: taxonomy is inferred from benchmark-level failures and task design, not exhaustively labeled per example.

## Quality Gate

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Suggested gate

- accept SLM outputs only for simple arithmetic-like prompts or when a verifier agrees
- escalate multi-step word problems and variable-dependent reasoning tasks
- Caveat: gate thresholds are policy recommendations inferred from historical evidence, not learned from fresh matched supervision.

## Deployment Zones

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred deployment stance

- Likely SDDF stance: LLM-preferred for general mathematical reasoning, with narrow SLM carve-outs.
- Why: historical accuracy and robustness both deteriorate materially once reasoning depth increases.
- Caveat: zone assignment is a benchmark-level recommendation and should be revalidated after reruns.

## Routing Policy

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Suggested routing policy

- route simple arithmetic and direct conversions to SLMs if cost matters
- route multi-step reasoning tasks to LLMs or verification-heavy workflows
- Caveat: this is a hand-authored routing rule from historical evidence, not a learned router threshold.

