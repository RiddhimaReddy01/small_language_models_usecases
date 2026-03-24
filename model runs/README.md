# Model Runs

This folder holds the canonical model-run specification for all task evaluations in this repo.

Canonical ladder:
- `SLM-0`: 0.5B tiny model
- `SLM-1`: Qwen 2B-class model
- `SLM-2`: Phi 3B-class model
- `BASELINE`: Groq-hosted LLM

Contents:
- `CANONICAL_MODEL_LADDER.md` - standard model ladder and routing role
- `CANONICAL_EVAL_SCHEMA.md` - required metrics, prompts, hardware, and reporting fields
- `task_run_template.json` - machine-readable run template for each task/model evaluation

Every task run should capture:
- capability metrics
- operational metrics
- semantic risk metrics
- model settings
- prompt settings
- hardware/runtime settings
- SDDF outputs
- routing decision inputs and outputs
