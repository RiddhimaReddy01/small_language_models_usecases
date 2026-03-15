from __future__ import annotations

import json
from pathlib import Path

from ie_benchmark.reporting import write_jsonl


FIELD_ALIASES = {
    "company": "company",
    "vendor": "company",
    "vendor_name": "company",
    "address": "address",
    "date": "date",
    "total": "total",
    "total_amount": "total",
    "amount": "total",
}

TARGET_FIELDS = ["company", "address", "date", "total"]


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def _parse_ocr_file(path: Path) -> str:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "text" in payload:
            return str(payload["text"]).strip()
        if isinstance(payload, list):
            return "\n".join(str(item) for item in payload).strip()
        return str(payload).strip()
    return _read_text_file(path)


def _parse_label_line(line: str) -> tuple[str, str] | None:
    for separator in [":", "\t", ","]:
        if separator in line:
            key, value = line.split(separator, 1)
            return key.strip(), value.strip()
    return None


def _normalize_fields(fields: dict[str, str]) -> dict[str, str]:
    normalized = {field: "" for field in TARGET_FIELDS}
    for key, value in fields.items():
        alias = FIELD_ALIASES.get(key.strip().lower())
        if alias:
            normalized[alias] = value.strip()
    return normalized


def _parse_label_file(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return {field: "" for field in TARGET_FIELDS}

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, dict):
        return _normalize_fields({str(key): "" if value is None else str(value) for key, value in payload.items()})

    parsed: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        item = _parse_label_line(line)
        if item is None:
            continue
        key, value = item
        parsed[key] = value
    return _normalize_fields(parsed)


def ingest_sroie(ocr_dir: str, labels_dir: str, output_path: str, split: str = "clean") -> int:
    ocr_root = Path(ocr_dir)
    labels_root = Path(labels_dir)
    output = Path(output_path)

    if not ocr_root.exists():
        raise FileNotFoundError(f"OCR directory not found: {ocr_root}")
    if not labels_root.exists():
        raise FileNotFoundError(f"Labels directory not found: {labels_root}")

    label_files = sorted(path for path in labels_root.iterdir() if path.is_file())
    rows: list[dict[str, object]] = []

    for label_path in label_files:
        stem = label_path.stem
        ocr_candidates = [ocr_root / f"{stem}.txt", ocr_root / f"{stem}.json"]
        ocr_path = next((candidate for candidate in ocr_candidates if candidate.exists()), None)
        if ocr_path is None:
            continue

        rows.append(
            {
                "id": stem,
                "text": _parse_ocr_file(ocr_path),
                "fields": _parse_label_file(label_path),
                "split": split,
            }
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output, rows)
    return len(rows)
