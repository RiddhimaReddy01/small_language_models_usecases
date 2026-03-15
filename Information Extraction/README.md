# Information Extraction Benchmark Pipeline

This repository is structured to be easy to push to GitHub, easy to install, and easy to run for SROIE-style receipt extraction experiments.

The benchmark produces two primary result tables:

- capability metrics
- operational metrics

## Repo structure

```text
.
|-- configs/
|-- data/
|   |-- raw/
|   |-- processed/
|   `-- README.md
|-- scripts/
|-- src/ie_benchmark/
|-- ingest_sroie.py
|-- run_benchmark.py
`-- pyproject.toml
```

## Install

```powershell
& 'C:\Users\riddh\anaconda3\python.exe' -m pip install -e .
```

For 4-bit inference:

```powershell
& 'C:\Users\riddh\anaconda3\python.exe' -m pip install -e .[quant]
```

## Data ingestion

Put raw SROIE-style OCR files and label files under `data/raw/`, for example:

```text
data/raw/sroie/clean/ocr/
data/raw/sroie/clean/labels/
data/raw/sroie/noisy/ocr/
data/raw/sroie/noisy/labels/
```

Convert them into benchmark-ready JSONL:

```powershell
ie-benchmark ingest-sroie --ocr-dir data/raw/sroie/clean/ocr --labels-dir data/raw/sroie/clean/labels --output data/processed/sroie_clean.jsonl
ie-benchmark ingest-sroie --ocr-dir data/raw/sroie/noisy/ocr --labels-dir data/raw/sroie/noisy/labels --output data/processed/sroie_noisy.jsonl --split noisy
```

Or download the Hugging Face mirror directly:

```powershell
ie-benchmark download-sroie-hf --output data/processed/sroie_clean.jsonl --split train
```

The ingester supports:

- OCR `.txt`
- OCR `.json` with a `text` field or simple list payload
- label files in JSON or line-based `key:value`, `key<TAB>value`, or `key,value` form

## Run inference

Packaged CLI:

```powershell
ie-benchmark run --config configs/sroie_quick.json
```

Repo-root wrapper:

```powershell
& 'C:\Users\riddh\anaconda3\python.exe' run_benchmark.py
```

Fast iteration config:

```powershell
& 'C:\Users\riddh\anaconda3\python.exe' run_benchmark.py run --config configs/sroie_cpu_iter.json
```

Single config for the current working local models:

```powershell
ie-benchmark run --config configs/sroie_cpu_working_models.json
```

If you later install Ollama, the same benchmark can use a long-lived local backend process:

```powershell
ollama serve
ollama pull qwen2.5:0.5b-instruct
& 'C:\Users\riddh\anaconda3\python.exe' run_benchmark.py run --config configs/sroie_ollama_iter.json
```

## Save final tables

Use the stable `results/` directory for the final comparison you want to commit or share.

Export selected run summaries:

```powershell
ie-benchmark export-results `
  --summary outputs/20260314_063054/summary.json `
  --summary outputs/20260314_061420/summary.json `
  --summary outputs/20260314_054734/summary.json `
  --model SmolLM2-1.7B-Instruct `
  --model Qwen2.5-0.5B-Instruct `
  --model Qwen2.5-1.5B-Instruct `
  --output-dir results
```

Or use the helper script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/export_final_results.ps1
```

For a cleaner apples-to-apples comparison going forward, rerun the shared config first:

```powershell
ie-benchmark run --config configs/sroie_cpu_working_models.json
```

## Outputs

Outputs are written to `outputs/<timestamp>/`:

- `capability_metrics.csv`
- `operational_metrics.csv`
- `capability_metrics.md`
- `operational_metrics.md`
- `summary.json`
- `per_example_predictions.jsonl`

Stable final artifacts can be exported to `results/`:

- `final_capability_metrics.csv`
- `final_capability_metrics.md`
- `final_operational_metrics.csv`
- `final_operational_metrics.md`
- `final_sources.json`

## Expected processed format

Each processed JSONL line should look like:

```json
{
  "id": "receipt_0001",
  "text": "OCR text for the receipt",
  "fields": {
    "company": "ABC Store",
    "address": "12 Main Street",
    "date": "2023-04-21",
    "total": "12.40"
  }
}
```

## Notes

- JSON config works out of the box.
- YAML config works if `PyYAML` is installed.
- Hugging Face generation requires `transformers` and `torch`.
- If `torch.cuda` is unavailable, GPU memory metrics are reported as empty.
