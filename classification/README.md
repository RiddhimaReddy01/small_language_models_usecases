# Classification Evaluation Framework

This project benchmarks local or API-backed language models on text classification tasks.

## Repo Structure

- `main.py`: thin CLI entrypoint
- `classification_eval/config.py`: shared configuration defaults
- `classification_eval/datasets.py`: built-in datasets and uploaded file ingestion
- `classification_eval/models.py`: Ollama and Gemini model wrappers
- `classification_eval/evaluator.py`: prediction loop and metrics
- `results/`: saved outputs and comparison reports
- `examples/`: sample uploaded datasets

## Quick Start

Run the built-in benchmark:

```bash
python "main.py" --model "phi3:mini" --profile "fast15"
```

Run a custom uploaded dataset:

```bash
python "main.py" --model "gemma2:2b" --input-file "examples/upload_example.csv" --dataset-name "demo-upload" --task-type "Sentiment"
```

If your uploaded file uses different column names, pass them explicitly:

```bash
python "main.py" --model "qwen2.5:1.5b" --input-file "my_data.csv" --text-column "review" --label-column "sentiment"
```

For numeric labels, provide the ordered label list:

```bash
python "main.py" --model "phi3:mini" --input-file "my_data.csv" --text-column "text" --label-column "label_id" --labels "negative,positive"
```

## Supported Uploaded Formats

- `.csv`
- `.jsonl`
- `.json`

Uploaded datasets should contain:

- one text column
- one label column

The pipeline will try to infer them automatically from common names such as `text`, `sentence`, `description`, and `label`.

## Output Files

Each run writes:

- `results/live_results_<model>_<timestamp>.csv`
- `results/raw_results_<timestamp>.csv`
- `results/metrics_summary_<timestamp>.json`

Saved model comparison tables live in `results/model_comparison.md`.

## Gemini Notes

Put `GOOGLE_API_KEY` in `.env` for Gemini runs.

The Gemini wrapper uses:

- primary: `gemini-3.1-flash-lite-preview`
- fallback on quota/rate-limit errors: `gemini-2.5-flash-lite`

