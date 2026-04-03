# Test Phase Report (Frozen Policy)

| Task | Model | N | Frozen Policy | Pass Gate | Coverage(SLM) | Capability(SLM) | Risk(SLM) | F1 | Acc | dAcc vs Always-SLM | p(McNemar) | dUtility vs Always-SLM |
|---|---|---:|:---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|
| classification | tinyllama:1.1b | 20 | yes | yes | 1.000 | 0.900 | 0.064 | 0.947 | 0.900 | 0.000 | 1.0000 | 0.000 |
| classification | qwen2.5:1.5b | 20 | yes | yes | 1.000 | 0.850 | 0.096 | 0.919 | 0.850 | 0.000 | 1.0000 | 0.000 |
| classification | phi3:mini | 20 | yes | yes | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | 1.0000 | 0.000 |
| classification | groq:llama-3.3-70b-versatile | 20 | yes | yes | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | 1.0000 | 0.000 |
| code_generation | tinyllama:1.1b | 20 | yes | no | 0.000 | 0.000 | 1.000 | 0.000 | 0.200 | -0.600 | 0.0139 | -2.038 |
| code_generation | qwen2.5:1.5b | 20 | yes | no | 0.000 | 0.000 | 1.000 | 0.000 | 0.200 | -0.600 | 0.0139 | -2.038 |
| code_generation | phi3:mini | 20 | yes | no | 0.100 | 0.500 | 0.404 | 0.118 | 0.250 | -0.500 | 0.0339 | -1.229 |
| code_generation | groq:llama-3.3-70b-versatile | 20 | yes | yes | 0.950 | 1.000 | 0.000 | 0.974 | 0.950 | -0.050 | 1.0000 | -0.050 |
| information_extraction | tinyllama:1.1b | 20 | yes | yes | 0.950 | 0.895 | 0.021 | 0.919 | 0.850 | -0.050 | 1.0000 | -0.052 |
| information_extraction | qwen2.5:1.5b | 20 | yes | yes | 1.000 | 0.950 | 0.010 | 0.974 | 0.950 | 0.000 | 1.0000 | 0.000 |
| information_extraction | phi3:mini | 20 | yes | yes | 1.000 | 0.950 | 0.010 | 0.974 | 0.950 | 0.000 | 1.0000 | 0.000 |
| information_extraction | groq:llama-3.3-70b-versatile | 20 | yes | yes | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | 1.0000 | 0.000 |
| instruction_following | tinyllama:1.1b | 20 | yes | no | 0.500 | 0.300 | 0.343 | 0.300 | 0.300 | -0.200 | 0.3428 | -0.648 |
| instruction_following | qwen2.5:1.5b | 20 | yes | no | 0.950 | 0.789 | 0.103 | 0.882 | 0.800 | 0.050 | 1.0000 | -0.021 |
| instruction_following | phi3:mini | 20 | yes | no | 0.000 | 0.000 | 1.000 | 0.000 | 0.350 | -0.300 | 0.2636 | -1.991 |
| instruction_following | groq:llama-3.3-70b-versatile | 20 | yes | yes | 0.950 | 0.947 | 0.026 | 0.947 | 0.900 | -0.050 | 1.0000 | -0.052 |
| maths | tinyllama:1.1b | 20 | yes | no | 0.000 | 0.000 | 1.000 | 0.000 | 0.900 | 0.800 | 0.0008 | -1.377 |
| maths | qwen2.5:1.5b | 20 | yes | no | 0.000 | 0.000 | 1.000 | 0.000 | 0.600 | 0.200 | 0.5023 | -1.668 |
| maths | phi3:mini | 20 | yes | yes | 0.300 | 0.833 | 0.120 | 0.500 | 0.500 | -0.200 | 0.4227 | -0.571 |
| maths | groq:llama-3.3-70b-versatile | 20 | yes | yes | 1.000 | 0.900 | 0.072 | 0.947 | 0.900 | 0.000 | 1.0000 | 0.000 |
| retrieval_grounded | tinyllama:1.1b | 20 | yes | yes | 0.750 | 0.933 | 0.045 | 0.903 | 0.850 | 0.050 | 1.0000 | -0.158 |
| retrieval_grounded | qwen2.5:1.5b | 20 | yes | yes | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | 1.0000 | 0.000 |
| retrieval_grounded | phi3:mini | 20 | yes | yes | 1.000 | 0.850 | 0.070 | 0.919 | 0.850 | 0.000 | 1.0000 | 0.000 |
| retrieval_grounded | groq:llama-3.3-70b-versatile | 20 | yes | yes | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 | 1.0000 | 0.000 |
| summarization | tinyllama:1.1b | 20 | yes | no | 1.000 | 0.750 | 0.105 | 0.857 | 0.750 | 0.000 | 1.0000 | 0.000 |
| summarization | qwen2.5:1.5b | 20 | yes | yes | 0.450 | 0.889 | 0.047 | 0.727 | 0.700 | 0.050 | 1.0000 | -0.390 |
| summarization | phi3:mini | 20 | yes | yes | 1.000 | 0.900 | 0.042 | 0.947 | 0.900 | 0.000 | 1.0000 | 0.000 |
| summarization | groq:llama-3.3-70b-versatile | 20 | yes | yes | 1.000 | 0.950 | 0.021 | 0.974 | 0.950 | 0.000 | 1.0000 | 0.000 |
| text_generation | tinyllama:1.1b | 19 | yes | no | 1.000 | 0.789 | 0.088 | 0.882 | 0.789 | 0.000 | 1.0000 | 0.000 |
| text_generation | qwen2.5:1.5b | 19 | yes | no | 0.000 | 0.000 | 1.000 | 0.000 | 0.526 | 0.053 | 1.0000 | -1.897 |
| text_generation | phi3:mini | 19 | yes | no | 1.000 | 0.737 | 0.111 | 0.848 | 0.737 | 0.000 | 1.0000 | 0.000 |
| text_generation | groq:llama-3.3-70b-versatile | 19 | yes | yes | 1.000 | 0.947 | 0.022 | 0.973 | 0.947 | 0.000 | 1.0000 | 0.000 |
