# Code Generation Evaluation Harness

This repository benchmarks natural-language-to-Python code generation with a time-bounded evaluation pipeline built around `HumanEval` and `MBPP`.

## What The Pipeline Produces

Each raw run writes:

- `task_results.jsonl`: task-level prompts, raw generations, extracted code, execution status, and metrics
- `summary.json`: aggregated model metrics
- `report.md`: markdown report with capability and operational tables
- `config_snapshot.json`: exact run settings used for that run

The repo also supports curated benchmark exports under `benchmarks/`:

- `benchmarks/tables/capability_metrics.md`
- `benchmarks/tables/operational_metrics.md`
- `benchmarks/tables/latest_summary.json`
- `benchmarks/manifests/latest_benchmark.json`

## Repository Layout

```text
src/codegen_eval/         Core evaluation package
configs/examples/         Starter configs for supported backends
configs/experiments/      Curated reproducible benchmark presets
benchmarks/               Curated benchmark tables and manifests
docs/                     Design and setup documentation
scripts/                  Helper scripts such as Windows llama.cpp setup
runs/                     Latest raw run artifacts
archive/                  Archived configs, runs, and debug artifacts
tests/                    Lightweight regression tests
```

## Supported Backends

- local Hugging Face models via `transformers`
- `llama.cpp` via `llama-cpp-python`
- Hugging Face Inference API
- Ollama
- Gemini via `google-genai` or `google-generativeai`

## Install

Core package:

```bash
pip install -e .
```

Local inference:

```bash
pip install -e .[local]
```

Hugging Face Inference API:

```bash
pip install -e .[hf_api]
```

Gemini:

```bash
pip install -e .[gemini]
```

Everything except optional backend combinations can be installed together, for example:

```bash
pip install -e .[local,hf_api,gemini]
```

## Start From A Config

Use one of the example configs in `configs/examples/`:

- `configs/examples/sample_config.json`
- `configs/examples/quick_run_config.json`
- `configs/examples/hf_api_quick_run_config.json`
- `configs/examples/ollama_quick_run_config.json`

Curated benchmark presets live in `configs/experiments/`.

Notable benchmark presets:

- `configs/experiments/transformers_codegen_top3_under15.json`
- `configs/experiments/gemini_codegen_baseline_under15.json`

## Run An Evaluation

Backward-compatible command:

```bash
python -m codegen_eval --config configs/examples/sample_config.json --output-dir runs
```

Explicit run command:

```bash
python -m codegen_eval run --config configs/examples/sample_config.json --output-dir runs
```

Installed console script:

```bash
codegen-eval --config configs/examples/sample_config.json --output-dir runs
```

## Export Curated Benchmark Tables

Export the latest raw run into the tracked `benchmarks/` area:

```bash
python -m codegen_eval export-tables --run-dir runs/run_YYYYMMDD_HHMMSS --output-dir benchmarks --source-config configs/experiments/transformers_codegen_top3_under15.json
```

Merge multiple runs, and optionally deprecate runs that hit rate limits:

```bash
python -m codegen_eval export-combined-tables --run-dir runs/run_local --run-dir runs/run_gemini --source-config configs/experiments/transformers_codegen_top3_under15.json --source-config configs/experiments/gemini_codegen_baseline_under15.json --output-dir benchmarks --deprecate-on-rate-limit
```

## Environment Variables

For Gemini:

```bash
set GEMINI_API_KEY=your_key_here
```

For the Hugging Face Inference API:

```bash
set HF_TOKEN=your_token_here
```

## Notes

- All models in a run share the same sampled task pool.
- The wall-clock budget is enforced per model after adapter construction.
- Safety screening blocks obvious shell, network, and destructive file operations before execution.
- Execution runs in a lightweight subprocess sandbox, not a hardened security boundary.
- `Self-Consistency Score` and `Deterministic Reproducibility` are only populated when extra generations or reruns are enabled.
- `benchmarks/` is the curated publishable layer; `runs/` is the raw local artifact layer.

## Key Files

- `src/codegen_eval/dataset_loader.py`: loads and samples `HumanEval` and `MBPP`
- `src/codegen_eval/models.py`: backend adapters
- `src/codegen_eval/prompts.py`: prompt construction and code extraction
- `src/codegen_eval/metrics.py`: capability and operational metric aggregation
- `src/codegen_eval/reporting.py`: per-run reports and benchmark exports
- `src/codegen_eval/runner.py`: CLI entrypoint and orchestration
- `docs/evaluation_design.md`: evaluation methodology
- `docs/llamacpp_windows_setup.md`: Windows setup notes for `llama.cpp`
