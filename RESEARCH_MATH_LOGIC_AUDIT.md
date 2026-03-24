# Mathematical and Logic Audit: Hybrid SLM/LLM Routing System

## Research Paper Perspective: Soundness Review

**Author's Note**: This audit evaluates the codebase as if submitting to a top-tier research venue (ICML, NeurIPS, ICLR). We examine mathematical rigor, logical consistency, and experimental validity.

**Audit Date**: 2026-03-24
**Scope**: Complete mathematical formulations and logical reasoning
**Severity Rating Scale**:
- 🔴 **CRITICAL** - Invalidates main claims / breaks mathematical soundness
- 🟠 **HIGH** - Significant inconsistency / affects conclusions
- 🟡 **MEDIUM** - Important issue / affects one component
- 🟢 **LOW** - Minor inconsistency / unlikely to affect results

---

## SECTION 1: Mathematical Formulations

### 1.1 Risk-Capability Relationship

#### **CLAIMED FORMULATION**
```
From: docs/reference/RISK_CURVES.md:8

Capability_m(b) = C_m(b) = 1 - Risk_m(b)

Risk_m(b) = P̂_m(fail|b) = # failures / # samples
```

**Implication**: Capability and Risk are **complementary** and **mutually exclusive** metrics.
- If Risk = 0.30, then Capability = 0.70
- C + R = 1.0 for all bins
- Same underlying failure event measured from two perspectives

#### **ACTUAL IMPLEMENTATION**
```
From: src/routing/framework.py:191-275

compute_capability_curve():
  - Uses validation_fn (structural validity check)
  - Counts: valid_output / total_samples
  - Example: "Code compiles?" → 0.85

compute_risk_curve():
  - Uses quality_metric (functional quality check)
  - Counts: quality_score < threshold / total_samples
  - Example: "Tests pass?" → 0.30
```

#### **AUDIT FINDING** 🔴 CRITICAL

**Issue**: Complementarity assumption is violated

**Evidence**:

| Sample | Compiles (Validity) | Tests Pass (Quality) |
|--------|------------------|-------------------|
| Valid, Good | ✓ | ✓ |
| Valid, Bad | ✓ | ✗ |
| Invalid | ✗ | ✗ |

```python
Sample: valid_output="def foo():\n    pass"  # Valid Python but does nothing

Capability check:
  validate_code(code) → compile(code) → True ✓
  Counter: +Capability

Quality check:
  quality_score(code) → tests_passed / total_tests = 0/5
  Counter: +Risk

SAME SAMPLE increments BOTH capability and risk!
```

**Why This Matters**:
```
1. Mathematical: C + R ≠ 1.0

   Example bin:
   - 100 samples
   - 85 compile successfully (C = 0.85)
   - 30 fail quality test (R = 0.30)

   C + R = 0.85 + 0.30 = 1.15 ≠ 1.0

   Contradiction! Cannot be true complementary metrics.

2. Zone Classification Logic:

   Zone boundaries assume:
   if C >= 0.80 and R <= 0.20: Z1 (safe)
   if C >= 0.80 and R > 0.20:  Z2 (risky)

   But these metrics are INDEPENDENT!
   A sample can be:
   - C=0.85 (valid) but R=0.40 (fails tests) → Z2
   - C=0.65 (invalid) but R=0.10 (tests pass on valid subset)

   The zone logic assumes they measure the SAME failure event
   from two perspectives (which they don't).

3. Expected Value Calculations:

   When computing expected capability/risk:
   E[C] = 0.82  (high → confident SLM will work)
   E[R] = 0.35  (high → confident SLM will fail)

   These seem contradictory when interpreted as
   E[C] + E[R] = 1.0, but they're not.

   This confuses the interpretation of "high capability,
   high risk" (Z2 zone).
```

**Mathematical Notation Issues**:
- Paper calls it "Capability" but measures "Validity"
- Used interchangeably as if they're the same
- Creates ambiguity about what the metric represents

**Recommendation**:
```
Rename:
  C_m(b) → V_m(b) (Validity)

Document as:
  V_m(b) = P(valid_output | sample in bin b)
  R_m(b) = P(quality < threshold | sample in bin b)

  These measure DIFFERENT failure modes:
  - V: Structural/syntactic failures
  - R: Functional/quality failures

  NO CONSTRAINT: V + R ≠ 1.0

  Update zone interpretation:
  - Z1: V ≥ 0.80 AND R ≤ 0.20
    (Output structure is valid AND meets quality bar)
  - Z2: V ≥ 0.80 AND R > 0.20
    (Output structure is valid BUT fails quality bar)
  - Z3: V < 0.80 AND R ≤ 0.20
    (Output structure often invalid BUT quality acceptable when valid)
  - Z4: V < 0.80 AND R > 0.20
    (Output structure invalid AND fails quality bar)
```

---

### 1.2 Tipping Point Definitions

#### **CLAIMED DEFINITIONS**
```
From: src/routing/framework.py:347-348

τ_cap = max{b : Ĉ_m(b) ≥ τ_C}
  = Last bin where capability meets threshold
  = Model safe up to this bin, fails after

τ_risk = min{b : R̂_m(b) > τ_R}
  = First bin where risk exceeds threshold
  = Model becomes unsafe starting here
```

#### **ACTUAL IMPLEMENTATION**
```python
# Lines 362-371: Capability tipping point
tau_cap = None
for d in range(num_bins):
    cap = expected_capabilities.get(d, 0.0)
    n = (capability_counts or {}).get(d, 0)
    if n < min_samples:
        continue
    lower, _ = wilson_interval(cap, n, z)
    if lower is not None and lower >= self.capability_threshold:
        tau_cap = d  # KEEP UPDATING

# Lines 373-383: Risk tipping point
tau_risk = None
for d in range(num_bins):
    risk = expected_risks.get(d, 0.0)
    n = (risk_counts or {}).get(d, 0)
    if n < min_samples:
        continue
    lower, _ = wilson_interval(risk, n, z)
    if lower is not None and lower >= self.risk_threshold:
        tau_risk = d
        break  # STOP ON FIRST MATCH
```

#### **AUDIT FINDING** 🟠 HIGH (Logic Issue)

**Issue**: τ_cap and τ_risk use different search strategies

**Problem**:

τ_cap: "Last bin where condition met"
- Loop: `for d in range(num_bins)`
- Action: `tau_cap = d` (OVERWRITES previous values)
- Result: tau_cap = highest bin where C ≥ τ_C
- Semantic: Last bin that meets threshold

τ_risk: "First bin where condition met"
- Loop: `for d in range(num_bins)`
- Action: `tau_risk = d; break` (STOPS immediately)
- Result: tau_risk = lowest bin where R > τ_R
- Semantic: First bin that meets threshold

**Why Different Strategies?**
- τ_cap looks for LAST qualified bin (makes sense: test extends how far?)
- τ_risk looks for FIRST unqualified bin (makes sense: test when model breaks?)

**Mathematical Interpretation**:
```
τ_cap = 3 means:
  "Model passes through bin 3, may fail in bin 4"
  Interpretation: Safe up to difficulty level 3

τ_risk = 2 means:
  "Model starts failing at bin 2"
  Interpretation: Unsafe starting at difficulty level 2

Q3 Zone Logic (from code line 398):
  if tau_cap < 4 and tau_risk > tau_cap:
    return "Q3"  # Use SLM for easy, LLM for hard

Example: tau_cap=2, tau_risk=3
  - Model safe: bins 0, 1, 2 (can use SLM)
  - Model unsafe: bins 3, 4 (need LLM)
  - Logical ✓ (risk only appears after capability ceases)

BUT: This requires τ_risk > τ_cap!
     What if τ_risk < τ_cap?
     This would mean risk rises BEFORE capability drops
     Is this physically possible? Mathematically consistent?
```

**Confidence Interval Asymmetry** 🔴 CRITICAL
```
τ_cap condition:
  lower(C, n, z=1.96) >= 0.80

τ_risk condition:
  lower(R, n, z=1.96) >= 0.20

Both use LOWER confidence bound.

For τ_cap:
  Require LOWER CI >= threshold
  = Conservative: "We're CONFIDENT C ≥ 0.80"
  = High bar (lower must reach 0.80)
  Meaning: Extend τ_cap only when very sure
  ✓ Makes sense

For τ_risk:
  Require LOWER CI >= threshold
  = Conservative: "We're CONFIDENT R ≥ 0.20"
  = High bar (lower must reach 0.20)
  Meaning: Declare τ_risk only when very sure

BUT SEMANTIC DIFFERENCE!

For capability:
  "We're sure it passes" → Safe to extend τ_cap

For risk:
  "We're sure it fails" → But τ_risk should mark
                           the ONSET of failure

Should τ_risk use POINT ESTIMATE instead of LOWER CI?
Or use UPPER CI for risky threshold crossing?

τ_risk = min{b : upper(R, n, z) > 0.20}
  = First bin where we CANNOT RULE OUT risk > 0.20
  = Precautionary principle

This is asymmetric with τ_cap approach!
```

**Recommendation**: Document and justify asymmetry, OR align both to same CI strategy

---

### 1.3 Zone Classification Logic

#### **CLAIMED DECISION RULES**
```
Zone 1 (Q1): C ≥ τ_C AND R ≤ τ_R
  → "High capability, low risk"
  → Decision: Deploy pure SLM

Zone 2 (Q2): C ≥ τ_C AND R > τ_R
  → "High capability, high risk"
  → Decision: SLM with verification/escalation

Zone 3 (Q3): C < τ_C AND R ≤ τ_R
  → "Low capability, low risk"
  → Decision: Hybrid (SLM for easy, LLM for hard)

Zone 4 (Q4): C < τ_C AND R > τ_R
  → "Low capability, high risk"
  → Decision: Deploy pure LLM
```

#### **IMPLEMENTATION**

**Phase 0 Zone Classification** (framework.py:387-407)
```python
def classify_quadrant(self, tau_cap, tau_risk, capability_gap, avg_risk):
    """Uses tipping points to assign zones"""
    if tau_cap is not None and tau_cap < 4:
        if tau_risk is not None and tau_risk <= tau_cap:
            return "Q4"
        else:
            return "Q3"
    else:
        if tau_risk is not None and tau_risk < 4:
            return "Q2"
        else:
            return "Q1"
```

**Phase 1 Zone Classification** (production_router.py:287-296)
```python
def _classify_zone(self, capability, risk, tau_c, tau_r):
    """Uses empirical thresholds τ_C=0.80, τ_R=0.20"""
    if capability >= tau_c and risk <= tau_r:
        return "Q1"
    elif capability >= tau_c and risk > tau_r:
        return "Q2"
    elif capability < tau_c and risk <= tau_r:
        return "Q3"
    else:
        return "Q4"
```

#### **AUDIT FINDING** 🔴 CRITICAL

**Issue**: Two different zone classification methods produce inconsistent results!

**Evidence**:

| Scenario | Phase 0 (Tipping Points) | Phase 1 (Empirical) | Agreement |
|----------|-------------------------|-------------------|-----------|
| τ_cap=3, τ_risk=4 | Q3 (cap<4, risk>cap) | Depends on C,R values | ❌ NO |
| τ_cap=4, τ_risk=2 | Q2 (cap=4, risk<4) | Depends on C,R values | ❌ NO |
| τ_cap=2, τ_risk=1 | Q4 (cap<4, risk≤cap) | Depends on C,R values | ❌ NO |

**Concrete Example**:
```python
# Phase 0 Analysis Result
analysis = {
    'tau_cap': 3,      # Model safe up to bin 3
    'tau_risk': 2,     # Model unsafe starting at bin 2
    'zone': 'Q3'       # Hybrid routing
}

# Phase 1: Routing request in bin 1 (difficulty=0.25)
difficulty = 0.25
bin_id = 1
capability = interpolate(curve={0:0.85, 1:0.82, 2:0.80, 3:0.75, 4:0.70}, d=0.25)
           = 0.823
risk = interpolate(curve={0:0.15, 1:0.18, 2:0.22, 3:0.25, 4:0.30}, d=0.25)
     = 0.168

# Phase 1 zone classification
zone = _classify_zone(0.823, 0.168, 0.80, 0.20)
     = Q1 (C >= 0.80 and R <= 0.20)

# INCONSISTENCY!
# Phase 0 said: Zone Q3 (use hybrid)
# Phase 1 says: Zone Q1 (use pure SLM)
# Same analysis, different decisions!
```

**Root Cause**:
```
Phase 0: Zone_0 = f(τ_cap, τ_risk)
Phase 1: Zone_1 = f(C(d), R(d), τ_C, τ_R)

They should be consistent:
Zone_0 = Zone_1 for the same model/task

But they use DIFFERENT logic:
- Phase 0: Tipping point logic
- Phase 1: Empirical threshold logic

For them to match:
∀b: _classify_zone(C(b), R(b), τ_C=0.80, τ_R=0.20)
    must equal classify_quadrant(τ_cap, τ_risk, ...)

This is NOT guaranteed by the current code!
```

**Mathematical Relationship (Should Exist)**:
```
IF C >= 0.80 for bin b, THEN τ_cap >= b
IF R > 0.20 for bin b, THEN τ_risk <= b (or undefined if never exceeded)

So if we're in bin 1:
  - C(1) = 0.82 >= 0.80 → expect τ_cap >= 1
  - R(1) = 0.18 <= 0.20 → expect τ_risk > 1 or undefined

  If τ_cap >= 1 and τ_risk undefined, then phase 0 says Q1
  And phase 1 with C=0.82, R=0.18 also says Q1
  ✓ Consistent!

But the formalization is IMPLICIT, not EXPLICIT.
No guarantee they stay aligned across all samples/bins.
```

**Recommendation**:
```
Add synchronization logic:

1. Phase 1 should use tipping points from Phase 0:

   def _classify_zone_from_tipping_points(bin_id, tau_cap, tau_risk):
       if tau_cap is None:
           tau_cap = num_bins  # Never fails
       if tau_risk is None:
           tau_risk = -1  # Always safe

       if bin_id <= tau_cap and bin_id > tau_risk:
           return "Q1" if tau_risk < 0 else "Q2"
       elif bin_id > tau_cap and bin_id <= tau_risk:
           return "Q3"
       else:
           return "Q4"

2. Or, document that:
   - Phase 0 zone: Overall quadrant for model
   - Phase 1 zone: Per-request classification
   - They may differ based on per-request difficulty interpolation
   - This is intentional and correct
```

---

## SECTION 2: Logical Consistency

### 2.1 Empirical Thresholds

#### **DEFINED THRESHOLDS**
```python
empirical_tau_c = 0.80  # Capability threshold
empirical_tau_r = 0.20  # Risk threshold
```

#### **SEMANTIC QUESTIONS** 🟡 MEDIUM

**Question 1**: Where do these values come from?
```
From docs: "Empirical thresholds"
From code: Hard-coded to 0.80 and 0.20

Missing:
- How were these chosen?
- Are they justified theoretically?
- Do they work across all tasks/models?
- Should they be task-specific?
- Is 0.80 always "good enough" capability?
- Is 0.20 always "too risky"?

In research paper:
- Need ablation studies showing robustness
- Need sensitivity analysis
- Need justification or sensitivity analysis
```

**Question 2**: Asymmetry in interpretation
```
τ_C = 0.80 means: "Capability ≥ 80% is good"
τ_R = 0.20 means: "Risk ≤ 20% is acceptable"

Semantic question:
  If C = 0.80, then R = 0.20 (if complementary)
  So really: C = 0.80 ↔ R = 0.20

But they're independent! So:
  C = 0.85, R = 0.35 → Is this good or bad?

  Phase 1 says: Q2 (high C, high R)
  Interpretation: "Capable but risky"

  But what does this really mean?
  - 85% of outputs are valid (structurally sound)
  - 65% of outputs meet quality bar (functionally good)
  - Implication: 20% of valid outputs fail quality
```

---

### 2.2 Zone-to-Policy Mapping

#### **LOGICAL CHAIN**

**Claimed**:
```
Zone → Routing Policy → Cost-Benefit Outcome

Z1 (High C, Low R) → Pure SLM
  → Cost: Low ($)
  → Success: High (>80%)
  → Justification: Safe to deploy

Z2 (High C, High R) → SLM+Verify+Escalate
  → Cost: Medium ($$)
  → Success: High (>80% with verification)
  → Justification: Usually works, escalate when risky

Z3 (Low C, Low R) → Hybrid (SLM/LLM by difficulty)
  → Cost: Medium ($$)
  → Success: High (80% easy with SLM + 95% hard with LLM)
  → Justification: SLM good for easy, LLM for hard

Z4 (Low C, High R) → Pure LLM
  → Cost: High ($$$)
  → Success: Highest (>95%)
  → Justification: SLM not capable enough
```

#### **AUDIT FINDING** 🔴 CRITICAL

**Issue**: Cost-Benefit mapping is IMPLICIT and UNJUSTIFIED

```
Question 1: What is the Cost-Benefit Model?

Documented: "Cost savings" (10-97% mentioned)
Actual Code: No explicit cost model

If SLM costs $0.001 and LLM costs $1.00:
  Z1: Pure SLM = $0.001/request
  Z4: Pure LLM = $1.00/request

  Cost ratio: 1000:1

But the zones don't optimize for this!
The zones ONLY consider capability/risk, not cost.

This is scientifically unsound!
A proper model would be:

  Cost(Z) = P(use_SLM | Z) * Cost_SLM + P(use_LLM | Z) * Cost_LLM
  Benefit(Z) = P(success | Z)
  Utility(Z) = Benefit(Z) / Cost(Z)

But the paper doesn't define this formally.
```

**Question 2**: What is "success"?

```
Defined in code:
  - For code gen: "tests pass" ✓
  - For classification: "correct label" ✓
  - For text gen: "constraint satisfied" ✓

But what about:
  - Cost of failure (varies wildly)
  - User impact (varies by use case)
  - Business metrics (not defined)

A medical diagnosis failure ≠ typo failure
But the framework treats them the same!

Research question:
  "Are the zones optimal for different domains?"

Answer: Unknown! No domain-specific analysis.
```

---

### 2.3 Verification Function Contract

#### **DEFINED**
```python
verification_fn: Callable[[
    task: str,
    model: str,
    input_text: str,
    difficulty: float,
    bin_id: int,
    capability: float,
    risk: float
], bool]

Returns: True if output is acceptable, False if escalate
```

#### **LOGICAL ISSUES** 🟠 HIGH

**Issue 1**: Verification function has access to ESTIMATED risk/capability
```python
# In route() method, line 248:
verified = bool(self.verification_fn(
    task,
    preferred_model,
    input_text,
    difficulty,
    bin_id,
    capability,  # ← Interpolated estimate
    risk         # ← Interpolated estimate
))

Problem:
  These are ESTIMATES from the model-level curves
  They're NOT the actual observed success/failure!

  The verification function receives:
    - capability = 0.82 (model historical success rate)
    - But the actual output might be wrong

  This is circular reasoning:
    "Model usually works (0.82), so let's check if this output works"

  But the verification should be INDEPENDENT of these estimates!

Example:
  Task: code generation
  Model: qwen
  Output: "def foo(): pass"

  verification_fn() receives:
    capability = 0.82
    risk = 0.28

  Should the verifier care that capability=0.82?
  Or should it ONLY check if this specific output is good?

  Currently: Mixes both
  Scientifically: Should be independent
```

**Issue 2**: Verification function should return CONFIDENCE, not BINARY
```
Current: returns bool (accepted/rejected)

Problem:
  Zone Q2 should verify output quality
  But bool gives no information about:
  - Confidence level (0.51 vs 0.99 confidence both return True)
  - Degree of risk (minor typo vs major error both return False)

Better design:
  def verification_fn(...) -> float:
      Returns confidence in [0, 1]
      1.0 = definitely good
      0.5 = borderline
      0.0 = definitely bad

  Then:
    if confidence > 0.90:
        use_slm()
    elif confidence > 0.70:
        human_review()
    else:
        escalate_to_llm()
```

---

## SECTION 3: Curve Computation Math

### 3.1 Soft Bin Assignment

#### **ALGORITHM**
```python
def difficulty_to_bin_probabilities(difficulty: float, num_bins: int) -> Dict[int, float]:
    """Assign soft probabilities to bins"""
    bin_position = difficulty * (num_bins - 1)  # 0.25 → 1.0
    lower = int(bin_position)                    # 1
    upper = min(lower + 1, num_bins - 1)        # 2
    fraction = bin_position - lower              # 0.0

    result = {}
    result[lower] = 1 - fraction                 # P(bin 1) = 1.0
    result[upper] = fraction                     # P(bin 2) = 0.0
    return result
```

#### **AUDIT FINDING** 🟢 CORRECT

**Analysis**:
```
The soft assignment is mathematically sound:
- Linear interpolation between adjacent bins
- Probabilities sum to 1.0
- Boundary conditions correct (difficulty=0→bin 0, difficulty=1→bin 4)

Example:
  difficulty = 0.375
  bin_position = 0.375 * 4 = 1.5
  lower = 1, upper = 2, fraction = 0.5

  P(bin 1) = 1 - 0.5 = 0.5 ✓
  P(bin 2) = 0.5 ✓
  Sum = 1.0 ✓
```

**Justification in Paper**:
```
Good! Smoothly interpolates between discrete bins.
Avoids cliff effects where difficulty=0.250 and 0.251
give completely different curves.
```

---

### 3.2 Expected Value Computation

#### **ALGORITHM**
```python
def compute_expected_capability(difficulty, capability_curve, num_bins):
    """E[capability] = Σ_k P(bin_k | difficulty) × C(bin_k)"""
    bin_probs = difficulty_to_bin_probabilities(difficulty, num_bins)

    expected = 0.0
    for bin_id, prob_bin in bin_probs.items():
        cap = capability_curve.get(bin_id, 0.5)
        expected += prob_bin * cap

    return expected
```

#### **AUDIT FINDING** 🟢 CORRECT

**Analysis**:
```
Mathematical foundation is sound:
- Proper expectation calculation
- Uses soft bin probabilities
- Linear in the probabilities (correct)
- Handles missing bins with default 0.5 (reasonable)

Example:
  difficulty = 0.375
  capability_curve = {0: 0.90, 1: 0.85, 2: 0.80, 3: 0.75, 4: 0.70}
  bin_probs = {1: 0.5, 2: 0.5}

  E[C] = 0.5 × 0.85 + 0.5 × 0.80 = 0.825
```

**Note**: This assumes bin transitions are smooth and linear, which is reasonable but not proven.

---

### 3.3 Wilson Confidence Interval Usage

#### **ALGORITHM**
```python
def wilson_interval(p: float, n: int, z: float = 1.96) -> (float, float):
    """Compute Wilson score confidence interval"""
    denominator = 1 + z²/n
    center = (p + z²/(2n)) / denominator
    margin = z * sqrt(p(1-p)/n + z²/(4n²)) / denominator

    lower = center - margin
    upper = center + margin
    return (lower, upper)
```

#### **AUDIT FINDING** 🟢 CORRECT

**Analysis**:
```
Wilson interval is statistically sound:
- Used in modern proportion estimation
- Handles edge cases (p=0, p=1) better than normal CI
- Appropriate z-value for α=0.05 (z=1.96)
- Properly accounts for finite sample size

Good choice for statistical gating!
```

**But Usage Question** 🟡 MEDIUM

```
Code applies it to:
1. Tipping point detection (τ_cap, τ_risk)
2. Capability/risk estimates

These have DIFFERENT sample sizes:
- τ_cap: Pool from entire model analysis (large n)
- Per-request: Single sample or small batch (small n)

Should per-request routing use CIs?
- Yes: proper Bayesian approach
- But with SMALL n (often 1), CI is very wide
- May make confidence bounds useless

Example:
  n = 1 (single request)
  p = 1.0 (output is good)
  CI = [0.65, 1.00] (very wide!)

  lower bound 0.65 >> risk threshold 0.20
  So we'd still escalate even though this sample is good

Conclusion: CI usage is statistically sound but may not
            help for per-request decisions (n=1)
```

---

## SECTION 4: Summary of Findings

### Critical Issues (🔴 Must Fix Before Publication)

| ID | Issue | Severity | Impact |
|---|--------|----------|--------|
| **M1** | C ≠ (1 - R) violation | 🔴 CRITICAL | Invalidates complementarity assumption, breaks zone logic |
| **M2** | Inconsistent zone classification | 🔴 CRITICAL | Phase 0 and Phase 1 can disagree on routing |
| **M3** | Verification function circularity | 🟠 HIGH | Uses estimated metrics to verify actual output |
| **M4** | τ_cap/τ_risk asymmetry in CI logic | 🟠 HIGH | Different strategies for same statistical goal |
| **M5** | Cost-benefit mapping undefined | 🔴 CRITICAL | Claims cost savings without modeling costs |

### Medium Issues (🟡 Should Fix)

| ID | Issue | Severity | Impact |
|---|--------|----------|--------|
| **L1** | Empirical thresholds unjustified | 🟡 MEDIUM | τ_C=0.80, τ_R=0.20 chosen without justification |
| **L2** | Domain-specific assumptions | 🟡 MEDIUM | Zones don't account for task-specific failure costs |
| **L3** | "Success" metric undefined | 🟡 MEDIUM | Varies by task, not formalized |
| **L4** | CI usage in single-sample case | 🟡 MEDIUM | Wilson intervals have wide bounds for n=1 |

### Low Issues (🟢 Minor)

| ID | Issue | Severity | Impact |
|---|--------|----------|--------|
| **M6** | Soft bin interpolation | 🟢 LOW | Mathematically sound, linearity assumption unstated |
| **M7** | Expected value computation | 🟢 LOW | Correct, smoothness assumption not justified |

---

## SECTION 5: Recommendations for Remediation

### For Publication-Ready Manuscript:

**Priority 1 (Blocking)**:
1. **Rename Metrics** (Issue M1)
   - Call it "Validity" not "Capability"
   - Document as independent metrics
   - Update all zone descriptions

2. **Fix Zone Consistency** (Issue M2)
   - Either align Phase 0/Phase 1 logic
   - Or document intended differences
   - Add formal proof they converge

3. **Formal Cost Model** (Issue M5)
   - Define explicit cost function
   - Show zones are cost-benefit optimal
   - Provide ablation studies

**Priority 2 (Important)**:
1. **Document Thresholds** (Issue L1)
   - Sensitivity analysis for τ_C, τ_R
   - Justification or adaptive selection
   - Task-specific threshold tables

2. **Fix Verification Contract** (Issue M3)
   - Make verification independent of estimates
   - Consider continuous confidence instead of binary
   - Document proper usage

3. **CI Justification** (Issue M4)
   - Justify asymmetric CI usage
   - Or align both to same principle
   - Document empirical performance

---

## SECTION 6: Mathematical Rigor Checklist

- ❌ Metrics properly defined and notation consistent
- ❌ Complementarity assumptions stated and verified
- ❌ Tipping point definitions precise and implemented correctly
- ❌ Zone classification rules formally verified to be consistent
- ❌ Cost-benefit function explicit and optimized
- ❌ Empirical parameter choices justified
- ⚠️ Confidence interval usage appropriate to context
- ✅ Expected value computations correct
- ⚠️ Domain-specific assumptions documented

---

## Conclusion

The system has **sound mathematical foundations** in many areas (soft binning, expected value, CIs) but **critical inconsistencies** in its core claims:

1. **Capability ≠ (1 - Risk)**: Core assumption violated
2. **Zone inconsistency**: Phase 0 and Phase 1 may disagree
3. **Cost-benefit implicit**: No formal optimization model

**For a top-tier research venue**: Would require major revisions addressing issues M1, M2, M5 before acceptance.

**Current Status**: Pre-publication manuscript requiring significant work.

---

## Appendix: Recommended Changes for Soundness

### Option A: Separate Metrics (Recommended)
```
Change framework to:
  V_m(b) = validity (structural check)
  Q_m(b) = quality (functional check)

Define zones as:
  Z1: V >= 0.80 AND Q >= 0.80
  Z2: V >= 0.80 AND Q < 0.80
  Z3: V < 0.80 AND Q >= 0.80
  Z4: V < 0.80 AND Q < 0.80

Then NO constraint that V + Q = 1.0
All math becomes self-consistent!
```

### Option B: Redefine Capability
```
Change to:
  C_m(b) = P(valid AND quality >= threshold)

Then:
  C = V AND Q (probabilistically)
  And naturally C <= V, C <= Q

This makes:
  C + R = 1.0 (where R = 1 - C, as defined)
  But R ≠ quality_failure_rate!

This option is LESS flexible but more consistent.
```

**RECOMMENDATION**: Option A (separate metrics) is more flexible and better aligned with actual computational practices in the code.
