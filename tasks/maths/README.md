# Math Benchmark

This repo benchmarks math reasoning models with a cleaner workflow for three stages:

1. `data ingestion`
2. `modeling / evaluation`
3. `results / reporting`

The goal is that someone new can add benchmark data, run the pipeline, and find outputs without needing to read the whole codebase first.

## Structured repo layout

```text
configs/                 benchmark configs
data/
  raw/                   raw source datasets
  processed/             normalized benchmark-ready datasets
  samples/               small hand-checkable examples
src/                     core pipeline modules
cli/                     runnable benchmark commands
outputs/
  predictions/           saved experiment outputs
  metrics/               generated summaries and benchmark tables
  logs/                  runtime logs
scripts/                 environment helpers and legacy scripts
tests/                   test suite placeholder
eval_pipeline/           existing implementation kept for compatibility
math_benchmark/          internal wrappers for the new structure
```

## Quick start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Add normalized datasets in `data/processed/` or keep the current top-level JSONL files in `data/`:

```text
data/processed/gsm8k.jsonl
data/processed/svamp.jsonl
data/processed/math_subset.jsonl
```

Each record must look like:

```json
{"question": "Problem text", "answer": "42", "difficulty": "easy"}
```

`difficulty` must be one of `easy`, `medium`, or `hard`.

3. If you only have raw source files, place them here:

```text
data/raw/gsm8k
data/raw/svamp
data/raw/math
```

Then normalize them with:

```bash
python cli/prepare_datasets.py
```

4. Run a dry run first:

```bash
python cli/run_experiment.py --dry-run
```

This writes a structured result file to `outputs/predictions/results_benchmark.json`.

5. Run the full benchmark:

```bash
python cli/run_experiment.py
```

6. Regenerate reports from any saved result files in `results/raw/`:

```bash
python cli/generate_reports.py
```

Reports are written to `outputs/metrics/`.

## Where to put new data

For someone adding a new dataset, the easiest path is:

1. Put normalized JSONL into `data/processed/`.
2. Add or update the dataset entry in [configs/config.yaml](/c:/Users/riddh/OneDrive/Desktop/SLM%20use%20cases/maths/configs/config.yaml).
3. Run `python cli/run_experiment.py --dry-run` to validate the structure.
4. Run `python cli/generate_reports.py` after a successful benchmark.

## Main entry points

- `python cli/prepare_datasets.py`
- `python cli/run_experiment.py`
- `python cli/generate_reports.py`
- `python scripts/run_gemini_real_eval.py`

The root scripts remain as simple wrappers so existing commands keep working.

## Benchmark behavior

- Real datasets are required in all modes.
- `--dry-run` simulates model responses but still reads real dataset files.
- Benchmark outputs are stored in `outputs/predictions/`.
- Reports are generated from supported `results*.json` files in `outputs/predictions/`.
- If a real Gemini results file is present, reporting prefers it over older dry-run Gemini results.

## Environment variables for live runs

- `GEMINI_API_URL`
- `GEMINI_API_KEY`
- `LOCAL_SLM_ENDPOINT_PHI3`
- `LOCAL_SLM_ENDPOINT_GEMMA2B`
- `LOCAL_SLM_ENDPOINT_MISTRAL7B`

## Local SLM setup

The simplest local setup is Ollama:

```bash
ollama pull phi3:mini
ollama pull gemma2:2b
ollama pull mistral:7b
```

Then persist local endpoint variables:

```powershell
./scripts/set_local_endpoints.ps1
```

## Notes for maintainers

- `src/` and `cli/` now match the intended public repo structure.
- `eval_pipeline/` and `math_benchmark/` are still present to avoid breaking current imports while the repo transitions.
