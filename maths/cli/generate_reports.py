import json
from pathlib import Path

from src.reporting import REPORT_OUTPUTS, generate_reports


ROOT = Path(__file__).resolve().parent.parent
METRICS_DIR = ROOT / "outputs" / "metrics"


def main():
    structured, markdown, tables, summary, sources = generate_reports(ROOT)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    (METRICS_DIR / REPORT_OUTPUTS["json"]).write_text(json.dumps(structured, indent=2), encoding="utf-8")
    (METRICS_DIR / REPORT_OUTPUTS["markdown"]).write_text(markdown, encoding="utf-8")
    (METRICS_DIR / REPORT_OUTPUTS["tables"]).write_text(tables, encoding="utf-8")
    (METRICS_DIR / REPORT_OUTPUTS["summary"]).write_text(summary, encoding="utf-8")
    models = ", ".join(sorted(structured["models"]))
    print(f"Loaded sources: {', '.join(sources)}")
    print(f"Models: {models}")
    print(f"Gemini mode: {'REAL API' if 'REAL API' in structured['critical_note'] else 'DRY RUN'}")
    print(f"Wrote reports to {METRICS_DIR}")


if __name__ == "__main__":
    main()
