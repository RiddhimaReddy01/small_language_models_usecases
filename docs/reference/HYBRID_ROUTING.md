# Hybrid Routing Quick Reference

## What is Hybrid Routing?

Hybrid routing = **Use different models for different difficulty levels**

- Easy problems → Fast SLM (Qwen, Phi-3)
- Hard problems → Powerful LLM (Llama)

---

## When to Use Hybrid?

**Zone 3**: Low Capability + Low Risk

```
Characteristics:
  ✓ Model fails often (< 80% accuracy)
  ✓ Failures don't matter much (< 20% risk)

Use cases:
  - Draft generation (human edits after)
  - Preprocessing (filtered/validated later)
  - Search ranking (suggestions, not critical)
  - Summarization feedback (user reviews)
```

---

## The Routing Decision

### Simple Rule: Use Tipping Point as Threshold

```
Step 1: Get model's τ_cap (capability tipping point)
        τ_cap = last bin where accuracy ≥ 80%

Step 2: Compute input difficulty → bin (0-4)

Step 3: Route based on comparison
        IF bin ≤ τ_cap:
            USE SLM (model is good here)
        ELSE:
            USE LLM (model struggles, use stronger model)
```

---

## Real Example: Code Generation with Qwen

```
Qwen's Capability Curve:
  Bin 0 (easy):    67% → BELOW 80%
  Bin 1 (medium):  80% → OK
  Bin 2 (med-hard):80% → OK (last bin ≥ 80%)
  Bin 3 (hard):    67% → BELOW 80%
  Bin 4 (vhard):   73% → BELOW 80%

τ_cap = 2 (last bin where Qwen achieves ≥ 80%)

Routing Rule:
  IF problem_difficulty_bin ≤ 2:
      USE QWEN (we're confident)
  ELSE:
      USE LLAMA (we need guarantees)
```

---

## Cost Breakdown

### Scenario: 60% of problems are hard, 40% are easy

```
Easy problems (bin ≤ 2):  40% of traffic
  Model: Qwen (1.5B)
  Cost: $1 per 1M tokens
  Latency: 5 seconds

Hard problems (bin > 2):  60% of traffic
  Model: Llama (70B)
  Cost: $20 per 1M tokens
  Latency: 20 seconds

Total Cost:
  0.4 × $1 + 0.6 × $20 = $12.40 per 1M tokens

Savings vs pure Llama: 38%
Quality gain vs pure Qwen: Higher accuracy on hard problems
```

---

## Implementation (Minimal Version)

```python
def hybrid_route(input_text, task):
    """Route to SLM or LLM based on difficulty"""

    # Get model's tipping point
    tau_cap = TIPPING_POINTS[task]['qwen']  # e.g., 2

    # Compute difficulty
    difficulty = estimate_difficulty(input_text)
    bin_id = int(difficulty * 4)  # Convert to bin 0-4

    # Route
    if bin_id <= tau_cap:
        # Easy: Use fast SLM
        model = qwen
    else:
        # Hard: Use powerful LLM
        model = llama

    return model.generate(input_text)
```

---

## Why Hybrid Works

### For Zone 3 Tasks (Low Cap, Low Risk):

**Problem with SLM-only:**
```
Qwen on hard problems: 67% accuracy
→ Fails 1/3 of the time
→ Unacceptable for critical tasks
```

**Problem with LLM-only:**
```
Always use Llama: Very expensive
→ $20 per 1M tokens
→ Overkill for easy problems where Qwen works fine
```

**Hybrid Solution:**
```
Easy problems → Qwen: 80% accuracy, cheap
Hard problems → Llama: 87% accuracy, expensive

Best of both:
  - Cost-effective overall
  - Good accuracy
  - Escalates when needed
```

---

## Decision Matrix: When NOT to Use Hybrid

```
Zone 1 (High Cap, Low Risk):
  ✗ Don't use hybrid (SLM always works)
  → Use: SLM for everything

Zone 2 (High Cap, High Risk):
  ✗ Don't use hybrid (use verify+escalate instead)
  → Use: SLM + verification + escalate

Zone 4 (Low Cap, High Risk):
  ✗ Don't use hybrid (failures are too costly)
  → Use: LLM always

Zone 3 (Low Cap, Low Risk):
  ✓ USE HYBRID (perfect use case)
  → Route: Easy→SLM, Hard→LLM using τ_cap
```

---

## Hybrid Routing Monitoring

```python
# Track how often we use each model
daily_stats = {
    'qwen_used': 100,      # 40% of traffic
    'qwen_successes': 80,  # 80% success rate
    'llama_used': 150,     # 60% of traffic
    'llama_successes': 150 # 100% success rate
}

# Alert if thresholds change
if estimated_tau_cap_new < tau_cap_old:
    print("WARNING: tau_cap shifted left")
    print("Model getting weaker, adjust hybrid threshold")
    # May need to shift more traffic from SLM to LLM
```

---

## One-Minute Summary

**Hybrid Routing for Zone 3:**

```
1. Compute τ_cap (tipping point) from model's capability curve

2. For each input:
   - Estimate difficulty → bin (0-4)
   - IF bin ≤ τ_cap: use SLM (fast, cheap)
   - IF bin > τ_cap: use LLM (slower, guaranteed)

3. Result: 40% of traffic on SLM, 60% on LLM
   Cost: ~6× cheaper than pure LLM
   Quality: Higher than SLM-only

4. Monitor: τ_cap may change over time
   Alert if it shifts left (model degrading)
```

---

## Files for Hybrid Routing

| File | Purpose |
|------|---------|
| `ROUTING_POLICIES.md` | Complete policy definitions |
| `ROUTING_DECISION_TREE.md` | Visual decision flow + code |
| `HYBRID_ROUTING_QUICK_REFERENCE.md` | This file |

**Key Insight**: Use τ_cap as the difficulty threshold that separates "SLM OK" from "Need LLM".
