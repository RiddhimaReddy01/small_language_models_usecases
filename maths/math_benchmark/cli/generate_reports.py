import json

from eval_pipeline.reporting import REPORT_OUTPUTS, generate_reports
from math_benchmark.paths import LEGACY_REPORTS_DIR, REPORTS_DIR, ROOT


def main():
    structured, markdown, summary, sources = generate_reports(ROOT)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / REPORT_OUTPUTS["json"]).write_text(json.dumps(structured, indent=2), encoding="utf-8")
    (REPORTS_DIR / REPORT_OUTPUTS["markdown"]).write_text(markdown, encoding="utf-8")
    (REPORTS_DIR / REPORT_OUTPUTS["summary"]).write_text(summary, encoding="utf-8")
    LEGACY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (LEGACY_REPORTS_DIR / REPORT_OUTPUTS["json"]).write_text(json.dumps(structured, indent=2), encoding="utf-8")
    (LEGACY_REPORTS_DIR / REPORT_OUTPUTS["markdown"]).write_text(markdown, encoding="utf-8")
    (LEGACY_REPORTS_DIR / REPORT_OUTPUTS["summary"]).write_text(summary, encoding="utf-8")
    models = ", ".join(sorted(structured["models"]))
    print(f"Loaded sources: {', '.join(sources)}")
    print(f"Models: {models}")
    print(f"Gemini mode: {'REAL API' if 'REAL API' in structured['critical_note'] else 'DRY RUN'}")
    print(f"Wrote reports to {REPORTS_DIR}")


if __name__ == "__main__":
    main()
