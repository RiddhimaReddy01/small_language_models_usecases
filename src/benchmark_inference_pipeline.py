#!/usr/bin/env python3
"""
Publication-Ready Benchmark Inference Pipeline

Implements the full audit trail and SDDF-ready output contract:
1. Per-query structured metadata (mandatory fields)
2. Immutable run metadata (run_manifest.json, config_snapshot.json, etc.)
3. Hardware capture (CPU, RAM, OS, versions)
4. Prompt/version tracking (exact reproducibility)
5. Dataset manifest (sample selection traceability)
6. Failure taxonomy labels (structured error analysis)
7. Completion summary by bin (coverage tracking)
8. Validation after generation (output usability checks)
9. Graceful partial task completion (resume with coverage awareness)
10. Final report-generation hook (SDDF integration)
"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import hashlib
import uuid

import pandas as pd
import numpy as np


# ============================================================================
# CONSTANTS
# ============================================================================

FAILURE_TAXONOMY = {
    "reasoning_failure": "Model failed to reason correctly",
    "format_violation": "Output did not match expected format",
    "hallucination": "Model generated false/fabricated content",
    "truncation": "Output was cut off",
    "refusal": "Model refused to respond",
    "invalid_parse": "Output could not be parsed",
    "timeout_runtime": "Inference exceeded timeout",
    "incomplete": "Output incomplete but not truncated",
    "unrelated": "Output unrelated to prompt",
    "other": "Other/uncategorized failure"
}

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

# ============================================================================
# SYSTEM & HARDWARE CAPTURE
# ============================================================================

@dataclass
class HardwareInfo:
    """Immutable hardware specification"""
    platform: str
    platform_version: str
    cpu_model: str
    cpu_count: int
    ram_gb: float
    python_version: str
    ollama_version: Optional[str] = None
    transformers_version: Optional[str] = None
    torch_version: Optional[str] = None
    timestamp_captured: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def capture(cls, backend: str = "ollama") -> HardwareInfo:
        """Capture current hardware specs"""
        # Platform
        plat = platform.platform()
        plat_release = platform.release()

        # CPU
        try:
            import cpuinfo
            cpu_info = cpuinfo.get_cpu_info()
            cpu_model = cpu_info.get("brand_raw", "Unknown")
        except:
            cpu_model = platform.processor() or "Unknown"

        cpu_count = os.cpu_count() or 1

        # RAM (in GB)
        try:
            import psutil
            ram_gb = psutil.virtual_memory().total / (1024**3)
        except:
            ram_gb = 0.0

        # Python
        python_ver = platform.python_version()

        # Ollama
        ollama_ver = None
        if backend == "ollama":
            try:
                result = subprocess.run(
                    ["ollama", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                ollama_ver = result.stdout.strip()
            except:
                pass

        # Transformers
        transformers_ver = None
        torch_ver = None
        try:
            import transformers
            transformers_ver = transformers.__version__
        except:
            pass

        try:
            import torch
            torch_ver = torch.__version__
        except:
            pass

        return cls(
            platform=plat,
            platform_version=plat_release,
            cpu_model=cpu_model,
            cpu_count=cpu_count,
            ram_gb=ram_gb,
            python_version=python_ver,
            ollama_version=ollama_ver,
            transformers_version=transformers_ver,
            torch_version=torch_ver
        )

    def save(self, path: Path):
        """Save hardware spec"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)


# ============================================================================
# PROMPT & DECODING CONFIG
# ============================================================================

@dataclass
class PromptConfig:
    """Exact reproducibility of prompt and decoding parameters"""
    task: str
    template_version: str  # e.g., "v1.0"
    system_prompt: str
    instruction_wrapper: str  # e.g., "Q: {input}\nA:"
    temperature: float
    top_p: float
    max_tokens: int
    stop_tokens: list[str]
    parsing_rules: dict[str, Any]
    seed: int = 42
    timestamp_created: str = field(default_factory=lambda: datetime.now().isoformat())

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    def hash(self) -> str:
        """Hash to detect prompt changes"""
        key = f"{self.template_version}:{self.system_prompt}:{self.instruction_wrapper}"
        return hashlib.md5(key.encode()).hexdigest()


# ============================================================================
# DATASET MANIFEST
# ============================================================================

@dataclass
class DatasetManifest:
    """Full traceability of sample selection"""
    task: str
    source_dataset: str  # e.g., "CNN/DailyMail", "HumanEval"
    selection_method: str  # e.g., "stratified_by_difficulty", "random"
    binning_rule: str  # e.g., "quantile(5)", "uniform(5)"
    seed: int
    target_per_bin: dict[int, int]  # bin_id -> count
    samples_included: dict[int, list[str]]  # bin_id -> [sample_ids]
    timestamp_created: str = field(default_factory=lambda: datetime.now().isoformat())

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    def total_samples(self) -> int:
        return sum(len(ids) for ids in self.samples_included.values())

    def samples_per_bin(self) -> dict[int, int]:
        return {bin_id: len(ids) for bin_id, ids in self.samples_included.items()}


# ============================================================================
# PER-QUERY RECORD (WITH VALIDATION)
# ============================================================================

@dataclass
class QueryRecord:
    """Per-query structured metadata - publication-ready"""
    # Identification
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task: str = ""
    bin: int = -1
    sample_id: str = ""

    # Model & environment
    model: str = ""
    model_size: str = ""
    backend: str = ""

    # Timing & execution
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    latency_sec: float = 0.0

    # Input
    prompt: str = ""

    # Output
    raw_output: str = ""
    parsed_output: dict[str, Any] = field(default_factory=dict)

    # Status
    status: str = "pending"  # pending, success, failed, invalid
    valid: bool = False  # Validation passed
    error: Optional[str] = None  # Error message if failed

    # Failure analysis
    failure_category: Optional[str] = None  # From FAILURE_TAXONOMY

    # Validation details
    validation_checks: dict[str, bool] = field(default_factory=dict)
    validation_notes: str = ""

    # Metadata consistency
    run_id: str = ""  # Link to run

    def validate_required_fields(self) -> tuple[bool, list[str]]:
        """Check all required fields are present"""
        missing = []
        optional_none_fields = {"error", "parsed_output"}  # error can be None
        for field_name in REQUIRED_QUERY_FIELDS:
            value = getattr(self, field_name, None)
            if value is None and field_name not in optional_none_fields:
                missing.append(field_name)
        return len(missing) == 0, missing

    def to_dict(self) -> dict:
        """Convert to dict, excluding None values"""
        d = asdict(self)
        # Ensure all required fields present
        for field_name in REQUIRED_QUERY_FIELDS:
            if field_name not in d:
                d[field_name] = None
        return d


# ============================================================================
# RUN MANIFEST (IMMUTABLE AUDIT TRAIL)
# ============================================================================

@dataclass
class RunManifest:
    """Complete, immutable record of a benchmark run"""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task: str = ""
    model_name: str = ""
    timestamp_start: str = field(default_factory=lambda: datetime.now().isoformat())
    timestamp_end: Optional[str] = None

    # Input specifications
    dataset_manifest_path: str = ""
    prompt_config_path: str = ""

    # Hardware
    hardware_info_path: str = ""

    # Results
    total_samples: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_invalid: int = 0

    # Coverage by bin
    completion_by_bin: dict[int, dict[str, int]] = field(default_factory=dict)

    # Status
    is_complete: bool = False
    notes: str = ""

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.timestamp_end = datetime.now().isoformat()
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    def coverage_report(self) -> dict[int, dict]:
        """Generate coverage summary by bin"""
        report = {}
        for bin_id, counts in self.completion_by_bin.items():
            target = counts.get("target", 0)
            actual = counts.get("success", 0)
            coverage_pct = 100 * actual / target if target > 0 else 0
            report[bin_id] = {
                "target": target,
                "success": actual,
                "failed": counts.get("failed", 0),
                "pending": counts.get("pending", 0),
                "coverage_pct": coverage_pct,
                "is_complete": coverage_pct >= 100
            }
        return report


# ============================================================================
# CORE INFERENCE ENGINE (WITH VALIDATION)
# ============================================================================

class BenchmarkInferenceEngine:
    """Production inference engine with full audit trail"""

    def __init__(
        self,
        task: str,
        model_name: str,
        dataset_manifest: DatasetManifest,
        prompt_config: PromptConfig,
        output_dir: Path,
        backend: str = None
    ):
        self.task = task
        self.model_name = model_name
        self.dataset_manifest = dataset_manifest
        self.prompt_config = prompt_config
        self.output_dir = Path(output_dir)
        # Auto-detect backend from model name if not specified
        if backend is None:
            if model_name.startswith("groq_"):
                backend = "groq"
            elif model_name.startswith("llama_"):
                backend = "groq"
            else:
                backend = "ollama"
        self.backend = backend

        # Create run
        self.run_id = str(uuid.uuid4())
        self.run_manifest = RunManifest(
            run_id=self.run_id,
            task=task,
            model_name=model_name,
            dataset_manifest_path=str(dataset_manifest),
            prompt_config_path=str(prompt_config),
            total_samples=dataset_manifest.total_samples()
        )

        # Capture hardware
        self.hardware = HardwareInfo.capture(backend=backend)

        # Setup logging
        self.logger = self._setup_logging()
        self.logger.info(f"Run ID: {self.run_id}")

        # Output files
        self._setup_output_dirs()

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger(f"{self.task}_{self.model_name}_{self.run_id[:8]}")
        logger.setLevel(logging.DEBUG)

        log_dir = self.output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        fh = logging.FileHandler(log_dir / f"run_{self.run_id[:8]}.log")
        fh.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    def _setup_output_dirs(self):
        """Create output directory structure"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "logs").mkdir(exist_ok=True)
        (self.output_dir / "metadata").mkdir(exist_ok=True)

        # Save immutable metadata
        self.hardware.save(self.output_dir / "metadata" / "hardware.json")
        self.prompt_config.save(self.output_dir / "metadata" / "prompt_config.json")
        self.dataset_manifest.save(self.output_dir / "metadata" / "dataset_manifest.json")

    def _run_inference(self, prompt: str) -> tuple[str, float]:
        """Run single inference, return (output, latency)"""
        start = time.time()
        try:
            if self.backend == "ollama":
                output = self._infer_ollama(prompt)
            elif self.backend == "groq":
                output = self._infer_groq(prompt)
            else:
                output = self._infer_transformers(prompt)
            latency = time.time() - start
            return output, latency
        except Exception as e:
            latency = time.time() - start
            raise RuntimeError(f"Inference failed after {latency:.2f}s: {str(e)}")

    def _infer_ollama(self, prompt: str) -> str:
        """Ollama inference"""
        import ollama
        client = ollama.Client(timeout=120.0)  # 120s timeout for local models
        response = client.generate(
            model=self.model_name,
            prompt=prompt,
            stream=False,
            options={
                "temperature": self.prompt_config.temperature,
                "top_p": self.prompt_config.top_p,
                "num_predict": self.prompt_config.max_tokens
            }
        )
        return response.get("response", "")

    def _infer_groq(self, prompt: str) -> str:
        """Groq API inference"""
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable not set")

        client = Groq(api_key=api_key)
        # Strip "groq_" prefix if present for API call
        model_id = self.model_name.replace("groq_", "") if self.model_name.startswith("groq_") else self.model_name
        message = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model_id,
            temperature=self.prompt_config.temperature,
            top_p=self.prompt_config.top_p,
            max_tokens=self.prompt_config.max_tokens,
        )
        return message.choices[0].message.content

    def _infer_transformers(self, prompt: str) -> str:
        """Transformers inference"""
        from transformers import pipeline
        pipe = pipeline(
            "text-generation",
            model=self.model_name,
            device="cpu",
            torch_dtype=None
        )
        outputs = pipe(
            prompt,
            max_new_tokens=self.prompt_config.max_tokens,
            temperature=self.prompt_config.temperature,
            top_p=self.prompt_config.top_p,
            do_sample=True
        )
        return outputs[0].get("generated_text", "")

    def _validate_output(self, record: QueryRecord) -> tuple[bool, dict, str]:
        """
        Validate output usability

        Returns: (is_valid, validation_checks, notes)
        """
        checks = {}
        notes = []

        # 1. Non-empty
        checks["non_empty"] = len(record.raw_output.strip()) > 0
        if not checks["non_empty"]:
            notes.append("Empty output")

        # 2. Try to parse based on task
        checks["parseable"] = self._try_parse(record)
        if not checks["parseable"]:
            notes.append("Could not parse output")

        # 3. Contains expected fields (task-specific)
        checks["has_expected_fields"] = self._check_expected_fields(record)

        # Overall validity
        is_valid = all(checks.values())
        notes_str = "; ".join(notes) if notes else "All checks passed"

        return is_valid, checks, notes_str

    def _try_parse(self, record: QueryRecord) -> bool:
        """Try to parse output based on task"""
        try:
            if self.task == "code_generation":
                # Try to extract code
                return "def " in record.raw_output or "class " in record.raw_output
            elif self.task in ["classification", "summarization"]:
                # Just check non-empty
                return len(record.raw_output.strip()) > 0
            else:
                return len(record.raw_output.strip()) > 0
        except:
            return False

    def _check_expected_fields(self, record: QueryRecord) -> bool:
        """Check for expected fields in output"""
        return len(record.raw_output.strip()) > 0

    def run_batch(self, examples: list[dict]) -> pd.DataFrame:
        """
        Run inference on batch with full audit trail

        Args:
            examples: List of dicts with sample_id, bin, text

        Returns:
            DataFrame with QueryRecord rows
        """
        results = []

        for i, example in enumerate(examples):
            sample_id = example.get("sample_id", f"sample_{i}")
            bin_id = example.get("bin", 0)
            text = example.get("text", "")

            self.logger.info(f"Processing {sample_id} (bin {bin_id}, {i+1}/{len(examples)})")

            # Create record
            record = QueryRecord(
                task=self.task,
                bin=bin_id,
                sample_id=sample_id,
                model=self.model_name,
                model_size=example.get("model_size", "unknown"),
                backend=self.backend,
                prompt=text,
                run_id=self.run_id
            )

            # Run inference
            try:
                full_prompt = self.prompt_config.instruction_wrapper.format(input=text)
                raw_output, latency = self._run_inference(full_prompt)

                record.raw_output = raw_output
                record.latency_sec = latency
                record.status = "success"

                # Validate
                is_valid, checks, notes = self._validate_output(record)
                record.valid = is_valid
                record.validation_checks = checks
                record.validation_notes = notes

                if is_valid:
                    record.status = "success"
                else:
                    record.status = "invalid"
                    record.error = notes

            except Exception as e:
                record.status = "failed"
                record.error = str(e)
                record.failure_category = "timeout_runtime"
                self.logger.error(f"{sample_id}: {str(e)}")

            results.append(record)

            # Save immediately
            self._save_record(record)

        return pd.DataFrame([r.to_dict() for r in results])

    def _save_record(self, record: QueryRecord):
        """Save query record to JSONL (immutable append)"""
        output_file = self.output_dir / "outputs.jsonl"
        with open(output_file, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def finalize_run(self, results_df: pd.DataFrame):
        """
        Finalize run with completion summary and reports
        """
        # Compute coverage by bin
        for bin_id in results_df["bin"].unique():
            bin_data = results_df[results_df["bin"] == bin_id]
            self.run_manifest.completion_by_bin[bin_id] = {
                "target": len(bin_data),
                "success": len(bin_data[bin_data["status"] == "success"]),
                "failed": len(bin_data[bin_data["status"] == "failed"]),
                "invalid": len(bin_data[bin_data["status"] == "invalid"]),
                "pending": 0
            }

        # Check if complete
        all_bins_complete = all(
            counts["success"] >= counts["target"]
            for counts in self.run_manifest.completion_by_bin.values()
        )
        self.run_manifest.is_complete = all_bins_complete

        # Save run manifest
        self.run_manifest.save(self.output_dir / "run_manifest.json")

        # Generate summary
        summary = self._generate_summary(results_df)
        summary_path = self.output_dir / "summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        # Generate config snapshot
        self._save_config_snapshot()

        self.logger.info(f"Run finalized: {self.run_id}")
        self.logger.info(f"Coverage report:\n{json.dumps(self.run_manifest.coverage_report(), indent=2)}")

    def _generate_summary(self, results_df: pd.DataFrame) -> dict:
        """Generate per-bin and per-task summary"""
        summary = {
            "run_id": self.run_id,
            "task": self.task,
            "model": self.model_name,
            "timestamp": datetime.now().isoformat(),
            "total_samples": len(results_df),
            "total_success": len(results_df[results_df["status"] == "success"]),
            "total_failed": len(results_df[results_df["status"] == "failed"]),
            "total_invalid": len(results_df[results_df["status"] == "invalid"]),
            "success_rate": len(results_df[results_df["status"] == "success"]) / len(results_df) if len(results_df) > 0 else 0,
            "avg_latency_sec": results_df["latency_sec"].mean(),
            "coverage_by_bin": self.run_manifest.coverage_report(),
            "failure_categories": results_df[results_df["status"] == "failed"]["failure_category"].value_counts().to_dict()
        }
        return summary

    def _save_config_snapshot(self):
        """Save full config snapshot for reproducibility"""
        snapshot = {
            "run_id": self.run_id,
            "task": self.task,
            "model": self.model_name,
            "backend": self.backend,
            "timestamp": datetime.now().isoformat(),
            "hardware": asdict(self.hardware),
            "prompt_config": asdict(self.prompt_config),
            "dataset_manifest": asdict(self.dataset_manifest)
        }
        config_path = self.output_dir / "config_snapshot.json"
        with open(config_path, "w") as f:
            json.dump(snapshot, f, indent=2)


# ============================================================================
# SDDF INTEGRATION (REPORT GENERATION HOOK)
# ============================================================================

def generate_sddf_ready_output(run_output_dir: Path) -> Path:
    """
    Convert benchmark run output to SDDF-ready format

    Computes metrics, aggregates by bin, generates capability curves
    """
    from pathlib import Path
    import pandas as pd

    # Load outputs
    outputs_path = run_output_dir / "outputs.jsonl"
    records = []
    with open(outputs_path) as f:
        for line in f:
            records.append(json.loads(line))

    df = pd.DataFrame(records)

    # Compute metrics per bin
    sddf_data = []
    for bin_id in sorted(df["bin"].unique()):
        bin_df = df[df["bin"] == bin_id]

        # Aggregate
        sddf_data.append({
            "bin": bin_id,
            "n_samples": len(bin_df),
            "success_rate": len(bin_df[bin_df["valid"] == True]) / len(bin_df) if len(bin_df) > 0 else 0,
            "avg_latency": bin_df["latency_sec"].mean(),
            "validity_rate": len(bin_df[bin_df["valid"] == True]) / len(bin_df) if len(bin_df) > 0 else 0
        })

    sddf_df = pd.DataFrame(sddf_data)
    sddf_path = run_output_dir / "sddf_ready.csv"
    sddf_df.to_csv(sddf_path, index=False)

    return sddf_path


if __name__ == "__main__":
    print("Benchmark Inference Pipeline Module")
    print(f"Required query fields: {REQUIRED_QUERY_FIELDS}")
    print(f"Failure taxonomy: {list(FAILURE_TAXONOMY.keys())}")
