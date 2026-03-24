# Part B - SDDF Analysis

- Benchmark: `retrieval_grounded`
- Run path: `Retrieval_grounded\outputs_hf_llama1b_smoke`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `available`
- Reason: Computed from SDDF archive.

### Summary

- `n_in`: 12 examples

## Difficulty Annotation + Binning

- Status: `available`
- Reason: Computed from SDDF archive.

### Bin Counts

- Bin `nan` / `LLM`: 6 rows
- Bin `nan` / `SLM`: 6 rows

## Matched SLM vs LLM Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### Pairs

- `hf_api:meta-llama/Llama-3.2-1B-Instruct` vs `gemini/gemini-3.1-flash-lite-preview` on `retrieval_grounded`: 6 matched examples

## Capability Curve + Tipping Point

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini/gemini-3.1-flash-lite-preview

- Tipping point: `None`
- Tipping sensitivity: `{'0.90': None, '0.93': None, '0.95': None, '0.97': None}`
- Plot file: `Retrieval_grounded\outputs_hf_llama1b_smoke\sddf\reports\retrieval_grounded_hf_api_meta_llama_llama_3_2_1b_instruct_vs_gemini_gemini_3_1_flash_lite_preview.png`

![Capability curve](retrieval_grounded_hf_api_meta_llama_llama_3_2_1b_instruct_vs_gemini_gemini_3_1_flash_lite_preview.png)


## Uncertainty Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini/gemini-3.1-flash-lite-preview

- Tipping median: `None`
- 95% CI: `None` to `None`
- Threshold sweep: `{'0.90': None, '0.93': None, '0.95': None, '0.97': None}`


## Failure Taxonomy

- Status: `available`
- Reason: Computed from SDDF archive.

- Heuristic structural failures: 0
- Heuristic fixable failures: 12
- Invalid outputs: 0
- Validity note: partial or invalid runs should be excluded from strict cross-model comparison.
- Note: this taxonomy is heuristic and should be reviewed against task-specific failure labels.

## Quality Gate

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini/gemini-3.1-flash-lite-preview



## Deployment Zones

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini/gemini-3.1-flash-lite-preview

- Bin `0` at difficulty `31.000` -> Zone `C`


## Routing Policy

- Status: `available`
- Reason: Computed from SDDF archive.

### hf_api:meta-llama/Llama-3.2-1B-Instruct vs gemini/gemini-3.1-flash-lite-preview

- No routing threshold learned.


