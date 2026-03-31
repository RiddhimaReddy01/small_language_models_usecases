# SDDF Pipeline (Current)

## 1) Data Ingestion

- Inputs: `model_runs/<task>/<model>/outputs.jsonl`
- Ground truth: `data/ground_truth/<task>.jsonl|json`
- Rows are deduped by `sample_id` and aligned across models.

## 2) Difficulty Scoring

- Feature set: `n_in`, `entropy`, `reasoning_proxy`, `constraint_count`, `parametric_dependence`, `dependency_distance`.
- Optional family-specific learned weights (`--learn-family-weights`) are trained on `train` split only and saved to:
  - `model_runs/difficulty_weights/family_weights_learned.json`

## 3) Train / Val / Test

- `train`: learn family difficulty weights from semantic-failure targets.
- `val` (and train+val calibration pool): fit bin boundaries and calibrate policy.
- `test` (`--report-split test`): evaluate frozen policy only.
- Split fallback is deterministic from `sample_id` hash when explicit split is missing.

## 4) Curves and Thresholds

- Per-bin capability and risk are computed from independent ground truth.
- Wilson CI is used for finite-sample certification.
- Capability gate uses Wilson lower bound.
- Risk gate is conservative: breach if Wilson upper bound exceeds risk threshold.

## 5) Routing Policy

- Certified limit is derived from `tau_cap` and `tau_risk`.
- Abstention half-band `delta` is calibrated around the limit.
- Runtime states:
  - `SLM`
  - `HYBRID_ABSTAIN`
  - `BASELINE`

## 6) Outputs

Per task:
- `model_runs/<task>/sddf/thresholds.json`
- `model_runs/<task>/sddf/routing_policy.json`
- `model_runs/<task>/sddf/canonical_rows.jsonl`
- `model_runs/<task>/sddf/capability_curve.png`
- `model_runs/<task>/sddf/risk_curve.png`
- `model_runs/<task>/sddf/decision_matrix.png`

Global:
- `model_runs/sddf_summary.json`
- `model_runs/business_analytics/dashboard.json`
- `model_runs/business_analytics/dashboard.md`
