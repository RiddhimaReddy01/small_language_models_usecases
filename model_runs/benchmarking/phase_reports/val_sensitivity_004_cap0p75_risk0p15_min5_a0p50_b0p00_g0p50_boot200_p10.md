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
| classification | qwen2.5:0.5b | 160 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.606 [0.537, 0.669] | 0.0041 | 0.1016 | -0.537 |
| classification | qwen2.5:3b | 160 | yes | 0.784 [0.687, 0.880] | 0.444 [0.354, 0.527] | 0.567 [0.478, 0.645] | 0.619 [0.556, 0.681] | 0.4435 | 1.0000 | -0.313 |
| classification | qwen2.5:7b | 160 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.531 [0.469, 0.600] | 0.3382 | 1.0000 | -0.547 |
| classification | groq:llama-3.3-70b-versatile | 160 | no | 0.688 [0.523, 0.850] | 0.117 [0.072, 0.176] | 0.200 [0.127, 0.286] | 0.450 [0.388, 0.519] | 0.0801 | 1.0000 | -0.438 |
| code_generation | qwen2.5:0.5b | 171 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.509 [0.444, 0.573] | 0.8784 | 1.0000 | -0.875 |
| code_generation | qwen2.5:3b | 171 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.497 [0.427, 0.556] | 1.0000 | 1.0000 | -0.878 |
| code_generation | qwen2.5:7b | 171 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.480 [0.415, 0.544] | 0.6464 | 1.0000 | -0.883 |
| code_generation | groq:llama-3.3-70b-versatile | 171 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.474 [0.409, 0.538] | 0.6444 | 1.0000 | -0.620 |
| information_extraction | qwen2.5:0.5b | 105 | no | 0.667 [0.399, 0.900] | 0.085 [0.029, 0.145] | 0.150 [0.053, 0.242] | 0.352 [0.286, 0.419] | 0.0008 | 0.0197 | -0.459 |
| information_extraction | qwen2.5:3b | 105 | yes | 0.765 [0.631, 0.885] | 0.356 [0.270, 0.451] | 0.486 [0.380, 0.581] | 0.476 [0.400, 0.562] | 0.0090 | 0.2167 | -0.328 |
| information_extraction | qwen2.5:7b | 105 | yes | 0.806 [0.737, 0.870] | 0.940 [0.901, 0.977] | 0.868 [0.821, 0.906] | 0.771 [0.705, 0.829] | 0.4497 | 1.0000 | -0.032 |
| information_extraction | groq:llama-3.3-70b-versatile | 105 | yes | 0.833 [0.768, 0.890] | 0.952 [0.911, 0.988] | 0.889 [0.847, 0.926] | 0.810 [0.743, 0.867] | 1.0000 | 1.0000 | -0.038 |
| instruction_following | qwen2.5:0.5b | 213 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.437 [0.380, 0.493] | 0.0748 | 1.0000 | -0.940 |
| instruction_following | qwen2.5:3b | 213 | yes | 0.786 [0.732, 0.845] | 0.724 [0.660, 0.781] | 0.753 [0.707, 0.801] | 0.662 [0.610, 0.718] | 0.2418 | 1.0000 | -0.161 |
| instruction_following | qwen2.5:7b | 213 | yes | 0.800 [0.429, 1.000] | 0.030 [0.007, 0.053] | 0.057 [0.015, 0.101] | 0.380 [0.319, 0.432] | 0.0002 | 0.0064 | -0.465 |
| instruction_following | groq:llama-3.3-70b-versatile | 213 | yes | 0.837 [0.796, 0.877] | 0.972 [0.952, 0.989] | 0.899 [0.873, 0.924] | 0.817 [0.775, 0.859] | 0.0736 | 1.0000 | -0.012 |
| maths | qwen2.5:0.5b | 202 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.752 [0.708, 0.802] | 0.0000 | 0.0000 | -0.865 |
| maths | qwen2.5:3b | 202 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.455 [0.401, 0.510] | 0.2317 | 1.0000 | -0.918 |
| maths | qwen2.5:7b | 202 | no | 0.699 [0.646, 0.751] | 0.979 [0.957, 1.000] | 0.815 [0.778, 0.851] | 0.693 [0.644, 0.743] | 0.6831 | 1.0000 | -0.014 |
| maths | groq:llama-3.3-70b-versatile | 202 | yes | 0.761 [0.709, 0.812] | 0.968 [0.942, 0.988] | 0.852 [0.815, 0.884] | 0.743 [0.688, 0.792] | 0.0736 | 1.0000 | -0.013 |
| retrieval_grounded | qwen2.5:0.5b | 185 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.535 [0.476, 0.595] | 0.3776 | 1.0000 | -0.919 |
| retrieval_grounded | qwen2.5:3b | 185 | yes | 0.827 [0.747, 0.900] | 0.549 [0.477, 0.632] | 0.660 [0.589, 0.727] | 0.654 [0.595, 0.719] | 0.5045 | 1.0000 | -0.265 |
| retrieval_grounded | qwen2.5:7b | 185 | yes | 1.000 [1.000, 1.000] | 0.125 [0.073, 0.183] | 0.222 [0.136, 0.309] | 0.508 [0.454, 0.568] | 0.4926 | 1.0000 | -0.399 |
| retrieval_grounded | groq:llama-3.3-70b-versatile | 185 | yes | 0.824 [0.764, 0.885] | 0.701 [0.635, 0.770] | 0.757 [0.705, 0.812] | 0.692 [0.638, 0.751] | 1.0000 | 1.0000 | -0.187 |
| summarization | qwen2.5:0.5b | 166 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.277 [0.217, 0.331] | 0.0000 | 0.0000 | -0.975 |
| summarization | qwen2.5:3b | 166 | yes | 0.800 [0.555, 1.000] | 0.072 [0.029, 0.114] | 0.132 [0.057, 0.203] | 0.367 [0.307, 0.428] | 0.0001 | 0.0024 | -0.458 |
| summarization | qwen2.5:7b | 166 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.313 [0.253, 0.380] | 0.0000 | 0.0001 | -0.972 |
| summarization | groq:llama-3.3-70b-versatile | 166 | yes | 1.000 [0.000, 1.000] | 0.010 [0.000, 0.024] | 0.020 [0.000, 0.046] | 0.404 [0.337, 0.464] | 0.0127 | 0.2928 | -0.461 |
| text_generation | qwen2.5:0.5b | 128 | no | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.453 [0.375, 0.523] | 0.3309 | 1.0000 | -0.968 |
| text_generation | qwen2.5:3b | 128 | no | 0.640 [0.583, 0.714] | 0.964 [0.927, 0.989] | 0.769 [0.726, 0.826] | 0.625 [0.570, 0.703] | 0.2482 | 1.0000 | -0.012 |
| text_generation | qwen2.5:7b | 128 | yes | 0.837 [0.786, 0.892] | 0.963 [0.929, 0.991] | 0.896 [0.857, 0.929] | 0.812 [0.750, 0.867] | 0.3711 | 1.0000 | -0.019 |
| text_generation | groq:llama-3.3-70b-versatile | 128 | yes | 1.000 [1.000, 1.000] | 0.516 [0.453, 0.586] | 0.680 [0.623, 0.739] | 0.516 [0.453, 0.586] | 0.0000 | 0.0000 | -0.242 |
