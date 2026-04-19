# SDDF v3 Implementation Notes

## Custom Pipeline Implementation

This directory contains exploratory implementations of SDDF v3 TRAIN/VALIDATE/TEST phases:

- `sddf/train_paper_aligned_multimodel.py` — Train 3 Qwen models independently
- `sddf/validate_paper_aligned_multimodel.py` — Validate each model, compute consensus
- `run_full_pipeline_multimodel.py` — Full pipeline orchestrator

## Important Disclaimer

These are **custom implementations** created during exploration. They may not exactly match the official SDDF v3 pipeline that produced the paper results.

### Known Differences from Official Pipeline

1. **Data path**: Uses `sddf_training_splits/` (may differ from official source)
2. **Seed handling**: Custom seed assignment (official uses [42-46] for first 5 tasks, [42] for last 3)
3. **Validation algorithm**: Custom "3-strategy consensus" implementation
4. **Feature count**: 19 features (may differ from paper's 20)

## Official Results Location

The official SDDF v3 pipeline results are located in:
```
repos/small_language_models_usecases/model_runs/sddf_training_splits_slm_only/sddf_pipeline_artifacts_v3/
├── training_report.json
├── val_threshold_calibration_report.json
├── test_evaluation_report.json
└── (per-task/model/seed artifacts)
```

## Recommendations

For reproducing paper results:
1. Use the official repo code and artifacts in `repos/small_language_models_usecases/`
2. Reference `sddf/validation_dynamic.py` for the actual threshold selection algorithm
3. Check the artifact JSON files for exact methodology and results

For experimentation:
1. These custom implementations can serve as starting points
2. Modify as needed for research exploration
3. Do not assume exact match to paper values
