"""Run the fast local preset plus a Gemini baseline."""
import sys

from _bootstrap import bootstrap

bootstrap()

from instruction_following.cli import main


if __name__ == "__main__":
    sys.argv.extend(["--include-gemini"])
    main()
