from __future__ import annotations

import argparse
import ast
import json
import re
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEGACY_BENCHMARK_ROOT = ROOT / "model_runs" / "benchmark_75"
BENCHMARK_ROOT = LEGACY_BENCHMARK_ROOT if LEGACY_BENCHMARK_ROOT.exists() else ROOT / "model_runs"
SUPPORTED_TASKS = ("classification", "code_generation", "maths", "text_generation")
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAMES = {
    "tinyllama_1.1b": "tinyllama:1.1b",
    "phi3_mini": "phi3:mini",
    "qwen2.5_1.5b": "qwen2.5:1.5b",
    "llama_llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
}
MODEL_SIZES = {
    "tinyllama_1.1b": "1B",
    "phi3_mini": "7B",
    "qwen2.5_1.5b": "1.5B",
    "llama_llama-3.3-70b-versatile": "70B",
}
PROMPT_BANK = {
    "classification": [
        "Classify sentiment: 'This movie was amazing!'",
        "Classify sentiment: 'Terrible experience, never again'",
        "Classify sentiment: 'It was okay, nothing special'",
        "Categorize text: Political or Sports?",
        "Is this email spam or not spam?",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rerun only missing benchmark samples for a tracked task/model.")
    parser.add_argument("--task", required=True, choices=SUPPORTED_TASKS)
    parser.add_argument("--model-folder", required=True, choices=sorted(MODEL_NAMES))
    parser.add_argument(
        "--sample-id",
        action="append",
        default=None,
        help="Specific sample_id to rerun. Pass multiple times. If omitted, the script reruns all currently missing sample_ids.",
    )
    parser.add_argument(
        "--ollama-url",
        default=OLLAMA_URL,
        help="Ollama generate endpoint. Defaults to the local daemon.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature for reruns.",
    )
    parser.add_argument(
        "--timeout-s",
        type=int,
        default=300,
        help="HTTP timeout per generation request.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="num_predict for Ollama generation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the missing sample_ids and prompts without calling the model or editing files.",
    )
    return parser.parse_args()


def load_expected_rows(task: str, task_root: Path) -> list[dict[str, Any]]:
    if task == "classification":
        prompts = PROMPT_BANK["classification"]
        rows: list[dict[str, Any]] = []
        for index in range(75):
            within_bin = index % 15
            rows.append(
                {
                    "sample_id": f"classification_{index}",
                    "bin": index // 15,
                    "prompt": f"{prompts[within_bin % len(prompts)]} (Example {within_bin + 1})",
                }
            )
        return rows

    baseline_candidates = [
        task_root / "llama_llama-3.3-70b-versatile" / "outputs.jsonl",
        task_root / "qwen2.5_1.5b" / "outputs.jsonl",
        task_root / "phi3_mini" / "outputs.jsonl",
        task_root / "tinyllama_1.1b" / "outputs.jsonl",
    ]
    source = next((p for p in baseline_candidates if p.exists()), None)
    if source is None:
        raise FileNotFoundError(f"Could not find a baseline outputs.jsonl for task '{task}' under {task_root}")

    rows = []
    for row in dedupe_rows(load_jsonl(source)):
        rows.append(
            {
                "sample_id": str(row["sample_id"]),
                "bin": int(row.get("bin", 0) or 0),
                "prompt": str(row.get("prompt", "")),
            }
        )
    rows.sort(key=lambda item: int(str(item["sample_id"]).rsplit("_", 1)[1]))
    return rows


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sample: dict[str, dict[str, Any]] = {}
    for row in rows:
        sample_id = str(row["sample_id"])
        existing = by_sample.get(sample_id)
        if existing is None or str(row.get("timestamp") or "") >= str(existing.get("timestamp") or ""):
            by_sample[sample_id] = row
    return sorted(by_sample.values(), key=lambda row: int(str(row["sample_id"]).rsplit("_", 1)[1]))


def extract_code_blocks(text: str) -> list[str]:
    matches = re.findall(r"```(?:python)?\s*(.*?)```", text or "", flags=re.DOTALL | re.IGNORECASE)
    if matches:
        return [match.strip() for match in matches if match.strip()]
    return []


def build_parsed_output(task: str, raw_output: str) -> dict[str, Any]:
    if task != "code_generation":
        return {}
    blocks = extract_code_blocks(raw_output)
    syntax_valid = False
    if blocks:
        try:
            ast.parse(blocks[0])
            syntax_valid = True
        except SyntaxError:
            syntax_valid = False
    return {
        "code_blocks": blocks,
        "syntax_valid": syntax_valid,
    }


def build_row(task: str, model_folder: str, sample: dict[str, Any], response_text: str, latency_s: float) -> dict[str, Any]:
    parsed_output = build_parsed_output(task, response_text)
    status = "success"
    error = None
    if task == "code_generation" and not parsed_output.get("code_blocks"):
        status = "invalid"
        error = "No code block detected in recovery rerun output."
    return {
        "query_id": str(uuid.uuid4()),
        "task": task,
        "bin": sample["bin"],
        "sample_id": sample["sample_id"],
        "model": MODEL_NAMES[model_folder],
        "model_size": MODEL_SIZES[model_folder],
        "backend": "ollama",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "latency_sec": latency_s,
        "prompt": sample["prompt"],
        "raw_output": response_text,
        "parsed_output": parsed_output,
        "status": status,
        "valid": bool(response_text.strip()),
        "error": error,
        "failure_category": None if response_text.strip() else "empty_output",
        "validation_checks": {
            "non_empty": bool(response_text.strip()),
            "parseable": True,
            "has_expected_fields": True,
        },
        "validation_notes": "Recovery rerun generated via tools/rerun_missing_benchmark_samples.py",
        "run_id": f"recovery-{uuid.uuid4()}",
    }


def ollama_generate(model_name: str, prompt: str, ollama_url: str, temperature: float, timeout_s: int, max_tokens: int) -> tuple[str, float]:
    payload = json.dumps(
        {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        ollama_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Unable to reach Ollama at {ollama_url}: {exc.reason}") from exc
    latency_s = time.perf_counter() - start
    return str(body.get("response") or ""), latency_s


def main() -> int:
    args = parse_args()
    task_root = BENCHMARK_ROOT / args.task
    output_path = task_root / args.model_folder / "outputs.jsonl"
    existing_rows = dedupe_rows(load_jsonl(output_path))
    existing_ids = {str(row["sample_id"]) for row in existing_rows}
    expected_rows = load_expected_rows(args.task, task_root)
    expected_lookup = {row["sample_id"]: row for row in expected_rows}

    if args.sample_id:
        target_ids = list(dict.fromkeys(args.sample_id))
    else:
        target_ids = [row["sample_id"] for row in expected_rows if row["sample_id"] not in existing_ids]

    if not target_ids:
        print("No missing sample_ids to rerun.")
        return 0

    missing_samples = [expected_lookup[sample_id] for sample_id in target_ids]
    print(f"Preparing to rerun {len(missing_samples)} samples for {args.task}/{args.model_folder}.")
    for sample in missing_samples:
        print(f"  - {sample['sample_id']} (bin {sample['bin']}): {sample['prompt']}")

    if args.dry_run:
        return 0

    new_rows: list[dict[str, Any]] = []
    for sample in missing_samples:
        print(f"Running {sample['sample_id']} ...")
        response_text, latency_s = ollama_generate(
            MODEL_NAMES[args.model_folder],
            sample["prompt"],
            args.ollama_url,
            args.temperature,
            args.timeout_s,
            args.max_tokens,
        )
        new_rows.append(build_row(args.task, args.model_folder, sample, response_text, latency_s))

    merged_rows = dedupe_rows(existing_rows + new_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    json_lines = [json.dumps(row, ensure_ascii=True, separators=(",", ":")) for row in merged_rows]
    output_path.write_text("\n".join(json_lines) + "\n", encoding="utf-8")
    print(f"Merged {len(new_rows)} rerun rows into {output_path}")
    print(f"File now contains {len(merged_rows)} unique sample_ids.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
