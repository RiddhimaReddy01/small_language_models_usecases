# Deployment Decision Matrix

## Multi-Dimensional Routing Framework

**Input Dimensions**:
1. **Task** (what operation: code_gen, classification, etc.)
2. **Difficulty Bin** (query complexity: 0=easy → 4=hard)
3. **Performance Metric** (accuracy, latency, memory)

**Output**: Routing decision (SLM vs LLM) + confidence

---

## Quick Reference: Routing by Task

| Task | Bin 0 | Bin 1 | Bin 2 | Bin 3 | Bin 4 | Best SLM |
|------|-------|-------|-------|-------|-------|----------|
| **text_generation** | Qwen | Qwen | Qwen | Phi-3 | Qwen | Qwen (9.2s) |
| **code_generation** | Llama | Llama | Llama | Llama | Llama | None (use Llama) |
| **classification** | Phi-3 | Phi-3 | Qwen | Qwen | Qwen | Qwen |
| **maths** | Qwen | Qwen | Qwen | Phi-3 | Phi-3 | Qwen (100%) |
| **summarization** | Phi-3 | Phi-3 | Phi-3 | Phi-3 | Phi-3 | Phi-3 (S=0.755) |
| **retrieval_qa** | Phi-3 | Phi-3 | Phi-3 | Phi-3 | Phi-3 | Phi-3 (Cov=0.89) |
| **instruction** | Qwen | Qwen | Qwen | Qwen | Qwen | Qwen |
| **info_extract** | Qwen | Qwen | Qwen | Qwen | Qwen | Qwen (2.4s) |

---

## Detailed Routing Logic

### TEXT_GENERATION
```
IF accuracy < 95%:
  USE Llama
ELSE IF latency > 20s:
  USE Qwen (9.2s, 100% accuracy)
ELSE:
  USE Phi-3 (17.2s, 100% accuracy)
```
**Rationale**: All accurate, choose by latency
**Confidence**: HIGH (no tipping point)

---

### CODE_GENERATION ⚠️ CRITICAL
```
USE Llama (mandatory)

# ALL SLMs fail at Bin 0:
# - Phi-3:    81.2% vs Llama 86.7%  (UNSAFE)
# - Qwen:     66.7% vs Llama 86.7%  (UNSAFE)
# - TinyLlama: 68.3% vs Llama 86.7% (UNSAFE)

# No SLM acceptable for production code
# Syntax/logic errors unrecoverable
```
**Rationale**: Syntax correctness is non-negotiable
**Confidence**: CRITICAL (0% SLM safe cases)
**Fallback**: None (LLM mandatory)

---

### CLASSIFICATION
```
IF bin <= 2:
  USE Phi-3 or Qwen (both 100%)
ELSE (bin >= 3):
  USE Qwen (Cov=0.227 vs Phi-3 Cov=0.160)
```
**Rationale**: All accurate, Qwen better coverage on hard samples
**Confidence**: MEDIUM (100% accuracy, but coverage signal weak)

---

### MATHS
```
IF model == TinyLlama AND bin >= 3:
  USE Phi-3 (avoid TinyLlama degradation)
ELSE:
  USE Qwen (fastest: 6.77s, 100%)
```
**Rationale**: All SLMs safe, Qwen fastest overall
**Confidence**: HIGH (100% throughout)

---

### SUMMARIZATION
```
USE Phi-3 (best consistency S=0.755)

# Alternative: Qwen (1.3x faster)
# Trade-off: S=0.636 vs 0.755
```
**Rationale**: All 100% valid, Phi-3 most consistent lengths
**Confidence**: HIGH (no accuracy gap)

---

### RETRIEVAL_GROUNDED
```
USE Phi-3 (highest coverage Cov=0.893)

# Acceptable alternatives:
# - Qwen: Cov=0.827 (3% gap)
# - TinyLlama: Cov=0.784 (9% gap)
```
**Rationale**: All 100% accurate, Phi-3 best coverage
**Confidence**: MEDIUM (coverage heuristic-based)

---

### INSTRUCTION_FOLLOWING
```
USE Qwen or Phi-3 (both 100%)

AVOID TinyLlama (1 failure observed in Bin 0)
```
**Rationale**: All accurate; avoid TinyLlama edge case
**Confidence**: MEDIUM (TinyLlama failure may be sampling artifact)

---

### INFORMATION_EXTRACTION
```
USE Qwen (fastest: 2.4s, 100%)

# All models identical accuracy
# Choose by latency/cost
```
**Rationale**: All 100% valid, Qwen fastest
**Confidence**: HIGH (clear speed winner)

---

## Cost-Benefit Analysis

### Savings by Task (vs Llama-70B baseline)

| Task | Best SLM | Latency Improvement | Memory Saving | Accuracy Loss |
|------|----------|---|---|---|
| text_generation | Qwen | 4.6× faster | 97.9% less | 0% |
| code_generation | — | — | — | 5-20% (use Llama) |
| classification | Qwen | 13× faster | 97.9% less | 0% |
| maths | Qwen | 14× faster | 97.9% less | 0% |
| summarization | Phi-3 | 2.0× slower | 94.6% less | 0% |
| retrieval_qa | Phi-3 | 2.8× slower | 94.6% less | 0% |
| instruction | Qwen | 2.1× faster | 97.9% less | 0% |
| info_extract | Qwen | 1.4× faster | 97.9% less | 0% |

### Memory Footprint

```
Llama-70B:     140 GB (baseline)
Phi-3 (3.8B):    7.6 GB (94.6% savings)
Qwen (1.5B):     3.0 GB (97.9% savings)
TinyLlama (1.1B): 2.2 GB (98.4% savings)
```

### TCO for 1M inferences/day

```
Llama (API):          $500/day
Phi-3 (local GPU):    $20/day (96% cheaper)
Qwen (local GPU):     $15/day (97% cheaper)

Breaks even after: 3-5 days of deployment
```

---

## Deployment Stages

### Stage 1: Safe Deployments (Immediate)
```
✓ Deploy SLMs on:
  - Text generation (Qwen)
  - Classification (Qwen)
  - Maths (Qwen)
  - Information extraction (Qwen)
  - Instruction following (Qwen/Phi-3)

Expected: 70% of traffic, 5-40% latency improvement
```

### Stage 2: Conditional Deployments (With Monitoring)
```
~ Monitor closely on:
  - Summarization (Phi-3) — confidence S=0.755
  - Retrieval QA (Phi-3) — coverage is heuristic-based

Acceptance criteria:
  - Accuracy >= 95% (vs Llama)
  - No production incidents in 30 days
```

### Stage 3: Avoid Completely
```
✗ Code generation:
  - NO SLM deployment (ever)
  - Maintain Llama-only route
  - Reason: Syntax errors are unrecoverable
```

---

## Production Monitoring

### Metrics to Track

**Per-Task, Per-Bin**:
1. **Accuracy**: % valid outputs
   - Alert if < 90% (threshold: bin-specific)
   - Compare to Llama baseline

2. **Latency**: p50, p95, p99
   - Alert if > 50% slower than expected
   - Track resource utilization

3. **Error Rate**: failures by category
   - Track syntax/logic errors (code)
   - Track validation failures (maths)

### Escalation Policy

```
IF accuracy_drop > 5% for 100 consecutive samples:
  → Escalate to Llama (failover)
  → Page on-call engineer
  → Log incident for analysis

IF latency degradation > 50%:
  → Check GPU load
  → Scale horizontally if needed
  → Revert to Llama if scaling fails
```

---

## Decision Flow Pseudocode

```python
def route_inference(task, query_text, difficulty_bin):
    """Main routing logic"""

    # Hard gates (safety first)
    if task == "code_generation":
        return "llama"  # ALWAYS

    if task == "instruction_following" and model == "tinyllama":
        return "qwen"   # Avoid tiny

    # Soft routing (by capability)
    routes = {
        "text_generation": "qwen",
        "classification": "phi3" if bin <= 2 else "qwen",
        "maths": "qwen" if model != "tinyllama" else "phi3",
        "summarization": "phi3",
        "retrieval_grounded": "phi3",
        "instruction_following": "qwen",
        "information_extraction": "qwen",
    }

    slm = routes.get(task, "qwen")

    # Latency optimization
    if requires_lowest_latency(query_context):
        slm = "qwen"  # Always fastest

    # Fallback to Llama if unsure
    if confidence(slm, task) < 0.75:
        return "llama"

    return slm
```

---

## Success Criteria

### Deployment Successful When:
- [ ] Code generation: Llama only, 0% SLM usage
- [ ] Safe tasks: >90% SLM usage
- [ ] Accuracy gap: <2% vs Llama baseline
- [ ] Latency improvement: 5-40% average
- [ ] Memory savings: 65-98%
- [ ] Zero escalations in 30 days
- [ ] Cost reduction: 70-97%

---

## Next Steps

1. **Implement routing** in production system
2. **Set up monitoring** dashboards per task
3. **Deploy Stage 1** (safe tasks) to 10% traffic
4. **Monitor for 1 week**, validate metrics
5. **Ramp to 50%** if no issues
6. **Deploy Stage 2** with alerting
7. **Maintain Llama** as ultimate fallback

