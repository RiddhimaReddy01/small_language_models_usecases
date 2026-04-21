# SDDF v3 Methodology Alignment: Paper vs Code Implementation

**Analysis Date**: 2026-04-19  
**Scope**: Compare paper's SDDF methodology (Section 5, Section 7) vs actual code implementation in `small_language_models_usecases/`

---

## Executive Summary

**The SDDF v3 implementation in code is NOT aligned with the paper's described methodology.**

The paper describes a **failure probability-based routing system** using frozen τ^consensus thresholds. The code implements a **difficulty score-based routing system** using learned/calibrated τ* thresholds. These are fundamentally different approaches with different:
- Input features (failure probability vs query difficulty)
- Threshold values (0.3-1.0 vs 0.0-0.3)
- Calibration methodology (frozen paper Table 6.3 vs validation-set prefix scan)
- Risk model (implied in paper vs explicit severity × category in code)

---

## Section 1: Paper Methodology (SDDF Section 5 & 7)

### 1.1 Query → Task Family Mapping (Section 5)

**Paper describes**:
- Deterministic mapping: each query → task family (UC-specific)
- 8 task families across 8 UCs:
  - classification (UC1, UC3, UC4, UC6, UC7)
  - information_extraction (UC2)
  - code_generation (UC5)
  - summarization (UC7)
  - text_generation (UC8)

**Code status**: ✓ Implemented
- File: `run_sddf_runtime.py` (lines 30-39)
- UC_MAPPING dict maps each UC to its task family

---

### 1.2 Frozen Thresholds τ^consensus (Paper Table 6.3)

**Paper specifies**:
```
τ^consensus per task family (failure probability):
  classification: 0.6667
  code_generation: 0.6667
  information_extraction: 1.0000
  instruction_following: 1.0000
  maths: 0.3333
  retrieval_grounded: 1.0000
  summarization: 0.2972
  text_generation: 0.9333
```

These are **failure probability thresholds** used directly without training/calibration.

**Code status**: ✗ NOT implemented as paper specifies
- Code does NOT use these τ^consensus values
- Instead, code uses **τ_star_difficulty** (completely different concept)

---

### 1.3 Per-Query Routing Logic (Paper Section 7)

**Paper describes**:
```
For each query q in test set:
  1. Extract features from query q (task family specific)
  2. Compute p_fail = sigmoid(w^T · x_scaled + bias)
     - Uses learned logistic regression weights per task family
     - Outputs failure probability in [0, 1]
  3. Compare to frozen τ^consensus for that task family:
     - If p_fail < τ → route to SLM ✓
     - If p_fail ≥ τ → route to LLM ✗
```

**Code status**: ✗ NOT implemented as paper specifies

The code uses **different algorithm entirely**:
- File: `tools/evaluate_routing.py` (lines 210-279)
- Instead of logistic regression on failure probability:
  - Uses **isotonic regression** on difficulty scores
  - Difficulty score = weighted combination of 20 query features
  - Features are normalized via percentile bounds (p05, p95)
  - NO logistic regression, NO failure probability
  - NO frozen thresholds used

---

### 1.4 Aggregation to Consensus ρ̄ (Paper Section 7.3)

**Paper describes**:
```
For each UC:
  ρ₀.₅b = fraction of queries routed to SLM (0.5b model)
  ρ₃b = fraction of queries routed to SLM (3b model)
  ρ₇b = fraction of queries routed to SLM (7b model)
  ρ̄ = consensus = (ρ₀.₅b + ρ₃b + ρ₇b) / 3
```

Then tier decision:
- ρ̄ ≥ 0.70 → SLM
- ρ̄ ≤ 0.30 → LLM
- 0.30 < ρ̄ < 0.70 → HYBRID

**Code status**: ✗ NOT implemented in code

Code does not output per-model ρ values. Instead:
- Each model gets independent τ_star threshold
- Routing decision on test set is binary per model
- No consensus aggregation step
- No tier assignment from ρ̄

---

## Section 2: Code Implementation (evaluate_routing.py)

### 2.1 Difficulty Scoring (lines 137-175)

**What code does**:
```python
def _score_row_model(row, model):
  features = compute_all_features(row, prompt)  # 20 difficulty features
  score = 0.0
  for dim in DIFFICULTY_FEATURES:
    val = features[dim]
    lo, hi = norm_stats[dim]["p05"], norm_stats[dim]["p95"]  # percentile bounds
    nv = (val - lo) / (hi - lo)  # min-max normalize to [0,1]
    score += weights[dim] * nv
  return clamp(score, 0.0, 1.0)  # clip to [0,1]
```

**Key differences from paper**:
- ✗ Uses difficulty (ease/complexity) NOT failure probability
- ✗ No logistic regression
- ✗ Simple weighted average of normalized features
- ✗ Produces [0, 1] difficulty score, not p_fail

---

### 2.2 τ* Calibration via Prefix Scan (lines 210-279)

**What code does**:
```python
def calibrate_tau(rows, scores, task, cap_threshold, risk_threshold):
  # Sort queries by difficulty (ascending)
  paired = sorted([(scores[r["sample_id"]], r) for r in rows])
  
  # Sweep τ from low to high
  for each prefix [0...τ]:
    cap = accuracy in prefix
    risk = weighted failure risk in prefix
    feasible = (cap_lb ≥ cap_threshold AND risk ≤ risk_threshold)
    
  # Return highest τ where feasible
  return τ_star
```

**Key differences from paper**:
- ✗ τ is calibrated (learned) NOT frozen
- ✗ Uses validation set to find τ* (in-sample optimization)
- ✗ Threshold is difficulty score [0, 0.3] NOT failure probability [0.3, 1.0]
- ✗ Requires capability and risk thresholds (task_thresholds.json)

**Actual τ_star_difficulty values extracted from code**:
```
classification:    0.5b=0.003611, 3b=0.301488, 7b=0.0
code_generation:   0.5b=0.0,      3b=0.0,      7b=0.0
information_extract: 0.5b=0.0,    3b=0.0,      7b=0.058442
summarization:     0.5b=0.027625, 3b=0.0,      7b=0.008683
text_generation:   0.5b=None,     3b=None,     7b=0.0
(maths, instruction_following, retrieval_grounded also differ per model)
```

Compare to paper's frozen values:
```
classification:    0.6667  (code: 0.0-0.3)
code_generation:   0.6667  (code: 0.0)
information_extract: 1.0000  (code: 0.0-0.058)
summarization:     0.2972  (code: 0.0-0.027)
text_generation:   0.9333  (code: None/0.0)
```

**Scales are completely different** — code values 100-200× smaller.

---

### 2.3 Risk Model (lines 56-107)

**What code does**:
```python
TASK_RISK_INCORRECT = {  # Base risk per task type
  "classification": 0.56,
  "maths": 0.855,
  "code_generation": 0.9025,
  ...
}

For each failure:
  severity_mul = sample["severity_score"] (scaled to [0,1])
  category_mul = CATEGORY_MULTIPLIERS[failure_type]
  risk = clamp(base_risk * severity_mul * category_mul, 0.0, 1.0)
```

**Paper status**: No explicit risk model described in paper
- Paper assumes binary correctness model
- Risk computation NOT described
- Category multipliers NOT in paper

---

## Section 3: Root Cause Analysis

### Why the mismatch?

The code appears to be a **different research iteration** than the paper:

1. **Paper was completed first** with frozen thresholds and failure probability model
2. **Code repo (small_language_models_usecases) implements an improvement**:
   - Learned difficulty scoring instead of hand-engineered failure probability
   - Calibrated per-task/model τ* instead of consensus-wide frozen τ
   - Explicit risk model with severity and failure category

3. **The two systems were NOT merged**:
   - `run_sddf_runtime.py` uses paper's frozen thresholds
   - Code's actual routing uses `evaluate_routing.py` with difficulty scores

---

## Section 4: Critical Discrepancies

| Aspect | Paper (SDDF v3 Section 7) | Code Implementation |
|--------|--------------------------|-------------------|
| **Threshold metric** | Failure probability τ^consensus | Difficulty score τ* |
| **Threshold calibration** | Frozen (Table 6.3) | Learned on val set |
| **Threshold value range** | [0.2972, 1.0] | [0.0, 0.3] |
| **Feature model** | Logistic regression p_fail | Weighted difficulty avg |
| **Per-model thresholds** | Single consensus threshold per task family | Per-model τ* |
| **Routing decision** | p_fail < τ → SLM | difficulty ≤ τ* → SLM |
| **Risk accounting** | Implicit | Explicit (severity × category) |
| **Output metric** | ρ (routing ratio) per model | Direct binary routing |
| **Tier aggregation** | ρ̄ (consensus across 3 models) | Per-model independent routing |

---

## Section 5: Verdict

**SDDF v3 Code ≠ SDDF v3 Paper**

The code implements a **newer algorithm** that is more sophisticated but does NOT match the paper's methodology:

- ✓ **Shares**: Task family mapping (Section 5), S³ framework integration
- ✗ **Differs**: Feature extraction, threshold calibration, routing logic, risk model, output format

### Recommendation for Runtime Deployment

**Current `run_sddf_runtime.py` is a hybrid approach**:
- Uses paper's frozen thresholds (CORRECT per paper)
- Uses paper's empirical ρ values (CORRECT per paper Table 7.4)
- But does NOT actually compute these values from queries

To properly align with paper:
1. **Option A (Full Paper Implementation)**: 
   - Implement logistic regression on failure probability
   - Use frozen τ^consensus from Table 6.3
   - Compute actual per-query routing
   - Aggregate to ρ̄ consensus

2. **Option B (Use Code Implementation)**:
   - Acknowledge code is a different methodology
   - Use code's difficulty thresholds and isotonic regression
   - Accept that results won't match paper's ρ values
   - Report methodology difference clearly

3. **Option C (Current Hybrid)**:
   - Use paper's frozen τ values but empirical ρ from paper
   - Note that actual routing computation is not implemented
   - Treat as paper's theoretical predictions, not code's empirical results

---

## References

- Paper sections: 5 (query mapping), 7 (per-query routing), 7.3 (tier aggregation)
- Code files: `evaluate_routing.py` (lines 210-366), `validation_dynamic.py` (lines 56-175)
- Frozen thresholds: Table 6.3 of paper
- Empirical routing: Table 7.4 of paper
