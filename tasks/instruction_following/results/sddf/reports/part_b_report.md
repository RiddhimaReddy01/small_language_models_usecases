# Part B - SDDF Analysis

- Benchmark: `instruction_following`
- Run path: `instruction_following\results\results_detailed.json`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `available`
- Reason: Computed from SDDF archive.

### Summary

- `|Gamma|`: 15 examples

## Difficulty Annotation + Binning

- Status: `available`
- Reason: Computed from SDDF archive.

### Bin Counts

- Bin `nan` / `LLM`: 7 rows
- Bin `nan` / `SLM`: 8 rows

## Matched SLM vs LLM Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### Pairs

- `hf_api:meta-llama/Llama-3.2-1B-Instruct` vs `gemini-2.5-flash [BASELINE]` on `instruction_following`: 7 matched examples

## Capability Curve + Tipping Point

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash [BASELINE]

- Tipping point: `None`
- Tipping sensitivity: `{'0.90': None, '0.93': None, '0.95': None, '0.97': None}`
- Plot file: `instruction_following\results\sddf\reports\instruction_following_hf_api_meta_llama_llama_3_2_1b_instruct_vs_gemini_2_5_flash_baseline.png`

![Capability curve](instruction_following_hf_api_meta_llama_llama_3_2_1b_instruct_vs_gemini_2_5_flash_baseline.png)


## Uncertainty Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash [BASELINE]

- Tipping median: `None`
- 95% CI: `None` to `None`
- Threshold sweep: `{'0.90': None, '0.93': None, '0.95': None, '0.97': None}`


## Failure Taxonomy

- Status: `available`
- Reason: Computed from SDDF archive.

- Heuristic structural failures: 0
- Heuristic fixable failures: 15
- Invalid outputs: 0
- Validity note: partial or invalid runs should be excluded from strict cross-model comparison.
- Note: this taxonomy is heuristic and should be reviewed against task-specific failure labels.

## Quality Gate

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash [BASELINE]

- Max difficulty: `0.0`
- Gate precision: `1.0`
- Gate recall: `1.0`
- Evaluated precision: `1.0`
- Evaluated recall: `1.0`
- Evaluated F1: `1.0`


## Deployment Zones

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash [BASELINE]

- Bin `0` at difficulty `0.000` -> Zone `A`


## Routing Policy

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash [BASELINE]

- Suggested `SLM` threshold: difficulty <= `0.0`
- Suggested `SLM_WITH_GATE` threshold: difficulty <= `0.0`
- Suggested `LLM` threshold: difficulty > `0.0`


