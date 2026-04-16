# Appendix G, H, K

## Appendix G. S3–SDDF Mapping

### G.1 Enterprise Use Case to Task-Family Mapping (UC1 to UC8)

| Use case | Task family | S3 score | S3 tier | Runtime tier | Routing decision |
|---|---|---:|---|---|---|
| UC1 | classification | 3.40 | Hybrid | LLM Only | LLM |
| UC2 | information_extraction | 2.60 | Pure SLM | Pure SLM | SLM |
| UC3 | classification | 2.67 | Pure SLM | LLM Only | LLM |
| UC4 | classification | 2.07 | Pure SLM | LLM Only | LLM |
| UC5 | code_generation | 3.27 | Hybrid | Hybrid | HYBRID |
| UC6 | classification | 4.27 | LLM Only | LLM Only | LLM |
| UC7 | summarization | 3.20 | Hybrid | LLM Only | LLM |
| UC8 | text_generation | 3.07 | LLM Only | Pure SLM | SLM |

### G.2 Task-Family Bridge Table (Smita `s3_sddf_bridge_*.csv`)

| Task family | S3 score | S3 tier | SDDF best SLM | SDDF coverage | SDDF avg capability | SDDF cap threshold | SDDF risk threshold | Agreement |
|---|---:|---|---|---:|---:|---:|---:|---|
| classification | 2.93 | Pure SLM | qwen2.5_3b | 0.0000 | 0.5635 | 0.75 | 0.20 | PARTIAL |
| code_generation | 3.40 | LLM Only | qwen2.5_0.5b | 0.6894 | 0.4842 | 0.55 | 0.40 | DISAGREE |
| information_extraction | 2.87 | Pure SLM | qwen2.5_7b | 0.0000 | 0.8005 | 0.75 | 0.25 | AGREE |
| instruction_following | 2.47 | Pure SLM | qwen2.5_3b | 0.0000 | 0.7126 | 0.70 | 0.30 | AGREE |
| maths | 2.87 | Pure SLM | qwen2.5_3b | 0.0000 | 0.6928 | 0.65 | 0.35 | AGREE |
| retrieval_grounded | 3.00 | Pure SLM | qwen2.5_3b | 0.2840 | 0.6114 | 0.70 | 0.30 | PARTIAL |
| summarization | 2.47 | Pure SLM | qwen2.5_0.5b | 0.7984 | 0.7261 | 0.65 | 0.35 | AGREE |
| text_generation | 2.53 | Pure SLM | qwen2.5_7b | 0.0000 | 0.6882 | 0.70 | 0.30 | AGREE |

### G.3 Seed-42 Bridge Decisions by Task Family (Riddhima `s3_sddf_bridge_seed42.json`)

| Task family | Models | Mean artifact_tau | Mean tau_route | Tier decisions observed |
|---|---:|---:|---:|---|
| classification | 3 | 0.3667 | 0.3667 | pure_slm:3 |
| code_generation | 3 | 0.2000 | 0.2000 | hybrid:3 |
| information_extraction | 3 | 0.1167 | 0.1167 | pure_slm:3 |
| instruction_following | 3 | 0.3000 | 0.3000 | pure_slm:3 |
| maths | 3 | 0.1167 | 0.1167 | hybrid:3 |
| retrieval_grounded | 3 | 0.3167 | 0.3167 | hybrid:3 |
| summarization | 3 | 0.5333 | 0.5333 | pure_slm:3 |
| text_generation | 3 | 0.4667 | 0.4667 | pure_slm:3 |

## Appendix H. Statistical Validation

### H.1 Cross-Framework Correlation and Tier Correctness (Section 8 summary)

| Statistic | Value |
|---|---:|
| Spearman corr(S3, C_m(d)) | -0.2664 |
| Spearman p-value (S3 vs C_m(d)) | 0.5237 |
| Spearman corr(S3, R_m(d)) | 0.2664 |
| Spearman p-value (S3 vs R_m(d)) | 0.5237 |
| Kendall tau-b corr(S3, C_m(d)) | -0.1612 |
| Kendall tau-b p-value (S3 vs C_m(d)) | 0.5952 |
| Tier matches | 3 |
| Underestimations | 4 |
| Overestimations | 1 |
| Convergence rate | 0.3750 |
| Decision accuracy | 0.5000 |

### H.2 Macro Metrics and Tradeoff Summary (Section 8 summary)

| System | Accuracy_macro | F1_macro | Failure_macro |
|---|---:|---:|---:|
| Runtime routing | 0.7857 | 0.7266 | 0.2143 |
| LLM-only baseline | 0.7857 | 0.7202 | 0.2143 |
| SLM-only baseline | 0.8095 | 0.7794 | 0.1905 |

| Tradeoff metric | Value |
|---|---:|
| Runtime mean P95 (ms) | 3381.65 |
| LLM-only mean P95 (ms) | 2111.18 |
| SLM-only mean P95 (ms) | 2799.64 |
| Runtime cost low mean (USD/mo) | 35848.54 |
| Runtime cost high mean (USD/mo) | 71766.88 |
| LLM-only cost low (USD/mo) | 50000.00 |
| LLM-only cost high (USD/mo) | 100000.00 |

### H.3 Validation/Test Run Coverage by Task Family (Riddhima SDDF v3 reports)

| Task family | Val runs | strict_feasible_max | fallback_min_violation | Test runs | Distinct seeds in test |
|---|---:|---:|---:|---:|---:|
| classification | 15 | 10 | 5 | 15 | 5 |
| code_generation | 15 | 5 | 10 | 15 | 5 |
| information_extraction | 15 | 10 | 5 | 15 | 5 |
| instruction_following | 15 | 15 | 0 | 15 | 5 |
| maths | 15 | 5 | 10 | 15 | 5 |
| retrieval_grounded | 3 | 3 | 0 | 3 | 1 |
| summarization | 3 | 3 | 0 | 3 | 1 |
| text_generation | 3 | 3 | 0 | 3 | 1 |

## Appendix K. Failure Taxonomy

### K.1 Failure Categories and Harm/Risk Weights (`error_taxonomy_by_task_model.json`)

| Failure type | Semantic risk weight | Failure harm weight |
|---|---:|---:|
| answer_mismatch | 0.850 | 0.800 |
| arithmetic_error | 0.900 | 0.800 |
| constraint_violation | 0.700 | 0.700 |
| empty_output | 0.100 | 0.100 |
| format_error | 0.400 | 0.400 |
| incomplete_output | 0.400 | 0.350 |
| logic_error | 0.950 | 0.850 |
| low_relevance | 0.600 | 0.700 |
| missing_field | 0.450 | 0.450 |
| missing_ground_truth | 0.300 | 0.300 |
| no_answer | 0.200 | 0.200 |
| quality_failure | 0.500 | 0.600 |
| timeout_runtime | 0.100 | 0.100 |
| wrong_label | 0.800 | 0.800 |

### K.2 Error Taxonomy by Task and Model (`error_taxonomy_by_task_model.csv`)

| Task | Model | n_rows | n_failures | failure_rate | avg_semantic_risk | avg_failure_harm | top_failure_1 | top_failure_1_count |
|---|---|---:|---:|---:|---:|---:|---|---:|
| classification | groq:llama-3.3-70b-versatile | 20 | 0 | 0.0000 | 0.0000 | 0.0000 |  | 0 |
| classification | phi3:mini | 20 | 0 | 0.0000 | 0.0000 | 0.0000 |  | 0 |
| classification | qwen2.5:1.5b | 20 | 3 | 0.1500 | 0.0960 | 0.6400 | wrong_label | 3 |
| classification | tinyllama:1.1b | 20 | 2 | 0.1000 | 0.0640 | 0.6400 | wrong_label | 2 |
| code_generation | groq:llama-3.3-70b-versatile | 20 | 0 | 0.0000 | 0.0000 | 0.0000 |  | 0 |
| code_generation | phi3:mini | 20 | 5 | 0.2500 | 0.1371 | 0.5485 | logic_error | 3 |
| code_generation | qwen2.5:1.5b | 20 | 4 | 0.2000 | 0.1615 | 0.8075 | logic_error | 4 |
| code_generation | tinyllama:1.1b | 20 | 4 | 0.2000 | 0.1615 | 0.8075 | logic_error | 4 |
| information_extraction | groq:llama-3.3-70b-versatile | 20 | 0 | 0.0000 | 0.0000 | 0.0000 |  | 0 |
| information_extraction | phi3:mini | 20 | 1 | 0.0500 | 0.0101 | 0.2025 | missing_field | 1 |
| information_extraction | qwen2.5:1.5b | 20 | 1 | 0.0500 | 0.0101 | 0.2025 | missing_field | 1 |
| information_extraction | tinyllama:1.1b | 20 | 2 | 0.1000 | 0.0202 | 0.2025 | missing_field | 2 |
| instruction_following | groq:llama-3.3-70b-versatile | 20 | 1 | 0.0500 | 0.0245 | 0.4900 | constraint_violation | 1 |
| instruction_following | phi3:mini | 20 | 7 | 0.3500 | 0.1715 | 0.4900 | constraint_violation | 7 |
| instruction_following | qwen2.5:1.5b | 20 | 5 | 0.2500 | 0.1225 | 0.4900 | constraint_violation | 5 |
| instruction_following | tinyllama:1.1b | 20 | 10 | 0.5000 | 0.2450 | 0.4900 | constraint_violation | 10 |
| maths | groq:llama-3.3-70b-versatile | 20 | 2 | 0.1000 | 0.0720 | 0.7200 | arithmetic_error | 2 |
| maths | phi3:mini | 20 | 6 | 0.3000 | 0.2160 | 0.7200 | arithmetic_error | 6 |
| maths | qwen2.5:1.5b | 20 | 12 | 0.6000 | 0.4320 | 0.7200 | arithmetic_error | 12 |
| maths | tinyllama:1.1b | 20 | 18 | 0.9000 | 0.6480 | 0.7200 | arithmetic_error | 18 |
| retrieval_grounded | groq:llama-3.3-70b-versatile | 20 | 0 | 0.0000 | 0.0000 | 0.0000 |  | 0 |
| retrieval_grounded | phi3:mini | 20 | 3 | 0.1500 | 0.0700 | 0.4667 | answer_mismatch | 2 |
| retrieval_grounded | qwen2.5:1.5b | 20 | 0 | 0.0000 | 0.0000 | 0.0000 |  | 0 |
| retrieval_grounded | tinyllama:1.1b | 20 | 4 | 0.2000 | 0.1040 | 0.5200 | answer_mismatch | 3 |
| summarization | groq:llama-3.3-70b-versatile | 20 | 1 | 0.0500 | 0.0210 | 0.4200 | low_relevance | 1 |
| summarization | phi3:mini | 20 | 2 | 0.1000 | 0.0420 | 0.4200 | low_relevance | 2 |
| summarization | qwen2.5:1.5b | 20 | 7 | 0.3500 | 0.1470 | 0.4200 | low_relevance | 7 |
| summarization | tinyllama:1.1b | 20 | 5 | 0.2500 | 0.1050 | 0.4200 | low_relevance | 5 |
| text_generation | groq:llama-3.3-70b-versatile | 19 | 1 | 0.0526 | 0.0221 | 0.4200 | low_relevance | 1 |
| text_generation | phi3:mini | 19 | 5 | 0.2632 | 0.1105 | 0.4200 | low_relevance | 5 |
| text_generation | qwen2.5:1.5b | 19 | 10 | 0.5263 | 0.2211 | 0.4200 | low_relevance | 10 |
| text_generation | tinyllama:1.1b | 19 | 4 | 0.2105 | 0.0884 | 0.4200 | low_relevance | 4 |

### K.3 Raw-Output ERROR Rows by Enterprise Use Case (Smita `data/raw_outputs`)

| Raw file | total_rows | error_rows (`pred_label=ERROR`) | error_rate |
|---|---:|---:|---:|
| uc1_raw_20260303_165536.csv | 630 | 0 | 0.0000 |
| uc2_raw_20260310_112624.csv | 630 | 0 | 0.0000 |
| uc3_raw_20260311_092607.csv | 630 | 0 | 0.0000 |
| uc4_raw_20260303_202703.csv | 630 | 0 | 0.0000 |
| uc5_raw_20260413_110810.csv | 630 | 0 | 0.0000 |
| uc6_raw_20260310_135253.csv | 632 | 2 | 0.0032 |
| uc7_raw_20260413_113202.csv | 630 | 0 | 0.0000 |
| uc8_raw_20260311_120455.csv | 669 | 0 | 0.0000 |

### K.4 Aggregate Failure Typology from Section 8 Summary

| Category | Count |
|---|---:|
| hard_failure | 108 |
| wrong_prediction | 15 |
| none | 21 |

## Source Files Used

- `docs/section8_outputs/section8_uc_evaluation_table_enhanced.csv`
- `repos/SLM_Research_Project/evaluation/s3_sddf_bridge_20260413_234328.csv`
- `repos/small_language_models_usecases/model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/s3_sddf_bridge_seed42.json`
- `docs/section8_outputs/section8_summary_enhanced.json`
- `repos/small_language_models_usecases/model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/val_evaluation_report.json`
- `repos/small_language_models_usecases/model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/test_evaluation_report.json`
- `repos/small_language_models_usecases/model_runs/benchmarking/error_taxonomy/error_taxonomy_by_task_model.csv`
- `repos/small_language_models_usecases/model_runs/benchmarking/error_taxonomy/error_taxonomy_by_task_model.json`
- `repos/SLM_Research_Project/data/raw_outputs/uc*_raw_*.csv`
