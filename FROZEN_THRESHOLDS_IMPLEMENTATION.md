# Implementation: Frozen Thresholds & Consensus Aggregation

**Status**: ✅ COMPLETE  
**Date**: 2026-04-19  
**Reference**: Paper Table 6.3, Sections 7.2-7.4

---

## What Was Implemented

### 1. Frozen Thresholds Module (`sddf/frozen_thresholds.py`)

**New file** that defines the frozen tau^consensus values from Paper Table 6.3.

```python
FROZEN_TAU_CONSENSUS = {
    "classification": 0.6667,
    "code_generation": 0.6667,
    "information_extraction": 1.0000,
    "instruction_following": 1.0000,
    "maths": 0.3333,
    "retrieval_grounded": 1.0000,
    "summarization": 0.2972,
    "text_generation": 0.9333,
}
```

**Functions**:
- `get_frozen_threshold(task_family)` → float
- `validate_task_family(task_family)` → bool
- `all_frozen_thresholds()` → dict

**Key Feature**: These values are **frozen** and should NOT be re-learned. Use directly in runtime.

---

### 2. Runtime Routing Module (`sddf/runtime_routing.py`)

**New file** that implements Paper Sections 7.2-7.4:
- Query-level routing decisions
- Consensus aggregation across models
- Tier assignment from aggregated routing ratio

**Key Functions**:

#### `route_query(p_fail, task_family) -> "SLM" | "LLM"`
Routes a single query based on frozen threshold:
```python
route = "SLM" if p_fail < tau_consensus[task_family] else "LLM"
```

#### `consensus_routing_ratio(per_model_rho) -> float`
Computes consensus ratio across three SLMs:
```python
rho_bar = (1/3) * (rho_0.5b + rho_3b + rho_7b)
```

#### `tier_from_consensus_ratio(rho_bar) -> "SLM" | "HYBRID" | "LLM"`
Maps aggregated ratio to tier:
```
if rho_bar >= 0.70 -> SLM
if rho_bar <= 0.30 -> LLM
else              -> HYBRID
```

#### `route_use_case_multimodel(query_failures_by_model, task_family)`
Complete workflow for all queries across all models:
1. Route each query using frozen threshold
2. Compute per-model routing ratio rho(m)
3. Aggregate to rho_bar
4. Assign tier

---

### 3. Demo & Validation (`demo_frozen_thresholds.py`)

**Executable demo** showing:
1. ✅ Frozen thresholds loaded from Table 6.3
2. ✅ Query-level routing with frozen thresholds
3. ✅ Consensus aggregation across models
4. ✅ Multimodel use-case routing with tier decision
5. ✅ Comparison: Frozen vs Old Code-Learned values

**Run with**:
```bash
python3 demo_frozen_thresholds.py
```

**Output shows**:
- All 8 frozen thresholds
- Example routing decisions
- Consensus ratio computation
- Tier assignment logic
- Quantifies difference from old learned values (2.9x scale factor)

---

## Changes to Existing Files

### `sddf/__init__.py`
Added exports:
```python
from .frozen_thresholds import (
    FROZEN_TAU_CONSENSUS,
    get_frozen_threshold,
    validate_task_family,
    all_frozen_thresholds,
)
from .runtime_routing import (
    route_query,
    aggregate_routing_ratio,
    consensus_routing_ratio,
    tier_from_consensus_ratio,
    route_use_case,
    route_query_multimodel,
    route_use_case_multimodel,
)

__all__ = [
    # ... existing exports ...
    "FROZEN_TAU_CONSENSUS",
    "get_frozen_threshold",
    "validate_task_family",
    "all_frozen_thresholds",
    "route_query",
    "aggregate_routing_ratio",
    "consensus_routing_ratio",
    "tier_from_consensus_ratio",
    "route_use_case",
    "route_query_multimodel",
    "route_use_case_multimodel",
]
```

---

## How to Use in Your Code

### Example 1: Query-Level Routing
```python
from sddf import route_query

# For a single query
p_fail = 0.45  # Predicted failure probability
task_family = "classification"

decision = route_query(p_fail, task_family)
print(decision)  # "SLM" if p_fail < 0.6667, else "LLM"
```

### Example 2: Multimodel Use-Case Routing
```python
from sddf import route_use_case_multimodel

# Failure probabilities per model per query
query_failures_by_model = {
    "qwen2.5_0.5b": {"q1": 0.3, "q2": 0.6, ...},
    "qwen2.5_3b": {"q1": 0.4, "q2": 0.5, ...},
    "qwen2.5_7b": {"q1": 0.35, "q2": 0.55, ...},
}

result = route_use_case_multimodel(query_failures_by_model, "classification")

print(f"Tier: {result['tier']}")  # "SLM", "HYBRID", or "LLM"
print(f"Consensus ratio: {result['rho_bar']:.4f}")
print(f"Per-model ratios: {result['per_model_rho']}")
```

### Example 3: Check Task Family Validity
```python
from sddf import validate_task_family, get_frozen_threshold

if validate_task_family("summarization"):
    tau = get_frozen_threshold("summarization")
    print(f"Frozen threshold: {tau}")  # 0.2972
else:
    print("Unknown task family")
```

---

## Key Differences from Old Code

| Aspect | Old Code | New Implementation |
|--------|----------|-------------------|
| **Thresholds** | Learned per task/model | Frozen from Table 6.3 |
| **Scale** | [0.0, 0.6] | [0.3, 1.0] |
| **Consensus** | NOT computed | Implemented: tau^consensus |
| **Routing Ratio** | Per-model only | Aggregated to rho_bar |
| **Tier Decision** | Not computed | SLM/HYBRID/LLM from rho_bar |
| **Runtime Routing** | Minimal | Full Paper Section 7 implementation |

**Scale Difference**: Paper thresholds are ~2.9x larger than old learned values

---

## Next Steps (For Full Alignment)

### Phase 2: Constraint Definition
- [ ] Extract LLM baseline C_baseline and R̄_val from paper experiments
- [ ] Reference actual LLM performance, not hardcoded values
- [ ] Update validation phase to use real baseline constraints

### Phase 3: Integration
- [ ] Update validation pipeline to use frozen thresholds
- [ ] Update test pipeline to apply frozen consensus thresholds
- [ ] Implement consensus aggregation in benchmarking scripts

### Phase 4: Validation
- [ ] Run full benchmarking with frozen thresholds
- [ ] Verify tier agreement matches paper Table 8.1
- [ ] Generate updated results tables

---

## Testing

Run the demo to verify everything works:
```bash
python3 demo_frozen_thresholds.py
```

Expected output:
- All 8 frozen thresholds displayed
- 5 demonstrations running successfully
- No errors or exceptions

---

## Files Created

```
sddf/
  ├── frozen_thresholds.py          [NEW] Frozen tau^consensus values
  ├── runtime_routing.py            [NEW] Query/use-case routing with consensus
  ├── __init__.py                   [MODIFIED] Added exports
  
demo_frozen_thresholds.py            [NEW] Executable demo
FROZEN_THRESHOLDS_IMPLEMENTATION.md  [NEW] This file
```

---

## Paper References

- **Table 6.3**: Frozen tau^consensus values (Section 6.3.3)
- **Section 7.2**: Query-level routing rule
- **Section 7.3**: Use-case aggregation logic and tier mapping
- **Section 7.4**: Runtime results by use case

---

**Implementation Complete** ✅

The frozen thresholds and consensus aggregation logic are now available and ready for integration into the benchmarking pipeline.
