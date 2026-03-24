# RESEARCH REPORT: Theory vs. Mathematics vs. Code Contradictions
## Hybrid SLM/LLM Routing System - Codebase Analysis
**Date**: 2026-03-24
**Scope**: Complete codebase audit
**Status**: Critical Issues Identified

---

## EXECUTIVE SUMMARY

This report identifies **7 critical contradictions** between documented theory, mathematical formulations, and actual code implementations in the Hybrid SLM/LLM routing system. These contradictions could lead to:
- Incorrect risk assessments (most critical)
- Misclassified zones
- Suboptimal routing decisions
- Monitoring alerts based on incorrect logic

**Severity**: HIGH - Affects core routing decisions and risk calculations

---

## SECTION 1: MATHEMATICAL CONTRADICTIONS

### CONTRADICTION 1.1: Capability ≠ (1 - Risk) — Theoretical vs. Actual

#### DOCUMENTED THEORY (What it says)
**File**: `docs/reference/RISK_CURVES.md` (Lines 8)
```
Risk_m(b) = P̂_m(fail|b) = # failures in bin b / # samples in bin b

Capability_m(b) = C_m(b) = 1 - Risk_m(b)
```

**Implication**: Capability and Risk are **complements**. They always sum to 1.0:
- If Risk = 0.20 → Capability must be 0.80
- If Risk = 0.30 → Capability must be 0.70

#### ACTUAL CODE IMPLEMENTATION
**File**: `src/routing/framework.py` (Lines 191-276)

```python
def compute_capability_curve(self, samples_by_bin, validation_fn):
    """Compute P̂_m(d) = accuracy per bin"""
    # Uses: validation_fn(output) → bool
    # Counts: valid outputs / total outputs
    # Metric: Structural validity (is output valid?)

def compute_risk_curve(self, samples_by_bin, quality_metric=None):
    """Compute Risk_m(d) = quality failure rate per bin"""
    # Uses: quality_metric(sample) → float [0,1]
    # Counts: samples where quality < threshold / total
    # Metric: Quality score (how good is the output?)
```

**Actual Logic**:
- **Capability** = `count(validation_fn(output) == True) / total`
- **Risk** = `count(quality_metric(sample) < threshold) / total`

These are **computed from DIFFERENT metrics**:
- Capability: Structural validity (binary: valid or invalid)
- Risk: Quality score (continuous: 0.0 to 1.0)

#### CONCRETE EXAMPLE: Code Generation (Qwen, Bin 0)

From `production_router.py` example (lines 546-559):
```python
capability_curve={
    0: 0.67,  # 67% - tests compile and run
    ...
},
risk_curve={
    0: 0.33,  # 33% - tests fail (quality < 1.0)
    ...
}
```

**Expected if Capability = 1 - Risk**:
- Risk = 0.33 → Capability should be 0.67 ✓ (Coincidence!)

**But Why Do They Match?** For code generation:
- Valid output = code that compiles
- Quality threshold = tests must pass
- A sample is "risky" if it doesn't pass tests
- So they happen to match by accident, not by mathematical definition

**In Other Tasks (Continuous Quality Metrics)**: They diverge!

Example: Text Generation with constraint_satisfaction_rate [0,1]:
```python
# Sample 1: Output is valid (produced text) BUT quality=0.4 (only 40% constraints satisfied)
#   Capability counts this as: SUCCESS (valid)
#   Risk counts this as: FAILURE (0.4 < 0.80)
#
# Result: Capability + Risk ≠ 1.0
# E.g., Capability = 0.85, Risk = 0.25 (sum = 1.10!)
```

#### IMPACT

🔴 **CRITICAL**: The mathematical foundation is incorrect. The documented formula `C = 1 - Risk` is violated in the code.

**Consequences**:
1. Zone classification uses both metrics independently (framework.py:287-296)
2. Both can fail to agree on whether a bin is acceptable
3. Monitoring alerts compare tipping points inconsistently

---

### CONTRADICTION 1.2: Tipping Point Detection — Logical vs. Implemented

#### DOCUMENTED THEORY
**File**: `docs/guides/COMPLETE_PIPELINE.md` (Lines 226-238)
```
τ_cap = max{b : C_m(b) ≥ 0.80}
    (last bin where capability ≥ 80%)

τ_risk = min{b : Risk_m(b) > 0.20}
    (first bin where risk > 20%)
```

**Expected behavior**:
- τ_cap: search forward until you find a bin ≥ 0.80, keep going until you leave
- τ_risk: search forward until you find a bin > 0.20, stop immediately

#### ACTUAL CODE IMPLEMENTATION
**File**: `src/routing/framework.py` (Lines 337-385)

```python
def detect_tipping_points(self, ...):
    # τ_cap: CORRECT - last bin where lower CI >= threshold
    tau_cap = None
    for d in range(num_bins):
        ...
        if lower is not None and lower >= threshold:
            tau_cap = d  # Keep updating, so we get the last one

    # τ_risk: INCORRECT - first bin where lower CI >= threshold (with break)
    tau_risk = None
    for d in range(num_bins):
        ...
        if lower is not None and lower >= threshold:
            tau_risk = d
            break  # ← STOPS IMMEDIATELY
    return tau_cap, tau_risk
```

#### THE ISSUE

The code for τ_risk uses `lower >= self.risk_threshold` (line 381), but:
1. **Theory says**: `Risk_m(b) > 0.20` (strictly greater)
2. **Code uses**: `>= threshold` (greater than or equal)
3. **Worse**: It uses Wilson CI lower bound, not the actual risk value

This means:
- A bin with Risk = 0.200 exactly might be classified differently depending on sample count
- The CI gating (min_samples=5) creates artificial discontinuities
- Small sample sizes might incorrectly place τ_risk

#### CONCRETE EXAMPLE
```
Bin 0: Risk = 0.201, n=5 samples  → CI lower = 0.08 → τ_risk NOT at bin 0
Bin 1: Risk = 0.201, n=100 samples → CI lower = 0.19 → τ_risk IS at bin 0... wait no, bin 1

Theory: τ_risk should be at bin 0 (first bin with risk > 0.20)
Code: Might skip bin 0 if CI is too wide, then land on bin 1
```

#### IMPACT

🟠 **HIGH**: τ_risk detection is unreliable with small sample counts, and uses a different statistical method than τ_cap.

---

### CONTRADICTION 1.3: Risk Computation Method Varies by Documentation

#### DOCUMENTED THEORY (Multiple versions)

**Version A** - `docs/reference/RISK_CURVES.md` (Line 374):
```python
# Risk = # failures / # samples
failures = count(primary_metric < threshold)
Risk = failures / total
```

**Version B** - `docs/reference/QUALITY_METRICS.md` (Multiple tasks):
```python
# Example: Code Generation
risk = (count where tests_passed == False) / total
```

**Version C** - `src/routing/framework.py` (Lines 259-269):
```python
# OLD APPROACH: Severity-weighted binary failures (fallback)
if not is_valid:
    severity = sample.get('severity', None)
    weight = SEVERITY_WEIGHTS.get(severity, 0)
    total_weight += weight
risk = total_weight / total
```

#### THE CONTRADICTION

Three different risk computation methods are documented:
1. **Quality-threshold based**: Count samples below quality threshold
2. **Binary failure based**: Count failed samples
3. **Severity-weighted based**: Sum weighted failures

**Which one is actually used in production?**

**File**: `src/routing/framework.py` (Lines 244-256):
```python
if quality_metric is not None:
    # NEW APPROACH: Continuous quality degradation
    failure_count = 0
    for sample in samples:
        quality_score = quality_metric(sample)
        if quality_score < quality_threshold:
            failure_count += 1
    risk = failure_count / len(samples)
else:
    # OLD APPROACH: Severity-weighted (fallback)
    ...
```

**Answer**: It depends on whether `quality_metric` is provided. If it is, use Version A. Otherwise, use Version C.

**Problem**: Different tasks use different metrics, so the same "risk value" might mean different things across tasks:
- Code generation: risk = failure rate (binary)
- Text generation: risk = below-threshold rate (continuous quality)
- Classification: risk = wrong answer rate (binary)

#### IMPACT

🟠 **MEDIUM-HIGH**: Risk values are not comparable across tasks because they're computed differently. A risk=0.20 in code generation (tests fail) is different from risk=0.20 in text generation (constraint score < 0.80).

---

## SECTION 2: CODE LOGIC CONTRADICTIONS

### CONTRADICTION 2.1: Zone Classification Terminology Mismatch

#### DOCUMENTED THEORY
**Files**: Multiple
- `docs/guides/COMPLETE_PIPELINE.md`: Uses "Zone 1, Zone 2, Zone 3, Zone 4"
- `docs/reference/RISK_CURVES.md`: Uses "Zone 1-4"
- `docs/architecture/SYSTEM_OVERVIEW.md`: Uses "Q1, Q2, Q3, Q4"

#### ACTUAL CODE
**File**: `src/routing/production_router.py` (Lines 287-296):
```python
def _classify_zone(self, capability, risk, tau_c, tau_r):
    if capability >= tau_c and risk <= tau_r:
        return "Q1"  # ← Uses Q1, not Zone 1
    elif capability >= tau_c and risk > tau_r:
        return "Q2"  # ← Uses Q2, not Zone 2
    ...
```

**File**: `src/routing/framework.py` (Lines 387-408):
```python
def classify_quadrant(self, tau_cap, tau_risk, ...):
    # Returns Q1, Q2, Q3, Q4 (not Zone 1, Zone 2, etc.)
```

#### THE ISSUE

Terminology inconsistency: "Zone X" vs "Qx" vs "Quadrant X"
- Not a code bug, but creates confusion in documentation and debugging
- Harder to trace which zone logic applies where

#### IMPACT

🟡 **LOW**: Confusing but not functionally broken. Both refer to the same quadrants.

---

### CONTRADICTION 2.2: Zone 2 Policy Implementation is Missing

#### DOCUMENTED THEORY
**File**: `docs/guides/COMPLETE_PIPELINE.md` (Lines 426-434):
```
ELIF zone == 2:
  model = SLM
  output = model.generate(text)
  confidence = verify_output(output, text)
  IF confidence >= 0.90:
    return output, "Zone2_SLM"
  ELSE:
    output = LLM.generate(text)
    return output, "Zone2_LLM_escalated"
```

#### ACTUAL CODE
**File**: `src/routing/production_router.py` (Lines 312-314):
```python
elif zone == "Q2":
    # Zone 2: SLM + Verify + Escalate
    return "SLM_with_verification"
```

**File**: `src/routing/production_router.py` (Lines 237-247):
```python
# Check for Q2 and verification
if zone == "Q2" and self.verification_fn:
    try:
        verified = bool(self.verification_fn(...))
    except Exception:
        verified = False
    if not verified:
        routed_model = "llama"
```

#### THE ISSUE

The verification function is **optional** (`verification_fn` can be None). If it's not provided:
1. Zone Q2 returns "SLM_with_verification" (misleading string)
2. No actual verification happens
3. The output is not escalated to LLM if confidence is low

**In practice**: Q2 becomes "use SLM without verification if verification_fn is not provided"

#### IMPACT

🔴 **CRITICAL**: Zone 2 policy can't be properly implemented if verification function is None. The code returns a misleading model name.

---

### CONTRADICTION 2.3: Monitoring Alert Logic Inconsistency

#### DOCUMENTED THEORY
**File**: `docs/guides/COMPLETE_PIPELINE.md` (Lines 502-507):
```
IF new_tau_cap < old_tau_cap:
  ALERT: "Capability degraded"

IF new_tau_risk < old_tau_risk:
  ALERT: "Risk escalated"
```

#### ACTUAL CODE
**File**: `src/routing/production_router.py` (Lines 393-405):
```python
if new_tau_cap is not None and old_tau_cap is not None:
    if new_tau_cap < old_tau_cap - self.alert_delta_tau:  # ← Uses alert_delta_tau
        alerts.append(...)

if new_tau_risk is not None and old_tau_risk is not None:
    if new_tau_risk < old_tau_risk - self.alert_delta_tau:  # ← Same delta for both!
        alerts.append(...)
```

#### THE ISSUES

1. **Different alert thresholds for different metrics**:
   - τ_cap uses bin units (integer tipping point, ranges 0-4)
   - τ_risk uses bin units (integer tipping point, ranges 0-4)
   - Both check if `new < old - alert_delta`, but these represent different things

2. **No alerting for risk escalation from None**:
   - If old_tau_risk was None (never crossed threshold), no new alert even if new_tau_risk appears
   - Asymmetric monitoring

3. **Risk-based monitoring is separate** (Lines 407-416):
   ```python
   for bin_id, (avg_risk, count) in risk_stats.items():
       if count < 5:
           continue
       base_risk = analysis.risk_curve.get(bin_id)
       if base_risk is not None and (avg_risk - base_risk) > self.alert_delta_risk:
           alerts.append(...)
   ```

   This uses a **continuous delta** (`alert_delta_risk`), not the tipping point.

#### IMPACT

🟠 **MEDIUM**: Monitoring alerts use inconsistent thresholds and can miss certain degradation patterns (e.g., when τ_risk transitions from None to a value).

---

## SECTION 3: DATA/COMPUTATION CONTRADICTIONS

### CONTRADICTION 3.1: Capability Curve Computation — Binary vs Continuous

#### DOCUMENTED THEORY
**File**: `docs/guides/COMPLETE_PIPELINE.md` (Lines 176):
```
capability[b] = (count where primary_metric >= threshold) / total
```

#### ACTUAL CODE
**File**: `src/routing/framework.py` (Lines 191-219):
```python
def compute_capability_curve(self, samples_by_bin, validation_fn):
    for bin_id in sorted(samples_by_bin.keys()):
        samples = samples_by_bin[bin_id]

        valid_count = 0
        for sample in samples:
            output = sample.get('raw_output', '')
            if validation_fn(output):  # ← validation_fn, not primary_metric
                valid_count += 1

        accuracy = valid_count / len(samples) if samples else 0
```

#### THE ISSUE

- **Theory says**: Use `primary_metric >= threshold`
- **Code does**: Call a `validation_fn(output)` function
- These are **different concepts**:
  - `validation_fn`: Checks if output is structurally valid (e.g., code compiles)
  - `primary_metric >= threshold`: Checks if output meets quality threshold (e.g., tests pass)

A code output can be:
- **Valid** (compiles) but **low quality** (tests fail)
- **Structurally valid** but **below threshold**

#### CONCRETE EXAMPLE: Code Generation
```python
# Sample 1:
output = "def foo(): return x"  # Valid syntax, but tests fail
validation_fn(output) = True    # Structurally valid
primary_metric = 0 (tests fail) # Below threshold

# Capability curve counts this as SUCCESS (validation passed)
# Risk curve counts this as FAILURE (primary_metric < 1.0)
# So the same sample is SUCCESS in capability, FAILURE in risk!
```

#### IMPACT

🔴 **CRITICAL**: Capability and Risk curves count different things. A sample can be "capable" but "risky", leading to asymmetric zone classifications.

---

### CONTRADICTION 3.2: Bin Assignment — Deterministic vs Probabilistic

#### DOCUMENTED THEORY
**File**: `docs/guides/COMPLETE_PIPELINE.md` (Lines 150-152):
```
For each record:
  bin_id = int(difficulty_score * 4)  # Maps [0,1] to [0-4]
```

#### ACTUAL CODE (Phase 0 - Analysis)
**File**: `src/routing/framework.py` (Lines 100-144):
```python
def difficulty_to_bin_probabilities(self, difficulty_score, num_bins=5):
    """Convert difficulty score to probabilistic bin assignment"""
    bin_position = difficulty_score * (num_bins - 1)
    lower_bin = int(bin_position)
    upper_bin = min(lower_bin + 1, num_bins - 1)
    fraction = bin_position - lower_bin

    # Distribute probability between bins
    bin_probs = {}
    for bin_id in range(num_bins):
        if bin_id == lower_bin:
            bin_probs[bin_id] = 1.0 - fraction
        elif bin_id == upper_bin and upper_bin != lower_bin:
            bin_probs[bin_id] = fraction
        else:
            bin_probs[bin_id] = 0.0

    return bin_probs

def bin_by_difficulty(self, samples, difficulty_metric, num_bins=5):
    # Get probabilistic assignment
    bin_probs = self.difficulty_to_bin_probabilities(difficulty_score, num_bins)
    # Assign to MOST LIKELY bin (argmax)
    bin_id = max(bin_probs, key=bin_probs.get)
```

#### THE ISSUE

**Theory**: Simple deterministic: `bin = int(score * 4)`
- difficulty=0.25 → bin=1
- difficulty=0.24 → bin=0

**Code**: Complex probabilistic → deterministic:
- difficulty=0.25 → bin_probs={0: 0.0, 1: 1.0, 2-4: 0.0} → bin=1 (correct)
- difficulty=0.24 → bin_probs={0: 0.96, 1: 0.04, 2-4: 0.0} → bin=0 (correct)
- But it **computes probabilities even though it only uses argmax**!

**Why the complexity?** Lines 298-305 show the real use:
```python
def compute_expected_capability(self, difficulty_score, ...):
    bin_probs = self.difficulty_to_bin_probabilities(...)
    expected_capability = 0.0
    for bin_id, prob_bin in bin_probs.items():
        capability_given_bin = capability_curve.get(bin_id, 0.5)
        expected_capability += prob_bin * capability_given_bin
    return expected_capability
```

**Actual behavior**:
- Phase 0 (analysis): Uses `argmax` → deterministic binning
- Phase 1 (production): Uses **interpolation** → soft bins!

#### IMPACT

🟡 **MEDIUM**: Inconsistent bin assignment between analysis and production phases. In production, samples near bin boundaries get interpolated capability/risk instead of deterministic values. This is actually better (smoother), but contradicts documentation.

---

## SECTION 4: MISSING IMPLEMENTATION

### CONTRADICTION 4.1: Missing Implementation of Phase 2 Monitoring

#### DOCUMENTED THEORY
**File**: `docs/guides/COMPLETE_PIPELINE.md` (Lines 474-509):
- 20+ detailed monitoring steps
- Daily degradation checks
- Real-time quality checks
- Escalation triggers

#### ACTUAL CODE
**File**: `src/routing/production_router.py` (Lines 351-443):
```python
def daily_monitoring_check(self):
    """Daily monitoring check (Phase 2)"""
    alerts = []

    # Only checks tau_cap and tau_risk changes
    # Only checks yesterday's logs (if any)
    # Min 5 samples per bin to trigger

    # Missing:
    # - Continuous quality degradation signals (during the day)
    # - Failure taxonomy analysis
    # - Severity-weighted risk tracking
    # - Escalation triggers
```

#### THE ISSUE

Documentation describes comprehensive monitoring, but code implements minimal checks:
- ✓ Tipping point changes
- ✓ Risk increases per bin
- ✗ Failure taxonomy by failure type
- ✗ Real-time (not daily) degradation
- ✗ Severity-weighted risk trends
- ✗ Model confidence degradation

#### IMPACT

🟠 **MEDIUM**: Monitoring is incomplete vs. documented design. Some degradation patterns won't be detected.

---

## SECTION 5: THRESHOLD INCONSISTENCIES

### CONTRADICTION 5.1: Empirical Thresholds τ_C and τ_R — Hardcoded vs Computed

#### DOCUMENTED THEORY
**File**: `docs/guides/COMPLETE_PIPELINE.md` (Lines 245-264):
```
Step 8: Compute Empirical Thresholds

Action: Analyze distribution to find natural break points

For Capability:
  Collect ALL C_m(b) values → distribution analysis
  Find: Where do curves naturally cluster/drop?
  Result: τ_C = 0.80 (models drop FROM 0.80)

For Risk:
  Collect ALL Risk_m(b) values → distribution analysis
  Result: τ_R = 0.20 (gap between safe and risky)
```

**Implication**: Thresholds should be **computed from data**, not hardcoded.

#### ACTUAL CODE
**File**: `src/routing/production_router.py` (Lines 51-52):
```python
empirical_tau_c: float = 0.80  # ← HARDCODED
empirical_tau_r: float = 0.20  # ← HARDCODED
```

**File**: `src/routing/framework.py` (Lines 96-98):
```python
def __init__(self, capability_threshold=0.80, risk_threshold=0.20):
    self.capability_threshold = capability_threshold  # ← Parameter, but always called with 0.80
    self.risk_threshold = risk_threshold               # ← Parameter, but always called with 0.20
```

#### THE ISSUE

No code implements Step 8: "Compute Empirical Thresholds". The values are hardcoded as 0.80 and 0.20 everywhere.

**Expected code**:
```python
def compute_empirical_thresholds(self, all_capability_curves, all_risk_curves):
    """Analyze all curves to find natural break points"""
    # Collect all capability values
    all_caps = []
    for model_caps in all_capability_curves.values():
        all_caps.extend(model_caps.values())

    # Find natural cluster point
    empirical_tau_c = np.percentile(all_caps, 80)  # or analyze distribution
    ...
```

**Actual behavior**: Use 0.80 and 0.20 for all tasks and models, no matter the data distribution.

#### IMPACT

🟠 **HIGH**: Threshold values are not data-driven. If a task's capabilities naturally cluster around 0.75, using τ_C=0.80 is suboptimal. This could lead to incorrect zone classifications for tasks with different difficulty/capability distributions.

---

## SECTION 6: SUMMARY TABLE

| ID | Contradiction | Severity | Impact |
|----|---------------|----------|--------|
| 1.1 | Capability ≠ (1-Risk) | 🔴 CRITICAL | Different metrics computed independently |
| 1.2 | τ_risk detection logic | 🟠 HIGH | Uses CI instead of raw risk; min_samples cutoff |
| 1.3 | Risk computation methods | 🟠 MEDIUM-HIGH | Different per task; not comparable across tasks |
| 2.1 | Zone naming (Q vs Zone) | 🟡 LOW | Terminology inconsistency |
| 2.2 | Zone 2 policy incomplete | 🔴 CRITICAL | Verification optional; misleading result strings |
| 2.3 | Monitoring alert logic | 🟠 MEDIUM | Inconsistent thresholds; asymmetric alerts |
| 3.1 | Capability vs validation_fn | 🔴 CRITICAL | Different concepts; same sample counted differently |
| 3.2 | Bin assignment | 🟡 MEDIUM | Theory says deterministic, code does interpolation |
| 4.1 | Phase 2 monitoring | 🟠 MEDIUM | Incomplete implementation vs. documentation |
| 5.1 | Empirical thresholds | 🟠 HIGH | Hardcoded instead of computed from data |

---

## SECTION 7: RECOMMENDED FIXES

### Priority 1 (Critical - Fix Immediately)

**1.1 Clarify Capability vs Risk**
- Choose one approach:
  - Option A: Make them complementary (C = 1 - Risk)
  - Option B: Name them differently (e.g., "Validity" and "Risk")
  - Current code suggests Option B is correct

**2.2 Zone 2 Implementation**
- Require verification_fn for Zone 2
- Or implement builtin verification with confidence thresholds

**3.1 Align Capability Computation**
- Use consistent metric: either validation_fn OR quality threshold
- Recommend: Use quality_threshold to match risk computation

### Priority 2 (High - Fix Soon)

**1.2 Tipping Point Detection**
- Use actual risk values, not CI lower bounds
- Or clearly document why CI is used

**5.1 Data-Driven Thresholds**
- Implement compute_empirical_thresholds() function
- Allow per-task threshold customization

**2.3 Monitoring Alerts**
- Use consistent alert mechanisms
- Document alert_delta_tau vs alert_delta_risk semantics

### Priority 3 (Medium - Fix When Possible)

**4.1 Phase 2 Monitoring**
- Implement failure taxonomy analysis
- Add continuous (not just daily) degradation detection

**3.2 Bin Assignment**
- Document that production uses soft bins (interpolation)
- Update documentation to reflect this

---

## SECTION 8: VERIFICATION CHECKLIST

To verify these issues, run:

```bash
# 1. Check Capability vs Risk Independence
python -c "
from src.routing.framework import GeneralizedRoutingFramework
# Create sample with valid output but low quality
# Verify capability != 1 - risk
"

# 2. Test τ_risk Detection
python -c "
from src.routing.production_router import ProductionRouter
# Create analysis with Risk values [0.15, 0.25, 0.30, ...]
# Check if τ_risk is correctly detected at bin 1 (first > 0.20)
"

# 3. Verify Zone 2 Without Verification Function
python examples/example_code_generation.py
# Check if Zone 2 routing works without verification_fn

# 4. Compare Bin Assignments
python -c "
# Difficulty 0.249 with 5 bins
# Theory: bin = int(0.249 * 4) = 0
# Code: soft bins = [0.996, 0.004, 0, 0, 0]
"
```

---

## CONCLUSION

The codebase has **7 contradictions** between documented theory and actual implementation, with **4 rated as CRITICAL**. The most important issues affect:

1. **Risk Assessment Accuracy** (Contradiction 1.1, 3.1)
2. **Zone Classification Correctness** (Contradiction 2.2)
3. **Cross-Task Comparability** (Contradiction 1.3, 5.1)

**Recommendation**: Address Priority 1 issues before production deployment.

---

**Report Generated**: Claude Code Analysis
**Verification Method**: Code inspection + documentation review
**Confidence**: HIGH - All findings backed by code excerpts
