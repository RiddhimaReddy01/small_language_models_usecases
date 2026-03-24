# Component Learning Status Report

**Date**: 2026-03-19
**Status**: Analysis Complete - Awaiting Ground Truth Clarification

---

## Summary

I've analyzed the framework to determine available ground truth for component learning. Here's what was found:

## Ground Truth Available in Benchmark

### In `outputs.jsonl` Files:
- **`valid` field**: Binary indicator (true/false) - indicates whether output passed validation checks
- **Validation checks**:
  - `non_empty`: Output is not empty
  - `parseable`: Output can be parsed per format rules
  - `has_expected_fields`: Required fields present

### Validity Statistics Across Tasks:
| Task | Sample Size | Failure Rate |
|------|-------------|--------------|
| Text Generation | 325 | 0.3% (1 sample) |
| Code Generation | 325 | 7.4% (24 samples) |
| Classification | 325 | 0.0% |
| Maths | 325 | 0.0% |
| Summarization | 325 | 0.0% |
| Retrieval Grounded | 325 | 0.0% |
| Instruction Following | 300 | 0.7% (2 samples) |
| Information Extraction | 300 | 0.0% |

---

## Component Learning Findings

### Current Implementation Issue

The analysis reveals that components have **insufficient variance for correlation analysis**:

- **R (reasoning depth)**: ✅ Per-sample, shows variance
- **Gamma (constraint count)**: ❌ Hard-coded per-task (constant within task)
- **Alpha (parametric dependence)**: ❌ Hard-coded per-task (constant within task)

### Correlation Analysis Results

**Only R shows any correlation with semantic failure:**
- Code Generation: r = +0.090 (weak, p = 0.107)
- Text Generation: r = -0.065 (weak, p = 0.244)

Other components cannot be correlated due to zero variance.

---

## Question: What Ground Truth to Use?

I found **two interpretations** of "official ground truths":

### Option 1: Use Current `valid` Field (Syntactic Validity)
- ✅ Available in all benchmark outputs
- ❌ Only checks format/parsing, not semantic correctness
- ❌ Mostly zeros (very low failure rates)
- **Impact**: Insufficient variance for meaningful component learning

### Option 2: Use External Ground Truth (Semantic Correctness)
- ❌ Not found in current benchmark structure
- Would need: Reference outputs, human labels, or official dataset annotations
- **Where to look**: Separate ground truth files, reference answer datasets, HuggingFace dataset annotations

---

## Recommendation

**I need clarification:**

1. **Which ground truth to use for component learning?**
   - The `valid` field (syntactic, low variance) currently in outputs.jsonl?
   - OR
   - External/official ground truth you referenced ("official ground truths for the datasets you used")?

2. **If external ground truth exists:**
   - Where are the official reference answers/labels stored?
   - What format (JSON, CSV, HuggingFace dataset)?
   - What metrics available (Pass@1, F1, exact match, human rating)?

3. **If using current `valid` field:**
   - Accept that component learning will have limited signal due to low failure rates?
   - Focus on Code Generation task (only 7.4% failures, only one with meaningful variance)?

---

## Files Created

- `src/analysis/component_learner.py` - Correlation analysis engine
- `component_learning_results.json` - Analysis output showing zero correlations for Gamma/Alpha

## Next Steps (Blocked)

1. Await clarification on ground truth source
2. If external ground truth exists: integrate into analysis
3. If using current `valid` field: modify Gamma/Alpha to be sample-specific for variance
4. Re-run component learning with proper ground truth signal

---

**Awaiting your guidance on Q1 from the earlier audit:**
> "Q1: Component Learning Ground Truth - didnt you download the official ground truths for eh datasets you used"

Should I be looking for a separate ground truth dataset, or should I use the `valid` field that's embedded in the benchmark outputs?
