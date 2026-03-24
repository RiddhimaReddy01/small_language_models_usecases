# CRITICAL ISSUES EXPLAINED: Detailed Walkthrough
## Visual Explanations with Real Examples

---

## ISSUE #1: Capability ≠ (1 - Risk)

### The Documented Formula

**From**: `docs/reference/RISK_CURVES.md`, Line 8

```
Risk_m(b) = P̂_m(fail|b) = # failures in bin b / # samples in bin b

Capability_m(b) = C_m(b) = 1 - Risk_m(b)
```

This says: **They are mathematical complements**

If Risk = 0.30, then Capability MUST = 0.70 (they sum to 1.0)

```
Capability + Risk = 1.0 (ALWAYS)
```

### What Actually Happens in the Code

The code computes them **independently from different things**:

```python
# CAPABILITY: Is output structurally valid?
def compute_capability_curve(samples_by_bin, validation_fn):
    for sample in samples:
        output = sample.get('raw_output')
        if validation_fn(output):  # ← Check if VALID
            valid_count += 1
    capability = valid_count / total


# RISK: Is output meeting quality standards?
def compute_risk_curve(samples_by_bin, quality_metric):
    for sample in samples:
        quality_score = quality_metric(sample)  # ← Check QUALITY
        if quality_score < threshold:
            failure_count += 1
    risk = failure_count / total
```

### Visual Example: Code Generation Task

Imagine you run Qwen on 10 code generation problems:

```
Sample 1: Code compiles ✓ but tests fail ✗
Sample 2: Code compiles ✓ but tests fail ✗
Sample 3: Code compiles ✓ and tests pass ✓
Sample 4: Code compiles ✓ but tests fail ✗
Sample 5: Code compiles ✓ but tests fail ✗
Sample 6: Code compiles ✓ but tests fail ✗
Sample 7: Code compiles ✓ and tests pass ✓
Sample 8: Syntax error ✗ and tests fail ✗
Sample 9: Code compiles ✓ but tests fail ✗
Sample 10: Code compiles ✓ but tests fail ✗
```

### How They're Counted

#### Capability Calculation (Validity Check)

```
Question: Is the code syntactically valid?

Sample 1: ✓ compiles
Sample 2: ✓ compiles
Sample 3: ✓ compiles
Sample 4: ✓ compiles
Sample 5: ✓ compiles
Sample 6: ✓ compiles
Sample 7: ✓ compiles
Sample 8: ✗ SYNTAX ERROR (fails here)
Sample 9: ✓ compiles
Sample 10: ✓ compiles

CAPABILITY = 9/10 = 0.90 (90% of outputs are valid)
```

#### Risk Calculation (Quality Check)

```
Question: Do the tests pass? (threshold = 1.0, all tests must pass)

Sample 1: ✗ tests fail
Sample 2: ✗ tests fail
Sample 3: ✓ tests pass
Sample 4: ✗ tests fail
Sample 5: ✗ tests fail
Sample 6: ✗ tests fail
Sample 7: ✓ tests pass
Sample 8: ✗ tests fail (already invalid)
Sample 9: ✗ tests fail
Sample 10: ✗ tests fail

RISK = 8/10 = 0.80 (80% of outputs failed tests)
```

### The Math Breaks

```
Theory says:  Capability + Risk = 1.0
              0.90 + 0.80 = 1.70 ← WRONG! Should be 1.0
```

### Why This Matters: Zone Classification

**File**: `src/routing/production_router.py:287-296`

```python
def _classify_zone(self, capability, risk, tau_c, tau_r):
    if capability >= tau_c and risk <= tau_r:
        return "Q1"  # Safe to use SLM
    elif capability >= tau_c and risk > tau_r:
        return "Q2"  # Need verification
    elif capability < tau_c and risk <= tau_r:
        return "Q3"  # Hybrid (easy→SLM, hard→LLM)
    else:
        return "Q4"  # Use LLM
```

With our example:
- Capability = 0.90, Risk = 0.80
- τ_c = 0.80, τ_r = 0.20

```
Check: capability >= 0.80?  YES (0.90 ≥ 0.80) ✓
Check: risk <= 0.20?        NO  (0.80 > 0.20) ✗

Result: Q2 (SLM + verification)
```

**But the math says**: If capability=0.90, then risk SHOULD be 0.10 (not 0.80)!

### The Real Problem

They're measuring **different failure modes**:

```
VALIDITY FAILURES (Capability):
  ├─ Syntax errors
  ├─ Code won't compile
  └─ Structural issues

QUALITY FAILURES (Risk):
  ├─ Code compiles but tests fail
  ├─ Logic errors
  └─ Wrong algorithm implementation
```

A sample can be:
1. **Valid but low quality** ← Counts as SUCCESS in capability, FAILURE in risk
2. **Invalid** ← Counts as FAILURE in both (by definition)
3. **Valid and high quality** ← Counts as SUCCESS in both

### Visual Comparison

```
WITHOUT UNDERSTANDING THE DIFFERENCE:

You see: "Capability = 0.90, Risk = 0.80"
You think: "High capability, high risk → Q2 (risky but capable)"
You route to: SLM + verification

REALITY:
"90% of code compiles" != "90% of code passes tests"
These are measuring DIFFERENT things!

The code is well-formed but broken.
Verification won't help if the logic is wrong.
```

---

## ISSUE #2: Zone Q2 Missing Implementation

### The Theory: SLM + Verification + Escalation

**From**: `docs/guides/COMPLETE_PIPELINE.md:426-434`

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

**Expected flow**:
```
INPUT
  ↓
TRY SLM (quick, cheap)
  ↓
VERIFY OUTPUT
  ├─ Confidence ≥ 0.90? → RETURN SLM OUTPUT (success!)
  └─ Confidence < 0.90? → ESCALATE TO LLM
                           ↓
                        RETURN LLM OUTPUT (safe)
  ↓
OUTPUT
```

### What the Code Actually Does

**File**: `src/routing/production_router.py:312-314`

```python
elif zone == "Q2":
    # Zone 2: SLM + Verify + Escalate
    return "SLM_with_verification"
```

**That's it!** Just returns a string.

### Where Verification Actually Happens

**File**: `src/routing/production_router.py:237-247`

```python
# After _apply_zone_policy has already returned...

routed_model = self._apply_zone_policy(...)
# For Q2: routed_model = "SLM_with_verification"

verification_status = "not_applicable"
if zone == "Q2" and self.verification_fn:
    # ↑ PROBLEM: verification_fn is OPTIONAL (can be None)
    try:
        verified = bool(self.verification_fn(...))
    except:
        verified = False

    if not verified:
        routed_model = "llama"
```

### The Problem Illustrated

#### Scenario 1: Verification Function IS Provided

```python
router = ProductionRouter(verification_fn=my_verify_fn)

zone = "Q2"
routed_model = router._apply_zone_policy(...)  # Returns "SLM_with_verification"

if zone == "Q2" and router.verification_fn:  # ✓ verification_fn is NOT None
    confidence = router.verification_fn(...)
    if confidence < 0.90:
        routed_model = "llama"  # Override to LLM

# routed_model now = "llama" or "qwen" (actual model)
```

**Result**: Works! (by accident, because verification happens later)

#### Scenario 2: Verification Function NOT Provided

```python
router = ProductionRouter()  # verification_fn = None (default)

zone = "Q2"
routed_model = router._apply_zone_policy(...)  # Returns "SLM_with_verification"

if zone == "Q2" and router.verification_fn:  # ✗ verification_fn IS None
    # This block is SKIPPED
    pass

# routed_model still = "SLM_with_verification"

# Problem: Now the code tries to use "SLM_with_verification" as a model!
# But it's not a real model, it's just a string.
```

**Result**: BROKEN! The model identifier is invalid.

### What Calling Code Would Do

```python
model, decision = router.route(input_text="...", task="code_generation")

# If Zone Q2 without verification_fn:
# model = "SLM_with_verification"  ← Not a valid model!

# Later, code tries:
output = model.generate(input_text)  # AttributeError: str has no method 'generate'
```

### Visual Comparison: Theory vs Code

```
THEORY (What should happen):

Zone Q2 detected
  ↓
SLM generates output
  ↓
VERIFY output
  ├─ Good? ✓ → Return SLM output
  └─ Bad? ✗ → Generate LLM output, return that
  ↓
Return actual output + decision


CODE (What actually happens):

Zone Q2 detected
  ↓
_apply_zone_policy returns "SLM_with_verification" (string)
  ↓
IF verification_fn provided:
    Check if verified
    IF verified: routed_model = "qwen"
    ELSE: routed_model = "llama"
ELSE:
    routed_model = "SLM_with_verification" (unchanged)
  ↓
Return routed_model + decision

IF routed_model = "SLM_with_verification":
    This isn't a real model! ✗
```

### Why This Breaks Zone Q2

Zone Q2 is for tasks that are:
- **Capable** (model works well most of the time)
- **Risky** (failures are costly or unpredictable)

**Example**: Code generation with SLM
- 85% of code passes tests (capable)
- But when it fails, it fails catastrophically (risky)
- Verification could catch the failures

**Without proper Q2 implementation**:
- You can't use the SLM + verification strategy
- You have to either use pure SLM (risky) or pure LLM (expensive)
- You lose a whole routing option

---

## ISSUE #3: Capability vs Validity - Different Metrics

### The Confusion

The code uses **two different terms** for **three different concepts**:

```
TERM: "Capability"
CONCEPT 1: Validity (structural soundness)
CONCEPT 2: Quality (functional correctness)
CONCEPT 3: Can it do the task? (combination)

These are NOT the same thing!
```

### Let's Trace Through Code Generation

**Sample**: Python code to reverse a list

```python
# Qwen's Output:
def reverse(lst):
    return lst[::-1]
```

#### Check 1: Is it VALID? (validation_fn)

```python
def validate_code(output):
    try:
        compile(output, '<string>', 'exec')
        return True
    except SyntaxError:
        return False

validate_code(reverse_func) = True  # ✓ Compiles
```

**Capability counter**: +1 (counted as capable)

#### Check 2: Is it GOOD? (quality_metric)

```python
def compute_quality(sample):
    return sample['tests_passed'] / sample['total_tests']

quality_score = 5/5 = 1.0  # ✓ All tests pass
threshold = 1.0

is_high_quality = (1.0 >= 1.0) = True
```

**Risk counter**: 0 (counted as safe, no risk)

### Now Change the Example

**Another Sample**: Broken code

```python
# Qwen's Output:
def reverse(lst):
    return lst  # Bug: doesn't actually reverse
```

#### Check 1: Is it VALID?

```python
validate_code(broken_func) = True  # ✓ Still compiles!
```

**Capability counter**: +1 (counted as capable)

#### Check 2: Is it GOOD?

```python
quality_score = 0/5 = 0.0  # ✗ All tests fail
is_high_quality = (0.0 >= 1.0) = False
```

**Risk counter**: +1 (counted as risky)

### The Problem

**For the same sample** (broken code that compiles):

| Metric | Value | Interpretation | Counter |
|--------|-------|-----------------|---------|
| **Validity** | ✓ Compiles | Code is valid | +Capability |
| **Quality** | ✗ Tests fail | Code is wrong | +Risk |

**Same sample is counted OPPOSITE ways!**

```
Capability = "This code is valid"     ← TRUE (it's syntactically correct)
Risk       = "This code will fail"    ← TRUE (tests don't pass)

Both are correct, but they're not complements!
They measure different failure modes.
```

### Real-World Scenario: 10 Code Samples

```
Sample #  | Compiles? | Tests Pass? | Capability | Risk
----------|-----------|-------------|------------|-------
1         | ✓         | ✓           | +1         | 0
2         | ✓         | ✗           | +1         | +1  ← KEY ISSUE
3         | ✓         | ✗           | +1         | +1
4         | ✓         | ✓           | +1         | 0
5         | ✓         | ✗           | +1         | +1
6         | ✗         | ✗           | 0          | +1
7         | ✓         | ✓           | +1         | 0
8         | ✓         | ✗           | +1         | +1
9         | ✓         | ✓           | +1         | 0
10        | ✓         | ✗           | +1         | +1

TOTALS:   9/10       5/10
          Capability = 0.90 (90% valid)
          Risk = 0.50 (50% fail tests)

Capability + Risk = 0.90 + 0.50 = 1.40 ≠ 1.0
```

### Why This Matters

When you classify zones, you're treating them as related but independent:

```python
if capability >= 0.80 and risk <= 0.20:
    zone = Q1  # Safe, capable
elif capability >= 0.80 and risk > 0.20:
    zone = Q2  # Capable but risky
elif capability < 0.80 and risk <= 0.20:
    zone = Q3  # Weak but safe
else:
    zone = Q4  # Weak and risky
```

**But if they're not truly complementary**, the zones don't make logical sense:

```
What does "Capable=0.90, Risk=0.50" mean?
"90% of code compiles, but 50% of code fails tests"

These don't contradict each other because they measure different things!
- The 90% is "valid syntax"
- The 50% is "wrong logic"

A syntactically valid program can have logic errors.
```

---

## ISSUE #4: Risk Computation Variance

### The Three Different Methods

#### Method 1: Quality Threshold (Continuous)

**Used for**: Text generation, summarization, instruction following

```python
# Example: Text generation with constraint satisfaction rate

def compute_risk_text_gen(samples):
    failures = 0
    for sample in samples:
        quality_score = sample['metrics']['constraint_satisfaction_rate']
        # quality_score is a continuous value: 0.0 to 1.0
        # (what fraction of constraints are satisfied?)

        if quality_score < 0.80:  # Below threshold?
            failures += 1

    risk = failures / total
```

**What it measures**: "What % of samples don't meet the quality bar?"

**Example scenario**:
```
Sample 1: constraint_satisfaction = 0.95 ✓ Above 0.80 → counts as PASS
Sample 2: constraint_satisfaction = 0.75 ✗ Below 0.80 → counts as FAIL
Sample 3: constraint_satisfaction = 0.80 ✓ Equal to 0.80 → counts as PASS
Sample 4: constraint_satisfaction = 0.50 ✗ Below 0.80 → counts as FAIL

Risk = 2 failures / 4 samples = 0.50 (50%)
```

#### Method 2: Binary Failure (Tests Pass/Fail)

**Used for**: Code generation, classification, maths

```python
# Example: Code generation with test pass/fail

def compute_risk_code_gen(samples):
    failures = 0
    for sample in samples:
        tests_passed = sample['passed']  # Boolean: True/False

        if not tests_passed:  # Tests failed?
            failures += 1

    risk = failures / total
```

**What it measures**: "What % of samples failed?"

**Example scenario**:
```
Sample 1: tests_passed = True  ✓ → counts as PASS
Sample 2: tests_passed = False ✗ → counts as FAIL
Sample 3: tests_passed = True  ✓ → counts as PASS
Sample 4: tests_passed = False ✗ → counts as FAIL

Risk = 2 failures / 4 samples = 0.50 (50%)
```

#### Method 3: Severity-Weighted (Fallback)

**Used for**: When quality_metric not provided

```python
# Example: Custom task with severity weights

SEVERITY_WEIGHTS = {
    "critical": 1.0,    # Timeout, empty output
    "high": 0.8,        # Execution error, wrong result
    "medium": 0.5,      # Incomplete output
    "low": 0.2,         # Formatting issues
}

def compute_risk_weighted(samples):
    total_weight = 0.0
    for sample in samples:
        if not sample['valid']:
            severity = sample['severity']
            weight = SEVERITY_WEIGHTS[severity]
            total_weight += weight

    risk = total_weight / total
```

**What it measures**: "What's the weighted severity of failures?"

**Example scenario**:
```
Sample 1: valid=True  → weight = 0.0
Sample 2: valid=False, severity="critical"  → weight = 1.0
Sample 3: valid=True  → weight = 0.0
Sample 4: valid=False, severity="low"  → weight = 0.2

Risk = (0.0 + 1.0 + 0.0 + 0.2) / 4 = 0.30 (30%)
```

### The Problem: Same Risk Value, Different Meanings

Let's say we have two tasks, both showing **Risk = 0.25**

#### Task A: Text Generation (Continuous Quality)

```
25% of outputs have constraint_satisfaction_rate < 0.80
```

**Interpretation**:
- Output 1: 50% constraints satisfied (minor issue, fixable)
- Output 2: 75% constraints satisfied (mostly works)
- Output 3: 45% constraints satisfied (significant rework needed)
- ...etc

**Severity**: Varies by how far below 0.80 they fall

#### Task B: Code Generation (Binary Tests)

```
25% of outputs have tests failing
```

**Interpretation**:
- Output 1: All tests fail (completely broken)
- Output 2: All tests fail (completely broken)
- Output 3: All tests fail (completely broken)
- ...etc

**Severity**: All equally bad (tests pass or they don't)

### Visual Comparison

```
RISK = 0.25 IN DIFFERENT CONTEXTS:

Text Generation:
┌─────────────────────────────────────┐
│ Constraint Satisfaction             │
│ 0%        40%       80%       100%   │
│ ├───F───┤├────F────┤├──PASS──┤     │
│ 25% are below the 80% bar            │
│ → Minor rework needed                │
└─────────────────────────────────────┘

Code Generation:
┌─────────────────────────────────────┐
│ Tests Pass/Fail                      │
│ FAIL  FAIL  FAIL  PASS               │
│ F     F     F     P   (25% pass)     │
│ → Complete rewrite needed            │
└─────────────────────────────────────┘

SAME NUMBER (0.25), DIFFERENT SEVERITY!
```

### Why This Breaks Comparisons

**Scenario**: Monitoring degradation across tasks

```
BASELINE (Week 1):
├─ Text Gen Risk:          0.20 (20% outputs below quality bar)
├─ Code Gen Risk:          0.20 (20% of tests fail)
└─ Classification Risk:     0.05 (5% predictions wrong)

NEW (Week 2):
├─ Text Gen Risk:          0.25 (+0.05) ← Triggered Alert
├─ Code Gen Risk:          0.25 (+0.05) ← Triggered Alert
└─ Classification Risk:     0.10 (+0.05) ← Triggered Alert

All three triggered with the SAME INCREASE.
But severity is different:
├─ Text Gen: Slightly worse constraints → FIXABLE
├─ Code Gen: More tests failing → CRITICAL
└─ Classification: More wrong predictions → IMPORTANT
```

**The alert system treats them equally, but they're not!**

### Example: Thresholds Are Inconsistent

```
Task-Specific Quality Thresholds:

Text Generation:
    threshold = 0.80 (constraint satisfaction ≥ 80%)

Summarization:
    threshold = 0.80 (ROUGE F1 ≥ 80%)

Code Generation:
    threshold = 1.0 (ALL tests must pass)

Classification:
    threshold = 1.0 (prediction must be correct)
```

**What "Risk = 0.20" means**:

```
Text Gen:    20% of outputs have CSR < 0.80
             (could have 0.79, 0.50, 0.01, etc.)

Code Gen:    20% of outputs have tests not passing
             (binary: either pass or fail)

Classification:
             20% of predictions are wrong
             (binary: either correct or incorrect)
```

**Are these comparable?** Technically yes, numerically. But semantically NO.

---

## Summary: Why These 4 Issues Are Critical

### Issue #1: Capability ≠ (1 - Risk)
**Impact**: Zone classification logic assumes they're complements, but they're independent measures
**Risk**: Wrong zones assigned, suboptimal routing decisions

### Issue #2: Zone Q2 Missing
**Impact**: Can't actually implement verification + escalation strategy
**Risk**: Have to choose between expensive LLM or unreliable SLM, lose a routing option

### Issue #3: Capability vs Validity
**Impact**: Same sample counted differently in capability and risk curves
**Risk**: Misleading metrics, zones don't make logical sense

### Issue #4: Risk Variance
**Impact**: Risk values aren't comparable across tasks
**Risk**: Monitoring alerts triggered equally for vastly different severity levels

---

## Visual Summary: How They Interconnect

```
┌────────────────────────────────────────────────────────┐
│          THEORY (Documented)                           │
│  Capability = 1 - Risk  ← Complementary metrics       │
│  Zone 1/2/3/4 classification                          │
│  Q2: SLM + Verify + Escalate                          │
│  Risk: Universal meaning across tasks                  │
└────────────────────────────────────────────────────────┘
                         ↓ MISMATCH ↓
┌────────────────────────────────────────────────────────┐
│          CODE (Actual Implementation)                  │
│  Capability = Validity (independent from Risk)       │
│  Risk = Quality (independent from Validity)           │
│  Zone Q2: Returns "SLM_with_verification" string     │
│  Risk: Task-specific, different methods              │
│  → Capability + Risk ≠ 1.0                           │
│  → Q2 not properly implemented                        │
│  → Same sample counts differently                     │
│  → Risk not comparable across tasks                   │
└────────────────────────────────────────────────────────┘
```

---

**End of Critical Issues Explanation**
