# Instruction Following Evaluation Pipeline

This repo evaluates local language models and an optional Gemini baseline on instruction-following prompts from `google/IFEval`.

## Repository Layout

- `src/instruction_following/`: core package
- `scripts/`: runnable entrypoints and analysis helpers
- `tests/`: parser validation script
- `data/`: local dataset placeholder and future checked-in samples
- `results/`: generated evaluation artifacts

Core package modules:
- `src/instruction_following/cli.py`: main CLI entrypoint
- `src/instruction_following/pipeline_core.py`: dataset loading, inference, metrics, and result export
- `src/instruction_following/constraint_validators.py`: constraint checks
- `src/instruction_following/gemini_wrapper.py`: Gemini API wrapper with deprecation on quota/auth errors

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
python scripts/run_fast.py
```

Full local run:

```bash
python scripts/evaluate.py --device cuda
```

Local models plus Gemini baseline:

```bash
python scripts/run_with_gemini.py
```

Gemini-only baseline:

```bash
python scripts/evaluate_gemini_only.py
```

## Common Options

```bash
python pipeline.py --help
```

Useful examples:

```bash
python pipeline.py --preset fast --num-prompts 10
python pipeline.py --preset full --models Qwen/Qwen2.5-Coder-1.5B --device cuda
python pipeline.py --preset fast --include-gemini --output results/custom_run.json
```

## Outputs

The pipeline writes JSON results to:
- `results/results_detailed.json` for local-only runs by default
- `results/results_with_baseline.json` when Gemini is included by default

Console output includes:
- one combined capability + reliability table
- one operational metrics table

## Notes For Other Contributors

- No API keys are hardcoded in the repo.
- The dataset loader falls back to a tiny deterministic dataset if `google/IFEval` cannot be loaded.
- If Gemini hits quota or auth issues, the model is deprecated for the rest of the run instead of crashing the pipeline.
- On stronger hardware, pass `--device cuda` to use a GPU-backed setup if your local environment supports it.
- If you decide to vendor benchmark samples locally later, put them under `data/`.
