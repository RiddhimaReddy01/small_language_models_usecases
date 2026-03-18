# Routing Policies for All Decision Zones

## Overview

The routing policy determines **which model to use** based on the task's zone and difficulty level.

---

## Zone 1: Pure SLM (High Capability, Low Risk)

```
Criteria: C_m(b) ≥ 0.80 for all b, Risk_m(b) ≤ 0.20 for all b
Examples: Classification, Retrieval, Instruction Following
```

### Routing Policy: SLM Always

```
For ANY input:
  IF task is in Zone 1:
    ROUTE TO SLM (Qwen, Phi-3, etc.)
    NO verification needed
    NO escalation possible
```

### Implementation

```python
def route_zone1(input_text, task):
    """Pure SLM routing"""

    # Always use SLM, no conditionals
    model = select_best_slm(task)  # e.g., Qwen (fastest)

    output = model.generate(input_text)

    return output  # No fallback, no checks
```

### Cost & Performance

```
Model:    Qwen (1.5B SLM)
Latency:  3-15 seconds
Memory:   ~2 GB
Cost:     ~$1/million tokens
Accuracy: 100% (same as Llama)
```

---

## Zone 2: SLM with Guardrails (High Capability, High Risk)

```
Criteria: C_m(b) ≥ 0.80 for all b, Risk_m(b) > 0.20 for some b
Meaning: Model is usually correct, but failures are costly
Examples: Code with 85% tests passing (15% fail = costly)
```

### Routing Policy: SLM + Verification + Escalation

```
For ANY input:
  1. ROUTE TO SLM
  2. VERIFY output
     IF verification_passes:
       RETURN output
     ELSE:
       ESCALATE TO LLM
  3. RETURN LLM output
```

### Implementation

```python
def route_zone2(input_text, task, model_m, model_llm):
    """SLM with guardrails and escalation"""

    # Step 1: Try SLM first (it usually works)
    slm_output = model_m.generate(input_text)

    # Step 2: Verify the output
    confidence = verify_output(slm_output, task)

    if confidence >= VERIFICATION_THRESHOLD:  # Default: 0.95
        # SLM passed verification
        return slm_output
    else:
        # Verification failed, escalate to LLM
        llm_output = model_llm.generate(input_text)
        return llm_output
```

### Verification Function (Task-Specific)

**For Code Generation:**
```python
def verify_output(code, task):
    """Run unit tests to verify code"""
    try:
        tests_passed = run_tests(code)
        if tests_passed == 100:
            return 1.0  # Perfect
        elif tests_passed >= 50:
            return 0.7  # Partially works
        else:
            return 0.0  # Broken
    except:
        return 0.0  # Syntax error
```

**For Text Generation:**
```python
def verify_output(text, task):
    """Check constraints satisfaction"""
    constraints = get_constraints(task)
    satisfied = count_satisfied_constraints(text, constraints)
    confidence = satisfied / len(constraints)
    return confidence  # e.g., 0.8 = 80% constraints satisfied
```

**For Classification:**
```python
def verify_output(prediction, task):
    """Check confidence score"""
    if prediction_confidence >= 0.95:
        return 1.0  # High confidence
    elif prediction_confidence >= 0.70:
        return 0.5  # Medium confidence, risky
    else:
        return 0.0  # Low confidence, escalate
```

### Cost & Performance

```
Scenario 1: SLM passes verification (80% of cases)
  Model:    Qwen (1.5B)
  Latency:  3-15 seconds
  Cost:     ~$1/million tokens

Scenario 2: SLM fails verification (20% of cases)
  Model:    Llama (70B)
  Latency:  5-30 seconds
  Cost:     ~$20/million tokens

Overall Cost: 0.8 × $1 + 0.2 × $20 = $4.80/million tokens
Savings vs pure Llama: 76%
```

---

## Zone 3: Hybrid Routing (Low Capability, Low Risk)

```
Criteria: C_m(b) < 0.80 for some b, Risk_m(b) ≤ 0.20 for all b
Meaning: Model fails often, but failures are recoverable
Examples: Draft generation, summary feedback, preprocessing
```

### Routing Policy: SLM for Easy, LLM for Hard

**By Difficulty Bin:**

```
For input with difficulty d:
  1. COMPUTE bin b = discretize(d)
  2. IF b <= tau_cap:  (easy problems, model is capable)
       ROUTE TO SLM
       IF failure:
         Can be handled as draft/preprocessing
  3. IF b > tau_cap:   (hard problems, model struggles)
       ROUTE TO LLM
       Use LLM for guarantee
```

### Implementation

```python
def route_zone3(input_text, task, model_m, model_llm):
    """Hybrid routing based on difficulty tipping point"""

    # Step 1: Compute difficulty and bin
    difficulty = compute_difficulty(input_text, task)
    bin_id = int(difficulty * (NUM_BINS - 1))

    # Step 2: Get task's capability tipping point
    tau_cap = get_tipping_point(task, model_m)

    # Step 3: Route based on bin vs tipping point
    if bin_id <= tau_cap:
        # Easy enough for SLM
        output = model_m.generate(input_text)
        return output, "SLM"
    else:
        # Too hard for SLM, use LLM
        output = model_llm.generate(input_text)
        return output, "LLM"
```

### Tipping Point Decision

```
Example: Code Generation with Qwen (tau_cap = 2)

Bin 0 (easy):    67% accuracy → SLM OK
Bin 1 (med):     80% accuracy → SLM OK
Bin 2 (med+):    80% accuracy → SLM OK (last bin where tau_cap applies)
Bin 3 (hard):    67% accuracy → ESCALATE TO LLM
Bin 4 (vhard):   73% accuracy → ESCALATE TO LLM
```

### Use Cases

**When to Use Zone 3 Hybrid:**
1. **Draft Generation**: SLM generates draft for hard problems, human polishes
2. **Preprocessing**: SLM filters/cleans data, LLM for complex cases
3. **Search/Ranking**: SLM ranks candidates, LLM for final scoring
4. **Summarization**: SLM summarizes simple articles, LLM for complex ones

### Cost & Performance

```
Scenario A: Easy problem (40% of traffic)
  Model:    Qwen (1.5B)
  Latency:  3-15 seconds
  Cost:     ~$1/million tokens

Scenario B: Hard problem (60% of traffic)
  Model:    Llama (70B)
  Latency:  5-30 seconds
  Cost:     ~$20/million tokens

Overall Cost: 0.4 × $1 + 0.6 × $20 = $12.40/million tokens
Savings vs pure Llama: 38% (not as good as Zone 1/2, but accuracy better than SLM-only)
```

### Quality Degradation Handling

Since Risk is low, failures in Zone 3 are recoverable:

```python
def handle_zone3_failure(output, input_text, task):
    """Handle SLM failure gracefully"""

    # Option 1: Return as draft
    if task == "summarization":
        return {
            "summary": output,
            "quality": "draft",  # Mark as draft
            "needs_review": True
        }

    # Option 2: Escalate automatically
    if task == "preprocessing":
        if output_quality_score < DRAFT_THRESHOLD:
            output = llm_fallback(input_text)
        return output

    # Option 3: Notify user
    if task == "search_ranking":
        return {
            "results": output,
            "reliability": "low",  # Mark as uncertain
            "confidence": output_confidence_score
        }
```

---

## Zone 4: LLM Only (Low Capability, High Risk)

```
Criteria: C_m(b) < 0.80 for some b, Risk_m(b) > 0.20 for some b
Meaning: Model fails often AND failures are costly
Examples: Code generation, medical diagnosis, legal review
```

### Routing Policy: LLM Always, No Fallback

```
For ANY input:
  ROUTE TO LLM (Llama, Claude, etc.)
  NO SLM fallback
  NO hybrid routing
  Use LLM for safety guarantee
```

### Implementation

```python
def route_zone4(input_text, task, model_llm):
    """LLM-only routing, no SLM"""

    # Never use SLM for Zone 4 tasks
    # High risk + low capability = unacceptable

    output = model_llm.generate(input_text)

    return output  # LLM is the policy
```

### When Zone 4 Occurs

**Code Generation Example:**
```
Qwen: τ_cap = 2, τ_risk = 0
      - Capability: 67% (below 80%)
      - Risk: 33% (above 20%)
      - Both curves fail → Zone 4

Llama: τ_cap = 4, τ_risk = None
       - Capability: 87% (always good)
       - Risk: 13% (always safe)
       - Both curves succeed → Zone 1

Decision: Use Llama only for code generation
```

---

## Hybrid Routing Summary Table

| Zone | Criteria | Routing Policy | Use Case | Cost Ratio |
|------|----------|---|---|---|
| **1** | High Cap, Low Risk | SLM always | Classification, Retrieval | 1× (100% SLM) |
| **2** | High Cap, High Risk | SLM + verify + escalate | Code with tests, Critical output | ~5× (80% SLM, 20% LLM) |
| **3** | Low Cap, Low Risk | SLM for easy, LLM for hard | Drafts, Preprocessing | 6× (40% SLM, 60% LLM) |
| **4** | Low Cap, High Risk | LLM always | Code generation | 20× (100% LLM) |

---

## Detailed Zone 3 (Hybrid) Example: Code Generation

### Scenario: Using Qwen with Fallback to Llama

```python
class HybridRouter:
    def __init__(self):
        self.qwen = Model("qwen2.5:1.5b")
        self.llama = Model("llama-3.3-70b")

        # From analysis:
        # Qwen: tau_cap = 2, tau_risk = 0
        # Llama: tau_cap = 4, tau_risk = None

    def route(self, problem_statement):
        """Hybrid routing for code generation"""

        # Step 1: Assess difficulty
        difficulty = assess_complexity(problem_statement)
        # Returns: 0.0 (trivial) to 1.0 (extremely hard)

        bin_id = int(difficulty * 4)  # Map to bins 0-4

        # Step 2: Route based on tipping point
        if bin_id <= 2:  # tau_cap = 2
            # Easy-to-medium complexity: Qwen can handle
            code = self.qwen.generate(problem_statement)

            # Optional: Verify with tests
            if can_run_tests(problem_statement):
                tests_pass = run_tests(code)
                if tests_pass:
                    return code, "qwen"
                else:
                    # Tests failed, escalate
                    code = self.llama.generate(problem_statement)
                    return code, "llama_fallback"
            else:
                # No tests available, trust Qwen for easy problems
                return code, "qwen"
        else:
            # Hard complexity: Use Llama
            code = self.llama.generate(problem_statement)
            return code, "llama"

# Usage
router = HybridRouter()
code, source = router.route("Write a quicksort algorithm")
# Output: code from Qwen (easy), source = "qwen"

code, source = router.route("Implement a distributed consensus algorithm")
# Output: code from Llama (hard), source = "llama"
```

---

## Monitoring Hybrid Routing

```python
class HybridMonitor:
    def __init__(self):
        self.metrics = {
            "slm_used": 0,
            "llm_used": 0,
            "slm_successes": 0,
            "slm_failures": 0,
            "llm_successes": 0,
        }

    def log_result(self, source, success):
        """Track hybrid routing effectiveness"""
        if source == "qwen":
            self.metrics["slm_used"] += 1
            if success:
                self.metrics["slm_successes"] += 1
            else:
                self.metrics["slm_failures"] += 1
        elif source == "llama":
            self.metrics["llm_used"] += 1
            if success:
                self.metrics["llm_successes"] += 1

    def report(self):
        """Print routing statistics"""
        slm_rate = self.metrics["slm_used"] / (self.metrics["slm_used"] + self.metrics["llm_used"])
        slm_success = self.metrics["slm_successes"] / max(self.metrics["slm_used"], 1)

        print(f"SLM usage: {slm_rate:.1%}")
        print(f"SLM success rate: {slm_success:.1%}")
        print(f"Cost: {self.compute_cost():.2f}x vs pure LLM")
```

---

## Summary: When to Use Each Routing Policy

| Situation | Policy | Example |
|-----------|--------|---------|
| Safe task, all difficulties | **Zone 1: SLM Always** | Classification (100% acc, 0% risk) |
| Capable task, some risky outputs | **Zone 2: SLM+Verify+Escalate** | Code (85% pass, 15% failures are costly) |
| Weak task, failures recoverable | **Zone 3: SLM for Easy, LLM for Hard** | Draft generation, preprocessing |
| Weak task, failures very costly | **Zone 4: LLM Only** | Code generation (67% acc, 33% failures) |

**Key Decision: Use τ_cap (tipping point) to determine easy vs hard thresholds in hybrid routing.**
