from __future__ import annotations

from pathlib import Path

from sddf.validator import save_historical_run_validation


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    output_path = repo_root / "historical_report_readiness.json"
    saved = save_historical_run_validation(repo_root, output_path)
    print(f"Saved report-readiness audit to {saved}")


if __name__ == "__main__":
    main()
