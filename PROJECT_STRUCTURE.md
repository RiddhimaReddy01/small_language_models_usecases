# Project Structure (Clean & Organized)

**Updated:** 2026-04-20  
**Status:** ✅ Fully organized and reproducible

---

## Root Directory (Clean)

```
project_root/
├── 📖 README.md                           # Original project README
├── 📖 README_CONSOLIDATED.md              # System overview + quick start
├── 📖 REPRODUCIBILITY.md                  # Exact reproduction steps
├── 📖 SDDF_METHODOLOGY_VERIFICATION.md   # Technical verification
├── 📖 PROJECT_STRUCTURE.md                # This file
├── 📖 ROOT_FILES_AUDIT.md                 # Cleanup audit details
│
├── 🎯 run_test_with_frozen_thresholds.py  # MAIN ENTRY POINT
├── 📝 requirements.txt                    # Python dependencies (pip install)
│
├── 🐍 scripts/                            # All utility scripts
├── 📦 sddf/                               # Core framework
├── 📊 model_runs/                         # Results & artifacts
├── 📚 docs/                               # Documentation
├── 🔧 repos/                              # Git submodules
├── 📁 tests/                              # Test suite
├── 🛠️ tools/                              # Tools & utilities
└── 📁 data/                               # Data files
```

---

## Important Directories

### 🎯 Entry Point
```
run_test_with_frozen_thresholds.py
  ↑ Start here for full SDDF pipeline
```

### 🐍 Scripts Organization

```
scripts/
├── analysis/                      # Analysis & sensitivity studies
│   ├── analyze_uc_tier_sensitivity.py
│   └── analyze_uc_tier_sensitivity_v2.py
│
├── compute/                       # Computation scripts
│   ├── compute_continuous_validation_results.py
│   └── compute_uc_routing_decisions.py
│
├── demo/                          # Demonstrations
│   └── demo_frozen_thresholds.py
│
├── tests/                         # Test scripts
│   ├── test_adaptive_validation.py
│   └── test_adaptive_validation_all_models.py
│
├── visualization/                 # Plotting & visualization
│   └── plot_uc_empirical_routing.py
│
├── deployment/                    # Production deployment
│   └── production_deployment.py
│
├── pipelines/                     # End-to-end pipelines
│   ├── end_to_end_runtime_pipeline.py
│   └── run_slm_research_usecases.py
│
├── setup/                         # Setup & initialization
│   └── pull_ollama_models.sh
│
├── automation/                    # Scheduled tasks
│   └── run_overnight.bat
│
├── section5_task_classifier.py    # Section 5 specific
├── section7_runtime_routing.py    # Section 7 specific
└── runtime_routing_section7.py    # Section 7 specific
```

### 📦 Core Framework

```
sddf/
├── config.py                      # 🔑 SINGLE SOURCE OF TRUTH
│   ↑ All parameters, seeds, thresholds documented here
│
├── frozen_thresholds.py           # Frozen τ values (immutable at runtime)
├── runtime_routing.py             # Query routing logic
├── usecase_mapping.py             # UC → task family mapping
├── threshold_sensitivity_analysis.py  # SelectiveNet optimization
│
├── train_paper_aligned_multimodel.py  # Training phase
├── validation_with_frozen.py      # Validation phase
├── test_with_frozen.py            # Test phase
│
└── [... 20+ other modules ...]
```

### 📊 Results & Artifacts

```
model_runs/
├── sddf_training_splits/          # Training data (8 tasks × 3 models)
├── clean_deterministic_splits/    # Validation/test data
├── test_with_frozen_thresholds/   # Main results (JSON + PNG)
│   ├── validation_with_frozen.json
│   ├── test_with_frozen.json
│   ├── usecase_tiers_with_frozen.json
│   ├── threshold_sensitivity.json
│   └── threshold_sensitivity_analysis.png
│
└── archive/                       # Archived results
    ├── adaptive_validation_comprehensive_results.json
    ├── continuous_validation_results.json
    ├── section7_routing_results.json
    ├── task_thresholds.json
    ├── benchmark_governance_registry.json
    └── benchmark_pipeline_registry.json
```

### 📚 Documentation

```
docs/
├── archive/                       # Legacy documentation
│   ├── INDEX.md
│   ├── (28 legacy .md files)
│   ├── BEFORE_AFTER_COMPARISON.txt
│   ├── IMPLEMENTATION_SUMMARY.txt
│   ├── OPERATIONAL_ZONE_SUMMARY.txt
│   └── tmp_final_alignment_extracted.txt
│
└── [... other doc folders ...]
```

### 📁 Logs

```
logs/
└── pipeline_llm_baseline_output.log    # Pipeline logs
```

---

## Quick Reference: What's Where?

| Need | Location | File(s) |
|------|----------|---------|
| **System overview** | Root | README_CONSOLIDATED.md |
| **How to reproduce** | Root | REPRODUCIBILITY.md |
| **All parameters** | sddf/ | config.py |
| **Run full pipeline** | Root | run_test_with_frozen_thresholds.py |
| **Analysis tools** | scripts/analysis/ | *.py |
| **Tests** | scripts/tests/ | *.py |
| **Visualization** | scripts/visualization/ | *.py |
| **Results** | model_runs/ | *.json, *.png |
| **Historical docs** | docs/archive/ | *.md |
| **Logs** | logs/ | *.log |

---

## File Counts

| Type | Count | Location |
|------|-------|----------|
| Root .md files | 5 | Root |
| Root .py files | 1 | Root |
| Root config | 1 | requirements.txt |
| Core framework | 23 | sddf/ |
| Scripts | 15 | scripts/ |
| Results/Artifacts | 10+ | model_runs/ |
| Documentation | 30+ | docs/ |
| Tests | - | tests/ |

**Total organization:** Clean, logical, easy to navigate ✅

---

## How to Use This Structure

### For First-Time Users
```bash
1. Read: README_CONSOLIDATED.md
2. Check: sddf/config.py (all parameters)
3. Run: python run_test_with_frozen_thresholds.py
```

### For Developers
```bash
1. Modify parameters: sddf/config.py
2. Run specific script: scripts/{category}/{script}.py
3. Check results: model_runs/test_with_frozen_thresholds/
```

### For Analysis
```bash
1. Run analysis: python scripts/analysis/analyze_*.py
2. Visualize: python scripts/visualization/plot_*.py
3. Review results: model_runs/
```

---

## Before & After

```
BEFORE Cleanup:
- 30 loose files at root
- 15 Python scripts scattered
- 6 JSON results mixed in
- Confusing directory structure
- Hard to find anything

AFTER Cleanup:
✅ 6 files at root (only essentials)
✅ 15 Python scripts organized in scripts/
✅ 6 JSON files in model_runs/archive/
✅ Clear logical structure
✅ Easy navigation & maintenance
```

---

## Maintenance Guidelines

**ADD FILES:**
- Python utilities → `scripts/{category}/`
- Results/artifacts → `model_runs/`
- Documentation → `docs/`
- Don't add files to root!

**CHANGE PARAMETERS:**
- Edit `sddf/config.py` (single source of truth)
- Never hardcode values elsewhere

**DELETE FILES:**
- Archive old results → `model_runs/archive/`
- Archive old docs → `docs/archive/`

---

**Status:** ✅ Organized | ✅ Reproducible | ✅ Maintainable
