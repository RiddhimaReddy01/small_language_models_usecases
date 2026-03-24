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

If your laptop is memory-constrained, change `model.model_name` in `configs/default.json` to `t5-small`.

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

Create a local virtual environment so the project is easy to run on another laptop:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you prefer Conda, use your normal Conda environment and run the same `python -m pip install -r requirements.txt` command inside it.

## Run

Use the smoke test first. It evaluates 2 samples with `t5-small`, which is much faster for validating that installs, downloads, inference, metrics, and output writing all work correctly on a laptop.

```powershell
python .\scripts\run_benchmark.py --config .\configs\smoke_test.json
```

Then run the fuller CPU benchmark:

```powershell
python .\scripts\run_benchmark.py --config .\configs\default.json
```

To try another model, edit the config file or create a second config and pass it with `--config`.

Note:

- The first run downloads the dataset and model weights from Hugging Face, so it needs internet access.
- Later runs reuse the local cache and are much faster to start.

## Expected output

After a successful smoke test, you should see progress output followed by three generated files under `outputs/smoke_test/`.

Example:

```text
Evaluating: 100%|##########| 2/2 [00:03<00:00,  1.77s/it]

Per-sample results saved to: outputs/smoke_test/summarization_results.csv
Aggregate summary saved to: outputs/smoke_test/summarization_summary.json
Metrics tables saved to: outputs/smoke_test/summarization_metrics_tables.md
```

The exact timing numbers will vary by machine, but the run should complete and produce all three files.

## Outputs

The runner creates the configured output directory automatically if it does not already exist.

The default benchmark writes:

- `outputs/summarization_results.csv`
- `outputs/summarization_summary.json`
- `outputs/summarization_metrics_tables.md`

The smoke test writes:

- `outputs/smoke_test/summarization_results.csv`
- `outputs/smoke_test/summarization_summary.json`
- `outputs/smoke_test/summarization_metrics_tables.md`
