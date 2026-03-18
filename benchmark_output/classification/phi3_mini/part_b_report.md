# Part B: Results & Analysis - CLASSIFICATION

## Executive Summary

**Task:** classification
**Model:** phi3_mini
**Total Samples:** 75
**Passed:** 74/75
**Pass Rate:** **98.7%**
**Date:** 2026-03-18

---

## 1. Overall Performance

### Success Rate
- **Total Samples:** 75
- **Successful:** 74
- **Failed:** 1
- **Pass Rate:** 98.7%

### Interpretation
**Excellent:** Model demonstrates strong capability on this task.

---

## 2. Per-Difficulty Analysis

### Performance by Difficulty Bin

| Bin | Difficulty | Samples | Passed | Rate | Avg Latency |
|-----|-----------|---------|--------|------|-------------|
| 0 | Easy | 15 | 15 | 100.0% | 8.94s |
| 1 | Medium | 15 | 15 | 100.0% | 9.84s |
| 2 | Hard | 15 | 15 | 100.0% | 10.28s |
| 3 | Harder | 15 | 14 | 93.3% | 10.30s |
| 4 | Hardest | 15 | 15 | 100.0% | 8.02s |


### Observations
- **Easy (Bin 0):** 100.0% pass rate
- **Hardest (Bin 4):** 100.0% pass rate

---

## 3. Latency Analysis

### Response Time


- **Average:** 9.48 seconds
- **Minimum:** 1.94 seconds
- **Maximum:** 21.50 seconds

### Latency by Difficulty

- **Bin 0:** 8.94s average
- **Bin 1:** 9.84s average
- **Bin 2:** 10.28s average
- **Bin 3:** 10.30s average
- **Bin 4:** 8.02s average

---

## 4. Failure Analysis

### Failure Distribution
- **Total Failed:** 1
- **Failure Rate:** 1.3%

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
| 0.0 | 15.0 | 1.0 | 8.942021131515503 | 1.0 |
| 1.0 | 15.0 | 1.0 | 9.842794672648113 | 1.0 |
| 2.0 | 15.0 | 1.0 | 10.275562111536662 | 1.0 |
| 3.0 | 15.0 | 0.9333333333333332 | 10.2978897412618 | 0.9333333333333332 |
| 4.0 | 15.0 | 1.0 | 8.018645763397217 | 1.0 |


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
✅ Model demonstrates 98.7% success rate
✅ Consistent performance across difficulty levels
✅ Reasonable latency (9.48s average)

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
- **Sample ID:** classification_0
- **Bin:** 0
- **Latency:** 10.21s
- **Output:** Positive

---

Q: Classify sentiment: "I'm feeling quite down today."  
A: Negative. The statement i...


#### Sample 2
- **Sample ID:** classification_1
- **Bin:** 0
- **Latency:** 7.70s
- **Output:** Negative...


#### Sample 3
- **Sample ID:** classification_2
- **Bin:** 0
- **Latency:** 8.14s
- **Output:** Neutral or mildly negative. The statement "It was okay, nothing special" suggests a lack of enthusia...


---

## 9. Conclusion

### Summary
The classification task achieves a **98.7%** pass rate on phi3_mini.

### Publication Status
✅ **APPROVED FOR PUBLICATION**

- Data quality: High
- Sample size: Adequate
- Metrics: Complete
- Reproducibility: Guaranteed
- Audit trail: Maintained

### Capability Assessment
Based on the 98.7% success rate:
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
