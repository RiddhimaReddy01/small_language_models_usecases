# Routing Decision Tree: From Input to Model Selection

## Visual Decision Flow

```
INPUT: task + input_text
  |
  v
[Assess Task Zone]
  |
  +---> Zone 1: High Cap, Low Risk
  |       Decision: ROUTE TO SLM
  |       [SLM]
  |
  +---> Zone 2: High Cap, High Risk
  |       [Verify Output?]
  |       |
  |       +---> PASS --> [Return SLM Output]
  |       |
  |       +---> FAIL --> [Escalate to LLM] --> [Return LLM Output]
  |
  +---> Zone 3: Low Cap, Low Risk
  |       [Assess Difficulty]
  |       |
  |       +---> Easy (bin <= tau_cap)  --> [SLM]
  |       |
  |       +---> Hard (bin > tau_cap)   --> [LLM]
  |
  +---> Zone 4: Low Cap, High Risk
          Decision: ROUTE TO LLM
          [LLM]

OUTPUT: model response
```

---

## Decision Tree Implementation

```python
def intelligent_router(input_text, task):
    """
    Main routing function that selects SLM or LLM
    based on task zone and input difficulty
    """

    # Step 1: Get task metadata
    task_zone = get_task_zone(task)
    tau_cap, tau_risk = get_tipping_points(task)

    # Step 2: Route based on zone
    if task_zone == "Zone 1":
        return route_zone_1(input_text, task)

    elif task_zone == "Zone 2":
        return route_zone_2(input_text, task, tau_cap, tau_risk)

    elif task_zone == "Zone 3":
        return route_zone_3(input_text, task, tau_cap)

    elif task_zone == "Zone 4":
        return route_zone_4(input_text, task)


# ====== ZONE 1: Pure SLM ======
def route_zone_1(input_text, task):
    """
    High capability, low risk → Always use SLM
    """
    model = get_slm(task)
    output = model.generate(input_text)
    return output


# ====== ZONE 2: SLM with Guardrails ======
def route_zone_2(input_text, task, tau_cap, tau_risk):
    """
    High capability, high risk → Try SLM, verify, escalate if needed
    """
    slm = get_slm(task)
    llm = get_llm(task)

    # Try SLM first
    output = slm.generate(input_text)

    # Verify the output
    confidence = verify_output(output, task)

    if confidence >= 0.90:  # High confidence threshold
        return output  # SLM output is good
    else:
        output = llm.generate(input_text)  # Escalate to LLM
        return output


# ====== ZONE 3: Hybrid (SLM for Easy, LLM for Hard) ======
def route_zone_3(input_text, task, tau_cap):
    """
    Low capability, low risk → Use difficulty-based routing
    """
    # Compute difficulty
    difficulty = compute_difficulty(input_text, task)
    bin_id = int(difficulty * 4)  # Map to bins 0-4

    slm = get_slm(task)
    llm = get_llm(task)

    if bin_id <= tau_cap:
        # Easy problem: SLM can handle
        output = slm.generate(input_text)
    else:
        # Hard problem: Use LLM
        output = llm.generate(input_text)

    return output


# ====== ZONE 4: LLM Only ======
def route_zone_4(input_text, task):
    """
    Low capability, high risk → Always use LLM
    """
    model = get_llm(task)
    output = model.generate(input_text)
    return output
```

---

## Hybrid Routing (Zone 3) Decision Logic

```
Input: problem_statement
  |
  v
[Compute Difficulty: d = complexity(problem)]
  |
  v
[Map to Bin: b = int(d * 4)]
  |
  v
[Get tau_cap for model]
  |
  v
[Decision]
  |
  +---> IF b <= tau_cap:
  |       Model is CAPABLE on this difficulty
  |       Use SLM (fast, cheap)
  |
  |       Probability of success: high (>80%)
  |       If failure: acceptable (low risk)
  |
  +---> IF b > tau_cap:
          Model STRUGGLES on this difficulty
          Use LLM (slower, expensive)

          Ensures quality on hard problems

OUTPUT: either SLM or LLM result
```

---

## Example: Hybrid Code Generation

```
Task: code_generation
Tipping points: tau_cap = 2 (Qwen), tau_risk = 0

Problem 1: "Write a function to reverse a list"
  Difficulty: 0.2 (easy)
  Bin: 0
  Decision: 0 <= tau_cap(2) → USE QWEN
  ✓ Result: Fast, cheap, usually works

Problem 2: "Implement a distributed consensus algorithm"
  Difficulty: 0.85 (hard)
  Bin: 3
  Decision: 3 > tau_cap(2) → USE LLAMA
  ✓ Result: Slower, expensive, guaranteed to work

Problem 3: "Write a sorting function with custom comparator"
  Difficulty: 0.55 (medium)
  Bin: 2
  Decision: 2 <= tau_cap(2) → USE QWEN
  ✓ Result: Fast, cheap, should work
```

---

## Cost vs Quality Tradeoff

### Zone 1: Pure SLM
```
Cost:    [========] (lowest)
Quality: [========] (highest, SLM perfect)
Speed:   [========] (fastest)

Decision: Use SLM for all inputs
Example: Classification (all difficulties)
```

### Zone 2: SLM + Guardrails
```
Cost:    [=====   ] (low-medium, ~5× vs SLM)
Quality: [========] (highest, LLM fallback ensures quality)
Speed:   [=====   ] (fast most of time, slower on failures)

Decision: Try SLM, escalate on uncertainty
Example: Code with tests (can verify)
```

### Zone 3: Hybrid
```
Cost:    [======  ] (medium, ~6× vs SLM)
Quality: [===     ] (medium, SLM on easy, LLM on hard)
Speed:   [======  ] (mixed: fast on easy, slow on hard)

Decision: SLM for easy, LLM for hard
Example: Draft generation, preprocessing
```

### Zone 4: LLM Only
```
Cost:    [======================================] (highest)
Quality: [========] (highest, LLM always)
Speed:   [==      ] (slowest)

Decision: Use LLM for all inputs
Example: Code generation (risky from Bin 0)
```

---

## Monitoring & Alerting

```python
class RoutingMonitor:
    """Track routing decisions and alert on anomalies"""

    def should_alert(self, metrics):
        alerts = []

        # Alert 1: SLM failure rate too high
        if metrics['slm_failure_rate'] > 0.25:
            alerts.append("SLM failing too often, consider escalation")

        # Alert 2: Tipping point shifted
        if metrics['tau_cap_new'] < metrics['tau_cap_old']:
            alerts.append("Capability degrading, shift to LLM")

        # Alert 3: Risk increased
        if metrics['tau_risk_new'] < metrics['tau_risk_old']:
            alerts.append("Risk escalating, escalate to LLM")

        # Alert 4: Cost anomaly
        if metrics['cost_per_request'] > metrics['cost_threshold']:
            alerts.append("Unusual cost spike, check routing")

        return alerts


# Daily monitoring loop
def daily_routing_check():
    """
    Every morning:
    1. Recompute tipping points from yesterday's results
    2. Compare to baseline
    3. Alert if any degradation
    4. Update routing policy if needed
    """
    old_points = load_baseline_tipping_points()
    new_points = compute_tipping_points(yesterday_results)

    if new_points != old_points:
        send_alert(f"Tipping points changed: {new_points}")
        # May need to update Zone classifications
```

---

## Summary: Which Route to Choose

```
START HERE: Compute task zone from analysis

┌─────────────────────────────────────────────────┐
│          Zone Classification Result             │
└─────────────────────────────────────────────────┘
           |
           v
┌─────────────────────────────────────────────────┐
│ Zone 1: High Cap, Low Risk                      │
│ ✓ Safe from start                               │
│ → Decision: SLM always                          │
│ → Cost: 1× (baseline)                           │
│ → Examples: Classification, Retrieval           │
└─────────────────────────────────────────────────┘
           |
           v
┌─────────────────────────────────────────────────┐
│ Zone 2: High Cap, High Risk                     │
│ ✓ Can do it but failures costly                 │
│ → Decision: SLM + verify + escalate             │
│ → Cost: ~5× (occasional LLM)                    │
│ → Examples: Code (with tests)                   │
└─────────────────────────────────────────────────┘
           |
           v
┌─────────────────────────────────────────────────┐
│ Zone 3: Low Cap, Low Risk [HYBRID]              │
│ ⚠ Weak model, but failures OK                   │
│ → Decision: Easy→SLM, Hard→LLM                  │
│ → Cost: ~6× (majority LLM)                      │
│ → Examples: Drafts, Preprocessing               │
│ → Tipping point: Use tau_cap as threshold       │
└─────────────────────────────────────────────────┘
           |
           v
┌─────────────────────────────────────────────────┐
│ Zone 4: Low Cap, High Risk                      │
│ ✗ Never deploy SLM                              │
│ → Decision: LLM always                          │
│ → Cost: 20× (full LLM)                          │
│ → Examples: Code generation                     │
└─────────────────────────────────────────────────┘
```

**Key Insight**: Use **τ_cap (tipping point)** as the difficulty threshold for hybrid routing. Easy problems (bin ≤ τ_cap) go to SLM; hard problems (bin > τ_cap) go to LLM.
