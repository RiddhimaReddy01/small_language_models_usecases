"""
Validation-split inference runner.

SPLIT is hard-coded to "val" — it cannot be changed by a CLI flag.
This script only ever processes samples whose SHA-1 bucket is 30-69.

Purpose:
    Collect model outputs for the VALIDATION set.
    These outputs are used to TUNE the SDDF routing threshold (tau*).
    Do NOT look at test outputs before threshold is frozen.

Usage:
    python tools/run_val.py                     # all models, all tasks
    python tools/run_val.py --ollama-only        # skip Groq
    python tools/run_val.py --groq-only          # skip Ollama
    python tools/run_val.py --tasks maths classification
    python tools/run_val.py --dry-run            # show plan, no inference
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# HARD-CODED SPLIT — do not add a --split argument to this script.
# If you need train or test, use run_train.py or run_test.py.
# ---------------------------------------------------------------------------
SPLIT = "val"

# Inject split into argv so the shared runner picks it up.
_cleaned: list[str] = []
_skip_next = False
for _a in sys.argv[1:]:
    if _skip_next:
        _skip_next = False
        continue
    if _a == "--split":
        _skip_next = True
        continue
    if _a.startswith("--split="):
        continue
    _cleaned.append(_a)

sys.argv = [sys.argv[0]] + ["--split", SPLIT] + _cleaned

sys.path.insert(0, str(Path(__file__).parent))

from run_inference_overnight import main  # noqa: E402

if __name__ == "__main__":
    main()
