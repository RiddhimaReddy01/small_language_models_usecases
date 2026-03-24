# ACTION ITEMS & RECOMMENDED FIXES
## Addressing Theory vs Code Contradictions

**Document**: Priority-ordered list of fixes
**Severity Levels**: 🔴 CRITICAL | 🟠 HIGH | 🟡 MEDIUM | 🟢 LOW

---

## PRIORITY TIER 1: CRITICAL (Fix Immediately Before Production)

### FIX 1.1: Clarify Capability & Risk Semantics

**Issue**: Documented as complementary (C = 1 - R) but computed independently

**Current Behavior**:
- Capability = P(structurally valid output)
- Risk = P(quality below threshold)
- Can both fail independently

**Option A: Make Them Complementary** ❌ RECOMMENDED: NO
- Would require redefining one metric
- Breaks logical separation of concerns

**Option B: Rename & Document Separately** ✅ RECOMMENDED: YES
- Rename "Capability" → "Validity" (structural soundness)
- Keep "Risk" → (quality metric failure rate)
- Update all documentation

**Implementation Steps**:

1. **Update Documentation**:
   - File: `docs/reference/RISK_CURVES.md`
   - Remove line 8: `Capability_m(b) = C_m(b) = 1 - Risk_m(b)`
   - Add section: "Validity vs Risk: Independent Metrics"

2. **Update Code Comments**:
   ```python
   # BEFORE
   def compute_capability_curve(...):
       """Compute P̂_m(d) = accuracy per bin"""

   # AFTER
   def compute_validity_curve(...):
       """Compute P(valid|d) = structural validity rate per bin

       Measures: fraction of outputs that are structurally valid
       (e.g., code compiles, JSON parses, etc.)

       Independent from quality/risk metrics.
       """
   ```

3. **Update All References**:
   ```bash
   grep -r "capability_curve" src/
   # Replace with validity_curve where appropriate
   # Or keep name but update docstrings
   ```

4. **Update Zone Logic**:
   ```python
   # BEFORE
   if capability >= tau_c and risk <= tau_r:
       return "Q1"

   # AFTER
   if validity >= tau_c and risk <= tau_r:
       return "Q1"
   ```

5. **Add Clarification to Decision Matrix**:
   ```markdown
   ## Q1: High Validity, Low Risk
   - Output is structurally valid (compiles, parses, etc.)
   - Quality is above threshold (meets requirements)
   - Safe to deploy SLM

   ## Q4: Low Validity OR High Risk
   - Either output is invalid OR quality is poor
   - Not safe, escalate to LLM
   ```

**Affected Files**:
- `src/routing/framework.py` (compute_validity_curve)
- `src/routing/production_router.py` (all references to capability)
- `docs/reference/RISK_CURVES.md`
- `docs/reference/QUALITY_METRICS.md`
- `docs/guides/COMPLETE_PIPELINE.md`

**Effort**: 2-3 hours (rename + update docs)
**Testing**: Check that zone assignments still work correctly

---

### FIX 2.2: Implement Zone Q2 Policy Properly

**Issue**: Zone Q2 returns string "SLM_with_verification" instead of actual model name

**Current Code**:
```python
elif zone == "Q2":
    return "SLM_with_verification"
```

**Problem**:
- Not a real model identifier
- Verification function is optional (None is possible)
- No escalation logic in _apply_zone_policy

**Solution**: Move zone policy application AFTER verification

**New Implementation**:

```python
def route(...):
    """Route a production request"""

    # ... existing code ...

    # Step 15: Classify zone
    zone = self._classify_zone(capability, risk, tau_c, tau_r)

    # Step 16: Apply zone policy AND verification
    if zone == "Q1":
        routed_model = preferred_model
        verification_status = "not_applicable"

    elif zone == "Q2":
        # ZONE 2: SLM + Verification + Escalation
        routed_model = preferred_model

        if not self.verification_fn:
            # Requirement: verification_fn MUST be provided for Q2
            warnings.warn(
                f"Zone Q2 requires verification_fn to be provided. "
                f"Falling back to Q4 (LLM only).",
                UserWarning
            )
            routed_model = "llama"
            verification_status = "verification_fn_missing"
        else:
            # Run verification
            try:
                confidence = self.verification_fn(
                    task=task,
                    model=preferred_model,
                    input_text=input_text,
                    difficulty=difficulty,
                    bin_id=bin_id,
                    capability=capability,
                    risk=risk
                )

                if confidence >= 0.90:
                    routed_model = preferred_model
                    verification_status = "passed"
                else:
                    routed_model = "llama"  # Escalate
                    verification_status = "failed_escalated"

            except Exception as e:
                # Verification error → escalate to LLM
                routed_model = "llama"
                verification_status = f"error:{type(e).__name__}"

    elif zone == "Q3":
        # ZONE 3: Hybrid
        if tau_cap is not None and bin_id <= tau_cap:
            routed_model = preferred_model
        else:
            routed_model = "llama"
        verification_status = "not_applicable"

    else:  # zone == "Q4"
        routed_model = "llama"
        verification_status = "not_applicable"

    # ... rest of code ...
```

**OR Simpler: Use Required Verification**

```python
class ProductionRouter:
    def __init__(self, verification_fn: Callable[..., float], ...):
        """
        Initialize router

        Args:
            verification_fn: REQUIRED for Q2 zones.
                Should return confidence score [0, 1]
        """
        if verification_fn is None:
            raise ValueError("verification_fn is required to handle Q2 zones")
        self.verification_fn = verification_fn
```

**Validation Tests to Add**:
```python
def test_zone_q2_with_verification():
    def verify_fn(...):
        return 0.95  # high confidence

    router = ProductionRouter(verification_fn=verify_fn)
    model, decision = router.route(...)

    if decision.zone == "Q2":
        assert model in ["qwen", "llama"]  # Not "SLM_with_verification"
        assert decision.verification_status in ["passed", "failed_escalated", "error:..."]

def test_zone_q2_without_verification_raises():
    try:
        router = ProductionRouter(verification_fn=None)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "verification_fn is required" in str(e)
```

**Affected Files**:
- `src/routing/production_router.py` (route method + __init__)
- `tests/test_zone_q2.py` (new tests)

**Effort**: 3-4 hours
**Testing**: Add 5-10 new unit tests

---

### FIX 3.1: Separate Validity and Quality Metrics

**Issue**: Capability computation uses validation_fn; risk uses quality_metric. Different concepts.

**Current**:
```python
# Capability: Is output valid?
def validate_code(output):
    compile(output, '<string>', 'exec')  # raises if invalid

# Risk: Does output meet quality bar?
def compute_quality(sample):
    return sample['tests_passed'] / sample['total_tests']
```

**Problem**: A sample can be valid but low quality (or invalid but irrelevant for quality computation)

**Solution**: Explicitly define both for each task

**New Implementation Pattern**:

```python
@dataclass
class TaskMetrics:
    """Metrics for a specific task"""
    # VALIDITY: Is output structurally sound?
    validity_fn: Callable[[str], bool]  # output → bool

    # QUALITY: How good is the output?
    quality_fn: Callable[[Dict], float]  # sample → [0, 1]
    quality_threshold: float = 0.80

# Example: Code Generation
code_gen_metrics = TaskMetrics(
    # A code snippet is valid if it compiles
    validity_fn=lambda output: is_valid_python(output),

    # Quality is measured by test pass rate
    quality_fn=lambda sample: sample['tests_passed'] / sample['total_tests'],

    quality_threshold=1.0  # All tests must pass
)

# Example: Text Generation
text_gen_metrics = TaskMetrics(
    # Valid if we got some output
    validity_fn=lambda output: len(output.strip()) > 0,

    # Quality is constraint satisfaction
    quality_fn=lambda sample: sample['metrics']['constraint_satisfaction_rate'],

    quality_threshold=0.80  # 80% constraints must be satisfied
)
```

**Usage in Framework**:
```python
def analyze_task(self, task_metrics: TaskMetrics, outputs_by_model):
    """Analyze task with explicit validity and quality metrics"""

    for model_name, outputs in outputs_by_model.items():
        # Bin by difficulty
        binned = self.bin_by_difficulty(...)

        # Compute validity (structural soundness)
        validity_curve, counts = self.compute_validity_curve(
            binned,
            task_metrics.validity_fn
        )

        # Compute quality-based risk
        risk_curve, counts = self.compute_risk_curve(
            binned,
            task_metrics.quality_fn,
            task_metrics.quality_threshold
        )

        # Detect tipping points
        tau_cap, tau_risk = self.detect_tipping_points(
            validity_curve, risk_curve, ...
        )

        # Classify zone
        zone = self.classify_zone(...)
```

**Create TaskMetrics for All Tasks**:

```python
TASK_METRICS = {
    'code_generation': TaskMetrics(
        validity_fn=is_valid_python,
        quality_fn=lambda s: s['tests_passed'] / s['total_tests'],
        quality_threshold=1.0
    ),
    'classification': TaskMetrics(
        validity_fn=lambda o: len(o.strip()) > 0,
        quality_fn=lambda s: float(s['prediction'] == s['reference']),
        quality_threshold=1.0
    ),
    'summarization': TaskMetrics(
        validity_fn=lambda o: len(o.strip()) > 10,
        quality_fn=lambda s: s['rouge_1_f1'],
        quality_threshold=0.80
    ),
    # ... etc
}
```

**Affected Files**:
- `src/routing/framework.py` (add TaskMetrics dataclass)
- `src/routing/task_metrics.py` (new file with all task definitions)
- `src/routing/production_router.py` (use TaskMetrics)

**Effort**: 4-5 hours
**Testing**: Verify validity and risk curves independently

---

## PRIORITY TIER 2: HIGH (Fix Soon)

### FIX 1.2: Improve τ_risk Detection

**Issue**: Uses CI lower bounds instead of raw values; skips undersampled bins

**Current Code**:
```python
lower, _ = wilson_interval(risk, n, z)
if lower is not None and lower >= self.risk_threshold:
    tau_risk = d
    break
```

**Problems**:
1. Small samples (n < 5) → very wide CI → might miss true tau_risk
2. CI lower bound vs. raw value: different interpretation
3. >= vs >: off-by-one for boundary cases

**Solution Option A: Use Raw Values (Simpler)**

```python
def detect_tipping_points(self, ...):
    """Detect two tipping points using raw values"""

    # τ_cap: last bin where raw capability >= threshold
    tau_cap = None
    for d in range(num_bins):
        cap = capability_curve.get(d, 0.0)
        if cap >= self.capability_threshold:
            tau_cap = d

    # τ_risk: first bin where raw risk > threshold
    tau_risk = None
    for d in range(num_bins):
        risk = risk_curve.get(d, 0.0)
        if risk > self.risk_threshold:  # Strict >
            tau_risk = d
            break  # First one only

    return tau_cap, tau_risk
```

**Solution Option B: Use CI with Better Logic (Recommended)**

```python
def detect_tipping_points(self, ..., min_samples: int = 10, alpha: float = 0.05):
    """
    Detect tipping points with confidence interval gating

    Args:
        min_samples: Minimum samples required for a bin to be considered
        alpha: Significance level for confidence intervals
    """
    z = 1.96 if alpha == 0.05 else 1.64

    # For τ_cap: last bin where LOWER CI of validity >= threshold
    tau_cap = None
    for d in range(num_bins):
        validity = validity_curve.get(d, 0.0)
        n = (validity_counts or {}).get(d, 0)

        if n < min_samples:
            # Warn about undersampling but continue
            # (don't skip, in case this is the last bin)
            continue

        lower, _ = wilson_interval(validity, n, z)

        # Use LOWER CI as conservative estimate
        if lower is not None and lower >= self.capability_threshold:
            tau_cap = d
        else:
            # Stop updating once we drop below threshold
            break

    # For τ_risk: first bin where UPPER CI of risk > threshold
    tau_risk = None
    for d in range(num_bins):
        risk = risk_curve.get(d, 0.0)
        n = (risk_counts or {}).get(d, 0)

        if n < min_samples:
            continue

        _, upper = wilson_interval(risk, n, z)

        # Use UPPER CI as conservative estimate (more risky)
        if upper is not None and upper > self.risk_threshold:
            tau_risk = d
            break  # First one only

    return tau_cap, tau_risk
```

**Add Logging**:
```python
def detect_tipping_points(self, ...):
    # ... computation ...

    # Log warnings about undersampling
    under_min = [d for d, count in validity_counts.items()
                 if count < min_samples]
    if under_min:
        warnings.warn(
            f"Bins {under_min} have < {min_samples} samples. "
            f"Tipping points may be unreliable.",
            UserWarning
        )

    return tau_cap, tau_risk
```

**Add Tests**:
```python
def test_tau_risk_first_bin():
    """Verify τ_risk is detected at first bin > threshold"""
    framework = GeneralizedRoutingFramework(risk_threshold=0.20)

    risk_curve = {0: 0.20, 1: 0.25, 2: 0.30}
    risk_counts = {0: 100, 1: 100, 2: 100}

    tau_cap, tau_risk = framework.detect_tipping_points(
        {}, risk_curve, risk_counts=risk_counts
    )

    assert tau_risk == 1  # First bin where risk > 0.20

def test_tau_risk_with_undersampling():
    """Warn when bins have too few samples"""
    framework = GeneralizedRoutingFramework(risk_threshold=0.20)

    risk_curve = {0: 0.25, 1: 0.25, 2: 0.25}
    risk_counts = {0: 2, 1: 100, 2: 100}  # Bin 0 undersampled

    with warnings.catch_warnings(record=True) as w:
        tau_cap, tau_risk = framework.detect_tipping_points(
            {}, risk_curve, risk_counts=risk_counts, min_samples=5
        )

        assert len(w) == 1
        assert "undersampl" in str(w[0].message).lower()
```

**Affected Files**:
- `src/routing/framework.py` (detect_tipping_points method)
- `tests/test_tipping_points.py` (new tests)

**Effort**: 2-3 hours
**Testing**: Add boundary case tests

---

### FIX 5.1: Data-Driven Empirical Thresholds

**Issue**: τ_C = 0.80 and τ_R = 0.20 hardcoded for all tasks

**Current Code**:
```python
empirical_tau_c: float = 0.80
empirical_tau_r: float = 0.20
```

**Problem**: Ignores actual data distribution. Some tasks might naturally cluster differently.

**Solution: Implement Step 8 from Documentation**

**File**: `src/routing/threshold_detection.py` (new)

```python
import numpy as np
from scipy import stats
from collections import defaultdict
from typing import Dict, Tuple

def compute_empirical_thresholds(
    capability_curves: Dict[str, Dict[int, float]],
    risk_curves: Dict[str, Dict[int, float]],
    method: str = "percentile"
) -> Tuple[float, float]:
    """
    Detect empirical thresholds from distribution of capability and risk values

    Args:
        capability_curves: {model: {bin: capability}}
        risk_curves: {model: {bin: risk}}
        method: "percentile", "natural_gap", or "kmeans"

    Returns:
        (empirical_tau_c, empirical_tau_r)
    """

    # Collect all values
    all_capabilities = []
    all_risks = []

    for model, curve in capability_curves.items():
        all_capabilities.extend(curve.values())

    for model, curve in risk_curves.items():
        all_risks.extend(curve.values())

    if method == "percentile":
        # Find natural cluster points
        # Capability: values cluster around 0.80-0.90 (good models) and 0.50-0.70 (weak)
        # Look for where good models end
        empirical_tau_c = np.percentile(all_capabilities, 80)

        # Risk: values cluster around 0.05-0.20 (safe) and 0.30+ (risky)
        # Look for where risky starts
        empirical_tau_r = np.percentile(all_risks, 20)

    elif method == "natural_gap":
        # Find largest gaps in distribution
        caps_sorted = np.sort(all_capabilities)
        gaps = np.diff(caps_sorted)
        gap_idx = np.argmax(gaps)
        empirical_tau_c = (caps_sorted[gap_idx] + caps_sorted[gap_idx + 1]) / 2

        risks_sorted = np.sort(all_risks)
        gaps = np.diff(risks_sorted)
        gap_idx = np.argmax(gaps)
        empirical_tau_r = (risks_sorted[gap_idx] + risks_sorted[gap_idx + 1]) / 2

    elif method == "kmeans":
        # Cluster values, use cluster centers as thresholds
        from sklearn.cluster import KMeans

        # Capability: 2 clusters (good vs weak models)
        km_cap = KMeans(n_clusters=2)
        cap_labels = km_cap.fit_predict(np.array(all_capabilities).reshape(-1, 1))
        empirical_tau_c = np.sort(km_cap.cluster_centers_.flatten())[0]

        # Risk: 2 clusters (safe vs risky)
        km_risk = KMeans(n_clusters=2)
        risk_labels = km_risk.fit_predict(np.array(all_risks).reshape(-1, 1))
        empirical_tau_r = np.sort(km_risk.cluster_centers_.flatten())[0]

    else:
        raise ValueError(f"Unknown method: {method}")

    return float(empirical_tau_c), float(empirical_tau_r)


def analyze_threshold_sensitivity(
    capability_curves: Dict,
    risk_curves: Dict,
    tau_c_range: Tuple[float, float] = (0.70, 0.95),
    tau_r_range: Tuple[float, float] = (0.10, 0.30)
) -> Dict:
    """
    Analyze how zone assignments change with different thresholds

    Returns statistics on robustness
    """
    results = defaultdict(list)

    tau_c_values = np.linspace(tau_c_range[0], tau_c_range[1], 10)
    tau_r_values = np.linspace(tau_r_range[0], tau_r_range[1], 10)

    for tau_c in tau_c_values:
        for tau_r in tau_r_values:
            zone_counts = defaultdict(int)

            for model, cap_curve in capability_curves.items():
                risk_curve = risk_curves.get(model, {})

                for bin_id in cap_curve:
                    cap = cap_curve[bin_id]
                    risk = risk_curve.get(bin_id, 0.5)

                    if cap >= tau_c and risk <= tau_r:
                        zone = "Q1"
                    elif cap >= tau_c and risk > tau_r:
                        zone = "Q2"
                    elif cap < tau_c and risk <= tau_r:
                        zone = "Q3"
                    else:
                        zone = "Q4"

                    zone_counts[zone] += 1

            results[(tau_c, tau_r)] = dict(zone_counts)

    return results
```

**Usage in Analysis**:

```python
# Phase 0: Compute empirical thresholds
def run_analysis(...):
    # Compute curves
    capability_curves = {}  # {model: {bin: capability}}
    risk_curves = {}  # {model: {bin: risk}}

    # Detect empirical thresholds from data
    tau_c, tau_r = compute_empirical_thresholds(
        capability_curves,
        risk_curves,
        method="natural_gap"  # or "percentile", "kmeans"
    )

    print(f"Detected empirical thresholds:")
    print(f"  τ_C = {tau_c:.3f} (capability threshold)")
    print(f"  τ_R = {tau_r:.3f} (risk threshold)")

    # Use detected thresholds
    for model, cap_curve in capability_curves.items():
        zone = classify_zone(tau_c, tau_r, ...)
```

**Add to Documentation**:

```markdown
## Step 8: Compute Empirical Thresholds

Instead of hardcoding τ_C=0.80 and τ_R=0.20, analyze your data:

### Method 1: Percentile-Based (Recommended)
τ_C = 80th percentile of all capability values
τ_R = 20th percentile of all risk values

This finds the dividing line between capable/incapable and safe/risky models.

### Method 2: Natural Gap
Find largest discontinuity in the distribution.

### Method 3: K-Means Clustering
Separate models into "good" and "weak" clusters.

### Sensitivity Analysis
Before deploying, check how zone assignments change if thresholds vary by ±10%.
```

**Affected Files**:
- `src/routing/threshold_detection.py` (new)
- `src/routing/analysis.py` (call compute_empirical_thresholds)
- `tests/test_thresholds.py` (new)
- Documentation

**Effort**: 4-5 hours
**Testing**: Verify thresholds on historical data

---

## PRIORITY TIER 3: MEDIUM (Fix When Possible)

### FIX 2.3: Consistent Monitoring Alert Thresholds

**Issue**: Uses alert_delta_tau for tipping points but alert_delta_risk for bin-wise risks

**Current**:
```python
# Tipping point alerts
if new_tau_cap < old_tau_cap - self.alert_delta_tau:
    alerts.append(...)

# Bin-wise risk alerts
if (avg_risk - base_risk) > self.alert_delta_risk:
    alerts.append(...)
```

**Problem**: Different metrics, different deltas, hard to coordinate

**Solution: Unified Alert System**

```python
@dataclass
class AlertThresholds:
    """Threshold for triggering monitoring alerts"""
    tau_cap_shift: int = 1        # Bins
    tau_risk_shift: int = 1       # Bins
    risk_increase: float = 0.10   # Absolute increase
    risk_increase_pct: float = 0.20  # Percent increase
    min_samples: int = 5          # Min samples to trigger alert

class ProductionRouter:
    def __init__(self, alert_thresholds: AlertThresholds = None):
        self.alert_thresholds = alert_thresholds or AlertThresholds()

    def daily_monitoring_check(self) -> List[str]:
        """Daily monitoring with consistent alert logic"""
        alerts = []

        for (task, model), analysis in self.analyses.items():
            # Recompute tipping points
            new_tau_cap, new_tau_risk = self._compute_tipping_points_from_logs(
                task, model
            )
            old_tau_cap = analysis.tau_cap
            old_tau_risk = analysis.tau_risk

            # Alert 1: Capability degradation
            if new_tau_cap is not None and old_tau_cap is not None:
                if old_tau_cap - new_tau_cap >= self.alert_thresholds.tau_cap_shift:
                    alerts.append(
                        f"🚨 {task}/{model} capability degraded: "
                        f"τ_cap {old_tau_cap} → {new_tau_cap}"
                    )

            # Alert 2: Risk escalation (tipping point)
            if new_tau_risk is not None and old_tau_risk is not None:
                if new_tau_risk - old_tau_risk >= self.alert_thresholds.tau_risk_shift:
                    alerts.append(
                        f"🚨 {task}/{model} risk escalated: "
                        f"τ_risk {old_tau_risk} → {new_tau_risk}"
                    )
            elif new_tau_risk is not None and old_tau_risk is None:
                # First time crossing threshold
                alerts.append(
                    f"⚠️  {task}/{model} risk crossed threshold: "
                    f"τ_risk newly detected at bin {new_tau_risk}"
                )

            # Alert 3: Bin-wise risk increase
            for bin_id in range(analysis.num_bins):
                base_risk = analysis.risk_curve.get(bin_id)
                new_risk = self._avg_risk_for_bin(task, model, bin_id)
                count = self._sample_count_for_bin(task, model, bin_id)

                if count < self.alert_thresholds.min_samples:
                    continue

                if base_risk is not None and new_risk is not None:
                    abs_increase = new_risk - base_risk
                    pct_increase = abs_increase / base_risk if base_risk > 0 else 0

                    if abs_increase > self.alert_thresholds.risk_increase:
                        alerts.append(
                            f"⚠️  {task}/{model}/bin{bin_id} risk increased: "
                            f"{base_risk:.3f} → {new_risk:.3f} (+{abs_increase:.3f})"
                        )

                    if pct_increase > self.alert_thresholds.risk_increase_pct:
                        alerts.append(
                            f"⚠️  {task}/{model}/bin{bin_id} risk increased: "
                            f"+{pct_increase:.1%}"
                        )

        return alerts
```

**Affected Files**:
- `src/routing/production_router.py` (daily_monitoring_check)
- `src/routing/monitoring.py` (new, AlertThresholds)

**Effort**: 2-3 hours
**Testing**: Unit tests for alert generation

---

### FIX 3.2: Document Soft Bin Interpolation

**Issue**: Documentation says deterministic binning; code uses interpolation in production

**Solution: Update Documentation**

```markdown
## Bin Assignment in Production (Phase 1)

### Theory (Simple)
```python
bin = int(difficulty * 4)
```

### Production (Actual - Soft Binning with Interpolation)

For smoother transitions, production uses interpolated curves:

```python
bin_position = difficulty * (num_bins - 1)
lower_bin = int(bin_position)
upper_bin = lower_bin + 1
fraction = bin_position - lower_bin

# Interpolate between adjacent bins
capability = (1 - fraction) * curve[lower_bin] + fraction * curve[upper_bin]
```

**Why?** Hard bin boundaries create discontinuities. If a sample with difficulty=0.249 is just barely in bin 1, using exactly bin 1's capability value is too coarse. Interpolation smooths the transition.

**Example**:
```
difficulty = 0.249 (just below bin boundary at 0.25)
bin_position = 0.249 * 4 = 0.996

lower_bin = 0, upper_bin = 1, fraction = 0.996
capability = 0.004 * cap[0] + 0.996 * cap[1]

Result: Mostly bin 1's capability, tiny bit of bin 0
→ Smooth transition near boundaries
```

### When Binning Happens

| Phase | Binning | Deterministic | Purpose |
|-------|---------|--------------|---------|
| **Phase 0: Analysis** | Hard bins (argmax) | ✓ YES | Group samples for statistics |
| **Phase 1: Production** | Soft bins (interpolate) | ✗ NO | Smooth routing decisions |

Both approaches are correct; they optimize for different goals.
```

**Affected Files**:
- `docs/guides/COMPLETE_PIPELINE.md` (update Step 13)
- `docs/reference/` (new subsection on bin interpolation)

**Effort**: 1 hour

---

### FIX 4.1: Complete Phase 2 Monitoring

**Issue**: Phase 2 monitoring is minimal vs. documented design

**Current Implementation**:
- ✓ τ_cap detection
- ✓ τ_risk detection
- ✓ Bin-wise risk increases
- ✗ Failure taxonomy analysis
- ✗ Severity-weighted degradation
- ✗ Continuous (real-time) monitoring

**Enhancement Path**:

**Step 1**: Add failure taxonomy tracking

```python
class FailureAnalyzer:
    """Analyze failure patterns in monitoring logs"""

    def __init__(self):
        self.failures_by_type = defaultdict(int)
        self.severity_weights = {
            "syntax_error": 1.0,
            "timeout": 1.0,
            "logic_error": 0.8,
            "wrong_output": 0.6,
            "incomplete": 0.4,
        }

    def analyze_degradation(self, yesterday_logs, baseline_analysis):
        """Compare failure patterns to baseline"""

        # Count failure types
        new_failures = defaultdict(int)
        new_severity = 0.0

        for log in yesterday_logs:
            # Extract failure type from log
            failure_type = log.get('failure_type')
            new_failures[failure_type] += 1
            new_severity += self.severity_weights.get(failure_type, 0.0)

        # Compare to baseline
        baseline_severity = baseline_analysis.get('avg_severity', 0.0)

        if new_severity > baseline_severity * 1.1:  # 10% increase
            return f"Severity-weighted degradation: {baseline_severity:.2f} → {new_severity:.2f}"

        return None
```

**Step 2**: Enable real-time monitoring (if needed)

```python
def streaming_monitoring_check(self, result: RoutingDecisionRecord):
    """Check for degradation in real-time (per-request)"""
    alerts = []

    # Get baseline for this bin
    analysis = self.get_analysis(result.task, result.routed_model)

    if analysis is None:
        return []

    baseline_risk = analysis.risk_curve.get(result.bin_id, 0.5)
    baseline_cap = analysis.capability_curve.get(result.bin_id, 0.5)

    # Check if this single result is anomalous
    if result.capability < baseline_cap * 0.8:  # 20% drop
        alerts.append(
            f"⚠️  {result.task}/{result.routed_model}/bin{result.bin_id} "
            f"capability lower than expected"
        )

    if result.risk > baseline_risk * 1.2:  # 20% increase
        alerts.append(
            f"⚠️  {result.task}/{result.routed_model}/bin{result.bin_id} "
            f"risk higher than expected"
        )

    return alerts
```

**Affected Files**:
- `src/routing/monitoring.py` (new, FailureAnalyzer, streaming checks)
- `src/routing/production_router.py` (integrate streaming monitoring)

**Effort**: 5-6 hours
**Priority**: Lower (nice-to-have, not critical)

---

## Summary Table: Implementation Priority

| Fix | ID | Title | Effort | Risk | Impact |
|-----|--|-|--:|--:|--|
| 🔴 CRITICAL 1 | 1.1 | Clarify Capability vs Risk | 2-3h | MEDIUM | High |
| 🔴 CRITICAL 2 | 2.2 | Zone Q2 Implementation | 3-4h | HIGH | Critical |
| 🔴 CRITICAL 3 | 3.1 | Separate Validity/Quality | 4-5h | HIGH | Critical |
| 🟠 HIGH 1 | 1.2 | τ_risk Detection | 2-3h | MEDIUM | High |
| 🟠 HIGH 2 | 5.1 | Data-Driven Thresholds | 4-5h | LOW | High |
| 🟡 MEDIUM 1 | 2.3 | Monitoring Alerts | 2-3h | LOW | Medium |
| 🟡 MEDIUM 2 | 3.2 | Bin Documentation | 1h | LOW | Low |
| 🟡 MEDIUM 3 | 4.1 | Complete Monitoring | 5-6h | LOW | Medium |

**Total Effort**: ~25-30 hours
**Recommended Timeline**: 2-3 weeks (part-time)

---

## Testing Strategy

For each fix, add tests:

```bash
# Unit tests
pytest tests/test_fixes/test_capability_vs_risk.py -v
pytest tests/test_fixes/test_zone_q2.py -v
pytest tests/test_fixes/test_validity_quality.py -v
pytest tests/test_fixes/test_tipping_points.py -v
pytest tests/test_fixes/test_thresholds.py -v

# Integration tests
pytest tests/test_complete_pipeline_after_fixes.py -v

# Regression tests
pytest tests/ -v  # All existing tests should still pass
```

---

**End of Action Items Document**
