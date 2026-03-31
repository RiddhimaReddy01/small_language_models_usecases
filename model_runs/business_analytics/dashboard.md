# Benchmark 75 Business Dashboard

This dashboard uses SDDF capability/risk plus explicit proxy economics to estimate unit economics, expected value/loss, and break-even routing.

## Assumptions

- Success value per correct query: $0.0500
- Failure loss per semantic failure: $0.2000
- Latency cost per second: $0.0001
- Local inference cost per second: $0.0002
- Baseline API cost per query: $0.0035

## classification

- Pareto frontier: qwen2.5:1.5b, phi3:mini, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\classification_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| tinyllama:1.1b | 0.884 | 0.116 | 17.561 | 0.057 | $0.0035 | $0.0157 | dominated | 0 | 0.000 | 0.209 |
| qwen2.5:1.5b | 0.953 | 0.047 | 5.236 | 0.191 | $0.0010 | $0.0368 | frontier | 1 | 0.000 | 0.372 |
| phi3:mini | 1.000 | 0.000 | 8.351 | 0.120 | $0.0017 | $0.0475 | frontier | 4 | 0.000 | 1.000 |
| groq:llama-3.3-70b-versatile | 0.977 | 0.023 | 2.775 | 0.360 | $0.0035 | $0.0404 | frontier | 4 | 0.000 | 1.000 |

## code_generation

- Pareto frontier: qwen2.5:1.5b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\code_generation_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| tinyllama:1.1b | 0.667 | 0.333 | 17.573 | 0.057 | $0.0035 | $-0.0386 | dominated | NA | 0.000 | 0.000 |
| qwen2.5:1.5b | 0.778 | 0.222 | 7.505 | 0.133 | $0.0015 | $-0.0078 | frontier | NA | 0.000 | 0.000 |
| phi3:mini | 0.750 | 0.250 | 10.750 | 0.093 | $0.0021 | $-0.0157 | dominated | NA | 0.000 | 0.000 |
| groq:llama-3.3-70b-versatile | 0.917 | 0.083 | 2.824 | 0.354 | $0.0035 | $0.0254 | frontier | 3 | 0.000 | 0.861 |

## information_extraction

- Pareto frontier: tinyllama:1.1b, qwen2.5:1.5b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\information_extraction_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| tinyllama:1.1b | 0.765 | 0.235 | 4.743 | 0.211 | $0.0009 | $-0.0102 | frontier | 0 | 0.000 | 0.353 |
| qwen2.5:1.5b | 0.941 | 0.059 | 4.874 | 0.205 | $0.0010 | $0.0338 | frontier | 3 | 0.000 | 0.824 |
| phi3:mini | 0.765 | 0.235 | 7.525 | 0.133 | $0.0015 | $-0.0111 | dominated | 2 | 0.000 | 0.676 |
| groq:llama-3.3-70b-versatile | 1.000 | 0.000 | 2.731 | 0.366 | $0.0035 | $0.0462 | frontier | 4 | 0.000 | 1.000 |

## instruction_following

- Pareto frontier: tinyllama:1.1b, qwen2.5:1.5b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\instruction_following_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| tinyllama:1.1b | 0.794 | 0.206 | 4.769 | 0.210 | $0.0010 | $-0.0029 | frontier | 0 | 0.000 | 0.324 |
| qwen2.5:1.5b | 0.941 | 0.059 | 6.229 | 0.161 | $0.0012 | $0.0334 | frontier | 0 | 0.000 | 0.324 |
| phi3:mini | 0.794 | 0.206 | 6.474 | 0.154 | $0.0013 | $-0.0034 | dominated | 0 | 0.000 | 0.324 |
| groq:llama-3.3-70b-versatile | 0.941 | 0.059 | 2.647 | 0.378 | $0.0035 | $0.0315 | frontier | 0 | 0.000 | 0.324 |

## maths

- Pareto frontier: qwen2.5:1.5b, phi3:mini, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\maths_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| tinyllama:1.1b | 0.122 | 0.878 | 17.640 | 0.057 | $0.0035 | $-0.1748 | dominated | NA | 0.000 | 0.000 |
| qwen2.5:1.5b | 0.585 | 0.415 | 6.340 | 0.158 | $0.0013 | $-0.0556 | frontier | NA | 0.000 | 0.000 |
| phi3:mini | 0.732 | 0.268 | 13.131 | 0.076 | $0.0026 | $-0.0210 | frontier | NA | 0.000 | 0.000 |
| groq:llama-3.3-70b-versatile | 0.951 | 0.049 | 2.719 | 0.368 | $0.0035 | $0.0340 | frontier | 1 | 0.000 | 0.537 |

## retrieval_grounded

- Pareto frontier: qwen2.5:1.5b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\retrieval_grounded_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| tinyllama:1.1b | 0.781 | 0.219 | 6.474 | 0.154 | $0.0013 | $-0.0066 | dominated | NA | 0.000 | 0.000 |
| qwen2.5:1.5b | 0.906 | 0.094 | 5.620 | 0.178 | $0.0011 | $0.0249 | frontier | 2 | 0.000 | 0.562 |
| phi3:mini | 0.906 | 0.094 | 8.343 | 0.120 | $0.0017 | $0.0241 | dominated | NA | 0.000 | 0.000 |
| groq:llama-3.3-70b-versatile | 1.000 | 0.000 | 2.746 | 0.364 | $0.0035 | $0.0462 | frontier | 4 | 0.000 | 1.000 |

## summarization

- Pareto frontier: tinyllama:1.1b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\summarization_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| tinyllama:1.1b | 0.946 | 0.054 | 6.513 | 0.154 | $0.0013 | $0.0345 | frontier | 2 | 0.000 | 0.541 |
| qwen2.5:1.5b | 0.838 | 0.162 | 8.276 | 0.121 | $0.0017 | $0.0070 | dominated | NA | 0.000 | 0.000 |
| phi3:mini | 0.892 | 0.108 | 9.811 | 0.102 | $0.0020 | $0.0200 | dominated | 1 | 0.000 | 0.243 |
| groq:llama-3.3-70b-versatile | 0.973 | 0.027 | 2.699 | 0.371 | $0.0035 | $0.0395 | frontier | 4 | 0.000 | 1.000 |

## text_generation

- Pareto frontier: qwen2.5:1.5b, phi3:mini, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\text_generation_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| tinyllama:1.1b | 0.879 | 0.121 | 17.513 | 0.057 | $0.0035 | $0.0144 | dominated | 3 | 0.000 | 0.818 |
| qwen2.5:1.5b | 0.636 | 0.364 | 6.875 | 0.145 | $0.0014 | $-0.0430 | frontier | NA | 0.000 | 0.000 |
| phi3:mini | 0.727 | 0.273 | 13.886 | 0.072 | $0.0028 | $-0.0223 | frontier | 2 | 0.000 | 0.545 |
| groq:llama-3.3-70b-versatile | 0.970 | 0.030 | 5.959 | 0.168 | $0.0035 | $0.0383 | frontier | 4 | 0.000 | 1.000 |

