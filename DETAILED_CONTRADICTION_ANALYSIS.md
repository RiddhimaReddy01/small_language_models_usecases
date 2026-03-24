# DETAILED CONTRADICTION ANALYSIS: Code Excerpts & Explanations
## Supplementary Document to RESEARCH_REPORT_THEORY_VS_CODE.md

---

## DEEP DIVE 1: Capability vs Risk Independence

### The Core Problem

**File**: `docs/reference/RISK_CURVES.md`, Line 8
```
Capability_m(b) = C_m(b) = 1 - Risk_m(b)
```

This statement claims a **mathematical relationship**: Capability and Risk always sum to 1.0.

But the actual code implementation breaks this assumption.

### Capability Computation

**File**: `src/routing/framework.py`, Lines 191-219

```python
def compute_capability_curve(self, samples_by_bin: Dict[int, List],
                            validation_fn: Callable) -> Dict[int, float]:
    """
    Compute P̂_m(d) = accuracy per bin

    Returns:
        ({bin_id: accuracy_0_to_1}, {bin_id: sample_count})
    """
    capabilities = {}
    counts = {}

    for bin_id in sorted(samples_by_bin.keys()):
        samples = samples_by_bin[bin_id]

        valid_count = 0
        for sample in samples:
            output = sample.get('raw_output', '')
            try:
                if validation_fn(output):  # ← Binary: True/False
                    valid_count += 1
            except:
                pass

        accuracy = valid_count / len(samples) if samples else 0
        capabilities[bin_id] = accuracy
        counts[bin_id] = len(samples)

    return capabilities, counts
```

**Key point**: Uses `validation_fn(output)` which returns **binary True/False**

**Example**: Code compilation check
```python
def validate_code(output):
    try:
        compile(output, '<string>', 'exec')
        return True  # Code is syntactically valid
    except:
        return False  # Code has syntax errors
```

### Risk Computation

**File**: `src/routing/framework.py`, Lines 221-275

```python
def compute_risk_curve(self, samples_by_bin: Dict[int, List],
                      quality_metric: Optional[Callable] = None,
                      quality_threshold: float = 0.80) -> Dict[int, float]:
    """
    Compute Risk_m(d) = quality failure rate per bin

    NEW APPROACH (recommended): Use continuous quality metrics
    - Risk = fraction of samples where quality_score < quality_threshold

    OLD APPROACH (fallback): Severity-weighted binary failures

    Returns:
        ({bin_id: risk_0_to_1}, {bin_id: sample_count})
    """
    risks = {}
    counts = {}

    for bin_id in sorted(samples_by_bin.keys()):
        samples = samples_by_bin[bin_id]

        # NEW APPROACH: Continuous quality degradation
        if quality_metric is not None:
            failure_count = 0
            for sample in samples:
                try:
                    quality_score = quality_metric(sample)  # ← Float: 0.0 to 1.0
                    if quality_score < quality_threshold:
                        failure_count += 1
                except:
                    failure_count += 1

            risk = failure_count / len(samples) if samples else 0

        # OLD APPROACH: Severity-weighted binary failures (fallback)
        else:
            total_weight = 0
            for sample in samples:
                is_valid = sample.get('valid', False)

                if not is_valid:
                    severity = sample.get('severity', None)
                    weight = self.SEVERITY_WEIGHTS.get(severity, 0)
                    total_weight += weight

            risk = total_weight / len(samples) if samples else 0

        risks[bin_id] = risk
        counts[bin_id] = len(samples)

    return risks, counts
```

**Key point**: Uses `quality_metric(sample)` which returns **continuous float [0,1]**

**Example**: Test pass rate
```python
def compute_quality(sample):
    # Returns: (tests_passed / total_tests)
    # 0.0 = no tests pass
    # 1.0 = all tests pass
    return sample['tests_passed'] / sample['total_tests']
```

### Why They're Different

**Capability checks**: "Is the output structurally valid?"
- Code compiles? ✓
- JSON parses? ✓
- No crashes? ✓

**Risk checks**: "Does the output meet quality standards?"
- Tests pass? (quality ≥ 1.0)
- ROUGE score > 0.80? (quality ≥ 0.80)
- Constraints satisfied? (quality ≥ 0.80)

### Concrete Example: Same Sample Counted Differently

**Sample**: Generated Python code that compiles but fails tests

```python
sample = {
    'raw_input': 'Write a function that reverses a list',
    'raw_output': '''def reverse(lst):
        return lst  # BUG: doesn't actually reverse
    ''',
    'passed': False,  # Test: failed
    'total_tests': 5,
    'tests_passed': 0,
}
```

**Capability computation**:
```python
# Step 1: Try to compile
compile(sample['raw_output'], '<string>', 'exec')
# Success! Code is syntactically valid

# Step 2: Count as valid
valid_count += 1
# Result: Capability += 1 (counted as SUCCESS)
```

**Risk computation**:
```python
# Step 1: Compute quality score
quality = sample['tests_passed'] / sample['total_tests']
# = 0 / 5 = 0.0

# Step 2: Compare to threshold
if quality < 1.0:  # 0.0 < 1.0? YES
    failure_count += 1
# Result: Risk += 1 (counted as FAILURE)
```

**For the same sample**:
- Capability = +1 (valid)
- Risk = +1 (failure)

If we have 10 samples in a bin:
- 8 compile successfully (valid code)
- 3 pass tests (quality ≥ 1.0)

**Computed curves**:
- Capability = 8/10 = 0.80
- Risk = (10-3)/10 = 0.70

**Check**: Capability + Risk = 0.80 + 0.70 = 1.50 ≠ 1.0 ❌

### Why Documentation Says They're Complementary

Looking at RISK_CURVES.md more closely:

```markdown
# Risk Curves: Visual Guide

## Mathematical Foundation

Risk_m(b) = P̂_m(fail|b) = # failures in bin b / # samples in bin b

Capability_m(b) = C_m(b) = 1 - Risk_m(b)
```

This suggests:
- Risk = P(failure)
- Capability = 1 - P(failure) = P(success)

**But in code**:
- Risk = P(quality < threshold)
- Capability = P(valid)

These are NOT complements unless "failure" means both "invalid" AND "low quality".

### Specific Task Examples Where They Diverge

#### Text Generation

**Capability**: Output text produced (not empty, etc.)
```python
def validate_text(output):
    return len(output.strip()) > 10
```

**Quality**: Constraint satisfaction
```python
def compute_quality(sample):
    metrics = sample.get('metrics', {})
    return metrics.get('constraint_satisfaction_rate', 0.0)
    # Range: 0.0 (no constraints met) to 1.0 (all met)
```

**Scenario**: Model produces long text (valid) with only 50% constraints satisfied
- Capability: SUCCESS (text produced)
- Risk: FAILURE (0.50 < 0.80)

#### Summarization

**Capability**: Summary produced
```python
def validate_summary(output):
    return len(output.strip()) > 20
```

**Quality**: ROUGE F1 score
```python
def compute_quality(sample):
    return sample.get('rouge_1_f1', 0.0)
    # Range: 0.0 to 1.0 (perfect match)
```

**Scenario**: Model produces valid summary (long enough) with ROUGE=0.75
- Capability: SUCCESS (summary produced)
- Risk: FAILURE (0.75 < 0.80)

### Impact on Zone Classification

When zones are classified (framework.py:387-408):

```python
def classify_quadrant(self, tau_cap, tau_risk, capability_gap, avg_risk):
    if tau_cap is not None and tau_cap < 4:
        if tau_risk is not None and tau_risk <= tau_cap:
            return "Q4"  # Low Cap, Risky
        else:
            return "Q3"  # Low Cap, Safe
    else:
        if tau_risk is not None and tau_risk < 4:
            return "Q2"  # High Cap, Risky
        else:
            return "Q1"  # High Cap, Safe
```

The classifier uses BOTH τ_cap and τ_risk independently. Since they measure different things, a task could fall into unexpected zones.

---

## DEEP DIVE 2: τ_risk Detection with Statistical Confidence Intervals

### The Documented Approach

**File**: `docs/guides/COMPLETE_PIPELINE.md`, Lines 229

```
τ_risk = min{b : Risk_m(b) > 0.20}
    (first bin where risk > 20%)
```

Simple: Scan from bin 0 to 4, return the first bin where Risk > 0.20.

### The Implemented Approach

**File**: `src/routing/framework.py`, Lines 337-385

```python
def detect_tipping_points(self, capability_curve: Dict[int, float],
                         risk_curve: Dict[int, float],
                         num_bins: int = 5,
                         capability_counts: Optional[Dict[int, int]] = None,
                         risk_counts: Optional[Dict[int, int]] = None,
                         min_samples: int = 5,
                         alpha: float = 0.05) -> Tuple[Optional[int], Optional[int]]:
    """
    Detect two tipping points

    τ_cap = max{d : P̂_m(d) ≥ threshold}
    τ_risk = min{d : Risk_m(d) > threshold}

    Returns:
        (tau_cap, tau_risk)
    """
    z = 1.96 if alpha == 0.05 else 1.64

    expected_capabilities = {}
    expected_risks = {}
    for d in range(num_bins):
        difficulty_mid = d / max(1, (num_bins - 1))
        expected_capabilities[d] = self.compute_expected_capability(
            difficulty_mid, capability_curve, num_bins
        )
        expected_risks[d] = self.compute_expected_risk(
            difficulty_mid, risk_curve, num_bins
        )

    # Capability tipping point: last bin where lower CI >= threshold
    tau_cap = None
    for d in range(num_bins):
        cap = expected_capabilities.get(d, 0.0)
        n = (capability_counts or {}).get(d, 0)
        if n < min_samples:  # ← Min sample gating
            continue
        lower, _ = wilson_interval(cap, n, z)  # ← Use Wilson CI
        if lower is not None and lower >= self.capability_threshold:
            tau_cap = d

    # Risk tipping point: first bin where lower CI >= threshold
    tau_risk = None
    for d in range(num_bins):
        risk = expected_risks.get(d, 0.0)
        n = (risk_counts or {}).get(d, 0)
        if n < min_samples:  # ← Min sample gating
            continue
        lower, _ = wilson_interval(risk, n, z)  # ← Use Wilson CI
        if lower is not None and lower >= self.risk_threshold:  # ← >= not >
            tau_risk = d
            break

    return tau_cap, tau_risk
```

**Key differences**:
1. Uses **Wilson confidence intervals** instead of raw values
2. Requires **min_samples=5** per bin (skips undersampled bins)
3. Uses `>= threshold` instead of `> threshold`
4. Breaks immediately (first bin found)

### The Wilson Confidence Interval

**File**: `src/utils/stats.py` (hypothetical, but referenced)

```python
def wilson_interval(success_rate, n, z=1.96):
    """
    Compute Wilson score interval for binomial proportion

    Returns: (lower_ci, upper_ci)

    Handles edge cases like 0% or 100% success rates
    """
    if n == 0:
        return None, None

    p = success_rate
    q = 1 - p

    denominator = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denominator
    margin = z * math.sqrt(p*q/n + z**2/(4*n**2)) / denominator

    lower = center - margin
    upper = center + margin

    return max(0, lower), min(1, upper)
```

### Problem 1: Different Statistical Approaches

For the same risk value 0.21 with varying sample counts:

```
n=5 samples:
  Risk = 0.21 (1/5 fails)
  CI Lower = ~ 0.05 (very wide CI due to small n)
  Is 0.05 >= 0.20? NO
  → τ_risk not at this bin

n=100 samples:
  Risk = 0.21 (21/100 fail)
  CI Lower = ~ 0.19 (narrower CI)
  Is 0.19 >= 0.20? NO (still no)
  → τ_risk not at this bin

n=10000 samples:
  Risk = 0.21 (2100/10000 fail)
  CI Lower = ~ 0.20 (tight CI)
  Is 0.20 >= 0.20? YES
  → τ_risk FOUND at this bin!
```

**Effect**: With few samples, τ_risk detection becomes unreliable. A bin with true risk 0.21 might not be detected as the tipping point until you have many samples.

### Problem 2: Hard Min Sample Requirement

```python
if n < min_samples:
    continue
```

With `min_samples=5`, bins with 0-4 samples are **completely skipped**. Example:

```
Task: Code Generation, Qwen
Bin 0 (easy): 20 samples → analyzed
Bin 1 (medium): 3 samples → SKIPPED
Bin 2 (med-hard): 25 samples → analyzed
...

Result: τ_risk might jump from bin 0 directly to bin 2
        missing the actual bin 1 tipping point
```

### Problem 3: >= vs >

Documentation says:
```
Risk_m(b) > 0.20
```

Code checks:
```python
if lower is not None and lower >= self.risk_threshold:
```

For Risk exactly equal to 0.20:
- Theory: Risk = 0.20 is NOT risky (0.20 is not > 0.20)
- Code: Risk = 0.20 IS risky (0.20 >= 0.20)

This creates a hard boundary at exactly 0.20 that shouldn't exist.

### Real-World Example

```
Scenario: Code Generation, Model Qwen, analyzing from benchmarks

Expected (Theory):
  Bin 0: Risk = 0.20 → NOT RISKY (0.20 is not > 0.20)
  Bin 1: Risk = 0.21 → RISKY (first bin > 0.20)
  τ_risk = 1

Actual (Code):
  Bin 0: Risk = 0.20, n = 10 samples
         CI Lower = 0.17
         Is 0.17 >= 0.20? NO
  Bin 1: Risk = 0.21, n = 20 samples
         CI Lower = 0.18
         Is 0.18 >= 0.20? NO
  Bin 2: Risk = 0.22, n = 100 samples
         CI Lower = 0.20
         Is 0.20 >= 0.20? YES
         τ_risk = 2 (break)

Result: τ_risk = 2 (not 1)
Effect: Zone classification differs from theory
```

---

## DEEP DIVE 3: Missing Zone 2 Implementation

### The Theory

**File**: `docs/guides/COMPLETE_PIPELINE.md`, Lines 426-434

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

**Expected behavior**:
1. Try SLM first
2. Verify the output
3. If verification succeeds (confidence ≥ 0.90), return SLM output
4. If verification fails, escalate to LLM and return LLM output

### The Code

**File**: `src/routing/production_router.py`, Lines 298-325

```python
def _apply_zone_policy(
    self,
    zone: str,
    model: str,
    bin_id: int,
    tau_cap: Optional[int],
    capability: float,
    risk: float
) -> str:
    """Apply zone-specific routing policy"""
    if zone == "Q1":
        return model

    elif zone == "Q2":
        return "SLM_with_verification"  # ← Just returns a string!

    elif zone == "Q3":
        if tau_cap is not None and bin_id <= tau_cap:
            return model
        else:
            return "llama"

    else:  # zone == "Q4"
        return "llama"
```

**Problem**: Zone Q2 just returns `"SLM_with_verification"` string!

The actual verification happens elsewhere:

**File**: `src/routing/production_router.py`, Lines 237-247

```python
# Step 16: Apply zone policy
routed_model = self._apply_zone_policy(...)

verification_status = "not_applicable"
if zone == "Q2" and self.verification_fn:  # ← verification_fn is OPTIONAL
    try:
        verified = bool(self.verification_fn(
            task, preferred_model, input_text, difficulty, bin_id, capability, risk
        ))
    except Exception as exc:
        verified = False
        verification_status = f"error:{exc}"
    else:
        verification_status = "passed" if verified else "failed_escalated"
    if not verified:
        routed_model = "llama"  # ← Override to llama if not verified
```

### The Problem

**Issue 1: Verification Function is Optional**

```python
if zone == "Q2" and self.verification_fn:
```

If `verification_fn` is None:
- Condition is False
- No verification happens
- routed_model stays as "SLM_with_verification"
- But output is generated by... what? The string isn't an actual model!

**Issue 2: Return Value is Misleading**

```python
return routed_model, decision
```

For Zone Q2:
- If verification_fn provided and passes: returns "qwen" (or other SLM)
- If verification_fn provided and fails: returns "llama"
- If verification_fn NOT provided: returns "SLM_with_verification" (not a real model!)

**Issue 3: The Verification Signature is Unclear**

```python
self.verification_fn(
    task, preferred_model, input_text, difficulty, bin_id, capability, risk
)
```

Where does `verification_fn` come from? How is it defined?

**File**: `src/routing/production_router.py`, Line 104

```python
def __init__(self, verification_fn: Optional[Callable[..., bool]] = None,
             alert_delta_tau: int = 1,
             alert_delta_risk: float = 0.1):
    self.verification_fn = verification_fn
```

It's passed in the constructor but no examples show how to define it.

### What Should Happen vs What Does

**Expected** (Theory):
```
Zone 2 detected for input
  ↓
Generate output with SLM
  ↓
Verify output (confidence check)
  ↓
IF confidence ≥ 0.90:
  Return SLM output ("Zone2_SLM")
ELSE:
  Generate output with LLM
  Return LLM output ("Zone2_LLM_escalated")
```

**Actual** (Code):
```
Zone 2 detected for input
  ↓
_apply_zone_policy returns "SLM_with_verification"
  ↓
IF verification_fn is provided:
  Check if verified
  IF verified: routed_model = SLM (e.g., "qwen")
  ELSE: routed_model = "llama"
ELSE:
  routed_model stays "SLM_with_verification"
  ↓
Return routed_model ("SLM_with_verification" or "qwen" or "llama")
```

**The string "SLM_with_verification" is returned but it's not a real model!**

### Example Usage (What It Should Look Like)

```python
def verify_code_output(task, model, input_text, difficulty, bin_id, capability, risk):
    """Verify that generated code meets standards"""
    # Call some verification service/function
    confidence = compute_verification_score(task, output)
    return confidence >= 0.90

router = ProductionRouter(verification_fn=verify_code_output)
model, decision = router.route(input_text="...", task="code_generation", ...)
```

**But what if you don't provide it?**

```python
router = ProductionRouter()  # verification_fn = None
model, decision = router.route(...)
# If Zone 2: model = "SLM_with_verification"
# This isn't a valid model identifier!
```

---

## DEEP DIVE 4: Risk Computation Inconsistency Across Tasks

### The Three Methods

#### Method 1: Quality Threshold Based (Recommended)

**File**: `docs/reference/QUALITY_METRICS.md`, Lines 17-39 (Text Generation example)

```python
def compute_text_generation_risk(outputs_by_bin):
    """
    Risk = fraction of outputs where constraint_satisfaction_rate < 0.80
    """
    risks = {}
    for bin_id, samples in outputs_by_bin.items():
        quality_scores = []

        for sample in samples:
            metrics = sample.get('metrics', {})
            framework = metrics.get('framework', {})
            instruction = framework.get('instruction_following', {})
            csr = instruction.get('constraint_satisfaction_rate', 0.0)
            quality_scores.append(csr)

        failures = sum(1 for q in quality_scores if q < 0.80)
        risk = failures / len(quality_scores) if quality_scores else 0
        risks[bin_id] = risk

    return risks
```

**Used for tasks with continuous quality metrics**:
- Text Generation (constraint_satisfaction_rate)
- Summarization (ROUGE F1)
- Instruction Following (constraint satisfaction ratio)
- Information Extraction (F1 score)

#### Method 2: Binary Failure Rate

**File**: `docs/reference/QUALITY_METRICS.md`, Lines 54-75 (Code Generation example)

```python
def compute_code_generation_risk(outputs_by_bin):
    """
    Risk = fraction of outputs where tests_passed == False
    """
    risks = {}
    for bin_id, samples in outputs_by_bin.items():
        test_passed = []

        for sample in samples:
            passed = sample.get('passed', False)
            test_passed.append(passed)

        failures = sum(1 for p in test_passed if not p)
        risk = failures / len(test_passed) if test_passed else 0
        risks[bin_id] = risk

    return risks
```

**Used for tasks with binary success/failure**:
- Code Generation (tests pass/fail)
- Classification (correct/incorrect prediction)
- Maths (correct/incorrect answer)
- Retrieval (exact match/no match)

#### Method 3: Severity-Weighted Failures (Fallback)

**File**: `src/routing/framework.py`, Lines 259-269

```python
else:
    # OLD APPROACH: Severity-weighted binary failures (fallback)
    total_weight = 0
    for sample in samples:
        is_valid = sample.get('valid', False)

        if not is_valid:
            severity = sample.get('severity', None)
            weight = self.SEVERITY_WEIGHTS.get(severity, 0)
            total_weight += weight

    risk = total_weight / len(samples) if samples else 0
```

**Used when**:
- No quality_metric provided
- Fallback for custom tasks

**Severity weights**:
```python
SEVERITY_WEIGHTS = {
    "critical": 1.0,    # timeout, empty_output, syntax_error
    "high": 0.8,        # execution_error, logic_error, wrong_label
    "medium": 0.5,      # incomplete_output, reasoning_error
    "low": 0.2,         # too_short, too_long, low_relevance
    None: 0.0
}
```

### The Problem: Same Risk Value Means Different Things

**Scenario**: Compare two tasks, both have risk=0.25

**Task A - Text Generation**:
- Risk 0.25 means: "25% of outputs have constraint satisfaction < 0.80"
- This is continuous quality degradation
- Can be partially acceptable (50% constraints met)

**Task B - Code Generation**:
- Risk 0.25 means: "25% of outputs have tests failing"
- This is binary failure
- No gradation (either passes or fails)

**Can you compare them?** No, they measure different things!

### Another Example: Threshold Differences

**Task A - Code Generation**:
- Quality threshold = 1.0 (must pass ALL tests)
- Risk = 1 - (tests_passed / total_tests)
- Risk=0.25 means "25% of samples fail at least one test"

**Task B - Summarization**:
- Quality threshold = 0.80 (ROUGE F1 ≥ 0.80)
- Risk = count where ROUGE F1 < 0.80 / total
- Risk=0.25 means "25% of summaries have ROUGE F1 < 0.80"

**Are these comparable?** Technically yes, but semantically no.
- Code failure is binary and catastrophic
- ROUGE below 0.80 is a continuous degradation

### Real-World Impact

If you're monitoring degradation across tasks:

```python
# All tasks at baseline
baseline = {
    'code_generation': 0.20,    # 20% tests fail
    'summarization': 0.20,      # 20% summaries below threshold
    'classification': 0.20,     # 20% wrong predictions
}

# After model update
current = {
    'code_generation': 0.25,    # ← +0.05 (5% more tests fail)
    'summarization': 0.25,      # ← +0.05 (5% more below threshold)
    'classification': 0.25,     # ← +0.05 (5% more wrong)
}

# Alert threshold
if current[task] - baseline[task] > 0.05:
    alert("Risk degradation detected")

# All three trigger alerts with same magnitude
# But the severity is different!
# - Code: Tests failing is critical
# - Summarization: Slightly worse ROUGE is minor
# - Classification: 5% more errors is significant
```

---

## DEEP DIVE 5: Bin Assignment - Theory vs Code

### Documented Theory

**File**: `docs/guides/COMPLETE_PIPELINE.md`, Lines 150-152

```
For each record:
  bin_id = int(difficulty_score * 4)  # Maps [0,1] to [0-4]
  binned[bin_id].append(record)
```

**Simple deterministic formula**.

Example:
- difficulty=0.00 → bin=0
- difficulty=0.25 → bin=1
- difficulty=0.50 → bin=2
- difficulty=0.75 → bin=3
- difficulty=1.00 → bin=4

### Actual Implementation

**File**: `src/routing/framework.py`, Lines 100-144

```python
def difficulty_to_bin_probabilities(self, difficulty_score, num_bins=5):
    """Convert difficulty score to probabilistic bin assignment"""
    difficulty_score = max(0.0, min(1.0, difficulty_score))
    bin_position = difficulty_score * (num_bins - 1)

    lower_bin = int(bin_position)
    upper_bin = min(lower_bin + 1, num_bins - 1)
    fraction = bin_position - lower_bin

    bin_probs = {}
    for bin_id in range(num_bins):
        if bin_id == lower_bin:
            bin_probs[bin_id] = 1.0 - fraction
        elif bin_id == upper_bin and upper_bin != lower_bin:
            bin_probs[bin_id] = fraction
        else:
            bin_probs[bin_id] = 0.0

    return bin_probs
```

**Example**: difficulty=0.25 with 5 bins
```
bin_position = 0.25 * 4 = 1.0
lower_bin = 1
upper_bin = 1
fraction = 0.0

bin_probs = {0: 0.0, 1: 1.0, 2: 0.0, 3: 0.0, 4: 0.0}
```

Result: Exactly at bin boundary → all probability to bin 1 ✓

**Example**: difficulty=0.249 with 5 bins
```
bin_position = 0.249 * 4 = 0.996
lower_bin = 0
upper_bin = 1
fraction = 0.996

bin_probs = {0: 0.004, 1: 0.996, 2: 0.0, 3: 0.0, 4: 0.0}
```

Result: Near bin boundary → mostly bin 1, tiny bit bin 0

### How This Gets Used

**In Analysis (Phase 0)**:

**File**: `src/routing/framework.py`, Lines 145-189

```python
def bin_by_difficulty(self, samples, difficulty_metric, num_bins=5):
    binned = defaultdict(list, {i: [] for i in range(num_bins)})

    for sample in samples:
        input_text = sample.get('raw_input', '')
        difficulty_score = difficulty_metric(input_text)

        # Get probabilistic assignment
        bin_probs = self.difficulty_to_bin_probabilities(difficulty_score, num_bins)

        # Assign to MOST LIKELY bin (argmax)
        bin_id = max(bin_probs, key=bin_probs.get)

        sample['_bin_id'] = bin_id
        sample['_bin_probs'] = bin_probs  # ← Store probabilities
        binned[bin_id].append(sample)

    return dict(binned)
```

**Used in Analysis**: Deterministic assignment via argmax ✓

**In Production (Phase 1)**:

**File**: `src/routing/production_router.py`, Lines 217-219

```python
capability = self._expected_metric(difficulty, analysis.capability_curve, num_bins)
risk = self._expected_metric(difficulty, analysis.risk_curve, num_bins)

@staticmethod
def _expected_metric(difficulty, curve, num_bins):
    """Interpolate capability/risk for a given difficulty."""
    bin_position = difficulty * (num_bins - 1)
    lower = int(bin_position)
    upper = min(lower + 1, num_bins - 1)
    fraction = bin_position - lower
    lower_val = curve.get(lower, 0.0)
    upper_val = curve.get(upper, 0.0)
    return lower_val * (1 - fraction) + upper_val * fraction
```

**Used in Production**: Interpolated (soft) assignment ✓

### The Contradiction

| Phase | Binning | Deterministic? | Example (diff=0.249) |
|-------|---------|----------------|----|
| **Theory** | Direct formula | ✓ YES | bin=0 |
| **Analysis** | Probabilistic argmax | ✓ YES | bin=1 |
| **Production** | Linear interpolation | ✗ NO | cap=0.004×cap[0]+0.996×cap[1] |

**Analysis and Production use different methods!**

### Impact on Routing Decisions

**Scenario**: Model has capability curve [0.60, 0.90, 0.85, 0.70, 0.65]

**Input with difficulty=0.249**:

**Analysis phase** (Phase 0):
- Bin assignment: bin 1 (argmax)
- Use capability[1] = 0.90

**Production phase** (Phase 1):
- Interpolation: 0.004×0.60 + 0.996×0.90 = 0.8976
- Use 0.8976 (smoother, better)

**Which is correct?** Production's interpolation is actually better (smoother transitions), but it violates the documented simple formula.

---

## SUMMARY TABLE: Mapping Contradictions to Code Locations

| Contradiction | Theory File | Code File | Lines | Severity |
|---|---|---|---|---|
| 1.1: Capability vs Risk Independence | RISK_CURVES.md:8 | framework.py | 191-275 | 🔴 CRITICAL |
| 1.2: τ_risk Detection | COMPLETE_PIPELINE.md:229 | framework.py | 373-385 | 🟠 HIGH |
| 1.3: Risk Computation Methods | Multiple | framework.py | 244-269 | 🟠 MEDIUM-HIGH |
| 2.1: Zone Naming | docs/* | production_router.py | 287-296 | 🟡 LOW |
| 2.2: Zone 2 Policy | COMPLETE_PIPELINE.md:426 | production_router.py | 312-247 | 🔴 CRITICAL |
| 2.3: Monitoring Alerts | COMPLETE_PIPELINE.md:502 | production_router.py | 393-416 | 🟠 MEDIUM |
| 3.1: Capability Computation | QUALITY_METRICS.md | framework.py | 191-219 | 🔴 CRITICAL |
| 3.2: Bin Assignment | COMPLETE_PIPELINE.md:151 | framework.py/production_router.py | 100-285 | 🟡 MEDIUM |
| 4.1: Phase 2 Monitoring | COMPLETE_PIPELINE.md:474 | production_router.py | 351-443 | 🟠 MEDIUM |
| 5.1: Empirical Thresholds | COMPLETE_PIPELINE.md:245 | production_router.py | 51-52 | 🟠 HIGH |

---

**End of Detailed Analysis Document**
