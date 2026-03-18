# Part B - SDDF Analysis

- Benchmark: `code_generation`
- Run path: `code_generation\archive\runs\run_20260314_023126`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred dominant dimension

- Inferred dominant difficulty dimension: `R_hat`
- Basis: historical code-generation failures track algorithmic reasoning depth and state tracking more than formatting or syntax alone.
- Caveat: inferred from historical task structure and aggregate benchmark behavior rather than recalculated from a fresh matched rerun.

## Difficulty Annotation + Binning

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred binning rule

- Low difficulty bucket: single-loop or direct-map programming tasks
- Mid difficulty bucket: moderate control flow with limited state
- High difficulty bucket: algorithmic problems requiring recursion, stacks, or multi-step decomposition
- Caveat: bins are historical workload strata, not newly recomputed row-level bins.

## Matched SLM vs LLM Analysis

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Historical comparison

- Historical code-generation results suggest API baselines retain an advantage on non-trivial algorithmic tasks, while local SLMs only pass trivial tasks reliably.
- Because the saved artifacts are aggregate, this remains a directional comparison rather than a paired one.
- Caveat: this comparison is aggregate and not example-matched, so it should not be treated as a strict paired test.

## Capability Curve + Tipping Point

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred transition point

- Historical tipping signal: historical evidence suggests a sharp break once tasks move beyond trivial single-loop logic into algorithmic reasoning.
- Operational reading: local SLMs can sometimes handle trivial tasks, but non-trivial algorithms are still a strong escalation signal.
- Caveat: tipping point is inferred from prior benchmark patterns, not estimated from a fresh ratio curve on matched rows.

## Uncertainty Analysis

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Historical uncertainty

- Historical sample size signal: `2` task results were saved.
- Uncertainty source: completed-task counts are unstable and some local runs were incomplete, so exact thresholds should be treated cautiously.
- Caveat: no bootstrap confidence interval was available without matched rerun rows.

## Failure Taxonomy

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred failure modes

- algorithmic reasoning failure despite syntactic validity
- incorrect API or library usage
- state-tracking errors in multi-step solutions
- Caveat: taxonomy is inferred from benchmark-level failures and task design, not exhaustively labeled per example.

## Quality Gate

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Suggested gate

- accept SLM outputs only on trivial, low-reasoning tasks with passing tests
- escalate recursive, multi-structure, or benchmark-hard tasks by default
- Caveat: gate thresholds are policy recommendations inferred from historical evidence, not learned from fresh matched supervision.

## Deployment Zones

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred deployment stance

- Likely SDDF stance: LLM-preferred except for trivial code generation slices.
- Why: historical pass rates show the primary bottleneck is reasoning depth, not formatting.
- Caveat: zone assignment is a benchmark-level recommendation and should be revalidated after reruns.

## Routing Policy

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Suggested routing policy

- reserve SLMs for simple transformation or boilerplate tasks
- route algorithmic or benchmark-hard tasks directly to stronger models
- Caveat: this is a hand-authored routing rule from historical evidence, not a learned router threshold.

