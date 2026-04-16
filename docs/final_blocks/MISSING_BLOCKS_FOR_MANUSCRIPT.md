## Ethics, Privacy, and Governance Statement

This study uses open-source benchmark datasets and repository-based experimental artifacts from `SLM_Research_Project` and `small_language_models_usecases`. No human subjects were recruited, no intervention was performed on individuals, and no private personally identifiable records were collected by the authors during this research workflow. The evaluation pipeline operates on pre-existing task inputs, model outputs, and derived metrics under reproducible scripts and logged configurations.

From a governance perspective, the framework explicitly separates policy-layer controls (S3 gate rules) from empirical runtime controls (SDDF capability-risk thresholds). This separation supports auditable deployment decisions for high-stakes enterprise contexts by preventing purely compensatory scoring in safety-sensitive cases and by enforcing escalation when empirical boundary conditions are not met.

## Threats to Validity

### Internal Validity

Potential internal threats arise from threshold calibration behavior, especially when fallback minimum-violation selection is used frequently relative to strict feasible selection. Additional internal threats include seed-coverage imbalance across task families and dependency on deterministic decoding settings, which may reduce variance exploration under alternative inference regimes.

### Construct Validity

Construct threats concern mapping between conceptual variables and operational metrics. S3 dimensions are expert-scored managerial constructs, while SDDF uses empirical capability and risk proxies over task-family difficulty. Some disagreement cases may reflect imperfect construct alignment, particularly when one enterprise use case contains mixed computational sub-tasks but is mapped to a single dominant family.

### External Validity

Generalization is bounded by the current evidence scope: eight enterprise use cases, selected model set, and available artifacts across the two repos. Results are strongest as protocol-level and artifact-level evidence for the studied settings. Broader claims across industries, model families, and deployment infrastructures require additional multi-dataset and cross-environment replication.

## 13. Future Work

Future work will extend this study in four directions. First, we will run broader cross-dataset external validation across additional enterprise domains to improve external validity. Second, we will strengthen generalization analysis with complete cross-model transfer artifacts and standardized reporting across all task families. Third, we will test adaptive recalibration strategies for S3-SDDF boundary updates under drifted workload profiles. Fourth, we will evaluate operational performance under richer inference configurations, including non-zero temperature and alternative decoding controls, to characterize robustness under realistic production variability.

## Acknowledgements

The authors thank Professor Ashim Bose for guidance and feedback during this research conducted in BUAN 6399.001.
