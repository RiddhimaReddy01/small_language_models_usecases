# Val Phase Report (Frozen Policy)

| Task | Model | N | Frozen Policy | Pass Gate | Coverage(SLM) | Capability(SLM) | Risk(SLM) | F1 | Acc | dAcc vs Always-SLM | p(McNemar) | dUtility vs Always-SLM |
|---|---|---:|:---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|
| classification | tinyllama:1.1b | 200 | yes | yes | 0.985 | 0.858 | 0.093 | 0.921 | 0.855 | 0.005 | 1.0000 | -0.008 |
| classification | qwen2.5:1.5b | 200 | yes | yes | 0.985 | 0.904 | 0.062 | 0.944 | 0.895 | -0.005 | 1.0000 | -0.012 |
| classification | phi3:mini | 200 | yes | yes | 0.985 | 0.975 | 0.016 | 0.980 | 0.960 | -0.015 | 0.2482 | -0.015 |
| classification | groq:llama-3.3-70b-versatile | 200 | yes | yes | 0.985 | 0.964 | 0.023 | 0.974 | 0.950 | -0.015 | 0.2482 | -0.015 |
| code_generation | tinyllama:1.1b | 200 | yes | no | 0.000 | 0.000 | 1.000 | 0.000 | 0.355 | -0.290 | 0.0001 | -1.877 |
| code_generation | qwen2.5:1.5b | 200 | yes | no | 0.000 | 0.000 | 1.000 | 0.000 | 0.225 | -0.550 | 0.0000 | -2.022 |
| code_generation | phi3:mini | 200 | yes | yes | 0.105 | 0.905 | 0.077 | 0.221 | 0.330 | -0.425 | 0.0000 | -0.769 |
| code_generation | groq:llama-3.3-70b-versatile | 200 | yes | yes | 0.995 | 0.935 | 0.053 | 0.966 | 0.935 | 0.005 | 1.0000 | -0.000 |
| information_extraction | tinyllama:1.1b | 200 | yes | no | 0.845 | 0.799 | 0.041 | 0.854 | 0.770 | 0.035 | 0.2812 | -0.126 |
| information_extraction | qwen2.5:1.5b | 200 | yes | yes | 0.985 | 0.914 | 0.017 | 0.947 | 0.900 | -0.015 | 0.2482 | -0.016 |
| information_extraction | phi3:mini | 200 | yes | yes | 0.985 | 0.848 | 0.031 | 0.915 | 0.845 | 0.005 | 1.0000 | -0.012 |
| information_extraction | groq:llama-3.3-70b-versatile | 200 | yes | yes | 0.985 | 0.980 | 0.004 | 0.982 | 0.965 | -0.015 | 0.2482 | -0.015 |
| instruction_following | tinyllama:1.1b | 200 | yes | yes | 0.555 | 0.811 | 0.097 | 0.674 | 0.565 | -0.215 | 0.0000 | -0.424 |
| instruction_following | qwen2.5:1.5b | 200 | yes | yes | 0.925 | 0.827 | 0.085 | 0.872 | 0.775 | -0.055 | 0.0098 | -0.077 |
| instruction_following | phi3:mini | 200 | yes | yes | 0.050 | 1.000 | 0.000 | 0.136 | 0.365 | -0.320 | 0.0000 | -0.717 |
| instruction_following | groq:llama-3.3-70b-versatile | 200 | yes | yes | 0.925 | 0.930 | 0.034 | 0.925 | 0.860 | -0.075 | 0.0003 | -0.079 |
| maths | tinyllama:1.1b | 200 | yes | no | 0.000 | 0.000 | 1.000 | 0.000 | 0.905 | 0.810 | 0.0000 | -1.372 |
| maths | qwen2.5:1.5b | 200 | yes | no | 0.000 | 0.000 | 1.000 | 0.000 | 0.335 | -0.330 | 0.0000 | -1.925 |
| maths | phi3:mini | 200 | yes | yes | 0.445 | 0.831 | 0.121 | 0.649 | 0.600 | -0.095 | 0.0875 | -0.423 |
| maths | groq:llama-3.3-70b-versatile | 200 | yes | yes | 0.985 | 0.909 | 0.066 | 0.945 | 0.895 | -0.015 | 0.2482 | -0.016 |
| retrieval_grounded | tinyllama:1.1b | 200 | yes | no | 0.715 | 0.797 | 0.102 | 0.773 | 0.665 | -0.095 | 0.0171 | -0.253 |
| retrieval_grounded | qwen2.5:1.5b | 200 | yes | yes | 0.985 | 0.929 | 0.048 | 0.961 | 0.925 | 0.005 | 1.0000 | -0.007 |
| retrieval_grounded | phi3:mini | 200 | yes | yes | 0.985 | 0.848 | 0.081 | 0.913 | 0.840 | -0.005 | 1.0000 | -0.012 |
| retrieval_grounded | groq:llama-3.3-70b-versatile | 200 | yes | yes | 0.985 | 0.985 | 0.010 | 0.985 | 0.970 | -0.015 | 0.2482 | -0.015 |
| summarization | tinyllama:1.1b | 200 | yes | yes | 0.990 | 0.934 | 0.028 | 0.961 | 0.925 | -0.010 | 0.4795 | -0.010 |
| summarization | qwen2.5:1.5b | 200 | yes | yes | 0.455 | 0.824 | 0.074 | 0.610 | 0.520 | -0.255 | 0.0000 | -0.512 |
| summarization | phi3:mini | 200 | yes | yes | 0.990 | 0.919 | 0.034 | 0.953 | 0.910 | -0.010 | 0.4795 | -0.011 |
| summarization | groq:llama-3.3-70b-versatile | 200 | yes | yes | 0.990 | 0.955 | 0.019 | 0.972 | 0.945 | -0.010 | 0.4795 | -0.010 |
| text_generation | tinyllama:1.1b | 178 | yes | yes | 0.978 | 0.908 | 0.039 | 0.943 | 0.893 | -0.011 | 0.6171 | -0.020 |
| text_generation | qwen2.5:1.5b | 178 | yes | no | 0.000 | 0.000 | 1.000 | 0.000 | 0.365 | -0.270 | 0.0004 | -2.005 |
| text_generation | phi3:mini | 178 | yes | yes | 0.978 | 0.822 | 0.075 | 0.897 | 0.815 | 0.000 | 0.6171 | -0.018 |
| text_generation | groq:llama-3.3-70b-versatile | 178 | yes | yes | 0.978 | 0.977 | 0.010 | 0.977 | 0.955 | -0.022 | 0.1336 | -0.023 |
