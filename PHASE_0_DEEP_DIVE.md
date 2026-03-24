# PHASE 0 Deep Dive: One-Time Analysis

## The Input: 1000 Benchmark Samples

Before Phase 0 starts, we have **raw benchmark data**:
- 1000 code generation samples
- For each sample: (input prompt, SLM output, LLM output)
- Manual evaluation: did each output pass or fail?

```
Raw Benchmark Data (example 3 samples):

Sample 1:
  input: "Write a function to find the maximum element in a list"
  slm_output: "def max_elem(lst): return max(lst)"
  llm_output: "def find_max(lst): ... [detailed error handling] ..."
  slm_passed: YES (1)
  llm_passed: YES (1)

Sample 2:
  input: "Implement a concurrent hash map with thread-safe operations and custom collision resolution"
  slm_output: "... [confusing code that doesn't work] ..."
  llm_output: "... [correct, production-ready implementation] ..."
  slm_passed: NO (0)
  llm_passed: YES (1)

Sample 3:
  input: "Sort a list"
  slm_output: "sorted(lst)"
  llm_output: "sorted(lst)"
  slm_passed: YES (1)
  llm_passed: YES (1)

... [997 more samples] ...
```

---

## STEP 1: Normalize Data → Canonical Schema

**Goal**: Convert messy raw data into standardized format (SDDF)

### Before Normalization (Raw, unstructured):
```
Different task formats have different column names/structures:
  ├─ Code generation: {task_id, prompt, code_output, passed}
  ├─ Text summarization: {input_text, summary_pred, gold_summary, rouge_score > 0.3}
  ├─ Math problems: {problem, slm_answer, llm_answer, is_correct}
  └─ Classification: {text, prediction, label, accuracy}

All different! Can't compare directly.
```

### After Normalization (Canonical SDDF schema):
```
Standardized columns (all tasks use these):
  ├─ example_id: unique identifier
  ├─ raw_input: the prompt/problem/text (string)
  ├─ raw_output: model's response (string)
  ├─ valid: boolean (did it pass evaluation?)
  ├─ quality_score: 0.0-1.0 continuous score
  ├─ task: which task is this (code_generation, summarization, etc.)
  └─ model: which model produced this (qwen_1.5b, llama_70b)

Result: All 1000 samples now in same format
```

### Example After Normalization:
```
example_id | raw_input                              | raw_output            | valid | quality_score | task             | model
-----------|----------------------------------------|----------------------|-------|---------------|------------------|----------
1          | "Write a function to find max..."     | "def max_elem(lst)..." | 1     | 1.0           | code_generation  | qwen_1.5b
2          | "Implement concurrent hash map..."     | "... [bad code] ..."   | 0     | 0.1           | code_generation  | qwen_1.5b
3          | "Sort a list"                          | "sorted(lst)"          | 1     | 1.0           | code_generation  | qwen_1.5b
...

Now all 1000 samples are in SDDF format and comparable!
```

---

## STEP 2: Compute 6D Difficulty Vector

**Goal**: For each sample, create a 6-dimensional difficulty score

The difficulty vector has 6 components:

### Component 1: n_in (Input Complexity)
```
How much text does the model need to read and understand?
Formula: normalized input length

Example:
  "Sort a list"
  → length = 12 chars
  → normalized = 12 / 1000 = 0.012
  → n_in = 0.012

  "Implement a concurrent hash map with thread-safe operations
   and custom collision resolution strategy for distributed systems"
  → length = 145 chars
  → normalized = 145 / 1000 = 0.145
  → n_in = 0.145
```

### Component 2: H (Vocabulary Entropy)
```
How many unique, complex words? (ambiguity measure)

Example:
  "Sort a list"
  → words: [sort, a, list] = 3 unique words
  → word complexity: common words
  → entropy H ≈ 0.1 (very simple)

  "Implement concurrent hash map with thread-safe operations"
  → words: [implement, concurrent, hash, map, thread, safe, operations]
  → word complexity: specialized terms
  → entropy H ≈ 0.7 (complex vocabulary)
```

### Component 3: R̂ (Reasoning Required)
```
How much algorithmic/logical reasoning is needed?

Example:
  "Sort a list"
  → Just call built-in function
  → Reasoning = 0.1 (minimal)

  "Implement concurrent hash map"
  → Need to understand: hashing, collision resolution, thread safety
  → Reasoning = 0.8 (substantial)
```

### Component 4: |Γ| (Constraint Count)
```
How many restrictions/requirements?

Example:
  "Sort a list"
  → 0 constraints (do it however you want)
  → |Γ| = 0

  "Implement a concurrent hash map
   - Must be thread-safe
   - O(1) average lookup
   - Handle 1M+ elements
   - Memory efficient"
  → 4 constraints
  → |Γ| = 4
```

### Component 5: α (Style/Content Sensitivity)
```
How sensitive to formatting, style, or content filtering?

Example:
  "Sort a list"
  → No style requirements
  → No content sensitivity
  → α = 0.1

  "Write code that handles hate speech filtering"
  → Must be politically correct
  → Content sensitivity critical
  → α = 0.9
```

### Component 6: D (Output Diversity)
```
How many valid correct answers are there?

Example:
  "Sort a list"
  → Many valid implementations: sorted(), manual sort, numpy, etc.
  → Diversity D = 0.9 (many valid answers)

  "Implement quicksort"
  → Specific algorithm required, less variation
  → Diversity D = 0.3 (fewer valid answers)
```

### Combining into Single Difficulty Score:

```
SDDF Framework uses a WEIGHTED COMBINATION:

difficulty_score = w1*n_in + w2*H + w3*R̂ + w4*|Γ| + w5*α + w6*D

Typical weights (task-dependent):
  ├─ w1 = 0.1 (input length, minor impact)
  ├─ w2 = 0.15 (vocabulary, moderate)
  ├─ w3 = 0.35 (reasoning, major!)
  ├─ w4 = 0.15 (constraints, moderate)
  ├─ w5 = 0.15 (style sensitivity, moderate)
  └─ w6 = 0.1 (diversity, minor)

Example 1: "Sort a list"
  difficulty = 0.1*(0.012) + 0.15*(0.1) + 0.35*(0.1) + 0.15*(0) + 0.15*(0.1) + 0.1*(0.9)
             = 0.0012 + 0.015 + 0.035 + 0 + 0.015 + 0.09
             = 0.156 ≈ 0.16 (EASY)

Example 2: "Implement concurrent hash map"
  difficulty = 0.1*(0.145) + 0.15*(0.7) + 0.35*(0.8) + 0.15*(4) + 0.15*(0.9) + 0.1*(0.3)
             = 0.0145 + 0.105 + 0.28 + 0.6 + 0.135 + 0.03
             = 1.164 → clamped to 1.0 (VERY HARD)
```

### After Step 2: Each sample now has 6D vector + combined score

```
example_id | raw_input                    | difficulty_score | n_in  | H    | R    | |Γ| | α   | D
-----------|------------------------------|-----------------|-------|------|------|-----|-----|-----
1          | "Sort a list"                | 0.16            | 0.012 | 0.1  | 0.1 | 0   | 0.1 | 0.9
2          | "Concurrent hash map..."     | 0.95            | 0.145 | 0.7  | 0.8 | 4   | 0.9 | 0.3
3          | "Binary search implementation"| 0.38            | 0.055 | 0.2  | 0.4 | 1   | 0.1 | 0.8
...

Now we have difficulty scores for all 1000 samples!
```

---

## STEP 3: Bin Samples into 5 Difficulty Buckets

**Goal**: Group similar-difficulty samples together

### Binning Formula:
```
Probabilistic binning with linear interpolation

For each sample with difficulty_score D:
  1. Map to continuous position: pos = D × (num_bins - 1)
  2. Compute probabilities between nearest bins
  3. Assign to bin with highest probability (argmax)

Example with 5 bins (0-4):

If D = 0.16 (easy):
  pos = 0.16 × 4 = 0.64
  lower_bin = 0, upper_bin = 1
  fraction = 0.64
  probabilities = {0: 0.36, 1: 0.64, 2: 0, 3: 0, 4: 0}
  argmax = bin 1 (0.64 probability)
  → Assign to BIN 1

If D = 0.95 (very hard):
  pos = 0.95 × 4 = 3.8
  lower_bin = 3, upper_bin = 4
  fraction = 0.8
  probabilities = {0: 0, 1: 0, 2: 0, 3: 0.2, 4: 0.8}
  argmax = bin 4 (0.8 probability)
  → Assign to BIN 4

If D = 0.38 (medium):
  pos = 0.38 × 4 = 1.52
  lower_bin = 1, upper_bin = 2
  fraction = 0.52
  probabilities = {0: 0, 1: 0.48, 2: 0.52, 3: 0, 4: 0}
  argmax = bin 2 (0.52 probability)
  → Assign to BIN 2
```

### After Step 3: Samples grouped into 5 bins

```
BIN 0 (very easy):     120 samples with difficulty ≤ 0.125
BIN 1 (easy):          250 samples with difficulty 0.125-0.375
BIN 2 (medium):        280 samples with difficulty 0.375-0.625
BIN 3 (hard):          220 samples with difficulty 0.625-0.875
BIN 4 (very hard):     130 samples with difficulty > 0.875

Total: 1000 samples ✓
```

---

## STEP 4: Calculate Capability Curve

**Goal**: For each bin, compute "What % of SLM outputs passed?"

### From Raw Data to Counts:

```
For each bin, count successes:

BIN 0 (120 samples):
  ├─ SLM passed: 114
  ├─ SLM failed: 6
  └─ Capability = 114/120 = 0.95 (95% success)

BIN 1 (250 samples):
  ├─ SLM passed: 210
  ├─ SLM failed: 40
  └─ Capability = 210/250 = 0.84 (84% success)

BIN 2 (280 samples):
  ├─ SLM passed: 168
  ├─ SLM failed: 112
  └─ Capability = 168/280 = 0.60 (60% success)

BIN 3 (220 samples):
  ├─ SLM passed: 66
  ├─ SLM failed: 154
  └─ Capability = 66/220 = 0.30 (30% success)

BIN 4 (130 samples):
  ├─ SLM passed: 13
  ├─ SLM failed: 117
  └─ Capability = 13/130 = 0.10 (10% success)
```

### Result: Capability Curve

```
       CAPABILITY CURVE
       (% of SLM outputs that work)

100% ████
 90% ████
 80% ████
 70% ████
 60% ████
 50% ████  ██
 40% ████  ██
 30% ████  ██  ██
 20% ████  ██  ██  ██
 10% ████  ██  ██  ██  ██
  0% ─────────────────────
     B0  B1 B2  B3 B4
    easy        hard

Data points:
  B0: 95%
  B1: 84%
  B2: 60%
  B3: 30%
  B4: 10%

KEY INSIGHT:
  SLM works great on easy tasks (95%)
  SLM fails badly on hard tasks (10%)
```

---

## STEP 5: Calculate Risk Curve

**Goal**: For each bin, compute "What % of SLM outputs are DANGEROUSLY BAD?"

"Dangerously bad" = semantic failures (produces harmful/wrong output):
- Code that crashes
- Code with security vulnerabilities
- Mathematically incorrect logic
- Misleading information

### From Raw Data to Counts:

```
For each bin, count dangerous failures:

BIN 0 (120 samples):
  ├─ Dangerous failures: 1
  └─ Risk = 1/120 = 0.008 (0.8% are dangerous)

BIN 1 (250 samples):
  ├─ Dangerous failures: 8
  └─ Risk = 8/250 = 0.032 (3.2% are dangerous)

BIN 2 (280 samples):
  ├─ Dangerous failures: 28
  └─ Risk = 28/280 = 0.10 (10% are dangerous)

BIN 3 (220 samples):
  ├─ Dangerous failures: 55
  └─ Risk = 55/220 = 0.25 (25% are dangerous)

BIN 4 (130 samples):
  ├─ Dangerous failures: 78
  └─ Risk = 78/130 = 0.60 (60% are dangerous!)
```

### Result: Risk Curve

```
         RISK CURVE
    (% of outputs that are dangerously bad)

100%
 90%
 80%
 70%
 60%                              ██
 50%                           ██
 40%                        ██
 30%                     ██
 20%                  ██
 10%              ██
  0% ────────────────────────────
     B0  B1  B2  B3  B4
    easy           hard

Data points:
  B0: 0.8%
  B1: 3.2%
  B2: 10%
  B3: 25%
  B4: 60%

KEY INSIGHT:
  Easy tasks: almost no dangerous outputs
  Hard tasks: VERY risky (60% of outputs are bad)
```

---

## STEP 6: Find τ_cap (Capability Tipping Point)

**Goal**: Find the last bin where SLM is "good enough"

### Decision Rule:
```
τ_cap = Last bin where capability >= threshold

Common thresholds:
  ├─ Conservative: >= 0.90 (very strict)
  ├─ Moderate: >= 0.80 (balanced)
  └─ Aggressive: >= 0.70 (trust SLM more)

In this example, threshold = 0.80 (moderate)
```

### Finding τ_cap:
```
Check each bin:
  B0: 95% >= 80%? YES ✓
  B1: 84% >= 80%? YES ✓
  B2: 60% >= 80%? NO ✗
  B3: 30% >= 80%? NO ✗
  B4: 10% >= 80%? NO ✗

τ_cap = 1 (last bin where capability >= 80%)

Interpretation:
  "SLM is CAPABLE up to bin 1 (easy tasks)"
  "At bin 2 (medium), SLM loses capability"
```

---

## STEP 7: Find τ_risk (Risk Tipping Point)

**Goal**: Find the first bin where outputs become dangerously risky

### Decision Rule:
```
τ_risk = First bin where risk > threshold

Common thresholds:
  ├─ Conservative: > 0.05 (5% risk too much)
  ├─ Moderate: > 0.15 (15% risk acceptable)
  └─ Aggressive: > 0.30 (30% risk tolerable)

In this example, threshold = 0.15 (moderate)
```

### Finding τ_risk:
```
Check each bin:
  B0: 0.8% > 15%? NO ✓
  B1: 3.2% > 15%? NO ✓
  B2: 10% > 15%? NO ✓
  B3: 25% > 15%? YES ✗
  B4: 60% > 15%? YES ✗

τ_risk = 3 (first bin where risk > 15%)

Interpretation:
  "Outputs are SAFE up to bin 2"
  "At bin 3, risk becomes unacceptable"
```

---

## STEP 8: Create 2×2 Quadrant Decision Matrix

**Goal**: Combine τ_cap and τ_risk into routing decisions

### The Decision Matrix:

```
             Capable? (≤ τ_cap)    Incapable (> τ_cap)
Safe? (≤ τ_risk)    Q1                Q3
Risky (> τ_risk)    Q2                Q4

With our values (τ_cap = 1, τ_risk = 3):

         Capable (B0-1)    Incapable (B2-4)
Safe (B0-2)    Q1              Q3
Risky (B3-4)   Q2              Q4
```

### Assigning Bins to Quadrants:

```
BIN 0:
  ├─ Capability: 95% (capable, <= τ_cap=1) ✓
  ├─ Risk: 0.8% (safe, <= τ_risk=3) ✓
  └─ QUADRANT: Q1

BIN 1:
  ├─ Capability: 84% (capable, <= τ_cap=1) ✓
  ├─ Risk: 3.2% (safe, <= τ_risk=3) ✓
  └─ QUADRANT: Q1

BIN 2:
  ├─ Capability: 60% (incapable, > τ_cap=1) ✗
  ├─ Risk: 10% (safe, <= τ_risk=3) ✓
  └─ QUADRANT: Q3

BIN 3:
  ├─ Capability: 30% (incapable, > τ_cap=1) ✗
  ├─ Risk: 25% (risky, > τ_risk=3) ✗
  └─ QUADRANT: Q4

BIN 4:
  ├─ Capability: 10% (incapable, > τ_cap=1) ✗
  ├─ Risk: 60% (risky, > τ_risk=3) ✗
  └─ QUADRANT: Q4
```

### Quadrant Interpretations:

```
Q1 (Capable & Safe):
  ├─ Bins: 0, 1
  ├─ Meaning: SLM can solve AND outputs are safe
  └─ Strategy: USE SLM DIRECTLY (no verification needed)

Q2 (Capable but Risky):
  ├─ Bins: (none in this example)
  ├─ Meaning: SLM can solve BUT outputs sometimes bad
  └─ Strategy: USE SLM + VERIFY (check before deploying)

Q3 (Incapable but Safe):
  ├─ Bins: 2
  ├─ Meaning: SLM can't solve BUT wrong answers aren't dangerous
  └─ Strategy: USE HYBRID (SLM first, escalate if confidence low)

Q4 (Incapable & Risky):
  ├─ Bins: 3, 4
  ├─ Meaning: SLM fails AND failures are dangerous
  └─ Strategy: USE LLM (don't risk SLM)
```

---

## STEP 8b: Final Frozen Policy

**Goal**: Write the routing decision as a production-ready policy file

### Policy File (JSON):

```json
{
  "task": "code_generation",
  "model": "qwen_1.5b",
  "analysis_date": "2024-03-21",
  "capability_threshold": 0.80,
  "risk_threshold": 0.15,
  "num_bins": 5,

  "curves": {
    "capability": {
      "bin_0": 0.95,
      "bin_1": 0.84,
      "bin_2": 0.60,
      "bin_3": 0.30,
      "bin_4": 0.10
    },
    "risk": {
      "bin_0": 0.008,
      "bin_1": 0.032,
      "bin_2": 0.10,
      "bin_3": 0.25,
      "bin_4": 0.60
    }
  },

  "tipping_points": {
    "tau_cap": 1,
    "tau_risk": 3
  },

  "quadrants": {
    "Q1": {
      "bins": [0, 1],
      "meaning": "Capable & Safe",
      "strategy": "use_slm_directly",
      "sample_count": 370
    },
    "Q2": {
      "bins": [],
      "meaning": "Capable but Risky",
      "strategy": "use_slm_with_verification",
      "sample_count": 0
    },
    "Q3": {
      "bins": [2],
      "meaning": "Incapable but Safe",
      "strategy": "use_hybrid",
      "sample_count": 280
    },
    "Q4": {
      "bins": [3, 4],
      "meaning": "Incapable & Risky",
      "strategy": "use_llm",
      "sample_count": 350
    }
  },

  "routing_decisions": {
    "bin_0": "use_slm_directly",
    "bin_1": "use_slm_directly",
    "bin_2": "use_hybrid",
    "bin_3": "use_llm",
    "bin_4": "use_llm"
  }
}
```

### What This Policy Means:

```
When a request comes in (Phase 1):
  1. Compute difficulty
  2. Assign to bin (0-4)
  3. Look up bin in this policy file
  4. Apply the associated strategy

Examples:

  Request: "Sort a list" (difficulty 0.16)
    ├─ Assign to bin: 1
    ├─ Look up: routing_decisions["bin_1"]
    ├─ Get: "use_slm_directly"
    └─ Action: Send to SLM (fast, cheap)

  Request: "Concurrent hash map" (difficulty 0.95)
    ├─ Assign to bin: 4
    ├─ Look up: routing_decisions["bin_4"]
    ├─ Get: "use_llm"
    └─ Action: Send to LLM (accurate, expensive)

  Request: "Binary search" (difficulty 0.38)
    ├─ Assign to bin: 2
    ├─ Look up: routing_decisions["bin_2"]
    ├─ Get: "use_hybrid"
    └─ Action: Try SLM first, verify or escalate if needed
```

---

## Summary: What Phase 0 Produces

```
INPUT:
  1000 benchmark samples (raw outputs from both models)

PROCESSING:
  1. Normalize → standardized schema
  2. Compute → 6D difficulty vector per sample
  3. Bin → group by difficulty (5 buckets)
  4. Calculate → capability curve (success % per bin)
  5. Calculate → risk curve (dangerous failures % per bin)
  6. Find → τ_cap (last capable bin)
  7. Find → τ_risk (first risky bin)
  8. Create → quadrant matrix (Q1/Q2/Q3/Q4 routing)

OUTPUT:
  Frozen policy file (JSON)

  ├─ Capability curve data
  ├─ Risk curve data
  ├─ Tipping points (τ_cap, τ_risk)
  └─ Routing decisions per bin (bin_0→bin_4)

PROPERTIES:
  ✓ Frozen (won't change after Phase 0 completes)
  ✓ Production-ready (safe to deploy)
  ✓ O(1) lookup (fast in Phase 1)
  ✓ Data-driven (based on real benchmarks)

RESULT:
  A routing policy that says:
  "Easy tasks (bins 0-1) → use SLM"
  "Medium tasks (bin 2) → use hybrid"
  "Hard tasks (bins 3-4) → use LLM"
```

---

## Why This Approach Works

### 1. **Data-Driven**: Not guessing, based on actual benchmarks
```
We measured SLM on 1000 real samples
We know exactly where it succeeds (95% at easy)
We know exactly where it fails (10% at hard)
```

### 2. **Two-Dimensional Thinking**: Separates capability from risk
```
NOT: "Just use SLM where success % is high"

BUT: "Use SLM where it's both capable AND safe"

Example: Bin 2 might be 60% successful but 10% dangerous
  → Don't use directly, hybrid approach better
```

### 3. **Frozen Policy**: Learned once, used forever
```
Phase 0: Expensive analysis (10 minutes)
Phase 1: Cheap lookups (1 millisecond)

Total savings by separating offline/online work!
```

### 4. **Adaptive Routing**: Different strategies per zone
```
Q1: Direct use (trust SLM)
Q2: Verification (double-check)
Q3: Hybrid (fallback to LLM)
Q4: LLM only (SLM not reliable)
```

---

## Real Impact

```
Benchmark results (1000 samples):

Cost if always using LLM:
  1000 samples × $0.01 = $10

Cost with routing policy:
  370 samples (Q1) → SLM: $0.37
  280 samples (Q3) → Hybrid: $2
  350 samples (Q4) → LLM: $3.50
  Total: $5.87

SAVINGS: 41% cost reduction!

Quality maintained:
  Q1: 95% success (trust SLM) ✓
  Q2: verify outputs ✓
  Q3: hybrid approach ✓
  Q4: use LLM ✓
```
