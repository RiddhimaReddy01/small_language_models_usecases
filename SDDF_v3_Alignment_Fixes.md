# SDDF v3 Code Alignment Fixes: Train-Val-Test Pipeline

**Goal**: Make code implementation match paper's SDDF v3 methodology exactly  
**Date**: 2026-04-19  
**Paper Reference**: Sections 6.2 (Train), 6.3 (Val), 7 (Test Runtime)

---

## PHASE 1: TRAIN (Per Task Family)

### Paper Specification (Section 6.2)

**Input**: Training split with `x_i^(t)` features and `F_i` failure labels per task family

**Step 1: Feature Extraction (6.2.1)**
```
x_i^(t) = [x_{i1}, x_{i2}, ..., x_{ip_t}]

Shared backbone (all families):
  - Input length n_in
  - Lexical entropy H
  - Reasoning proxy R̂
  - Constraint count |Γ|
  - Parametric dependence P
  - Dependency distance D

Interaction terms:
  - (R̂ · |Γ|), (n_in · H), (P · R̂)

Task-specific augmentations:
  classification:         negation_count, entity_density, sentiment_lexicon_score
  code_generation:        code_symbol_density, algorithm_keyword_density
  information_extraction: entity_count, slot_marker_density
  instruction_following:  format_keyword_density, step_marker_density
  maths:                  digit_ratio, symbol_density, quantity_mention_density
  summarization:          compression_ratio, discourse_marker_density
  text_generation:        type_token_ratio, flesch_kincaid_grade
```

**Step 2: Difficulty Function (6.2.2)**
```
d_i = σ(w_t^T x_i^(t))

Where:
  - σ(·) is the logistic function: σ(z) = 1/(1 + e^(-z))
  - w_t is estimated via LOGISTIC REGRESSION on failure labels F_i
  - d_i ∈ [0, 1] represents predicted failure probability
```

**Step 3: Failure/Capability Signals (6.2.3)**
```
F_i = 1(incorrect_i^m ∨ invalid_i^m ∨ error_i)     [Binary: 0 or 1]
C_i = 1 − F_i                                        [Capability = not failed]
```

**Step 4: Risk Construction (6.2.4)**
```
R_i = {  0,              if F_i = 0
      {  ErrorMagnitude_i, if F_i = 1

ErrorMagnitude by task family:
  classification:         1(y_pred ≠ y_true)
  code_generation:        1 − (#tests passed / #tests total)
  information_extraction: 1 − FieldF1_i
  instruction_following:  1 − (#constraints satisfied / #constraints total)
  maths:                  1 − (#correct terms / #total terms)
  retrieval_grounded:     1 − (α·AnswerCorrectness + (1−α)·GroundingScore)
  summarization:          1 − Similarity(y_pred, y_true)
  text_generation:        1 − QualityScore_i
```

### Current Code Status
- ❌ Does NOT fit logistic regression
- ❌ Uses weighted average of features instead of w_t^T x
- ❌ No explicit failure/risk computation per paper's definitions
- ✓ Has task-family-specific feature sets (partial)

### REQUIRED FIXES

#### Fix 1.1: Implement Logistic Regression Fitting
```python
# FILE: sddf/training.py (NEW)

from sklearn.linear_model import LogisticRegression
import numpy as np

def fit_difficulty_model(task_family: str, train_rows: list[dict]) -> dict:
    """
    Fit logistic regression per paper Section 6.2.2.
    
    Returns:
        model_artifact = {
            'task_family': str,
            'weights_w': np.array,      # w_t coefficients
            'intercept_b': float,
            'feature_names': list,
            'model': LogisticRegression,
            'train_set_size': int
        }
    """
    # 1. Extract features x_i^(t) per Section 6.2.1
    X_train = np.array([
        extract_task_family_features(row, task_family)
        for row in train_rows
    ])
    
    # 2. Extract failure labels F_i per Section 6.2.3
    y_train = np.array([
        int(row.get('incorrect') or row.get('invalid') or row.get('error', False))
        for row in train_rows
    ])
    
    # 3. Fit logistic regression per Section 6.2.2
    lr = LogisticRegression(
        penalty='l2',
        C=1.0,           # Regularization strength
        max_iter=1000,
        solver='lbfgs',  # For stability
        random_state=42
    )
    lr.fit(X_train, y_train)
    
    return {
        'task_family': task_family,
        'weights_w': lr.coef_[0],        # shape (n_features,)
        'intercept_b': lr.intercept_[0],
        'feature_names': get_feature_names(task_family),
        'model': lr,
        'train_set_size': len(train_rows)
    }


def extract_task_family_features(row: dict, task_family: str) -> list:
    """
    Extract x_i^(t) per Section 6.2.1.
    Includes backbone + task-specific + interaction terms.
    """
    features = {}
    
    # BACKBONE FEATURES (all families)
    prompt = row.get('prompt_text', '')
    target = row.get('target', '')
    
    features['input_length'] = len(prompt.split())
    features['lexical_entropy'] = compute_entropy(prompt)
    features['reasoning_proxy'] = estimate_reasoning_complexity(prompt)
    features['constraint_count'] = count_constraints(prompt)
    features['parametric_dependence'] = count_parameters(prompt)
    features['dependency_distance'] = compute_dependency_distance(prompt)
    
    # INTERACTION TERMS
    features['reasoning_x_constraints'] = (
        features['reasoning_proxy'] * features['constraint_count']
    )
    features['length_x_entropy'] = (
        features['input_length'] * features['lexical_entropy']
    )
    features['param_x_reasoning'] = (
        features['parametric_dependence'] * features['reasoning_proxy']
    )
    
    # TASK-SPECIFIC AUGMENTATIONS
    if task_family == 'classification':
        features['negation_count'] = count_negations(prompt)
        features['entity_density'] = count_entities(prompt) / len(prompt.split())
        features['sentiment_lexicon_score'] = score_sentiment_words(prompt)
        features['dep_tree_depth'] = estimate_syntactic_depth(prompt)
    
    elif task_family == 'code_generation':
        features['code_symbol_density'] = count_code_symbols(prompt) / len(prompt)
        features['algorithm_keyword_density'] = count_algo_keywords(prompt) / len(prompt.split())
        features['embedding_query_context_cosine'] = compute_query_context_similarity(row)
    
    elif task_family == 'information_extraction':
        features['entity_count'] = count_entities(prompt)
        features['entity_type_count'] = count_entity_types(prompt)
        features['slot_marker_density'] = count_slot_markers(prompt) / len(prompt.split())
        features['bm25_query_context_max'] = compute_bm25_max(row)
    
    # ... (continue for other families per Appendix A.1)
    
    return [features.get(fn, 0.0) for fn in get_feature_names(task_family)]
```

#### Fix 1.2: Compute Difficulty Predictions (d_i)
```python
def compute_difficulty_scores(rows: list[dict], model_artifact: dict) -> np.array:
    """
    Compute d_i = σ(w_t^T x_i^(t)) per Section 6.2.2.
    
    Args:
        rows: list of query dicts
        model_artifact: output from fit_difficulty_model()
    
    Returns:
        difficulties: [0, 1] array of predicted failure probabilities
    """
    task_family = model_artifact['task_family']
    
    # Extract features for all rows
    X = np.array([
        extract_task_family_features(row, task_family)
        for row in rows
    ])
    
    # Use fitted logistic regression
    model = model_artifact['model']
    difficulties = model.predict_proba(X)[:, 1]  # P(failure=1)
    
    return difficulties  # Returns ∈ [0, 1]
```

#### Fix 1.3: Compute Risk Values (R_i)
```python
def compute_risk_values(rows: list[dict], task_family: str) -> np.array:
    """
    Compute R_i per Section 6.2.4 (Error-Based Definition).
    
    Returns:
        risks: [0, 1] array of normalized error magnitudes
    """
    risks = []
    
    for row in rows:
        # Check if failed per Section 6.2.3
        failed = row.get('incorrect') or row.get('invalid') or row.get('error', False)
        
        if not failed:
            risks.append(0.0)
        else:
            # Compute ErrorMagnitude_i per task family
            error_mag = compute_error_magnitude(row, task_family)
            risks.append(error_mag)
    
    return np.array(risks)


def compute_error_magnitude(row: dict, task_family: str) -> float:
    """
    ErrorMagnitude_i per Section 6.2.4 table.
    Range: [0, 1]
    """
    if task_family == 'classification':
        return 1.0 if row['pred'] != row['target'] else 0.0
    
    elif task_family == 'code_generation':
        tests_passed = row.get('tests_passed', 0)
        tests_total = row.get('tests_total', 1)
        if tests_total == 0:
            return 1.0
        return 1.0 - (tests_passed / tests_total)
    
    elif task_family == 'information_extraction':
        field_f1 = row.get('field_f1_score', 0.0)
        return 1.0 - field_f1
    
    elif task_family == 'instruction_following':
        constraints_sat = row.get('constraints_satisfied', 0)
        constraints_total = row.get('constraints_total', 1)
        if constraints_total == 0:
            return 1.0
        # Hard violations = 1.0 risk
        if row.get('hard_violation', False):
            return 1.0
        return 1.0 - (constraints_sat / constraints_total)
    
    elif task_family == 'summarization':
        similarity = row.get('rouge_score', 0.0)
        return 1.0 - similarity
    
    elif task_family == 'text_generation':
        quality = row.get('quality_score', 0.0)
        return 1.0 - quality
    
    # ... (other families)
    
    return 0.5  # default


def store_train_artifacts(artifacts: dict, output_path: Path):
    """
    Save per-task-family w_t, b, feature names.
    Later used in Val and Test phases.
    
    Output structure:
    {
        'classification': {
            'weights_w': [...],
            'intercept_b': float,
            'feature_names': [...],
            'timestamp': str
        },
        'code_generation': {...},
        ...
    }
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump({
            k: {
                'weights_w': v['weights_w'].tolist(),
                'intercept_b': float(v['intercept_b']),
                'feature_names': v['feature_names'],
                'train_set_size': v['train_set_size']
            }
            for k, v in artifacts.items()
        }, f, indent=2)
```

---

## PHASE 2: VALIDATION (Per Task Family × Model)

### Paper Specification (Section 6.3)

**Input**: 
- Validation split with computed d_i (from Train phase)
- Frozen w_t, b from training
- Baseline performance C_baseline, R_val

**Step 1: Bin-Based Capability & Risk Curves (6.3.1)**
```
Partition difficulty range [0, 1] into K bins.
For each bin k and model m:

    Ĉ_{m,t,k} = #correct / n_{m,t,k}
    R̂_{m,t,k} = Σ R_i / n_{m,t,k}

Smooth estimates via soft bin membership P(k|d):

    C_m(d) = Σ_k P(k|d) · Ĉ_{m,t,k}
    R_m(d) = Σ_k P(k|d) · R̂_{m,t,k}
```

**Step 2: Constraint Definition (6.3.2)**
```
Acceptable operating conditions:

    C_dyn = C_baseline − ε_C
    R_dyn = R̄_val + ε_R

Where:
    C_baseline: target capability level (e.g., 0.85)
    R̄_val:     average validation risk
    ε_C, ε_R:   small robustness margins (e.g., 0.05)
```

**Step 3: Threshold Selection (6.3.3)**
```
τ_m*(t) = max d  s.t.  C_m(d) ≥ C_dyn  AND  R_m(d) ≤ R_dyn

If strict feasible region is empty:
    Use fallback: τ_m* = min d where violations are smallest (min-violation)
    Record provenance: 'strict_feasible_max' vs 'fallback_min_violation'

Monotonic regularization:
    - C_m(d) forced monotone non-decreasing
    - R_m(d) forced monotone non-increasing
```

**Step 4: Consensus Threshold**
```
τ_t^consensus = (1/N) Σ τ_m*(t)  for m ∈ {qwen0.5b, qwen3b, qwen7b}

These τ_t^consensus values are FROZEN and used in Test phase.
```

### Current Code Status
- ❌ Does NOT compute C_m(d), R_m(d) curves
- ❌ Does NOT use bin-based aggregation per Section 6.3.1
- ✓ Attempts τ* calibration but uses different method
- ❌ No consensus aggregation across 3 models

### REQUIRED FIXES

#### Fix 2.1: Build Capability Curves C_m(d)
```python
# FILE: sddf/validation_dynamic.py (REWRITE)

import numpy as np
from scipy.interpolate import isotonic_regression

def build_capability_curve(val_rows: list[dict], difficulties: np.array,
                           task_family: str, model_name: str,
                           n_bins: int = 10) -> dict:
    """
    Build C_m(d) per Section 6.3.1.
    
    Args:
        val_rows: validation split
        difficulties: d_i values from logistic regression (Section 6.2.2)
        task_family: 'classification', 'code_generation', etc.
        model_name: 'qwen2.5_0.5b', 'qwen2.5_3b', 'qwen2.5_7b'
        n_bins: number of difficulty bins
    
    Returns:
        curve_artifact = {
            'task_family': str,
            'model_name': str,
            'bin_edges': [0.0, 0.1, 0.2, ..., 1.0],
            'bin_capabilities': [C_hat_{m,t,1}, ..., C_hat_{m,t,K}],
            'bin_counts': [n_1, ..., n_K],
            'interpolator': callable,  # C_m(d) function
            'mono_regulated': np.array  # monotone version
        }
    """
    # 1. Partition difficulty into K bins
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(difficulties, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)
    
    # 2. Compute Ĉ_{m,t,k} per bin
    bin_capabilities = []
    bin_counts = []
    
    for k in range(n_bins):
        mask = bin_indices == k
        if mask.sum() == 0:
            bin_capabilities.append(0.5)  # default
            bin_counts.append(0)
        else:
            # Extract correctness for this bin
            correct = np.array([
                1 - (row.get('incorrect') or row.get('error', False))
                for row in np.array(val_rows)[mask]
            ])
            bin_capabilities.append(correct.mean())
            bin_counts.append(mask.sum())
    
    # 3. Apply isotonic regression (monotone non-decreasing)
    bin_capabilities_mono = isotonic_regression(
        bin_capabilities,
        y_min=0.0, y_max=1.0,
        increasing=True
    )
    
    # 4. Create interpolator for smooth C_m(d)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    def interpolate_capability(d: float) -> float:
        """Linear interpolation for C_m(d)"""
        if d <= bin_centers[0]:
            return bin_capabilities_mono[0]
        if d >= bin_centers[-1]:
            return bin_capabilities_mono[-1]
        idx = np.searchsorted(bin_centers, d)
        w = (d - bin_centers[idx-1]) / (bin_centers[idx] - bin_centers[idx-1])
        return (1-w) * bin_capabilities_mono[idx-1] + w * bin_capabilities_mono[idx]
    
    return {
        'task_family': task_family,
        'model_name': model_name,
        'bin_edges': bin_edges.tolist(),
        'bin_capabilities': bin_capabilities_mono.tolist(),
        'bin_counts': bin_counts,
        'interpolator': interpolate_capability,
        'timestamp': datetime.now().isoformat()
    }
```

#### Fix 2.2: Build Risk Curves R_m(d)
```python
def build_risk_curve(val_rows: list[dict], difficulties: np.array,
                     task_family: str, model_name: str,
                     n_bins: int = 10) -> dict:
    """
    Build R_m(d) per Section 6.3.1.
    
    Returns:
        curve_artifact = {
            'task_family': str,
            'model_name': str,
            'bin_edges': [0.0, 0.1, ..., 1.0],
            'bin_risks': [R̂_{m,t,1}, ..., R̂_{m,t,K}],
            'bin_counts': [n_1, ..., n_K],
            'interpolator': callable,  # R_m(d) function
            'mono_regulated': np.array  # monotone version (non-increasing)
        }
    """
    # 1. Partition into bins (same as capability)
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(difficulties, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)
    
    # 2. Compute R̂_{m,t,k} per bin
    bin_risks = []
    bin_counts = []
    
    for k in range(n_bins):
        mask = bin_indices == k
        if mask.sum() == 0:
            bin_risks.append(0.5)  # default
            bin_counts.append(0)
        else:
            # Extract risk values for this bin
            risks = np.array([
                compute_error_magnitude(row, task_family)
                for row in np.array(val_rows)[mask]
            ])
            bin_risks.append(risks.mean())
            bin_counts.append(mask.sum())
    
    # 3. Apply isotonic regression (monotone non-increasing, i.e., decreasing)
    bin_risks_mono = isotonic_regression(
        bin_risks,
        y_min=0.0, y_max=1.0,
        increasing=False  # Risk decreases with lower difficulty
    )
    
    # 4. Create interpolator
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    def interpolate_risk(d: float) -> float:
        """Linear interpolation for R_m(d)"""
        if d <= bin_centers[0]:
            return bin_risks_mono[0]
        if d >= bin_centers[-1]:
            return bin_risks_mono[-1]
        idx = np.searchsorted(bin_centers, d)
        w = (d - bin_centers[idx-1]) / (bin_centers[idx] - bin_centers[idx-1])
        return (1-w) * bin_risks_mono[idx-1] + w * bin_risks_mono[idx]
    
    return {
        'task_family': task_family,
        'model_name': model_name,
        'bin_edges': bin_edges.tolist(),
        'bin_risks': bin_risks_mono.tolist(),
        'bin_counts': bin_counts,
        'interpolator': interpolate_risk,
        'timestamp': datetime.now().isoformat()
    }
```

#### Fix 2.3: Define Constraints & Select Thresholds
```python
def select_routing_threshold(cap_curve: dict, risk_curve: dict,
                            c_baseline: float = 0.85,
                            epsilon_c: float = 0.05,
                            epsilon_r: float = 0.05) -> dict:
    """
    Select τ_m*(t) per Section 6.3.2 & 6.3.3.
    
    Args:
        cap_curve: output from build_capability_curve()
        risk_curve: output from build_risk_curve()
        c_baseline: target capability (e.g., 0.85)
        epsilon_c: capability margin (e.g., 0.05)
        epsilon_r: risk margin (e.g., 0.05)
    
    Returns:
        threshold_artifact = {
            'task_family': str,
            'model_name': str,
            'c_dyn': float,
            'r_dyn': float,
            'tau_star': float,
            'provenance': 'strict_feasible_max' | 'fallback_min_violation',
            'feasible_region': {'start_d': float, 'end_d': float},
            'c_at_tau': float,
            'r_at_tau': float
        }
    """
    # 1. Compute constraints per Section 6.3.2
    c_dyn = c_baseline - epsilon_c
    r_dyn = cap_curve['val_mean_risk'] + epsilon_r  # ≈ R̄_val
    
    # 2. Scan for feasible region
    difficulties = np.linspace(0, 1, 1000)
    cap_fn = cap_curve['interpolator']
    risk_fn = risk_curve['interpolator']
    
    feasible_region = []
    for d in difficulties:
        c_d = cap_fn(d)
        r_d = risk_fn(d)
        if c_d >= c_dyn and r_d <= r_dyn:
            feasible_region.append(d)
    
    # 3. Select threshold
    if feasible_region:
        tau_star = max(feasible_region)  # Highest d in feasible region
        provenance = 'strict_feasible_max'
    else:
        # Fallback: minimize violations
        violations = []
        for d in difficulties:
            c_d = cap_fn(d)
            r_d = risk_fn(d)
            cap_violation = max(0, c_dyn - c_d)
            risk_violation = max(0, r_d - r_dyn)
            violations.append(cap_violation + risk_violation)
        
        tau_star = difficulties[np.argmin(violations)]
        provenance = 'fallback_min_violation'
    
    return {
        'task_family': cap_curve['task_family'],
        'model_name': cap_curve['model_name'],
        'c_dyn': c_dyn,
        'r_dyn': r_dyn,
        'tau_star': tau_star,
        'provenance': provenance,
        'feasible_region': {
            'start_d': feasible_region[0] if feasible_region else None,
            'end_d': feasible_region[-1] if feasible_region else None
        },
        'c_at_tau': cap_fn(tau_star),
        'r_at_tau': risk_fn(tau_star)
    }
```

#### Fix 2.4: Compute Consensus Threshold
```python
def compute_consensus_threshold(thresholds_by_model: dict) -> dict:
    """
    Compute τ_t^consensus per Section 6.3.3.
    
    Args:
        thresholds_by_model: {
            'qwen2.5_0.5b': threshold_artifact,
            'qwen2.5_3b': threshold_artifact,
            'qwen2.5_7b': threshold_artifact
        }
    
    Returns:
        consensus_artifact = {
            'task_family': str,
            'tau_consensus': float,  # Mean across 3 models
            'tau_per_model': {...},
            'mean_coverage': float,
            'mean_c_tau': float,
            'mean_r_tau': float
        }
    """
    tau_values = [
        thresh['tau_star']
        for thresh in thresholds_by_model.values()
    ]
    
    tau_consensus = np.mean(tau_values)
    
    return {
        'task_family': next(iter(thresholds_by_model.values()))['task_family'],
        'tau_consensus': tau_consensus,
        'tau_per_model': {
            model: thresh['tau_star']
            for model, thresh in thresholds_by_model.items()
        },
        'mean_coverage': np.mean([t['c_at_tau'] for t in thresholds_by_model.values()]),
        'mean_c_tau': np.mean([t['c_at_tau'] for t in thresholds_by_model.values()]),
        'mean_r_tau': np.mean([t['r_at_tau'] for t in thresholds_by_model.values()]),
        'frozen_timestamp': datetime.now().isoformat()
    }


def freeze_consensus_thresholds(consensus_dict: dict, output_path: Path):
    """
    Save τ_t^consensus values for Test phase.
    These are FROZEN and never changed after validation.
    
    Output: Table 6.3 format
    {
        'classification': 0.6667,
        'code_generation': 0.6667,
        'information_extraction': 1.0000,
        ...
    }
    """
    frozen_thresholds = {
        v['task_family']: v['tau_consensus']
        for v in consensus_dict.values()
    }
    
    with open(output_path, 'w') as f:
        json.dump(frozen_thresholds, f, indent=2)
    
    print(f"✓ Frozen τ^consensus saved to {output_path}")
    print(f"  Ready for Test phase (do NOT recalibrate)")
```

---

## PHASE 3: TEST (Query-Level Routing with Frozen Thresholds)

### Paper Specification (Section 7)

**Input**:
- Test split (unseen queries)
- Frozen τ^consensus from Validation (Table 6.3)
- Fitted logistic regression models w_t, b from Training

**Step 1: Per-Query Feature Extraction & Difficulty (7.2)**
```
For each query x_j in test set:
  1. Extract features x_j^(t)
  2. Compute d_j = σ(w_t^T x_j^(t))  [using frozen weights from Training]
```

**Step 2: Per-Query Routing (7.2)**
```
For each model m ∈ {qwen0.5b, qwen3b, qwen7b}:
  route_m(x_j) = {  SLM,  if p_fail^(m)(x_j) < τ_m
                   {  LLM,  if p_fail^(m)(x_j) ≥ τ_m

Where p_fail^(m)(x_j) = d_j  [from Step 1]
And τ_m = frozen threshold for model m's task family

NOTE: Use CONSENSUS τ per task family, NOT per-model τ*!
```

**Step 3: Aggregate to Use-Case Level (7.3)**
```
For each use case (maps to task family):

ρ^(m) = (1/N) Σ_j 1[route_m(x_j) = SLM]  [SLM routing fraction for model m]

ρ̄ = (1/3) Σ_{m∈{0.5b, 3b, 7b}} ρ^(m)  [Consensus across 3 models]

Tier decision:
  If ρ̄ ≥ 0.70  →  SLM    (can safely route most to SLM)
  If ρ̄ ≤ 0.30  →  LLM    (must escalate most)
  If 0.30 < ρ̄ < 0.70  →  HYBRID (mixed routing needed)
```

**Step 4: Compare S3 Policy Tier vs Runtime Tier**
```
TierCorrect(u) = 1[Tier_S3_new(u) = Tier_RT(u)]

Where:
  Tier_S3_new: S³ framework decision (Section 4)
  Tier_RT: Runtime aggregated routing decision from Step 3

Agreement = Σ TierCorrect / 8 use cases
```

### Current Code Status
- ❌ Uses per-model τ* instead of consensus τ
- ❌ Does NOT use frozen thresholds from Table 6.3
- ❌ Skips ρ aggregation step
- ❌ No explicit comparison to S³ tier

### REQUIRED FIXES

#### Fix 3.1: Runtime Routing with Frozen Thresholds
```python
# FILE: tools/sddf_runtime_routing.py (NEW)

def route_query_paper_spec(query: dict, task_family: str, model_name: str,
                           frozen_thresholds: dict,
                           train_artifacts: dict) -> str:
    """
    Route single query per paper Section 7.2.
    
    Args:
        query: test query dict
        task_family: mapped family (e.g., 'classification')
        model_name: 'qwen2.5_0.5b', 'qwen2.5_3b', 'qwen2.5_7b'
        frozen_thresholds: {'classification': 0.6667, ...}  [from validation]
        train_artifacts: {'classification': {w, b, features}, ...}  [from training]
    
    Returns:
        'SLM' or 'LLM'
    """
    # 1. Extract features and compute difficulty
    features = extract_task_family_features(query, task_family)
    artifact = train_artifacts[task_family]
    
    # Use frozen weights from training
    w = np.array(artifact['weights_w'])
    b = artifact['intercept_b']
    
    # Compute d_j = σ(w^T x_j + b)
    z = np.dot(w, features) + b
    d_j = sigmoid(z)  # ∈ [0, 1]
    
    # 2. Look up CONSENSUS threshold (NOT per-model!)
    tau_consensus = frozen_thresholds[task_family]
    
    # 3. Make routing decision per Section 7.2
    if d_j < tau_consensus:
        return 'SLM'
    else:
        return 'LLM'


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def route_test_set(test_rows: list[dict], uc_to_family: dict,
                   frozen_thresholds: dict,
                   train_artifacts: dict) -> dict:
    """
    Route all test queries per paper Section 7.2-7.3.
    
    Returns:
        routing_results = {
            'UC1': {
                'qwen2.5_0.5b': ['SLM', 'LLM', 'SLM', ...],  # per-query routes
                'qwen2.5_3b': [...],
                'qwen2.5_7b': [...],
                'consensus_rho': 0.6667,  # ρ̄
                'runtime_tier': 'HYBRID'
            },
            ...
        }
    """
    results = {}
    
    for uc, task_family in uc_to_family.items():
        uc_rows = [r for r in test_rows if r.get('use_case') == uc]
        
        per_model_routes = {}
        
        for model in ['qwen2.5_0.5b', 'qwen2.5_3b', 'qwen2.5_7b']:
            routes = [
                route_query_paper_spec(
                    row, task_family, model,
                    frozen_thresholds, train_artifacts
                )
                for row in uc_rows
            ]
            per_model_routes[model] = routes
        
        # 3. Aggregate to ρ̄ per Section 7.3
        rho_values = {
            model: sum(1 for r in routes if r == 'SLM') / len(uc_rows)
            for model, routes in per_model_routes.items()
        }
        
        rho_consensus = np.mean(list(rho_values.values()))
        
        # Determine runtime tier
        if rho_consensus >= 0.70:
            runtime_tier = 'SLM'
        elif rho_consensus <= 0.30:
            runtime_tier = 'LLM'
        else:
            runtime_tier = 'HYBRID'
        
        results[uc] = {
            'per_model_routes': per_model_routes,
            'rho_per_model': rho_values,
            'rho_consensus': rho_consensus,
            'runtime_tier': runtime_tier,
            'test_set_size': len(uc_rows)
        }
    
    return results
```

#### Fix 3.2: Compute Test-Phase Performance Metrics
```python
def evaluate_test_routing(routing_results: dict, test_rows: list[dict],
                          uc_to_family: dict) -> dict:
    """
    Evaluate routing decisions on test set.
    Measure agreement with actual correctness.
    """
    metrics = {}
    
    for uc, routing_info in routing_results.items():
        uc_rows = [r for r in test_rows if r.get('use_case') == uc]
        
        # Per-model accuracy in SLM region
        per_model_metrics = {}
        
        for model in ['qwen2.5_0.5b', 'qwen2.5_3b', 'qwen2.5_7b']:
            routes = routing_info['per_model_routes'][model]
            
            slm_mask = np.array([r == 'SLM' for r in routes])
            llm_mask = ~slm_mask
            
            # Measure SLM region quality
            if slm_mask.sum() > 0:
                slm_rows = np.array(uc_rows)[slm_mask]
                slm_accuracy = sum(
                    1 for row in slm_rows
                    if not (row.get('incorrect') or row.get('error'))
                ) / len(slm_rows)
            else:
                slm_accuracy = None
            
            # Measure LLM region quality (should be high)
            if llm_mask.sum() > 0:
                llm_rows = np.array(uc_rows)[llm_mask]
                llm_accuracy = sum(
                    1 for row in llm_rows
                    if not (row.get('incorrect') or row.get('error'))
                ) / len(llm_rows)
            else:
                llm_accuracy = None
            
            per_model_metrics[model] = {
                'slm_region_accuracy': slm_accuracy,
                'slm_region_coverage': slm_mask.sum() / len(uc_rows),
                'llm_region_accuracy': llm_accuracy,
                'system_accuracy': sum(
                    1 for i, row in enumerate(uc_rows)
                    if not (row.get('incorrect') or row.get('error'))
                ) / len(uc_rows)
            }
        
        metrics[uc] = {
            'per_model': per_model_metrics,
            'consensus_rho': routing_info['rho_consensus'],
            'runtime_tier': routing_info['runtime_tier']
        }
    
    return metrics
```

#### Fix 3.3: Cross-Framework Validation (S³ vs SDDF Runtime)
```python
def compare_s3_vs_sddf(s3_tiers: dict, runtime_results: dict) -> dict:
    """
    Compare S³ policy tier vs SDDF runtime tier per paper Section 8-9.
    
    Args:
        s3_tiers: {'UC1': 'Pure SLM', 'UC2': 'Hybrid', ...}
        runtime_results: {'UC1': {'runtime_tier': 'SLM', ...}, ...}
    
    Returns:
        comparison = {
            'agreement_count': int,
            'agreement_rate': float,
            'gap_analysis': {
                'UC1': {
                    's3_tier': 'Pure SLM',
                    'runtime_tier': 'SLM',
                    'gap_type': 'MATCH',
                    'interpretation': '...'
                },
                ...
            },
            'spearman_correlation': float  # Between S3 score and SDDF routing
        }
    """
    agreement = 0
    gap_analysis = {}
    
    for uc in s3_tiers.keys():
        s3_tier = s3_tiers[uc]
        runtime_tier = runtime_results[uc]['runtime_tier']
        
        # Normalize tier names for comparison
        s3_normalized = normalize_tier_name(s3_tier)
        
        if s3_normalized == runtime_tier:
            gap_type = 'MATCH'
            agreement += 1
        elif is_underestimation(s3_normalized, runtime_tier):
            gap_type = 'UNDERESTIMATION'
        else:
            gap_type = 'OVERESTIMATION'
        
        gap_analysis[uc] = {
            's3_tier': s3_tier,
            'runtime_tier': runtime_tier,
            'gap_type': gap_type,
            'rho': runtime_results[uc].get('rho_consensus')
        }
    
    return {
        'agreement_count': agreement,
        'agreement_rate': agreement / len(s3_tiers),
        'gap_analysis': gap_analysis,
        'paper_table_9_1_row': build_table_9_1_row(runtime_results)
    }


def normalize_tier_name(tier: str) -> str:
    """Normalize various tier names to 'SLM', 'HYBRID', 'LLM'"""
    tier_lower = tier.lower()
    if 'pure' in tier_lower or 'slm' in tier_lower and 'only' not in tier_lower:
        return 'SLM'
    elif 'hybrid' in tier_lower:
        return 'HYBRID'
    elif 'llm' in tier_lower:
        return 'LLM'
    return 'UNKNOWN'


def build_table_9_1_row(runtime_results: dict) -> dict:
    """
    Format results as Paper's Table 9.1.
    
    Output row:
    {
        'Use case': 'UC1 (SMS Threat Detection)',
        'S3 score': 3.40,
        'Predicted tier': 'LLM Only',
        'Mapped task family': 'classification',
        'C_m(d)': 0.3145,
        'R_m(d)': 0.3428,
        'tau_frozen': 0.6667,
        'Runtime behavior': 'LLM',
        'Agreement / disagreement': 'Agreement'
    }
    """
    # Populate from runtime_results and s3_scores
    pass
```

---

## Summary of Fixes Needed

| Phase | Issue | Fix File | Key Changes |
|-------|-------|----------|-------------|
| **Train** | No logistic regression | `sddf/training.py` (NEW) | Fit LogisticRegression on failure labels F_i per Section 6.2.2 |
| **Val** | No C_m(d), R_m(d) curves | `sddf/validation_dynamic.py` (REWRITE) | Implement binned capability/risk curves with isotonic regularization per Section 6.3.1 |
| **Val** | No constraint enforcement | `sddf/validation_dynamic.py` | Add C_dyn, R_dyn constraints; find τ* per Section 6.3.2-6.3.3 |
| **Val** | No consensus threshold | `sddf/validation_dynamic.py` | Average τ* across 3 models; freeze per Table 6.3 |
| **Test** | Uses per-model τ* | `tools/sddf_runtime_routing.py` (NEW) | Use frozen τ^consensus; compute ρ per Section 7.2-7.3 |
| **Test** | No S³-vs-SDDF comparison | `tools/sddf_runtime_routing.py` | Add cross-framework validation per Section 8-9 |

---

## Implementation Roadmap

### Week 1: Train Phase
- [ ] Implement `sddf/training.py` with logistic regression fitting
- [ ] Validate against paper's Section 6.2 specification
- [ ] Store w_t, b, feature names per task family

### Week 2: Val Phase Part 1
- [ ] Rewrite `sddf/validation_dynamic.py` for capability curves
- [ ] Implement binning, isotonic regression, interpolation
- [ ] Validate C_m(d) shapes match paper expectations

### Week 2: Val Phase Part 2
- [ ] Implement risk curves R_m(d)
- [ ] Add C_dyn, R_dyn constraint computation
- [ ] Implement τ* selection with feasibility check

### Week 3: Val Phase Part 3
- [ ] Compute consensus τ^consensus across 3 models
- [ ] Freeze thresholds (output Table 6.3 format)
- [ ] Unit test against paper's reported values

### Week 4: Test Phase
- [ ] Implement `tools/sddf_runtime_routing.py`
- [ ] Route all test queries using frozen thresholds
- [ ] Compute ρ̄ per use case
- [ ] Compare to S³ tiers (Table 9.1)
- [ ] Verify Spearman correlation (paper: −0.726, p=0.010)

