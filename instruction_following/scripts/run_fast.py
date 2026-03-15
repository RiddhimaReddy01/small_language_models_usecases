"""Run the fast local evaluation preset."""

from _bootstrap import bootstrap

bootstrap()

from instruction_following.cli import main


if __name__ == "__main__":
    main()
