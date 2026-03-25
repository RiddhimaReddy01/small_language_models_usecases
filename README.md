# SLM Use Cases

This repository implements the Sample Difficulty Distribution Framework (SDDF) for benchmarking small language models, comparing them with a stronger baseline, and converting those results into routing decisions.

The repository already includes tracked benchmark artifacts under `model_runs/benchmark_75/`, so there are two normal ways to use it:

1. Reproduce the analysis from existing benchmark outputs.
2. Re-run a task benchmark, then refresh the SDDF-derived artifacts.

## Reproducibility First

Use the same execution order every time:

1. Create a clean environment.
2. Install root dependencies.
3. Run the regression tests.
4. Reuse tracked benchmark artifacts unless you intentionally want fresh model runs.
5. Regenerate derived reports, dashboards, and learned weights from those artifacts.

That sequence keeps the workflow predictable and makes the project much easier to hand off to another engineer.

## Environment Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
npm install
```

Notes:

- `requirements.txt` installs the shared SDDF and test dependencies.
- `npm install` is only needed for the Node-based report generation path.
- Some task folders have their own task-specific dependencies. Install those only when re-running that task.

## Stable Repository Contract

Treat these directories as the project contract:

- `docs/`: pipeline theory and repository layout.
- `data/01_processed/`: processed benchmark outputs.
- `data/02_sampling/`: sampling manifests and bin-level sampling artifacts.
- `data/03_complexity/`: difficulty annotations, learned weights, and complexity metadata.
- `model_runs/benchmark_75/`: tracked benchmark outputs and SDDF-ready artifacts by task and model.
- `sddf/`: reusable SDDF scoring, gating, risk, routing, and reporting utilities.
- `src/routing/`: routing framework and production policy logic.
- `tasks/`: task-specific benchmark runners.
- `tools/`: helper scripts for retraining weights and generating business summaries.

## Fast Validation

Run the root regression suite before changing pipeline logic:

```powershell
python -m pytest tests
```

This covers the SDDF core, ingest flow, reporting, benchmark contracts, and routing integration tests.

## Reproduce From Existing Benchmark Artifacts

If you want reproducible analysis from the tracked benchmark set, start with `model_runs/benchmark_75/`.

Inspect the currently available tasks and models:

```powershell
python .\load_benchmark_data.py
```

Example:

```python
from load_benchmark_data import load_benchmark_outputs

outputs = load_benchmark_outputs("classification", "phi3_mini")
print(len(outputs))
```

## Re-run Task Benchmarks

Re-run benchmarks inside the relevant task folder because each task has its own CLI, config format, and dependency profile.

Useful task entrypoints:

- `tasks/classification/README.md`
- `tasks/Summarization/README.md`
- `tasks/Retrieval_grounded/README.md`
- `tasks/code_generation/README.md`
- `tasks/instruction_following/README.md`
- `tasks/maths/README.md`
- `tasks/Information Extraction/README.md`
- `tasks/text_generation/README.md`

Recommended operating pattern:

1. Install that task's dependencies.
2. Run its smoke or tiny config first.
3. Run the full benchmark only after the smoke path succeeds.
4. Verify that the run emitted a manifest, outputs, and summary artifacts.
5. Move or consolidate the outputs into the tracked benchmark layout if the run should feed SDDF analysis.

## Ollama Model Preparation

For local SLM runs, pull the expected Ollama models first:

```bash
bash pull_ollama_models.sh
```

Or manually:

```bash
ollama pull phi3:mini
ollama pull qwen2.5:1.5b
ollama pull tinyllama:1.1b
```

## Regenerate Derived Analysis

Once benchmark artifacts exist, regenerate downstream summaries from the repository root.

Generate the business analytics dashboard:

```powershell
python .\tools\generate_business_dashboard.py
```

This writes outputs under `model_runs/benchmark_75/business_analytics/`.

Refresh learned difficulty weights from prepared bin-level JSON inputs:

```powershell
python .\tools\train_difficulty_weights.py --features <features.json> --cap_curve <capability.json> --risk_curve <risk.json> --output <difficulty_weights.json>
```

## Expected Artifact Contract

Each model directory under `model_runs/benchmark_75/<task>/<model>/` should contain, at minimum:

- `run_manifest.json`
- `sddf_ready.csv`
- `metadata/`

Many runs will also include:

- `outputs.jsonl`
- task reports such as `part_a_report.md` and `part_b_report.md`
- additional diagnostics

Each task-level SDDF directory under `model_runs/benchmark_75/<task>/sddf/` should contain routing and curve artifacts such as:

- `routing_policy.json`
- `thresholds.json`
- capability and risk curve images
- decision matrix visualizations

## Recommended Re-run Sequence

When adding a new model run, use this order:

1. Run the task benchmark and produce raw outputs.
2. Verify that the run manifest and metadata are complete.
3. Convert the run into SDDF-ready artifacts such as `sddf_ready.csv`.
4. Refresh task-level SDDF thresholds and routing outputs.
5. Regenerate cross-task dashboards or business summaries.
6. Re-run `python -m pytest tests` before publishing results.

## Canonical References

- `docs/SDDF_PIPELINE.md`: SDDF equations, learned threshold logic, and routing rationale.
- `docs/README_STRUCTURE.md`: repository storage layout and stage boundaries.
- `model_runs/BENCHMARK_README.md`: benchmark dataset inventory and model/task coverage.

Use this README as the execution guide and the docs files as the design reference.
