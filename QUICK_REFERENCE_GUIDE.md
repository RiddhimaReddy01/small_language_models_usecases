# QUICK REFERENCE GUIDE: Critical Issues at a Glance
## One-Page Summary for Each Issue

---

## 🔴 ISSUE #1: Capability ≠ (1 - Risk)

### The Problem in One Sentence
**Documented as complementary** (C + R = 1.0) **but computed from independent metrics** (validation_fn vs quality_metric)

### What Gets Counted

| Sample | Compiles? | Tests Pass? | Validity? | Risk? |
|--------|-----------|-------------|-----------|-------|
| Valid + Good | ✓ | ✓ | +1 (capable) | 0 (safe) |
| Valid + Bad | ✓ | ✗ | +1 (capable) | +1 (risk) |
| Invalid + Bad | ✗ | ✗ | 0 (invalid) | +1 (risk) |

**Result**: Validity + Risk ≠ 1.0

### Code Location
- **Theory**: `docs/reference/RISK_CURVES.md:8`
- **Code**: `src/routing/framework.py:191-275`

### Why It Matters
Zone classification uses both independently:
```python
if capability >= 0.80 and risk <= 0.20:
    zone = Q1
```

If they're not truly complementary, the zones don't make logical sense.

### The Fix
Rename "Capability" → "Validity" and document them as independent metrics measuring different failure modes.

---

## 🔴 ISSUE #2: Zone Q2 Missing Implementation

### The Problem in One Sentence
Zone Q2 returns string `"SLM_with_verification"` instead of actual model name, and verification is optional (can be None)

### What Should Happen
```
Zone Q2 detected
  ↓
Generate with SLM
  ↓
Verify output (confidence check)
  ├─ confidence ≥ 0.90? → Return SLM output
  └─ confidence < 0.90? → Generate with LLM, return that
```

### What Actually Happens
```
Zone Q2 detected
  ↓
_apply_zone_policy() returns "SLM_with_verification" (string)
  ↓
Later: IF verification_fn provided THEN override routed_model
       ELSE routed_model stays "SLM_with_verification" ✗
```

### Code Location
- **Theory**: `docs/guides/COMPLETE_PIPELINE.md:426-434`
- **Code**: `src/routing/production_router.py:312-314, 237-247`

### Why It Matters
```python
# If verification_fn is None (default):
model, decision = router.route(...)
# model = "SLM_with_verification"  ← Not a real model!

# Later code tries:
output = model.generate(...)  # ERROR: str has no attribute 'generate'
```

### The Fix
Move verification logic into `_apply_zone_policy()` and make verification_fn REQUIRED for Q2:

```python
def __init__(self, verification_fn: Callable[..., float]):  # REQUIRED
    if verification_fn is None:
        raise ValueError("verification_fn required for Q2 zones")
```

---

## 🔴 ISSUE #3: Capability vs Validity - Different Metrics

### The Problem in One Sentence
Capability is measured using `validation_fn` (structural validity) while Risk is measured using `quality_metric` (functional quality). The **same sample can count opposite ways**.

### Concrete Example
```python
# Sample: Code that compiles but logic is wrong

code = """
def reverse(lst):
    return lst  # BUG!
"""

# Capability check:
validate_code(code)  # Tries: compile(code, ...)
# Result: True ✓ (syntax is valid)
# Counter: +Capability

# Risk check:
quality = tests_passed / total_tests
# Result: 0/5 = 0.0 (tests fail)
# Counter: +Risk

# SAME SAMPLE counts as BOTH "capable" AND "risky"!
```

### What Gets Measured

```
VALIDITY (Capability):
  Does the output have correct syntax/structure?
  ├─ Code compiles?
  ├─ JSON parses?
  └─ Output is non-empty?

QUALITY (Risk):
  Does the output meet performance requirements?
  ├─ Tests pass?
  ├─ ROUGE score > 0.80?
  └─ Constraints satisfied?
```

**These are different things!**

### Code Location
- **Theory**: `docs/reference/QUALITY_METRICS.md`
- **Validity**: `src/routing/framework.py:191-219`
- **Quality/Risk**: `src/routing/framework.py:221-275`

### Why It Matters
A valid but incorrect output will:
- Boost capability (counts as successful)
- Increase risk (counts as failed)

This creates asymmetric zone classifications.

### The Fix
Explicitly separate into `validity_fn` and `quality_metric` and document that they measure independent failure modes.

---

## 🔴 ISSUE #4: Risk Computation Variance

### The Problem in One Sentence
Risk is computed **three different ways** across tasks, so risk values **aren't comparable** across tasks.

### The Three Methods

#### Method 1: Quality Threshold (Continuous)
**Used for**: Text gen, summarization, instruction following
```python
# Risk = count where quality_score < threshold
risk = sum(1 for sample in samples if compute_quality(sample) < 0.80) / len(samples)
```
**Measures**: "What % of samples don't meet the quality bar?"

#### Method 2: Binary Failure
**Used for**: Code gen, classification, maths
```python
# Risk = count where tests_passed == False
risk = sum(1 for sample in samples if not sample['passed']) / len(samples)
```
**Measures**: "What % of samples failed?"

#### Method 3: Severity-Weighted (Fallback)
**Used for**: Custom tasks or when quality_metric not provided
```python
# Risk = sum of weighted severity / total
risk = sum(SEVERITY_WEIGHTS[sample['severity']] for sample in samples) / len(samples)
```
**Measures**: "What's the weighted severity of failures?"

### Example: Same Risk Value, Different Severity

```
Task A - Text Generation:
  Risk = 0.25
  Meaning: "25% of outputs have constraint_satisfaction < 0.80"
  Severity: Varies (could be 0.79 or 0.01)
  Fixability: Rework those constraints

Task B - Code Generation:
  Risk = 0.25
  Meaning: "25% of outputs have tests failing"
  Severity: All equal (binary failure)
  Fixability: Rewrite the logic

SAME NUMBER, DIFFERENT SEVERITY!
```

### Code Location
- **Theory**: `docs/reference/QUALITY_METRICS.md` (multiple methods)
- **Code**: `src/routing/framework.py:244-269`

### Why It Matters
**Monitoring alerts don't distinguish severity**:
```python
# All three alert equally for +0.05 increase:
if (current_risk - baseline_risk) > 0.05:
    alert("Risk degradation")

Text Gen Risk +0.05:    Minor (constraints slightly worse)  ← Low severity
Code Gen Risk +0.05:    Critical (5% more tests failing)   ← High severity
Classification Risk +0.05: Important (5% more wrong)       ← Medium severity

All treated the same! ✗
```

### The Fix
Define `TaskMetrics` dataclass with explicit quality_fn and quality_threshold for each task. Make risk computation consistent.

---

## Summary Table

| Issue | Problem | Code Location | Impact |
|-------|---------|---------------|--------|
| **#1** | C ≠ (1-R) | framework.py:191-275 | Zone classification breaks |
| **#2** | Q2 string return | production_router.py:312 | Can't verify/escalate properly |
| **#3** | Validity vs Quality | framework.py:191-275 | Same sample counts differently |
| **#4** | 3 risk methods | framework.py:244-269 | Risks not comparable across tasks |

---

## Which Issue Affects What?

### Zone Classification (Most Affected)
- Issue #1: C ≠ (1-R) breaks logical basis
- Issue #3: Same sample counted differently
- Issue #4: Risk values inconsistent

### Production Routing
- Issue #2: Q2 can't actually route with verification

### Monitoring/Alerts
- Issue #4: Can't compare risks across tasks

---

## Severity Ranking

```
🔴 CRITICAL - Fix immediately before production:
   ├─ Issue #2 (Q2 missing) - breaks a whole routing strategy
   ├─ Issue #1 (C ≠ 1-R) - zone logic is unsound
   └─ Issue #3 (Validity vs Quality) - metrics are confusing

🟠 HIGH - Fix soon:
   └─ Issue #4 (Risk variance) - affects monitoring and comparisons
```

---

## Quick Diagnosis: Which Issue Are You Experiencing?

### Symptom: "Zone assignments seem wrong"
→ **Issues #1 or #3** - Check if capability and risk are really measuring what you think

### Symptom: "Q2 routing fails or returns invalid model"
→ **Issue #2** - Q2 implementation is incomplete

### Symptom: "Monitoring alerts don't make sense across tasks"
→ **Issue #4** - Risk values aren't comparable

### Symptom: "Same sample counted differently in capability vs risk"
→ **Issue #3** - Validity and quality are independent

---

## Testing Each Issue

### Issue #1: Verify C + R ≠ 1.0
```python
# Compute curves
cap_curve = {0: 0.80, 1: 0.85, ...}
risk_curve = {0: 0.70, 1: 0.72, ...}

# Check: Should sum to 1.0 if truly complementary
for b in cap_curve:
    total = cap_curve[b] + risk_curve[b]
    if total != 1.0:
        print(f"Bin {b}: C+R = {total} (not 1.0)")
```

### Issue #2: Verify Q2 Gets Real Model Name
```python
router = ProductionRouter()  # No verification_fn
model, decision = router.route(..., preferred_model="qwen")

if decision.zone == "Q2":
    assert model in ["qwen", "llama"], f"Got {model} (invalid!)"
    assert model != "SLM_with_verification"
```

### Issue #3: Verify Same Sample Counted Independently
```python
# Create sample: valid but bad quality
sample = {
    'raw_output': 'valid code',  # Would pass validation_fn
    'tests_passed': False,       # But fails quality check
}

# Compute curves
validity_count, quality_count = 0, 0
if validation_fn(sample['raw_output']):
    validity_count += 1  # +1
if not sample['tests_passed']:
    quality_count += 1   # +1

assert validity_count == 1
assert quality_count == 1
# Both counters increment = ISSUE confirmed
```

### Issue #4: Verify Different Risk Meanings
```python
# Compare text gen and code gen with same risk value
text_gen_risk = compute_risk_by_quality_threshold(samples, threshold=0.80)
code_gen_risk = compute_risk_by_binary_failure(samples)

# Both might = 0.25, but they mean different things
print(f"Text Gen Risk=0.25: {text_gen_risk_meaning}")
print(f"Code Gen Risk=0.25: {code_gen_risk_meaning}")
# These are semantically different!
```

---

## Document Map

| Document | Purpose | Size |
|----------|---------|------|
| **RESEARCH_REPORT_THEORY_VS_CODE.md** | Executive summary, all 7 issues | 14 KB |
| **DETAILED_CONTRADICTION_ANALYSIS.md** | Deep technical analysis with code | 18 KB |
| **CRITICAL_ISSUES_EXPLAINED.md** | Visual explanations of 4 critical issues | 15 KB |
| **ACTION_ITEMS_AND_FIXES.md** | Implementation roadmap with code examples | 20 KB |
| **QUICK_REFERENCE_GUIDE.md** | This file - one-page per issue | 5 KB |

---

**Next Steps**:
1. Read CRITICAL_ISSUES_EXPLAINED.md for visual walkthrough
2. Check which issues affect your use case (see "Symptom" section above)
3. Review ACTION_ITEMS_AND_FIXES.md for implementation plan

**Questions?** Each issue is fully explained with:
- Concrete code examples
- Visual diagrams
- Impact analysis
- Recommended fixes
