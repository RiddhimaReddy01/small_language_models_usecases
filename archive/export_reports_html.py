from __future__ import annotations

from pathlib import Path

import markdown


REPORTS = [
    ("Classification", Path("classification/results/reports")),
    ("Text Generation", Path("text_generation/results/runs/suite_20260315_000947/reports")),
    ("Summarization", Path("Summarization/outputs/reports")),
    ("Instruction Following", Path("instruction_following/results/reports")),
    ("Code Generation", Path("code_generation/archive/runs/run_20260314_023126/reports")),
    ("Maths", Path("maths/reports")),
    ("Retrieval Grounded QA", Path("Retrieval_grounded/outputs_qwen05b_arrow30/reports")),
    ("Information Extraction", Path("Information Extraction/outputs/20260314_071350/reports")),
]


STYLE = """
body { font-family: Georgia, 'Times New Roman', serif; margin: 40px auto; max-width: 920px; padding: 0 20px; color: #1f2937; line-height: 1.6; }
h1, h2, h3 { color: #0f172a; }
code { background: #f3f4f6; padding: 2px 5px; border-radius: 4px; }
pre { background: #111827; color: #f9fafb; padding: 16px; border-radius: 10px; overflow-x: auto; }
a { color: #0f766e; }
img { max-width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 8px; }
.card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px 18px; margin-bottom: 14px; background: #ffffff; }
.muted { color: #6b7280; }
"""


def wrap_html(title: str, body_html: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{STYLE}</style>
</head>
<body>
{body_html}
</body>
</html>
"""


def convert_markdown(report_dir: Path) -> None:
    for md_path in sorted(report_dir.glob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        body_html = markdown.markdown(text, extensions=["tables", "fenced_code"])
        html = wrap_html(md_path.stem.replace("_", " ").title(), body_html)
        md_path.with_suffix(".html").write_text(html, encoding="utf-8")


def write_index(root: Path) -> Path:
    cards: list[str] = ["<h1>SDDF Benchmark Reports</h1>", '<p class="muted">Open any combined report below.</p>']
    for label, report_dir in REPORTS:
        combined = report_dir / "combined_report.html"
        part_a = report_dir / "part_a_report.html"
        part_b = report_dir / "part_b_report.html"
        cards.append(
            f"""
<div class="card">
  <h2>{label}</h2>
  <p><a href="{combined.as_posix()}">Combined report</a></p>
  <p class="muted"><a href="{part_a.as_posix()}">Part A</a> | <a href="{part_b.as_posix()}">Part B</a></p>
</div>
""".strip()
        )
    output = root / "reports_index.html"
    output.write_text(wrap_html("SDDF Benchmark Reports", "\n".join(cards)), encoding="utf-8")
    return output


def main() -> None:
    root = Path.cwd()
    for _, report_dir in REPORTS:
        if report_dir.exists():
            convert_markdown(report_dir)
    index_path = write_index(root)
    print(index_path)


if __name__ == "__main__":
    main()
