# Train / Val / Test Protocol Table (No Leakage)

| Phase | Primary Purpose | Inputs Allowed | Forbidden Inputs | Outputs | Statistical Use |
|---|---|---|---|---|---|
| Train | Learn difficulty representation and family weights | Train split rows, train references | Val/test rows, any val/test labels | Family weights, train curves | Model fitting only |
| Val | Select operating policy (`tau`, band, routing thresholds) | Val split rows, frozen train artifacts | Test rows/outcomes | Calibrated routing policy | Selection stability (CIs/significance for tuning) |
| Test | Frozen-policy generalization audit | Test split rows, frozen train+val policy | Any refit/recalibration using test outcomes | Final metrics/claims | Headline CIs/significance for claims |

## Leakage Guards

1. `report_split` is explicit (`train`, `val`, or `test`) and evaluated independently.
2. `threshold_split` must remain `val` for frozen-policy checks in headline test reporting.
3. No parameter updates after entering test evaluation.
4. Any tuning after test must be performed on val and re-tested on a fresh holdout.

## Recommended Reporting

1. Validation report:
 - CIs and significance for policy-selection candidates.
 - Used for tuning decisions only.
2. Test report:
 - Frozen policy only.
 - CIs/significance on final headline metrics.
3. Separate deployment report:
 - Cost/latency/safety tradeoffs.
 - Keep separate from scientific train/val/test claim tables.

