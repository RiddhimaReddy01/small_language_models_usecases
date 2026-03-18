# Dynamic Routing Policy

## Policy Overview

**Policy Name**: Difficulty-Based Dynamic Routing

Routes queries to models based on detected difficulty and accuracy thresholds

## Tier Definitions

### FAST: Fast/Cheap

- **Minimum Accuracy**: 75%
- **Use Cases**: Local CPU SLMs

### BALANCED: Balanced

- **Minimum Accuracy**: 85%
- **Use Cases**: Medium cloud models

### PREMIUM: Premium

- **Minimum Accuracy**: 95%
- **Use Cases**: Large LLMs

---

## Routing Decisions

| Difficulty | Model | Size | Accuracy | Tier | Rationale |
|------------|-------|------|----------|------|----------|
| Bin 0 (Easy) | Qwen2.5 | 1.5B | 90.0% | FAST | Accuracy meets fast-tier threshold; using cheapest/fastest option |
| Bin 1 (Medium) | Qwen2.5 | 1.5B | 92.5% | FAST | Accuracy meets fast-tier threshold; using cheapest/fastest option |
| Bin 2 (Hard) | Qwen2.5 | 1.5B | 92.5% | FAST | Accuracy meets fast-tier threshold; using cheapest/fastest option |
| Bin 3 (Very Hard) | Qwen2.5 | 1.5B | 93.3% | FAST | Accuracy meets fast-tier threshold; using cheapest/fastest option |
| Bin 4 (Hardest) | Qwen2.5 | 1.5B | 94.2% | FAST | Accuracy meets fast-tier threshold; using cheapest/fastest option |

## Validation Results

### Accuracy vs Cost Tradeoff

| Bin | Model | Accuracy | Gap vs Best | Cost Savings |
|-----|-------|----------|-------------|---------------|
| Easy | Qwen2.5 | 90.0% | -21.7% | 40.0x |
| Medium | Qwen2.5 | 92.5% | -24.2% | 40.0x |
| Hard | Qwen2.5 | 92.5% | -23.3% | 40.0x |
| Very Hard | Qwen2.5 | 93.3% | -26.7% | 40.0x |
| Hardest | Qwen2.5 | 94.2% | -26.7% | 40.0x |

---

## Pseudocode

```python
def route_query(detected_difficulty_bin):
    """Route a query to appropriate model based on difficulty"""

    if detected_difficulty_bin == 0:
        return MODEL['Qwen2.5']
    if detected_difficulty_bin == 1:
        return MODEL['Qwen2.5']
    if detected_difficulty_bin == 2:
        return MODEL['Qwen2.5']
    if detected_difficulty_bin == 3:
        return MODEL['Qwen2.5']
    if detected_difficulty_bin == 4:
        return MODEL['Qwen2.5']
```

