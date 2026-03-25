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
| tinyllama:1.1b | 0.933 | 0.067 | 47.745 | 0.021 | $0.0095 | $0.0190 | dominated | 1.0 | 0.0 |
| qwen2.5:1.5b | 0.947 | 0.053 | 3.287 | 0.304 | $0.0007 | $0.0357 | frontier | 1.0 | 0.0 |
| phi3:mini | 1.000 | 0.000 | 9.475 | 0.106 | $0.0019 | $0.0472 | frontier | 1.0 | 0.0 |
| groq:llama-3.3-70b-versatile | 0.987 | 0.013 | 3.227 | 0.310 | $0.0035 | $0.0428 | frontier | 1.0 | 0.0 |

## code_generation

- Pareto frontier: qwen2.5:1.5b, groq:llama-3.3-70b-versatile
- Chart: `model_runs\benchmark_75\business_analytics\code_generation_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Empirical Strategy | Certified Strategy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| tinyllama:1.1b | 0.027 | 0.973 | 48.206 | 0.021 | $0.0096 | $-0.2078 | dominated | 0.0 | 0.0 |
| qwen2.5:1.5b | 0.907 | 0.093 | 10.288 | 0.097 | $0.0021 | $0.0236 | frontier | 1.0 | 0.0 |
| phi3:mini | 0.013 | 0.987 | 17.120 | 0.058 | $0.0034 | $-0.2018 | dominated | 0.0 | 0.0 |
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
| tinyllama:1.1b | 0.067 | 0.933 | 47.921 | 0.021 | $0.0096 | $-0.1977 | dominated | 0.0 | 0.0 |
| qwen2.5:1.5b | 0.747 | 0.253 | 6.768 | 0.148 | $0.0014 | $-0.0154 | frontier | 1.0 | 0.0 |
| phi3:mini | 0.693 | 0.307 | 25.154 | 0.040 | $0.0050 | $-0.0342 | dominated | 0.8 | 0.0 |
| groq:llama-3.3-70b-versatile | 0.947 | 0.053 | 3.314 | 0.302 | $0.0035 | $0.0328 | frontier | 1.0 | 0.0 |

## retrieval_grounded

- Pareto frontier: qwen2.5:1.5b, groq:llama-3.3-70b-versatile
- Chart: `model_runs\benchmark_75\business_analytics\retrieval_grounded_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Empirical Strategy | Certified Strategy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| tinyllama:1.1b | 0.787 | 0.213 | 11.134 | 0.090 | $0.0022 | $-0.0067 | dominated | 0.8 | 0.0 |
| qwen2.5:1.5b | 1.000 | 0.000 | 4.780 | 0.209 | $0.0010 | $0.0486 | frontier | 1.0 | 0.0 |
| phi3:mini | 0.880 | 0.120 | 8.897 | 0.112 | $0.0018 | $0.0173 | dominated | 1.0 | 0.0 |
| groq:llama-3.3-70b-versatile | 1.000 | 0.000 | 3.230 | 0.310 | $0.0035 | $0.0462 | frontier | 1.0 | 0.0 |

## summarization

- Pareto frontier: tinyllama:1.1b, groq:llama-3.3-70b-versatile
- Chart: `model_runs\benchmark_75\business_analytics\summarization_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Empirical Strategy | Certified Strategy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| tinyllama:1.1b | 1.000 | 0.000 | 11.090 | 0.090 | $0.0022 | $0.0467 | frontier | 1.0 | 0.0 |
| qwen2.5:1.5b | 0.773 | 0.227 | 13.741 | 0.073 | $0.0027 | $-0.0108 | dominated | 1.0 | 0.0 |
| phi3:mini | 0.987 | 0.013 | 14.236 | 0.070 | $0.0028 | $0.0424 | dominated | 1.0 | 0.0 |
| groq:llama-3.3-70b-versatile | 1.000 | 0.000 | 3.375 | 0.296 | $0.0035 | $0.0462 | frontier | 1.0 | 0.0 |

## text_generation

- Pareto frontier: qwen2.5:1.5b, groq:llama-3.3-70b-versatile
- Chart: `model_runs\benchmark_75\business_analytics\text_generation_pareto.png`

| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Empirical Strategy | Certified Strategy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| tinyllama:1.1b | 0.987 | 0.013 | 48.123 | 0.021 | $0.0096 | $0.0322 | dominated | 1.0 | 0.0 |
| qwen2.5:1.5b | 0.053 | 0.947 | 9.169 | 0.109 | $0.0018 | $-0.1894 | frontier | 0.0 | 0.0 |
| phi3:mini | 0.493 | 0.507 | 27.549 | 0.036 | $0.0055 | $-0.0849 | dominated | 1.0 | 0.0 |
| groq:llama-3.3-70b-versatile | 0.987 | 0.013 | 14.081 | 0.071 | $0.0035 | $0.0418 | frontier | 1.0 | 0.0 |

