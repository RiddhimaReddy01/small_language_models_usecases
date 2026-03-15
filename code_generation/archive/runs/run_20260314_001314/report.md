# Code Generation Evaluation Report

## Table A: Capability Metrics
| Model | HumanEval Attempted | MBPP Attempted | Total Attempted | pass@1 | Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | Self-Consistency Score | Format Compliance | Signature Compliance | Instruction Adherence | Deterministic Reproducibility | Unsafe Code Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Phi-3 Mini (Ollama) | 1 | 1 | 2 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | N/A | 1.000 | 0.000 | 1.000 | N/A | 0.000 |
| Gemma 2B (Ollama) | 1 | 0 | 1 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | N/A | 0.000 | 0.000 | 0.000 | N/A | 0.000 |
| Mistral 7B (Ollama) | 1 | 1 | 2 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | N/A | 0.000 | 0.000 | 0.000 | N/A | 0.000 |

## Table B: Operational Metrics
| Model | Time Budget (min) | Tasks Completed | Avg Latency / Task (s) | P95 Latency (s) | Tokens/sec | Peak RAM (GB) | Avg Output Tokens | Cost / Request |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Phi-3 Mini (Ollama) | 10 | 2 | 149.655 | 179.001 | 0.445 | 0.000 | 64 | 0.000 |
| Gemma 2B (Ollama) | 10 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Mistral 7B (Ollama) | 10 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
