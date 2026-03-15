# Code Generation Evaluation Report

## Table A: Capability Metrics
| Model | HumanEval Attempted | MBPP Attempted | Total Attempted | pass@1 | Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | Self-Consistency Score | Format Compliance | Signature Compliance | Instruction Adherence | Deterministic Reproducibility | Unsafe Code Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5 Coder 1.5B (Transformers Tiny) | 0 | 2 | 2 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | N/A | 1.000 | 1.000 | 1.000 | N/A | 0.000 |

## Table B: Operational Metrics
| Model | Time Budget (min) | Tasks Completed | Avg Latency / Task (s) | P95 Latency (s) | Tokens/sec | Peak RAM (GB) | Avg Output Tokens | Cost / Request |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5 Coder 1.5B (Transformers Tiny) | 4 | 2 | 97.176 | 150.281 | 0.648 | 0.013 | 48.500 | 0.000 |
