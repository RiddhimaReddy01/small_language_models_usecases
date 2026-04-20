## 11. Limitations

This study provides a unified S3 plus SDDF deployment framework, but the current evidence base has important constraints that should bound interpretation of Sections 6 to 10 and inform future replications.

### 11.1 Sample Size and Statistical Power at Enterprise-Task Level

The enterprise-layer evaluation is based on eight use cases (UC1 to UC8), which limits inferential power for cross-framework statistics. In Section 8, correlation between S3 and SDDF outcomes is directionally interpretable but statistically weak at UC level (non-significant p-values).

\[
N_{UC}=8
\]

\[
\rho_{Spearman}(S3,C_m(d))=-0.2664,\quad p=0.5237
\]

\[
\rho_{Spearman}(S3,R_m(d))=+0.2664,\quad p=0.5237
\]

Implication: Section 9 and Section 10 findings should be treated as strong design evidence for protocol behavior, but only moderate statistical evidence for generalizable monotonic relationships at enterprise-task level.

### 11.2 High Dependence on Fallback Threshold Selection in SDDF

The SDDF validation artifacts show frequent reliance on fallback thresholding rather than strict feasible selection.

From `continuous_validation_results.json`:

- `fallback_min_violation_robust`: 20 cases
- `strict_feasible_max`: 4 cases

Thus, most operational thresholds are selected under constrained feasibility conditions rather than full satisfaction of capability-risk constraints.

\[
\text{Fallback Share}=\frac{20}{24}=0.8333
\]

Implication: Runtime routing in Sections 7 to 10 is operationally valid for this dataset, but may be sensitive to calibration choices when feasible regions are sparse.

### 11.3 Uneven Seed Coverage Across Task Families

The SDDF test report (`test_evaluation_report.json`) is not uniform across task families:

- Classification, code generation, information extraction, instruction following, and maths have 5 seeds per model.
- Retrieval-grounded, summarization, and text generation have 1 seed per model.

This creates heterogeneous uncertainty across task families.

\[
|\mathcal{S}_{task}|\in\{1,5\}
\]

Implication: Cross-family comparisons in Sections 6 and 8 combine estimates with different variance support, which can bias apparent stability.

### 11.4 Partial Outcome Observability at UC Level

Section 8 explicitly excludes UC8 from label-based macro metrics because compatible ground-truth label structure is unavailable in the same format used for UC1 to UC7. This reduces comparability of aggregate quality statistics.

\[
\text{Macro metrics computed on } \{UC1,\dots,UC7\},\quad UC8\notin\text{macro label set}
\]

Implication: Reported macro accuracy, F1, and failure rates are not full UC1 to UC8 aggregates.

### 11.5 Abstraction Loss in Enterprise-to-Task-Family Mapping

The S3 to SDDF bridge maps each enterprise use case to a primary task family, but several use cases are computationally mixed (as discussed in Section 10.4). A single-family mapping can suppress secondary difficulty modes.

Examples from Sections 9 and 10:

- UC7 (legal contract risk): summarization primary label, but includes retrieval and clause-level reasoning demands.
- UC8 (financial drafting): text-generation primary label, but includes instruction-constraint and numeric consistency components.

Implication: Some disagreements between policy tier and runtime tier can reflect mapping granularity, not only policy-score error.

### 11.6 Policy Conservatism as Both Safeguard and Efficiency Constraint

S3 gate rules are intentionally non-compensatory (`s3_framework.py`), which improves safety governance but can produce conservative over-assignment in edge cases.

Formal gate behavior:

\[
SK=5\Rightarrow\text{Disqualified}
\]

\[
TC=5\land SK\ge 4\Rightarrow\text{Disqualified}
\]

\[
SK\ge 4\Rightarrow\text{Minimum Tier=Hybrid}
\]

Implication: As shown in Sections 9 and 10, this asymmetry is appropriate for harm prevention but may reduce cost-optimal local routing for some feasible workloads.

### 11.7 Determinism and Reproducibility Trade-off

The framework uses fixed experimental controls (`inference_config.json`: temperature 0.0, top_p 1.0, fixed seed lists) and deterministic split summaries (`summary.json`), which strengthens reproducibility but narrows exploration of stochastic variance under broader inference settings.

Implication: Results are highly auditable for this configuration, but robustness to alternative decoding regimes requires additional experimentation.

### 11.8 Consolidated Limitation Matrix

| Limitation | Evidence artifact(s) | Observed effect on Sections 6 to 10 |
|---|---|---|
| Small UC sample | `section8_summary_enhanced.json` | Low statistical power for UC-level convergence claims |
| Fallback-heavy SDDF thresholds | `continuous_validation_results.json` | Routing sensitivity to calibration fallback logic |
| Uneven seed coverage by task family | `test_evaluation_report.json` | Non-uniform uncertainty across task-family results |
| UC8 label-metric gap | `section8_uc_evaluation_table_enhanced.csv`, `SECTION_8_REVISED.md` | Macro quality metrics exclude UC8 |
| Single-family mapping abstraction | `runtime_routing_consensus_frozen_tau.csv`, Section 10 discussion | Potential attribution error in agreement/disagreement analysis |
| Conservative hard gates | `s3_framework.py`, Section 4 extract | Safety-preserving but sometimes cost-inefficient assignments |
| Fixed decode controls | `configs/inference_config.json` | Strong reproducibility with reduced stochastic diversity |

### 11.9 Practical Reading of These Limitations

The limitations do not invalidate the framework. Instead, they define the current evidentiary boundary: S3 plus SDDF is demonstrated as an auditable decision protocol with clear operational behavior, while external generalization and variance robustness require broader multi-dataset, multi-seed, and multi-configuration replication.

Ground-truth files used:

- `docs/source_extracts/S3_SDDF_Paper_Section1.txt`
- `docs/source_extracts/S3_SDDF_Sections2_3_v2.txt`
- `docs/section6_7_rewrite/SECTION_6_7_REWRITTEN.md`
- `docs/section8_outputs/SECTION_8_REVISED.md`
- `docs/section9_outputs/SECTION_9_RESULTS.md`
- `docs/section10_outputs/SECTION_10_DISCUSSION.md`
- `repos/small_language_models_usecases/sddf/s3_framework.py`
- `repos/small_language_models_usecases/sddf/validation_dynamic.py`
- `repos/small_language_models_usecases/continuous_validation_results.json`
- `repos/small_language_models_usecases/model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/test_evaluation_report.json`
- `repos/small_language_models_usecases/model_runs/sddf_training_splits_slm_only/summary.json`
- `repos/SLM_Research_Project/configs/inference_config.json`
