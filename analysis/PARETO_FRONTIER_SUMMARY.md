# Pareto Frontier Analysis

## Overview

Models on the Pareto frontier represent optimal tradeoffs between:
- **Accuracy**: Correctness of predictions
- **Latency**: Inference speed
- **Cost**: API pricing

A model is Pareto-efficient if no other model is better on ALL three dimensions.

---

## Bin 0 (Easy)

**Efficiency**: 3 of 5 models on frontier

### Pareto-Efficient Models

| Model | Size | Accuracy | Latency | Cost | Score |
|-------|------|----------|---------|------|-------|
| TinyLLaMA | 0.5B | 93.3% | 5318ms | $0.00 | 200.56 |
| Mixtral-8x7B | 45.0B | 0.0% | 2ms | $0.27 | 1.71 |
| Llama-3.3-70B | 70.0B | 68.3% | 2964ms | $0.40 | 0.90 |

### Model Recommendations

- **Best Accuracy**: TinyLLaMA (93.3%)
- **Fastest**: Mixtral-8x7B (2ms)
- **Cheapest**: TinyLLaMA ($0.00/1K)
- **Best Overall**: TinyLLaMA (Score: 200.56)

### Dominated Models

These models are strictly worse than Pareto-efficient models:

- Qwen2.5 (1.5B): 90.0% accuracy, 6863ms, $0.00/1K
- Phi-3 (3.8B): 74.2% accuracy, 10976ms, $0.00/1K

---

## Bin 1 (Medium)

**Efficiency**: 3 of 5 models on frontier

### Pareto-Efficient Models

| Model | Size | Accuracy | Latency | Cost | Score |
|-------|------|----------|---------|------|-------|
| TinyLLaMA | 0.5B | 100.0% | 5983ms | $0.00 | 200.60 |
| Mixtral-8x7B | 45.0B | 0.0% | 2ms | $0.27 | 1.71 |
| Llama-3.3-70B | 70.0B | 68.3% | 3142ms | $0.40 | 0.90 |

### Model Recommendations

- **Best Accuracy**: TinyLLaMA (100.0%)
- **Fastest**: Mixtral-8x7B (2ms)
- **Cheapest**: TinyLLaMA ($0.00/1K)
- **Best Overall**: TinyLLaMA (Score: 200.60)

### Dominated Models

These models are strictly worse than Pareto-efficient models:

- Qwen2.5 (1.5B): 92.5% accuracy, 6344ms, $0.00/1K
- Phi-3 (3.8B): 78.5% accuracy, 10995ms, $0.00/1K

---

## Bin 2 (Hard)

**Efficiency**: 3 of 5 models on frontier

### Pareto-Efficient Models

| Model | Size | Accuracy | Latency | Cost | Score |
|-------|------|----------|---------|------|-------|
| TinyLLaMA | 0.5B | 93.3% | 5373ms | $0.00 | 200.56 |
| Mixtral-8x7B | 45.0B | 0.0% | 2ms | $0.27 | 1.71 |
| Llama-3.3-70B | 70.0B | 69.2% | 3263ms | $0.40 | 0.90 |

### Model Recommendations

- **Best Accuracy**: TinyLLaMA (93.3%)
- **Fastest**: Mixtral-8x7B (2ms)
- **Cheapest**: TinyLLaMA ($0.00/1K)
- **Best Overall**: TinyLLaMA (Score: 200.56)

### Dominated Models

These models are strictly worse than Pareto-efficient models:

- Qwen2.5 (1.5B): 92.5% accuracy, 6734ms, $0.00/1K
- Phi-3 (3.8B): 72.5% accuracy, 11109ms, $0.00/1K

---

## Bin 3 (Very Hard)

**Efficiency**: 3 of 5 models on frontier

### Pareto-Efficient Models

| Model | Size | Accuracy | Latency | Cost | Score |
|-------|------|----------|---------|------|-------|
| TinyLLaMA | 0.5B | 93.3% | 4736ms | $0.00 | 200.56 |
| Mixtral-8x7B | 45.0B | 0.0% | 2ms | $0.27 | 1.71 |
| Llama-3.3-70B | 70.0B | 66.7% | 3366ms | $0.40 | 0.89 |

### Model Recommendations

- **Best Accuracy**: TinyLLaMA (93.3%)
- **Fastest**: Mixtral-8x7B (2ms)
- **Cheapest**: TinyLLaMA ($0.00/1K)
- **Best Overall**: TinyLLaMA (Score: 200.56)

### Dominated Models

These models are strictly worse than Pareto-efficient models:

- Qwen2.5 (1.5B): 93.3% accuracy, 9242ms, $0.00/1K
- Phi-3 (3.8B): 74.2% accuracy, 10380ms, $0.00/1K

---

## Bin 4 (Hardest)

**Efficiency**: 3 of 5 models on frontier

### Pareto-Efficient Models

| Model | Size | Accuracy | Latency | Cost | Score |
|-------|------|----------|---------|------|-------|
| TinyLLaMA | 0.5B | 100.0% | 5456ms | $0.00 | 200.60 |
| Mixtral-8x7B | 45.0B | 0.0% | 2ms | $0.27 | 1.71 |
| Llama-3.3-70B | 70.0B | 67.5% | 3317ms | $0.40 | 0.89 |

### Model Recommendations

- **Best Accuracy**: TinyLLaMA (100.0%)
- **Fastest**: Mixtral-8x7B (2ms)
- **Cheapest**: TinyLLaMA ($0.00/1K)
- **Best Overall**: TinyLLaMA (Score: 200.60)

### Dominated Models

These models are strictly worse than Pareto-efficient models:

- Qwen2.5 (1.5B): 94.2% accuracy, 6259ms, $0.00/1K
- Phi-3 (3.8B): 79.6% accuracy, 19525ms, $0.00/1K

---

