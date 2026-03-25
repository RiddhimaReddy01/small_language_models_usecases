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
- Chart: `model_runs\benchmark_75\business_analytics\classification_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Empirical Strategy | Certified Strategy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| tinyllama:1.1b | 0.970 | 0.030 | 45.147 | 0.022 | $0.0090 | $0.0290 | dominated | 1.0 | 0.0 |
| qwen2.5:1.5b | 0.960 | 0.040 | 3.287 | 0.304 | $0.0007 | $0.0390 | frontier | 1.0 | 0.0 |
| phi3:mini | 1.000 | 0.000 | 9.475 | 0.106 | $0.0019 | $0.0472 | frontier | 1.0 | 0.0 |
| groq:llama-3.3-70b-versatile | 0.987 | 0.013 | 3.227 | 0.310 | $0.0035 | $0.0428 | frontier | 1.0 | 0.0 |

## code_generation

- Pareto frontier: qwen2.5:1.5b, groq:llama-3.3-70b-versatile
- Chart: `model_runs\benchmark_75\business_analytics\code_generation_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Empirical Strategy | Certified Strategy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| tinyllama:1.1b | 0.000 | 1.000 | 41.495 | 0.024 | $0.0083 | $-0.2124 | dominated | 0.0 | 0.0 |
| qwen2.5:1.5b | 0.903 | 0.097 | 10.288 | 0.097 | $0.0021 | $0.0227 | frontier | 1.0 | 0.0 |
| phi3:mini | 0.000 | 1.000 | 16.142 | 0.062 | $0.0032 | $-0.2048 | dominated | 0.0 | 0.0 |
| groq:llama-3.3-70b-versatile | 0.000 | 1.000 | 3.517 | 0.284 | $0.0035 | $-0.2039 | frontier | 0.0 | 0.0 |

## information_extraction

- Pareto frontier: qwen2.5:1.5b, groq:llama-3.3-70b-versatile
- Chart: `model_runs\benchmark_75\business_analytics\information_extraction_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Empirical Strategy | Certified Strategy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| tinyllama:1.1b | 0.867 | 0.133 | 5.406 | 0.185 | $0.0011 | $0.0150 | dominated | 1.0 | 0.0 |
| qwen2.5:1.5b | 0.973 | 0.027 | 2.403 | 0.416 | $0.0005 | $0.0426 | frontier | 1.0 | 0.0 |
| phi3:mini | 0.947 | 0.053 | 6.757 | 0.148 | $0.0014 | $0.0346 | dominated | 1.0 | 0.0 |
| groq:llama-3.3-70b-versatile | 1.000 | 0.000 | 3.176 | 0.315 | $0.0035 | $0.0462 | frontier | 1.0 | 0.0 |

## instruction_following

- Pareto frontier: tinyllama:1.1b, qwen2.5:1.5b, phi3:mini, groq:llama-3.3-70b-versatile
- Chart: `model_runs\benchmark_75\business_analytics\instruction_following_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Empirical Strategy | Certified Strategy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| tinyllama:1.1b | 0.760 | 0.240 | 5.340 | 0.187 | $0.0011 | $-0.0116 | frontier | 1.0 | 0.0 |
| qwen2.5:1.5b | 0.853 | 0.147 | 6.273 | 0.159 | $0.0013 | $0.0115 | frontier | 1.0 | 0.0 |
| phi3:mini | 0.667 | 0.333 | 3.021 | 0.331 | $0.0006 | $-0.0342 | frontier | 0.0 | 0.0 |
| groq:llama-3.3-70b-versatile | 1.000 | 0.000 | 3.152 | 0.317 | $0.0035 | $0.0462 | frontier | 1.0 | 0.0 |

## maths

- Pareto frontier: qwen2.5:1.5b, groq:llama-3.3-70b-versatile
- Chart: `model_runs\benchmark_75\business_analytics\maths_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Empirical Strategy | Certified Strategy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| tinyllama:1.1b | 0.121 | 0.879 | 45.503 | 0.022 | $0.0091 | $-0.1833 | dominated | 0.0 | 0.0 |
| qwen2.5:1.5b | 0.750 | 0.250 | 6.768 | 0.148 | $0.0014 | $-0.0145 | frontier | 1.0 | 0.0 |
| phi3:mini | 0.687 | 0.313 | 25.154 | 0.040 | $0.0050 | $-0.0357 | dominated | 0.8450704225352113 | 0.0 |
| groq:llama-3.3-70b-versatile | 0.942 | 0.058 | 3.314 | 0.302 | $0.0035 | $0.0316 | frontier | 1.0 | 0.0 |

## retrieval_grounded

- Pareto frontier: qwen2.5:1.5b, groq:llama-3.3-70b-versatile
- Chart: `model_runs\benchmark_75\business_analytics\retrieval_grounded_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Empirical Strategy | Certified Strategy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| tinyllama:1.1b | 0.773 | 0.227 | 12.717 | 0.079 | $0.0025 | $-0.0105 | dominated | 1.0 | 0.0 |
| qwen2.5:1.5b | 1.000 | 0.000 | 4.780 | 0.209 | $0.0010 | $0.0486 | frontier | 1.0 | 0.0 |
| phi3:mini | 0.880 | 0.120 | 8.897 | 0.112 | $0.0018 | $0.0173 | dominated | 1.0 | 0.0 |
| groq:llama-3.3-70b-versatile | 1.000 | 0.000 | 3.230 | 0.310 | $0.0035 | $0.0462 | frontier | 1.0 | 0.0 |

## summarization

- Pareto frontier: tinyllama:1.1b, groq:llama-3.3-70b-versatile
- Chart: `model_runs\benchmark_75\business_analytics\summarization_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Empirical Strategy | Certified Strategy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| tinyllama:1.1b | 0.987 | 0.013 | 12.618 | 0.079 | $0.0025 | $0.0429 | frontier | 1.0 | 0.0 |
| qwen2.5:1.5b | 0.773 | 0.227 | 13.741 | 0.073 | $0.0027 | $-0.0108 | dominated | 1.0 | 0.0 |
| phi3:mini | 0.987 | 0.013 | 14.236 | 0.070 | $0.0028 | $0.0424 | dominated | 1.0 | 0.0 |
| groq:llama-3.3-70b-versatile | 1.000 | 0.000 | 3.375 | 0.296 | $0.0035 | $0.0462 | frontier | 1.0 | 0.0 |

## text_generation

- Pareto frontier: qwen2.5:1.5b, phi3:mini, groq:llama-3.3-70b-versatile
- Chart: `model_runs\benchmark_75\business_analytics\text_generation_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Empirical Strategy | Certified Strategy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| tinyllama:1.1b | 0.650 | 0.350 | 41.695 | 0.024 | $0.0083 | $-0.0500 | dominated | 0.9574468085106383 | 0.0 |
| qwen2.5:1.5b | 0.033 | 0.967 | 9.169 | 0.109 | $0.0018 | $-0.1944 | frontier | 0.0 | 0.0 |
| phi3:mini | 0.133 | 0.867 | 17.044 | 0.059 | $0.0034 | $-0.1718 | frontier | 0.0 | 0.0 |
| groq:llama-3.3-70b-versatile | 1.000 | 0.000 | 14.081 | 0.071 | $0.0035 | $0.0451 | frontier | 0.9574468085106383 | 0.0 |

