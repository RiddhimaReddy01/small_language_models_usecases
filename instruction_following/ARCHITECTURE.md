# Architecture

## Flow

1. `pipeline.py` parses CLI arguments.
2. `pipeline_core.py` loads prompts from `google/IFEval` or falls back to a local synthetic sample.
3. Each configured model is evaluated:
   - local Hugging Face models go through Transformers inference
   - Gemini goes through `gemini_wrapper.py`
4. `constraint_validators.py` scores each response.
5. Aggregate metrics are written to JSON and printed as tables.

## Main Modules

- `pipeline.py`: user-facing CLI
- `pipeline_core.py`: shared orchestration and metrics aggregation
- `constraint_validators.py`: validation logic
- `gemini_wrapper.py`: API client, safe text extraction, retry/deprecation behavior

## Why This Layout

- One implementation path reduces drift between "fast", "full", and "with baseline" runs.
- Wrapper scripts keep old commands working for convenience.
- Config is CLI-driven, so someone on a stronger laptop can change prompt count, device, output path, or model list without editing code.

## Typical Commands

```bash
python pipeline.py --preset fast
python pipeline.py --preset full --device cuda
python pipeline.py --preset fast --include-gemini
```
