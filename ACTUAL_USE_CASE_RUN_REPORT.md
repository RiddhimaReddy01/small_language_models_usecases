# Actual Use Case Run Report

This report is based on actual saved benchmark artifacts in the repository, not only on README defaults.

Each section names the specific artifact used. If a benchmark did not record a field such as full hardware metadata, that gap is called out explicitly.

## Classification

Artifact used: [classification/results/metrics_summary_1773488616.json](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/classification/results/metrics_summary_1773488616.json)

### Use Case

Single-label text classification across sentiment, emotion, and news topic tasks.

### Dataset

- `SST-2`
- `Emotion`
- `AG News`
- Source: Hugging Face datasets through the benchmark loader
- License: not recorded in the run artifact

### Sampling

- Profile: `fast15`
- Test mode: `true`
- Seed: `42`
- Actual sampled counts in this run:
  - `SST-2`: 2
  - `Emotion`: 6
  - `AG News`: 4
- Sampling technique: label-balanced sampling with `test_mode` downscaling

### Model Specification

- Model: `phi3:mini`
- Backend: Ollama-style local model wrapper
- Quantization: not recorded
- Temperature / max tokens / device: not recorded in saved summary

### Hardware Environment

Recorded:

- CPU utilization average per dataset
- memory delta per dataset

Not recorded:

- CPU model
- RAM total
- GPU
- OS
- Python version

### Experimental Pipeline

1. Load built-in dataset
2. Build balanced sample
3. Prompt the classifier with label-only instruction
4. Store live and raw predictions
5. Compute capability and operational summaries

### Prompting Strategy

The model is asked to choose exactly one label and return only the label text.

### Capability Metrics

| Dataset | Accuracy | Macro F1 | Weighted F1 | Precision | Recall | Validity Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SST-2 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Emotion | 0.6667 | 0.5556 | 0.5556 | 0.5000 | 0.6667 | 1.0000 |
| AG News | 0.7500 | 0.6667 | 0.6667 | 0.6250 | 0.7500 | 1.0000 |

### Operational Metrics

| Dataset | Samples | Total Time (s) | Throughput | Mean Latency (s) | P95 Latency (s) | CPU Util Avg | Mem Delta MB | Parse Failure Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SST-2 | 2 | 11.0439 | 0.1811 | 5.5200 | 9.0031 | 46.80 | 1143.2266 | 0.0000 |
| Emotion | 6 | 7.9892 | 0.7510 | 1.3300 | 2.1089 | 67.20 | 602.6797 | 0.0000 |
| AG News | 4 | 9.9858 | 0.4006 | 2.4949 | 3.2489 | 91.85 | -838.1211 | 0.0000 |

## Text Generation

Artifacts used:

- [text_generation/results/runs/suite_20260315_000947/suite_manifest.json](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/text_generation/results/runs/suite_20260315_000947/suite_manifest.json)
- [text_generation/results/runs/suite_20260315_000947/benchmark_summary.json](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/text_generation/results/runs/suite_20260315_000947/benchmark_summary.json)

### Use Case

Constraint-aware open text generation benchmark over local prompt files.

### Dataset

- Task type: `samples`
- Actual tasks: `15`
- Source: local prompt file in `text_generation/data`
- License: not recorded in run artifact

### Sampling

- Seed: `42`
- Repeats: `1`
- Perturbation: `false`
- Sample selection: prompt-file driven, already materialized into the suite

### Model Specifications

| Model | Backend | Context | Threads | Quantization Signal | Model File Size |
| --- | --- | ---: | ---: | --- | ---: |
| qwen-2.5-3b | GGUF / `llama_cpp` | 4096 | 4 | `q4_k_m` in filename | 2104932768 bytes |
| phi-3.5-mini | GGUF / `llama_cpp` | 4096 | 4 | `Q4_K_M` in filename | 2393232672 bytes |
| gemini-baseline | Google API | n/a | n/a | n/a | n/a |

Common run settings:

- Temperature: `0.7`
- Workers: `1`
- Seed: `42`

### Hardware Environment

Recorded:

- peak RAM for local runs
- RAM delta
- model load time

Not recorded:

- CPU model
- OS
- Python version
- GPU identifier

### Experimental Pipeline

1. Load local prompt tasks
2. Initialize backend runner
3. Run generation
4. Save per-model JSON result file
5. Aggregate benchmark summary
6. Publish markdown tables

### Prompting Strategy

Task-native prompt text loaded from dataset file, optionally checked against constraints and references.

### Capability Metrics

| Model | Tasks | Success Rate | Avg Constraint Satisfaction | Avg Format Compliance | Avg Refusal Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| gemini-baseline | 15 | 1.0000 | 0.1667 | 1.0000 | 0.0667 |
| phi-3.5-mini | 15 | 1.0000 | 0.0000 | 1.0000 | 0.0667 |
| qwen-2.5-3b | 15 | 1.0000 | 0.1333 | 1.0000 | 0.0667 |

### Operational Metrics

| Model | Avg TTFT (s) | Avg Total Time (s) | Avg Tokens Generated | Avg TPS | Avg Peak RAM MB | Avg RAM Delta MB | Avg Model Load Time (s) | Total Cost USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gemini-baseline | 1.1757 | 5.8787 | 155.4800 | 39.0056 | 0.0000 | 0.0000 | 0.0010 | 0.0001749 |
| phi-3.5-mini | 0.8435 | 45.6180 | 402.8667 | 9.1310 | 3035.5568 | -86.9195 | 3.2469 | 0.0000000 |
| qwen-2.5-3b | 0.5061 | 22.1081 | 241.8667 | 10.8736 | 2486.0938 | 28.8404 | 6.1511 | 0.0000000 |

## Information Extraction

Artifacts used:

- [Information Extraction/configs/sroie_gemini_iter.json](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/Information%20Extraction/configs/sroie_gemini_iter.json)
- [Information Extraction/outputs/20260314_071350/summary.json](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/Information%20Extraction/outputs/20260314_071350/summary.json)

### Use Case

Receipt OCR field extraction into strict JSON schema.

### Dataset

- Dataset: `SROIE`
- Processed source: `data/processed/sroie_clean.jsonl`
- Target fields: `company`, `address`, `date`, `total`
- License: not recorded in run artifact

### Sampling

- Sample size: `4`
- Sampling method: `random`
- Seed: `42`
- Clean sample size: `4`
- Noisy sample size: `0`

### Model Specification

- Model: `Gemini-2.5-Flash`
- Backend: `gemini`
- Backend model: `gemini-2.5-flash`
- Device: `cpu`
- Quantization: `none`
- Temperature: `0.0`
- Top-p: `1.0`
- Max new tokens: `96`
- Torch threads: `6`

### Hardware Environment

Recorded:

- configured device: CPU
- average input tokens
- average output tokens
- average latency

Not recorded:

- CPU model
- OS
- RAM total
- Python version

### Experimental Pipeline

1. Load processed receipts
2. Randomly sample clean documents
3. Prompt model for strict JSON extraction
4. Save per-example predictions
5. Aggregate capability and operational metrics

### Prompting Strategy

JSON-only extraction prompt with fixed required keys and normalization instructions.

### Capability Metrics

| Model | Macro F1 | Micro F1 | Exact Match | Schema Valid Rate | Hallucination Rate | F1 Clean | Invalid Output Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Gemini-2.5-Flash | 0.1875 | 0.3000 | 0.0000 | 0.2500 | 0.2500 | 0.3000 | 0.7500 |

### Operational Metrics

| Model | Avg Latency / Doc (s) | Throughput (docs/min) | Avg Input Tokens | Avg Output Tokens | Peak GPU Memory MB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Gemini-2.5-Flash | 0.8567 | 70.0356 | 494.7500 | 15.7500 | n/a |

## Summarization

Artifact used: [Summarization/outputs/summarization_summary.json](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/Summarization/outputs/summarization_summary.json)

### Use Case

News summarization benchmark on CNN/DailyMail articles.

### Dataset

- Dataset: `cnn_dailymail:3.0.0`
- Split: `test`
- Articles evaluated: `30`
- Source: Hugging Face
- License: not recorded in run artifact

### Sampling

- Number of articles: `30`
- Max article tokens: `400`
- Seed: `42`
- Sampling technique: filtered sample based on max source-token limit

### Model Specification

- Model: `sshleifer/distilbart-cnn-12-6`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Temperature: `0.0`
- Top-p: `1.0`
- Max new tokens: `60`
- Sampling enabled: `false`

### Hardware Environment

Recorded:

- average memory usage MB
- average latency
- tokens per second

Not recorded:

- CPU model
- OS
- Python version
- GPU model

### Experimental Pipeline

1. Load filtered CNN/DailyMail sample
2. Generate one-sentence summaries
3. Score summaries against references
4. Save CSV and JSON summary

### Prompting Strategy

One-sentence summarization prompt:

```text
Summarize the following article in one sentence.
```

### Capability Metrics

| Model | ROUGE-1 F1 | ROUGE-2 F1 | ROUGE-L F1 | Semantic Similarity | Compression Ratio | Hallucination Rate | Length Violation Rate | Information Loss Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sshleifer/distilbart-cnn-12-6 | 0.4343 | 0.2037 | 0.3127 | 0.7651 | 0.1977 | 0.3000 | 1.0000 | 0.8333 |

### Operational Metrics

| Model | Articles | Avg Latency (s) | Tokens / Sec | Avg Memory MB | Avg Input Tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| sshleifer/distilbart-cnn-12-6 | 30 | 13.1839 | 5.0467 | 1171.0790 | 313.8000 |

## Code Generation

Artifacts used:

- [code_generation/runs/run_20260314_232239/summary.json](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/code_generation/runs/run_20260314_232239/summary.json)
- [code_generation/runs/run_20260314_232239/config_snapshot.json](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/code_generation/runs/run_20260314_232239/config_snapshot.json)

### Use Case

Natural-language-to-Python generation with execution against test cases.

### Dataset

- HumanEval attempted: `1`
- MBPP attempted: `0`
- Total attempted: `1`
- Source: benchmark task pool loader
- License: not recorded in run artifact

### Sampling

- HumanEval sample: `1`
- MBPP sample: `1` in config snapshot, but actual attempted MBPP in this run: `0`
- Time budget: `1` minute
- Execution timeout: `10` seconds
- Seed: `42`
- Prompt variant: `default`

### Model Specification

- Model label: `Phi-3 Mini`
- Model name: `microsoft/Phi-3-mini-4k-instruct`
- Backend: `hf_local`
- Load in 4-bit: `false`
- Use chat template: `true`
- Temperature: `0.2`
- Max new tokens: `128`
- Min new tokens: `48`
- Top-p: `1.0`
- Generation seed: `42`

### Hardware Environment

Recorded:

- peak RAM GB
- latency
- tokens per second

Not recorded:

- CPU model
- OS
- GPU
- Python version

### Experimental Pipeline

1. Load sampled code task
2. Build code-only prompt
3. Generate Python solution
4. Apply safety scan
5. Execute generated code against tests
6. Save task-level JSONL and summary

### Prompting Strategy

Code-only prompt requiring exact function signature and no explanation.

### Capability Metrics

| Model | pass@1 | Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | Format Compliance | Signature Compliance | Instruction Adherence | Unsafe Code Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Phi-3 Mini | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |

### Operational Metrics

| Model | Tasks Completed | Avg Latency / Task (s) | P95 Latency (s) | Tokens / Sec | Peak RAM (GB) | Avg Output Tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Phi-3 Mini | 1 | 621.6728 | 621.6728 | 0.1255 | 0.0105 | 78 |

## Instruction Following

Artifact used: [instruction_following/results/results_detailed.json](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/instruction_following/results/results_detailed.json)

### Use Case

Constraint-following evaluation over prompt instructions with length, format, and lexical constraints.

### Dataset

- Dataset used in saved artifact: fallback deterministic prompt set repeated to `20` prompts
- Primary dataset path in code: `google/IFEval`
- Source in actual artifact: fallback dataset was likely used for this result file
- License: not recorded

### Sampling

- Prompt count:
  - `Qwen/Qwen2.5-Coder-0.5B`: `20`
  - `deepseek-ai/deepseek-coder-1.3b-base`: `20`
  - `gemini-2.5-flash [BASELINE]`: `13` before deprecation
- Sampling technique: first-N selection or fallback deterministic prompt generation

### Model Specifications

| Model | Backend Type | Prompts |
| --- | --- | ---: |
| Qwen/Qwen2.5-Coder-0.5B | local Hugging Face | 20 |
| deepseek-ai/deepseek-coder-1.3b-base | local Hugging Face | 20 |
| gemini-2.5-flash [BASELINE] | Gemini API | 13 |

Quantization and device were not stored in the artifact.

### Hardware Environment

Recorded:

- average latency
- average tokens/sec
- average memory usage MB
- average output tokens

Not recorded:

- CPU model
- OS
- GPU
- Python version

### Experimental Pipeline

1. Load prompt sample
2. Generate response per prompt
3. Validate constraint satisfaction
4. Aggregate capability and reliability
5. Save combined JSON

### Prompting Strategy

Wrapper prompt:

```text
Follow the instruction exactly.
```

### Capability Metrics

| Model | Prompts | Pass Rate | Constraint Satisfaction | Format Compliance | Length Compliance | Lexical Compliance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen/Qwen2.5-Coder-0.5B | 20 | 0.4000 | 0.4000 | 0.0000 | 0.5000 | 0.5000 |
| deepseek-ai/deepseek-coder-1.3b-base | 20 | 0.4000 | 0.4000 | 1.0000 | 0.5000 | 0.0000 |
| gemini-2.5-flash [BASELINE] | 13 | 1.0000 | 0.0000 | n/a | n/a | n/a |

### Operational Metrics

| Model | Avg Latency (s) | Avg Tokens / Sec | Avg Memory MB | Avg Output Tokens | Notable Run Note |
| --- | ---: | ---: | ---: | ---: | --- |
| Qwen/Qwen2.5-Coder-0.5B | 17.8864 | 4.7858 | -9.1060 | 85.6000 | heavy overgeneration |
| deepseek-ai/deepseek-coder-1.3b-base | 42.8291 | 2.3349 | 72.5643 | 100.0000 | slower but better format compliance |
| gemini-2.5-flash [BASELINE] | 0.9784 | n/a | n/a | 0.0000 | deprecated after rate limit |

## Maths

Artifact used: [maths/outputs/predictions/results_gemini_real_api.json](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/maths/outputs/predictions/results_gemini_real_api.json)

### Use Case

Math word-problem reasoning benchmark over normalized datasets.

### Dataset

Actual saved live API artifact contains:

- `GSM8K`
- `SVAMP`

Source: normalized local benchmark datasets
License: not recorded in artifact

### Sampling

- `GSM8K`: `30` records
- `SVAMP`: `30` records
- Sampling seed for this live artifact: not recorded in file
- Sampling technique in benchmark code: stratified and deterministic by seed, but not fully echoed into this live file

### Model Specification

- Model: `gemini_2_5_flash_real`
- Mode: `live_api`
- Backend: Gemini API
- Quantization: n/a
- Device: cloud API, not recorded as local hardware

### Hardware Environment

Not meaningfully recorded for this live API run. No local CPU/RAM/GPU manifest is stored in the artifact.

### Experimental Pipeline

1. Load normalized dataset
2. Build sampled records
3. Send prompt to model
4. Parse final answer
5. Save per-record outputs

### Prompting Strategy

Math prompt requires a final numeric answer in:

```text
Final Answer: <number>
```

### Capability Metrics

| Dataset | Records | Accuracy |
| --- | ---: | ---: |
| GSM8K | 30 | 0.7667 |
| SVAMP | 30 | 0.0000 |

### Operational Metrics

| Dataset | Avg Latency (s) | Operational Note |
| --- | ---: | --- |
| GSM8K | 2.1515 | successful live API run |
| SVAMP | 0.0000 | run collapsed due to repeated 429 quota errors |

## Retrieval Grounded

Artifacts used:

- [Retrieval_grounded/outputs/metrics/results.json](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/Retrieval_grounded/outputs/metrics/results.json)
- [Retrieval_grounded/outputs/metrics/reproducibility.md](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/Retrieval_grounded/outputs/metrics/reproducibility.md)

### Use Case

Context-grounded question answering where answers must come from the provided passage.

### Dataset

- Dataset: `squad`
- Actual questions in saved result artifact: `1`
- Config file still shows `2`, so the saved artifact reflects a smaller realized run
- Source: Hugging Face SQuAD
- License: not recorded in artifact

### Sampling

- Configured:
  - split: `validation`
  - max context tokens: `80`
  - max answer tokens: `8`
  - temperature: `0.0`
  - device: `cpu`
- Actual evaluated questions in artifact: `1`

### Model Specification

- Model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- Device: `cpu`
- Temperature: `0.0`
- Top-p: `1.0`
- Max new tokens: `10`
- Quantization: not recorded

### Hardware Environment

Recorded in reproducibility notes:

- Platform: `Windows-11-10.0.26200-SP0`
- Device: `cpu`
- Python: `unknown`
- PyTorch: `unknown`
- Transformers: `unknown`

### Experimental Pipeline

1. Load and truncate QA sample
2. Prompt model with context-only QA instruction
3. Save prediction JSON
4. Compute capability and operational metrics
5. Write reproducibility notes

### Prompting Strategy

The model is instructed to answer using only the given context.

### Capability Metrics

| Model | Questions | Exact Match | F1 Score | Context Utilization | Answer Length Accuracy | Hallucination Rate | Unsupported Answer Rate | Partial Answer Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen/Qwen2.5-Coder-0.5B-Instruct | 1 | 100.0000 | 100.0000 | 100.0000 | 100.0000 | 0.0000 | 0.0000 | 0.0000 |

### Operational Metrics

| Model | Avg Latency (ms) | P50 (ms) | P95 (ms) | Tokens / Sec | Output Tokens | Avg Input Tokens | Memory MB | Wall Time (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen/Qwen2.5-Coder-0.5B-Instruct | 2876.9480 | 2876.9480 | 2876.9480 | 3.4759 | 10 | 101.0000 | 0.0000 | 2.8999 |

## Cross-Use Case Notes

- Full hardware metadata is still inconsistent across use cases.
- `Retrieval_grounded` has the best explicit environment logging in saved artifacts.
- `text_generation` has the best saved model-file metadata.
- `maths` and `instruction_following` show real evidence of API-rate-limit interruptions in some saved runs.
- `code_generation` run quality in the latest saved artifact is poor, but the artifact itself is well-structured.
