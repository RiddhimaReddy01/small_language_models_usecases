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
| Bin 0 (Easy) | TinyLLaMA | 0.5B | 93.3% | FAST | Accuracy meets fast-tier threshold; using cheapest/fastest option |
| Bin 1 (Medium) | TinyLLaMA | 0.5B | 100.0% | FAST | Accuracy meets fast-tier threshold; using cheapest/fastest option |
| Bin 2 (Hard) | TinyLLaMA | 0.5B | 93.3% | FAST | Accuracy meets fast-tier threshold; using cheapest/fastest option |
| Bin 3 (Very Hard) | TinyLLaMA | 0.5B | 93.3% | FAST | Accuracy meets fast-tier threshold; using cheapest/fastest option |
| Bin 4 (Hardest) | TinyLLaMA | 0.5B | 100.0% | FAST | Accuracy meets fast-tier threshold; using cheapest/fastest option |

## Validation Results

### Accuracy vs Cost Tradeoff

| Bin | Model | Accuracy | Gap vs Best | Cost Savings |
|-----|-------|----------|-------------|---------------|
| Easy | TinyLLaMA | 93.3% | -25.0% | 40.0x |
| Medium | TinyLLaMA | 100.0% | -31.7% | 40.0x |
| Hard | TinyLLaMA | 93.3% | -24.2% | 40.0x |
| Very Hard | TinyLLaMA | 93.3% | -26.7% | 40.0x |
| Hardest | TinyLLaMA | 100.0% | -32.5% | 40.0x |

---

## Pseudocode

```python
def route_query(detected_difficulty_bin):
    """Route a query to appropriate model based on difficulty"""

    if detected_difficulty_bin == 0:
        return MODEL['TinyLLaMA']
    if detected_difficulty_bin == 1:
        return MODEL['TinyLLaMA']
    if detected_difficulty_bin == 2:
        return MODEL['TinyLLaMA']
    if detected_difficulty_bin == 3:
        return MODEL['TinyLLaMA']
    if detected_difficulty_bin == 4:
        return MODEL['TinyLLaMA']
```

