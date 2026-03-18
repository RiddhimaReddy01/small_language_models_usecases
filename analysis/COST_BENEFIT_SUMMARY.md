# Cost-Benefit Analysis

## Cost per 1K Tokens (Pricing)

| Model | Type | $/1K Tokens | Cost per Accuracy Point |
|-------|------|-------------|------------------------|
| TinyLLaMA | SLM-Local | $0.00 | $0.0000 |
| Qwen2.5 | SLM-Local | $0.00 | $0.0000 |
| Phi-3 | SLM-Local | $0.00 | $0.0000 |
| Mixtral-8x7B | Medium-Cloud | $0.27 | $0.0000 |
| Llama-3.3-70B | LLM-Cloud | $0.40 | $0.5854 |

## Latency Comparison

| Model | Avg Latency (ms) | Tokens/sec |
|-------|-----------------|------------|
| TinyLLaMA | 5.0 | 200 |
| Qwen2.5 | 6863.0 | 100 |
| Phi-3 | 8830.3 | 80 |
| Mixtral-8x7B | 2.0 | 5000 |
| Llama-3.3-70B | 2963.6 | 3000 |

## Pareto-Efficient Models by Difficulty

### Bin 0 (Easy)

Recommended models (best tradeoff):

- **TinyLLaMA (0.5B)**
  - Accuracy: 0.0%
  - Latency: 5.0ms
  - Cost: $0.00/1K tokens
  - Score: 200.40

- **Qwen2.5 (1.5B)**
  - Accuracy: 90.0%
  - Latency: 6863.0ms
  - Cost: $0.00/1K tokens
  - Score: 200.54

- **Mixtral-8x7B (45.0B)**
  - Accuracy: 0.0%
  - Latency: 2.0ms
  - Cost: $0.27/1K tokens
  - Score: 1.71

- **Llama-3.3-70B (70.0B)**
  - Accuracy: 68.3%
  - Latency: 2963.6ms
  - Cost: $0.40/1K tokens
  - Score: 0.90

### Bin 1 (Medium)

Recommended models (best tradeoff):

- **TinyLLaMA (0.5B)**
  - Accuracy: 0.0%
  - Latency: 5.0ms
  - Cost: $0.00/1K tokens
  - Score: 200.40

- **Qwen2.5 (1.5B)**
  - Accuracy: 92.5%
  - Latency: 6344.5ms
  - Cost: $0.00/1K tokens
  - Score: 200.56

- **Mixtral-8x7B (45.0B)**
  - Accuracy: 0.0%
  - Latency: 2.0ms
  - Cost: $0.27/1K tokens
  - Score: 1.71

- **Llama-3.3-70B (70.0B)**
  - Accuracy: 68.3%
  - Latency: 3142.3ms
  - Cost: $0.40/1K tokens
  - Score: 0.90

### Bin 2 (Hard)

Recommended models (best tradeoff):

- **TinyLLaMA (0.5B)**
  - Accuracy: 0.0%
  - Latency: 5.0ms
  - Cost: $0.00/1K tokens
  - Score: 200.40

- **Qwen2.5 (1.5B)**
  - Accuracy: 92.5%
  - Latency: 6734.2ms
  - Cost: $0.00/1K tokens
  - Score: 200.56

- **Mixtral-8x7B (45.0B)**
  - Accuracy: 0.0%
  - Latency: 2.0ms
  - Cost: $0.27/1K tokens
  - Score: 1.71

- **Llama-3.3-70B (70.0B)**
  - Accuracy: 69.2%
  - Latency: 3263.2ms
  - Cost: $0.40/1K tokens
  - Score: 0.90

### Bin 3 (Very Hard)

Recommended models (best tradeoff):

- **TinyLLaMA (0.5B)**
  - Accuracy: 0.0%
  - Latency: 5.0ms
  - Cost: $0.00/1K tokens
  - Score: 200.40

- **Qwen2.5 (1.5B)**
  - Accuracy: 93.3%
  - Latency: 9242.3ms
  - Cost: $0.00/1K tokens
  - Score: 200.56

- **Phi-3 (3.8B)**
  - Accuracy: 87.8%
  - Latency: 8754.3ms
  - Cost: $0.00/1K tokens
  - Score: 200.53

- **Mixtral-8x7B (45.0B)**
  - Accuracy: 0.0%
  - Latency: 2.0ms
  - Cost: $0.27/1K tokens
  - Score: 1.71

- **Llama-3.3-70B (70.0B)**
  - Accuracy: 66.7%
  - Latency: 3366.1ms
  - Cost: $0.40/1K tokens
  - Score: 0.89

### Bin 4 (Hardest)

Recommended models (best tradeoff):

- **TinyLLaMA (0.5B)**
  - Accuracy: 0.0%
  - Latency: 5.0ms
  - Cost: $0.00/1K tokens
  - Score: 200.40

- **Qwen2.5 (1.5B)**
  - Accuracy: 94.2%
  - Latency: 6258.9ms
  - Cost: $0.00/1K tokens
  - Score: 200.57

- **Mixtral-8x7B (45.0B)**
  - Accuracy: 0.0%
  - Latency: 2.0ms
  - Cost: $0.27/1K tokens
  - Score: 1.71

- **Llama-3.3-70B (70.0B)**
  - Accuracy: 67.5%
  - Latency: 3317.1ms
  - Cost: $0.40/1K tokens
  - Score: 0.89

