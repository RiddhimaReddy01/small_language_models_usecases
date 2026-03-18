# Codebase Organization

## Structure Overview

```
SLM use cases/
├── README.md                    # Main project readme
├── requirements.txt             # Python dependencies
├── CODEBASE_ORGANIZATION.md    # This file
│
├── src/                         # Core implementation (production code)
│   ├── __init__.py
│   ├── benchmark_inference_pipeline.py    # Main inference engine (950 LOC)
│   ├── task_specific_parser.py            # Output validation parsers (530 LOC)
│   ├── prepare_benchmark_data.py          # Dataset preparation
│   ├── generate_reports.py                # Part A & Part B report generation (580 LOC)
│   ├── cleanup_empty_outputs.py           # Data cleaning utilities (150 LOC)
│   └── revalidate_outputs.py              # Re-validation without re-inference (180 LOC)
│
├── scripts/                     # Entry points and runners
│   ├── __init__.py
│   └── run_benchmark_all_8_tasks.py       # Main benchmark runner (261 LOC)
│
├── tests/                       # Test suite
│   ├── test_benchmark_inference_contract.py      # 32 passing tests
│   ├── test_benchmark_pipeline_contract.py
│   ├── test_benchmark_governance_contract.py
│   ├── test_benchmark_structure.py
│   ├── test_execution.py
│   ├── test_sddf_core.py
│   └── test_sddf_ingest_pipeline.py
│
├── docs/                        # Documentation
│   ├── HOW_TO_RUN.md                       # Execution guide
│   ├── QUICK_START.md                      # 5-minute quickstart
│   ├── PUBLICATION_READY_CONTRACT.md       # 10-requirement spec
│   ├── NEXT_INFERENCE_IMPROVEMENTS.md      # Planned improvements
│   ├── TIMING_ESTIMATE_75_EXAMPLES.md      # Runtime estimates
│   ├── BACKEND_MATRIX.md
│   ├── BATCH_PIPELINE_SETUP.md
│   ├── BENCHMARK_GOVERNANCE.md
│   ├── CANONICAL_PIPELINE.md
│   └── COMPREHENSIVE_FREE_STRATEGY.md
│
├── benchmark_output/            # Generated results (DO NOT EDIT)
│   ├── classification/          # Task results
│   │   └── phi3_mini/
│   │       ├── outputs.jsonl           # All 75 inference records
│   │       ├── sddf_ready.csv          # SDDF metrics
│   │       ├── run_manifest.json       # Audit trail
│   │       ├── dataset_manifest.json
│   │       ├── part_a_report.md        # Methodology
│   │       └── part_b_report.md        # Results & analysis
│   ├── code_generation/
│   ├── information_extraction/
│   ├── instruction_following/
│   ├── maths/
│   ├── retrieval_grounded/
│   ├── summarization/
│   └── text_generation/
│
├── benchmarking/                # SDDF framework (standardization layer)
│   ├── __init__.py
│   ├── interface.py
│   └── standardize.py
│
├── archive/                     # Old/obsolete implementations
│   ├── audit_benchmark_governance.py
│   ├── audit_report_readiness.py
│   ├── batch_inference_pipeline.py     # Old version (replaced by benchmark_inference_pipeline.py)
│   ├── export_reports_html.py          # Old
│   ├── generate_benchmark_report.py    # Old (replaced by generate_reports.py)
│   ├── generate_part_b_report.py       # Old (replaced by generate_reports.py)
│   ├── routing_policy.py               # Old
│   ├── run_batch_pipeline.sh           # Old
│   ├── run_benchmark.py                # Old
│   ├── run_benchmark_example.py        # Old
│   ├── run_benchmark_inference.py      # Old
│   └── *.json                          # Old registry/governance files
│
└── [Legacy task folders]        # Old task-specific implementations
    ├── classification/
    ├── code_generation/
    ├── information_extraction/
    ├── instruction_following/
    ├── maths/
    ├── retrieval_grounded/
    ├── summarization/
    ├── text_generation/
    ├── Information Extraction/          # Note: Capitalized variant
    ├── Retrieval_grounded/              # Note: Different casing
    └── Summarization/                   # Note: Capitalized variant
```

## File Purposes

### Core Implementation (`src/`)

**benchmark_inference_pipeline.py** (950 LOC)
- Main inference engine with publication-ready infrastructure
- QueryRecord: 14-field dataclass for per-sample metadata
- RunManifest: Immutable audit trail with completion tracking
- HardwareInfo: CPU/RAM/OS/versions captured at runtime
- PromptConfig: Template versions, temperature, top_p, max_tokens
- DatasetManifest: Sample selection metadata
- BenchmarkInferenceEngine: run_batch() with checkpoints
- FAILURE_TAXONOMY: 10 structured failure categories
- generate_sddf_ready_output(): Converts outputs.jsonl to SDDF CSV

**task_specific_parser.py** (530 LOC)
- Custom validators for each task type
- CodeGenerationParser: Syntax validation with ast.parse
- ClassificationParser: Class label extraction
- MathsParser: Numerical answer extraction
- SummarizationParser: Word count & coherence checks
- RetrievalGroundedParser: Quote extraction & validation
- InstructionFollowingParser: List/sequence/alphabetical validation
- InformationExtractionParser: Named entity extraction
- TextGenerationParser: Word count & coherence validation
- PARSERS registry and parse_task_output() function

**generate_reports.py** (580 LOC)
- Part A: Methodology reports (task, sampling, prompts, validation)
- Part B: Results & analysis (performance, latency, findings)
- load_task_data(): Loads outputs.jsonl, sddf_ready.csv, manifests
- generate_part_a(): Creates comprehensive methodology docs
- generate_part_b(): Creates results & analysis reports

**prepare_benchmark_data.py**
- Dataset preparation with stratified sampling
- Creates 75 samples per task (15 per difficulty bin)
- Generates rebin_results.csv for each task

**cleanup_empty_outputs.py** (150 LOC)
- Removes empty outputs from failed inferences
- Balances data to 75 per task (15 per bin)
- Regenerates SDDF CSVs

**revalidate_outputs.py** (180 LOC)
- Re-validates existing outputs without re-running inference
- Fixed validation thresholds (changed from 800 to 1000 chars)
- Regenerates SDDF metrics and validation checks

### Entry Points (`scripts/`)

**run_benchmark_all_8_tasks.py** (261 LOC)
- Main runner for all 8 tasks
- Sequential execution on CPU with Ollama
- Generates benchmark_output/ with all artifacts
- Resumable from checkpoints

### Tests (`tests/`)

**test_benchmark_inference_contract.py** (32 passing tests)
- Validates all 10 publication requirements
- Per-requirement test suites
- All tests passing ✅

### Documentation (`docs/`)

- HOW_TO_RUN.md: Step-by-step execution guide
- PUBLICATION_READY_CONTRACT.md: Full 10-requirement specification
- NEXT_INFERENCE_IMPROVEMENTS.md: Planned prompt improvements
- QUICK_START.md: Get started in 5 minutes
- Other: Architecture, governance, strategy docs

## Migration Notes

### Files Moved to `src/`
- benchmark_inference_pipeline.py
- task_specific_parser.py
- prepare_benchmark_data.py
- generate_reports.py
- cleanup_empty_outputs.py
- revalidate_outputs.py

### Files Moved to `scripts/`
- run_benchmark_all_8_tasks.py

### Files Moved to `docs/`
- All .md documentation files

### Files Moved to `archive/`
- Old benchmark implementations (batch_inference_pipeline.py)
- Old report generators (generate_benchmark_report.py, generate_part_b_report.py)
- Old runners (run_benchmark.py, run_benchmark_example.py, etc.)
- Old utilities (audit_*, export_*, routing_policy.py)
- Old registry/governance JSON files

### Import Updates

**scripts/run_benchmark_all_8_tasks.py**
```python
# Added to imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

**tests/test_benchmark_inference_contract.py**
```python
# Updated path reference
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

## How to Run

```bash
# From project root

# Run all 8 tasks
python scripts/run_benchmark_all_8_tasks.py

# Generate reports (after run completes)
python src/generate_reports.py

# Re-validate outputs (optional)
python src/revalidate_outputs.py

# Clean up and rebuild metrics (optional)
python src/cleanup_empty_outputs.py
python src/task_specific_parser.py
```

## Directory Rationale

| Folder | Purpose |
| --- | --- |
| `src/` | Production code that can be imported and tested |
| `scripts/` | Executable entry points (can import from src) |
| `tests/` | Test suite validating requirements |
| `docs/` | Documentation, guides, specifications |
| `benchmark_output/` | Generated results (immutable, don't edit) |
| `archive/` | Old implementations (for reference/history) |
| Root | Configuration, git, main README |

## Key Principles

1. **src/** = importable modules (no main entry points)
2. **scripts/** = executable entry points with main()
3. **tests/** = validation of requirements
4. **docs/** = all documentation
5. **archive/** = old code for reference
6. **benchmark_output/** = generated results (never edit manually)

## Unused Legacy Folders

These contain old task-specific implementations and can be ignored:
- `classification/`
- `code_generation/`
- `instruction_following/`
- `maths/`
- `information_extraction/`
- `retrieval_grounded/`
- `Summarization/` / `summarization/`
- `text_generation/`
- `Information Extraction/`
- `Retrieval_grounded/`

The new benchmark pipeline in `src/benchmark_inference_pipeline.py` supersedes all task-specific implementations.
