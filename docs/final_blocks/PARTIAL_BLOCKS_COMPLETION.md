## Partial Blocks Completion (Repo-Grounded)

## Contributions (Explicitly Split)

### Theoretical Contribution

This paper contributes a two-layer decision theory for enterprise model routing by combining a policy-layer suitability score (S3) with an empirical boundary layer (SDDF). The theoretical novelty is the coupling of a compensatory multi-criteria score with non-compensatory gate rules and then testing that policy against empirical capability-risk frontiers. This creates a formal offline-to-online chain: policy priors from S3, operational feasibility from SDDF, and runtime routing via task-family-specific threshold selection.

### Managerial Contribution

This paper provides a deployment-ready governance protocol for enterprise AI operations. Managers can pre-classify use cases by stakes, complexity, and operational constraints, freeze family-level thresholds from validation, and enforce escalation rules when boundary violations are likely. The result is a structured mechanism for cost control, risk control, and auditability across Pure SLM, Hybrid, and LLM-only operating tiers.

### Methodological Contribution

Methodologically, the study contributes a reproducible train-val-test calibration pipeline with leakage-aware checks, frozen-threshold transfer from validation to test, and sensitivity analysis over threshold and utility settings. The method is implemented across task families and models, with explicit artifacts for split policy, threshold policy, calibration diagnostics, and operating-point evaluation.

## Design-Science Method Details and Validity Checks

The artifact under evaluation is an enterprise routing protocol that links S3 policy decisions to SDDF runtime decisions. The design cycle is operationalized in two stages. In the offline stage, task-family difficulty features are used to estimate capability and risk behavior and to calibrate family-level operational thresholds. In the online stage, new enterprise use cases are mapped to task families, difficulty is computed, frozen thresholds are applied, and routing decisions are made as SLM or LLM fallback.

Validity checks are explicitly embedded in the pipeline artifacts:

| Validity check | Operational evidence in repos | Purpose |
|---|---|---|
| Split integrity and leakage checks | `model_runs/benchmarking/phase_reports/val_phase_report.json` (`split_contract_ok`, `leakage_violations`) | Internal validity against contamination |
| Frozen-policy transfer check | `model_runs/benchmarking/phase_reports/val_phase_report.json` (`frozen_policy_check`) | Verifies no threshold drift between calibration and evaluation |
| Cross-profile sensitivity | `model_runs/benchmarking/sensitivity/val_sensitivity_summary.json`, `scripts/sensitivity_analysis.py` | Robustness of routing decisions to policy variation |
| Policy-empirical convergence | `scripts/s3_sddf_bridge.py`, `evaluation/s3_sddf_bridge_report_*.txt` | Construct validity across S3 and SDDF layers |

## Canonical Experimental Setup (Single Consolidated Block)

| Component | Canonical setting | Primary artifact |
|---|---|---|
| Task families | 8 families (classification, information extraction, summarization, retrieval grounded, instruction following, maths, code generation, text generation) | `benchmark_pipeline_registry.json` |
| Enterprise use cases | 8 mapped use cases (UC1-UC8) evaluated in policy layer and runtime layer | `README.md`, section-level manuscript outputs |
| Split protocol | Deterministic hash split (`sha1(sample_id)%100`: train<30, val<70, test>=70) | `model_runs/benchmarking/phase_reports/val_phase_report.json` |
| Inference determinism | `temperature=0.0`, fixed seeds (`[42,43,44]` in Smita repo benchmark config) | `configs/inference_config.json`, `README.md` |
| Thresholding | Family-level operational tau from validation, then frozen for evaluation transfer | `model_runs/*/sddf/routing_policy.json`, `val_phase_report*.json` |
| Capability and risk targets | Capability threshold and risk threshold tracked per task-model evaluation row | `val_phase_report.csv`, `val_phase_report.json` |
| Statistical outputs | Bootstrap confidence intervals, McNemar p-values, Holm correction | `tools/evaluate_test_phase.py`, `test_phase_report.csv` |
| Sensitivity settings | Grid over bootstrap draws, conservative tau percentile, and utility coefficients | `val_sensitivity_summary.json`, `val_sensitivity_summary.csv` |
| Exclusion and failure handling | Invalid or failed samples represented in routing-quality accounting and risk metrics | `tools/evaluate_test_phase.py`, phase reports |

## Statistical Inference Block (CIs, Significance, Effect Magnitude)

Inference is reported using bootstrap confidence intervals for core performance and routing metrics, with paired significance testing against baseline policies.

| Statistical element | Implemented evidence | Reporting rule for paper |
|---|---|---|
| Confidence intervals | `precision_ci90_*`, `recall_ci90_*`, `f1_ci90_*`, `accuracy_ci90_*`, capability/risk/utility CI fields in `test_phase_report.csv` | Report point estimate with 90% CI in all key performance tables |
| Significance tests | McNemar tests plus Holm adjustment (`mcnemar_p_*`, `mcnemar_p_*_holm`) | Report adjusted p-values for policy vs always-SLM and policy vs always-baseline |
| Effect magnitude | Delta fields already available (`delta_accuracy_vs_*`, `delta_utility_vs_*`) in phase reports | Report these deltas as primary effect-size style magnitudes at task and aggregate levels |

Note on current status: CI and significance machinery are already present in repository outputs. Explicit narrative framing of effect magnitude should be added in manuscript tables by consistently reporting delta-accuracy and delta-utility columns alongside p-values.

## Robustness and Boundary Stress-Test Block

Boundary robustness is evaluated through explicit stress testing of threshold and utility configurations, with particular emphasis on near-boundary routing behavior.

| Stress-test axis | Artifact evidence | Interpretation target |
|---|---|---|
| Tau conservatism | `tau_conservative_percentile` sweeps (5 and 10) in `val_sensitivity_summary.json` | Tests whether routing policy is stable under conservative threshold shifts |
| Bootstrap uncertainty | `tau_bootstrap_draws` sweeps (100 and 200) in sensitivity summaries | Tests threshold stability under resampling variance |
| Utility preference shifts | `utility_alpha`, `utility_beta`, `utility_gamma` sweeps | Tests policy behavior under different business trade-off regimes |
| Feasible vs fallback boundary behavior | Continuous validation results in `CONTINUOUS_VALIDATION_SECTION_5_REGULARIZED.md` | Tests behavior when strict feasible sets are empty |
| Policy boundary cases | S3 boundary case documentation in `docs/s3_scoring_worksheet.md` and sensitivity report outputs | Tests classification sensitivity around tier boundaries and gate-rule activation |

The manuscript should name this as a standalone "Boundary Stress-Test Protocol" subsection and summarize pass-rate and policy-flip behavior across stress configurations.

## Reproducibility and Data/Code Availability Statement

All code, configuration, and derived artifacts used in this study are available in the two project repositories used as ground truth: `SLM_Research_Project` (policy layer, enterprise use-case benchmarking assets) and `small_language_models_usecases` (SDDF calibration, validation, routing, and sensitivity assets). Reproducibility is supported through deterministic inference settings, explicit split policies, frozen-threshold checks, and versioned phase reports that include calibration, uncertainty, and significance outputs.

The study uses open-source and repository-contained artifacts and does not rely on private human-subject data collection. Hardware and runtime environment capture scripts are included in the repositories, and benchmark/evaluation outputs are persisted as machine-readable CSV/JSON artifacts for independent verification.
