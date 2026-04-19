# Paper to Code Mapping: Enterprise SLM Deployment Framework

**Paper**: A Unified Framework for Enterprise SLM Deployment: S³ Policy and SDDF Empirical Validation

**Repository**: SLM use cases codebase

---

## 1. SECTION 4: S³ Framework (Pre-Deployment Policy)

### Paper Definition
The S³ Framework is a multicriteria decision-making instrument that scores enterprise workloads on six dimensions and maps them to deployment tiers (Pure SLM, Hybrid, LLM Only).

**Six Dimensions:**
- **TC (Task Complexity)**: 1-5 scale (binary to expert-level judgment)
- **OS (Output Sensitivity)**: 1-5 scale (free-form to strict schema)
- **SK (Specialized Knowledge)**: 1-5 scale (no domain knowledge to regulated)
- **DS (Data Sensitivity)**: 1-5 scale (public to classified data)
- **LT (Latency Tolerance)**: 1-5 scale (hours to <100ms)
- **VL (Volume Load)**: 1-5 scale (dozens to millions per day)

### Paper Formula
```
S3 = (3·TC + 2·OS + 5·SK + 2·DS + 2·LT + 1·VL) / 15
```

### Code Implementation

#### File: [sddf/s3_feature_scoring.py](sddf/s3_feature_scoring.py)
Implements automated scoring of all six dimensions.

**Key Functions:**
- `score_task_complexity(payload)` → int[1-5]
- `score_output_structure(payload)` → int[1-5]
- `score_stakes(payload)` → int[1-5] (SK)
- `score_data_sensitivity(payload)` → int[1-5]
- `score_latency_tolerance(payload)` → int[1-5]
- `score_volume_load(payload)` → int[1-5]
- `score_s3_dimensions(payload)` → dict[str, int]

**Status**: ✅ Complete

---

#### File: [sddf/s3_framework.py](sddf/s3_framework.py)
Core S³ logic: thresholds, tier mapping, gate rules.

**Key Functions:**
- `prescreen_gate(scores)` → GateResult
  - Hard Rule 1: SK=5 → disqualified
  - Hard Rule 2: TC=5 and SK≥4 → disqualified
  - Flag Rule: SK≥4 → minimum tier is Hybrid

- `compute_s3_score(scores, weights)` → float
  - Computes weighted sum S³ = (Σ scores·weights) / (15)
  - Enforces constraint: w_SK ≥ w_TC

- `tier_from_s3(s3_score, gate)` → Tier
  - Maps score to tier: Pure SLM | Hybrid | LLM Only

**Status**: ✅ Complete

**Note**: Code weights differ from paper:
```
Paper:  TC=3, OS=2, SK=5, DS=2, LT=2, VL=1
Code:   TC=3, OS=2, SK=4, DS=2, LT=3, VL=1  ⚠️ MISMATCH
```

---

#### File: [sddf/s3_config_builder.py](sddf/s3_config_builder.py)
Builds S³ configuration from task definitions.

**Key Functions:**
- `normalize_weights(weights)` → dict[str, int]
- `build_task_scores(task_inputs)` → dict[str, dict]
- `build_s3_task_config(weights, task_inputs)` → dict

**Status**: ✅ Complete

**Threshold Mapping** (Paper Section 1.3):
```
Paper thresholds:
- τ₁ = 2.55 → Pure SLM
- τ₂ = 3.30 → Hybrid/LLM Only boundary

Code defaults (s3_framework.py):
- tau1 = 3.2
- tau2 = 4.0
⚠️ MISMATCH with paper
```

---

## 2. SECTION 5: Task-Family Mapping

### Paper Definition
Maps use cases to SDDF task families using zero-shot classification via `MoritzLaurer/deberta-v3-large-zeroshot-v2.0`.

**Eight Task Families:**
1. `classification` → UC1 (SMS Threat), UC3 (Support Ticket), UC4 (Product Review), UC6 (Clinical Triage)
2. `information_extraction` → UC2 (Invoice Field)
3. `code_generation` → UC5 (Code Review)
4. `summarization` → UC7 (Legal Contract)
5. `text_generation` → UC8 (Financial Report)
6. `instruction_following` (framework)
7. `maths` (framework)
8. `retrieval_grounded` (framework)

**Mapping Rules** (Section 5.2, Ambiguity/Composite):
- Primary family = highest zero-shot score
- Secondary family added if close to top-1 and constraints require it
- Conservative merge: disqualified > llm_only > hybrid > pure_slm

### Code Implementation

#### Status: ✅ COMPLETE (marked in your note)

**Task-family features stored in**:
- Schema: `sddf_feature_schema_v2.json` (referenced in paper appendix)
- Task family definitions in [sddf/difficulty.py](sddf/difficulty.py)

**Sample Task Families** (from difficulty_weights.py):
```python
TASK_FAMILIES = {
    'classification': {...},
    'code_generation': {...},
    'information_extraction': {...},
    'instruction_following': {...},
    'maths': {...},
    'retrieval_grounded': {...},
    'summarization': {...},
    'text_generation': {...},
}
```

---

## 3. SECTION 6: SDDF v3 Empirical Validation

### Paper Definition
Three-phase train-validate-test protocol that:
1. Models task difficulty using features
2. Fits logistic regression failure predictor per model
3. Computes capability C(d) and risk R(d) curves
4. Selects optimal routing threshold τ*

### 6.1 Difficulty Feature Extraction

**Paper (Section 6.2.1):**
```
Backbone features:
- Input length (n_in)
- Lexical entropy (H)
- Reasoning proxy (R̂)
- Constraint count (|Γ|)
- Parametric dependence (P)
- Dependency distance (D)

Interaction terms:
- (R̂ · |Γ|), (n_in · H), (P · R̂)
```

#### Code Implementation: [sddf/difficulty.py](sddf/difficulty.py)

**Key Functions:**
- `compute_n_in(text)` → float
- `compute_entropy(text)` → float
- `compute_reasoning_proxy(text)` → float
- `compute_constraint_count(text)` → int
- `compute_parametric_dependence(text)` → float
- `compute_dependency_distance(text)` → float
- `annotate_dominant_dimension(features)` → str

**Status**: ✅ Complete

---

### 6.2 Failure & Capability Signals

**Paper (Section 6.2.3-6.2.4):**
```
Failure: F_i = 1(incorrect_i ∨ invalid_i ∨ error_i)
Capability: C_i = 1 - F_i
Risk: R_i = 0 if F_i=0, else ErrorMagnitude_i ∈ [0,1]
```

#### Code Implementation

**Training Phase**: [sddf/training.py](sddf/training.py)
- Fits logistic regression on features → failure probability
- Per-model, per-task-family, per-seed

**Status**: ✅ Complete

---

### 6.3 Capability & Risk Curves

**Paper (Section 6.3.1):**
```
Binned by difficulty:
- Ĉ_m,t,k = #correct / n_m,t,k
- R̂_m,t,k = Σ R_i / n_m,t,k

Smooth estimates via soft bin membership P(k|d):
- C_m(d) = Σ P(k|d) · Ĉ_m,t,k
- R_m(d) = Σ P(k|d) · R̂_m,t,k
```

#### Code Implementation: [sddf/validation_dynamic.py](sddf/validation_dynamic.py)

**Key Functions:**
- `build_difficulty_curves(df, model, task_family, seed)`
  - Applies isotonic regression to enforce monotonicity
  - C_m(d) monotone non-decreasing
  - R_m(d) monotone non-increasing

**Status**: ✅ Complete

---

### 6.4 Constraint Definition & Threshold Selection

**Paper (Section 6.3.2-6.3.3):**
```
Constraints:
- C_dyn = C_baseline - ε_C
- R_dyn = R̄_val + ε_R

Threshold:
- τ_m*(t) = max d s.t. C_m(d) ≥ C_dyn AND R_m(d) ≤ R_dyn

If no strict feasible point:
- Apply fallback_min_violation_robust

Consensus across SLMs:
- τ_t^consensus = (1/3) Σ τ_m*(t) for {qwen 0.5b, 3b, 7b}
```

#### Code Implementation: [sddf/validation_dynamic.py](sddf/validation_dynamic.py)

**Key Functions:**
- `select_threshold_strict_feasible_max()`
- `select_threshold_fallback_min_violation_robust()`
- `compute_frozen_consensus_threshold()`

**Status**: ✅ Complete

---

### 6.5 Test Phase Evaluation

**Paper (Appendix A.3):**
Evaluates frozen thresholds on held-out test set with metrics:
- Accuracy/F1 per task-family and model
- ROC-AUC, PR-AUC, Brier score, ECE

#### Code Implementation: [sddf/test.py](sddf/test.py)

**Key Functions:**
- `evaluate_frozen_thresholds()`
- Computes metrics per (task-family, model) pair

**Status**: ✅ Complete

---

## 4. SECTION 7: Runtime Deployment

### Paper Definition
Two-stage process:
1. **Stage 1 (Pre-deployment)**: S³ defines governance tier
2. **Stage 2 (Runtime)**: SDDF provides per-query routing

**Query-Level Rule** (Section 7.2):
```
For each query x_j:
- Compute task-family features → p̂_fail^(m)(x_j)
- Compare against frozen threshold τ_m

route_m(x_j) = {
  SLM  if p̂_fail^(m)(x_j) < τ_m
  LLM  if p̂_fail^(m)(x_j) ≥ τ_m
}
```

**Use-Case Aggregation** (Section 7.3):
```
SLM routing ratio: ρ^(m) = (1/N) Σ 1[route_m(x_j) = SLM]

Consensus: ρ̄ = (1/3) Σ ρ^(m) for three SLMs

Decision:
- SLM   if ρ̄ ≥ 0.70
- HYBRID if 0.30 < ρ̄ < 0.70
- LLM   if ρ̄ ≤ 0.30
```

### Code Implementation

#### File: [sddf/s3_runtime_policy.py](sddf/s3_runtime_policy.py)

**Key Functions:**
- `enforce_runtime_policy()`
  - Applies S³ gate rules to incoming query
  - Returns enforcement decision

**Status**: ✅ Complete

---

## 5. SECTION 8-9: Evaluation & Results

### Paper (Section 8-9)
Evaluates tier correctness:
```
TierCorrect(u) = 1[Tier_S3_new(u) = Tier_RT(u)]
```

Results: 5/8 agreement (62.5%) at use-case level

### Code Implementation

**Benchmarking Pipeline**: [framework/benchmarking/](framework/benchmarking/)

**Key Scripts:**
- `sddf_train_pipeline.py`
- `sddf_val_pipeline.py`
- `sddf_test_pipeline.py`
- `s3_sddf_bridge.py` → Connects S³ tier to SDDF runtime routing

**Status**: ✅ Complete

---

## 6. Cross-Framework Validation

### Paper (Section 8)
Reports Spearman rank correlation:
```
ρ(S3_new, capability) = -0.726 (p=0.010)
ρ(S3_new, semantic_risk) = +0.726 (p=0.010)
```

Indicates convergent validity between managerial policy (S³) and empirical routing (SDDF).

### Code Status

**Cross-framework correlations** computed in:
- [sddf/validation.py](sddf/validation.py) (likely)

---

## Key File Dependency Map

```
s3_framework.py
├─ prescreen_gate()          [Paper 4.2: Gate Rules]
├─ compute_s3_score()        [Paper 4.1.1: Formula]
└─ tier_from_s3()            [Paper 4.1.3: Tier Mapping]

s3_feature_scoring.py
├─ score_task_complexity()   [Paper 4.1: Dimension Scoring]
├─ score_output_structure()
├─ score_stakes()
├─ score_data_sensitivity()
├─ score_latency_tolerance()
├─ score_volume_load()
└─ score_s3_dimensions()

difficulty.py
├─ compute_n_in()            [Paper 6.2.1: Difficulty Features]
├─ compute_entropy()
├─ compute_reasoning_proxy()
├─ compute_constraint_count()
├─ compute_parametric_dependence()
└─ compute_dependency_distance()

training.py                  [Paper 6.2.2: Logistic Regression]
├─ Fit per (family, model, seed)
└─ Difficulty-indexed feature vectors

validation_dynamic.py        [Paper 6.3: Curves & Thresholds]
├─ build_difficulty_curves()
├─ select_threshold_*()
└─ compute_frozen_consensus_threshold()

test.py                      [Paper 6.3.1: Test Evaluation]
├─ evaluate_frozen_thresholds()
└─ Metrics: ROC-AUC, PR-AUC, Brier, ECE

s3_runtime_policy.py         [Paper 7: Runtime]
└─ enforce_runtime_policy()

s3_sddf_bridge.py            [Paper 7.5: S³-to-SDDF Bridge]
└─ Connects policy tier to empirical thresholds
```

---

## Known Discrepancies ⚠️

### S³ Framework Mismatches
| Component | Paper (Section 4) | Code | Status |
|-----------|-------|------|--------|
| S³ Weights (SK) | 5 | 4 | ❌ WEIGHT MISMATCH |
| S³ Weights (LT) | 2 | 3 | ❌ WEIGHT MISMATCH |
| τ₁ threshold | 2.55 | 3.2 | ❌ THRESHOLD MISMATCH |
| τ₂ threshold | 3.30 | 4.0 | ❌ THRESHOLD MISMATCH |

### SDDF v3 Framework Mismatches (Critical)
| Component | Paper (Section 6-7) | Code | Status |
|-----------|-------|------|--------|
| Consensus Aggregation | τ^consensus = avg(3 SLMs) | Per-model independent | ❌ **MISSING** |
| Frozen Thresholds | Table 6.3 values | Learned per task/model | ❌ **DIVERGED** |
| Constraint Definition | C_dyn = C_baseline(LLM) - ε | Fixed per-task hardcoded | ❌ **DIVERGED** |
| Tier Assignment Logic | ρ̄ → SLM/HYBRID/LLM | Not computed | ❌ **MISSING** |

**See [SDDF Code vs Paper Methodology](memory/sddf_code_paper_methodology_reconciliation.md) for detailed analysis.**

---

## Critical Alignment Issues (Already Documented)

### Issue 1: Missing Consensus Aggregation ❌
**Paper specifies** (Section 7.3):
```
Task-family consensus threshold:
τ_t^consensus = (1/3) Σ τ_m*(t) across {qwen2.5_0.5b, qwen2.5_3b, qwen2.5_7b}

Use-case aggregation:
ρ̄ = (1/3) Σ ρ(m) across three SLMs
Then map ρ̄ → tier: {SLM if ≥0.70, HYBRID if 0.30-0.70, LLM if ≤0.30}
```

**Code currently**: 
- Per-model thresholds computed independently
- NO consensus averaging across models
- NO ρ̄ metric computed
- NO tier decision from aggregation

**Impact**: Cannot reproduce Table 7.4 (runtime behavior by use case)

### Issue 2: Constraint Definition Mismatch ❌
**Paper specifies** (Section 6.3.2):
```
C_dyn = C_baseline(LLM) - ε_C
R_dyn = R̄_validation(LLM) + ε_R
```
Where C_baseline and R̄_validation are actual LLM performance metrics.

**Code currently**: 
- Hardcoded per-task thresholds (see `task_thresholds.json`)
- NOT derived from actual LLM baseline
- Static across all model evaluations

**Impact**: τ* calibration targets are NOT aligned with paper's LLM reference baseline

### Issue 3: Frozen Threshold Values ❌
**Paper Table 6.3** provides frozen consensus thresholds:
```json
{
  "classification": 0.6667,
  "code_generation": 0.6667,
  "information_extraction": 1.0000,
  "instruction_following": 1.0000,
  "maths": 0.3333,
  "retrieval_grounded": 1.0000,
  "summarization": 0.2972,
  "text_generation": 0.9333
}
```

**Code currently**: 
- Computes task-family thresholds from data
- Values diverge significantly from paper (different scale, sources)

**Impact**: Cannot directly reproduce paper's runtime routing decisions

---

## Existing Alignment Action Plan

See: [SDDF Alignment Action Plan](memory/SDDF_Alignment_Action_Plan.md)

**Current Status**: 3 fixes pending
1. **Train logistic regression** → Align difficulty scoring with paper spec
2. **Val curves & constraints** → Fix constraint definition to reference LLM baseline
3. **Test runtime & consensus** → Implement consensus aggregation and tier assignment

**Timeline**: 4-week implementation roadmap already documented

---

## How to Use This Document

**To understand paper sections**: Navigate by section number (4, 5, 6, 7, etc.)

**To find code implementation**: Look for file paths: `sddf/filename.py`

**To understand discrepancies**: See the "Known Discrepancies" section and linked memory files

**To reproduce paper results**: 
- Start with [SDDF Alignment Action Plan](memory/SDDF_Alignment_Action_Plan.md)
- This mapping provides the reference points for each fix

---

**Document Generated**: 2026-04-19  
**Paper Version**: final_alignment.pdf  
**Codebase Root**: `/c/Users/riddh/OneDrive/Desktop/SLM use cases/`  
**Related Memory Files**:
- [SDDF Code vs Paper Methodology](memory/sddf_code_paper_methodology_reconciliation.md)
- [SDDF Framework Deep Dive](memory/sddf_framework_deep_dive.md)
- [SDDF Alignment Action Plan](memory/SDDF_Alignment_Action_Plan.md)
