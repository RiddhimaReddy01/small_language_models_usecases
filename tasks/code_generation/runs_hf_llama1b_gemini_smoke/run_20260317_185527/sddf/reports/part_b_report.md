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

### Pairs

- `meta-llama/Llama-3.2-1B-Instruct` vs `gemini-2.5-flash` on `HumanEval`: 1 matched examples
- `meta-llama/Llama-3.2-1B-Instruct` vs `gemini-2.5-flash` on `MBPP`: 1 matched examples

## Capability Curve + Tipping Point

- Status: `available`
- Reason: Computed from SDDF archive.

### meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash

- Tipping point: `None`
- Tipping sensitivity: `{'0.90': None, '0.93': None, '0.95': None, '0.97': None}`
- Plot file: `code_generation\runs_hf_llama1b_gemini_smoke\run_20260317_185527\sddf\reports\humaneval_meta_llama_llama_3_2_1b_instruct_vs_gemini_2_5_flash.png`

![Capability curve](humaneval_meta_llama_llama_3_2_1b_instruct_vs_gemini_2_5_flash.png)

### meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash

- Tipping point: `None`
- Tipping sensitivity: `{'0.90': None, '0.93': None, '0.95': None, '0.97': None}`
- Plot file: `code_generation\runs_hf_llama1b_gemini_smoke\run_20260317_185527\sddf\reports\mbpp_meta_llama_llama_3_2_1b_instruct_vs_gemini_2_5_flash.png`

![Capability curve](mbpp_meta_llama_llama_3_2_1b_instruct_vs_gemini_2_5_flash.png)


## Uncertainty Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash

- Tipping median: `None`
- 95% CI: `None` to `None`
- Threshold sweep: `{'0.90': None, '0.93': None, '0.95': None, '0.97': None}`

### meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash

- Tipping median: `None`
- 95% CI: `None` to `None`
- Threshold sweep: `{'0.90': None, '0.93': None, '0.95': None, '0.97': None}`


## Failure Taxonomy

- Status: `available`
- Reason: Computed from SDDF archive.

- Heuristic structural failures: 0
- Heuristic fixable failures: 4
- Invalid outputs: 2
- Validity note: partial or invalid runs should be excluded from strict cross-model comparison.
- Note: this taxonomy is heuristic and should be reviewed against task-specific failure labels.

## Quality Gate

- Status: `available`
- Reason: Computed from SDDF archive.

### meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash


### meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash



## Size-First Decision Matrix

- Status: `available`
- Reason: Computed from SDDF archive.

### meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash

- Bin `0` at difficulty `0.000` contributes to the tau-based threshold evidence.

### meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash

- Bin `0` at difficulty `0.000` contributes to the tau-based threshold evidence.


## Two-Stage Routing Policy

- Status: `available`
- Reason: Computed from SDDF archive.

### meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash

- No routing threshold learned.

### meta-llama/Llama-3.2-1B-Instruct vs gemini-2.5-flash

- No routing threshold learned.


