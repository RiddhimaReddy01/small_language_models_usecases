"""Backwards-compatible full evaluation wrapper."""
import sys

from pipeline import main


if __name__ == "__main__":
    sys.argv.extend(["--preset", "full"])
    main()
