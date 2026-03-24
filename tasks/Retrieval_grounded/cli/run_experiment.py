"""CLI entrypoint for running experiments."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.runners import main


if __name__ == "__main__":
    main()
