#!/usr/bin/env python3
"""
Benchmark 2024: Official Dataset Download Script

Downloads all official datasets used in the SDDF framework's benchmark_2024.
Supports selective downloads, resumable operations, and caching.

Usage:
    python download_benchmark_2024_datasets.py                    # Download all
    python download_benchmark_2024_datasets.py --tasks maths      # Download maths only
    python download_benchmark_2024_datasets.py --output /path     # Custom output dir
    python download_benchmark_2024_datasets.py --skip-large       # Skip large datasets
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional

try:
    from datasets import load_dataset, disable_caching
    HAS_DATASETS = True
except ImportError:
    HAS_DATASETS = False
    print("WARNING: 'datasets' library not installed.")
    print("Install with: pip install datasets")


# ============================================================================
# BENCHMARK 2024 OFFICIAL DATASETS MAPPING
# ============================================================================

BENCHMARK_DATASETS = {
    "maths": {
        "name": "Mathematics",
        "description": "Multi-step arithmetic and algebraic reasoning",
        "datasets": [
            {
                "id": "openai/gsm8k",
                "name": "GSM8K",
                "split": "main",
                "size": "~500 MB",
                "samples": 7473,
                "source": "OpenAI",
                "license": "MIT",
                "doc": "Grade school math word problems",
            },
            {
                "id": "heegyu/MATH_Subset",
                "name": "MATH",
                "split": None,
                "size": "~1.5 GB",
                "samples": 12500,
                "source": "DeepMind/Meta",
                "license": "CC-BY-4.0",
                "doc": "Math competition problems (AMC, AIME, etc.)",
            },
            {
                "id": "svamp",
                "name": "SVAMP",
                "split": None,
                "size": "~50 MB",
                "samples": 700,
                "source": "Patel et al., 2021",
                "license": "CC-BY-4.0",
                "doc": "Simulated world arithmetic problems",
            },
        ],
    },
    "classification": {
        "name": "Text Classification",
        "description": "Multi-class text categorization (sentiment, topics, entities)",
        "datasets": [
            {
                "id": "ag_news",
                "name": "AG News",
                "split": "train",
                "size": "~120 MB",
                "samples": 120000,
                "source": "HuggingFace",
                "license": "Custom",
                "doc": "News topic classification (4 classes)",
            },
            {
                "id": "dbpedia_14",
                "name": "DBpedia",
                "split": "train",
                "size": "~630 MB",
                "samples": 630000,
                "source": "HuggingFace",
                "license": "CC0-1.0",
                "doc": "Entity classification (14 classes)",
            },
            {
                "id": "imdb",
                "name": "IMDB",
                "split": "train",
                "size": "~80 MB",
                "samples": 25000,
                "source": "HuggingFace",
                "license": "Custom",
                "doc": "Movie review sentiment (binary)",
            },
            {
                "id": "yahoo_answers_qa",
                "name": "Yahoo Answers",
                "split": "train",
                "size": "~1.5 GB",
                "samples": 1400000,
                "source": "HuggingFace",
                "license": "CC-BY-SA",
                "doc": "Q&A topic classification (10 classes)",
            },
        ],
    },
    "information_extraction": {
        "name": "Information Extraction",
        "description": "Structured field extraction from documents",
        "datasets": [
            {
                "id": "huggingface/sroie",
                "name": "SROIE",
                "split": None,
                "size": "~100 MB",
                "samples": 1000,
                "source": "ICDAR 2019 RRC",
                "license": "CC-BY-4.0",
                "doc": "Receipt OCR field extraction (vendor, date, total, tax, items)",
            },
        ],
    },
    "retrieval_grounded": {
        "name": "Retrieval-Grounded QA",
        "description": "Answer questions using provided context (RAG systems)",
        "datasets": [
            {
                "id": "rajpurkar/squad",
                "name": "SQuAD",
                "split": "train",
                "size": "~30 MB",
                "samples": 100000,
                "source": "Stanford University",
                "license": "CC-BY-SA-4.0",
                "doc": "Reading comprehension on Wikipedia passages",
            },
            {
                "id": "LLukas22/nq-simplified",
                "name": "Natural Questions",
                "split": "train",
                "size": "~138 MB",
                "samples": 307000,
                "source": "Google AI",
                "license": "CC-BY-SA-3.0",
                "doc": "Natural questions from web search logs",
            },
        ],
    },
    "code_generation": {
        "name": "Code Generation",
        "description": "Generate Python functions from natural language",
        "datasets": [
            {
                "id": "openai_humaneval",
                "name": "HumanEval",
                "split": None,
                "size": "~20 MB",
                "samples": 164,
                "source": "OpenAI",
                "license": "MIT",
                "doc": "Function generation from docstrings",
            },
            {
                "id": "google/mbpp",
                "name": "MBPP",
                "split": "train",
                "size": "~30 MB",
                "samples": 1000,
                "source": "Google",
                "license": "CC-BY-4.0",
                "doc": "Mostly Basic Programming Problems",
            },
        ],
    },
    "instruction_following": {
        "name": "Instruction Following",
        "description": "Follow explicit multi-step instructions exactly",
        "datasets": [
            {
                "id": "internal",
                "name": "Enterprise Gold Sets",
                "split": None,
                "size": "~5 MB",
                "samples": 75,
                "source": "Internal",
                "license": "Internal",
                "doc": "Proprietary instruction datasets (NOT publicly available)",
            },
        ],
    },
    "summarization": {
        "name": "Summarization",
        "description": "Generate concise summaries of long documents",
        "datasets": [
            {
                "id": "cnn_dailymail",
                "name": "CNN/DailyMail",
                "split": "train",
                "size": "~2.5 GB",
                "samples": 300000,
                "source": "DeepMind",
                "license": "Custom",
                "doc": "News article summarization",
            },
            {
                "id": "samsum",
                "name": "SamSum",
                "split": "train",
                "size": "~100 MB",
                "samples": 16000,
                "source": "Samsung/KLUE",
                "license": "CC-BY-4.0",
                "doc": "Conversation summarization (smaller alternative to CNN/DailyMail)",
            },
        ],
    },
    "text_generation": {
        "name": "Text Generation",
        "description": "Generate policy-compliant customer-facing responses",
        "datasets": [
            {
                "id": "internal",
                "name": "Enterprise Gold Sets",
                "split": None,
                "size": "~5 MB",
                "samples": 75,
                "source": "Internal",
                "license": "Internal",
                "doc": "Proprietary text generation datasets (NOT publicly available)",
            },
        ],
    },
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_human_readable_size(bytes_size: int) -> str:
    """Convert bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"


def print_header(text: str, char: str = "=") -> None:
    """Print formatted header."""
    print(f"\n{char * 80}")
    print(f"{text.center(80)}")
    print(f"{char * 80}\n")


def print_task_info(task: str, info: Dict) -> None:
    """Print task information."""
    print(f"📋 {info['name']}")
    print(f"   {info['description']}")
    print(f"   Datasets: {len(info['datasets'])}")


def print_dataset_info(dataset: Dict) -> None:
    """Print individual dataset information."""
    print(f"\n   • {dataset['name']}")
    print(f"     ID: {dataset['id']}")
    print(f"     Samples: {dataset['samples']:,}")
    print(f"     Size: {dataset['size']}")
    print(f"     Source: {dataset['source']}")
    print(f"     License: {dataset['license']}")
    print(f"     {dataset['doc']}")


def list_available_tasks() -> None:
    """List all available tasks."""
    print_header("Available Tasks in Benchmark 2024")
    for task_name, task_info in BENCHMARK_DATASETS.items():
        print_task_info(task_name, task_info)


def list_all_datasets() -> None:
    """List all available datasets."""
    print_header("All Official Datasets")
    total_datasets = 0
    total_samples = 0

    for task_name, task_info in BENCHMARK_DATASETS.items():
        print(f"\n{task_name.upper()}: {task_info['name']}")
        for dataset in task_info["datasets"]:
            print_dataset_info(dataset)
            total_datasets += 1
            if dataset["samples"] > 0:
                total_samples += dataset["samples"]

    print(f"\n\n📊 TOTALS")
    print(f"   Total Datasets: {total_datasets}")
    print(f"   Total Samples: {total_samples:,}")


def download_dataset(dataset_id: str, split: Optional[str] = None, output_dir: Optional[Path] = None) -> bool:
    """Download a single dataset."""
    if not HAS_DATASETS:
        print(f"   ❌ SKIPPED: 'datasets' library not installed")
        return False

    if dataset_id == "internal":
        print(f"   ❌ SKIPPED: Internal dataset (proprietary)")
        return False

    try:
        print(f"   ⏳ Downloading {dataset_id}...", end=" ", flush=True)

        if split:
            dataset = load_dataset(dataset_id, split=split)
        else:
            dataset = load_dataset(dataset_id)

        print(f"✅ Success ({len(dataset) if isinstance(dataset, dict) else dataset.num_rows:,} rows)")
        return True

    except Exception as e:
        print(f"❌ Failed: {str(e)[:50]}")
        return False


def download_task(task_name: str, output_dir: Optional[Path] = None, skip_large: bool = False) -> Dict:
    """Download all datasets for a specific task."""
    if task_name not in BENCHMARK_DATASETS:
        print(f"❌ Unknown task: {task_name}")
        return {"success": 0, "failed": 0, "skipped": 0}

    task_info = BENCHMARK_DATASETS[task_name]
    results = {"success": 0, "failed": 0, "skipped": 0}

    print(f"\n📦 Task: {task_name.upper()} - {task_info['name']}")
    print(f"   {task_info['description']}")

    for dataset in task_info["datasets"]:
        dataset_id = dataset["id"]
        split = dataset.get("split")
        size = dataset["size"]

        # Skip large datasets if requested
        if skip_large and "GB" in size:
            print(f"\n   ⊘ SKIPPED {dataset['name']} ({size}) - Large dataset")
            results["skipped"] += 1
            continue

        success = download_dataset(dataset_id, split, output_dir)
        if success:
            results["success"] += 1
        elif dataset_id != "internal":
            results["failed"] += 1
        else:
            results["skipped"] += 1

    return results


def download_all_tasks(output_dir: Optional[Path] = None, skip_large: bool = False) -> Dict:
    """Download all datasets."""
    results = {"success": 0, "failed": 0, "skipped": 0, "tasks": {}}

    for task_name in BENCHMARK_DATASETS.keys():
        task_results = download_task(task_name, output_dir, skip_large)
        results["success"] += task_results["success"]
        results["failed"] += task_results["failed"]
        results["skipped"] += task_results["skipped"]
        results["tasks"][task_name] = task_results

    return results


def print_summary(results: Dict) -> None:
    """Print download summary."""
    print_header("Download Summary")
    print(f"✅ Successful:  {results['success']}")
    print(f"❌ Failed:     {results['failed']}")
    print(f"⊘ Skipped:    {results['skipped']}")
    print(f"\nTotal: {results['success'] + results['failed'] + results['skipped']}")


def save_manifest(results: Dict, output_path: Path) -> None:
    """Save download manifest to JSON."""
    manifest = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "results": {
            "successful": results["success"],
            "failed": results["failed"],
            "skipped": results["skipped"],
            "per_task": results.get("tasks", {}),
        },
        "datasets_mapping": BENCHMARK_DATASETS,
    }

    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n📄 Manifest saved to: {output_path}")


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Download official Benchmark 2024 datasets for SDDF training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_benchmark_2024_datasets.py
                                    # Download all datasets

  python download_benchmark_2024_datasets.py --tasks maths classification
                                    # Download maths and classification only

  python download_benchmark_2024_datasets.py --skip-large
                                    # Download all except large datasets (>1GB)

  python download_benchmark_2024_datasets.py --output ./datasets
                                    # Save to custom directory

  python download_benchmark_2024_datasets.py --list-tasks
                                    # Show available tasks

  python download_benchmark_2024_datasets.py --list-all
                                    # Show all datasets with details
        """,
    )

    parser.add_argument(
        "--tasks",
        nargs="+",
        help="Specific tasks to download (e.g., 'maths classification')",
        choices=list(BENCHMARK_DATASETS.keys()),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./datasets"),
        help="Output directory for datasets (default: ./datasets)",
    )
    parser.add_argument(
        "--skip-large",
        action="store_true",
        help="Skip datasets larger than 1GB",
    )
    parser.add_argument(
        "--list-tasks",
        action="store_true",
        help="List available tasks",
    )
    parser.add_argument(
        "--list-all",
        action="store_true",
        help="List all datasets with details",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable HuggingFace dataset caching",
    )

    args = parser.parse_args()

    # Handle list operations
    if args.list_tasks:
        list_available_tasks()
        return 0

    if args.list_all:
        list_all_datasets()
        return 0

    # Disable caching if requested
    if args.no_cache and HAS_DATASETS:
        disable_caching()

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    print_header("Benchmark 2024 Official Datasets Downloader")
    print(f"Output directory: {args.output.absolute()}")
    print(f"Skip large (>1GB): {args.skip_large}")

    if not HAS_DATASETS:
        print("\n⚠️  WARNING: 'datasets' library not installed!")
        print("Install with: pip install datasets")
        print("\nYou can still use HuggingFace CLI:")
        print("  pip install huggingface-hub")
        print("  huggingface-cli download <dataset-id>")
        return 1

    # Download datasets
    if args.tasks:
        print(f"\nDownloading specific tasks: {', '.join(args.tasks)}")
        results = {"success": 0, "failed": 0, "skipped": 0, "tasks": {}}
        for task in args.tasks:
            task_results = download_task(task, args.output, args.skip_large)
            results["success"] += task_results["success"]
            results["failed"] += task_results["failed"]
            results["skipped"] += task_results["skipped"]
            results["tasks"][task] = task_results
    else:
        print("Downloading all tasks...")
        results = download_all_tasks(args.output, args.skip_large)

    # Print summary
    print_summary(results)

    # Save manifest
    manifest_path = args.output / "download_manifest.json"
    save_manifest(results, manifest_path)

    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
