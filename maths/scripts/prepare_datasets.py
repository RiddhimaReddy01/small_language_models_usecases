import argparse
import json
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional


ANSWER_MARKER_RE = re.compile(r"####\s*([^\n\r]+)")
BOXED_RE = re.compile(r"\\boxed\{([^{}]+)\}")
LEVEL_RE = re.compile(r"Level\s+(\d+)", re.IGNORECASE)


def parse_args():
    parser = argparse.ArgumentParser(description="Normalize GSM8K, SVAMP, and MATH data into benchmark JSONL files.")
    parser.add_argument("--gsm8k-source", default="data/raw/gsm8k", help="Path to raw GSM8K file or directory.")
    parser.add_argument("--svamp-source", default="data/raw/svamp", help="Path to raw SVAMP file or directory.")
    parser.add_argument("--math-source", default="data/raw/math", help="Path to raw MATH file or directory.")
    parser.add_argument("--output-dir", default="data", help="Directory for normalized benchmark JSONL files.")
    return parser.parse_args()


def read_json_file(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl_file(path: Path) -> List[Dict]:
    items = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def iter_records(source: Path) -> Iterable[Dict]:
    if not source.exists():
        raise FileNotFoundError(f"Raw dataset source not found: {source}")
    if source.is_file():
        if source.suffix.lower() == ".jsonl":
            for item in read_jsonl_file(source):
                yield item
            return
        if source.suffix.lower() == ".json":
            data = read_json_file(source)
            if isinstance(data, list):
                for item in data:
                    yield item
                return
            if isinstance(data, dict):
                for key in ["data", "examples", "problems"]:
                    if isinstance(data.get(key), list):
                        for item in data[key]:
                            yield item
                        return
                yield data
                return
        raise ValueError(f"Unsupported file format: {source}")

    for child in sorted(source.rglob("*")):
        if not child.is_file():
            continue
        if child.suffix.lower() == ".jsonl":
            for item in read_jsonl_file(child):
                yield item
        elif child.suffix.lower() == ".json":
            data = read_json_file(child)
            if isinstance(data, list):
                for item in data:
                    yield item
            elif isinstance(data, dict) and any(isinstance(data.get(k), list) for k in ["data", "examples", "problems"]):
                for key in ["data", "examples", "problems"]:
                    values = data.get(key)
                    if isinstance(values, list):
                        for item in values:
                            yield item
                        break
            else:
                yield data


def clean_answer(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    value = str(text).strip()
    if not value:
        return None
    marker = ANSWER_MARKER_RE.search(value)
    if marker:
        return marker.group(1).strip()
    boxed = BOXED_RE.findall(value)
    if boxed:
        return boxed[-1].strip()
    return value.strip()


def infer_difficulty(question: str, answer: str, level_hint: Optional[str] = None) -> str:
    if level_hint:
        match = LEVEL_RE.search(level_hint)
        if match:
            level = int(match.group(1))
            if level <= 2:
                return "easy"
            if level == 3:
                return "medium"
            return "hard"
        lowered = level_hint.strip().lower()
        if lowered in {"easy", "medium", "hard"}:
            return lowered

    text = f"{question} {answer}"
    word_count = len(re.findall(r"\w+", text))
    operation_count = len(re.findall(r"[+\-*/^=]", text))
    has_fraction = bool(re.search(r"\d+\s*/\s*\d+", text))
    has_system = any(token in text.lower() for token in ["prove", "polynomial", "triangle", "probability", "equation"])

    score = word_count + operation_count * 8
    if has_fraction:
        score += 20
    if has_system:
        score += 25

    if score < 80:
        return "easy"
    if score < 160:
        return "medium"
    return "hard"


def difficulty_score(question: str, answer: str) -> float:
    text = f"{question} {answer}"
    word_count = len(re.findall(r"\w+", text))
    operation_count = len(re.findall(r"[+\-*/^=]", text))
    has_fraction = bool(re.search(r"\d+\s*/\s*\d+", text))
    has_system = any(token in text.lower() for token in ["prove", "polynomial", "triangle", "probability", "equation"])
    return (
        word_count
        + operation_count * 8
        + (20 if has_fraction else 0)
        + (25 if has_system else 0)
    )


def assign_quantile_difficulties(records: List[Dict]) -> List[Dict]:
    scored = []
    for idx, record in enumerate(records):
        score = difficulty_score(record["question"], record["answer"])
        scored.append((score, idx))
    scored.sort()

    n = len(scored)
    if n < 3:
        for record in records:
            record["difficulty"] = "medium"
        return records

    lower_cut = math.ceil(n / 3)
    upper_cut = math.ceil(2 * n / 3)
    for rank, (_, idx) in enumerate(scored):
        if rank < lower_cut:
            records[idx]["difficulty"] = "easy"
        elif rank < upper_cut:
            records[idx]["difficulty"] = "medium"
        else:
            records[idx]["difficulty"] = "hard"
    return records


def normalize_gsm8k_item(item: Dict) -> Dict:
    question = item.get("question")
    answer = clean_answer(item.get("final_answer") or item.get("answer"))
    if not question or answer is None:
        raise ValueError("GSM8K record must provide question and answer.")
    difficulty = item.get("difficulty") or infer_difficulty(question, answer, item.get("level"))
    return {"question": str(question).strip(), "answer": answer, "difficulty": difficulty}


def normalize_svamp_item(item: Dict) -> Dict:
    body = item.get("Body") or item.get("body") or ""
    prompt = item.get("Question") or item.get("question") or ""
    question = " ".join(part.strip() for part in [body, prompt] if part and str(part).strip())
    answer = clean_answer(item.get("Answer") or item.get("answer"))
    if not question or answer is None:
        raise ValueError("SVAMP record must provide question/body and answer.")
    difficulty = item.get("difficulty") or infer_difficulty(question, answer, item.get("level"))
    return {"question": question, "answer": answer, "difficulty": difficulty}


def normalize_math_item(item: Dict) -> Dict:
    question = item.get("problem") or item.get("question")
    answer = clean_answer(item.get("answer") or item.get("final_answer") or item.get("solution"))
    level_hint = item.get("level") or item.get("difficulty")
    if not question or answer is None:
        raise ValueError("MATH record must provide problem/question and answer/solution.")
    difficulty = item.get("difficulty")
    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = infer_difficulty(question, answer, level_hint)
    return {"question": str(question).strip(), "answer": answer, "difficulty": difficulty}


def normalize_records(name: str, source: Path) -> List[Dict]:
    normalized = []
    for item in iter_records(source):
        if name == "gsm8k":
            record = normalize_gsm8k_item(item)
        elif name == "svamp":
            record = normalize_svamp_item(item)
        elif name == "math_subset":
            record = normalize_math_item(item)
        else:
            raise ValueError(f"Unsupported dataset name: {name}")
        normalized.append(record)
    if not normalized:
        raise ValueError(f"No records found for dataset '{name}' in {source}")
    if name in {"gsm8k", "svamp"}:
        normalized = assign_quantile_difficulties(normalized)
    return normalized


def ensure_difficulty_coverage(name: str, records: List[Dict]):
    counts = {"easy": 0, "medium": 0, "hard": 0}
    for record in records:
        difficulty = record["difficulty"]
        if difficulty not in counts:
            raise ValueError(f"{name} contains unsupported difficulty label: {difficulty}")
        counts[difficulty] += 1
    missing = [label for label, count in counts.items() if count == 0]
    if missing:
        raise ValueError(f"{name} is missing difficulty buckets: {', '.join(missing)}")
    return counts


def write_jsonl(path: Path, records: List[Dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    datasets = {
        "gsm8k": Path(args.gsm8k_source),
        "svamp": Path(args.svamp_source),
        "math_subset": Path(args.math_source),
    }

    for name, source in datasets.items():
        records = normalize_records(name, source)
        counts = ensure_difficulty_coverage(name, records)
        output_path = output_dir / f"{name}.jsonl"
        write_jsonl(output_path, records)
        print(f"Wrote {len(records)} records to {output_path} with difficulty counts {counts}")


if __name__ == "__main__":
    main()
