# Test Phase Report (Frozen Policy)

## Leakage Proof

- Hash split policy: `sha1(sample_id)%100: train<30, val<70, test>=70`
- Strict leakage mode: `on`

| Task | Model | report_split | threshold_split | train_rows | val_rows | report_rows | Frozen Policy | Split Contract OK | Leakage Violations |
|---|---|---|---|---:|---:|---:|:---:|:---:|---|
| classification | qwen2.5:0.5b | test | val | 120 | 160 | 120 | yes | yes | none |
| classification | qwen2.5:3b | test | val | 120 | 160 | 120 | yes | yes | none |
| classification | qwen2.5:7b | test | val | 120 | 160 | 120 | yes | yes | none |
| classification | groq:llama-3.3-70b-versatile | test | val | 120 | 160 | 120 | yes | yes | none |
| code_generation | qwen2.5:0.5b | test | val | 118 | 171 | 132 | yes | yes | none |
| code_generation | qwen2.5:3b | test | val | 118 | 171 | 132 | yes | yes | none |
| code_generation | qwen2.5:7b | test | val | 118 | 171 | 132 | yes | yes | none |
| code_generation | groq:llama-3.3-70b-versatile | test | val | 118 | 171 | 132 | yes | yes | none |
| information_extraction | qwen2.5:0.5b | test | val | 69 | 105 | 76 | yes | yes | none |
| information_extraction | qwen2.5:3b | test | val | 69 | 105 | 76 | yes | yes | none |
| information_extraction | qwen2.5:7b | test | val | 69 | 105 | 76 | yes | yes | none |
| information_extraction | groq:llama-3.3-70b-versatile | test | val | 69 | 105 | 76 | yes | yes | none |
| instruction_following | qwen2.5:0.5b | test | val | 153 | 213 | 134 | yes | yes | none |
| instruction_following | qwen2.5:3b | test | val | 153 | 213 | 134 | yes | yes | none |
| instruction_following | qwen2.5:7b | test | val | 153 | 213 | 134 | yes | yes | none |
| instruction_following | groq:llama-3.3-70b-versatile | test | val | 153 | 213 | 134 | yes | yes | none |
| maths | qwen2.5:0.5b | test | val | 135 | 202 | 163 | yes | yes | none |
| maths | qwen2.5:3b | test | val | 135 | 202 | 163 | yes | yes | none |
| maths | qwen2.5:7b | test | val | 135 | 202 | 163 | yes | yes | none |
| maths | groq:llama-3.3-70b-versatile | test | val | 135 | 202 | 163 | yes | yes | none |
| retrieval_grounded | qwen2.5:0.5b | test | val | 146 | 185 | 169 | yes | yes | none |
| retrieval_grounded | qwen2.5:3b | test | val | 146 | 185 | 169 | yes | yes | none |
| retrieval_grounded | qwen2.5:7b | test | val | 146 | 185 | 169 | yes | yes | none |
| retrieval_grounded | groq:llama-3.3-70b-versatile | test | val | 146 | 185 | 169 | yes | yes | none |
| summarization | qwen2.5:0.5b | test | val | 110 | 166 | 124 | yes | yes | none |
| summarization | qwen2.5:3b | test | val | 110 | 166 | 124 | yes | yes | none |
| summarization | qwen2.5:7b | test | val | 110 | 166 | 124 | yes | yes | none |
| summarization | groq:llama-3.3-70b-versatile | test | val | 110 | 166 | 124 | yes | yes | none |
| text_generation | qwen2.5:0.5b | test | val | 95 | 128 | 77 | yes | yes | none |
| text_generation | qwen2.5:3b | test | val | 95 | 128 | 77 | yes | yes | none |
| text_generation | qwen2.5:7b | test | val | 95 | 128 | 77 | yes | yes | none |
| text_generation | groq:llama-3.3-70b-versatile | test | val | 95 | 128 | 77 | yes | yes | none |

## Primary Statistical Results

| Task | Model | N | Pass Gate | Precision [90% CI] | Recall [90% CI] | F1 [90% CI] | Acc [90% CI] | p(McNemar vs Always-SLM) | p_holm | dUtility vs Always-SLM |
|---|---|---:|:---:|---|---|---|---|---:|---:|---:|
| classification | qwen2.5:0.5b | 120 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.575 [0.500, 0.658] | 0.1207 | 1.0000 | -1.962 |
| classification | qwen2.5:3b | 120 | yes | 0.909 [0.789, 1.000] | 0.260 [0.181, 0.343] | 0.404 [0.300, 0.500] | 0.508 [0.425, 0.592] | 0.1297 | 1.0000 | -0.683 |
| classification | qwen2.5:7b | 120 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.475 [0.408, 0.550] | 0.6481 | 1.0000 | -2.013 |
| classification | groq:llama-3.3-70b-versatile | 120 | yes | 0.800 [0.571, 1.000] | 0.098 [0.045, 0.152] | 0.174 [0.086, 0.258] | 0.367 [0.292, 0.442] | 0.0004 | 0.0092 | -0.858 |
| code_generation | qwen2.5:0.5b | 132 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.439 [0.371, 0.515] | 0.1917 | 1.0000 | -1.925 |
| code_generation | qwen2.5:3b | 132 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.439 [0.371, 0.515] | 0.1917 | 1.0000 | -1.925 |
| code_generation | qwen2.5:7b | 132 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.432 [0.356, 0.508] | 0.1390 | 1.0000 | -1.930 |
| code_generation | groq:llama-3.3-70b-versatile | 132 | no | 0.372 [0.290, 0.455] | 0.416 [0.329, 0.507] | 0.393 [0.322, 0.468] | 0.250 [0.197, 0.311] | 0.0000 | 0.0000 | -0.505 |
| information_extraction | qwen2.5:0.5b | 76 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.382 [0.289, 0.474] | 0.0512 | 0.6141 | -2.039 |
| information_extraction | qwen2.5:3b | 76 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.303 [0.224, 0.382] | 0.0009 | 0.0176 | -2.083 |
| information_extraction | qwen2.5:7b | 76 | no | 0.714 [0.400, 1.000] | 0.091 [0.035, 0.160] | 0.161 [0.065, 0.269] | 0.316 [0.237, 0.395] | 0.0003 | 0.0070 | -0.913 |
| information_extraction | groq:llama-3.3-70b-versatile | 76 | no | 0.764 [0.666, 0.855] | 0.724 [0.625, 0.817] | 0.743 [0.666, 0.817] | 0.618 [0.526, 0.711] | 0.0291 | 0.4073 | -0.276 |
| instruction_following | qwen2.5:0.5b | 134 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.567 [0.493, 0.642] | 0.1419 | 1.0000 | -1.952 |
| instruction_following | qwen2.5:3b | 134 | no | 0.737 [0.614, 0.853] | 0.315 [0.231, 0.392] | 0.441 [0.341, 0.520] | 0.470 [0.396, 0.545] | 0.0107 | 0.1716 | -0.678 |
| instruction_following | qwen2.5:7b | 134 | no | 0.636 [0.400, 0.858] | 0.080 [0.037, 0.129] | 0.143 [0.067, 0.220] | 0.373 [0.306, 0.440] | 0.0012 | 0.0222 | -0.925 |
| instruction_following | groq:llama-3.3-70b-versatile | 134 | yes | 1.000 [1.000, 1.000] | 0.038 [0.010, 0.072] | 0.073 [0.019, 0.135] | 0.239 [0.179, 0.306] | 0.0000 | 0.0000 | -0.860 |
| maths | qwen2.5:0.5b | 163 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.663 [0.601, 0.724] | 0.0000 | 0.0012 | -1.846 |
| maths | qwen2.5:3b | 163 | no | 0.582 [0.500, 0.667] | 0.515 [0.439, 0.591] | 0.546 [0.476, 0.618] | 0.460 [0.399, 0.522] | 0.0015 | 0.0263 | -0.472 |
| maths | qwen2.5:7b | 163 | no | 0.257 [0.184, 0.330] | 0.605 [0.463, 0.725] | 0.361 [0.267, 0.446] | 0.436 [0.368, 0.503] | 0.0006 | 0.0127 | -0.384 |
| maths | groq:llama-3.3-70b-versatile | 163 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.227 [0.172, 0.283] | 0.0000 | 0.0000 | -2.112 |
| retrieval_grounded | qwen2.5:0.5b | 169 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.456 [0.384, 0.515] | 0.2815 | 1.0000 | -1.998 |
| retrieval_grounded | qwen2.5:3b | 169 | yes | 0.885 [0.774, 0.971] | 0.211 [0.150, 0.282] | 0.341 [0.254, 0.433] | 0.473 [0.414, 0.538] | 0.0192 | 0.2881 | -0.714 |
| retrieval_grounded | qwen2.5:7b | 169 | yes | 0.833 [0.500, 1.000] | 0.044 [0.017, 0.080] | 0.084 [0.034, 0.149] | 0.355 [0.296, 0.414] | 0.0000 | 0.0012 | -0.874 |
| retrieval_grounded | groq:llama-3.3-70b-versatile | 169 | yes | 0.895 [0.806, 0.973] | 0.274 [0.213, 0.342] | 0.420 [0.338, 0.497] | 0.444 [0.385, 0.509] | 0.0000 | 0.0007 | -0.686 |
| summarization | qwen2.5:0.5b | 124 | no | 0.727 [0.628, 0.829] | 0.356 [0.271, 0.438] | 0.478 [0.385, 0.560] | 0.435 [0.363, 0.508] | 0.0001 | 0.0022 | -0.645 |
| summarization | qwen2.5:3b | 124 | no | 0.754 [0.677, 0.841] | 0.563 [0.483, 0.649] | 0.645 [0.575, 0.716] | 0.565 [0.492, 0.637] | 0.0372 | 0.4842 | -0.453 |
| summarization | qwen2.5:7b | 124 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.282 [0.217, 0.347] | 0.0000 | 0.0001 | -2.129 |
| summarization | groq:llama-3.3-70b-versatile | 124 | no | 0.738 [0.670, 0.808] | 0.844 [0.778, 0.912] | 0.788 [0.734, 0.841] | 0.669 [0.605, 0.742] | 0.1904 | 1.0000 | -0.164 |
| text_generation | qwen2.5:0.5b | 77 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.519 [0.416, 0.610] | 0.8197 | 1.0000 | -2.047 |
| text_generation | qwen2.5:3b | 77 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.532 [0.442, 0.636] | 0.6485 | 1.0000 | -2.042 |
| text_generation | qwen2.5:7b | 77 | no | 0.647 [0.500, 0.781] | 0.415 [0.304, 0.520] | 0.506 [0.395, 0.614] | 0.442 [0.351, 0.545] | 0.0061 | 0.1029 | -0.575 |
| text_generation | groq:llama-3.3-70b-versatile | 77 | yes | 1.000 [1.000, 1.000] | 0.468 [0.377, 0.558] | 0.637 [0.547, 0.717] | 0.468 [0.377, 0.558] | 0.0000 | 0.0000 | -0.532 |
