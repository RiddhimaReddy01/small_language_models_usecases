# Val Phase Report (Frozen Policy)

## Leakage Proof

- Hash split policy: `sha1(sample_id)%100: train<30, val<70, test>=70`
- Strict leakage mode: `on`

| Task | Model | report_split | threshold_split | train_rows | val_rows | report_rows | Frozen Policy | Split Contract OK | Leakage Violations |
|---|---|---|---|---:|---:|---:|:---:|:---:|---|
| classification | qwen2.5:0.5b | val | val | 120 | 160 | 160 | yes | yes | none |
| classification | qwen2.5:3b | val | val | 120 | 160 | 160 | yes | yes | none |
| classification | qwen2.5:7b | val | val | 120 | 160 | 160 | yes | yes | none |
| classification | groq:llama-3.3-70b-versatile | val | val | 120 | 160 | 160 | yes | yes | none |
| code_generation | qwen2.5:0.5b | val | val | 118 | 171 | 171 | yes | yes | none |
| code_generation | qwen2.5:3b | val | val | 118 | 171 | 171 | yes | yes | none |
| code_generation | qwen2.5:7b | val | val | 118 | 171 | 171 | yes | yes | none |
| code_generation | groq:llama-3.3-70b-versatile | val | val | 118 | 171 | 171 | yes | yes | none |
| information_extraction | qwen2.5:0.5b | val | val | 69 | 105 | 105 | yes | yes | none |
| information_extraction | qwen2.5:3b | val | val | 69 | 105 | 105 | yes | yes | none |
| information_extraction | qwen2.5:7b | val | val | 69 | 105 | 105 | yes | yes | none |
| information_extraction | groq:llama-3.3-70b-versatile | val | val | 69 | 105 | 105 | yes | yes | none |
| instruction_following | qwen2.5:0.5b | val | val | 153 | 213 | 213 | yes | yes | none |
| instruction_following | qwen2.5:3b | val | val | 153 | 213 | 213 | yes | yes | none |
| instruction_following | qwen2.5:7b | val | val | 153 | 213 | 213 | yes | yes | none |
| instruction_following | groq:llama-3.3-70b-versatile | val | val | 153 | 213 | 213 | yes | yes | none |
| maths | qwen2.5:0.5b | val | val | 135 | 202 | 202 | yes | yes | none |
| maths | qwen2.5:3b | val | val | 135 | 202 | 202 | yes | yes | none |
| maths | qwen2.5:7b | val | val | 135 | 202 | 202 | yes | yes | none |
| maths | groq:llama-3.3-70b-versatile | val | val | 135 | 202 | 202 | yes | yes | none |
| retrieval_grounded | qwen2.5:0.5b | val | val | 146 | 185 | 185 | yes | yes | none |
| retrieval_grounded | qwen2.5:3b | val | val | 146 | 185 | 185 | yes | yes | none |
| retrieval_grounded | qwen2.5:7b | val | val | 146 | 185 | 185 | yes | yes | none |
| retrieval_grounded | groq:llama-3.3-70b-versatile | val | val | 146 | 185 | 185 | yes | yes | none |
| summarization | qwen2.5:0.5b | val | val | 110 | 166 | 166 | yes | yes | none |
| summarization | qwen2.5:3b | val | val | 110 | 166 | 166 | yes | yes | none |
| summarization | qwen2.5:7b | val | val | 110 | 166 | 166 | yes | yes | none |
| summarization | groq:llama-3.3-70b-versatile | val | val | 110 | 166 | 166 | yes | yes | none |
| text_generation | qwen2.5:0.5b | val | val | 95 | 128 | 128 | yes | yes | none |
| text_generation | qwen2.5:3b | val | val | 95 | 128 | 128 | yes | yes | none |
| text_generation | qwen2.5:7b | val | val | 95 | 128 | 128 | yes | yes | none |
| text_generation | groq:llama-3.3-70b-versatile | val | val | 95 | 128 | 128 | yes | yes | none |

## Primary Statistical Results

| Task | Model | N | Pass Gate | Precision [90% CI] | Recall [90% CI] | F1 [90% CI] | Acc [90% CI] | p(McNemar vs Always-SLM) | p_holm | dUtility vs Always-SLM |
|---|---|---:|:---:|---|---|---|---|---:|---:|---:|
| classification | qwen2.5:0.5b | 160 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.625 [0.556, 0.688] | 0.0020 | 0.0389 | -1.938 |
| classification | qwen2.5:3b | 160 | yes | 0.839 [0.714, 0.957] | 0.289 [0.205, 0.379] | 0.430 [0.321, 0.523] | 0.569 [0.500, 0.631] | 1.0000 | 1.0000 | -0.668 |
| classification | qwen2.5:7b | 160 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.550 [0.487, 0.613] | 0.2357 | 1.0000 | -1.975 |
| classification | groq:llama-3.3-70b-versatile | 160 | no | 0.500 [0.273, 0.750] | 0.053 [0.021, 0.094] | 0.096 [0.040, 0.162] | 0.412 [0.344, 0.481] | 0.0275 | 0.4123 | -0.981 |
| code_generation | qwen2.5:0.5b | 171 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.509 [0.444, 0.573] | 0.8784 | 1.0000 | -1.874 |
| code_generation | qwen2.5:3b | 171 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.497 [0.427, 0.556] | 1.0000 | 1.0000 | -1.882 |
| code_generation | qwen2.5:7b | 171 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.480 [0.415, 0.544] | 0.6464 | 1.0000 | -1.895 |
| code_generation | groq:llama-3.3-70b-versatile | 171 | no | 0.369 [0.293, 0.450] | 0.511 [0.425, 0.604] | 0.429 [0.355, 0.507] | 0.298 [0.234, 0.368] | 0.0000 | 0.0000 | -0.394 |
| information_extraction | qwen2.5:0.5b | 105 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.324 [0.257, 0.390] | 0.0004 | 0.0093 | -2.071 |
| information_extraction | qwen2.5:3b | 105 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.305 [0.229, 0.381] | 0.0001 | 0.0021 | -2.082 |
| information_extraction | qwen2.5:7b | 105 | yes | 0.833 [0.500, 1.000] | 0.060 [0.023, 0.106] | 0.111 [0.045, 0.191] | 0.238 [0.171, 0.305] | 0.0000 | 0.0000 | -0.924 |
| information_extraction | groq:llama-3.3-70b-versatile | 105 | yes | 0.847 [0.781, 0.911] | 0.726 [0.654, 0.810] | 0.782 [0.726, 0.843] | 0.676 [0.610, 0.752] | 0.0367 | 0.5140 | -0.288 |
| instruction_following | qwen2.5:0.5b | 213 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.437 [0.380, 0.493] | 0.0748 | 0.9728 | -2.021 |
| instruction_following | qwen2.5:3b | 213 | yes | 0.843 [0.755, 0.927] | 0.283 [0.222, 0.342] | 0.424 [0.345, 0.493] | 0.451 [0.394, 0.507] | 0.0000 | 0.0004 | -0.693 |
| instruction_following | qwen2.5:7b | 213 | yes | 0.800 [0.571, 1.000] | 0.059 [0.028, 0.094] | 0.110 [0.055, 0.169] | 0.394 [0.333, 0.446] | 0.0004 | 0.0093 | -0.866 |
| instruction_following | groq:llama-3.3-70b-versatile | 213 | yes | 0.857 [0.599, 1.000] | 0.034 [0.011, 0.056] | 0.065 [0.022, 0.104] | 0.183 [0.141, 0.225] | 0.0000 | 0.0000 | -0.958 |
| maths | qwen2.5:0.5b | 202 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.752 [0.708, 0.802] | 0.0000 | 0.0000 | -1.791 |
| maths | qwen2.5:3b | 202 | no | 0.534 [0.457, 0.608] | 0.564 [0.487, 0.642] | 0.549 [0.479, 0.609] | 0.495 [0.435, 0.550] | 0.3318 | 1.0000 | -0.432 |
| maths | qwen2.5:7b | 202 | no | 0.621 [0.558, 0.690] | 0.586 [0.520, 0.664] | 0.603 [0.548, 0.660] | 0.465 [0.411, 0.525] | 0.0000 | 0.0000 | -0.390 |
| maths | groq:llama-3.3-70b-versatile | 202 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.233 [0.183, 0.287] | 0.0000 | 0.0000 | -2.108 |
| retrieval_grounded | qwen2.5:0.5b | 185 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.535 [0.476, 0.595] | 0.3776 | 1.0000 | -1.954 |
| retrieval_grounded | qwen2.5:3b | 185 | yes | 0.897 [0.782, 1.000] | 0.230 [0.165, 0.297] | 0.366 [0.277, 0.453] | 0.514 [0.459, 0.573] | 0.1735 | 1.0000 | -0.685 |
| retrieval_grounded | qwen2.5:7b | 185 | yes | 1.000 [1.000, 1.000] | 0.077 [0.036, 0.126] | 0.143 [0.069, 0.224] | 0.481 [0.427, 0.546] | 0.2927 | 1.0000 | -0.715 |
| retrieval_grounded | groq:llama-3.3-70b-versatile | 185 | yes | 0.947 [0.879, 1.000] | 0.283 [0.228, 0.351] | 0.436 [0.364, 0.513] | 0.497 [0.443, 0.557] | 0.0050 | 0.0908 | -0.650 |
| summarization | qwen2.5:0.5b | 166 | no | 0.723 [0.627, 0.818] | 0.392 [0.312, 0.452] | 0.508 [0.433, 0.569] | 0.452 [0.386, 0.512] | 0.0000 | 0.0003 | -0.608 |
| summarization | qwen2.5:3b | 166 | no | 0.739 [0.656, 0.806] | 0.613 [0.533, 0.682] | 0.670 [0.598, 0.727] | 0.596 [0.524, 0.651] | 0.2010 | 1.0000 | -0.415 |
| summarization | qwen2.5:7b | 166 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.313 [0.253, 0.380] | 0.0000 | 0.0001 | -2.115 |
| summarization | groq:llama-3.3-70b-versatile | 166 | no | 0.615 [0.553, 0.681] | 0.880 [0.830, 0.928] | 0.724 [0.675, 0.776] | 0.596 [0.536, 0.657] | 1.0000 | 1.0000 | -0.133 |
| text_generation | qwen2.5:0.5b | 128 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.617 [0.539, 0.688] | 0.0104 | 0.1763 | -2.009 |
| text_generation | qwen2.5:3b | 128 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.531 [0.461, 0.594] | 0.5361 | 1.0000 | -2.043 |
| text_generation | qwen2.5:7b | 128 | no | 0.717 [0.621, 0.806] | 0.489 [0.405, 0.579] | 0.581 [0.503, 0.655] | 0.516 [0.453, 0.586] | 0.0109 | 0.1763 | -0.520 |
| text_generation | groq:llama-3.3-70b-versatile | 128 | yes | 1.000 [1.000, 1.000] | 0.484 [0.421, 0.555] | 0.653 [0.593, 0.714] | 0.484 [0.421, 0.555] | 0.0000 | 0.0000 | -0.516 |
