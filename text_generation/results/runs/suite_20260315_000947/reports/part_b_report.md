# Part B - SDDF Analysis

- Benchmark: `text_generation`
- Run path: `text_generation\results\runs\suite_20260315_000947`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred dominant dimension

- Inferred dominant difficulty dimension: `|Gamma|`
- Basis: historical text-generation failures cluster around simultaneous output constraints rather than basic generation ability.
- Caveat: inferred from historical task structure and aggregate benchmark behavior rather than recalculated from a fresh matched rerun.

## Difficulty Annotation + Binning

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred binning rule

- Low difficulty bucket: open-ended generation with minimal formatting requirements
- Mid difficulty bucket: single format or tone constraints
- High difficulty bucket: exact length, multi-constraint, or strict formatting demands
- Caveat: bins are historical workload strata, not newly recomputed row-level bins.

## Matched SLM vs LLM Analysis

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Historical comparison

- Historical text-generation evidence indicates local SLMs are competitive on open-ended generation quality but fall behind on heavy multi-constraint adherence.
- Caveat: this comparison is aggregate and not example-matched, so it should not be treated as a strict paired test.

## Capability Curve + Tipping Point

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred transition point

- Historical tipping signal: historical evidence suggests the main break occurs once MC-style constraint burden reaches roughly 3 simultaneous requirements.
- Operational reading: generation quality remains acceptable, but compliance deteriorates quickly once multiple hard constraints stack up.
- Caveat: tipping point is inferred from prior benchmark patterns, not estimated from a fresh ratio curve on matched rows.

## Uncertainty Analysis

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Historical uncertainty

- Historical sample size signal: `15` examples per run.
- Uncertainty source: the saved matched rerun is tiny, so the inferred transition is directional only.
- Caveat: no bootstrap confidence interval was available without matched rerun rows.

## Failure Taxonomy

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred failure modes

- exact length non-compliance
- constraint collisions across format, keyword, and style requirements
- overgeneration despite otherwise fluent output
- Caveat: taxonomy is inferred from benchmark-level failures and task design, not exhaustively labeled per example.

## Quality Gate

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Suggested gate

- accept SLM outputs on unconstrained or lightly constrained prompts
- apply validators or constrained decoding before accepting multi-constraint generations
- Caveat: gate thresholds are policy recommendations inferred from historical evidence, not learned from fresh matched supervision.

## Deployment Zones

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Inferred deployment stance

- Likely SDDF stance: Hybrid or SLM-with-mitigation depending on constraint burden.
- Why: local SLMs are competitive on free-form generation, but constraint-heavy prompts benefit from a gate or escalation.
- Caveat: zone assignment is a benchmark-level recommendation and should be revalidated after reruns.

## Routing Policy

- Status: `partial`
- Reason: Inferred from historical benchmark artifacts; no SDDF archive was available for direct computation.

### Suggested routing policy

- send simple prompts to the SLM path
- use constrained decoding for moderate constraint bundles
- escalate high-constraint prompts to an LLM path when exact compliance matters
- Caveat: this is a hand-authored routing rule from historical evidence, not a learned router threshold.

