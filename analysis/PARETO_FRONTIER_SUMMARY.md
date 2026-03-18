# Pareto Frontier Analysis

## Overview

Models on the Pareto frontier represent optimal tradeoffs between:
- **Accuracy**: Correctness of predictions
- **Latency**: Inference speed
- **Cost**: API pricing

A model is Pareto-efficient if no other model is better on ALL three dimensions.

---

## Bin 0 (Easy)

**Efficiency**: 4 of 5 models on frontier

### Pareto-Efficient Models

| Model | Size | Accuracy | Latency | Cost | Score |
|-------|------|----------|---------|------|-------|
| TinyLLaMA | 0.5B | 0.0% | 5ms | $0.00 | 200.40 |
| Qwen2.5 | 1.5B | 90.0% | 6863ms | $0.00 | 200.54 |
| Mixtral-8x7B | 45.0B | 0.0% | 2ms | $0.27 | 1.71 |
| Llama-3.3-70B | 70.0B | 68.3% | 2964ms | $0.40 | 0.90 |

### Model Recommendations

- **Best Accuracy**: Qwen2.5 (90.0%)
- **Fastest**: Mixtral-8x7B (2ms)
- **Cheapest**: TinyLLaMA ($0.00/1K)
- **Best Overall**: Qwen2.5 (Score: 200.54)

### Dominated Models

These models are strictly worse than Pareto-efficient models:

- Phi-3 (3.8B): 87.8% accuracy, 8830ms, $0.00/1K

---

## Bin 1 (Medium)

**Efficiency**: 4 of 5 models on frontier

### Pareto-Efficient Models

| Model | Size | Accuracy | Latency | Cost | Score |
|-------|------|----------|---------|------|-------|
| TinyLLaMA | 0.5B | 0.0% | 5ms | $0.00 | 200.40 |
| Qwen2.5 | 1.5B | 92.5% | 6344ms | $0.00 | 200.56 |
| Mixtral-8x7B | 45.0B | 0.0% | 2ms | $0.27 | 1.71 |
| Llama-3.3-70B | 70.0B | 68.3% | 3142ms | $0.40 | 0.90 |

### Model Recommendations

- **Best Accuracy**: Qwen2.5 (92.5%)
- **Fastest**: Mixtral-8x7B (2ms)
- **Cheapest**: TinyLLaMA ($0.00/1K)
- **Best Overall**: Qwen2.5 (Score: 200.56)

### Dominated Models

These models are strictly worse than Pareto-efficient models:

- Phi-3 (3.8B): 92.2% accuracy, 9121ms, $0.00/1K

---

## Bin 2 (Hard)

**Efficiency**: 4 of 5 models on frontier

### Pareto-Efficient Models

| Model | Size | Accuracy | Latency | Cost | Score |
|-------|------|----------|---------|------|-------|
| TinyLLaMA | 0.5B | 0.0% | 5ms | $0.00 | 200.40 |
| Qwen2.5 | 1.5B | 92.5% | 6734ms | $0.00 | 200.56 |
| Mixtral-8x7B | 45.0B | 0.0% | 2ms | $0.27 | 1.71 |
| Llama-3.3-70B | 70.0B | 69.2% | 3263ms | $0.40 | 0.90 |

### Model Recommendations

- **Best Accuracy**: Qwen2.5 (92.5%)
- **Fastest**: Mixtral-8x7B (2ms)
- **Cheapest**: TinyLLaMA ($0.00/1K)
- **Best Overall**: Qwen2.5 (Score: 200.56)

### Dominated Models

These models are strictly worse than Pareto-efficient models:

- Phi-3 (3.8B): 84.4% accuracy, 9391ms, $0.00/1K

---

## Bin 3 (Very Hard)

**Efficiency**: 5 of 5 models on frontier

### Pareto-Efficient Models

| Model | Size | Accuracy | Latency | Cost | Score |
|-------|------|----------|---------|------|-------|
| TinyLLaMA | 0.5B | 0.0% | 5ms | $0.00 | 200.40 |
| Qwen2.5 | 1.5B | 93.3% | 9242ms | $0.00 | 200.56 |
| Phi-3 | 3.8B | 87.8% | 8754ms | $0.00 | 200.53 |
| Mixtral-8x7B | 45.0B | 0.0% | 2ms | $0.27 | 1.71 |
| Llama-3.3-70B | 70.0B | 66.7% | 3366ms | $0.40 | 0.89 |

### Model Recommendations

- **Best Accuracy**: Qwen2.5 (93.3%)
- **Fastest**: Mixtral-8x7B (2ms)
- **Cheapest**: TinyLLaMA ($0.00/1K)
- **Best Overall**: Qwen2.5 (Score: 200.56)

---

## Bin 4 (Hardest)

**Efficiency**: 4 of 5 models on frontier

### Pareto-Efficient Models

| Model | Size | Accuracy | Latency | Cost | Score |
|-------|------|----------|---------|------|-------|
| TinyLLaMA | 0.5B | 0.0% | 5ms | $0.00 | 200.40 |
| Qwen2.5 | 1.5B | 94.2% | 6259ms | $0.00 | 200.57 |
| Mixtral-8x7B | 45.0B | 0.0% | 2ms | $0.27 | 1.71 |
| Llama-3.3-70B | 70.0B | 67.5% | 3317ms | $0.40 | 0.89 |

### Model Recommendations

- **Best Accuracy**: Qwen2.5 (94.2%)
- **Fastest**: Mixtral-8x7B (2ms)
- **Cheapest**: TinyLLaMA ($0.00/1K)
- **Best Overall**: Qwen2.5 (Score: 200.57)

### Dominated Models

These models are strictly worse than Pareto-efficient models:

- Phi-3 (3.8B): 83.3% accuracy, 20187ms, $0.00/1K

---

