from __future__ import annotations

from pathlib import Path

from ie_benchmark.reporting import write_jsonl


TARGET_FIELDS = ["company", "address", "date", "total"]


def _normalize_entities(entities: dict) -> dict[str, str]:
    normalized = {field: "" for field in TARGET_FIELDS}
    for field in TARGET_FIELDS:
        value = entities.get(field, "")
        normalized[field] = "" if value is None else str(value).strip()
    return normalized


def _reconstruct_text(words: list, bboxes: list) -> str:
    tokens: list[tuple[int, int, str]] = []
    for word, bbox in zip(words or [], bboxes or []):
        token = str(word).strip()
        if not token or not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
            continue
        x1, y1, _, _ = [int(value) for value in bbox[:4]]
        tokens.append((y1, x1, token))

    if not tokens:
        return "\n".join(str(word).strip() for word in words or [] if str(word).strip())

    tokens.sort(key=lambda item: (item[0], item[1]))
    lines: list[list[tuple[int, str]]] = []
    current_line: list[tuple[int, str]] = []
    current_y: int | None = None
    line_threshold = 18

    for y, x, token in tokens:
        if current_y is None or abs(y - current_y) <= line_threshold:
            current_line.append((x, token))
            current_y = y if current_y is None else int((current_y + y) / 2)
        else:
            lines.append(sorted(current_line, key=lambda item: item[0]))
            current_line = [(x, token)]
            current_y = y

    if current_line:
        lines.append(sorted(current_line, key=lambda item: item[0]))

    rendered_lines = [" ".join(token for _, token in line).strip() for line in lines]
    return "\n".join(line for line in rendered_lines if line)


def download_sroie_from_hf(output_path: str, split: str = "train") -> int:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("Downloading from Hugging Face requires the datasets package.") from exc

    dataset = load_dataset("jsdnrs/ICDAR2019-SROIE", split=split)
    rows: list[dict[str, object]] = []

    for row in dataset:
        words = row.get("words", []) or []
        text = _reconstruct_text(words, row.get("bboxes", []) or [])
        rows.append(
            {
                "id": str(row.get("key", "")),
                "text": text,
                "fields": _normalize_entities(row.get("entities", {}) or {}),
                "split": "clean",
            }
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output, rows)
    return len(rows)
