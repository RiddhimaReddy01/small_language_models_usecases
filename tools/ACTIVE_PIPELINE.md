# Active Pipeline Map

Canonical scripts for the current SDDF workflow:

1. Inference by split
- `tools/run_train.py`
- `tools/run_val.py`
- `tools/run_test.py`
- Shared engine: `tools/run_inference_overnight.py`

2. Output scoring
- `tools/evaluate_outputs.py`

3. SDDF artifact generation
- `tools/generate_benchmark75_sddf.py`
- Wrapper: `tools/run_sddf_pipeline.py`

4. Phase reporting (uncertainty/significance + leakage checks)
- `tools/evaluate_test_phase.py`

5. Reproducibility bundle
- `tools/run_reproducibility_bundle.py`

6. Optional robustness/ablation sweep
- `tools/run_sddf_sensitivity.py`

Legacy utilities that are no longer part of the active pipeline are in `tools/legacy/`.
