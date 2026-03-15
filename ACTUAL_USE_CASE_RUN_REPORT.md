# Actual Use Case Run Report

This report is rebuilt from the saved benchmark artifacts already present in the repository.

Each use case follows the same reporting format:

1. Use case introduction
2. Dataset description
3. Sampling protocol
4. Model specifications
5. Hardware environment
6. Actual prompt used
7. Capability metrics
8. Operational metrics

Two guardrails were used while filling it:

- `Parameter count` is shown only when it is either recorded in the repo or safely inferred from the model identifier or local docs.
- `Hardware` is limited to what the artifacts or local runtime probes actually prove. In this workspace, direct host hardware queries such as `systeminfo` and CIM access returned `Access denied`, so CPU model and installed RAM are still missing unless a benchmark logged them itself.

Shared host facts that were verifiable in this workspace:

| Component | Specification |
| --- | --- |
| OS | `Windows-11-10.0.26200-SP0` |
| Python | `3.12.7` |
| CPU identifier | `AMD64 Family 25 Model 117 Stepping 2, AuthenticAMD` |
| CPU model | not accessible from this workspace without elevated host access |
| Installed RAM | not accessible from this workspace |
| GPU model | not accessible from this workspace |

## Cross-Use-Case Summary

| Use Case | Primary Dataset | Best Local Model In Saved Results | Baseline / Cloud Model | Capability Snapshot | Operational Snapshot |
| --- | --- | --- | --- | --- | --- |
| Classification | `SST-2`, `Emotion`, `AG News` | `gemma2:2b` by average accuracy / F1 | `gemini-2.5-flash-lite` | local best accuracy `0.8056`; Gemini baseline underperformed on this saved sample | Gemini was fastest; local Ollama runs were slower but more accurate |
| Text Generation | local prompt suite (`15` tasks) | `qwen-2.5-3b` on constraint satisfaction | `gemini-baseline` | all runs had `1.0000` success rate; Gemini baseline had best constraint satisfaction (`0.1667`) | Gemini baseline was fastest and cheapest; local GGUF runs consumed much more RAM |
| Information Extraction | `SROIE` receipts | `SmolLM2-1.7B-Instruct` | `Gemini-2.5-Flash` | SmolLM2 had best F1 (`0.5000` micro / clean); Gemini had lower extraction quality on this run | Gemini was dramatically faster per document |
| Summarization | `cnn_dailymail:3.0.0` | `sshleifer/distilbart-cnn-12-6` | `gemini-2.5-flash` partial | DistilBART had the strongest ROUGE and semantic similarity in saved results | `t5-small` was the fastest local run; Gemini row is only a partial run |
| Code Generation | MBPP-heavy benchmark mix | `Qwen2.5 Coder 1.5B (Transformers Fast)` by pass@1 in saved table | `Gemini 2.5 Flash Lite (Baseline)` | Qwen 1.5B had highest pass@1 (`0.667`) on a very small attempted set; Gemini baseline was lower (`0.150`) but on many more tasks | Gemini baseline was the fastest by far; larger local models were much slower |
| Instruction Following | deterministic fallback prompt set | local runs tied on pass rate (`0.4000`) with different strengths | `gemini-2.5-flash [BASELINE]` | Gemini baseline hit `1.0000` pass rate in the saved JSON, but the baseline row is not directly comparable because supporting detail is incomplete | Gemini baseline was much faster; local runs showed overgeneration and slower decoding |
| Maths | `GSM8K`, `SVAMP` aggregate tables | `orca_mini_7b` among local rows on final answer accuracy | `gemini_2_5_flash_real` | Gemini baseline had best final answer accuracy (`38.3%`); Orca Mini 7B was best local row (`30.0%`) | Gemini baseline was the fastest; local rows traded accuracy for much higher latency |
| Retrieval Grounded | `SQuAD` validation (`30` questions in final comparison) | `Qwen/Qwen2.5-Coder-0.5B-Instruct` by exact match | `gemini/gemini-3.1-flash-lite-preview` | Qwen had best EM (`66.6667`); Gemini had best F1 (`77.7778`) | Gemini was fastest; DeepSeek 1.3B was slowest and weakest on this setup |

## Read This Report

- Capability tables show task quality, correctness, adherence, and robustness metrics.
- Operational tables show latency, throughput, memory, and other runtime cost signals.
- When a baseline row is marked `partial` or the sample count differs across rows, treat that comparison as directional rather than strictly apples-to-apples.
- Hardware details are intentionally conservative: the report records only what artifacts or local host probes actually proved.

## Classification

Artifacts used:

- `classification/results/metrics_tables.md`
- `classification/results/metrics_summary_1773488616.json`
- `classification/classification_eval/models.py`

### Use Case Introduction

Single-label text classification over sentiment, emotion, and topic prediction tasks.

### Dataset Description

| Dataset | Task |
| --- | --- |
| `SST-2` | sentiment classification |
| `Emotion` | emotion classification |
| `AG News` | news topic classification |

Source is the benchmark loader used by `classification_eval`; dataset license is not echoed into the saved result tables.

### Sampling Protocol

| Field | Value |
| --- | --- |
| Comparison table scope | `16` sampled items per model in the saved comparison table |
| Representative saved run profile | `fast15` |
| Test mode | `true` |
| Seed | `42` |
| Selection style | label-balanced sample across the three datasets |

### Model Specifications

| Model Run | Model Name | Parameter Count | Quantization | Inference Backend |
| --- | --- | --- | --- | --- |
| `gemma2:2b` | Gemma 2 2B | `2B` inferred from model identifier | not recorded in code | Ollama local wrapper |
| `phi3:mini` | Phi-3 Mini | `~3.8B` from local repo docs | not recorded in classification code | Ollama local wrapper |
| `qwen2.5:1.5b` | Qwen 2.5 1.5B | `1.5B` inferred from model identifier | not recorded in code | Ollama local wrapper |
| `gemini-2.5-flash-lite` | Gemini 2.5 Flash Lite | not published in repo | n/a | Gemini API |

### Hardware Environment

| Component | Specification |
| --- | --- |
| Device | local process for Ollama runs; cloud-managed for Gemini API |
| OS | not logged by the benchmark artifact |
| Python | not logged by the benchmark artifact |
| CPU | host exposes `AMD64 Family 25 Model 117 Stepping 2, AuthenticAMD`; benchmark artifact itself does not log CPU |
| RAM | not logged as installed capacity; only per-run memory deltas were recorded |
| GPU | not logged |

### Actual Prompt Used

```text
You are a text classification system.

Choose exactly one label from the list:
{labels}

Respond with only one label and no extra words.

Text:
{text}
```

### Capability Metrics

| Model Run | Avg Accuracy | Avg Macro F1 | Avg Weighted F1 | Avg Precision | Avg Recall | Avg Validity Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `gemma2:2b` | 0.8056 | 0.7302 | 0.7593 | 0.7083 | 0.7738 | 0.9444 |
| `phi3:mini` | 0.7500 | 0.6836 | 0.6836 | 0.6667 | 0.7500 | 1.0000 |
| `qwen2.5:1.5b` | 0.6389 | 0.5741 | 0.5741 | 0.5528 | 0.6389 | 1.0000 |
| `gemini-2.5-flash-lite` | 0.3889 | 0.3714 | 0.3873 | 0.3869 | 0.3730 | 0.5833 |

### Operational Metrics

| Model Run | Total Samples | Total Runtime (s) | Avg Throughput (samples/s) | Avg Mean Latency (s) | Avg P95 Latency (s) | Avg CPU Util (%) | Avg Mem Delta (MB) | Avg Parse Failure Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gemma2:2b` | 16 | 23.44 | 0.7222 | 1.4722 | 2.6957 | 88.35 | -117.70 | 0.0556 |
| `phi3:mini` | 16 | 29.73 | 0.5547 | 1.9278 | 3.1425 | 40.92 | 469.37 | 0.0000 |
| `qwen2.5:1.5b` | 16 | 12.63 | 1.2814 | 0.8258 | 1.0652 | 90.27 | 160.18 | 0.0000 |
| `gemini-2.5-flash-lite` | 16 | 4.16 | 4.8784 | 0.2449 | 0.3896 | 59.12 | 8.65 | 0.4167 |

## Text Generation

Artifacts used:

- `text_generation/results/runs/suite_20260315_000947/metrics_tables.md`
- `text_generation/results/runs/suite_20260315_000947/benchmark_summary.json`
- `text_generation/results/runs/suite_20260315_000947/suite_manifest.json`
- `text_generation/results/runs/suite_20260315_000947/qwen-2.5-3b.json`
- `text_generation/data/samples.json`

### Use Case Introduction

Constraint-aware open generation benchmark across short summarization, email, creative, classification, translation, and code-style prompts.

### Dataset Description

The saved suite uses `text_generation/data/samples.json`, a local prompt set with `15` tasks and explicit lightweight constraints.

### Sampling Protocol

| Field | Value |
| --- | --- |
| Task source | `text_generation/data/samples.json` |
| Task count | `15` |
| Seed | `42` |
| Repeats | `1` |
| Perturbation | `false` |
| Selection style | fixed prompt file materialized into the suite |

### Model Specifications

| Model Run | Model Name | Parameter Count | Quantization | Inference Backend |
| --- | --- | --- | --- | --- |
| `qwen-2.5-3b` | Alibaba Qwen 2.5 3B Instruct | `3B` from config description and model name | `q4_k_m` from GGUF filename | `llama_cpp` / GGUF |
| `phi-3.5-mini` | Microsoft Phi-3.5 Mini Instruct | `~3.8B` inferred from model family name | `Q4_K_M` from GGUF filename | `llama_cpp` / GGUF |
| `gemini-baseline` | Gemini baseline run | not recorded in suite manifest | n/a | Google API |

Common run settings recorded in the suite:

| Setting | Value |
| --- | --- |
| Temperature | `0.7` |
| Workers | `1` |
| Seed | `42` |
| Context length | `4096` for local GGUF models |
| Threads | `4` for local GGUF models |

### Hardware Environment

| Component | Specification |
| --- | --- |
| Device | local GGUF inference process with `n_threads=4`; cloud-managed for Gemini API |
| OS | not logged in the suite |
| Python | not logged in the suite |
| CPU | host exposes `AMD64 Family 25 Model 117 Stepping 2, AuthenticAMD`; suite itself does not log CPU |
| RAM | peak process RAM and RAM deltas recorded per model |
| GPU | not logged |

### Actual Prompts Used

Examples pulled from the saved task file:

```text
Summarize the following text in one sentence: The Ryzen 9 7940HS is a high-end laptop processor from AMD. It features 8 cores and 16 threads, with a boost clock of up to 5.2 GHz. It is built on the Zen 4 architecture and includes an integrated Radeon 780M GPU.
```

```text
Write a short professional email to a client explaining that their project will be delayed by two days due to a server migration.
```

```text
Write a 4-line poem about artificial intelligence.
```

### Capability Metrics

| Model Run | Total Tasks | Success Rate | Constraint Satisfaction | Format Compliance | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore F1 | Refusal Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `phi-3.5-mini` | 15 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0667 |
| `qwen-2.5-3b` | 15 | 1.0000 | 0.1333 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0667 |
| `gemini-baseline` | 15 | 1.0000 | 0.1667 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0667 |

### Operational Metrics

| Model Run | Successful Tasks | Failed Tasks | Avg TTFT (s) | Avg Total Time (s) | Avg Tokens | Avg TPS | Avg Peak RAM MB | Avg Load Time (s) | Total Cost USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `phi-3.5-mini` | 15 | 0 | 0.8435 | 45.6180 | 402.8667 | 9.1310 | 3035.5568 | 3.2469 | 0.0000 |
| `qwen-2.5-3b` | 15 | 0 | 0.5061 | 22.1081 | 241.8667 | 10.8736 | 2486.0938 | 6.1511 | 0.0000 |
| `gemini-baseline` | 15 | 0 | 1.1757 | 5.8787 | 155.4800 | 39.0056 | 0.0000 | 0.0010 | 0.0002 |

## Information Extraction

Artifacts used:

- `Information Extraction/results/final_capability_metrics.md`
- `Information Extraction/results/final_operational_metrics.md`
- `Information Extraction/configs/sroie_gemini_iter.json`
- `Information Extraction/src/ie_benchmark/prompting.py`

### Use Case Introduction

Receipt information extraction into a fixed JSON schema.

### Dataset Description

| Field | Value |
| --- | --- |
| Dataset | `SROIE` |
| Processed source | `data/processed/sroie_clean.jsonl` |
| Target fields | `company`, `address`, `date`, `total` |
| License | not recorded in saved comparison tables |

### Sampling Protocol

The comparison tables in `Information Extraction/results` are the saved cross-model summary. The explicitly logged Gemini config for this benchmark records:

| Field | Value |
| --- | --- |
| Sample size | `4` |
| Seed | `42` |
| Sampling method | `random` |
| Clean sample size | `4` |
| Noisy sample size | `0` |

### Model Specifications

| Model Run | Model Name | Parameter Count | Quantization | Inference Backend |
| --- | --- | --- | --- | --- |
| `Gemini-2.5-Flash` | `gemini-2.5-flash` | not published in repo | `none` in Gemini config | Gemini API |
| `Qwen2.5-0.5B-Instruct` | Qwen 2.5 0.5B Instruct | `0.5B` inferred from model identifier | not recorded in saved comparison table | local transformers-style run |
| `Qwen2.5-1.5B-Instruct` | Qwen 2.5 1.5B Instruct | `1.5B` inferred from model identifier | not recorded in saved comparison table | local transformers-style run |
| `SmolLM2-1.7B-Instruct` | SmolLM2 1.7B Instruct | `1.7B` inferred from model identifier | not recorded in saved comparison table | local transformers-style run |

Gemini config also records:

| Setting | Value |
| --- | --- |
| Device | `cpu` |
| Temperature | `0.0` |
| Top-p | `1.0` |
| Max new tokens | `96` |
| Torch threads | `6` |

### Hardware Environment

| Component | Specification |
| --- | --- |
| Device | Gemini config explicitly says `cpu`; local comparison runs do not add richer host hardware |
| OS | not recorded |
| Python | not recorded |
| CPU | host exposes `AMD64 Family 25 Model 117 Stepping 2, AuthenticAMD`; comparison artifacts do not log CPU |
| RAM | only token counts and latency are consistently recorded |
| GPU | peak GPU memory column exists but is empty in the saved table |

### Actual Prompt Used

```text
Task: extract receipt fields from OCR text.
Fields: company, address, date, total
Output rules:
1. Return exactly one JSON object.
2. Do not use markdown, code fences, commentary, or explanations.
3. Always include all four keys: company, address, date, total.
4. If a field is missing, use an empty string.
5. Normalize date to YYYY-MM-DD when possible.
6. Copy values from the receipt text; do not invent values.

Return this exact schema:
{"company":"","address":"","date":"","total":""}

Receipt OCR text:
{document_text}
```

### Capability Metrics

| Model Run | Macro F1 | Micro F1 | Exact Match | Schema Valid Rate | Hallucination Rate | F1 Clean | F1 Noisy | Robustness Drop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Qwen2.5-0.5B-Instruct` | 0.1667 | 0.2222 | 0.0000 | 0.5000 | 0.0000 | 0.2222 |  |  |
| `Qwen2.5-1.5B-Instruct` | 0.0250 | 0.0417 | 0.0000 | 0.2000 | 0.3750 | 0.0417 |  |  |
| `SmolLM2-1.7B-Instruct` | 0.4792 | 0.5000 | 0.0000 | 1.0000 | 0.1667 | 0.5000 |  |  |
| `Gemini-2.5-Flash` | 0.1875 | 0.3000 | 0.0000 | 0.2500 | 0.2500 | 0.3000 |  |  |

### Operational Metrics

| Model Run | Avg Latency / Doc (s) | Throughput (docs/min) | Peak GPU Memory (MB) | Avg Input Tokens | Avg Output Tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| `Qwen2.5-0.5B-Instruct` | 14.5900 | 4.1124 |  | 372.7500 | 96.0000 |
| `Qwen2.5-1.5B-Instruct` | 17.4535 | 3.4377 |  | 383.1000 | 64.0000 |
| `SmolLM2-1.7B-Instruct` | 36.1407 | 1.6602 |  | 487.5000 | 53.0000 |
| `Gemini-2.5-Flash` | 0.8567 | 70.0356 |  | 494.7500 | 15.7500 |

## Summarization

Artifacts used:

- `Summarization/results_tables.md`
- `Summarization/outputs/summarization_summary.json`

### Use Case Introduction

Single-sentence article summarization over CNN/DailyMail-style news articles.

### Dataset Description

| Field | Value |
| --- | --- |
| Primary saved dataset | `cnn_dailymail:3.0.0` |
| Split | `test` |
| Article count in default saved run | `30` |
| Source | Hugging Face |
| License | not logged in the result tables |

### Sampling Protocol

| Field | Value |
| --- | --- |
| Number of articles | `30` in the default saved run |
| Max article tokens | `400` |
| Seed | `42` |
| Selection style | filtered sample based on source-token limit |

### Model Specifications

| Model Run | Model Name | Parameter Count | Quantization | Inference Backend |
| --- | --- | --- | --- | --- |
| `Default` | `sshleifer/distilbart-cnn-12-6` | not recorded in repo | not recorded in saved summary | local Hugging Face seq2seq |
| `Fast CPU` | `t5-small` | not recorded in repo | not recorded in saved table | local Hugging Face seq2seq |
| `Gemini Flash Partial` | `gemini-2.5-flash` | not published in repo | n/a | Gemini API |

The default saved run also records:

| Setting | Value |
| --- | --- |
| Temperature | `0.0` |
| Top-p | `1.0` |
| Max new tokens | `60` |
| Sampling enabled | `false` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |

### Hardware Environment

| Component | Specification |
| --- | --- |
| Device | local CPU process for local models; API-managed for Gemini runs |
| OS | not recorded |
| Python | not recorded |
| CPU | host exposes `AMD64 Family 25 Model 117 Stepping 2, AuthenticAMD`; summarization artifact itself does not log CPU |
| RAM | average process memory is recorded for local runs |
| GPU | not recorded |

### Actual Prompt Used

```text
Summarize the following article in one sentence.

Article:
{article}

Summary:
```

### Capability Metrics

| Run | Model | Articles | ROUGE-1 F1 | ROUGE-2 F1 | ROUGE-L F1 | Semantic Similarity | Compression Ratio | Hallucination Rate | Length Violation Rate | Information Loss Rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Default` | `sshleifer/distilbart-cnn-12-6` | 30 | 0.4343 | 0.2037 | 0.3127 | 0.7651 | 0.1977 | 0.3000 | 1.0000 | 0.8333 |
| `Fast CPU` | `t5-small` | 30 | 0.1173 | 0.0592 | 0.0814 | 0.2682 | 0.0510 | 0.7000 | 0.3000 | 0.9333 |
| `Gemini Flash Partial` | `gemini-2.5-flash` | 11 partial | 0.1227 | 0.0181 | 0.0884 | 0.3760 | 0.0277 | 0.4545 | 0.2727 | 1.0000 |

### Operational Metrics

| Run | Model | Articles | Avg Latency / Article | Throughput | Avg Memory Usage | Avg Input Tokens | End-to-End Wall Time |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `Default` | `sshleifer/distilbart-cnn-12-6` | 30 | 13.1839 s | 5.0467 tokens/s | 1171.08 MB | 313.80 | ~395.5 s |
| `Fast CPU` | `t5-small` | 30 | 0.7085 s | 15.3606 tokens/s | 681.99 MB | 318.03 | ~21.3 s |
| `Gemini Flash Partial` | `gemini-2.5-flash` | 11 partial | 0.8994 s | 9.4939 tokens/s | API-managed | 329.45 | Partial run |

## Code Generation

Artifacts used:

- `code_generation/benchmarks/tables/latest_report.md`
- `code_generation/benchmarks/tables/latest_summary.json`
- `code_generation/runs/run_20260314_232239/task_results.jsonl`
- `code_generation/src/codegen_eval/prompts.py`

### Use Case Introduction

Natural-language-to-code evaluation where generated Python is executed against benchmark tests.

### Dataset Description

The saved latest comparison table is MBPP-heavy:

| Field | Value |
| --- | --- |
| HumanEval attempted | `0` in the latest comparison table |
| MBPP attempted | model-dependent, up to `20` |
| Source | benchmark task pool loader |
| License | not logged in the saved comparison table |

### Sampling Protocol

| Field | Value |
| --- | --- |
| Time budget | `4` minutes per model in the saved comparison table |
| Dataset emphasis | MBPP in the latest saved comparison |
| Prompt variant | `default` in the concrete saved run artifact |
| Seed | not echoed in `latest_summary.json`; one concrete run snapshot records `42` |

### Model Specifications

| Model Run | Model Name | Parameter Count | Quantization | Inference Backend |
| --- | --- | --- | --- | --- |
| `Qwen2.5 Coder 0.5B (Transformers Fast)` | `Qwen/Qwen2.5-Coder-0.5B-Instruct` | `0.5B` inferred from model identifier | not recorded in saved summary | local Transformers |
| `DeepSeek Coder 1.3B (Transformers Fast)` | `deepseek-ai/deepseek-coder-1.3b-instruct` | `1.3B` inferred from model identifier | not recorded in saved summary | local Transformers |
| `Qwen2.5 Coder 1.5B (Transformers Fast)` | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | `1.5B` inferred from model identifier | not recorded in saved summary | local Transformers |
| `Gemini 2.5 Flash Lite (Baseline)` | `models/gemini-2.5-flash-lite` | not published in repo | n/a | Gemini API |

One concrete run snapshot for `Phi-3 Mini` also exists and records:

| Setting | Value |
| --- | --- |
| Model name | `microsoft/Phi-3-mini-4k-instruct` |
| Parameter count | `~3.8B` from local repo docs |
| Backend | `hf_local` |
| Load in 4-bit | `false` |
| Temperature | `0.2` |
| Max new tokens | `128` |
| Min new tokens | `48` |
| Top-p | `1.0` |
| Seed | `42` |

### Hardware Environment

| Component | Specification |
| --- | --- |
| Device | local process for Transformers runs; cloud-managed for Gemini baseline |
| OS | not logged in the saved comparison tables |
| Python | not logged in the saved comparison tables |
| CPU | host exposes `AMD64 Family 25 Model 117 Stepping 2, AuthenticAMD`; saved comparison table does not log CPU |
| RAM | peak RAM in GB is recorded |
| GPU | not logged |

### Actual Prompt Used

Example prompt pulled from the saved `Phi-3 Mini` task artifact:

~~~text
Write a Python function that solves the following problem.

Problem:
Complete the Python function defined in the starter code.

Starter code:
```python


def correct_bracketing(brackets: str):
    """ brackets is a string of "(" and ")".
    return True if every opening bracket has a corresponding closing bracket.

    >>> correct_bracketing("(")
    False
    >>> correct_bracketing("()")
    True
    >>> correct_bracketing("(()())")
    True
    >>> correct_bracketing(")(()")
    False
    """
```

Requirements:
- Return only Python code
- Use the exact function name `correct_bracketing`
- Preserve the required parameters
- Do not include explanations
~~~

### Capability Metrics

| Model Run | MBPP Attempted | Total Attempted | pass@1 | Syntax Error Rate | Runtime Failure Rate | Logical Failure Rate | Reliability Score | Format Compliance | Signature Compliance | Instruction Adherence | Unsafe Code Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Qwen2.5 Coder 0.5B (Transformers Fast)` | 20 | 20 | 0.100 | 0.250 | 0.250 | 0.400 | 0.100 | 0.750 | 0.750 | 0.750 | 0.000 |
| `DeepSeek Coder 1.3B (Transformers Fast)` | 6 | 6 | 0.167 | 0.667 | 0.000 | 0.167 | 0.167 | 0.000 | 0.333 | 0.000 | 0.000 |
| `Qwen2.5 Coder 1.5B (Transformers Fast)` | 3 | 3 | 0.667 | 0.333 | 0.000 | 0.000 | 0.667 | 0.667 | 0.667 | 0.667 | 0.000 |
| `Gemini 2.5 Flash Lite (Baseline)` | 20 | 20 | 0.150 | 0.100 | 0.450 | 0.300 | 0.150 | 0.550 | 0.550 | 0.550 | 0.000 |

### Operational Metrics

| Model Run | Time Budget (min) | Tasks Completed | Avg Latency / Task (s) | P95 Latency (s) | Tokens/sec | Peak RAM (GB) | Avg Output Tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Qwen2.5 Coder 0.5B (Transformers Fast)` | 4 | 20 | 6.131 | 9.615 | 7.027 | 0.014 | 41.450 |
| `DeepSeek Coder 1.3B (Transformers Fast)` | 4 | 6 | 45.797 | 49.950 | 1.296 | 0.013 | 59.333 |
| `Qwen2.5 Coder 1.5B (Transformers Fast)` | 4 | 3 | 94.947 | 125.208 | 0.578 | 0.013 | 54.333 |
| `Gemini 2.5 Flash Lite (Baseline)` | 4 | 13 | 0.665 | 0.871 | 110.141 | 0.013 | 59.538 |

## Instruction Following

Artifacts used:

- `instruction_following/results/results_detailed.json`
- `instruction_following/src/instruction_following/pipeline_core.py`

### Use Case Introduction

Instruction-following benchmark with constraint checks for format, length, and lexical rules.

### Dataset Description

The saved artifact strongly indicates the fallback deterministic prompt set was used. The prompt inventory repeats five instructions to reach `20` prompts for local models.

### Sampling Protocol

| Field | Value |
| --- | --- |
| Fallback prompt types | `5` repeated prompts |
| Prompt count | `20` for local models, `13` for Gemini baseline before deprecation |
| Selection style | deterministic fallback prompt generation or first-N dataset selection |
| Seed | not explicitly saved in `results_detailed.json` |

### Model Specifications

| Model Run | Model Name | Parameter Count | Quantization | Inference Backend |
| --- | --- | --- | --- | --- |
| `Qwen/Qwen2.5-Coder-0.5B` | Qwen 2.5 Coder 0.5B | `0.5B` inferred from model identifier | not recorded in saved artifact | local Hugging Face |
| `deepseek-ai/deepseek-coder-1.3b-base` | DeepSeek Coder 1.3B Base | `1.3B` inferred from model identifier | not recorded in saved artifact | local Hugging Face |
| `gemini-2.5-flash [BASELINE]` | Gemini 2.5 Flash | not published in repo | n/a | Gemini API |

Default inference params from the pipeline:

| Setting | Value |
| --- | --- |
| Temperature | `0.0` |
| Top-p | `1.0` |
| `do_sample` | `false` |
| Max new tokens | `120` |

### Hardware Environment

| Component | Specification |
| --- | --- |
| Device | local process for local Hugging Face models; API-managed for Gemini |
| OS | not logged in the saved artifact |
| Python | not logged in the saved artifact |
| CPU | host exposes `AMD64 Family 25 Model 117 Stepping 2, AuthenticAMD`; saved artifact does not log CPU |
| RAM | average memory delta in MB is recorded |
| GPU | not logged |

### Actual Prompts Used

Prompt wrapper:

```text
Follow the instruction exactly.

Instruction:
{instruction}

Response:
```

Actual fallback instructions present in the saved result file include:

```text
What is machine learning? Answer in exactly 15 words.
List benefits of Python as bullet points.
Explain AI without using 'intelligence' or 'learning'.
Describe climate change in under 40 words.
Write about Python programming and include 'efficient'.
```

### Capability Metrics

| Model Run | Prompts | Pass Rate | Constraint Satisfaction | Format Compliance | Length Compliance | Lexical Compliance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `Qwen/Qwen2.5-Coder-0.5B` | 20 | 0.4000 | 0.4000 | 0.0000 | 0.5000 | 0.5000 |
| `deepseek-ai/deepseek-coder-1.3b-base` | 20 | 0.4000 | 0.4000 | 1.0000 | 0.5000 | 0.0000 |
| `gemini-2.5-flash [BASELINE]` | 13 | 1.0000 | 0.0000 | n/a | n/a | n/a |

### Operational Metrics

| Model Run | Avg Latency (s) | Avg Tokens / Sec | Avg Memory MB | Avg Output Tokens | Notable Run Note |
| --- | ---: | ---: | ---: | ---: | --- |
| `Qwen/Qwen2.5-Coder-0.5B` | 17.8864 | 4.7858 | -9.1060 | 85.6000 | heavy overgeneration |
| `deepseek-ai/deepseek-coder-1.3b-base` | 42.8291 | 2.3349 | 72.5643 | 100.0000 | slower but better format compliance |
| `gemini-2.5-flash [BASELINE]` | 0.9784 | n/a | n/a | 0.0000 | deprecated after rate limit |

## Maths

Artifacts used:

- `maths/outputs/metrics/FINAL_COMPREHENSIVE_TABLES.md`
- `maths/outputs/metrics/BENCHMARK_RESULTS.md`
- `maths/outputs/metrics/benchmark_metrics.json`
- `maths/src/prompts.py`

### Use Case Introduction

Math word-problem solving benchmark over normalized arithmetic and reasoning datasets.

### Dataset Description

| Dataset | Source |
| --- | --- |
| `GSM8K` | normalized local benchmark dataset |
| `SVAMP` | normalized local benchmark dataset |

The live saved artifact does not echo source license text.

### Sampling Protocol

The saved comparison tables are aggregated across benchmark runs, not a single one-shot artifact. The metrics file records these realized sample totals:

| Model Run | Samples |
| --- | ---: |
| `orca_mini_7b` | 20 |
| `gemma_2b` | 130 |
| `phi3_mini` | 130 |
| `mistral_7b` | 110 |
| `gemini_2_5_flash_real` | 60 |

### Model Specifications

| Model Run | Model Name | Parameter Count | Quantization | Inference Backend |
| --- | --- | --- | --- | --- |
| `orca_mini_7b` | Orca Mini 7B | `7B` inferred from model identifier | not recorded in metrics file | local model runner |
| `gemma_2b` | Gemma 2B | `2B` inferred from model identifier | not recorded in metrics file | local model runner |
| `phi3_mini` | Phi-3 Mini | `~3.8B` from local repo docs / model family | not recorded in metrics file | local model runner |
| `mistral_7b` | Mistral 7B | `7B` inferred from model identifier | not recorded in metrics file | local model runner |
| `gemini_2_5_flash_real` | Gemini 2.5 Flash | not published in repo | n/a | Gemini API |

### Hardware Environment

| Component | Specification |
| --- | --- |
| Device | local model runs plus Gemini API baseline |
| OS | not logged in the saved maths tables |
| Python | not logged in the saved maths tables |
| CPU | local host CPU model not logged in maths artifacts |
| RAM | recorded in the operational table as GB by model |
| GPU | not logged |

### Actual Prompt Used

```text
Solve the following math problem carefully.

Provide the final answer in the format:

Final Answer: <number>

Problem:
{question}
```

### Capability Metrics

| Model | Final Answer Accuracy (%) | Pass@3 (%) | Majority Vote Accuracy (%) | Accuracy Variance | Hallucination Rate (%) | Perturbation Robustness (%) | Confident Error Rate (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `orca_mini_7b` | 30.0 | 65.7 | 21.6 | 22.11 | 35.0 | 70.0 | 23.3 |
| `gemma_2b` | 20.8 | 50.3 | 11.1 | 16.58 | 39.6 | 30.0 | 26.4 |
| `phi3_mini` | 19.2 | 47.3 | 9.7 | 15.65 | 40.4 | 32.0 | 26.9 |
| `mistral_7b` | 10.0 | 27.1 | 2.8 | 9.08 | 45.0 | 10.0 | 30.0 |
| `gemini_2_5_flash_real` | 38.3 | 76.5 | 32.8 | 24.04 | 30.8 | 85.0 | 20.6 |

### Operational Metrics

| Model | Output Consistency (%) | Answer Stability (%) | Reproducibility (%) | Format Compliance (%) | Traceable Reasoning (%) | Error Traceability (%) | Expected Calibration Error | Latency (s) | Throughput (queries/min) | RAM (GB) | Samples |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `orca_mini_7b` | 30.0 | 30.0 | 30.0 | 95.0 | 90.0 | 75.0 | 0.00 | 97.92 | 0.61 | 8 | 20 |
| `gemma_2b` | 100.0 | 33.3 | 33.3 | 95.0 | 90.0 | 75.0 | 0.00 | 10.24 | 5.86 | 4 | 130 |
| `phi3_mini` | 100.0 | 16.7 | 16.7 | 95.0 | 90.0 | 75.0 | 0.00 | 28.41 | 2.11 | 8 | 130 |
| `mistral_7b` | 100.0 | 0.0 | 0.0 | 95.0 | 90.0 | 75.0 | 0.00 | 20.44 | 2.94 | 12 | 110 |
| `gemini_2_5_flash_real` | 38.3 | 38.3 | 38.3 | 98.0 | 95.0 | 75.0 | 0.00 | 1.08 | 55.78 | 0 (cloud) | 60 |

## Retrieval Grounded

Artifacts used:

- `Retrieval_grounded/outputs_qwen05b_arrow30/metrics/results.json`
- `Retrieval_grounded/outputs_deepseek13b_arrow30/metrics/results.json`
- `Retrieval_grounded/outputs_gemini_flash_arrow30/metrics/results.json`
- `Retrieval_grounded/outputs_qwen05b_arrow30/metrics/reproducibility.md`
- `Retrieval_grounded/src/prompts.py`

### Use Case Introduction

Context-grounded QA where the answer must be supported by the supplied passage.

### Dataset Description

| Field | Value |
| --- | --- |
| Dataset | `squad` |
| Actual questions in final comparison | `30` |
| Configured split | `validation` |
| Source | Hugging Face SQuAD |
| License | not echoed into the saved artifact |

### Sampling Protocol

| Field | Value |
| --- | --- |
| Actual evaluated questions | `30` |
| Selection method | first `30` records from the locally cached validation Arrow file |
| Max context tokens | `80` |
| Max answer tokens | `8` |
| Temperature | `0.0` |
| `do_sample` | `false` |

### Model Specifications

| Model Run | Model Name | Parameter Count | Quantization | Inference Backend |
| --- | --- | --- | --- | --- |
| `Qwen/Qwen2.5-Coder-0.5B-Instruct` | Qwen 2.5 Coder 0.5B Instruct | `0.5B` inferred from name | not recorded | local Hugging Face-style QA runner |
| `deepseek-ai/deepseek-coder-1.3b-instruct` | DeepSeek Coder 1.3B Instruct | `1.3B` inferred from name | not recorded | local Hugging Face-style QA runner |
| `gemini/gemini-3.1-flash-lite-preview` | Gemini 3.1 Flash Lite Preview | not published in repo | n/a | Gemini API |

Additional run settings recorded in the artifact:

| Setting | Value |
| --- | --- |
| Device | `cpu` |
| Temperature | `0.0` |
| Top-p | `1.0` |
| Max new tokens | `10` |

### Hardware Environment

| Component | Specification |
| --- | --- |
| Platform | `Windows-11-10.0.26200-SP0` |
| Device | `cpu` for local runs; API-managed for Gemini baseline |
| Python | `3.12.7` on the local host; benchmark artifact does not log a per-run Python manifest |
| PyTorch | not logged in the final comparison artifacts |
| Transformers | not logged in the final comparison artifacts |
| CPU model | not logged |
| RAM | not logged as installed capacity; run memory metric exists separately |
| GPU | none recorded |

### Actual Prompt Used

```text
Answer the question using only the information in the context.

Context:
{context}

Question:
{question}

Answer:
```

### Capability Metrics

| Model Run | Questions | Exact Match | F1 Score | Context Utilization | Answer Length Accuracy | Hallucination Rate | Unsupported Answer Rate | Partial Answer Rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Qwen/Qwen2.5-Coder-0.5B-Instruct` | 30 | 66.6667 | 71.2576 | 96.6667 | 86.6667 | 3.3333 | 3.3333 | 13.3333 |
| `deepseek-ai/deepseek-coder-1.3b-instruct` | 30 | 36.6667 | 48.0532 | 46.6667 | 50.0000 | 53.3333 | 53.3333 | 30.0000 |
| `gemini/gemini-3.1-flash-lite-preview` | 30 | 63.3333 | 77.7778 | 83.3333 | 90.0000 | 16.6667 | 16.6667 | 26.6667 |

### Operational Metrics

| Model Run | Avg Latency (ms) | P50 (ms) | P95 (ms) | Tokens / Sec | Output Tokens | Avg Input Tokens | Memory MB | Wall Time (s) | Questions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Qwen/Qwen2.5-Coder-0.5B-Instruct` | 5534.1170 | 6442.2719 | 8078.8178 | 4.2283 | 702 | 196.8333 | 0.0000 | 166.3785 | 30 |
| `deepseek-ai/deepseek-coder-1.3b-instruct` | 17564.8148 | 16642.1094 | 41458.6238 | 1.3872 | 731 | 222.3333 | 0.0000 | 528.9000 | 30 |
| `gemini/gemini-3.1-flash-lite-preview` | 828.5257 | 828.9696 | 1055.8537 | 6.3969 | 159 | 191.2667 | 0.0000 | not recorded in results.json | 30 |

## Notes On Gaps

- `classification`, `instruction_following`, and `maths` still do not emit a full hardware manifest.
- `text_generation` has the best local model-file metadata.
- `Retrieval_grounded` has the best explicit reproducibility note for environment.
- `code_generation` and `Summarization` already have useful saved comparison tables; they are better sources than any single-run summary file.
