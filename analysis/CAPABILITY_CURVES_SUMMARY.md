# Capability Curves Analysis

## Model Scaling by Difficulty Bin

### Bin 0: Easy

| Model | Size | Accuracy | Variance | Latency (ms) |
|-------|------|----------|----------|---------------|
| TinyLLaMA | 0.5B | 0.0% | ±0.0% | 0 |
| Qwen2.5 | 1.5B | 90.0% | ±12.3% | 6863 |
| Phi-3 | 3.8B | 87.8% | ±18.6% | 8830 |
| Mixtral-8x7B | 45.0B | 0.0% | ±0.0% | 0 |
| Llama-3.3-70B | 70.0B | 68.3% | ±43.2% | 2964 |

### Bin 1: Medium

| Model | Size | Accuracy | Variance | Latency (ms) |
|-------|------|----------|----------|---------------|
| TinyLLaMA | 0.5B | 0.0% | ±0.0% | 0 |
| Qwen2.5 | 1.5B | 92.5% | ±10.4% | 6344 |
| Phi-3 | 3.8B | 92.2% | ±16.0% | 9121 |
| Mixtral-8x7B | 45.0B | 0.0% | ±0.0% | 0 |
| Llama-3.3-70B | 70.0B | 68.3% | ±43.2% | 3142 |

### Bin 2: Hard

| Model | Size | Accuracy | Variance | Latency (ms) |
|-------|------|----------|----------|---------------|
| TinyLLaMA | 0.5B | 0.0% | ±0.0% | 0 |
| Qwen2.5 | 1.5B | 92.5% | ±16.1% | 6734 |
| Phi-3 | 3.8B | 84.4% | ±27.2% | 9391 |
| Mixtral-8x7B | 45.0B | 0.0% | ±0.0% | 0 |
| Llama-3.3-70B | 70.0B | 69.2% | ±42.9% | 3263 |

### Bin 3: Very Hard

| Model | Size | Accuracy | Variance | Latency (ms) |
|-------|------|----------|----------|---------------|
| TinyLLaMA | 0.5B | 0.0% | ±0.0% | 0 |
| Qwen2.5 | 1.5B | 93.3% | ±11.3% | 9242 |
| Phi-3 | 3.8B | 87.8% | ±18.6% | 8754 |
| Mixtral-8x7B | 45.0B | 0.0% | ±0.0% | 0 |
| Llama-3.3-70B | 70.0B | 66.7% | ±44.2% | 3366 |

### Bin 4: Hardest

| Model | Size | Accuracy | Variance | Latency (ms) |
|-------|------|----------|----------|---------------|
| TinyLLaMA | 0.5B | 0.0% | ±0.0% | 0 |
| Qwen2.5 | 1.5B | 94.2% | ±11.5% | 6259 |
| Phi-3 | 3.8B | 83.3% | ±29.7% | 20187 |
| Mixtral-8x7B | 45.0B | 0.0% | ±0.0% | 0 |
| Llama-3.3-70B | 70.0B | 67.5% | ±44.6% | 3317 |

## Tipping Points by Model

### Mixtral-8x7B (45B)

| Task | Tipping Bin | Accuracy at Threshold |
|------|-------------|----------------------|
| text_generation | Easy | 0.0% |
| code_generation | Easy | 0.0% |
| classification | Easy | 0.0% |
| maths | Easy | 0.0% |
| summarization | Easy | 0.0% |
| retrieval_grounded | Easy | 0.0% |
| instruction_following | Easy | 0.0% |
| information_extraction | Easy | 0.0% |

### Llama-3.3-70B (70B)

| Task | Tipping Bin | Accuracy at Threshold |
|------|-------------|----------------------|
| text_generation | Easy | 0.0% |
| code_generation | Easy | 6.7% |
| classification | No tipping | No tipping point |
| maths | No tipping | No tipping point |
| summarization | No tipping | No tipping point |
| retrieval_grounded | No tipping | No tipping point |
| instruction_following | No tipping | No tipping point |
| information_extraction | No tipping | No tipping point |

### Phi-3 (3.8B)

| Task | Tipping Bin | Accuracy at Threshold |
|------|-------------|----------------------|
| classification | No tipping | No tipping point |
| maths | No tipping | No tipping point |
| summarization | Hard | 33.3% |
| retrieval_grounded | No tipping | No tipping point |
| instruction_following | No tipping | No tipping point |
| information_extraction | No tipping | No tipping point |

### Qwen2.5 (1.5B)

| Task | Tipping Bin | Accuracy at Threshold |
|------|-------------|----------------------|
| text_generation | No tipping | No tipping point |
| code_generation | No tipping | No tipping point |
| classification | No tipping | No tipping point |
| maths | No tipping | No tipping point |
| summarization | No tipping | No tipping point |
| retrieval_grounded | No tipping | No tipping point |
| instruction_following | No tipping | No tipping point |
| information_extraction | No tipping | No tipping point |

### TinyLLaMA (0.5B)

| Task | Tipping Bin | Accuracy at Threshold |
|------|-------------|----------------------|
| text_generation | Easy | 0.0% |
| code_generation | Easy | 0.0% |
| classification | Easy | 0.0% |
| maths | Easy | 0.0% |
| summarization | Easy | 0.0% |
| retrieval_grounded | Easy | 0.0% |
| instruction_following | Easy | 0.0% |
| information_extraction | Easy | 0.0% |

