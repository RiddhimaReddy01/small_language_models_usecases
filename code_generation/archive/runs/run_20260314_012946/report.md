# Code Generation Evaluation Report

## Table A: Capability Metrics
| Model | HumanEval Attempted | MBPP Attempted | Total Attempted | pass@1 | Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | Self-Consistency Score | Format Compliance | Signature Compliance | Instruction Adherence | Deterministic Reproducibility | Unsafe Code Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5 1.5B (Ollama Fast) | 0 | 3 | 3 | 0.000 | 0.667 | 0.333 | 0.000 | 0.000 | N/A | 0.667 | 0.000 | 0.667 | N/A | 0.000 |

## Table B: Operational Metrics
| Model | Time Budget (min) | Tasks Completed | Avg Latency / Task (s) | P95 Latency (s) | Tokens/sec | Peak RAM (GB) | Avg Output Tokens | Cost / Request |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5 1.5B (Ollama Fast) | 6 | 2 | 139.932 | 269.062 | 1.155 | 0.000 | 24 | 0.000 |
