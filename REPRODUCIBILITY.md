# REPRODUCIBILITY GUIDE

**How to reproduce SDDF results exactly.**

---

## Environment Setup

### 1. Python Version
```bash
python --version
# Required: Python 3.10 or later
```

### 2. Install Dependencies
```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install exact versions
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Verify Environment
```python
import numpy as np
import sklearn
print(f"NumPy: {np.__version__}")
print(f"Scikit-learn: {sklearn.__version__}")
```

---

## Critical Parameters for Reproducibility

All parameters are defined in `sddf/config.py`. **Do not change these without documenting the change.**

```python
from sddf.config import (
    RANDOM_SEED,              # 42
    TASK_FAMILIES,            # 8 tasks
    SLM_MODELS,               # [0.5b, 3b, 7b]
    DIFFICULTY_FEATURES,      # 19 features
    LR_SOLVER,                # lbfgs
    LR_MAX_ITER,              # 1000
    FROZEN_TAU_CONSENSUS,     # Learned thresholds
    TIER_SLM_THRESHOLD,       # 0.50 (paper default)
    TIER_LLM_THRESHOLD,       # 0.30 (default)
    SENSITIVITY_THRESHOLD_RANGE,  # (0.2, 0.9)
    SENSITIVITY_THRESHOLD_STEP,   # 0.05
)
```

---

## Complete Reproducible Pipeline

### Run Full Pipeline (Recommended)

```bash
# Execute end-to-end: train → validation → test → routing → sensitivity analysis
python run_test_with_frozen_thresholds.py

# Expected runtime: ~5-10 minutes (depending on data size)
```

### Expected Output Structure

```
model_runs/test_with_frozen_thresholds/
├── validation_with_frozen.json          # Validation phase results
│   ├── summary: {tasks_validated: 8, slm_tier_count: 8, ...}
│   └── results: {task_family: {tau_frozen, rho_bar, per_model_metrics, ...}}
│
├── test_with_frozen.json                # Test phase results
│   ├── summary: {tasks_evaluated: 8, total_queries: 88, ...}
│   └── results: {task_family: {tier_decision, consensus_rho, ...}}
│
├── usecase_tiers_with_frozen.json       # Use case tier assignments
│   ├── validation: {UC1: {tier: SLM, rho_bar, ...}, UC2: {...}, ...}
│   └── test: {UC1: {tier: SLM, rho_bar, ...}, UC2: {...}, ...}
│
└── threshold_sensitivity.json            # Sensitivity analysis results
    ├── summary: {total_sweep_points: 105, threshold_range: (0.2, 0.9), ...}
    ├── optimal_thresholds: {slm_threshold: X, llm_threshold: Y, overall_accuracy: Z}
    └── sweep_results: [{slm_threshold, llm_threshold, tier_distribution, ...}, ...]
```

---

## Verify Results (Reproducibility Checks)

### 1. Check Frozen Thresholds

```bash
python << 'EOF'
from sddf import FROZEN_TAU_CONSENSUS

expected = {
    "classification": 0.6667,
    "code_generation": 1.0000,
    "information_extraction": 0.9167,
    "instruction_following": 0.9167,
    "maths": 0.3333,
    "retrieval_grounded": 0.9167,
    "summarization": 1.0000,
    "text_generation": 1.0000,
}

for task, tau in FROZEN_TAU_CONSENSUS.items():
    exp_tau = expected[task]
    match = "✅" if abs(tau - exp_tau) < 0.0001 else "❌"
    print(f"{match} {task}: {tau:.4f} (expected {exp_tau:.4f})")
EOF
```

**Expected output:** All ✅ (8/8 match)

### 2. Check Random Seed

```bash
python << 'EOF'
from sddf.config import RANDOM_SEED
print(f"Random seed: {RANDOM_SEED}")
assert RANDOM_SEED == 42, "Seed must be 42 for reproducibility!"
print("✅ Random seed is correct (42)")
EOF
```

### 3. Check Task Families

```bash
python << 'EOF'
from sddf.config import TASK_FAMILIES, NUM_TASKS
print(f"Task families ({NUM_TASKS}):")
for i, tf in enumerate(TASK_FAMILIES, 1):
    print(f"  {i}. {tf}")
assert NUM_TASKS == 8, "Must have exactly 8 task families!"
print("✅ All 8 task families present")
EOF
```

### 4. Check Use Cases

```bash
python << 'EOF'
from sddf.config import USE_CASES, NUM_USE_CASES
print(f"Use cases ({NUM_USE_CASES}):")
for uc_id, info in USE_CASES.items():
    print(f"  {uc_id}: {info['name']} → {info['task_family']}")
assert NUM_USE_CASES == 8, "Must have exactly 8 use cases!"
print("✅ All 8 use cases properly mapped")
EOF
```

### 5. Check Output Files Exist

```bash
python << 'EOF'
from pathlib import Path

output_dir = Path("model_runs/test_with_frozen_thresholds")
required_files = [
    "validation_with_frozen.json",
    "test_with_frozen.json",
    "usecase_tiers_with_frozen.json",
    "threshold_sensitivity.json",
]

print("Checking output files:")
for fname in required_files:
    fpath = output_dir / fname
    exists = "✅" if fpath.exists() else "❌"
    print(f"  {exists} {fname}")

assert all((output_dir / f).exists() for f in required_files), "Missing outputs!"
print("\n✅ All expected outputs present")
EOF
```

---

## Step-by-Step Reproduction (Manual)

If you want to understand each step:

### Step 1: Train Phase (Already Done)

Training happens offline and produces `FROZEN_TAU_CONSENSUS` (stored in `sddf/frozen_thresholds.py`).

```python
from sddf.training import train_all_tasks_multimodel

# This trains all 8 tasks × 3 models = 24 combinations
# Results: Logistic regression models + weights + biases (already frozen in config)
results = train_all_tasks_multimodel()
```

### Step 2: Validation Phase

```python
from sddf.validation_with_frozen import validate_all_tasks
from sddf import FROZEN_TAU_CONSENSUS

task_families = list(FROZEN_TAU_CONSENSUS.keys())
model_names = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]

validation_results = validate_all_tasks(
    task_families,
    model_names,
    query_difficulties_by_task,    # Loaded from val.jsonl
    query_results_by_task,         # Loaded from val.jsonl
)

print(f"Validated {validation_results['summary']['tasks_validated']} tasks")
```

### Step 3: Test Phase

```python
from sddf.test_with_frozen import run_test_phase
from sddf import FROZEN_TAU_CONSENSUS

test_results = run_test_phase(
    task_families,
    model_names,
    test_samples_by_task,          # Loaded from test.jsonl
)

print(f"Evaluated {test_results['summary']['total_queries']} test queries")
```

### Step 4: Use Case Tier Mapping

```python
from sddf.usecase_mapping import create_usecase_tier_report

usecase_report = create_usecase_tier_report(
    validation_results,
    test_results,
)

print("Use case tier assignments:")
for uc_id, info in usecase_report["test"].items():
    tier = info["tier"]
    rho_bar = info.get("rho_bar", "N/A")
    print(f"  {uc_id}: {tier} (ρ̄={rho_bar})")
```

### Step 5: Threshold Sensitivity Analysis

```python
from sddf.threshold_sensitivity_analysis import analyze_threshold_sensitivity

sensitivity = analyze_threshold_sensitivity(
    test_results,
    threshold_range=(0.2, 0.9),
    step=0.05,
)

optimal = sensitivity["optimal_thresholds"]
print(f"Optimal SLM threshold: {optimal['slm_threshold']:.4f}")
print(f"Optimal LLM threshold: {optimal['llm_threshold']:.4f}")
print(f"Overall weighted accuracy: {optimal['overall_accuracy']:.4f}")
```

### Step 6: Runtime Routing (Using Optimal Thresholds)

```python
from sddf.runtime_routing import tier_from_consensus_ratio

# Use optimal thresholds from sensitivity analysis
optimal_slm_thresh = sensitivity["optimal_thresholds"]["slm_threshold"]
optimal_llm_thresh = sensitivity["optimal_thresholds"]["llm_threshold"]

# Route UC1 with consensus ρ̄ = 0.9333
tier = tier_from_consensus_ratio(
    rho_bar=0.9333,
    slm_threshold=optimal_slm_thresh,
    llm_threshold=optimal_llm_thresh,
)

print(f"UC1 deployment tier: {tier}")
```

---

## Checking Reproducibility

### Identical Results

If you run the pipeline multiple times **with the same random seed**, you should get:
- ✅ Identical frozen thresholds
- ✅ Identical routing ratios (ρ, ρ̄)
- ✅ Identical use case tier assignments
- ✅ Identical sensitivity analysis results

### Differences Allowed

✓ **Minor numerical differences** (<0.0001) due to floating-point precision  
✓ **Output ordering** (JSON keys may appear in different order)  
✓ **Line breaks** in printed output  

### Differences NOT Allowed

✗ **Different frozen thresholds** (τ should be fixed)  
✗ **Different tier assignments** (deterministic given thresholds)  
✗ **Missing use cases** (should always have 8 UCs)  
✗ **Different sensitivity sweep results** (must be deterministic)  

---

## Troubleshooting

### Issue: Different random seed
```bash
# Check seed in sddf/config.py
grep "RANDOM_SEED" sddf/config.py
# Expected: RANDOM_SEED = 42
```

### Issue: Missing data files
```bash
# Check if data exists
ls -la model_runs/clean_deterministic_splits/classification/qwen2.5_0.5b/
# Expected: train.jsonl, val.jsonl, test.jsonl
```

### Issue: Different feature extraction
```bash
# Verify features are identical
python -c "from sddf.config import DIFFICULTY_FEATURES; print(len(DIFFICULTY_FEATURES), 'features')"
# Expected: 19 features
```

### Issue: Frozen thresholds not matching
```bash
# Verify τ values
python << 'EOF'
from sddf.frozen_thresholds import FROZEN_TAU_CONSENSUS
import json
print(json.dumps(FROZEN_TAU_CONSENSUS, indent=2))
EOF
```

---

## Documentation Files

**Consolidated to 3 files for reproducibility:**

1. **README_CONSOLIDATED.md** - Overview, quick start, architecture
2. **REPRODUCIBILITY.md** - This file: exact steps to reproduce
3. **sddf/config.py** - Centralized parameters (source of truth)

**Archive (for reference only, not needed for reproducibility):**
- All other .md files in root directory (30+ legacy docs)
- Consolidated into docs/ or marked as archived

---

## Success Criteria

✅ **You have successfully reproduced SDDF when:**
1. All 4 output JSON files generated without errors
2. Frozen thresholds match `FROZEN_TAU_CONSENSUS`
3. All 8 use cases assigned tiers (SLM/HYBRID/LLM)
4. Sensitivity analysis produces consistent optimal thresholds
5. No warnings or errors in console output

**Time required:** ~5-10 minutes for full pipeline

---

**Last Updated:** 2026-04-20  
**Random Seed:** 42  
**Status:** ✅ Fully reproducible
