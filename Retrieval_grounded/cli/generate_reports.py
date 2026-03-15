"""Generate markdown report from metrics JSON."""

import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reporting import save_metric_tables


def main() -> None:
    input_path = Path("outputs/metrics/results.json")
    if not input_path.exists():
        raise FileNotFoundError(f"Metrics file not found: {input_path}")

    results = json.loads(input_path.read_text(encoding="utf-8"))
    metadata_path = Path("outputs/logs/run_metadata.json")
    metadata = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    config = metadata.get("config", {})
    environment = metadata.get("environment", {"platform": platform.platform()})

    save_metric_tables(Path("outputs/metrics"), results, config, environment)
    print("Wrote metrics tables to outputs/metrics")


if __name__ == "__main__":
    main()
