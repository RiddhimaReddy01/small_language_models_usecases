# Error Taxonomy by Task and Model

| Task | Model | N | Failure Rate | Avg Semantic Risk | Avg Failure Harm | Top Failure (count) |
|---|---|---:|---:|---:|---:|---|
| classification | groq:llama-3.3-70b-versatile | 20 | 0.000 | 0.000 | 0.000 | none (0) |
| classification | phi3:mini | 20 | 0.000 | 0.000 | 0.000 | none (0) |
| classification | qwen2.5:1.5b | 20 | 0.150 | 0.096 | 0.640 | wrong_label (3) |
| classification | tinyllama:1.1b | 20 | 0.100 | 0.064 | 0.640 | wrong_label (2) |
| code_generation | groq:llama-3.3-70b-versatile | 20 | 0.000 | 0.000 | 0.000 | none (0) |
| code_generation | phi3:mini | 20 | 0.250 | 0.137 | 0.548 | logic_error (3) |
| code_generation | qwen2.5:1.5b | 20 | 0.200 | 0.162 | 0.807 | logic_error (4) |
| code_generation | tinyllama:1.1b | 20 | 0.200 | 0.162 | 0.807 | logic_error (4) |
| information_extraction | groq:llama-3.3-70b-versatile | 20 | 0.000 | 0.000 | 0.000 | none (0) |
| information_extraction | phi3:mini | 20 | 0.050 | 0.010 | 0.203 | missing_field (1) |
| information_extraction | qwen2.5:1.5b | 20 | 0.050 | 0.010 | 0.203 | missing_field (1) |
| information_extraction | tinyllama:1.1b | 20 | 0.100 | 0.020 | 0.203 | missing_field (2) |
| instruction_following | groq:llama-3.3-70b-versatile | 20 | 0.050 | 0.024 | 0.490 | constraint_violation (1) |
| instruction_following | phi3:mini | 20 | 0.350 | 0.171 | 0.490 | constraint_violation (7) |
| instruction_following | qwen2.5:1.5b | 20 | 0.250 | 0.122 | 0.490 | constraint_violation (5) |
| instruction_following | tinyllama:1.1b | 20 | 0.500 | 0.245 | 0.490 | constraint_violation (10) |
| maths | groq:llama-3.3-70b-versatile | 20 | 0.100 | 0.072 | 0.720 | arithmetic_error (2) |
| maths | phi3:mini | 20 | 0.300 | 0.216 | 0.720 | arithmetic_error (6) |
| maths | qwen2.5:1.5b | 20 | 0.600 | 0.432 | 0.720 | arithmetic_error (12) |
| maths | tinyllama:1.1b | 20 | 0.900 | 0.648 | 0.720 | arithmetic_error (18) |
| retrieval_grounded | groq:llama-3.3-70b-versatile | 20 | 0.000 | 0.000 | 0.000 | none (0) |
| retrieval_grounded | phi3:mini | 20 | 0.150 | 0.070 | 0.467 | answer_mismatch (2) |
| retrieval_grounded | qwen2.5:1.5b | 20 | 0.000 | 0.000 | 0.000 | none (0) |
| retrieval_grounded | tinyllama:1.1b | 20 | 0.200 | 0.104 | 0.520 | answer_mismatch (3) |
| summarization | groq:llama-3.3-70b-versatile | 20 | 0.050 | 0.021 | 0.420 | low_relevance (1) |
| summarization | phi3:mini | 20 | 0.100 | 0.042 | 0.420 | low_relevance (2) |
| summarization | qwen2.5:1.5b | 20 | 0.350 | 0.147 | 0.420 | low_relevance (7) |
| summarization | tinyllama:1.1b | 20 | 0.250 | 0.105 | 0.420 | low_relevance (5) |
| text_generation | groq:llama-3.3-70b-versatile | 19 | 0.053 | 0.022 | 0.420 | low_relevance (1) |
| text_generation | phi3:mini | 19 | 0.263 | 0.111 | 0.420 | low_relevance (5) |
| text_generation | qwen2.5:1.5b | 19 | 0.526 | 0.221 | 0.420 | low_relevance (10) |
| text_generation | tinyllama:1.1b | 19 | 0.211 | 0.088 | 0.420 | low_relevance (4) |
