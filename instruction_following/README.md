# Instruction Following Evaluation Pipeline

This repo evaluates local language models and an optional Gemini baseline on instruction-following prompts from `google/IFEval`.

The project is now organized around a single shared pipeline so a fresh clone is easier to run:
- `pipeline.py`: main CLI entrypoint
- `pipeline_core.py`: dataset loading, inference, metrics, and result export
- `constraint_validators.py`: constraint checks
- `gemini_wrapper.py`: Gemini API wrapper with deprecation on quota/auth errors
- `run_fast.py`, `evaluate.py`, `run_with_gemini.py`: compatibility wrappers

## Setup

```bash
pip install -r requirements.txt
```

Optional Gemini setup:

```bash
cp .env.example .env
# then set GEMINI_API_KEY in your shell or env manager
```

PowerShell example:

```powershell
$env:GEMINI_API_KEY="your-key"
$env:GEMINI_MODEL="gemini-2.5-flash"
```

## Quick Start

Fast local run:

```bash
python pipeline.py --preset fast
```

Full local run:

```bash
python pipeline.py --preset full --device cuda
```

Local models plus Gemini baseline:

```bash
python pipeline.py --preset fast --include-gemini
```

Gemini-only baseline:

```bash
python evaluate_gemini_only.py
```

## Common Options

```bash
python pipeline.py --help
```

Useful examples:

```bash
python pipeline.py --preset fast --num-prompts 10
python pipeline.py --preset full --models Qwen/Qwen2.5-Coder-1.5B --device cuda
python pipeline.py --preset fast --include-gemini --output results_with_baseline.json
```

## Outputs

The pipeline writes JSON results to:
- `results_detailed.json` for local-only runs by default
- `results_with_baseline.json` when Gemini is included by default

Console output includes:
- one combined capability + reliability table
- one operational metrics table

## Notes For Other Contributors

- No API keys are hardcoded in the repo.
- The dataset loader falls back to a tiny deterministic dataset if `google/IFEval` cannot be loaded.
- If Gemini hits quota or auth issues, the model is deprecated for the rest of the run instead of crashing the pipeline.
- On stronger hardware, pass `--device cuda` to use a GPU-backed setup if your local environment supports it.
