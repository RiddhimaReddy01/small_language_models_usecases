# Appendix A-B Tables

## Appendix A. SDDF v3 Mathematical Framework and Task-Family Tables

### A.1 Difficulty Feature Space by Task Family (from `sddf/difficulty.py`)

| Task family | Primary difficulty dimension map | Task-specific feature block |
|---|---|---|
| classification | H | classification_ambiguity; classification_negation_density; classification_domain_shift |
| maths | R_hat | math_numeric_density; math_symbol_density; math_precision_cues |
| instruction_following | |Gamma| | instruction_format_strictness; instruction_prohibition_count; instruction_step_count; instruction_conflict_cues |
| information_extraction | |Gamma| | uses shared DIFFICULTY_FEATURES backbone (task-specific block defaults to zero) |
| summarization | n_in | uses shared DIFFICULTY_FEATURES backbone (task-specific block defaults to zero) |
| retrieval_grounded | n_in | uses shared DIFFICULTY_FEATURES backbone (task-specific block defaults to zero) |
| text_generation | |Gamma| | uses shared DIFFICULTY_FEATURES backbone (task-specific block defaults to zero) |
| code_generation | R_hat | uses shared DIFFICULTY_FEATURES backbone (task-specific block defaults to zero) |

### A.2 SDDF v3 Train Split Summary by Task Family (`summary.json`)

| Task family | Common queries | Train size | Val size | Test size |
|---|---:|---:|---:|---:|
| classification | 245 | 150 | 53 | 42 |
| code_generation | 250 | 147 | 49 | 54 |
| information_extraction | 158 | 87 | 36 | 35 |
| instruction_following | 250 | 146 | 50 | 54 |
| maths | 250 | 152 | 44 | 54 |
| retrieval_grounded | 250 | 145 | 42 | 63 |
| summarization | 250 | 150 | 44 | 56 |
| text_generation | 183 | 120 | 39 | 24 |

### A.3 SDDF v3 Validation Results by Task Family and SLM (`continuous_validation_results.json`)

| Task family | Model | n_samples | baseline_capability | mean_risk | c_dyn | r_dyn | tau_star | tau_source | feasible_set_size | coverage | selected_capability | selected_risk |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| classification | qwen2.5_0.5b | 53 | 0.9000 | 0.3208 | 0.8500 | 0.3708 | 0.0000 | fallback_min_violation_robust | 0 | 0.6415 | 0.0000 | 0.5000 |
| classification | qwen2.5_3b | 53 | 0.9000 | 0.2264 | 0.8500 | 0.2764 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.5472 | 0.2264 |
| classification | qwen2.5_7b | 53 | 0.9000 | 0.3019 | 0.8500 | 0.3519 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.3962 | 0.3019 |
| code_generation | qwen2.5_0.5b | 49 | 0.3800 | 0.4184 | 0.3300 | 0.4684 | 0.0000 | fallback_min_violation_robust | 0 | 0.6327 | 0.0968 | 0.4516 |
| code_generation | qwen2.5_3b | 49 | 0.3800 | 0.3163 | 0.3300 | 0.3663 | 1.0000 | strict_feasible_max | 1 | 1.0000 | 0.3673 | 0.3163 |
| code_generation | qwen2.5_7b | 49 | 0.3800 | 0.2755 | 0.3300 | 0.3255 | 1.0000 | strict_feasible_max | 1 | 1.0000 | 0.4490 | 0.2755 |
| information_extraction | qwen2.5_0.5b | 36 | 0.9200 | 0.1944 | 0.8700 | 0.2444 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.6111 | 0.1944 |
| information_extraction | qwen2.5_3b | 36 | 0.9200 | 0.1389 | 0.8700 | 0.1889 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.7222 | 0.1389 |
| information_extraction | qwen2.5_7b | 36 | 0.9200 | 0.1111 | 0.8700 | 0.1611 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.7778 | 0.1111 |
| instruction_following | qwen2.5_0.5b | 50 | 0.9000 | 0.2000 | 0.8500 | 0.2500 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.6000 | 0.2000 |
| instruction_following | qwen2.5_3b | 50 | 0.9000 | 0.1200 | 0.8500 | 0.1700 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.7600 | 0.1200 |
| instruction_following | qwen2.5_7b | 50 | 0.9000 | 0.1100 | 0.8500 | 0.1600 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.7800 | 0.1100 |
| maths | qwen2.5_0.5b | 44 | 0.7260 | 0.4432 | 0.6760 | 0.4932 | 0.0000 | fallback_min_violation_robust | 0 | 0.7727 | 0.0000 | 0.5000 |
| maths | qwen2.5_3b | 44 | 0.7260 | 0.2841 | 0.6760 | 0.3341 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.4318 | 0.2841 |
| maths | qwen2.5_7b | 44 | 0.7260 | 0.3409 | 0.6760 | 0.3909 | 0.0000 | fallback_min_violation_robust | 0 | 0.5682 | 0.0000 | 0.5000 |
| retrieval_grounded | qwen2.5_0.5b | 42 | 0.8800 | 0.2738 | 0.8300 | 0.3238 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.4524 | 0.2738 |
| retrieval_grounded | qwen2.5_3b | 42 | 0.8800 | 0.2143 | 0.8300 | 0.2643 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.5714 | 0.2143 |
| retrieval_grounded | qwen2.5_7b | 42 | 0.8800 | 0.2381 | 0.8300 | 0.2881 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.5238 | 0.2381 |
| summarization | qwen2.5_0.5b | 44 | 0.9500 | 0.1364 | 0.9000 | 0.1864 | 0.3929 | fallback_min_violation_robust | 0 | 0.9091 | 0.7000 | 0.1500 |
| summarization | qwen2.5_3b | 44 | 0.9500 | 0.0909 | 0.9000 | 0.1409 | 0.4034 | fallback_min_violation_robust | 0 | 0.9318 | 0.8049 | 0.0976 |
| summarization | qwen2.5_7b | 44 | 0.9500 | 0.1477 | 0.9000 | 0.1977 | 0.0952 | strict_feasible_max | 1 | 0.0227 | 1.0000 | 0.0000 |
| text_generation | qwen2.5_0.5b | 39 | 0.9300 | 0.1026 | 0.8800 | 0.1526 | 1.0000 | fallback_min_violation_robust | 0 | 1.0000 | 0.7949 | 0.1026 |
| text_generation | qwen2.5_3b | 39 | 0.9300 | 0.0641 | 0.8800 | 0.1141 | 0.8000 | fallback_min_violation_robust | 0 | 0.6410 | 0.8000 | 0.1000 |
| text_generation | qwen2.5_7b | 39 | 0.9300 | 0.0256 | 0.8800 | 0.0756 | 1.0000 | strict_feasible_max | 1 | 1.0000 | 0.9487 | 0.0256 |

### A.4 SDDF v3 Validation Aggregate by Task Family (mean across SLMs)

| Task family | SLM count | Mean tau_star | Mean coverage | Mean selected capability | Mean selected risk | Dominant tau_source |
|---|---:|---:|---:|---:|---:|---|
| classification | 3 | 0.6667 | 0.8805 | 0.3145 | 0.3428 | fallback_min_violation_robust |
| code_generation | 3 | 0.6667 | 0.8776 | 0.3044 | 0.3478 | strict_feasible_max |
| information_extraction | 3 | 1.0000 | 1.0000 | 0.7037 | 0.1481 | fallback_min_violation_robust |
| instruction_following | 3 | 1.0000 | 1.0000 | 0.7133 | 0.1433 | fallback_min_violation_robust |
| maths | 3 | 0.3333 | 0.7803 | 0.1439 | 0.4280 | fallback_min_violation_robust |
| retrieval_grounded | 3 | 1.0000 | 1.0000 | 0.5159 | 0.2421 | fallback_min_violation_robust |
| summarization | 3 | 0.2972 | 0.6212 | 0.8350 | 0.0825 | fallback_min_violation_robust |
| text_generation | 3 | 0.9333 | 0.8803 | 0.8479 | 0.0761 | fallback_min_violation_robust |

### A.5 SDDF v3 Validation Tau Selection Summary from `val_evaluation_report.json`

| Task family | Runs | Mean selected_tau | strict_feasible_max count | fallback_min_violation count | Mean cap_dynamic | Mean risk_dynamic |
|---|---:|---:|---:|---:|---:|---:|
| classification | 15 | 9.0000 | 10 | 5 | 0.6500 | 0.3425 |
| code_generation | 15 | 9.0000 | 5 | 10 | 0.6500 | 0.6611 |
| information_extraction | 15 | 9.0000 | 10 | 5 | 0.6500 | 0.3000 |
| instruction_following | 15 | 9.0000 | 15 | 0 | 0.6500 | 0.3000 |
| maths | 15 | 9.0000 | 5 | 10 | 0.6500 | 0.7233 |
| retrieval_grounded | 3 | 9.0000 | 3 | 0 | 0.6500 | 0.3463 |
| summarization | 3 | 9.0000 | 3 | 0 | 0.6500 | 0.3000 |
| text_generation | 3 | 9.0000 | 3 | 0 | 0.6500 | 0.3000 |

### A.6 SDDF v3 Test Performance by Task Family and SLM (`test_evaluation_report.json`)

| Task family | Model | Seeds | Mean tau | Mean n_test | Mean accuracy | Mean F1 | Mean ROC-AUC | Mean PR-AUC | Mean Brier | Mean ECE(10-bin) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| classification | qwen2.5_0.5b | 5 | 0.5000 | 42.0000 | 0.7381 | 0.7442 | 0.7212 | 0.8746 | 0.1983 | 0.2551 |
| classification | qwen2.5_3b | 5 | 0.4000 | 42.0000 | 0.8095 | 0.7778 | 0.9543 | 0.9525 | 0.1061 | 0.2213 |
| classification | qwen2.5_7b | 5 | 0.2000 | 42.0000 | 0.6190 | 0.7576 | 0.7139 | 0.8283 | 0.2193 | 0.1911 |
| code_generation | qwen2.5_0.5b | 5 | 0.0500 | 54.0000 | 0.7778 | 0.8750 | 0.6627 | 0.8510 | 0.2118 | 0.2252 |
| code_generation | qwen2.5_3b | 5 | 0.1000 | 54.0000 | 0.5370 | 0.6575 | 0.6486 | 0.5523 | 0.2597 | 0.1896 |
| code_generation | qwen2.5_7b | 5 | 0.4500 | 54.0000 | 0.6667 | 0.6087 | 0.6185 | 0.5173 | 0.2570 | 0.1851 |
| information_extraction | qwen2.5_0.5b | 5 | 0.0500 | 35.0000 | 0.4857 | 0.6400 | 0.6020 | 0.6269 | 0.2469 | 0.1682 |
| information_extraction | qwen2.5_3b | 5 | 0.1500 | 35.0000 | 0.2286 | 0.3721 | 0.6200 | 0.4520 | 0.2734 | 0.3141 |
| information_extraction | qwen2.5_7b | 5 | 0.1500 | 35.0000 | 0.3714 | 0.3889 | 0.7731 | 0.6752 | 0.2079 | 0.2961 |
| instruction_following | qwen2.5_0.5b | 5 | 0.4000 | 54.0000 | 0.6481 | 0.6545 | 0.6830 | 0.6289 | 0.2217 | 0.0965 |
| instruction_following | qwen2.5_3b | 5 | 0.2000 | 54.0000 | 0.2037 | 0.2456 | 0.4742 | 0.1362 | 0.2823 | 0.3577 |
| instruction_following | qwen2.5_7b | 5 | 0.3000 | 54.0000 | 0.3704 | 0.3462 | 0.6512 | 0.5844 | 0.2044 | 0.2859 |
| maths | qwen2.5_0.5b | 5 | 0.0500 | 54.0000 | 0.8519 | 0.9200 | 0.7283 | 0.9479 | 0.2499 | 0.3557 |
| maths | qwen2.5_3b | 5 | 0.2500 | 54.0000 | 0.4444 | 0.5312 | 0.8120 | 0.8117 | 0.1748 | 0.2076 |
| maths | qwen2.5_7b | 5 | 0.0500 | 54.0000 | 0.6481 | 0.7865 | 0.7414 | 0.8855 | 0.2145 | 0.1749 |
| retrieval_grounded | qwen2.5_0.5b | 1 | 0.1000 | 63.0000 | 0.5238 | 0.6512 | 0.8286 | 0.7738 | 0.1747 | 0.0989 |
| retrieval_grounded | qwen2.5_3b | 1 | 0.5500 | 63.0000 | 0.6984 | 0.6122 | 0.7413 | 0.6121 | 0.2097 | 0.1706 |
| retrieval_grounded | qwen2.5_7b | 1 | 0.3000 | 63.0000 | 0.6825 | 0.6774 | 0.8288 | 0.6654 | 0.1762 | 0.1587 |
| summarization | qwen2.5_0.5b | 1 | 0.8000 | 56.0000 | 0.6607 | 0.1739 | 0.7014 | 0.6072 | 0.2217 | 0.1395 |
| summarization | qwen2.5_3b | 1 | 0.6000 | 56.0000 | 0.6964 | 0.2609 | 0.5357 | 0.3053 | 0.2580 | 0.2422 |
| summarization | qwen2.5_7b | 1 | 0.2000 | 56.0000 | 0.3571 | 0.4706 | 0.5762 | 0.3386 | 0.2680 | 0.2507 |
| text_generation | qwen2.5_0.5b | 1 | 0.1500 | 24.0000 | 0.1250 | 0.2222 | 0.2698 | 0.1109 | 0.2421 | 0.3056 |
| text_generation | qwen2.5_3b | 1 | 0.6000 | 24.0000 | 0.5417 | 0.1538 | 0.5714 | 0.2736 | 0.2954 | 0.4424 |
| text_generation | qwen2.5_7b | 1 | 0.6500 | 24.0000 | 0.8333 | 0.0000 | 0.0435 | 0.0435 | 0.1825 | 0.2318 |

## Appendix B. Experimental Tables (UC1 to UC8)

### B.1 UC-Level Policy vs Runtime Core Table (`section8_uc_evaluation_table_enhanced.csv`)

| Use case | Task family | S3 score | S3 tier | Runtime tier | Routing decision | Gap analysis | C_m(d) | R_m(d) | tau_consensus | SLM coverage |
|---|---|---:|---|---|---|---|---:|---:|---:|---:|
| UC1 | classification | 3.40 | Hybrid | LLM Only | LLM | Underestimation (dangerous) | 0.3145 | 0.3428 | 0.6667 | 0.0000 |
| UC2 | information_extraction | 2.60 | Pure SLM | Pure SLM | SLM | Match | 0.7037 | 0.1481 | 1.0000 | 1.0000 |
| UC3 | classification | 2.67 | Pure SLM | LLM Only | LLM | Underestimation (dangerous) | 0.3145 | 0.3428 | 0.6667 | 0.0000 |
| UC4 | classification | 2.07 | Pure SLM | LLM Only | LLM | Underestimation (dangerous) | 0.3145 | 0.3428 | 0.6667 | 0.0000 |
| UC5 | code_generation | 3.27 | Hybrid | Hybrid | HYBRID | Match | 0.3044 | 0.3478 | 0.6667 | 0.2700 |
| UC6 | classification | 4.27 | LLM Only | LLM Only | LLM | Match | 0.3145 | 0.3428 | 0.6667 | 0.0000 |
| UC7 | summarization | 3.20 | Hybrid | LLM Only | LLM | Underestimation (dangerous) | 0.8350 | 0.0825 | 0.2972 | 0.0000 |
| UC8 | text_generation | 3.07 | LLM Only | Pure SLM | SLM | Overestimation (inefficient) | 0.8479 | 0.0761 | 0.9333 | 1.0000 |

### B.2 UC-Level Performance, Latency, and Cost Table (same source)

| Use case | Runtime acc est | Runtime F1 est | Runtime failure est | Runtime P95(ms) | Cost low USD/mo | Cost high USD/mo | Decision correct |
|---|---:|---:|---:|---:|---:|---:|---:|
| UC1 | 0.8333 | 0.8286 | 0.1667 | 2426.3000 | 50000.00 | 100000.00 | 0 |
| UC2 | 1.0000 | 1.0000 | 0.0000 | 3600.0500 | 127.00 | 500.00 | 1 |
| UC3 | 0.8333 | 0.7000 | 0.1667 | 2426.9000 | 50000.00 | 100000.00 | 0 |
| UC4 | 1.0000 | 1.0000 | 0.0000 | 363.1500 | 50000.00 | 100000.00 | 0 |
| UC5 | 0.8333 | 0.7117 | 0.1667 | 2738.0925 | 36534.29 | 73135.00 | 1 |
| UC6 | 0.5000 | 0.4333 | 0.5000 | 2593.9000 | 50000.00 | 100000.00 | 1 |
| UC7 | 0.5000 | 0.4127 | 0.5000 | 2639.3500 | 50000.00 | 100000.00 | 1 |
| UC8 | N/A | N/A | N/A | 10265.4500 | 127.00 | 500.00 | 0 |

### B.3 Raw UC Output Files Used (Smita repo)

| Use case | Raw output file | Summary file |
|---|---|---|
| UC1 | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\raw_outputs\uc1_raw_20260303_165536.csv | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\results\uc1_summary_20260303_165536.csv |
| UC2 | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\raw_outputs\uc2_raw_20260310_112624.csv | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\results\uc2_summary_20260310_112624.csv |
| UC3 | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\raw_outputs\uc3_raw_20260311_092607.csv | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\results\uc3_summary_20260311_092607.csv |
| UC4 | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\raw_outputs\uc4_raw_20260303_202703.csv | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\results\uc4_summary_20260303_202703.csv |
| UC5 | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\raw_outputs\uc5_raw_20260413_110810.csv | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\results\uc5_summary_20260413_110810.csv |
| UC6 | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\raw_outputs\uc6_raw_20260310_135253.csv | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\results\uc6_summary_20260311_084050.csv |
| UC7 | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\raw_outputs\uc7_raw_20260413_113202.csv | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\results\uc7_summary_20260413_113202.csv |
| UC8 | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\data\raw_outputs\uc8_raw_20260311_120455.csv | C:\Users\riddh\OneDrive\Desktop\SLM use cases\repos\SLM_Research_Project\evaluation\uc8_summary_20260311_152838.csv |
