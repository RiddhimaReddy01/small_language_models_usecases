# SDDF Runtime Router

Production-oriented implementation of the S3 + SDDF decision flow for enterprise SLM/LLM routing.

This README explains:
- what SDDF does in this repo,
- how S3 policy and SDDF runtime interact,
- how to run the project end-to-end.

## What This Repo Implements

The repository combines two layers:

1. `S3` governance layer
- Scores workload dimensions (`TC`, `OS`, `SK`, `DS`, `LT`, `VL`).
- Applies hard/flag gates and computes an S3 tier (`pure_slm`, `hybrid`, `llm_only`, `disqualified`).
- Files: `sddf/s3_framework.py`, `sddf/s3_runtime_policy.py`, `sddf/s3_feature_scoring.py`.

2. `SDDF` runtime layer
- Uses frozen per-task thresholds (`tau`) and predicted failure probability (`p_fail`).
- Routes each query to `SLM` or `LLM`.
- Aggregates routing into task/use-case tier decisions (`SLM`, `HYBRID`, `LLM`).
- Files: `sddf/frozen_thresholds.py`, `sddf/runtime_routing.py`, `sddf/usecase_mapping.py`.

The main pipeline entrypoint is:
- `run_test_with_frozen_thresholds.py`

## Runtime Behavior: S3 -> SDDF

At runtime, the flow is:

1. S3 prescreen and tiering
- `prescreen_gate(scores)` blocks unsafe workloads:
  - `SK == 5` -> `disqualified`
  - `TC == 5 and SK >= 4` -> `disqualified`
  - `SK >= 4` -> minimum tier at least `hybrid`
- `compute_s3_score(scores, weights)` calculates weighted S3 score.
- `tier_from_s3(...)` gives governance tier.

2. SDDF per-query routing
- For each task family, get frozen threshold `tau`.
- Route with `route_query(p_fail, task_family)`:
  - if `p_fail < tau` -> `SLM`
  - else -> `LLM`

3. SDDF consensus and deployment tier
- Aggregate model-level routing ratios into `rho_bar`.
- Convert `rho_bar` to deployment tier with `tier_from_consensus_ratio`:
  - `rho_bar >= slm_threshold` -> `SLM`
  - `rho_bar <= llm_threshold` -> `LLM`
  - else -> `HYBRID`

4. Final policy enforcement
- Apply S3 governance constraints to runtime route state using:
  - `enforce_runtime_policy(final_tier, proposed_route_state, ...)`
- `llm_only` and `disqualified` always force baseline/LLM lane.

This gives a policy-first, data-calibrated runtime decision.

## Repository Layout

- `sddf/`: core framework modules (S3 + SDDF logic)
- `run_test_with_frozen_thresholds.py`: end-to-end validation/test/tiering pipeline
- `scripts/`: auxiliary experiments, demos, and analysis scripts
- `model_runs/`: split data, artifacts, and generated outputs
- `docs/`: manuscript and archived documentation artifacts
- `BENCHMARK_2024_OFFICIAL_DATASETS.md`: benchmark source mapping

## Quick Start

1. Create environment and install dependencies

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

2. Run the end-to-end SDDF pipeline

```powershell
python run_test_with_frozen_thresholds.py
```

3. Inspect outputs

Generated in:
- `model_runs/test_with_frozen_thresholds/validation_with_frozen.json`
- `model_runs/test_with_frozen_thresholds/test_with_frozen.json`
- `model_runs/test_with_frozen_thresholds/usecase_tiers_with_frozen.json`
- `model_runs/test_with_frozen_thresholds/threshold_sensitivity.json`

## Programmatic Usage

```python
from sddf import route_query, tier_from_consensus_ratio
from sddf.s3_framework import decide_s3_and_route
from sddf.s3_runtime_policy import enforce_runtime_policy

# SDDF query routing
decision = route_query(p_fail=0.42, task_family="classification")

# SDDF tiering from consensus ratio
tier = tier_from_consensus_ratio(rho_bar=0.64, slm_threshold=0.70, llm_threshold=0.30)

# S3 governance + bridge tau
s3 = decide_s3_and_route(
    scores={"TC": 3, "OS": 2, "SK": 3, "DS": 3, "LT": 2, "VL": 2},
    weights={"TC": 4, "OS": 3, "SK": 5, "DS": 3, "LT": 2, "VL": 2},
    tau_risk=0.8,
    tau_cap=0.7,
)

# enforce policy on runtime decision
route_state = enforce_runtime_policy(
    final_tier=s3["final_tier"],
    proposed_route_state="SLM",
)
```

## Testing

Run all tests:

```powershell
pytest -q
```

Run a focused subset:

```powershell
pytest tests/test_s3_framework_tiers.py -q
pytest tests/test_sddf_validator.py -q
```

## Data and Benchmark Sources

Official benchmark/task-family source mapping is documented in:
- `BENCHMARK_2024_OFFICIAL_DATASETS.md`

If you need to download datasets:

```powershell
python download_benchmark_2024_datasets.py --list-tasks
python download_benchmark_2024_datasets.py
```

## Notes

- Prefer `run_test_with_frozen_thresholds.py` as the canonical runnable entrypoint.
- Some scripts under `scripts/` are research/experiment helpers and may assume specific local artifact layouts.
- For strict reproducibility settings and expected artifacts, see `REPRODUCIBILITY.md`.
