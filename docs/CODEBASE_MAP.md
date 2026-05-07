# Codebase Map

This repository contains several generations of SDDF/S3 experiments. Use this map to keep the active path clear and avoid mixing paper-aligned code with archived prototypes.

## Canonical SDDF Path

Use these files for the paper-aligned train, validation, test, and runtime story:

- `sddf/training.py` - trains one difficulty/failure model per task family and SLM, writes frozen train artifacts.
- `sddf/validation.py` - paper-aligned capability/risk validation and `tau_consensus` freezing.
- `sddf/test.py` - applies frozen consensus thresholds on the test split without refitting.
- `sddf/runtime_routing.py` - library helpers for query routing, routing-ratio aggregation, and runtime tiering.
- `sddf/usecase_mapping.py` - maps UC1-UC8 to task families and applies runtime tiers.

The intended flow is:

```text
train -> validation -> freeze tau_consensus -> test -> runtime routing -> S3 bridge
```

## Runtime And S3

- `scripts/section7_runtime_routing.py` - artifact-based Section 7 runtime implementation.
- `scripts/pipelines/end_to_end_runtime_pipeline.py` - end-to-end runtime pipeline candidate.
- `framework/benchmarking/s3_sddf_bridge.py` - connects S3 governance scores to SDDF evidence.
- `sddf/s3_framework.py` and `sddf/s3_runtime_policy.py` - S3 tiering and runtime policy enforcement.

At runtime, S3 defines the governance envelope. SDDF decides query-level routing inside that envelope.

## Experimental Or Historical Paths

These are useful reference material but should not be treated as the default active pipeline:

- `framework/benchmarking/sddf_train_pipeline.py`
- `framework/benchmarking/sddf_val_pipeline.py`
- `framework/benchmarking/sddf_test_pipeline.py`
- `tools/archive_unused_2026-04-22/`
- `framework/benchmarking/archive_unused_2026-04-22/`
- scripts that simulate or randomly generate `p_fail`.

The `framework/benchmarking/sddf_*_pipeline.py` path is newer in places, but the validation step does not fully match the paper-aligned tau-freezing logic in `sddf/validation.py`.

## Generated Artifacts

The following should generally stay out of git and be regenerated as needed:

- `model_runs/`
- `logs/`
- `tmp/`
- `tasks__removed/`
- `repos/SLM_Research_Project/data/`
- `repos/SLM_Research_Project/evaluation/`

Keep only small deterministic fixtures under `tests/fixtures/` if tests need sample data.

## Paper Runtime Bands

The paper runtime tier bands are:

- `rho_bar >= 0.50` -> `SLM`
- `0.30 <= rho_bar < 0.50` -> `HYBRID`
- `rho_bar < 0.30` -> `LLM`

Older code and plots may still mention `0.70/0.30`; treat those as stale unless a specific sensitivity-analysis experiment is intentionally overriding the paper bands.
