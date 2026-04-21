# Root Level Files Audit

**Status:** 30 loose files at root (need organization)

---

## Python Scripts (15 files)

### ✅ KEEP AT ROOT (Essential Entry Points)
| File | Purpose | Status |
|------|---------|--------|
| `run_test_with_frozen_thresholds.py` | Main SDDF pipeline | ✅ Entry point |
| `requirements.txt` | Dependencies | ✅ Essential |

### 📂 MOVE TO `scripts/` (Utilities & Analysis)

#### Tier Analysis Scripts
```
analyze_uc_tier_sensitivity.py         → scripts/analysis/
analyze_uc_tier_sensitivity_v2.py      → scripts/analysis/
```

#### Computation Scripts
```
compute_continuous_validation_results.py  → scripts/compute/
compute_uc_routing_decisions.py          → scripts/compute/
```

#### Demo & Testing
```
demo_frozen_thresholds.py              → scripts/demo/
test_adaptive_validation.py            → scripts/tests/
test_adaptive_validation_all_models.py → scripts/tests/
```

#### Visualization
```
plot_uc_empirical_routing.py           → scripts/visualization/
```

#### Section-Specific (Development)
```
section5_task_classifier.py            → docs/archive/scripts/
section7_runtime_routing.py            → docs/archive/scripts/
runtime_routing_section7.py            → docs/archive/scripts/
```

#### Production/Experiment Scripts
```
production_deployment.py               → scripts/deployment/
end_to_end_runtime_pipeline.py        → scripts/pipelines/
run_slm_research_usecases.py          → scripts/pipelines/
```

---

## JSON Files (6 files)

### 📊 MOVE TO `model_runs/` (Results & Artifacts)

```
adaptive_validation_comprehensive_results.json  → model_runs/archive/
continuous_validation_results.json             → model_runs/archive/
section7_routing_results.json                  → model_runs/archive/
task_thresholds.json                          → model_runs/archive/
```

### 📋 MOVE TO `sddf/` (Configuration)

```
benchmark_governance_registry.json     → sddf/registry/ or docs/
benchmark_pipeline_registry.json       → sddf/registry/ or docs/
```

---

## Other Files (9 files)

### 🗑️ DELETE (Temporary/Unnecessary)

```
python-3.11.9-embed-amd64.zip         # Embedded Python - not needed in repo
tmp_final_alignment_extracted.txt      # Temporary file - can delete
tmp_docx/                              # Temporary folder - can delete
__pycache__/                           # Python cache - ignore in .gitignore
```

### 📂 MOVE TO `logs/`

```
pipeline_llm_baseline_output.log       → logs/ (already exists)
```

### 📂 MOVE TO `scripts/`

```
pull_ollama_models.sh                  → scripts/setup/
run_overnight.bat                      → scripts/automation/
```

### 📂 MOVE TO `docs/archive/`

```
BEFORE_AFTER_COMPARISON.txt            → docs/archive/
IMPLEMENTATION_SUMMARY.txt             → docs/archive/
OPERATIONAL_ZONE_SUMMARY.txt           → docs/archive/
```

### ✅ KEEP AT ROOT

```
requirements.txt                       # Must be at root for pip install
```

---

## Proposed Directory Structure

```
project_root/
├── README.md                          # ✅ Keep
├── README_CONSOLIDATED.md             # ✅ Keep
├── REPRODUCIBILITY.md                 # ✅ Keep
├── SDDF_METHODOLOGY_VERIFICATION.md  # ✅ Keep
├── requirements.txt                   # ✅ Keep
├── run_test_with_frozen_thresholds.py # ✅ Keep (main entry point)
│
├── scripts/                           # 📂 NEW
│   ├── analysis/
│   │   ├── analyze_uc_tier_sensitivity.py
│   │   └── analyze_uc_tier_sensitivity_v2.py
│   ├── compute/
│   │   ├── compute_continuous_validation_results.py
│   │   └── compute_uc_routing_decisions.py
│   ├── demo/
│   │   └── demo_frozen_thresholds.py
│   ├── tests/
│   │   ├── test_adaptive_validation.py
│   │   └── test_adaptive_validation_all_models.py
│   ├── visualization/
│   │   └── plot_uc_empirical_routing.py
│   ├── deployment/
│   │   └── production_deployment.py
│   ├── pipelines/
│   │   ├── end_to_end_runtime_pipeline.py
│   │   └── run_slm_research_usecases.py
│   ├── setup/
│   │   └── pull_ollama_models.sh
│   └── automation/
│       └── run_overnight.bat
│
├── sddf/                              # ✅ Existing
│   ├── config.py
│   ├── frozen_thresholds.py
│   ├── runtime_routing.py
│   └── [... other modules ...]
│
├── model_runs/                        # ✅ Existing
│   ├── sddf_training_splits/
│   ├── clean_deterministic_splits/
│   ├── test_with_frozen_thresholds/
│   └── archive/                       # 📂 NEW
│       ├── adaptive_validation_comprehensive_results.json
│       ├── continuous_validation_results.json
│       └── [... other JSON files ...]
│
├── docs/                              # ✅ Existing
│   ├── archive/
│   │   ├── INDEX.md
│   │   └── [28 legacy .md files]
│   └── [... other docs ...]
│
├── logs/                              # ✅ Existing
│   └── pipeline_llm_baseline_output.log
│
├── repos/                             # ✅ Existing
├── tests/                             # ✅ Existing
├── tools/                             # ✅ Existing
├── data/                              # ✅ Existing
└── framework/                         # ✅ Existing
```

---

## Summary of Changes

| Category | Files | Action |
|----------|-------|--------|
| **Delete** | 4 | python-3.11.9-*.zip, tmp_docx/, __pycache__, tmp_*.txt |
| **Move to scripts/** | 13 | All Python utility scripts |
| **Move to docs/archive/** | 3 | TXT summary files |
| **Move to logs/** | 1 | Log file |
| **Move to model_runs/archive/** | 4 | JSON result files |
| **Keep at root** | 2 | requirements.txt, run_test_with_frozen_thresholds.py |
| **Keep at root (existing)** | 5 | README files, SDDF_METHODOLOGY_VERIFICATION.md |

**Result:** Root directory cleaned from 30 → 7 files (77% reduction)

---

## Implementation Plan

1. Create `scripts/` directory structure
2. Move Python scripts to appropriate subdirectories
3. Move JSON files to `model_runs/archive/`
4. Delete temporary files
5. Update all import paths in remaining scripts
6. Commit cleanup
7. Verify no broken imports

---

## Files That Need Review

These files have unclear purpose - recommend deleting unless specifically needed:

- `framework/` - Is this still used?
- `pandas/` - Why is pandas at root? Should be venv dependency
- `tools/` - What tools? Clarify or organize
- `validation_figures/` - Results? Should be in model_runs/
- `tasks__removed/` - Old/removed tasks? Archive or delete?

---

## .gitignore Updates Needed

```bash
# Add to .gitignore
__pycache__/
*.pyc
tmp_*/
.tmp_*
python-*.zip
pandas/
```

---

**Next Action:** Confirm which files to delete vs organize, then execute cleanup.
