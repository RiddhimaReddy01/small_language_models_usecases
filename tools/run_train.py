"""
Train-split inference runner.

SPLIT is hard-coded to "train" — it cannot be changed by a CLI flag.
This script only ever processes samples whose SHA-1 bucket < 30.

Purpose:
    Collect model outputs for the TRAINING set.
    These outputs are used to FIT the SDDF difficulty weights.
    Do NOT use these results to pick a routing threshold (use val for that).

Usage:
    python tools/run_train.py                   # all models, all tasks
    python tools/run_train.py --ollama-only      # skip Groq
    python tools/run_train.py --groq-only        # skip Ollama
    python tools/run_train.py --tasks maths classification
    python tools/run_train.py --dry-run          # show plan, no inference
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# HARD-CODED SPLIT — do not add a --split argument to this script.
# If you need val or test, use run_val.py or run_test.py.
# ---------------------------------------------------------------------------
SPLIT = "train"

# Inject split into argv so the shared runner picks it up.
# Strip any accidental --split flags the user may have typed.
_cleaned: list[str] = []
_skip_next = False
for _a in sys.argv[1:]:
    if _skip_next:
        _skip_next = False
        continue
    if _a == "--split":
        _skip_next = True          # skip value too
        continue
    if _a.startswith("--split="):
        continue                   # strip --split=xxx form
    _cleaned.append(_a)

sys.argv = [sys.argv[0]] + ["--split", SPLIT] + _cleaned

# Add tools/ to path so the overnight runner can be imported directly.
sys.path.insert(0, str(Path(__file__).parent))

from run_inference_overnight import main  # noqa: E402

if __name__ == "__main__":
    main()
