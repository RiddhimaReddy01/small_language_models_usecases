# SDDF: SLM Deployment Decision Framework

**A production-ready system for intelligent routing between Small Language Models (SLMs) and Large Language Models (LLMs).**

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run complete pipeline (train → validation → test → routing)
python run_test_with_frozen_thresholds.py

# 3. View results
ls -la model_runs/test_with_frozen_thresholds/
```

**Expected output:** JSON files with tier assignments, routing decisions, and sensitivity analysis.

---

## System Overview

SDDF implements a **3-phase ML pipeline** that learns when SLMs can handle queries independently vs when they need LLM fallback:

### Phase 1: Train
- Extract 19 difficulty features from queries (input length, constraints, complexity metrics)
- Train logistic regression: `P_fail(q) = sigmoid(weights · features + bias)` per task family
- Produces: Learned feature weights, failure probability predictions
- **Reproducibility:** Random seed = 42, LogisticRegression(solver=lbfgs, max_iter=1000)

### Phase 2: Validation
- Apply trained model to unseen validation data
- Measure SLM capability (accuracy) and risk (error severity) per task
- Compute consensus ρ̄ across 3 SLM models: `ρ̄ = mean(ρ_0.5b, ρ_3b, ρ_7b)`
- **Reproducibility:** Frozen thresholds τ from training, applied consistently

### Phase 3: Test
- Apply frozen thresholds to test data
- Route queries: if `p_fail < τ` → SLM, else → LLM
- Assign deployment tiers based on consensus ratio ρ̄
- **Reproducibility:** Thresholds fixed (not learned on test set)

### Runtime
- Map enterprise use cases (8 UC) to task families (8 task families, 3 SLMs = 24 combinations)
- Route individual queries using frozen thresholds
- Aggregate routing decisions into tier recommendations (SLM/HYBRID/LLM)
- **Tier Assignment:** Optimized via SelectiveNet-inspired threshold sensitivity analysis

---

## Critical Parameters (for ML Reproducibility)

All parameters are centralized in `sddf/config.py`:

| Parameter | Value | Purpose | Reproducible? |
|-----------|-------|---------|---|
| **Random Seed** | 42 | Logistic regression initialization | ✅ |
| **Task Families** | 8 | NLP task types | ✅ |
| **SLM Models** | qwen2.5 [0.5b, 3b, 7b] | Model variants | ✅ |
| **Features** | 19 linguistic + syntactic | Difficulty prediction | ✅ |
| **LR Solver** | lbfgs | Optimization algorithm | ✅ |
| **LR Max Iterations** | 1000 | Convergence criterion | ✅ |
| **Frozen τ (consensus)** | {task: threshold} | Fixed routing thresholds | ✅ |
| **Sensitivity Sweep** | (0.2, 0.9), step=0.05 | Threshold optimization range | ✅ |
| **Tier SLM Threshold** | 0.70 (default) | ρ̄ ≥ 0.70 → SLM | ✅ |
| **Tier LLM Threshold** | 0.30 (default) | ρ̄ ≤ 0.30 → LLM | ✅ |

**Optimal thresholds** (from sensitivity analysis) override defaults at runtime.

---

## Architecture

```
TRAINING DATA
  ├─ sddf_training_splits/{task}/{model}/[train.jsonl, val.jsonl, test.jsonl]
  └─ Feature extraction → Logistic regression per (task, model)
       └─ Outputs: Failure probabilities, weights, biases

                            ↓

FROZEN THRESHOLDS (seed42)
  ├─ τ per task family learned from training
  └─ Immutable at runtime (stored in sddf/frozen_thresholds.py)

                            ↓

VALIDATION PHASE
  ├─ Apply frozen τ to validation data
  ├─ Compute per-task ρ = (# SLM routed) / (# total)
  └─ Aggregate: ρ̄ = mean(ρ_0.5b, ρ_3b, ρ_7b)

                            ↓

TEST PHASE
  ├─ Apply frozen τ to test data
  ├─ Route: if p_fail < τ → SLM, else → LLM
  └─ Assign tiers based on consensus ρ̄

                            ↓

THRESHOLD SENSITIVITY ANALYSIS (SelectiveNet-inspired)
  ├─ Sweep: (slm_threshold, llm_threshold) combinations
  ├─ Objective: Maximize weighted accuracy across tiers
  └─ Outputs: Optimal thresholds (data-driven, not hardcoded)

                            ↓

RUNTIME ROUTING
  ├─ Use case → Task family mapping (8 UCs, 8 families)
  ├─ Per-query routing: compare p_fail < τ
  ├─ Aggregate: ρ̄ per task family
  └─ Tier assignment: Use optimal thresholds from sensitivity analysis

                            ↓

DEPLOYMENT RECOMMENDATION
  ├─ SLM tier if ρ̄ ≥ slm_threshold (use SLM only)
  ├─ LLM tier if ρ̄ ≤ llm_threshold (use LLM only)
  └─ HYBRID if llm_threshold < ρ̄ < slm_threshold (per-query routing)
```

---

## Code Structure

```
sddf/
├── config.py                        # 🔑 REPRODUCIBILITY: All parameters
├── frozen_thresholds.py             # τ values (fixed at runtime)
├── train_paper_aligned_multimodel.py # Phase 1: Train logistic regression
├── validation_with_frozen.py        # Phase 2: Validation
├── test_with_frozen.py              # Phase 3: Test
├── runtime_routing.py               # Runtime: Query routing, tier assignment
├── usecase_mapping.py               # Use case → task family mapping
├── threshold_sensitivity_analysis.py # Threshold optimization (SelectiveNet)
└── [other modules...]

run_test_with_frozen_thresholds.py  # 🔑 ENTRY POINT: End-to-end pipeline

model_runs/
├── sddf_training_splits/            # Training data (8 tasks × 3 models)
├── clean_deterministic_splits/      # Validation/test data
└── test_with_frozen_thresholds/     # Results (JSON + visualizations)
```

---

## How to Reproduce Experiments

### Full Pipeline

```bash
# Run everything: train → validation → test → routing → sensitivity analysis
python run_test_with_frozen_thresholds.py

# Check outputs
cat model_runs/test_with_frozen_thresholds/validation_with_frozen.json
cat model_runs/test_with_frozen_thresholds/test_with_frozen.json
cat model_runs/test_with_frozen_thresholds/usecase_tiers_with_frozen.json
cat model_runs/test_with_frozen_thresholds/threshold_sensitivity.json
```

### Step-by-Step

```python
# Step 1: Load frozen thresholds
from sddf import FROZEN_TAU_CONSENSUS
print(FROZEN_TAU_CONSENSUS)  # {task: tau} for all 8 tasks

# Step 2: Route a query
from sddf import route_query
decision = route_query(p_fail=0.45, task_family="classification")
# → "SLM" if p_fail < 0.6667, else "LLM"

# Step 3: Aggregate across 3 models
from sddf import consensus_routing_ratio, tier_from_consensus_ratio
rho_bar = consensus_routing_ratio({"qwen2.5_0.5b": 0.8, "qwen2.5_3b": 0.9, "qwen2.5_7b": 1.0})
# → 0.9333

tier = tier_from_consensus_ratio(rho_bar, slm_threshold=0.70, llm_threshold=0.30)
# → "SLM" (since 0.9333 ≥ 0.70)

# Step 4: Map to use case
from sddf.usecase_mapping import get_task_family, assign_usecase_tiers
task_family = get_task_family("UC1")  # → "classification"
tiers = assign_usecase_tiers({"classification": 0.9333}, slm_threshold=0.70, llm_threshold=0.30)
# → {"UC1": {"tier": "SLM", ...}}
```

---

## Key Concepts

### Frozen Thresholds (τ)
- Learned during training phase on 3 SLM models
- Fixed immutably at runtime (not re-learned on validation/test)
- Per-task-family: different difficulty levels per task type
- Example: τ = 0.6667 for classification, 0.3333 for maths

### Routing Probability (ρ)
- Fraction of queries routed to SLM: `ρ = (# SLM) / (# total)`
- Computed per model, then aggregated across 3 models
- Consensus ratio: `ρ̄ = mean(ρ_0.5b, ρ_3b, ρ_7b)`
- Range: [0, 1], where 1 = all queries to SLM, 0 = all to LLM

### Tier Assignment (Data-Driven)
- Not fixed rules, but optimized thresholds
- **SelectiveNet principle:** Find thresholds that maximize accuracy while minimizing LLM fallback
- Default thresholds (0.70/0.30) are starting points
- Optimal thresholds computed via sensitivity analysis sweep
- Always use optimal thresholds if available

### Use Case Mapping
- 8 enterprise use cases → 8 NLP task families
- UC inherits tier from task family
- Examples:
  - UC1 (SMS Threat Detection) → classification
  - UC2 (Invoice Extraction) → information_extraction
  - UC5 (Code Review) → code_generation

---

## Reproducibility Guarantees

✅ **Deterministic:** Random seed fixed (42)  
✅ **Documented:** All parameters in `sddf/config.py`  
✅ **Traceable:** Frozen thresholds versioned  
✅ **Auditable:** Config, features, models all centralized  
✅ **Testable:** Expected outputs documented  

---

## Files (For Reference)

**Essential:**
- `sddf/config.py` - All parameters for reproducibility
- `run_test_with_frozen_thresholds.py` - End-to-end pipeline
- `sddf/frozen_thresholds.py` - Frozen τ values
- `sddf/runtime_routing.py` - Query routing logic
- `sddf/usecase_mapping.py` - UC → task family mapping
- `sddf/threshold_sensitivity_analysis.py` - Threshold optimization

**Supporting:**
- `sddf/train_paper_aligned_multimodel.py` - Training logic
- `sddf/validation_with_frozen.py` - Validation phase
- `sddf/test_with_frozen.py` - Test phase
- `requirements.txt` - Dependencies

---

## References

- **Paper:** "A Unified Framework for Enterprise SLM Deployment"
- **Framework:** SDDF (SLM Deployment Decision Framework)
- **Inspiration:** SelectiveNet (confidence-coverage tradeoff optimization)
- **Random Seed:** 42 (for reproducibility)

---

**Status:** ✅ Production-ready | Fully reproducible | All parameters documented
