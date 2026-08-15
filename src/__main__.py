"""Allow the CLI to run with ``python3 -m src``."""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
