"""Compatibility CLI shim for local execution from the repo root."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from instruction_following.cli import main


if __name__ == "__main__":
    main()
