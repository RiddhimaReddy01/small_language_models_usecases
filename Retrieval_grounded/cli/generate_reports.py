"""Generate markdown report from metrics JSON."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reporting import generate_markdown_summary


def main() -> None:
    input_path = Path("outputs/metrics/results.json")
    if not input_path.exists():
        raise FileNotFoundError(f"Metrics file not found: {input_path}")

    results = json.loads(input_path.read_text(encoding="utf-8"))
    report = generate_markdown_summary(results)

    report_path = Path("outputs/metrics/report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"Wrote report to {report_path}")


if __name__ == "__main__":
    main()
