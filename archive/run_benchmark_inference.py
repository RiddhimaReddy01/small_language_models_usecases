#!/usr/bin/env python3
"""
Benchmark Inference Orchestrator

Implements:
- Per-query structured metadata
- Immutable run metadata
- Hardware capture
- Prompt/version tracking
- Dataset manifest
- Failure taxonomy labels
- Completion summary by bin
- Validation after generation
- Graceful partial task completion
- Final report-generation hook
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from benchmark_inference_pipeline import (
    BenchmarkInferenceEngine,
    DatasetManifest,
    PromptConfig,
    generate_sddf_ready_output,
)


# ============================================================================
# ORCHESTRATOR
# ============================================================================

class BenchmarkOrchestrator:
    """Master orchestrator for benchmark runs"""

    def __init__(self, output_root: Path):
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.runs_log = self.output_root / "all_runs.jsonl"

    def run_task(
        self,
        task: str,
        model_name: str,
        examples_csv: Path,
        prompt_config: PromptConfig,
        dataset_manifest: DatasetManifest,
        backend: str = "ollama"
    ) -> Optional[Path]:
        """
        Run a complete task with full audit trail

        Args:
            task: Task name
            model_name: Model to use
            examples_csv: CSV with columns: sample_id, bin, text, model_size
            prompt_config: Prompt and decoding config
            dataset_manifest: Dataset selection manifest
            backend: "ollama" or "transformers"

        Returns:
            Path to run output directory
        """
        # Create task output dir
        task_output = self.output_root / task / model_name.replace("/", "_")
        task_output.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*70}")
        print(f"Task: {task} | Model: {model_name}")
        print(f"Output: {task_output}")
        print(f"{'='*70}\n")

        # Load examples
        try:
            examples_df = pd.read_csv(examples_csv)
        except Exception as e:
            print(f"ERROR: Failed to load examples: {e}")
            return None

        examples = examples_df[["sample_id", "bin", "text"]].to_dict("records")

        # Add model_size if available
        if "model_size" in examples_df.columns:
            for i, ex in enumerate(examples):
                ex["model_size"] = examples_df.iloc[i]["model_size"]
        else:
            for ex in examples:
                ex["model_size"] = "unknown"

        # Create engine
        try:
            engine = BenchmarkInferenceEngine(
                task=task,
                model_name=model_name,
                dataset_manifest=dataset_manifest,
                prompt_config=prompt_config,
                output_dir=task_output,
                backend=backend
            )
        except Exception as e:
            print(f"ERROR: Failed to initialize engine: {e}")
            return None

        # Check for incomplete runs (graceful resume)
        existing_outputs = task_output / "outputs.jsonl"
        completed_samples = set()
        if existing_outputs.exists():
            print(f"Resuming from checkpoint...")
            with open(existing_outputs) as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        completed_samples.add(record["sample_id"])
                    except:
                        pass

        # Filter to incomplete examples
        examples_todo = [ex for ex in examples if ex["sample_id"] not in completed_samples]
        print(f"Completed: {len(completed_samples)} | Todo: {len(examples_todo)}\n")

        if len(examples_todo) == 0:
            print("Task already complete. Skipping.")
            # Still finalize in case summary is missing
            all_records = self._load_existing_records(existing_outputs)
            if all_records:
                engine.finalize_run(pd.DataFrame(all_records))
            return task_output

        # Run inference
        try:
            results_df = engine.run_batch(examples_todo)
        except Exception as e:
            print(f"ERROR during inference: {e}")
            return None

        # Finalize
        try:
            # Load all records (completed + new)
            all_records = completed_samples
            with open(existing_outputs) as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        all_records.add(record)
                    except:
                        pass

            df_all = pd.DataFrame(list(all_records))
            engine.finalize_run(df_all)
        except Exception as e:
            print(f"ERROR during finalization: {e}")
            return None

        # Generate SDDF-ready output
        try:
            sddf_path = generate_sddf_ready_output(task_output)
            print(f"SDDF-ready output: {sddf_path}")
        except Exception as e:
            print(f"WARNING: Could not generate SDDF output: {e}")

        # Log run
        self._log_run(task, model_name, task_output)

        return task_output

    def _load_existing_records(self, outputs_path: Path) -> list[dict]:
        """Load all existing records from JSONL"""
        records = []
        if outputs_path.exists():
            with open(outputs_path) as f:
                for line in f:
                    try:
                        records.append(json.loads(line))
                    except:
                        pass
        return records

    def _log_run(self, task: str, model: str, output_dir: Path):
        """Append run to master log"""
        with open(self.runs_log, "a") as f:
            f.write(json.dumps({
                "task": task,
                "model": model,
                "output_dir": str(output_dir),
                "timestamp": pd.Timestamp.now().isoformat()
            }) + "\n")

    def generate_coverage_report(self) -> dict:
        """
        Generate overall coverage report across all tasks

        Returns:
            Dict with coverage summary by task and bin
        """
        report = {}

        for task_dir in self.output_root.iterdir():
            if not task_dir.is_dir() or task_dir.name.startswith("."):
                continue

            task_report = {}
            for model_dir in task_dir.iterdir():
                if not model_dir.is_dir():
                    continue

                run_manifest = model_dir / "run_manifest.json"
                if run_manifest.exists():
                    with open(run_manifest) as f:
                        manifest = json.load(f)
                        task_report[model_dir.name] = manifest["coverage_by_bin"]

            if task_report:
                report[task_dir.name] = task_report

        return report

    def print_coverage_report(self):
        """Print human-readable coverage report"""
        report = self.generate_coverage_report()

        print("\n" + "="*80)
        print("BENCHMARK COVERAGE REPORT")
        print("="*80)

        for task, models in report.items():
            print(f"\n{task}:")
            for model, bins in models.items():
                print(f"  {model}:")
                for bin_id, coverage in sorted(bins.items()):
                    pct = coverage["coverage_pct"]
                    status = "COMPLETE" if coverage["is_complete"] else f"{pct:.0f}%"
                    print(f"    Bin {bin_id}: {coverage['success']}/{coverage['target']} [{status}]")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Example usage"""

    # Configuration
    output_root = Path("./benchmark_output")
    backend = "ollama"

    # Create orchestrator
    orchestrator = BenchmarkOrchestrator(output_root)

    # Task configuration
    tasks_config = {
        "text_generation": {
            "model": "qwen2.5:0.5b",
            "examples_csv": Path("text_generation/rebin_results.csv"),
        },
        "code_generation": {
            "model": "qwen2.5-coder:0.5b",
            "examples_csv": Path("code_generation/rebin_results.csv"),
        },
        "classification": {
            "model": "phi3:mini",
            "examples_csv": Path("classification/rebin_results.csv"),
        },
        # ... add other tasks
    }

    # Run each task
    for task, config in tasks_config.items():
        # Create prompt config (task-specific)
        prompt_config = PromptConfig(
            task=task,
            template_version="v1.0",
            system_prompt="You are a helpful assistant.",
            instruction_wrapper="Q: {input}\nA:",
            temperature=0.7,
            top_p=0.9,
            max_tokens=200,
            stop_tokens=["\n\n", "Human:", "Assistant:"],
            parsing_rules={}
        )

        # Create dataset manifest
        dataset_manifest = DatasetManifest(
            task=task,
            source_dataset="benchmark_2024",
            selection_method="stratified_by_difficulty",
            binning_rule="quantile(5)",
            seed=42,
            target_per_bin={0: 15, 1: 15, 2: 15, 3: 15, 4: 15},
            samples_included={0: [], 1: [], 2: [], 3: [], 4: []}  # Filled from CSV
        )

        # Run task
        orchestrator.run_task(
            task=task,
            model_name=config["model"],
            examples_csv=config["examples_csv"],
            prompt_config=prompt_config,
            dataset_manifest=dataset_manifest,
            backend=backend
        )

    # Print coverage report
    orchestrator.print_coverage_report()


if __name__ == "__main__":
    main()
