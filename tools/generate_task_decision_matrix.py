from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.routing.decision_matrix import export_task_decision_matrix


def main() -> int:
    markdown_path = REPO_ROOT / "docs" / "TASK_DECISION_MATRIX.md"
    json_path = REPO_ROOT / "docs" / "task_decision_matrix.json"
    records = export_task_decision_matrix(REPO_ROOT, markdown_path, json_path)
    print(f"Wrote {len(records)} task decision-matrix rows to {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
