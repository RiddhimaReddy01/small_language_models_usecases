# Code Generation Evaluation Report

## Table A: Capability Metrics
| Model | HumanEval Attempted | MBPP Attempted | Total Attempted | pass@1 | Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | Self-Consistency Score | Format Compliance | Signature Compliance | Instruction Adherence | Deterministic Reproducibility | Unsafe Code Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Phi-3 Mini (Ollama) | 1 | 1 | 2 | 0.000 | 0.500 | 0.500 | 0.000 | 0.000 | N/A | 1.000 | 0.500 | 1.000 | N/A | 0.000 |
| Gemma 2B (Ollama) | 1 | 1 | 2 | 0.000 | 0.500 | 0.500 | 0.000 | 0.000 | N/A | 0.500 | 0.000 | 0.500 | N/A | 0.000 |
| Mistral 7B (Ollama) | 1 | 1 | 2 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | N/A | 0.000 | 0.000 | 0.000 | N/A | 0.000 |

## Table B: Operational Metrics
| Model | Time Budget (min) | Tasks Completed | Avg Latency / Task (s) | P95 Latency (s) | Tokens/sec | Peak RAM (GB) | Avg Output Tokens | Cost / Request |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Phi-3 Mini (Ollama) | 6 | 2 | 38.832 | 44.181 | 0.723 | 0.013 | 28 | 0.000 |
| Gemma 2B (Ollama) | 6 | 1 | 15.450 | 15.450 | 2.071 | 0.000 | 32 | 0.000 |
| Mistral 7B (Ollama) | 6 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
