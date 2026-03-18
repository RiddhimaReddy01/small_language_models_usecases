#!/usr/bin/env python3
"""
Robust Batch Inference Pipeline
- CPU + Quantized models only
- Fixed model per task
- Auto-checkpoint & resume
- No manual intervention
- Offline (Ollama or local transformers)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import hashlib

import pandas as pd


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class InferenceConfig:
    """Configuration for a batch inference job"""
    task: str
    model_name: str
    n_examples: int
    max_retries: int = 3
    retry_delay: float = 5.0  # seconds
    checkpoint_interval: int = 1  # save after every N examples
    timeout_per_example: float = 60.0

    # Parallelism by model size
    parallelism_map: dict[str, int] = None

    def __post_init__(self):
        if self.parallelism_map is None:
            self.parallelism_map = {
                "Qwen/Qwen2.5-0.5B-Instruct": 4,      # Small: higher parallelism
                "meta-llama/Llama-3.2-1B-Instruct": 2,  # Medium
                "microsoft/Phi-3-mini-4k": 2,
                "Qwen/Qwen2.5-1.5B": 1,                 # Large: lower parallelism
                "Qwen/Qwen2.5-3B": 1,
                "mistralai/Mistral-7B": 1,              # Very large: CPU only
            }

    @property
    def parallelism(self) -> int:
        """Get parallelism level for this model"""
        return self.parallelism_map.get(self.model_name, 1)


# ============================================================================
# CHECKPOINT & RESUME
# ============================================================================

@dataclass
class InferenceCheckpoint:
    """Checkpoint for resumable inference"""
    task: str
    model: str
    timestamp: str
    total_processed: int
    total_errors: int
    completed_example_ids: list[str]
    last_error: Optional[str] = None

    def save(self, checkpoint_dir: Path) -> Path:
        """Save checkpoint to disk"""
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        path = checkpoint_dir / f"{self.task}_{self.model}.checkpoint.json"
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)
        return path

    @classmethod
    def load(cls, checkpoint_dir: Path, task: str, model: str) -> Optional[InferenceCheckpoint]:
        """Load checkpoint from disk"""
        path = checkpoint_dir / f"{task}_{model}.checkpoint.json"
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        return cls(**data)

    def update(self, example_id: str, success: bool, error: Optional[str] = None):
        """Update checkpoint with result"""
        self.timestamp = datetime.now().isoformat()
        if success:
            self.completed_example_ids.append(example_id)
            self.total_processed += 1
        else:
            self.total_errors += 1
            self.last_error = error


# ============================================================================
# QUERY DEDUPLICATION
# ============================================================================

class QueryManifest:
    """Track completed queries to avoid re-running"""

    def __init__(self, manifest_path: Path):
        self.path = manifest_path
        self.manifest = self._load()

    def _load(self) -> dict:
        """Load manifest from disk"""
        if not self.path.exists():
            return {}
        with open(self.path) as f:
            return json.load(f)

    def save(self):
        """Save manifest to disk"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.manifest, f, indent=2)

    def query_hash(self, task: str, model: str, example_id: str, text: str) -> str:
        """Generate hash of query to detect duplicates"""
        key = f"{task}:{model}:{example_id}:{text}"
        return hashlib.md5(key.encode()).hexdigest()

    def is_completed(self, task: str, model: str, example_id: str, text: str) -> bool:
        """Check if query was already completed"""
        qhash = self.query_hash(task, model, example_id, text)
        return qhash in self.manifest

    def mark_completed(self, task: str, model: str, example_id: str, text: str, result: dict):
        """Mark query as completed"""
        qhash = self.query_hash(task, model, example_id, text)
        self.manifest[qhash] = {
            "task": task,
            "model": model,
            "example_id": example_id,
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        self.save()


# ============================================================================
# INFERENCE ENGINE
# ============================================================================

class BatchInferenceEngine:
    """Main inference engine with checkpointing & resume"""

    def __init__(
        self,
        config: InferenceConfig,
        output_dir: Path,
        checkpoint_dir: Path,
        backend: str = "ollama"  # "ollama" or "transformers"
    ):
        self.config = config
        self.output_dir = Path(output_dir)
        self.checkpoint_dir = Path(checkpoint_dir)
        self.backend = backend
        self.logger = self._setup_logging()
        self.manifest = QueryManifest(output_dir / "manifest.json")
        self.checkpoint = self._load_or_create_checkpoint()
        self._init_inference_client()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging with file & console output"""
        logger = logging.getLogger(f"{self.config.task}_{self.config.model_name}")
        logger.setLevel(logging.DEBUG)

        # Create logs directory
        log_dir = self.output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # File handler
        fh = logging.FileHandler(log_dir / f"{self.config.task}_{self.config.model_name}.log")
        fh.setLevel(logging.DEBUG)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    def _init_inference_client(self):
        """Initialize inference client (Ollama or Transformers)"""
        if self.backend == "ollama":
            self._init_ollama()
        elif self.backend == "transformers":
            self._init_transformers()
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def _init_ollama(self):
        """Initialize Ollama client"""
        try:
            import ollama
            self.ollama_client = ollama.Client()
            # Verify model exists
            models = self.ollama_client.list()
            model_names = [m["name"] for m in models.get("models", [])]
            if self.config.model_name not in model_names:
                raise ValueError(
                    f"Model {self.config.model_name} not found in Ollama. "
                    f"Available: {model_names}"
                )
            self.logger.info(f"Ollama initialized with model {self.config.model_name}")
        except ImportError:
            raise ImportError("Ollama Python client not installed. Run: pip install ollama")

    def _init_transformers(self):
        """Initialize Transformers pipeline"""
        from transformers import pipeline

        try:
            self.pipeline = pipeline(
                "text-generation",
                model=self.config.model_name,
                device="cpu",  # Force CPU
                torch_dtype=None  # Use default (float32 for CPU)
            )
            self.logger.info(f"Transformers initialized with model {self.config.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize transformers: {e}")
            raise

    def _load_or_create_checkpoint(self) -> InferenceCheckpoint:
        """Load checkpoint or create new one"""
        existing = InferenceCheckpoint.load(
            self.checkpoint_dir,
            self.config.task,
            self.config.model_name
        )

        if existing:
            self.logger.info(
                f"Resuming from checkpoint: {len(existing.completed_example_ids)} "
                f"completed, {existing.total_errors} errors"
            )
            return existing

        checkpoint = InferenceCheckpoint(
            task=self.config.task,
            model=self.config.model_name,
            timestamp=datetime.now().isoformat(),
            total_processed=0,
            total_errors=0,
            completed_example_ids=[]
        )
        return checkpoint

    def _infer_ollama(self, text: str) -> dict[str, Any]:
        """Run inference via Ollama"""
        response = self.ollama_client.generate(
            model=self.config.model_name,
            prompt=text,
            stream=False,
            options={
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 100
            }
        )
        return {
            "output": response.get("response", ""),
            "model": self.config.model_name,
            "timestamp": datetime.now().isoformat(),
            "backend": "ollama"
        }

    def _infer_transformers(self, text: str) -> dict[str, Any]:
        """Run inference via Transformers"""
        outputs = self.pipeline(
            text,
            max_new_tokens=100,
            temperature=0.7,
            top_p=0.9,
            do_sample=True
        )
        return {
            "output": outputs[0].get("generated_text", ""),
            "model": self.config.model_name,
            "timestamp": datetime.now().isoformat(),
            "backend": "transformers"
        }

    def _run_inference_with_retry(self, example_id: str, text: str) -> tuple[bool, Optional[dict]]:
        """Run inference with automatic retry"""
        for attempt in range(self.config.max_retries):
            try:
                if self.backend == "ollama":
                    result = self._infer_ollama(text)
                else:
                    result = self._infer_transformers(text)

                return True, result

            except Exception as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.config.max_retries} failed for "
                    f"{example_id}: {str(e)}"
                )

                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    error_msg = f"Failed after {self.config.max_retries} retries: {str(e)}"
                    self.logger.error(f"{example_id}: {error_msg}")
                    return False, None

    def run_batch(self, examples: list[dict]) -> pd.DataFrame:
        """
        Run inference on batch of examples

        Args:
            examples: List of dicts with 'example_id' and 'text' keys

        Returns:
            DataFrame with results
        """
        results = []

        for i, example in enumerate(examples):
            example_id = example.get("example_id", f"example_{i}")
            text = example.get("text", "")

            # Skip if already completed
            if self.manifest.is_completed(self.config.task, self.config.model_name, example_id, text):
                self.logger.info(f"Skipping {example_id} (already completed)")
                continue

            # Skip if in current checkpoint
            if example_id in self.checkpoint.completed_example_ids:
                self.logger.debug(f"Skipping {example_id} (in current checkpoint)")
                continue

            self.logger.info(f"Processing {example_id} ({i+1}/{len(examples)})")

            # Run inference
            success, result = self._run_inference_with_retry(example_id, text)

            if success:
                result["example_id"] = example_id
                result["success"] = True
                results.append(result)

                # Update checkpoint
                self.checkpoint.update(example_id, success=True)

                # Mark in manifest
                self.manifest.mark_completed(
                    self.config.task,
                    self.config.model_name,
                    example_id,
                    text,
                    result
                )

                # Checkpoint interval
                if len(results) % self.config.checkpoint_interval == 0:
                    self.checkpoint.save(self.checkpoint_dir)
                    self.logger.info(
                        f"Checkpoint saved: {len(results)} results, "
                        f"{self.checkpoint.total_errors} errors"
                    )
            else:
                result = {
                    "example_id": example_id,
                    "success": False,
                    "error": "Max retries exceeded",
                    "timestamp": datetime.now().isoformat()
                }
                results.append(result)
                self.checkpoint.update(example_id, success=False, error=result["error"])

        # Final checkpoint
        self.checkpoint.save(self.checkpoint_dir)
        self.logger.info(
            f"Batch complete: {len(results)} results, "
            f"{self.checkpoint.total_errors} errors"
        )

        return pd.DataFrame(results)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def run_inference_job(
    task: str,
    model_name: str,
    examples_csv: Path,
    output_dir: Path,
    backend: str = "ollama",
    checkpoint_dir: Optional[Path] = None
) -> Path:
    """
    Run a complete inference job

    Args:
        task: Task name (e.g., "text_generation")
        model_name: Model to use (e.g., "Qwen/Qwen2.5-0.5B-Instruct")
        examples_csv: Path to CSV with example_id and text columns
        output_dir: Directory to save results
        backend: "ollama" or "transformers"
        checkpoint_dir: Directory for checkpoints (default: output_dir/.checkpoints)

    Returns:
        Path to results CSV
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if checkpoint_dir is None:
        checkpoint_dir = output_dir / ".checkpoints"

    # Load examples
    examples_df = pd.read_csv(examples_csv)
    examples = examples_df[["example_id", "text"]].to_dict("records")

    # Create config
    config = InferenceConfig(
        task=task,
        model_name=model_name,
        n_examples=len(examples)
    )

    # Run engine
    engine = BatchInferenceEngine(config, output_dir, checkpoint_dir, backend=backend)
    results_df = engine.run_batch(examples)

    # Save results
    results_path = output_dir / f"{task}_{model_name.replace('/', '_')}_results.csv"
    results_df.to_csv(results_path, index=False)

    print(f"\nResults saved to: {results_path}")
    print(f"Processed: {len(results_df)} examples")
    print(f"Checkpoint: {checkpoint_dir}")
    print(f"Manifest: {output_dir / 'manifest.json'}")

    return results_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python batch_inference_pipeline.py <task> <model> <examples_csv> [output_dir] [backend]")
        print("\nExample:")
        print("  python batch_inference_pipeline.py text_generation \\")
        print("    'Qwen/Qwen2.5-0.5B-Instruct' \\")
        print("    examples.csv \\")
        print("    ./output \\")
        print("    ollama")
        sys.exit(1)

    task = sys.argv[1]
    model = sys.argv[2]
    examples_csv = Path(sys.argv[3])
    output_dir = Path(sys.argv[4]) if len(sys.argv) > 4 else Path(f"./{task}_output")
    backend = sys.argv[5] if len(sys.argv) > 5 else "ollama"

    run_inference_job(task, model, examples_csv, output_dir, backend=backend)
