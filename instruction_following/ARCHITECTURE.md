# Architecture

## Repository Layout

- `src/instruction_following/` contains reusable benchmark code
- `scripts/` contains runnable wrappers for common experiment modes
- `tests/` contains lightweight validation utilities
- `data/` is reserved for local datasets or checked-in samples
- `results/` stores generated benchmark outputs

## Flow

1. `src/instruction_following/cli.py` parses CLI arguments.
2. `src/instruction_following/pipeline_core.py` loads prompts from `google/IFEval` or falls back to a local synthetic sample.
3. Each configured model is evaluated:
   - local Hugging Face models go through Transformers inference
   - Gemini goes through `src/instruction_following/gemini_wrapper.py`
4. `src/instruction_following/constraint_validators.py` scores each response.
5. Aggregate metrics are written to `results/` and printed as tables.

## Main Modules

- `src/instruction_following/cli.py`: user-facing CLI
- `src/instruction_following/pipeline_core.py`: shared orchestration and metrics aggregation
- `src/instruction_following/constraint_validators.py`: validation logic
- `src/instruction_following/gemini_wrapper.py`: API client, safe text extraction, retry/deprecation behavior

## Why This Layout

- One implementation path reduces drift between "fast", "full", and "with baseline" runs.
- Wrapper scripts in `scripts/` keep common commands obvious for contributors.
- Config is CLI-driven, so someone on a stronger laptop can change prompt count, device, output path, or model list without editing code.
- Separating `data/` and `results/` keeps source code distinct from artifacts.

## Typical Commands

```bash
python scripts/run_fast.py
python scripts/evaluate.py --device cuda
python scripts/run_with_gemini.py
```
