# Small Language Models: Use Cases & Deployment Criteria

Benchmark suite comparing SLMs and LLMs across real-world tasks with a unified execution contract and an SDDF post-processing layer for deployment analysis.

## Project Structure

```
.
├── docs/                           # Documentation
│   ├── HOW_TO_RUN.md              # Execution guide
│   ├── NEXT_INFERENCE_IMPROVEMENTS.md
│   ├── PUBLICATION_READY_CONTRACT.md
│   └── [other docs]
├── src/                            # Core implementation
│   ├── benchmark_inference_pipeline.py    # Main inference engine
│   ├── task_specific_parser.py           # Output validation
│   ├── prepare_benchmark_data.py         # Dataset prep
│   ├── generate_reports.py               # Report generation
│   ├── cleanup_empty_outputs.py          # Data cleaning
│   └── revalidate_outputs.py             # Re-validation
├── scripts/                        # Entry points
│   └── run_benchmark_all_8_tasks.py      # Main runner (8 tasks)
├── tests/                          # Test suite
│   └── test_benchmark_inference_contract.py
├── benchmark_output/               # Results (generated)
│   ├── [8 task directories with outputs.jsonl, sddf_ready.csv, reports]
├── benchmarking/                   # Standardization module
├── archive/                        # Old/obsolete files
└── [task folders]                  # Legacy task implementations
```

## What This Repo Does

This repository implements a publication-ready benchmark pipeline:

- **Inference Engine**: Stratified sampling (5 difficulty bins × 15 samples = 75 per task)
- **Standardized Outputs**: 14-field per-sample metadata, run manifests, hardware capture
- **Task-Specific Parsing**: Custom validators for code, classification, math, text, etc.
- **SDDF Integration**: Difficulty-driven framework for capability curves & routing
- **Complete Audit Trail**: Reproducibility guarantees with checkpoint support

## Benchmarked Tasks (8 Total)

| Task | Model | Status | Pass Rate |
| --- | --- | --- | --- |
| text_generation | qwen2.5:1.5b | ✅ | 100% |
| code_generation | qwen2.5:1.5b | ✅ | 65.3% |
| classification | phi3:mini | ✅ | 98.7% |
| maths | qwen2.5:1.5b | ✅ | 100% |
| summarization | qwen2.5:1.5b | ✅ | 92.0% |
| retrieval_grounded | qwen2.5:1.5b | ✅ | 97.3% |
| instruction_following | qwen2.5:1.5b | ✅ | 89.3% |
| information_extraction | phi3:mini | ✅ | 100% |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all 8 tasks (75 samples each, CPU inference with Ollama)
python scripts/run_benchmark_all_8_tasks.py

# Generate Part A & Part B reports
python src/generate_reports.py
```

## Publication-Ready Outputs

Each task in `benchmark_output/[task]/[model]/` contains:

- **outputs.jsonl**: All 75 inference records (14 fields, immutable audit trail)
- **sddf_ready.csv**: SDDF metrics per difficulty bin
- **run_manifest.json**: Complete audit trail (timestamps, config, hardware)
- **dataset_manifest.json**: Sample selection metadata
- **part_a_report.md**: Methodology (task, sampling, prompts, validation)
- **part_b_report.md**: Results & analysis (performance, latency, findings)

**Example**: `benchmark_output/text_generation/qwen2.5_1.5b/`
- 75 samples (15 per difficulty bin 0-4)
- 100% pass rate
- All validation checks passing
- Complete reproducibility guarantees

## 10 Publication Requirements (ALL SATISFIED)

✅ Stratified sampling by difficulty (5 bins × 15 samples = 75 per task)
✅ Balanced per-bin coverage (15 samples guaranteed per bin)
✅ Per-sample metadata (14 fields: task, bin, sample_id, model, latency, output, etc.)
✅ Hardware capture (CPU, RAM, Python, Ollama versions)
✅ Task-specific validation (code syntax, math answers, text summaries, etc.)
✅ Failure taxonomy (10 structured categories)
✅ Complete audit trail (append-only JSONL, timestamps, reproducibility)
✅ Checkpoint support (resumption from interruption, coverage tracking)
✅ SDDF integration (difficulty curves, tipping points, routing analysis)
✅ Publication reports (Part A methodology + Part B results for each task)

## Running the Benchmark

### Full 8-Task Run (Overnight)
```bash
python scripts/run_benchmark_all_8_tasks.py
# ~2-3 hours on CPU, generates benchmark_output/
```

### Generate Reports After Run
```bash
python src/generate_reports.py
# Creates part_a_report.md and part_b_report.md for each task
```

### Data Cleaning & Re-validation
```bash
# Remove empty outputs from failed inferences
python src/cleanup_empty_outputs.py

# Re-validate all outputs (without re-running inference)
python src/revalidate_outputs.py

# Parse outputs with task-specific validators
python src/task_specific_parser.py
```

## Directory Reference

| Path | Purpose |
| --- | --- |
| `docs/` | Detailed documentation & guides |
| `src/` | Core implementation (inference, parsing, reports) |
| `scripts/` | Entry points and runners |
| `tests/` | Test suite (32 tests, all passing) |
| `benchmark_output/` | Generated results (8 task dirs) |
| `archive/` | Old/obsolete implementations |

## Paper & SDDF

Paper authoring files in `paper/`:
- SDDF combined framework documentation
- Report generation and PDF export tooling
- Final SDDF report: `SDDF_Final_Report.pdf`

## Documentation

See `docs/` folder for:
- **HOW_TO_RUN.md** - Execution guide and timing estimates
- **PUBLICATION_READY_CONTRACT.md** - Full 10-requirement specification
- **NEXT_INFERENCE_IMPROVEMENTS.md** - Planned prompt improvements
- **QUICK_START.md** - Get started in 5 minutes
