# Archived Documentation

This directory contains legacy documentation files that have been consolidated into:
- **README_CONSOLIDATED.md** - System overview and architecture
- **REPRODUCIBILITY.md** - Step-by-step reproduction guide
- **sddf/config.py** - Centralized parameters (source of truth)

## Why Archived?

These files were created during development and analysis but are **no longer needed** for:
- Understanding the system
- Reproducing experiments
- Modifying the codebase

They are kept for **reference only** and document the development process.

## Contents

| File | Purpose |
|------|---------|
| ALIGNMENT_QUICK_REFERENCE.md | Early alignment analysis |
| CODE_CHANGES_BEFORE_AFTER.md | Code refactoring notes |
| COMPLETION_STATUS.md | Status snapshot from development |
| CONTINUOUS_VALIDATION_*.md (3) | Continuous validation analysis variants |
| DEPLOYMENT_GUIDE.md | Draft deployment guide |
| EMPIRICAL_ROUTING_*.md (2) | Empirical routing analysis |
| FROZEN_THRESHOLDS_*.md (2) | Frozen thresholds implementation notes |
| IMPLEMENTATION_*.md (4) | Implementation status snapshots |
| INTEGRATION_COMPLETE.md | Integration completion notes |
| PAPER_TO_CODE_MAPPING.md | Paper ↔ code mapping |
| SDDF_v3_*.md (2) | SDDF v3 alignment analysis |
| *_COMPLETION_SUMMARY.md (4) | Phase completion summaries |
| THRESHOLD_SENSITIVITY_ANALYSIS.md | Early sensitivity analysis |
| UC_*.md (5) | Use case analysis and metrics |

**Total:** 28 files, ~350KB

## If You Need This Information

- **Architecture:** See `README_CONSOLIDATED.md` (ARCHITECTURE section)
- **Reproduce:** See `REPRODUCIBILITY.md` (step-by-step guide)
- **Parameters:** See `sddf/config.py` (single source of truth)
- **Historical context:** Files in this directory show development progression

## To Delete

If cleaning up storage, these files can be safely deleted:
```bash
rm -rf docs/archive
```

Nothing in the production system depends on these files.
