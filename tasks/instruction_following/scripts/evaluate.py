"""Run the full local evaluation preset."""
import sys

from _bootstrap import bootstrap

bootstrap()

from instruction_following.cli import main


if __name__ == "__main__":
    sys.argv.extend(["--preset", "full"])
    main()
