# Summarization Benchmark

This project evaluates local summarization models on a small CNN/DailyMail sample using a reproducible repo structure.

## Repo structure

```text
Summarization/
|-- configs/
|   `-- default.json
|-- scripts/
|   `-- run_benchmark.py
|-- src/
|   `-- summarization_benchmark/
|       |-- config.py
|       |-- data.py
|       |-- inference.py
|       |-- metrics.py
|       |-- runner.py
|       `-- main.py
|-- outputs/
|-- requirements.txt
`-- README.md
```

Why this layout helps:

- `configs/` keeps experiment settings versionable and repeatable.
- `data.py` isolates dataset ingestion and filtering.
- `inference.py` isolates model loading and decoding behavior.
- `metrics.py` keeps evaluation logic reusable across models.
- `runner.py` owns orchestration and output writing.
- `scripts/run_benchmark.py` gives a stable entrypoint for local execution.

## Recommended model

Default recommendation: `sshleifer/distilbart-cnn-12-6`

Why this is the best fit for a local laptop CPU:

- It is a distilled BART model tuned specifically for news summarization.
- It is much lighter than full `bart-large-cnn` while usually staying stronger than very small generic models like `t5-small`.
- It is realistic for a 30-article CPU benchmark without turning runtime into a multi-hour job.

If your laptop is memory-constrained, change `model.model_name` in [configs/default.json](c:\Users\riddh\OneDrive\Desktop\SLM use cases\Summarization\configs\default.json) to `t5-small`.

## Prompt

```text
Summarize the following article in one sentence.

Article:
{article}

Summary:
```

Consistency constraint:

- Word limit check defaults to 20 words.

## Inference settings

- `temperature=0.0`
- `top_p=1.0`
- `max_new_tokens=60`
- `do_sample=False`

## Sampling strategy

- Dataset: `cnn_dailymail` config `3.0.0`
- Split: `test`
- Number of articles: `30`
- Filter: article length `<= 400` model tokens
- Reference summaries: dataset `highlights`

## Metrics

The script reports:

- `ROUGE-1`, `ROUGE-2`, `ROUGE-L`
- Semantic similarity using `sentence-transformers/all-MiniLM-L6-v2`
- Compression ratio as `summary_words / article_words`
- Reliability heuristics:
  - `hallucination_rate`
  - `length_violation_rate`
  - `information_loss_rate`
- Operational metrics:
  - `latency_seconds`
  - `tokens_per_second`
  - `memory_mb`
  - `input_tokens`

Note: the three reliability metrics are heuristic approximations, not formal factuality judgments.

## Install

Use the Python interpreter available on your machine. In this environment, the direct Anaconda path is the safest option:

```powershell
& 'C:\Users\riddh\anaconda3\python.exe' -m pip install -r requirements.txt
```

## Run

```powershell
& 'C:\Users\riddh\anaconda3\python.exe' .\scripts\run_benchmark.py --config .\configs\default.json
```

To try another model, edit the config file or create a second config and pass it with `--config`.

## Outputs

The run writes:

- `outputs/summarization_results.csv`
- `outputs/summarization_summary.json`
