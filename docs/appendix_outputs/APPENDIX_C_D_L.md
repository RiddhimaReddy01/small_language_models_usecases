# Appendix C, D, L

## Appendix C. Pipeline and Pseudocode (S3 -> SDDF -> Runtime)

### C.1 Unified Pipeline (from Smita `scripts/s3_sddf_bridge.py` and Riddhima `framework/benchmarking/s3_sddf_bridge.py`)

```text
Input: enterprise use case u, mapped task family t, task-family model artifacts

Stage 1: S3 Policy Layer (pre-deployment)
  1. Collect six S3 dimension scores: TC, OS, SK, DS, LT, VL
  2. Compute weighted score: S3 = [sum_i(score_i * w_i) / sum_i(5 * w_i)] * 5
  3. Apply gate rules:
     - Hard Rule 1: SK = 5 -> LLM Only/Disqualified
     - Hard Rule 2: TC = 5 and SK >= 4 -> LLM Only/Disqualified
     - Flag Rule: SK >= 4 -> minimum Hybrid
  4. Map to policy tier via thresholds tau1, tau2

Stage 2: SDDF Offline Calibration (task-family level)
  5. Compute task-family difficulty features d from sddf/difficulty.py
  6. Validation split: estimate capability C_m(d) and risk R_m(d) for each SLM
  7. Select tau* satisfying capability-risk constraints (strict or fallback_min_violation)
  8. Test split: verify operational performance at selected tau*

Stage 3: Runtime Online Routing (incoming query x)
  9. Compute d(x) using mapped task-family extractor
 10. Apply frozen tau*_t
 11. Route:
     if d(x) <= tau*_t: SLM
     else: LLM
 12. Aggregate per-query decisions to use-case runtime tier: Pure SLM / Hybrid / LLM Only
```

### C.2 Runtime Decision Function

$$
\\text{route}(x)=
\\begin{cases}
\\texttt{SLM}, & d(x)\\le\\tau_t^* \\\\
\\texttt{LLM}, & d(x)>\\tau_t^*
\\end{cases}
$$

## Appendix D. Sensitivity Analysis

### D.1 S3 Weight-Profile Sensitivity (Smita repo)

| Use case | Default tier | Security-First tier | Latency-First tier | Balanced tier | Volume-Heavy tier | Tier stability across 5 profiles |
|---|---|---|---|---|---|---|
| UC1_SMS_Threat | Hybrid | Hybrid | Hybrid | Hybrid | Hybrid | Stable |
| UC2_Invoice_Extract | Pure SLM | Pure SLM | Pure SLM | Pure SLM | Pure SLM | Stable |
| UC3_Ticket_Routing | Pure SLM | Pure SLM | Pure SLM | Pure SLM | Pure SLM | Stable |
| UC4_Review_Sentiment | Pure SLM | Pure SLM | Pure SLM | Pure SLM | Pure SLM | Stable |
| UC5_Code_Review | Hybrid | Pure SLM | Pure SLM | Pure SLM | Pure SLM | Changes |
| UC6_Clinical_Triage | LLM Only | LLM Only | LLM Only | LLM Only | LLM Only | Stable |
| UC7_Legal_Contract | Hybrid | Hybrid | Hybrid | Hybrid | Hybrid | Stable |
| UC8_Financial_Report | LLM Only | LLM Only | LLM Only | LLM Only | LLM Only | Stable |

Stability summary: 7/8 use cases keep the same tier across all five S3 weight profiles.

### D.2 SDDF Validation Sensitivity Sweep (Riddhima repo, val split)

| Statistic | Value |
|---|---:|
| Number of sensitivity configurations | 12 |
| Mean pass_rate | 0.4089 |
| Max pass_rate | 0.5000 |
| Mean avg_accuracy | 0.5500 |
| Mean avg_f1 | 0.3266 |
| Mean avg_coverage_slm | 0.3050 |
| Mean avg_delta_utility_vs_always_slm | -0.5716 |

| Top-5 sensitivity configs by pass_rate | cap_threshold | risk_threshold | min_samples | alpha | beta | gamma | bootstrap_draws | percentile | pass_rate | avg_accuracy | avg_f1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cfg_2 | 0.75 | 0.15 | 5 | 0.5 | 0.0 | 0.5 | 100 | 10.0 | 0.5000 | 0.5630 | 0.3626 |
| cfg_4 | 0.75 | 0.15 | 5 | 0.5 | 0.0 | 0.5 | 200 | 10.0 | 0.4688 | 0.5522 | 0.3336 |
| cfg_10 | 0.75 | 0.15 | 5 | 0.5 | 0.25 | 0.5 | 100 | 10.0 | 0.4375 | 0.5607 | 0.3545 |
| cfg_6 | 0.75 | 0.15 | 5 | 0.5 | 0.0 | 1.0 | 100 | 10.0 | 0.4375 | 0.5611 | 0.3549 |
| cfg_8 | 0.75 | 0.15 | 5 | 0.5 | 0.0 | 1.0 | 200 | 10.0 | 0.4062 | 0.5507 | 0.3277 |

## Appendix L. Ablations

### L.1 Feature-Ablation Coverage by Task Family (`val_feature_ablation__*__all.csv`)

| Task family | Rows in all-features report | Mean pass_operating_gate | Mean coverage_slm | Mean selected_capability | Mean selected_risk | Mean accuracy | Mean f1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| classification | 32 | 0.5938 | 0.2027 | 0.5772 | 0.3660 | 0.5179 | 0.2882 |
| code_generation | 32 | 0.5938 | 0.2027 | 0.5772 | 0.3660 | 0.5179 | 0.2882 |
| information_extraction | 32 | 0.5938 | 0.2027 | 0.5772 | 0.3660 | 0.5179 | 0.2882 |
| instruction_following | 32 | 0.5938 | 0.2027 | 0.5772 | 0.3660 | 0.5179 | 0.2882 |
| maths | 32 | 0.5938 | 0.2027 | 0.5772 | 0.3660 | 0.5179 | 0.2882 |
| retrieval_grounded | 32 | 0.5938 | 0.2027 | 0.5772 | 0.3660 | 0.5179 | 0.2882 |
| summarization | 32 | 0.5938 | 0.2027 | 0.5772 | 0.3660 | 0.5179 | 0.2882 |
| text_generation | 32 | 0.5938 | 0.2027 | 0.5772 | 0.3660 | 0.5179 | 0.2882 |

### L.2 Failed-Pairs Ablation Summary (`failed_pairs_ablation_summary.csv`)

| Task | Model | Test reason | Base coverage | Base capability | Base risk | Gate flip count |
|---|---|---|---:|---:|---:|---:|
| classification | qwen2.5:0.5b | cap_below+risk_above | 0.7647 | 0.5077 | 0.2757 | 0 |
| code_generation | qwen2.5:0.5b | cap_below+risk_above | 0.0000 | 0.0000 | 1.0000 | 0 |
| code_generation | qwen2.5:3b | cap_below+risk_above | 0.7348 | 0.3918 | 0.5489 | 0 |
| information_extraction | groq:llama-3.3-70b-versatile | cap_below | 0.8158 | 0.7419 | 0.1548 | 5 |
| information_extraction | qwen2.5:0.5b | cap_below+risk_above | 0.0263 | 0.5000 | 0.3000 | 0 |
| information_extraction | qwen2.5:3b | cap_below+risk_above | 0.0000 | 0.0000 | 1.0000 | 0 |
| information_extraction | qwen2.5:7b | cap_below+risk_above | 0.0395 | 0.6667 | 0.2000 | 5 |
| instruction_following | qwen2.5:0.5b | cap_below+risk_above | 0.3284 | 0.5227 | 0.2506 | 5 |
| maths | qwen2.5:0.5b | cap_below+risk_above | 0.0000 | 0.0000 | 1.0000 | 0 |
| maths | qwen2.5:3b | cap_below+risk_above | 0.0613 | 0.6000 | 0.3420 | 0 |
| maths | qwen2.5:7b | cap_below+risk_above | 0.0061 | 0.0000 | 0.8550 | 0 |
| summarization | qwen2.5:7b | cap_below | 0.3696 | 0.5588 | 0.1060 | 5 |
| text_generation | qwen2.5:0.5b | cap_below+risk_above | 0.0000 | 0.0000 | 1.0000 | 0 |
| text_generation | qwen2.5:3b | cap_below+risk_above | 0.0000 | 0.0000 | 1.0000 | 0 |

### L.3 Ablation Runner Procedure (from `framework/benchmarking/sddf_ablation_runner.py`)

1. Load base feature schema (`sddf_feature_schema_v2.json`).
2. Build ablation schemas (`all_features`, `no_embedding`, `lexical_surface`, `retrieval_context`, `syntax_entities`).
3. Run `sddf_train_pipeline.py` for each ablation schema and seed set.
4. Emit `ablation_report.json` with run successes/errors and artifact directories.

## Source Files Used

- `repos/SLM_Research_Project/scripts/s3_sddf_bridge.py`
- `repos/small_language_models_usecases/framework/benchmarking/s3_sddf_bridge.py`
- `repos/SLM_Research_Project/scripts/sensitivity_analysis.py`
- `repos/SLM_Research_Project/evaluation/sensitivity_matrix_20260413_234329.csv`
- `repos/small_language_models_usecases/tools/run_sddf_sensitivity.py`
- `repos/small_language_models_usecases/model_runs/benchmarking/sensitivity/val_sensitivity_summary.csv`
- `repos/small_language_models_usecases/framework/benchmarking/sddf_ablation_runner.py`
- `repos/small_language_models_usecases/model_runs/benchmarking/phase_reports/val_feature_ablation__*__all.csv`
- `repos/small_language_models_usecases/model_runs/benchmarking/phase_reports/failed_pairs_ablation_summary.csv`


