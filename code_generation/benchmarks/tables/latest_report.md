# Code Generation Evaluation Report

## Table A: Capability Metrics
| Model | MBPP Attempted | Total Attempted | pass@1 | Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | Format Compliance | Signature Compliance | Instruction Adherence | Unsafe Code Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5 Coder 0.5B (Transformers Fast) | 20 | 20 | 0.100 | 0.250 | 0.250 | 0.400 | 0.100 | 0.750 | 0.750 | 0.750 | 0.000 |
| DeepSeek Coder 1.3B (Transformers Fast) | 6 | 6 | 0.167 | 0.667 | 0.000 | 0.167 | 0.167 | 0.000 | 0.333 | 0.000 | 0.000 |
| Qwen2.5 Coder 1.5B (Transformers Fast) | 3 | 3 | 0.667 | 0.333 | 0.000 | 0.000 | 0.667 | 0.667 | 0.667 | 0.667 | 0.000 |
| Gemini 2.5 Flash Lite (Baseline) | 20 | 20 | 0.150 | 0.100 | 0.450 | 0.300 | 0.150 | 0.550 | 0.550 | 0.550 | 0.000 |

## Table B: Operational Metrics
| Model | Time Budget (min) | Tasks Completed | Avg Latency / Task (s) | P95 Latency (s) | Tokens/sec | Peak RAM (GB) | Avg Output Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5 Coder 0.5B (Transformers Fast) | 4 | 20 | 6.131 | 9.615 | 7.027 | 0.014 | 41.450 |
| DeepSeek Coder 1.3B (Transformers Fast) | 4 | 6 | 45.797 | 49.950 | 1.296 | 0.013 | 59.333 |
| Qwen2.5 Coder 1.5B (Transformers Fast) | 4 | 3 | 94.947 | 125.208 | 0.578 | 0.013 | 54.333 |
| Gemini 2.5 Flash Lite (Baseline) | 4 | 13 | 0.665 | 0.871 | 110.141 | 0.013 | 59.538 |
