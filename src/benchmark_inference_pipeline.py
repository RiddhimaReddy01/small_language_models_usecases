from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_QUERY_FIELDS = {
    "task",
    "bin",
    "sample_id",
    "model",
    "model_size",
    "backend",
    "timestamp",
    "status",
    "latency_sec",
    "prompt",
    "raw_output",
    "parsed_output",
    "valid",
    "error",
}

FAILURE_TAXONOMY = {
    "reasoning_failure": "Incorrect reasoning or task logic",
    "format_violation": "Output format does not match contract",
    "hallucination": "Output fabricates unsupported content",
    "truncation": "Output is incomplete or cut off",
    "refusal": "Model refused to answer",
    "invalid_parse": "Output cannot be parsed into the required schema",
    "timeout_runtime": "Inference timed out or crashed",
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


@dataclass
class QueryRecord:
    task: str | None
    bin: int
    sample_id: str
    model: str
    model_size: str
    backend: str
    timestamp: str
    status: str
    latency_sec: float
    prompt: str
    raw_output: str
    parsed_output: dict[str, Any] | list[Any] | None
    valid: bool
    error: str | None = None
    failure_category: str | None = None
    validation_checks: dict[str, Any] = field(default_factory=dict)
    validation_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def validate_required_fields(self) -> tuple[bool, list[str]]:
        payload = self.to_dict()
        optional_fields = {"error", "parsed_output"}
        missing = [field for field in REQUIRED_QUERY_FIELDS if field not in optional_fields and payload.get(field) is None]
        return len(missing) == 0, sorted(missing)


@dataclass
class RunManifest:
    task: str
    model_name: str
    total_samples: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_invalid: int = 0
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_start: str = field(default_factory=_timestamp)
    timestamp_end: str = field(default_factory=_timestamp)
    completion_by_bin: dict[int, dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["completion_by_bin"] = {str(key): value for key, value in self.completion_by_bin.items()}
        return payload

    def save(self, path: Path) -> None:
        self.timestamp_end = _timestamp()
        _write_json(path, self.to_dict())

    def coverage_report(self) -> dict[int, dict[str, Any]]:
        report: dict[int, dict[str, Any]] = {}
        for bin_id, counts in self.completion_by_bin.items():
            target = int(counts.get("target", 0) or 0)
            success = int(counts.get("success", 0) or 0)
            coverage = float((success / target) * 100.0) if target else 0.0
            report[bin_id] = {
                **counts,
                "coverage_pct": coverage,
                "is_complete": success >= target if target else False,
            }
        return report


@dataclass
class HardwareInfo:
    cpu_model: str
    cpu_count: int
    ram_gb: float
    platform: str
    platform_version: str
    python_version: str
    timestamp_captured: str
    ollama_version: str | None = None

    @classmethod
    def capture(cls, backend: str | None = None) -> "HardwareInfo":
        import os

        ollama_version = None
        if backend == "ollama":
            try:
                completed = subprocess.run(
                    ["ollama", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if completed.returncode == 0:
                    ollama_version = completed.stdout.strip() or completed.stderr.strip() or None
            except Exception:
                ollama_version = None
        ram_gb = 0.0
        try:
            if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in os.sysconf_names and "SC_PHYS_PAGES" in os.sysconf_names:
                ram_gb = (os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) / (1024 ** 3)
        except Exception:
            ram_gb = 0.0
        if ram_gb <= 0.0:
            ram_gb = 8.0
        return cls(
            cpu_model=platform.processor() or platform.machine() or "unknown",
            cpu_count=os.cpu_count() or 1,
            ram_gb=round(ram_gb, 2),
            platform=platform.system(),
            platform_version=platform.version(),
            python_version=platform.python_version(),
            timestamp_captured=_timestamp(),
            ollama_version=ollama_version,
        )

    def save(self, path: Path) -> None:
        _write_json(path, asdict(self))


@dataclass
class PromptConfig:
    task: str
    template_version: str
    system_prompt: str
    instruction_wrapper: str
    temperature: float
    top_p: float
    max_tokens: int
    stop_tokens: list[str]
    parsing_rules: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def save(self, path: Path) -> None:
        payload = self.to_dict()
        payload["config_hash"] = self.hash()
        _write_json(path, payload)


@dataclass
class DatasetManifest:
    task: str
    source_dataset: str
    selection_method: str
    binning_rule: str
    seed: int
    target_per_bin: dict[int, int]
    samples_included: dict[int, list[str]]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["target_per_bin"] = {str(key): value for key, value in self.target_per_bin.items()}
        payload["samples_included"] = {str(key): value for key, value in self.samples_included.items()}
        return payload

    def save(self, path: Path) -> None:
        _write_json(path, self.to_dict())


class BenchmarkInferenceEngine:
    def __init__(self, output_dir: str | Path | None = None):
        self.output_dir = Path(output_dir) if output_dir else None
        self.records: list[QueryRecord] = []
        self.run_manifest: RunManifest | None = None

    def log_query(self, record: QueryRecord) -> None:
        self.records.append(record)

    def set_run_manifest(self, manifest: RunManifest) -> None:
        self.run_manifest = manifest


def generate_sddf_ready_output(output_dir: str | Path) -> Path:
    output_root = Path(output_dir)
    source = output_root / "outputs.jsonl"
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_bin: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_bin.setdefault(int(row["bin"]), []).append(row)

    destination = output_root / "sddf_ready.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["bin", "n_samples", "success_rate", "avg_latency_sec"])
        writer.writeheader()
        for bin_id in sorted(by_bin):
            bucket = by_bin[bin_id]
            n_samples = len(bucket)
            success_rate = sum(1 for item in bucket if item.get("valid")) / n_samples if n_samples else 0.0
            avg_latency = sum(float(item.get("latency_sec", 0.0) or 0.0) for item in bucket) / n_samples if n_samples else 0.0
            writer.writerow(
                {
                    "bin": bin_id,
                    "n_samples": n_samples,
                    "success_rate": round(success_rate, 6),
                    "avg_latency_sec": round(avg_latency, 6),
                }
            )
    return destination
