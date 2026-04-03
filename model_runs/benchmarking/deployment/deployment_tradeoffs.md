# Deployment Tradeoffs (Separate from Train/Val/Test)

| Task | Model | N | SLM% | HYBRID% | BASELINE% | Avg Cost | Avg Latency(s) | Avg Risk | Avg Capability | Unsafe Rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| classification | groq:llama-3.3-70b-versatile | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 3.101 | 0.000 | 1.000 | 0.000 |
| classification | phi3:mini | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 8.818 | 0.000 | 1.000 | 0.000 |
| classification | qwen2.5:1.5b | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 3.999 | 0.096 | 0.850 | 0.150 |
| classification | tinyllama:1.1b | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 33.269 | 0.064 | 0.900 | 0.100 |
| code_generation | groq:llama-3.3-70b-versatile | 20 | 0.950 | 0.050 | 0.000 | 1.075 | 3.055 | 0.000 | 1.000 | 0.000 |
| code_generation | phi3:mini | 20 | 0.100 | 0.100 | 0.800 | 5.150 | 10.026 | 0.137 | 0.750 | 0.150 |
| code_generation | qwen2.5:1.5b | 20 | 0.000 | 0.000 | 1.000 | 6.000 | 8.174 | 0.162 | 0.800 | 0.200 |
| code_generation | tinyllama:1.1b | 20 | 0.000 | 0.000 | 1.000 | 6.000 | 22.010 | 0.162 | 0.800 | 0.200 |
| information_extraction | groq:llama-3.3-70b-versatile | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 2.849 | 0.000 | 1.000 | 0.000 |
| information_extraction | phi3:mini | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 8.431 | 0.010 | 0.950 | 0.050 |
| information_extraction | qwen2.5:1.5b | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 4.289 | 0.010 | 0.950 | 0.050 |
| information_extraction | tinyllama:1.1b | 20 | 0.950 | 0.000 | 0.050 | 1.250 | 4.900 | 0.020 | 0.900 | 0.100 |
| instruction_following | groq:llama-3.3-70b-versatile | 20 | 0.950 | 0.050 | 0.000 | 1.075 | 2.475 | 0.024 | 0.950 | 0.050 |
| instruction_following | phi3:mini | 20 | 0.000 | 0.500 | 0.500 | 4.250 | 6.754 | 0.171 | 0.650 | 0.350 |
| instruction_following | qwen2.5:1.5b | 20 | 0.950 | 0.050 | 0.000 | 1.075 | 6.321 | 0.122 | 0.750 | 0.250 |
| instruction_following | tinyllama:1.1b | 20 | 0.500 | 0.000 | 0.500 | 3.500 | 5.239 | 0.245 | 0.500 | 0.500 |
| maths | groq:llama-3.3-70b-versatile | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 2.710 | 0.072 | 0.900 | 0.100 |
| maths | phi3:mini | 20 | 0.300 | 0.050 | 0.650 | 4.325 | 10.331 | 0.216 | 0.700 | 0.300 |
| maths | qwen2.5:1.5b | 20 | 0.000 | 0.000 | 1.000 | 6.000 | 6.216 | 0.432 | 0.400 | 0.600 |
| maths | tinyllama:1.1b | 20 | 0.000 | 0.000 | 1.000 | 6.000 | 23.031 | 0.648 | 0.100 | 0.900 |
| retrieval_grounded | groq:llama-3.3-70b-versatile | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 2.512 | 0.000 | 1.000 | 0.000 |
| retrieval_grounded | phi3:mini | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 8.409 | 0.070 | 0.850 | 0.100 |
| retrieval_grounded | qwen2.5:1.5b | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 5.038 | 0.000 | 1.000 | 0.000 |
| retrieval_grounded | tinyllama:1.1b | 20 | 0.750 | 0.100 | 0.150 | 1.900 | 7.855 | 0.104 | 0.800 | 0.150 |
| summarization | groq:llama-3.3-70b-versatile | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 2.690 | 0.021 | 0.950 | 0.050 |
| summarization | phi3:mini | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 9.703 | 0.042 | 0.900 | 0.100 |
| summarization | qwen2.5:1.5b | 20 | 0.450 | 0.050 | 0.500 | 3.575 | 6.167 | 0.147 | 0.650 | 0.350 |
| summarization | tinyllama:1.1b | 20 | 1.000 | 0.000 | 0.000 | 1.000 | 6.157 | 0.105 | 0.750 | 0.250 |
| text_generation | groq:llama-3.3-70b-versatile | 19 | 1.000 | 0.000 | 0.000 | 1.000 | 2.738 | 0.022 | 0.947 | 0.053 |
| text_generation | phi3:mini | 19 | 1.000 | 0.000 | 0.000 | 1.000 | 8.748 | 0.111 | 0.737 | 0.263 |
| text_generation | qwen2.5:1.5b | 19 | 0.000 | 0.000 | 1.000 | 6.000 | 6.146 | 0.221 | 0.474 | 0.526 |
| text_generation | tinyllama:1.1b | 19 | 1.000 | 0.000 | 0.000 | 1.000 | 7.779 | 0.088 | 0.789 | 0.211 |
