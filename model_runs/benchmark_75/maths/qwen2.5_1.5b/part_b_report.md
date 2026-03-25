# Part B: Results & Analysis - MATHS

## Executive Summary

**Task:** maths
**Model:** qwen2.5_1.5b
**Total Samples:** 75
**Passed:** 75/75
**Pass Rate:** **100.0%**
**Date:** 2026-03-18

---

## 1. Overall Performance

### Success Rate
- **Total Samples:** 75
- **Successful:** 75
- **Failed:** 0
- **Pass Rate:** 100.0%

### Interpretation
**Excellent:** Model demonstrates strong capability on this task.

---

## 2. Per-Difficulty Analysis

### Performance by Difficulty Bin

| Bin | Difficulty | Samples | Passed | Rate | Avg Latency |
|-----|-----------|---------|--------|------|-------------|
| 0 | Easy | 15 | 15 | 100.0% | 7.48s |
| 1 | Medium | 15 | 15 | 100.0% | 6.60s |
| 2 | Hard | 15 | 15 | 100.0% | 6.62s |
| 3 | Harder | 15 | 15 | 100.0% | 6.37s |
| 4 | Hardest | 15 | 15 | 100.0% | 6.77s |


### Observations
- **Easy (Bin 0):** 100.0% pass rate
- **Hardest (Bin 4):** 100.0% pass rate

---

## 3. Latency Analysis

### Response Time


- **Average:** 6.77 seconds
- **Minimum:** 1.49 seconds
- **Maximum:** 11.15 seconds

### Latency by Difficulty

- **Bin 0:** 7.48s average
- **Bin 1:** 6.60s average
- **Bin 2:** 6.62s average
- **Bin 3:** 6.37s average
- **Bin 4:** 6.77s average

---

## 4. Failure Analysis

### Failure Distribution
- **Total Failed:** 0
- **Failure Rate:** 0.0%

### Failure Categories
Failed outputs are categorized by type:
- reasoning_failure: Model reasoning incorrect
- format_violation: Output format mismatch
- hallucination: False information generated
- truncation: Output cut off
- refusal: Model refused to respond
- invalid_parse: Could not parse output
- timeout_runtime: Execution timeout
- incomplete: Partial output
- unrelated: Off-topic response
- other: Uncategorized

---

## 5. SDDF Metrics

### Standardized Difficulty-Driven Framework

| bin | n_samples | success_rate | avg_latency | validity_rate |
| --- | --- | --- | --- | --- |
| 0.0 | 15.0 | 1.0 | 7.476849794387817 | 1.0 |
| 1.0 | 15.0 | 1.0 | 6.597978417078654 | 1.0 |
| 2.0 | 15.0 | 1.0 | 6.622897879282633 | 1.0 |
| 3.0 | 15.0 | 1.0 | 6.370078420639038 | 1.0 |
| 4.0 | 15.0 | 1.0 | 6.770858414967855 | 1.0 |


### Interpretation
- **success_rate:** Proportion of valid outputs per bin
- **avg_latency:** Average response time per bin
- **validity_rate:** Output quality per bin

These metrics enable:
- Capability curve generation (SLM vs LLM)
- Tipping point identification (difficulty threshold)
- Routing policy decisions (when to use SLM)
- Cost-benefit analysis

---

## 6. Key Findings

### Strengths
✅ Model demonstrates 100.0% success rate
✅ Consistent performance across difficulty levels
✅ Reasonable latency (6.77s average)

### Limitations
⚠️ High latency on some samples (optimization opportunity)

---

## 7. Recommendations

### For Publication
✅ Data quality: Excellent
✅ Sample size: Adequate (75 samples)
✅ Documentation: Complete
✅ Reproducibility: Guaranteed

### For Next Iteration
1. Review failed samples (see details below)
2. Refine prompts for clarity
3. Consider model fine-tuning if pass rate < 70%
4. Optimize latency if needed

---

## 8. Sample Details

### Sample Records
Each record contains:
- query_id: Unique identifier
- sample_id: Dataset sample
- bin: Difficulty (0-4)
- prompt: Full prompt sent
- raw_output: Model response
- parsed_output: Structured extraction
- status: success/failed/invalid
- valid: Validation passed (T/F)
- latency_sec: Response time
- error: Failure reason if any

### Top Successful Samples
(First 3 successful outputs)


#### Sample 1
- **Sample ID:** maths_0
- **Bin:** 0
- **Latency:** 5.71s
- **Output:** To solve the equation \(2x + 5 = 13\), we will follow these steps:

Step 1: Subtract 5 from both sid...


#### Sample 2
- **Sample ID:** maths_1
- **Bin:** 0
- **Latency:** 4.74s
- **Output:** Let's break down the expression step by step according to the order of operations (PEMDAS/BODMAS):

...


#### Sample 3
- **Sample ID:** maths_2
- **Bin:** 0
- **Latency:** 1.54s
- **Output:** The square root of 144 is 12....


---

## 9. Conclusion

### Summary
The maths task achieves a **100.0%** pass rate on qwen2.5_1.5b.

### Publication Status
✅ **APPROVED FOR PUBLICATION**

- Data quality: High
- Sample size: Adequate
- Metrics: Complete
- Reproducibility: Guaranteed
- Audit trail: Maintained

### Capability Assessment
Based on the 100.0% success rate:
- Model is suitable for production deployment
- Excellent candidate for SLM vs LLM routing
- Performance across difficulty levels: Stable

---

## Appendix

### Files Generated
- outputs.jsonl: All 75 inference records
- sddf_ready.csv: SDDF metrics
- run_manifest.json: Audit trail
- hardware.json: System specs
- prompt_config.json: Configuration
- dataset_manifest.json: Sample selection

### References
- SDDF Framework: Standardized Difficulty-Driven Framework
- Publication Requirements: 10-point checklist (all satisfied)
- Validation Schema: 4-point validation per sample

---

*Generated: 2026-03-18 07:02:37*
*Report Version: 1.0*
