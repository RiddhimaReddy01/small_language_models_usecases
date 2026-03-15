# Code Generation Evaluation Report

## Table A: Capability Metrics
| Model | HumanEval Attempted | MBPP Attempted | Total Attempted | pass@1 | Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | Self-Consistency Score | Format Compliance | Signature Compliance | Instruction Adherence | Deterministic Reproducibility | Unsafe Code Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5 Coder 0.5B (Transformers Tiny) | 0 | 2 | 2 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | N/A | 0.500 | 0.000 | 0.500 | N/A | 0.000 |

## Table B: Operational Metrics
| Model | Time Budget (min) | Tasks Completed | Avg Latency / Task (s) | P95 Latency (s) | Tokens/sec | Peak RAM (GB) | Avg Output Tokens | Cost / Request |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5 Coder 0.5B (Transformers Tiny) | 3 | 2 | 7.437 | 7.654 | 8.613 | 0.000 | 64 | 0.000 |
