# Code Generation Evaluation Report

## Table A: Capability Metrics
| Model | HumanEval Attempted | MBPP Attempted | Total Attempted | pass@1 | Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | Self-Consistency Score | Format Compliance | Signature Compliance | Instruction Adherence | Deterministic Reproducibility | Unsafe Code Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Phi-3 Mini (Ollama) | 1 | 1 | 2 | 0.000 | 0.500 | 0.500 | 0.000 | 0.000 | N/A | 1.000 | 0.500 | 1.000 | N/A | 0.000 |
| Gemma 2B (Ollama) | 1 | 1 | 2 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | N/A | 1.000 | 1.000 | 1.000 | N/A | 0.000 |
| Mistral 7B (Ollama) | 1 | 0 | 1 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | N/A | 0.000 | 0.000 | 0.000 | N/A | 0.000 |

## Table B: Operational Metrics
| Model | Time Budget (min) | Tasks Completed | Avg Latency / Task (s) | P95 Latency (s) | Tokens/sec | Peak RAM (GB) | Avg Output Tokens | Cost / Request |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Phi-3 Mini (Ollama) | 2 | 2 | 113.030 | 130.831 | 1.064 | 0.012 | 118.500 | 0.000 |
| Gemma 2B (Ollama) | 2 | 2 | 21.931 | 23.629 | 3.799 | 0.013 | 79 | 0.000 |
| Mistral 7B (Ollama) | 2 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
