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
| classification | qwen2.5:0.5b | 160 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.606 [0.537, 0.669] | 0.0041 | 0.0975 | -0.584 |
| classification | qwen2.5:3b | 160 | yes | 0.789 [0.673, 0.909] | 0.333 [0.247, 0.424] | 0.469 [0.364, 0.561] | 0.575 [0.512, 0.637] | 0.9279 | 1.0000 | -0.325 |
| classification | qwen2.5:7b | 160 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.531 [0.469, 0.600] | 0.3382 | 1.0000 | -0.603 |
| classification | groq:llama-3.3-70b-versatile | 160 | no | 0.500 [0.000, 1.000] | 0.021 [0.000, 0.049] | 0.041 [0.000, 0.091] | 0.412 [0.350, 0.469] | 0.0306 | 0.6434 | -0.509 |
| code_generation | qwen2.5:0.5b | 171 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.509 [0.444, 0.573] | 0.8784 | 1.0000 | -1.251 |
| code_generation | qwen2.5:3b | 171 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.497 [0.427, 0.556] | 1.0000 | 1.0000 | -1.256 |
| code_generation | qwen2.5:7b | 171 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.480 [0.415, 0.544] | 0.6464 | 1.0000 | -1.265 |
| code_generation | groq:llama-3.3-70b-versatile | 171 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.474 [0.409, 0.538] | 0.6444 | 1.0000 | -0.746 |
| information_extraction | qwen2.5:0.5b | 105 | no | 0.667 [0.399, 0.900] | 0.085 [0.029, 0.145] | 0.150 [0.053, 0.242] | 0.352 [0.286, 0.419] | 0.0008 | 0.0197 | -0.460 |
| information_extraction | qwen2.5:3b | 105 | no | 0.737 [0.562, 0.900] | 0.192 [0.114, 0.276] | 0.304 [0.195, 0.408] | 0.390 [0.314, 0.476] | 0.0008 | 0.0207 | -0.397 |
| information_extraction | qwen2.5:7b | 105 | yes | 0.806 [0.737, 0.870] | 0.940 [0.901, 0.977] | 0.868 [0.821, 0.906] | 0.771 [0.705, 0.829] | 0.4497 | 1.0000 | -0.031 |
| information_extraction | groq:llama-3.3-70b-versatile | 105 | yes | 0.842 [0.777, 0.900] | 0.952 [0.911, 0.988] | 0.894 [0.852, 0.929] | 0.819 [0.752, 0.876] | 0.7518 | 1.0000 | -0.035 |
| instruction_following | qwen2.5:0.5b | 213 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.437 [0.380, 0.493] | 0.0748 | 1.0000 | -1.380 |
| instruction_following | qwen2.5:3b | 213 | yes | 0.810 [0.752, 0.876] | 0.618 [0.549, 0.682] | 0.701 [0.642, 0.754] | 0.624 [0.568, 0.681] | 0.0676 | 1.0000 | -0.201 |
| instruction_following | qwen2.5:7b | 213 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.366 [0.310, 0.413] | 0.0001 | 0.0034 | -1.399 |
| instruction_following | groq:llama-3.3-70b-versatile | 213 | yes | 0.835 [0.795, 0.876] | 0.961 [0.936, 0.984] | 0.894 [0.867, 0.922] | 0.808 [0.765, 0.854] | 0.0233 | 0.5135 | -0.018 |
| maths | qwen2.5:0.5b | 202 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.752 [0.708, 0.802] | 0.0000 | 0.0000 | -1.229 |
| maths | qwen2.5:3b | 202 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.455 [0.401, 0.510] | 0.2317 | 1.0000 | -1.336 |
| maths | qwen2.5:7b | 202 | no | 0.699 [0.646, 0.751] | 0.979 [0.957, 1.000] | 0.815 [0.778, 0.851] | 0.693 [0.644, 0.743] | 0.6831 | 1.0000 | -0.013 |
| maths | groq:llama-3.3-70b-versatile | 202 | yes | 0.761 [0.709, 0.812] | 0.968 [0.942, 0.988] | 0.852 [0.815, 0.884] | 0.743 [0.688, 0.792] | 0.0736 | 1.0000 | -0.015 |
| retrieval_grounded | qwen2.5:0.5b | 185 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.535 [0.476, 0.595] | 0.3776 | 1.0000 | -1.338 |
| retrieval_grounded | qwen2.5:3b | 185 | yes | 0.833 [0.750, 0.908] | 0.531 [0.456, 0.612] | 0.649 [0.575, 0.715] | 0.649 [0.595, 0.708] | 0.5725 | 1.0000 | -0.238 |
| retrieval_grounded | qwen2.5:7b | 185 | yes | 1.000 [1.000, 1.000] | 0.125 [0.073, 0.183] | 0.222 [0.136, 0.309] | 0.508 [0.454, 0.568] | 0.4926 | 1.0000 | -0.332 |
| retrieval_grounded | groq:llama-3.3-70b-versatile | 185 | yes | 0.829 [0.771, 0.890] | 0.685 [0.620, 0.757] | 0.750 [0.698, 0.807] | 0.686 [0.632, 0.746] | 0.9110 | 1.0000 | -0.173 |
| summarization | qwen2.5:0.5b | 166 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.277 [0.217, 0.331] | 0.0000 | 0.0000 | -1.450 |
| summarization | qwen2.5:3b | 166 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.331 [0.271, 0.392] | 0.0000 | 0.0006 | -1.440 |
| summarization | qwen2.5:7b | 166 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.313 [0.253, 0.380] | 0.0000 | 0.0001 | -1.444 |
| summarization | groq:llama-3.3-70b-versatile | 166 | yes | 1.000 [0.000, 1.000] | 0.010 [0.000, 0.024] | 0.020 [0.000, 0.046] | 0.404 [0.337, 0.464] | 0.0127 | 0.2928 | -0.425 |
| text_generation | qwen2.5:0.5b | 128 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.453 [0.375, 0.523] | 0.3309 | 1.0000 | -1.437 |
| text_generation | qwen2.5:3b | 128 | no | 0.640 [0.583, 0.714] | 0.964 [0.927, 0.989] | 0.769 [0.726, 0.826] | 0.625 [0.570, 0.703] | 0.2482 | 1.0000 | -0.013 |
| text_generation | qwen2.5:7b | 128 | yes | 0.837 [0.786, 0.892] | 0.963 [0.929, 0.991] | 0.896 [0.857, 0.929] | 0.812 [0.750, 0.867] | 0.3711 | 1.0000 | -0.019 |
| text_generation | groq:llama-3.3-70b-versatile | 128 | yes | 1.000 [1.000, 1.000] | 0.516 [0.453, 0.586] | 0.680 [0.623, 0.739] | 0.516 [0.453, 0.586] | 0.0000 | 0.0000 | -0.242 |
