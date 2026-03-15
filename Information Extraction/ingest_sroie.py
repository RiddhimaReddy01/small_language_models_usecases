from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ie_benchmark.cli import main


if __name__ == "__main__":
    if len(sys.argv) == 1:
        raise SystemExit("Usage: python ingest_sroie.py --ocr-dir <dir> --labels-dir <dir> --output <path>")
    sys.argv.insert(1, "ingest-sroie")
    raise SystemExit(main())
