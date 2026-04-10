# Benchmark 75 Business Dashboard

This dashboard uses SDDF capability/risk plus explicit proxy economics to estimate unit economics, expected value/loss, and break-even routing.

## Assumptions

- Success value per correct query: $0.0500
- Failure loss per semantic failure: $0.2000
- Latency cost per second: $0.0001
- Local inference cost per second: $0.0002
- Baseline API cost per query: $0.0035

## classification

- Pareto frontier: qwen2.5:0.5b, qwen2.5:3b, qwen2.5:7b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\classification_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| qwen2.5:0.5b | 0.377 | 0.156 | 0.615 | 1.625 | $0.0001 | $-0.0125 | frontier | NA | 0.010 | 0.000 |
| qwen2.5:3b | 0.564 | 0.109 | 7.436 | 0.134 | $0.0015 | $0.0041 | frontier | NA | 0.022 | 0.000 |
| qwen2.5:7b | 0.445 | 0.139 | 3.383 | 0.296 | $0.0007 | $-0.0065 | frontier | NA | 0.007 | 0.000 |
| groq:llama-3.3-70b-versatile | 0.595 | 0.101 | 0.587 | 1.705 | $0.0035 | $0.0059 | frontier | NA | 0.002 | 0.000 |

## code_generation

- Pareto frontier: qwen2.5:0.5b, qwen2.5:3b, qwen2.5:7b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\code_generation_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| qwen2.5:0.5b | 0.452 | 0.269 | 6.539 | 0.153 | $0.0013 | $-0.0331 | frontier | NA | 0.005 | 0.000 |
| qwen2.5:3b | 0.465 | 0.262 | 12.946 | 0.077 | $0.0026 | $-0.0331 | frontier | NA | 0.005 | 0.000 |
| qwen2.5:7b | 0.514 | 0.238 | 30.641 | 0.033 | $0.0061 | $-0.0311 | frontier | NA | 0.005 | 0.000 |
| groq:llama-3.3-70b-versatile | 0.498 | 0.246 | 0.524 | 1.908 | $0.0035 | $-0.0278 | frontier | NA | 0.005 | 0.000 |

## information_extraction

- Pareto frontier: qwen2.5:0.5b, qwen2.5:3b, qwen2.5:7b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\information_extraction_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| qwen2.5:0.5b | 0.682 | 0.096 | 1.957 | 0.511 | $0.0004 | $0.0142 | frontier | NA | 0.005 | 0.000 |
| qwen2.5:3b | 0.697 | 0.092 | 7.647 | 0.131 | $0.0015 | $0.0143 | frontier | NA | 0.005 | 0.000 |
| qwen2.5:7b | 0.800 | 0.060 | 11.038 | 0.091 | $0.0022 | $0.0246 | frontier | NA | 0.010 | 0.000 |
| groq:llama-3.3-70b-versatile | 0.804 | 0.059 | 0.398 | 2.513 | $0.0035 | $0.0248 | frontier | NA | 0.010 | 0.000 |

## instruction_following

- Pareto frontier: qwen2.5:0.5b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\instruction_following_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| qwen2.5:0.5b | 0.562 | 0.120 | 6.509 | 0.154 | $0.0013 | $0.0021 | frontier | NA | 0.005 | 0.000 |
| qwen2.5:3b | 0.713 | 0.079 | 17.579 | 0.057 | $0.0035 | $0.0146 | dominated | NA | 0.010 | 0.000 |
| qwen2.5:7b | 0.632 | 0.101 | 26.888 | 0.037 | $0.0054 | $0.0033 | dominated | NA | 0.017 | 0.000 |
| groq:llama-3.3-70b-versatile | 0.843 | 0.043 | 1.329 | 0.752 | $0.0035 | $0.0298 | frontier | NA | 0.000 | 0.000 |

## maths

- Pareto frontier: qwen2.5:0.5b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\maths_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| qwen2.5:0.5b | 0.248 | 0.271 | 12.450 | 0.080 | $0.0025 | $-0.0455 | frontier | NA | 0.000 | 0.000 |
| qwen2.5:3b | 0.546 | 0.163 | 25.169 | 0.040 | $0.0050 | $-0.0129 | dominated | NA | 0.005 | 0.000 |
| qwen2.5:7b | 0.706 | 0.106 | 163.997 | 0.006 | $0.0328 | $-0.0351 | dominated | NA | 0.007 | 0.000 |
| groq:llama-3.3-70b-versatile | 0.771 | 0.082 | 0.850 | 1.176 | $0.0035 | $0.0185 | frontier | NA | 0.010 | 0.000 |

## retrieval_grounded

- Pareto frontier: qwen2.5:0.5b, qwen2.5:3b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\retrieval_grounded_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| qwen2.5:0.5b | 0.463 | 0.162 | 2.058 | 0.486 | $0.0004 | $-0.0099 | frontier | NA | 0.005 | 0.000 |
| qwen2.5:3b | 0.607 | 0.119 | 12.458 | 0.080 | $0.0025 | $0.0028 | frontier | NA | 0.010 | 0.000 |
| qwen2.5:7b | 0.558 | 0.134 | 12.811 | 0.078 | $0.0026 | $-0.0026 | dominated | NA | 0.000 | 0.000 |
| groq:llama-3.3-70b-versatile | 0.684 | 0.096 | 1.251 | 0.799 | $0.0035 | $0.0114 | frontier | NA | 0.007 | 0.000 |

## summarization

- Pareto frontier: qwen2.5:0.5b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\summarization_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| qwen2.5:0.5b | 0.727 | 0.049 | 2.962 | 0.338 | $0.0006 | $0.0256 | frontier | NA | 0.005 | 0.000 |
| qwen2.5:3b | 0.674 | 0.059 | 14.016 | 0.071 | $0.0028 | $0.0177 | dominated | NA | 0.003 | 0.000 |
| qwen2.5:7b | 0.686 | 0.057 | 18.849 | 0.053 | $0.0038 | $0.0173 | dominated | NA | 0.005 | 0.000 |
| groq:llama-3.3-70b-versatile | 0.606 | 0.071 | 0.607 | 1.648 | $0.0035 | $0.0125 | frontier | NA | 0.002 | 0.000 |

## text_generation

- Pareto frontier: qwen2.5:0.5b, qwen2.5:7b, groq:llama-3.3-70b-versatile
- Task status: ok
- Chart: `model_runs\business_analytics\text_generation_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| qwen2.5:0.5b | 0.549 | 0.063 | 1.504 | 0.665 | $0.0003 | $0.0144 | frontier | NA | 0.000 | 0.000 |
| qwen2.5:3b | 0.648 | 0.049 | 8.105 | 0.123 | $0.0016 | $0.0201 | dominated | NA | 0.000 | 0.000 |
| qwen2.5:7b | 0.838 | 0.023 | 5.170 | 0.193 | $0.0010 | $0.0359 | frontier | NA | 0.010 | 0.000 |
| groq:llama-3.3-70b-versatile | 1.000 | 0.000 | 0.678 | 1.475 | $0.0035 | $0.0464 | frontier | NA | 0.010 | 0.000 |

