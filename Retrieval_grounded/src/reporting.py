"""Reporting helpers for benchmark outputs."""

import json
from pathlib import Path


def save_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def generate_markdown_summary(results: dict) -> str:
    lines = ["# Experiment Report", ""]
    for model_name, model_result in results.items():
        capability = model_result.get("capability", {})
        lines.append(f"## {model_name}")
        lines.append(f"- EM: {capability.get('exact_match', 0):.2f}%")
        lines.append(f"- F1: {capability.get('f1_score', 0):.2f}%")
        lines.append("")
    return "\n".join(lines)
