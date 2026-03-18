# Part B - SDDF Analysis

- Benchmark: `text_generation`
- Run path: `c:\Users\riddh\OneDrive\Desktop\SLM use cases\text_generation\results\runs\combined_sddf_2shot`
- Interpretation note: sections marked `partial` are inference-augmented summaries derived from historical benchmark artifacts rather than fresh matched reruns.

## SDDF: Dominant Difficulty Dimension

- Status: `available`
- Reason: Computed from SDDF archive.

### Summary

- `|Gamma|`: 6 examples

## Difficulty Annotation + Binning

- Status: `available`
- Reason: Computed from SDDF archive.

### Bin Counts

- Bin `1` / `LLM`: 2 rows
- Bin `1` / `SLM`: 4 rows

## Matched SLM vs LLM Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### Pairs

- `phi3.5-mini-local` vs `gemini-2.5-flash-fresh` on `samples`: 2 matched examples
- `qwen2.5-3b-local` vs `gemini-2.5-flash-fresh` on `samples`: 2 matched examples

## Capability Curve + Tipping Point

- Status: `available`
- Reason: Computed from SDDF archive.

### phi3.5-mini-local vs gemini-2.5-flash-fresh

- Tipping point: `None`
- Plot file: `c:\Users\riddh\OneDrive\Desktop\SLM use cases\text_generation\results\runs\combined_sddf_2shot\sddf\reports\samples_phi3_5_mini_local_vs_gemini_2_5_flash_fresh.png`

![Capability curve](samples_phi3_5_mini_local_vs_gemini_2_5_flash_fresh.png)

### qwen2.5-3b-local vs gemini-2.5-flash-fresh

- Tipping point: `None`
- Plot file: `c:\Users\riddh\OneDrive\Desktop\SLM use cases\text_generation\results\runs\combined_sddf_2shot\sddf\reports\samples_qwen2_5_3b_local_vs_gemini_2_5_flash_fresh.png`

![Capability curve](samples_qwen2_5_3b_local_vs_gemini_2_5_flash_fresh.png)


## Uncertainty Analysis

- Status: `available`
- Reason: Computed from SDDF archive.

### phi3.5-mini-local vs gemini-2.5-flash-fresh

- Tipping median: `None`
- 95% CI: `None` to `None`

### qwen2.5-3b-local vs gemini-2.5-flash-fresh

- Tipping median: `None`
- 95% CI: `None` to `None`


## Failure Taxonomy

- Status: `available`
- Reason: Computed from SDDF archive.

- Heuristic structural failures: 0
- Heuristic fixable failures: 6
- Invalid outputs: 0
- Note: this taxonomy is heuristic and should be reviewed against task-specific failure labels.

## Quality Gate

- Status: `available`
- Reason: Computed from SDDF archive.

### phi3.5-mini-local vs gemini-2.5-flash-fresh


### qwen2.5-3b-local vs gemini-2.5-flash-fresh



## Deployment Zones

- Status: `available`
- Reason: Computed from SDDF archive.

### phi3.5-mini-local vs gemini-2.5-flash-fresh

- Bin `1` at difficulty `0.000` -> Zone `C`

### qwen2.5-3b-local vs gemini-2.5-flash-fresh

- Bin `1` at difficulty `0.000` -> Zone `C`


## Routing Policy

- Status: `available`
- Reason: Computed from SDDF archive.

### phi3.5-mini-local vs gemini-2.5-flash-fresh

- No routing threshold learned.

### qwen2.5-3b-local vs gemini-2.5-flash-fresh

- No routing threshold learned.


