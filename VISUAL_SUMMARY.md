# VISUAL SUMMARY: Understanding the 4 Critical Issues

---

## ISSUE #1: Capability ≠ (1 - Risk)

### What the Documentation Says

```
Mathematical Relationship:
┌─────────────────────────────────────┐
│  Capability = 1 - Risk              │
│  C + R = 1.0 (always)               │
│                                      │
│  Example:                           │
│  If Risk = 0.20 → Capability = 0.80 │
│  If Risk = 0.50 → Capability = 0.50 │
└─────────────────────────────────────┘
```

### What the Code Actually Does

```
Independent Computations:
┌──────────────────────┐      ┌──────────────────────┐
│  VALIDITY CHECK      │      │   QUALITY CHECK      │
│  (Capability)        │      │   (Risk)             │
│                      │      │                      │
│  Does output have    │      │  Does output meet    │
│  correct structure?  │      │  quality standards?  │
│                      │      │                      │
│  ✓ Compiles          │      │  ✓ Tests pass        │
│  ✓ JSON parses       │      │  ✓ ROUGE > 0.80      │
│  ✓ Non-empty         │      │  ✓ Constraints met   │
│                      │      │                      │
│  Result: Valid/Invalid     Result: Good/Bad      │
└──────────────────────┘      └──────────────────────┘
         ↓                              ↓
    CAPABILITY                        RISK
    (independent)              (independent)
```

### The Breakdown

```
10 Code Samples:

Sample #1:  Code compiles ✓  Tests pass ✓  → +Capability, 0 Risk
Sample #2:  Code compiles ✓  Tests fail ✗  → +Capability, +Risk    ← KEY!
Sample #3:  Code compiles ✓  Tests fail ✗  → +Capability, +Risk
Sample #4:  Syntax error ✗   Tests fail ✗  → 0 Capability, +Risk
...

TOTALS:
Capability = 9/10 = 0.90
Risk = 6/10 = 0.60

CHECK: 0.90 + 0.60 = 1.50 ✗ (should be 1.0)
```

### Why This Breaks Zone Logic

```
Zone Classification:
┌─────────────────────────────────────────────────┐
│  if capability >= 0.80 and risk <= 0.20:        │
│      zone = Q1  ← Safe, use SLM                  │
│  elif capability >= 0.80 and risk > 0.20:       │
│      zone = Q2  ← Risky, use SLM+verify         │
│  elif capability < 0.80 and risk <= 0.20:       │
│      zone = Q3  ← Weak but safe, hybrid         │
│  else:                                          │
│      zone = Q4  ← Weak and risky, use LLM       │
└─────────────────────────────────────────────────┘

With C=0.90, R=0.60:
├─ Should be IMPOSSIBLE if C = 1-R
├─ But it IS possible if they're independent
└─ Zone logic assumes they're related!
```

---

## ISSUE #2: Zone Q2 Missing Implementation

### Expected Flow (Theory)

```
                    INPUT
                      ↓
            ┌─────────────────────┐
            │  Is Zone Q2?        │
            │  (capable but risky)│
            └─────────┬───────────┘
                      │ YES
                      ↓
        ┌────────────────────────┐
        │  Generate with SLM     │
        │  (fast, cheap)         │
        └──────────┬─────────────┘
                   ↓
        ┌────────────────────────┐
        │  Verify Output         │
        │  (check confidence)    │
        └──────┬──────────┬──────┘
               │          │
          Good?         Bad?
        ≥0.90%        <0.90%
          │              │
          ↓              ↓
    ┌──────────┐    ┌──────────────┐
    │ Return   │    │ Generate     │
    │ SLM      │    │ with LLM     │
    │ output   │    │ (safe)       │
    └──┬───────┘    └──┬───────────┘
       │                │
       └────┬───────────┘
            ↓
        ┌─────────────┐
        │  OUTPUT     │
        └─────────────┘
```

### What Code Actually Does

```
                    INPUT
                      ↓
            ┌─────────────────────┐
            │  Is Zone Q2?        │
            └─────────┬───────────┘
                      │ YES
                      ↓
        ┌────────────────────────────┐
        │  _apply_zone_policy()      │
        │  returns:                  │
        │  "SLM_with_verification"   │
        │  (just a string!)          │
        └──────────┬─────────────────┘
                   ↓
        ┌────────────────────────────┐
        │  IF verification_fn        │
        │     provided?              │
        └────┬──────────────┬────────┘
             │              │
          YES?            NO?
             │              │
             ↓              ↓
        ┌─────────┐   ┌──────────────┐
        │ Check   │   │ routed_model │
        │ verify  │   │ stays as:    │
        │ result  │   │ "SLM_with_   │
        │ Override│   │  verification│
        │ model   │   │ (INVALID!)   │
        └─────────┘   └──────────────┘
           ↓
        ┌────────────────────────────┐
        │  OUTPUT                    │
        │  model = "qwen" or "llama" │
        │  (or "SLM_with_..." if no  │
        │   verification_fn)         │
        └────────────────────────────┘
```

### The Problem Highlighted

```
SCENARIO 1: verification_fn PROVIDED ✓
┌────────────────────────────────┐
│ router = ProductionRouter(      │
│     verification_fn=my_verify   │
│ )                              │
│                                │
│ model, decision = router.route(│
│     input_text="...",          │
│     task="code_gen"            │
│ )                              │
│                                │
│ Result: model = "qwen" ✓       │
│ (Works, but circuitous route)  │
└────────────────────────────────┘


SCENARIO 2: verification_fn NOT PROVIDED ✗
┌────────────────────────────────┐
│ router = ProductionRouter()     │
│ # verification_fn = None        │
│                                │
│ model, decision = router.route(│
│     input_text="...",          │
│     task="code_gen"            │
│ )                              │
│                                │
│ if decision.zone == "Q2":      │
│     # model = "SLM_with_      │
│     #           verification" │
│     #                          │
│     # This isn't a real model! │
│     # Later calls fail:        │
│     model.generate(...)  ✗     │
│     # AttributeError!          │
└────────────────────────────────┘
```

---

## ISSUE #3: Capability vs Validity - Different Metrics

### The Two Measurements

```
┌─────────────────────────────────────┐
│         VALIDITY MEASUREMENT        │
│         (calls validation_fn)       │
│                                     │
│  Question: Is output structurally   │
│            valid?                   │
│                                     │
│  Checks:                            │
│  ├─ Code compiles?                  │
│  ├─ JSON parses?                    │
│  ├─ Output non-empty?               │
│  └─ ...                             │
│                                     │
│  Result: BOOLEAN (valid/invalid)    │
└─────────────────────────────────────┘
         VALIDITY COUNTS +1
             ↓
         CAPABILITY
         (percentage valid)


┌─────────────────────────────────────┐
│         QUALITY MEASUREMENT         │
│         (calls quality_metric)      │
│                                     │
│  Question: Does output meet         │
│            quality standards?       │
│                                     │
│  Checks:                            │
│  ├─ Tests pass?                     │
│  ├─ ROUGE > 0.80?                   │
│  ├─ Constraints met?                │
│  └─ ...                             │
│                                     │
│  Result: FLOAT [0.0, 1.0]           │
│          compared to threshold      │
└─────────────────────────────────────┘
         QUALITY COUNTS +RISK
             ↓
           RISK
         (percentage low quality)
```

### Concrete Example: One Sample, Two Counts

```
SAMPLE: Generated Python Code

def reverse(lst):
    return lst[::-1]  # ← Correct!

┌──────────────────────────────────┐
│  VALIDITY CHECK                  │
│  compile(code, '<string>', 'ex') │
│  → Success (no exception)        │
│                                  │
│  Result: +1 CAPABILITY           │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  QUALITY CHECK                   │
│  tests_passed / total_tests      │
│  = 5 / 5 = 1.0                  │
│  Is 1.0 >= 1.0? YES             │
│                                  │
│  Result: 0 RISK                  │
└──────────────────────────────────┘


SAME SAMPLE: Broken Code

def reverse(lst):
    return lst  # ← Bug!

┌──────────────────────────────────┐
│  VALIDITY CHECK                  │
│  compile(code, '<string>', 'ex') │
│  → Success (no exception)        │
│                                  │
│  Result: +1 CAPABILITY           │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  QUALITY CHECK                   │
│  tests_passed / total_tests      │
│  = 0 / 5 = 0.0                  │
│  Is 0.0 >= 1.0? NO              │
│                                  │
│  Result: +1 RISK                 │
└──────────────────────────────────┘


BOTH samples have +CAPABILITY but different RISK!
```

### Distribution Across 10 Samples

```
10 samples analyzed:

Sample | Compiles? | Tests Pass? | Capability | Risk
-------|-----------|-------------|------------|------
1      | ✓         | ✓           |     +1     |  0
2      | ✓         | ✗           |     +1     |  +1  ← KEY ISSUE
3      | ✓         | ✗           |     +1     |  +1
4      | ✓         | ✓           |     +1     |  0
5      | ✓         | ✗           |     +1     |  +1
6      | ✗         | ✗           |      0     |  +1
7      | ✓         | ✓           |     +1     |  0
8      | ✓         | ✗           |     +1     |  +1
9      | ✓         | ✓           |     +1     |  0
10     | ✓         | ✗           |     +1     |  +1
-------|-----------|-------------|------------|------
TOTAL  | 9         | 5           | 0.90       | 0.60

Results: C=0.90, R=0.60
Check:   0.90 + 0.60 = 1.50 ≠ 1.0 ✗

Why the mismatch?
Sample #2: Valid syntax but failed tests
Sample #3: Valid syntax but failed tests
Sample #8: Valid syntax but failed tests

All count as BOTH capable AND risky!
```

---

## ISSUE #4: Risk Computation Variance

### Three Different Methods

```
METHOD 1: Quality Threshold (Continuous)
Used for: Text generation, summarization
┌──────────────────────────────────────────┐
│  for sample in samples:                  │
│      quality_score = quality_metric()    │
│      # Returns: 0.0 to 1.0 (continuous) │
│                                          │
│      if quality_score < threshold:       │
│          failures += 1                   │
│  risk = failures / total                 │
│                                          │
│  Example:                                │
│  ├─ Sample 1: quality=0.95 ✓ (OK)       │
│  ├─ Sample 2: quality=0.75 ✗ (FAIL)     │
│  └─ Risk = 1/2 = 0.50                   │
└──────────────────────────────────────────┘
  Measures: "What % below quality bar?"
  Severity: VARIES (depends how far below)


METHOD 2: Binary Failure
Used for: Code generation, classification
┌──────────────────────────────────────────┐
│  for sample in samples:                  │
│      passed = sample['passed']           │
│      # Returns: True/False (binary)      │
│                                          │
│      if not passed:                      │
│          failures += 1                   │
│  risk = failures / total                 │
│                                          │
│  Example:                                │
│  ├─ Sample 1: passed=True ✓              │
│  ├─ Sample 2: passed=False ✗             │
│  └─ Risk = 1/2 = 0.50                    │
└──────────────────────────────────────────┘
  Measures: "What % failed?"
  Severity: UNIFORM (all equal)


METHOD 3: Severity-Weighted
Used for: Custom tasks
┌──────────────────────────────────────────┐
│  for sample in samples:                  │
│      if not valid:                       │
│          severity = sample['severity']   │
│          weight = WEIGHTS[severity]      │
│          total_weight += weight          │
│  risk = total_weight / total             │
│                                          │
│  Example:                                │
│  ├─ Sample 1: critical → weight=1.0     │
│  ├─ Sample 2: low → weight=0.2          │
│  └─ Risk = 1.2/2 = 0.60                 │
└──────────────────────────────────────────┘
  Measures: "What's the weighted severity?"
  Severity: WEIGHTED by failure type
```

### Same Value, Different Meanings

```
RISK = 0.25 across three tasks:

TEXT GENERATION (Method 1)
┌──────────────────────────────────────┐
│  25% of outputs have CSR < 0.80      │
│                                      │
│  Distribution:                       │
│  ├─ Output A: CSR=0.79 (tiny miss)  │
│  ├─ Output B: CSR=0.50 (big miss)   │
│  └─ Output C: CSR=0.30 (major fail) │
│                                      │
│  Interpretation:                    │
│  "Mostly OK, some need tweaks"      │
│  Fixability: REWORK CONSTRAINTS     │
└──────────────────────────────────────┘

CODE GENERATION (Method 2)
┌──────────────────────────────────────┐
│  25% of outputs have tests failing   │
│                                      │
│  Distribution:                       │
│  ├─ Output A: ALL tests fail        │
│  ├─ Output B: ALL tests fail        │
│  └─ Output C: ALL tests fail        │
│                                      │
│  Interpretation:                    │
│  "Logic is broken in 1 out of 4"    │
│  Fixability: REWRITE LOGIC          │
└──────────────────────────────────────┘

CLASSIFICATION (Method 2)
┌──────────────────────────────────────┐
│  25% of predictions are wrong        │
│                                      │
│  Distribution:                       │
│  ├─ Output A: Wrong class           │
│  ├─ Output B: Wrong class           │
│  └─ Output C: Wrong class           │
│                                      │
│  Interpretation:                    │
│  "Model is confused 1 out of 4"     │
│  Fixability: RETRAIN/ADJUST         │
└──────────────────────────────────────┘


PROBLEM: Same alert for different severity!
```

### Monitoring Consequences

```
                    BASELINE (Week 1)
    Text Gen Risk = 0.20
    Code Gen Risk = 0.20
    Classification Risk = 0.05

                        ↓ WEEK 2 UPDATE ↓

                    CURRENT (Week 2)
    Text Gen Risk = 0.25 (+0.05)  ← ALERT
    Code Gen Risk = 0.25 (+0.05)  ← ALERT
    Classification Risk = 0.10 (+0.05)  ← ALERT

All three alert equally!

But actual severity is:
    Text Gen:       Slightly worse constraints
                    Severity: LOW ⚠️

    Code Gen:       More tests failing
                    Severity: CRITICAL 🔴

    Classification: 5% more wrong predictions
                    Severity: MEDIUM 🟠

Alert system treats them the same = BAD!
```

---

## Summary: All Four Issues at Once

```
┌─────────────────────────────────────────────────────────┐
│                    THEORY (Documented)                  │
│                                                         │
│  Capability = 1 - Risk          ← Complementary        │
│  Same metric, two representations                      │
│                                                         │
│  Zone Q2: SLM + Verify + Escalate   ← Fully defined   │
│  Implementation available                              │
│                                                         │
│  Risk has universal meaning across tasks ← Comparable │
│  All tasks use consistent risk computation             │
└─────────────────────────────────────────────────────────┘
                          ↕
                    MISMATCH ↕
                          ↕
┌─────────────────────────────────────────────────────────┐
│              CODE (Actual Implementation)                │
│                                                         │
│  Capability = Validity (structural)  ✗ NOT complementary
│  Risk = Quality (functional)                           │
│  They're independent measurements                      │
│                                                         │
│  Zone Q2: Returns "SLM_with_verification" string ✗    │
│  Not a real model, verification optional              │
│                                                         │
│  Risk computed 3 different ways ✗ NOT comparable      │
│  Different semantics across tasks                      │
└─────────────────────────────────────────────────────────┘

RESULT:
├─ Zone logic is mathematically unsound
├─ Q2 routing can't be implemented properly
├─ Risk metrics are confusing
└─ Monitoring alerts don't distinguish severity
```

---

## Severity Visualization

```
CRITICAL (Fix immediately):
║
╠══ ISSUE #1: Capability ≠ (1-Risk)
║   └─ Breaks zone classification logic entirely
║
╠══ ISSUE #2: Zone Q2 Missing
║   └─ Can't verify and escalate properly
║
╠══ ISSUE #3: Capability vs Validity
║   └─ Same sample counted opposite ways
║
╚════════════════════════════════════

HIGH (Fix soon):
║
╚══ ISSUE #4: Risk Variance
   └─ Monitoring alerts unreliable across tasks
```

---

**This visual summary can help you**:
1. Understand each issue independently
2. See how they interact
3. Explain them to others with diagrams
4. Remember the key examples

**Next**: Read CRITICAL_ISSUES_EXPLAINED.md for more detailed walkthroughs with code.
