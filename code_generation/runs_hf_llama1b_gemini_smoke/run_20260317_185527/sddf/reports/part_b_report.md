# Part B - SDDF Analysis

- Benchmark: `code_generation`
- Run path: `code_generation\runs_hf_llama1b_gemini_smoke\run_20260317_185527`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `available`
- Reason: Computed from SDDF archive.

### Summary

- `R_hat`: 4 examples

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

- Historical code-generation results suggest API baselines retain an advantage on non-trivial algorithmic tasks, while local SLMs only pass trivial tasks reliably.
- Because the saved artifacts are aggregate, this remains a directional comparison rather than a paired one.
- Caveat: this comparison is aggregate and not example-matched, so it should not be treated as a strict paired test.

## Capability Curve + Tipping Point

- Status: `available`
- Reason: Computed from SDDF archive.

### Inferred transition point

- Historical tipping signal: historical evidence suggests a sharp break once tasks move beyond trivial single-loop logic into algorithmic reasoning.
- Operational reading: local SLMs can sometimes handle trivial tasks, but non-trivial algorithms are still a strong escalation signal.
- Caveat: tipping point is inferred from prior benchmark patterns, not estimated from a fresh ratio curve on matched rows.

## Uncertainty Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### Historical uncertainty

- Historical sample size signal: `4` task results were saved.
- Uncertainty source: completed-task counts are unstable and some local runs were incomplete, so exact thresholds should be treated cautiously.
- Caveat: no bootstrap confidence interval was available without matched rerun rows.

## Failure Taxonomy

- Status: `available`
- Reason: Computed from SDDF archive.

- Heuristic structural failures: 0
- Heuristic fixable failures: 4
- Invalid outputs: 2
- Note: this taxonomy is heuristic and should be reviewed against task-specific failure labels.

## Quality Gate

- Status: `available`
- Reason: Computed from SDDF archive.

### Suggested gate

- accept SLM outputs only on trivial, low-reasoning tasks with passing tests
- escalate recursive, multi-structure, or benchmark-hard tasks by default
- Caveat: gate thresholds are policy recommendations inferred from historical evidence, not learned from fresh matched supervision.

## Deployment Zones

- Status: `available`
- Reason: Computed from SDDF archive.

### Inferred deployment stance

- Likely SDDF stance: LLM-preferred except for trivial code generation slices.
- Why: historical pass rates show the primary bottleneck is reasoning depth, not formatting.
- Caveat: zone assignment is a benchmark-level recommendation and should be revalidated after reruns.

## Routing Policy

- Status: `available`
- Reason: Computed from SDDF archive.

### Suggested routing policy

- reserve SLMs for simple transformation or boilerplate tasks
- route algorithmic or benchmark-hard tasks directly to stronger models
- Caveat: this is a hand-authored routing rule from historical evidence, not a learned router threshold.

