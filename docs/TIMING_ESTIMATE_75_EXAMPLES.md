# Timing Estimate: 75 Examples (15/bin) x 2 Models

## Configuration
- Total examples: 75
- Per bin: 15 (5 bins)
- Models: 2 (SLM + LLM)
- Tasks: 8
- Scope: LOCAL INFERENCE on your hardware

---

## Hardware Scenarios

### Scenario 1: CPU (Modern Laptop/Desktop)
```
Model load:    60s (30s × 2 models)
Inference:     225s (75 examples × 3s each)
Overhead:      30s
---
PER TASK:      5.2 minutes
ALL 8 TASKS:   42 minutes (0.7 hours)
```

### Scenario 2: CPU + Quantized (.gguf format)
```
Model load:    10s (faster with quantization)
Inference:     150s (75 × 2s)
Overhead:      30s
---
PER TASK:      3.2 minutes
ALL 8 TASKS:   25 minutes (0.4 hours)
```

### Scenario 3: GPU (NVIDIA T4 / RTX 3060)
```
Model load:    20s
Inference:     38s (75 × 0.5s)
Overhead:      30s
---
PER TASK:      1.5 minutes
ALL 8 TASKS:   12 minutes (0.2 hours)
```

### Scenario 4: GPU (A100 / H100)
```
Model load:    10s
Inference:     11s (75 × 0.15s)
Overhead:      30s
---
PER TASK:      0.9 minutes
ALL 8 TASKS:   7 minutes (0.1 hours)
```

---

## Realistic Timeline

### Option A: CPU (What most people have)
- Per task: 5-15 minutes
- All 8 tasks: 45 min - 2 hours
- Best approach: Sequential overnight batch
- Effort: 10 min setup + 2 hours runtime + 10 min check

### Option B: GPU (If available)
- All 8 tasks: 7-15 minutes
- Can run same day
- Effort: 10 min setup + 15 min runtime

### Option C: Recommended Hybrid
1. Phase 1 - Aggregate existing (30 min, NO new inference)
   - Expected: +20-30 examples per task from cached runs

2. Phase 2 - Sample remaining (1-2 hours)
   - Need: 45 new examples per task
   - 75 total per task (not just 75)

3. Phase 3 - Validation (30 min)
   - Verify bins, balance, quality

TOTAL: 2-2.5 hours wall time (can be overnight)

---

## Check Your Hardware

Run this to estimate YOUR exact timing:

```python
import torch
import time
from transformers import pipeline

# Check GPU
print("GPU Available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print("Memory:", torch.cuda.get_device_properties(0).total_memory / 1e9, "GB")

# Benchmark one inference
model_name = "Qwen/Qwen2.5-0.5B-Instruct"
pipe = pipeline("text-generation", model=model_name)

start = time.time()
output = pipe("What is machine learning?", max_new_tokens=50)
elapsed = time.time() - start

print(f"\nSingle inference time: {elapsed:.2f}s")
print(f"75 examples would take: {75 * elapsed / 60:.1f} minutes")
print(f"75 × 2 models would take: {75 * 2 * elapsed / 60:.1f} minutes")
print(f"All 8 tasks would take: {75 * 2 * elapsed * 8 / 3600:.1f} hours")
```

---

## My Recommendation: 75 Examples

**This is the SWEET SPOT:**

| Aspect | Rating | Why |
|--------|--------|-----|
| Coverage | Excellent | 15/bin = robust per-bin estimates |
| Curves | Excellent | 5 points with 15 samples each |
| Tipping Points | Good | Clear trend detection |
| Uncertainty | Robust | Full 200-sample bootstrap |
| Routing | Acceptable | 80-85% precision achievable |
| Time Cost | FAST | 30 min - 2 hours total |
| API Cost | FREE | Local inference only |
| Storage | Minimal | ~500MB-1GB per task |

---

## Execution Plan (75 Examples)

### Week 1
```
Day 1:
  [ ] Phase 1: Aggregate existing runs (30 min) -> +20-30 ex/task
  [ ] Phase 2: Setup local inference batch script (20 min)

Day 2:
  [ ] Run Phase 2 overnight
    - Sample 45 new examples per task
    - Get SLM + LLM outputs
    - Runtime: 1-2 hours (depending on hardware)

Day 3:
  [ ] Phase 3: Re-annotate into 5 difficulty bins (30 min)
  [ ] Verify: 75 examples per task, balanced, all bins covered
  [ ] Generate SDDF reports (30 min)

Result: ALL 4 capabilities ready
  - Capability curves (excellent quality)
  - Tipping points (reliable)
  - Uncertainty intervals (robust)
  - Routing policy (80% precision)
```

---

## Real-World Timing Examples

### Example 1: Your Laptop (CPU)
- Aggregation: 30 min
- New inference: 2 hours (can be overnight)
- Validation: 30 min
- **TOTAL: 3 hours** (mostly automated)

### Example 2: Desktop with GPU
- Aggregation: 30 min
- New inference: 15 min
- Validation: 30 min
- **TOTAL: 1.25 hours**

### Example 3: Cloud GPU (AWS g4dn.xlarge)
- Aggregation: 30 min
- New inference: 10 min (T4 GPU)
- Validation: 30 min
- **TOTAL: 1.17 hours**
- **COST: $0.52** (GPU time only)

---

## Summary Table

| Hardware | Per Task | All Tasks | Timeline |
|----------|----------|-----------|----------|
| CPU | 5-15 min | 45 min - 2 hr | Overnight |
| CPU Quantized | 3-5 min | 25 min - 1 hr | Evening |
| GPU (T4/3060) | 1-2 min | 10-15 min | Same day |
| GPU (A100) | <1 min | 7 min | Quick run |

---

## Recommendation

**GO WITH 75 EXAMPLES (15/BIN)**

Timing: 30 min - 2 hours (depending on hardware)
Cost: FREE
Results: Publication-ready SDDF analysis with all 4 capabilities
Trade-off: Routing at 80% precision (very acceptable)

**Next step: Tell me your hardware (CPU/GPU/model) and I'll give exact ETA**
