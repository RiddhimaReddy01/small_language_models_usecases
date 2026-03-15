# Code Generation Evaluation Report

## Table A: Capability Metrics
| Model | HumanEval Attempted | MBPP Attempted | Total Attempted | pass@1 | Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | Self-Consistency Score | Format Compliance | Signature Compliance | Instruction Adherence | Deterministic Reproducibility | Unsafe Code Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SmolLM2 360M (Transformers Tiny) | 0 | 2 | 2 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | N/A | 1.000 | 1.000 | 1.000 | N/A | 0.000 |

## Table B: Operational Metrics
| Model | Time Budget (min) | Tasks Completed | Avg Latency / Task (s) | P95 Latency (s) | Tokens/sec | Peak RAM (GB) | Avg Output Tokens | Cost / Request |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SmolLM2 360M (Transformers Tiny) | 3 | 2 | 5.698 | 5.930 | 8.105 | 0.013 | 45 | 0.000 |
