# SDDF v3 Alignment: Quick Reference

**TL;DR**: Code uses learned τ* per model; Paper uses frozen τ^consensus per task family. Three critical fixes needed.

---

## The Core Problem

| Aspect | Paper Says | Code Does |
|--------|-----------|-----------|
| **Feature extraction** | Logistic regression on F_i labels | Weighted average of features |
| **Threshold source** | Frozen τ^consensus (Table 6.3) | Learned per-model τ* |
| **Consensus step** | ρ̄ = avg(ρ_0.5b, ρ_3b, ρ_7b) | No aggregation |
| **Test routing** | use fixed τ per task family | Uses per-model τ |

---

## Three Required Fixes (In Order)

### FIX 1: Implement Logistic Regression in Train Phase
**File**: `sddf/training.py` (create new)

**What**: Replace weighted-average difficulty with logistic regression  
**How**:
```python
from sklearn.linear_model import LogisticRegression

# Per task family:
y_train = [1 if row.incorrect else 0 for row in train_rows]  # F_i
X_train = extract_features(train_rows)  # x_i^(t)

model = LogisticRegression().fit(X_train, y_train)
# Save: w_t, b, feature names
```

**Output**: `model_artifacts.json` with per-task-family weights  
**Paper ref**: Section 6.2.2

---

### FIX 2: Build Capability & Risk Curves in Val Phase
**File**: `sddf/validation_dynamic.py` (rewrite)

**What**: Replace prefix-scan τ* selection with proper C_m(d), R_m(d) curves  
**How**:
```python
# For each task × model:
1. Compute d_i = sigmoid(w_t^T x_i) for all val queries
2. Bin difficulties into K bins [0.0, 0.1, ..., 1.0]
3. For each bin k:
   - Ĉ_{m,t,k} = accuracy in bin k
   - R̂_{m,t,k} = avg risk in bin k
4. Smooth via isotonic regression (C monotone ↑, R monotone ↓)
5. Find τ_m* = max d where C_m(d) ≥ C_dyn AND R_m(d) ≤ R_dyn
```

**Output**: Frozen `tau_consensus.json`:
```json
{
  "classification": 0.6667,
  "code_generation": 0.6667,
  "information_extraction": 1.0000,
  ...
}
```

**Paper ref**: Section 6.3.1-6.3.3, Table 6.3

---

### FIX 3: Route Test Queries with Frozen Thresholds
**File**: `tools/sddf_runtime_routing.py` (create new)

**What**: Use frozen τ^consensus, not per-model τ*; aggregate ρ  
**How**:
```python
# Per test query:
for each model m in [qwen0.5b, qwen3b, qwen7b]:
  d_j = sigmoid(w_t^T x_j + b)  # frozen weights from Train
  tau = frozen_thresholds[task_family]  # consensus, not per-model!
  route = SLM if d_j < tau else LLM

# Aggregate:
rho^(m) = (count routes to SLM) / total queries
rho_consensus = mean(rho^(0.5b), rho^(3b), rho^(7b))

# Tier:
if rho_consensus >= 0.70: tier = SLM
elif rho_consensus <= 0.30: tier = LLM
else: tier = HYBRID
```

**Output**: Table 7.4 format with per-model ρ values  
**Paper ref**: Section 7.2-7.3

---

## Key Differences Explained

### Paper's Approach (Sections 6-7)

```
TRAIN: Fit w_t via logistic regression on failures
  ↓
VAL:   Build C_m(d), R_m(d) curves
       Find max feasible τ per (task, model) 
       Average across 3 models → τ^consensus
       FREEZE these values
  ↓
TEST:  Route with frozen τ^consensus (same for all 3 models)
       Aggregate ρ across 3 models → ρ̄
       Compare ρ̄ to S³ tier
```

### Code's Current Approach

```
TRAIN: Compute difficulty as weighted feature sum
  ↓
VAL:   Calibrate per-model τ* on validation data
       (different τ for each model)
  ↓
TEST:  Route with per-model τ* (not consensus)
       No aggregation step
```

---

## Testing Checklist

After implementing fixes, verify:

- [ ] **Train**: w_t values are learned (not hand-weighted)
- [ ] **Val**: C_m(d) is monotone increasing
- [ ] **Val**: R_m(d) is monotone decreasing
- [ ] **Val**: τ^consensus matches Table 6.3 ± 0.05
- [ ] **Test**: ρ values match Table 7.4 ± 0.05
- [ ] **Test**: Spearman corr(S³, SDDF) ≈ −0.726 (Table 8.3)
- [ ] **Test**: Tier agreement ≈ 62.5% (5/8 use cases, Section 8.1)

---

## Timeline

- **Week 1**: Fix 1 (Train logistic regression)
- **Week 2**: Fix 2 (Val curves + frozen τ)
- **Week 3**: Fix 3 (Test routing with consensus)
- **Week 4**: Validation against paper's Table 6.3, 7.4, 8.3

---

## Critical Files to Modify/Create

| File | Action | Reason |
|------|--------|--------|
| `sddf/training.py` | CREATE | Logistic regression (Fix 1) |
| `sddf/validation_dynamic.py` | REWRITE | C_m(d), R_m(d), τ selection (Fix 2) |
| `tools/sddf_runtime_routing.py` | CREATE | Test-time consensus routing (Fix 3) |
| `tools/evaluate_routing.py` | DELETE/ARCHIVE | Replaced by Fix 3 |
| `task_thresholds.json` | DELETE | Replace with frozen τ^consensus |
| `family_weights_learned.json` | DELETE | Replace with logistic regression w_t |

---

## See Also

- Full specification: `SDDF_v3_Alignment_Fixes.md`
- Paper sections: 6.2 (Train), 6.3 (Val), 7 (Test), 8-9 (Evaluation)
- Analysis: `SDDF_v3_methodology_alignment_analysis.md`
