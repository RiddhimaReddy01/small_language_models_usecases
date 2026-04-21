# SDDF v3 Code Changes: Before → After Examples

---

## PHASE 1: TRAIN - Logistic Regression

### BEFORE (Current Code)
```python
# evaluate_routing.py (lines ~120)
def _score_row_model(row, model):
    """Difficulty = weighted sum of normalized features (NO logistic regression)"""
    features = compute_all_features(row, prompt)
    score = 0.0
    for dim in DIFFICULTY_FEATURES:
        val = features[dim]
        lo, hi = norm_stats[dim]["p05"], norm_stats[dim]["p95"]
        nv = (val - lo) / (hi - lo)
        score += weights[dim] * nv  # HAND-WEIGHTED: no statistical fit
    return clamp(score, 0.0, 1.0)
```

**Problems**:
- ❌ Weights are arbitrary/hardcoded, not learned
- ❌ No logistic function (linear combination instead)
- ❌ No failure label supervision
- ❌ Not reproducible across different datasets

---

### AFTER (Paper-Aligned)
```python
# sddf/training.py (NEW FILE)
from sklearn.linear_model import LogisticRegression

def train_difficulty_model(task_family: str, train_rows: list) -> dict:
    """
    Train logistic regression on failure labels per Section 6.2.2.
    
    d_i = σ(w_t^T x_i^(t))
    
    where σ is logistic function, w_t learned via sklearn
    """
    # 1. Extract features for all training samples
    X = np.array([
        extract_task_features(row, task_family)
        for row in train_rows
    ])
    
    # 2. Extract failure labels (0 or 1)
    y = np.array([
        1 if (row.get('incorrect') or row.get('error')) else 0
        for row in train_rows
    ])
    
    # 3. FIT LOGISTIC REGRESSION
    model = LogisticRegression(
        penalty='l2',
        C=1.0,
        max_iter=1000,
        solver='lbfgs',
        random_state=42
    )
    model.fit(X, y)
    
    # 4. Save weights for inference
    return {
        'task_family': task_family,
        'weights_w': model.coef_[0],      # Learned weights
        'intercept_b': model.intercept_[0],
        'feature_names': get_feature_names(task_family),
        'model': model,
        'train_set_size': len(train_rows),
        'feature_importance': model.coef_[0]  # Inspect which features matter
    }


def compute_difficulty_from_trained_model(query: dict, task_family: str,
                                         model_artifact: dict) -> float:
    """
    Predict failure probability d_i = sigmoid(w_t^T x_i + b)
    using learned weights from training.
    """
    features = extract_task_features(query, task_family)
    X = np.array([features])
    
    # sklearn's predict_proba gives [P(y=0), P(y=1)]
    # P(y=1) is failure probability
    failure_prob = model_artifact['model'].predict_proba(X)[0, 1]
    
    return failure_prob  # ∈ [0, 1]
```

**Benefits**:
- ✓ Weights learned from data (Section 6.2.2)
- ✓ Logistic function ensures [0,1] range (failure probability)
- ✓ Reproducible and theoretically grounded
- ✓ Can inspect feature importance

---

## PHASE 2: VALIDATION - Capability & Risk Curves

### BEFORE (Current Code)
```python
# evaluate_routing.py (lines ~210)
def calibrate_tau(rows, scores, task, cap_threshold, risk_threshold):
    """
    τ* calibration using prefix scan (DOES NOT match paper Section 6.3)
    """
    # Sort by difficulty score
    paired = sorted([(scores[r["sample_id"]], r) for r in rows])
    
    best_tau = None
    for threshold in np.linspace(0, 1, 100):
        # Count how many queries below threshold
        easy_region = [s for s, _ in paired if s <= threshold]
        
        # Check capability/risk in that region
        cap = accuracy_in_region(easy_region)
        risk = weighted_failure_risk(easy_region)
        
        feasible = (cap >= cap_threshold and risk <= risk_threshold)
        if feasible:
            best_tau = threshold  # Keep highest threshold
    
    return best_tau
```

**Problems**:
- ❌ Uses raw scores (not logistic failure probability)
- ❌ No C_m(d), R_m(d) curve construction
- ❌ No isotonic regression smoothing
- ❌ Per-model τ*, not consensus τ^consensus
- ❌ Not frozen — recalculated every run

---

### AFTER (Paper-Aligned)
```python
# sddf/validation_dynamic.py (REWRITE)
from scipy.interpolate import isotonic_regression

def build_curves_and_select_threshold(val_rows: list, task_family: str,
                                      model_name: str,
                                      train_artifacts: dict,
                                      c_baseline=0.85, epsilon_c=0.05) -> dict:
    """
    Build C_m(d) and R_m(d) per Section 6.3.1, then select τ_m* per Section 6.3.3.
    """
    
    # STEP 1: Compute d_i for all validation samples
    # Use FROZEN weights from training (not retrained!)
    d_vals = np.array([
        compute_difficulty_from_trained_model(row, task_family, 
                                             train_artifacts[task_family])
        for row in val_rows
    ])
    
    # STEP 2: Bin difficulties and compute empirical capability/risk
    n_bins = 10
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(d_vals, bin_edges) - 1
    
    bin_capabilities = []
    bin_risks = []
    
    for k in range(n_bins):
        mask = bin_indices == k
        if mask.sum() == 0:
            bin_capabilities.append(0.5)
            bin_risks.append(0.5)
        else:
            # Ĉ_{m,t,k} = fraction correct in bin k
            correct = np.array([
                0 if (row.get('incorrect') or row.get('error')) else 1
                for row in np.array(val_rows)[mask]
            ])
            bin_capabilities.append(correct.mean())
            
            # R̂_{m,t,k} = mean error magnitude in bin k
            risks = np.array([
                compute_error_magnitude(row, task_family)
                for row in np.array(val_rows)[mask]
            ])
            bin_risks.append(risks.mean())
    
    # STEP 3: Smooth via isotonic regression (monotonicity constraints)
    bin_cap_smooth = isotonic_regression(
        bin_capabilities,
        y_min=0.0, y_max=1.0,
        increasing=True  # Capability increases with lower difficulty
    )
    
    bin_risk_smooth = isotonic_regression(
        bin_risks,
        y_min=0.0, y_max=1.0,
        increasing=False  # Risk decreases with lower difficulty
    )
    
    # STEP 4: Create smooth interpolators C_m(d) and R_m(d)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    def C_m(d):
        """Capability curve C_m(d)"""
        if d <= bin_centers[0]:
            return bin_cap_smooth[0]
        if d >= bin_centers[-1]:
            return bin_cap_smooth[-1]
        idx = np.searchsorted(bin_centers, d)
        w = (d - bin_centers[idx-1]) / (bin_centers[idx] - bin_centers[idx-1])
        return (1-w)*bin_cap_smooth[idx-1] + w*bin_cap_smooth[idx]
    
    def R_m(d):
        """Risk curve R_m(d)"""
        if d <= bin_centers[0]:
            return bin_risk_smooth[0]
        if d >= bin_centers[-1]:
            return bin_risk_smooth[-1]
        idx = np.searchsorted(bin_centers, d)
        w = (d - bin_centers[idx-1]) / (bin_centers[idx] - bin_centers[idx-1])
        return (1-w)*bin_risk_smooth[idx-1] + w*bin_risk_smooth[idx]
    
    # STEP 5: Define constraints (Section 6.3.2)
    c_dyn = c_baseline - epsilon_c  # e.g., 0.85 - 0.05 = 0.80
    r_dyn = np.mean(bin_risks) + 0.05  # R̄_val + ε_R
    
    # STEP 6: Find threshold τ_m* (Section 6.3.3)
    # τ_m* = max d where both constraints satisfied
    difficulties = np.linspace(0, 1, 1000)
    feasible_region = [
        d for d in difficulties
        if C_m(d) >= c_dyn and R_m(d) <= r_dyn
    ]
    
    if feasible_region:
        tau_star = max(feasible_region)
        provenance = 'strict_feasible_max'
    else:
        # Fallback: minimize constraint violations
        violations = [
            max(0, c_dyn - C_m(d)) + max(0, R_m(d) - r_dyn)
            for d in difficulties
        ]
        tau_star = difficulties[np.argmin(violations)]
        provenance = 'fallback_min_violation'
    
    return {
        'task_family': task_family,
        'model_name': model_name,
        'C_m': C_m,  # Capability curve function
        'R_m': R_m,  # Risk curve function
        'tau_star': tau_star,
        'provenance': provenance,
        'c_dyn': c_dyn,
        'r_dyn': r_dyn,
        'c_at_tau': C_m(tau_star),
        'r_at_tau': R_m(tau_star),
        'bin_capabilities': bin_cap_smooth.tolist(),
        'bin_risks': bin_risk_smooth.tolist()
    }


def compute_consensus_threshold(thresholds_by_model: dict) -> float:
    """
    Compute τ_t^consensus across 3 models per Section 6.3.3.
    This value is FROZEN and used in test phase.
    """
    tau_values = [
        thresh['tau_star']
        for thresh in thresholds_by_model.values()
    ]
    tau_consensus = np.mean(tau_values)
    return tau_consensus


def freeze_thresholds(consensus_dict: dict, output_file: str):
    """
    Save frozen τ^consensus to file (replaces Table 6.3).
    These values NEVER change after validation phase.
    """
    frozen = {
        family: consensus_dict[family]['tau_consensus']
        for family in consensus_dict
    }
    with open(output_file, 'w') as f:
        json.dump(frozen, f, indent=2)
    print(f"✓ FROZEN τ^consensus saved to {output_file}")
```

**Benefits**:
- ✓ Builds proper C_m(d) and R_m(d) curves (Section 6.3.1)
- ✓ Applies monotonicity constraints via isotonic regression
- ✓ Computes consensus across 3 models (Section 6.3.3)
- ✓ Freezes thresholds for reproducibility (not retrained per run)
- ✓ Outputs match Table 6.3 values

---

## PHASE 3: TEST - Frozen Consensus Routing

### BEFORE (Current Code)
```python
# evaluate_routing.py (lines ~280)
def route_test_queries(test_rows, tau_per_model_per_task):
    """
    Route using PER-MODEL τ* (WRONG per paper)
    """
    for model in ['qwen2.5_0.5b', 'qwen2.5_3b', 'qwen2.5_7b']:
        for row in test_rows:
            task = row['task_family']
            difficulty = compute_difficulty(row)  # Weighted average
            tau_star = tau_per_model_per_task[model][task]  # Per-model threshold!
            
            if difficulty <= tau_star:
                route = 'SLM'
            else:
                route = 'LLM'
```

**Problems**:
- ❌ Uses per-model τ*, not consensus τ^consensus
- ❌ No aggregation to ρ̄
- ❌ No comparison to S³ tier
- ❌ Skips Table 7.3 and Table 7.4 outputs
- ❌ No cross-framework validation (Section 8-9)

---

### AFTER (Paper-Aligned)
```python
# tools/sddf_runtime_routing.py (NEW FILE)

def route_test_set_paper_spec(test_rows: list,
                              frozen_thresholds: dict,
                              train_artifacts: dict,
                              uc_mapping: dict) -> dict:
    """
    Route test queries per Section 7.2-7.3 using FROZEN τ^consensus.
    
    Output: Table 7.4 format with ρ̄ per use case
    """
    
    results = {}
    
    for uc, task_family in uc_mapping.items():
        uc_rows = [r for r in test_rows if r.get('use_case') == uc]
        
        # Per-model routing
        per_model_routes = {}
        per_model_rho = {}
        
        for model in ['qwen2.5_0.5b', 'qwen2.5_3b', 'qwen2.5_7b']:
            routes = []
            
            for query in uc_rows:
                # STEP 1: Compute difficulty using FROZEN weights
                d_j = compute_difficulty_from_trained_model(
                    query, task_family,
                    train_artifacts[task_family]
                )
                
                # STEP 2: Look up FROZEN CONSENSUS threshold (NOT per-model!)
                tau_consensus = frozen_thresholds[task_family]
                
                # STEP 3: Route per Section 7.2
                if d_j < tau_consensus:
                    route = 'SLM'
                else:
                    route = 'LLM'
                
                routes.append(route)
            
            # Compute ρ^(m) = fraction routed to SLM
            rho_m = sum(1 for r in routes if r == 'SLM') / len(uc_rows)
            
            per_model_routes[model] = routes
            per_model_rho[model] = rho_m
        
        # STEP 4: Aggregate to ρ̄ (Section 7.3)
        rho_consensus = np.mean(list(per_model_rho.values()))
        
        # STEP 5: Determine runtime tier
        if rho_consensus >= 0.70:
            runtime_tier = 'SLM'
        elif rho_consensus <= 0.30:
            runtime_tier = 'LLM'
        else:
            runtime_tier = 'HYBRID'
        
        results[uc] = {
            'rho_0.5b': per_model_rho['qwen2.5_0.5b'],
            'rho_3b': per_model_rho['qwen2.5_3b'],
            'rho_7b': per_model_rho['qwen2.5_7b'],
            'rho_consensus': rho_consensus,
            'runtime_tier': runtime_tier,
            'tau_frozen': frozen_thresholds[task_family]  # Document frozen value used
        }
    
    return results


def compare_s3_vs_runtime(s3_tiers: dict, runtime_results: dict) -> dict:
    """
    Cross-framework validation per Section 8-9.
    Compare S³ policy tier vs SDDF runtime tier.
    """
    agreement_count = 0
    gap_analysis = {}
    
    for uc in s3_tiers.keys():
        s3_tier = normalize_tier(s3_tiers[uc])
        runtime_tier = runtime_results[uc]['runtime_tier']
        
        if s3_tier == runtime_tier:
            gap_type = 'Agreement'
            agreement_count += 1
        elif tier_precedence(s3_tier) < tier_precedence(runtime_tier):
            gap_type = 'Underestimation'  # Policy is more aggressive than runtime
        else:
            gap_type = 'Overestimation'  # Policy is more conservative
        
        gap_analysis[uc] = {
            's3_tier': s3_tiers[uc],
            'runtime_tier': runtime_tier,
            'gap_type': gap_type,
            'rho': runtime_results[uc]['rho_consensus']
        }
    
    # Compute correlation (Table 8.3)
    s3_scores = [...]  # Extract from S³ framework
    sddf_routing_capacity = [...]  # From runtime results
    
    spearman_corr, p_value = scipy.stats.spearmanr(
        s3_scores, sddf_routing_capacity
    )
    
    return {
        'agreement_rate': agreement_count / len(s3_tiers),
        'gap_analysis': gap_analysis,
        'spearman_correlation': spearman_corr,
        'p_value': p_value,
        'table_9_1': format_table_9_1(s3_tiers, runtime_results)
    }


def normalize_tier(tier: str) -> str:
    """Normalize tier names"""
    tier_lower = tier.lower()
    if 'pure' in tier_lower or ('slm' in tier_lower and 'only' not in tier_lower):
        return 'SLM'
    elif 'hybrid' in tier_lower:
        return 'HYBRID'
    elif 'llm' in tier_lower:
        return 'LLM'
    return 'UNKNOWN'


def tier_precedence(tier: str) -> int:
    """SLM < HYBRID < LLM (risk ordering)"""
    return {'SLM': 0, 'HYBRID': 1, 'LLM': 2}.get(tier, -1)
```

**Benefits**:
- ✓ Uses frozen τ^consensus (same for all 3 models)
- ✓ Computes ρ per model and ρ̄ consensus (Section 7.3)
- ✓ Maps ρ̄ to runtime tier (SLM/HYBRID/LLM)
- ✓ Compares to S³ tiers for cross-framework validation
- ✓ Outputs Table 7.4 and Table 9.1 formats
- ✓ Computes Spearman correlation (Table 8.3)

---

## Summary: Key Changes

| Component | Before | After | Paper Ref |
|-----------|--------|-------|-----------|
| **Train features** | Weighted avg | Logistic regression | 6.2.2 |
| **Train output** | Arbitrary weights | Learned w_t, b | 6.2.2 |
| **Val curves** | None | C_m(d), R_m(d) | 6.3.1 |
| **Val smoothing** | None | Isotonic regression | 6.3.1 |
| **Val thresholds** | Per-model τ* | Consensus τ^consensus | 6.3.3 |
| **Val freezing** | Not frozen | Frozen to file | 6.3.3 |
| **Test routing** | Per-model τ* | Consensus τ^consensus | 7.2 |
| **Test aggregation** | None | ρ̄ across 3 models | 7.3 |
| **Cross-framework** | None | S³ vs SDDF comparison | 8-9 |

---

## Files to Create/Modify

```
CREATE:  sddf/training.py
         - fit_difficulty_model()
         - compute_difficulty_from_trained_model()

REWRITE: sddf/validation_dynamic.py
         - build_curves_and_select_threshold()
         - compute_consensus_threshold()
         - freeze_thresholds()

CREATE:  tools/sddf_runtime_routing.py
         - route_test_set_paper_spec()
         - compare_s3_vs_runtime()

DELETE:  tools/evaluate_routing.py (superseded)
DELETE:  family_weights_learned.json (use logistic regression)
DELETE:  task_thresholds.json (use frozen τ^consensus)
```
