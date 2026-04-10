# SDDF Pipeline (Current)

## 1) Data Ingestion

- Inputs:
  - Preferred: `model_runs/<task>/<model>/outputs_train.jsonl|outputs_val.jsonl|outputs_test.jsonl`
  - Legacy fallback: `model_runs/<task>/<model>/outputs.jsonl`
- Ground truth: `data/ground_truth/<task>.jsonl|json`
- Rows are deduped by `sample_id` and aligned across models.

## 2) Difficulty Scoring

- Feature set: `n_in`, `entropy`, `reasoning_proxy`, `constraint_count`, `parametric_dependence`, `dependency_distance`.
- Optional family-specific learned weights (`--learn-family-weights`) are trained on `train` split only and saved to:
  - `model_runs/difficulty_weights/family_weights_learned.json`

## 3) Train / Val / Test

- `train`: learn family difficulty weights from semantic-failure targets.
- `val` (and train+val calibration pool): calibrate policy on continuous difficulty.
- `test` (`--report-split test`): evaluate frozen policy only.
- Split fallback is deterministic from `sample_id` hash when explicit split is missing.

### Test-Phase Protocol (Frozen Policy)

1. Freeze policy artifacts from train+val:
 - task-family mapping / family weights
 - difficulty scoring formulas
 - capability/risk curves
 - `tau` + abstention band from validation
2. Score each unseen test query:
 - compute features
 - map to family
 - compute difficulty
 - route with frozen rule: `SLM` / `HYBRID_ABSTAIN` / `BASELINE`
3. Evaluate test-only outcomes:
 - routing quality (`precision`, `recall`, `f1`, `accuracy`) for safe-to-keep-on-SLM
 - selective performance (`coverage`, selected capability/risk, utility)
 - calibration (`ECE`, `Brier`) for expected capability/risk
 - uncertainty bands via bootstrap CI
4. Never refit on test:
 - if test misses target, tune on val and rerun test on a fresh holdout.

### Run Commands

Validation artifacts (for policy selection only):

```powershell
.\.venv\Scripts\python.exe tools\generate_benchmark75_sddf.py --report-split val
.\.venv\Scripts\python.exe tools\evaluate_test_phase.py --output-stem val_phase_report
```

Frozen-policy test artifacts (for headline claims):

```powershell
.\.venv\Scripts\python.exe tools\generate_benchmark75_sddf.py --report-split test
.\.venv\Scripts\python.exe tools\evaluate_test_phase.py --output-stem test_phase_report
.\.venv\Scripts\python.exe tools\tune_task_utility_coeffs.py
```

Error taxonomy (task/model, severity-linked):

```powershell
.\.venv\Scripts\python.exe tools\summarize_error_taxonomy.py
```

Separate deployment tradeoff framing (cost/latency/safety):

```powershell
.\.venv\Scripts\python.exe tools\summarize_deployment_tradeoffs.py
```

## 4) Continuous Curves and Thresholds

- Capability and risk are fit over continuous difficulty scores from independent ground truth.
- Wilson CI is used for finite-sample certification.
- Capability gate uses Wilson lower bound.
- Risk gate is conservative: breach if Wilson upper bound exceeds risk threshold.

## 5) Routing Policy

- Certified routing uses `tau` plus a safe/unsafe band (`d_safe`, `d_unsafe`).
- Hybrid band comes from certified CI boundaries or tau-local uncertainty fallback.
- Runtime states:
  - `SLM`
  - `HYBRID_ABSTAIN`
  - `BASELINE`

## 6) Outputs

Per task:
- `model_runs/<task>/sddf/thresholds.json`
- `model_runs/<task>/sddf/routing_policy.json`
- `model_runs/<task>/sddf/canonical_rows.jsonl`

Global:
- `model_runs/sddf_summary.json`
- `model_runs/business_analytics/dashboard.json`
- `model_runs/business_analytics/dashboard.md`
- `model_runs/benchmarking/configs/task_utility_coeffs.json`
- `model_runs/benchmarking/phase_reports/val_phase_report.json|csv|md`
- `model_runs/benchmarking/phase_reports/test_phase_report.json|csv|md`
- `model_runs/benchmarking/error_taxonomy/error_taxonomy_by_task_model.json|csv|md`
- `model_runs/benchmarking/deployment/deployment_tradeoffs.json|csv|md`
