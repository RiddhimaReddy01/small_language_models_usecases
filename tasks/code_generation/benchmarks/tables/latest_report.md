# Code Generation Evaluation Report

## Table A: Capability Metrics
| Model | MBPP Attempted | Total Attempted | pass@1 | Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | Format Compliance | Signature Compliance | Instruction Adherence | Unsafe Code Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Llama 3.2 1B (HF API) | 1 | 2 | 0.000 | 0.000 | 0.500 | 0.500 | 0.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| Gemini Flash | 1 | 2 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Table B: Operational Metrics
| Model | Time Budget (min) | Tasks Completed | Avg Latency / Task (s) | P95 Latency (s) | Tokens/sec | Peak RAM (GB) | Avg Output Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| Llama 3.2 1B (HF API) | 2 | 2 | 1.196 | 1.387 | 24.919 | 0.011 | 26.500 |
| Gemini Flash | 2 | 2 | 1.143 | 1.158 | 5.251 | 0.000 | 6 |
