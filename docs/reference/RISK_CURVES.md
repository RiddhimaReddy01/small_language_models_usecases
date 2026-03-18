# Risk Curves: Visual Guide

## Mathematical Foundation

```
Risk_m(b) = P̂_m(fail|b) = # failures in bin b / # samples in bin b

Capability_m(b) = C_m(b) = 1 - Risk_m(b)
```

Where:
- `m` = model (qwen, phi3, llama, tinyllama)
- `b` = difficulty bin (0=easy, 4=hard)
- "failure" = primary_metric < quality_threshold

---

## What The Risk Curve Looks Like

### Example 1: Safe Task (Classification)

```
Risk Curve:
100% |
     |
 80% |
     |
 60% |
     |
 40% |
     |
 20% |  ___________  <- All models: ~0% risk
     | /
  0% |________________
     0   1   2   3   4  (difficulty bin)

Interpretation:
- All models have ~0% failure rate across all difficulties
- Always safe, no matter difficulty
- Zone 1: Pure SLM deployment
```

### Example 2: Unsafe Task (Code Generation - SLM)

```
Risk Curve (Qwen):
100% |
     |
 80% |  /\
     | /  \___
 60% |/
     |
 40% |
     |
 20% | ___________  <- Threshold τ_R = 20%
     |/
  0% |________________
     0   1   2   3   4  (difficulty bin)

Interpretation:
- Starts at ~33% risk on easy problems (Bin 0)
- Immediately above safety threshold
- Zone 4: Route to stronger model (LLM only)
```

### Example 3: Degrading Performance (Code - Phi-3)

```
Risk Curve (Phi-3):
100% |
     |
 80% |
     |
 60% |
     |
 40% |           /
     |         /
 20% | _______/___  <- Threshold τ_R = 20%
     |
  0% |________________
     0   1   2   3   4  (difficulty bin)

Interpretation:
- Safe on easy problems (Bin 0: ~19% risk, just below threshold)
- Becomes unsafe on harder problems (Bin 3+: > 20%)
- Tipping point: τ_risk = 2 or 3
- Zone 4: Still LLM only (unsafe from start)
```

---

## 2x2 Decision Matrix

### The Four Zones

```
               CAPABILITY (C_m)
                   0.8
                    |
                    |
        Zone 1      |      Zone 2
      Pure SLM      |    SLM+Guards
       (Safe)       |     (Risky)
                    |
   ────────────────────────────────
                    |
        Zone 3      |      Zone 4
      SLM Draft     |   Stronger Model
      (Weak)        |     (Unsafe)
                    |
                    +────────────
                    0.2
                 RISK (R_m)
```

### Zone 1: High Capability, Low Risk
```
C_m(b) >= 0.80, R_m(b) <= 0.20

Characteristics:
- Model succeeds on most inputs
- Failures are rare
- Safe to deploy SLM

Examples:
- Classification: 100% accuracy, 0% risk
- Text generation: 90% constraint satisfaction, 5% risk
- Maths: 95% correct, 0% risk

Decision: DEPLOY SLM (pure, no guardrails)
Benefit: 10-97% cost savings
```

### Zone 2: High Capability, High Risk
```
C_m(b) >= 0.80, R_m(b) > 0.20

Characteristics:
- Model usually works (>80% success)
- But failures are severe / costly
- Failures impact operations

Examples:
- Code: 85% tests pass, but 30% of failures are syntax errors
- Finance: 90% correct, but errors cost real money

Decision: SLM WITH GUARDRAILS
Actions:
- Add verification layer
- Human review on high-cost outputs
- Real-time quality checks
- Escalation to LLM on uncertainty
```

### Zone 3: Low Capability, Low Risk
```
C_m(b) < 0.80, R_m(b) <= 0.20

Characteristics:
- Model fails often (< 80% success)
- But failures are recoverable
- Low cost when it fails

Examples:
- Draft generation: 70% acceptable, 15% risk (typos recoverable)
- Summarization with weak SLM: 75% good, 10% risk (human edit acceptable)

Decision: SLM FOR LOW-STAKES USE
Use cases:
- Draft generation (human edits)
- Preprocessing (filtered later)
- Cache/suggestion layer
- Not for final production
```

### Zone 4: Low Capability, High Risk
```
C_m(b) < 0.80, R_m(b) > 0.20

Characteristics:
- Model fails often (< 80% success)
- AND failures are severe / costly
- Unacceptable combination

Examples:
- Code generation: 67% tests pass, 33% failures are syntax errors
- Medical diagnosis: 75% accurate, 25% misdiagnosis risk

Decision: ROUTE TO STRONGER MODEL
Actions:
- Use LLM (larger model)
- Hybrid routing: SLM on easy, LLM on hard
- Human-in-the-loop
- Fine-tune SLM (long term)

Cost: Higher, but necessary for safety
```

---

## Reading the Curves: Example Tasks

### Text Generation (Q1: Pure SLM)

```
RISK CURVE:
Risk (%)
    |
 10 |    Qwen        Phi-3
    |     /\          /\
  5 |    /  \___     /  \___
    |___/          \__/
    0 |________________
      0   1   2   3   4

CAPABILITY CURVE:
Cap (%)
    |
100 | Qwen, Phi-3, Llama
    |_____________________
 80 |
    |
    0   1   2   3   4

ZONES:
- All models: ~100% capability, ~0-5% risk
- Zone 1 for all models
- Decision: Deploy Qwen (fastest SLM)
```

### Code Generation (Q4: LLM Only)

```
RISK CURVE:
Risk (%)
    |
 50 | TinyLlama  /
    |    /\     /
 33 | Qwen \/\  /
    |/   \/ \ \/
 19 | Phi-3  \Llama
    |__________|_____ (threshold 20%)
    0   1   2   3   4

CAPABILITY CURVE:
Cap (%)
    |
100 |    Llama
    |
 87 |____________
    |
 81 | Phi-3______
    |
 67 |Qwen_____
    |
    0   1   2   3   4

ZONES:
- Qwen: 67% cap, 33% risk → Zone 4
- Phi-3: 81% cap, 19% risk → Zone 4 (barely, risk at 0)
- TinyLlama: 68% cap, 32% risk → Zone 4
- Llama: 87% cap, 13% risk → Zone 1

Decision: Use Llama only (mandatory)
Why: Even Phi-3 (best SLM) fails at Bin 0
```

### Classification (Q1: Safe)

```
RISK CURVE:
Risk (%)
    |
  1 |
    |  TinyLlama (tiny spike)
  0 |___________________
    0   1   2   3   4

CAPABILITY CURVE:
Cap (%)
    |
100 |____________________ (all models perfect)
    |
    0   1   2   3   4

ZONES:
- All models: 100% cap, 0% risk
- Zone 1 for all

Decision: Deploy Qwen (fastest, same accuracy as Llama)
```

---

## How to Interpret the Curves

### Step 1: Look at Risk Curve

```
IF: Risk stays below 20% threshold
    → Model is operationally safe

IF: Risk rises above 20% threshold
    → Model enters danger zone
    → τ_risk = first bin where risk > 20%
```

### Step 2: Look at Capability Curve

```
IF: Capability stays above 80% threshold
    → Model is capable
    → τ_cap = last bin where capability >= 80%

IF: Capability drops below 80%
    → Model losing competence
    → Can't handle harder problems
```

### Step 3: Combine into Zone

```
CAPABILITY HIGH (≥ 80%)  +  RISK LOW (≤ 20%)     → Zone 1: SLM OK
CAPABILITY HIGH (≥ 80%)  +  RISK HIGH (> 20%)    → Zone 2: SLM + Guards
CAPABILITY LOW (< 80%)   +  RISK LOW (≤ 20%)     → Zone 3: SLM Draft
CAPABILITY LOW (< 80%)   +  RISK HIGH (> 20%)    → Zone 4: LLM Only
```

---

## Key Patterns

### Pattern 1: Always Safe
```
Risk: ___________ (flat at 0%)
Cap:  ___________ (flat at 100%)
Decision: Zone 1 - Pure SLM
Examples: Classification, Maths (for small models)
```

### Pattern 2: Degrades with Difficulty
```
Risk:  ___/   (starts low, rises)
Cap:  ___\    (starts high, drops)
Tipping points: τ_cap and τ_risk
Decision: Depends on where they cross thresholds
```

### Pattern 3: Always Risky
```
Risk: /\__/\ (elevated throughout)
Cap:  __\  (often drops below 80%)
Decision: Zone 4 - Need stronger model
Examples: Code generation with SLMs
```

### Pattern 4: Risky but Capable
```
Risk: ___/\_ (crosses threshold on hard)
Cap:  _____ (stays above 80%)
Decision: Zone 2 - SLM with guardrails
```

---

## Computing Risk for Your Tasks

```python
# For each task/model/bin:

failures = count where primary_metric < quality_threshold
total = number of samples in bin

Risk_m(b) = failures / total

# Example: Text Generation, Qwen, Bin 0
primary_metrics = [0.95, 0.72, 0.88, 0.45, 0.91, ...]  # 100 samples
threshold = 0.80

failures = count(pm < 0.80) = 2  # samples with 0.72 and 0.45
Risk = 2 / 100 = 0.02 = 2%

Capability = 1 - Risk = 98%
```

---

## Summary: Risk Curves Show

✓ **Where model succeeds**: low risk, high capability
✓ **Where model struggles**: drops in capability
✓ **Where model breaks**: crosses risk threshold
✓ **When to use SLM**: Zone 1 (low risk, high cap)
✓ **When to use LLM**: Zone 4 (high risk or low cap)
✓ **When to add guardrails**: Zone 2 (capable but risky)
✓ **When to use for drafts**: Zone 3 (weak but safe)

All from one simple formula: `Risk = # failures / # samples`
