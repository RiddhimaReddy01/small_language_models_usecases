# Backend Matrix

This document lists the supported inference backends for each benchmark and the
typical invocation pattern for local, Hugging Face hosted, and Gemini-backed
runs.

## Classification

- Local:
  `python -c "import sys; sys.argv=['runner','--model','phi3:mini']; from classification.classification_eval.runner import run; run()"`
- Hugging Face hosted:
  `python -c "import sys; sys.argv=['runner','--model','hf_api:meta-llama/Llama-3.2-1B-Instruct']; from classification.classification_eval.runner import run; run()"`
- Gemini:
  `python -c "import sys; sys.argv=['runner','--model','gemini-3.1-flash-lite-preview']; from classification.classification_eval.runner import run; run()"`

Notes:
- Default local path assumes Ollama-compatible local serving.
- Use `--output-dir <dir>` to isolate a dedicated run folder.

## Instruction Following

- Local:
  `python -m instruction_following.cli --models Qwen/Qwen2.5-Coder-0.5B --num-prompts 8`
- Hugging Face hosted:
  `python -m instruction_following.cli --models hf_api:meta-llama/Llama-3.2-1B-Instruct --num-prompts 8`
- Gemini:
  `python -m instruction_following.cli --models gemini-2.5-flash --num-prompts 8 --include-gemini`

Notes:
- Hosted Hugging Face models must be prefixed with `hf_api:`.
- Set `PYTHONPATH=instruction_following/src` when running from repo root if needed.

## Retrieval-Grounded QA

- Local:
  `python Retrieval_grounded/cli/run_experiment.py --config Retrieval_grounded/configs/config.smoke.yaml`
- Hugging Face hosted:
  `python Retrieval_grounded/cli/run_experiment.py --config Retrieval_grounded/configs/config.hf_llama1b.smoke.yaml`
- Gemini:
  `python Retrieval_grounded/cli/run_experiment.py --config Retrieval_grounded/configs/config.hf_llama1b.smoke.yaml --baseline-gemini`

Notes:
- Hosted models use `hf_api:<model_id>` in the config `models` list.
- Set `PYTHONPATH=.` when running from repo root so `sddf` imports resolve.

## Code Generation

- Local:
  `python -m codegen_eval run --config code_generation/configs/examples/quick_run_config.json --output-dir code_generation/runs_local`
- Hugging Face hosted:
  `python -m codegen_eval run --config code_generation/configs/examples/hf_api_quick_run_config.json --output-dir code_generation/runs_hf`
- Gemini:
  `python -m codegen_eval run --config code_generation/configs/examples/hf_api_llama1b_gemini_smoke.json --output-dir code_generation/runs_hf_gemini_smoke`

Notes:
- Run from repo root with `PYTHONPATH=code_generation/src` if the package is not installed.
- The codegen harness supports mixed backends in the same config.

## Maths

- Local:
  `python maths/cli/run_experiment.py --config maths/configs/config.smoke.yaml --output maths/outputs/predictions/results_local.json`
- Hugging Face hosted:
  `python maths/cli/run_experiment.py --config maths/configs/hf_llama1b_gemini_smoke.yaml --output maths/outputs/predictions/results_hf.json`
- Gemini:
  `python maths/cli/run_experiment.py --config maths/configs/hf_llama1b_gemini_smoke.yaml --output maths/outputs/predictions/results_hf_gemini.json`

Notes:
- Set `PYTHONPATH=.;maths` when running from repo root.
- Mixed configs are supported; current paired smoke config includes both HF and Gemini.

## Summarization

- Local:
  `python Summarization/scripts/run_benchmark.py --config Summarization/configs/fast_cpu.json`
- Hugging Face hosted:
  `python Summarization/scripts/run_benchmark.py --config Summarization/configs/hf_llama1b_fast.json`
- Gemini:
  `python Summarization/scripts/run_benchmark.py --config Summarization/configs/gemini_flash_lite_hf_pair.json`

Notes:
- Set `PYTHONPATH=.;Summarization/src` when running from repo root.
- Paired SLM+Gemini comparisons currently use separate benchmark executions on the same sample and then a combined SDDF report folder.

## Information Extraction

- Local:
  `python "Information Extraction/run_benchmark.py" run --config "Information Extraction/configs/sroie_cpu_working_models.json"`
- Hugging Face hosted:
  `python "Information Extraction/run_benchmark.py" run --config "Information Extraction/configs/sroie_hf_llama1b_smoke.json"`
- Gemini:
  `python "Information Extraction/run_benchmark.py" run --config "Information Extraction/configs/sroie_gemini_pair_smoke.json"`

Notes:
- Set `PYTHONPATH=.;Information Extraction/src` when running from repo root.
- Paired SLM+Gemini comparisons currently use separate benchmark executions on the same sample and then a combined SDDF report folder.

## Text Generation

- Local GGUF:
  `python run_benchmark.py --model_path path/to/model.gguf --model_type gguf --task_type samples --output_dir results/runs/local_run`
- Hugging Face hosted:
  `python run_benchmark.py --model_path meta-llama/Llama-3.2-1B-Instruct --model_name hf_llama32_1b --model_type huggingface --task_type samples --sample_size 2 --output_dir results/runs/hf_llama32_1b_2shot --api_key %HF_TOKEN%`
- Gemini:
  `python run_benchmark.py --model_path gemini-2.5-flash --model_name gemini-2.5-flash-fresh --model_type google --task_type samples --sample_size 2 --output_dir results/runs/gemini_fresh_2shot --api_key %GEMINI_API_KEY%`

Notes:
- Run from `text_generation/` so the benchmark can find `data/samples.json`.
- Multi-model comparisons currently use separate runs and a combined SDDF report folder.

## Shared Report Generation

- Combined benchmark report:
  `python generate_benchmark_report.py --benchmark <name> --run-path <run_dir_or_result_file>`
- HTML export:
  `python export_reports_html.py`

## Required Environment Variables

- Hugging Face hosted inference:
  `HF_TOKEN` or `HF_API_KEY`
- Gemini:
  `GEMINI_API_KEY`
- Some Gemini maths paths also use:
  `GEMINI_API_URL`
