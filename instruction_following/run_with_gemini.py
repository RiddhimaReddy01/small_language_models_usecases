"""Backwards-compatible wrapper for local models plus Gemini baseline."""
import sys

from pipeline import main


if __name__ == "__main__":
    sys.argv.extend(["--include-gemini"])
    main()
