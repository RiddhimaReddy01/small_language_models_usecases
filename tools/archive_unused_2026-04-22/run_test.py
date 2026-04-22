"""
Test-split inference runner.

SPLIT is hard-coded to "test" — it cannot be changed by a CLI flag.
This script only ever processes samples whose SHA-1 bucket >= 70.

Purpose:
    Collect model outputs for the HELD-OUT TEST set.

    *** RUN THIS LAST — AFTER tau* IS FROZEN ON VAL ***

    Results from this split are the FINAL reported numbers.
    Never refit difficulty weights or routing threshold after
    examining test outputs. One-shot evaluation only.

Usage:
    python tools/run_test.py                    # all models, all tasks
    python tools/run_test.py --ollama-only       # skip Groq
    python tools/run_test.py --groq-only         # skip Ollama
    python tools/run_test.py --tasks maths classification
    python tools/run_test.py --dry-run           # show plan, no inference
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# HARD-CODED SPLIT — do not add a --split argument to this script.
# If you need train or val, use run_train.py or run_val.py.
#
# WARNING: Do not run this until routing thresholds are finalised on val.
# ---------------------------------------------------------------------------
SPLIT = "test"

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
