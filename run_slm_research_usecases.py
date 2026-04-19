#!/usr/bin/env python3
"""
Run SDDF Pipeline on SLM Research Project Named Use Cases

Maps UC1-UC8 to:
- UC1: SMS Threat Detection
- UC2: Invoice Data Extraction
- UC3: Support Ticket Routing
- UC4: Product Review Sentiment Analysis
- UC5: Code Review Assistance
- UC6: Clinical Triage Assistance
- UC7: Legal Contract Analysis
- UC8: Financial Report Drafting
"""

import json
import csv
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# USE CASE MAPPING
# ============================================================================

UC_MAPPING = {
    "UC1": {"name": "SMS Threat Detection", "task_family": "classification"},
    "UC2": {"name": "Invoice Data Extraction", "task_family": "information_extraction"},
    "UC3": {"name": "Support Ticket Routing", "task_family": "classification"},
    "UC4": {"name": "Product Review Sentiment Analysis", "task_family": "classification"},
    "UC5": {"name": "Code Review Assistance", "task_family": "code_generation"},
    "UC6": {"name": "Clinical Triage Assistance", "task_family": "classification"},
    "UC7": {"name": "Legal Contract Analysis", "task_family": "summarization"},
    "UC8": {"name": "Financial Report Drafting", "task_family": "text_generation"},
}

# ============================================================================
# LOAD USE CASE DATA
# ============================================================================

def load_uc_data(uc_num: str) -> List[Dict]:
    """Load CSV data from SLM Research Project"""
    data_dir = (
        Path.home() / "OneDrive" / "Desktop" / "SLM use cases" /
        "repos" / "SLM_Research_Project" / "data" / "raw_outputs"
    )

    # Find the CSV file for this UC
    csv_files = list(data_dir.glob(f"{uc_num.lower()}_raw_*.csv"))

    if not csv_files:
        logger.error(f"No CSV file found for {uc_num}")
        return []

    csv_file = csv_files[0]
    logger.info(f"Loading {csv_file}")

    records = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
    except Exception as e:
        logger.error(f"Error reading {csv_file}: {e}")

    return records


def convert_to_pipeline_format(uc_records: List[Dict]) -> List[Dict]:
    """Convert UC CSV format to pipeline format (with 'prompt' field)"""
    converted = []

    for i, record in enumerate(uc_records):
        # Try to find the prompt/text field
        prompt = None
        for key in ['prompt', 'text', 'input', 'query', 'request', 'task']:
            if key in record and record[key]:
                prompt = record[key]
                break

        # If still no prompt, try concatenating relevant fields
        if not prompt and record:
            prompt = " ".join(str(v) for v in record.values() if v)

        if prompt:
            converted.append({
                "sample_id": f"{record.get('id', i):04d}",
                "prompt": prompt,
            })

    return converted


# ============================================================================
# RUN PIPELINE ON UC DATA
# ============================================================================

def run_uc_pipeline(uc_num: str, sample_size: int = 100):
    """Run SDDF pipeline on a single use case"""
    from section5_task_classifier import TaskFamilyClassifier
    from end_to_end_runtime_pipeline import (
        load_sddf_models,
        extract_features,
        route_query,
        QueryResult,
        UseCaseResult,
    )

    uc_info = UC_MAPPING[uc_num]
    uc_name = uc_info["name"]
    expected_task_family = uc_info["task_family"]

    print("\n" + "=" * 80)
    print(f"{uc_num}: {uc_name.upper()}")
    print("=" * 80)

    # Load data
    uc_records = load_uc_data(uc_num)
    if not uc_records:
        print(f"ERROR: No data found for {uc_num}")
        return None

    converted_records = convert_to_pipeline_format(uc_records[:sample_size])

    if not converted_records:
        print(f"ERROR: Could not convert data for {uc_num}")
        return None

    print(f"Loaded {len(converted_records)} records from UC")

    # Initialize classifier and models
    classifier = TaskFamilyClassifier()

    artifacts_dir = (
        Path.home() / "OneDrive" / "Desktop" / "SLM use cases" /
        "model_runs" / "sddf_training_splits_slm_only" / "sddf_pipeline_artifacts_v3"
    )
    sddf_models = load_sddf_models(artifacts_dir)

    # Process queries
    print(f"\n{'ID':<10} | {'Classified':<25} | {'0.5b':<6} | {'3b':<6} | {'7b':<6} | {'Consensus':<10}")
    print("-" * 85)

    slm_count_0_5b = 0
    slm_count_3b = 0
    slm_count_7b = 0
    task_family_counts = {}
    query_results = []

    for i, record in enumerate(converted_records):
        query_id = record.get("sample_id", f"query_{i:04d}")
        query_text = record.get("prompt", "")

        if not query_text:
            continue

        # Section 5: Classify
        classification_result = classifier.classify(query_text)
        task_family = classification_result.primary_task_family
        task_family_counts[task_family] = task_family_counts.get(task_family, 0) + 1

        # Extract features
        features = extract_features(query_text, task_family)

        # Section 7: Route per model
        slm_count = 0
        for model_size in ["0.5b", "3b", "7b"]:
            if task_family not in sddf_models or model_size not in sddf_models[task_family]:
                continue

            model_data = sddf_models[task_family][model_size]
            routing_decision = route_query(
                query_id=query_id,
                query_text=query_text,
                task_family=task_family,
                model_size=model_size,
                features=features,
                model_data=model_data
            )

            if routing_decision.routed_to == "SLM":
                slm_count += 1
                if model_size == "0.5b":
                    slm_count_0_5b += 1
                elif model_size == "3b":
                    slm_count_3b += 1
                elif model_size == "7b":
                    slm_count_7b += 1

        # Print progress
        r_0_5b = "SLM" if any(
            sddf_models[task_family]["0.5b"]["tau"] > 0.5  # Placeholder
            for _ in [1]
        ) else "LLM"
        r_3b = "SLM" if slm_count >= 1 else "LLM"
        r_7b = "SLM" if slm_count >= 2 else "LLM"

        if i < 30:  # Show first 30 queries
            print(
                f"{query_id:<10} | {task_family:<25} | {r_0_5b:<6} | {r_3b:<6} | {r_7b:<6} | {slm_count}/3"
            )

    # Aggregate results
    print(f"\nAggregating {len(converted_records)} queries...")

    rho_0_5b = slm_count_0_5b / len(converted_records) if converted_records else 0.0
    rho_3b = slm_count_3b / len(converted_records) if converted_records else 0.0
    rho_7b = slm_count_7b / len(converted_records) if converted_records else 0.0
    rho_bar = (rho_0_5b + rho_3b + rho_7b) / 3.0

    if rho_bar >= 0.70:
        predicted_tier = "SLM"
    elif rho_bar <= 0.30:
        predicted_tier = "LLM"
    else:
        predicted_tier = "HYBRID"

    # Print results
    print("\n" + "-" * 80)
    print("RESULTS")
    print("-" * 80)
    print(f"rho_0.5b = {slm_count_0_5b}/{len(converted_records)} = {rho_0_5b:.4f}")
    print(f"rho_3b   = {slm_count_3b}/{len(converted_records)} = {rho_3b:.4f}")
    print(f"rho_7b   = {slm_count_7b}/{len(converted_records)} = {rho_7b:.4f}")
    print(f"\nrho_bar = ({rho_0_5b:.4f} + {rho_3b:.4f} + {rho_7b:.4f}) / 3 = {rho_bar:.4f}")
    print(f"\nTier Decision: {predicted_tier}")
    print(f"Task Families Detected: {task_family_counts}")

    return {
        "uc": uc_num,
        "name": uc_name,
        "expected_task": expected_task_family,
        "detected_tasks": task_family_counts,
        "rho_0_5b": round(rho_0_5b, 4),
        "rho_3b": round(rho_3b, 4),
        "rho_7b": round(rho_7b, 4),
        "rho_bar": round(rho_bar, 4),
        "tier": predicted_tier,
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "=" * 80)
    print("SLM RESEARCH PROJECT: SDDF PIPELINE EVALUATION")
    print("=" * 80)

    results = {}

    for uc_num in ["UC1", "UC2", "UC3", "UC4", "UC5", "UC6", "UC7", "UC8"]:
        try:
            result = run_uc_pipeline(uc_num, sample_size=40)
            if result:
                results[uc_num] = result
        except Exception as e:
            logger.error(f"Error processing {uc_num}: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY: ALL USE CASES")
    print("=" * 80)
    print(f"{'UC':<6} | {'Use Case':<35} | {'Task':<20} | {'rho_bar':<10} | {'Tier':<8}")
    print("-" * 85)

    for uc_num, result in sorted(results.items()):
        print(
            f"{result['uc']:<6} | {result['name']:<35} | {result['expected_task']:<20} | "
            f"{result['rho_bar']:<10.4f} | {result['tier']:<8}"
        )

    # Save results
    output_file = Path.home() / "OneDrive" / "Desktop" / "SLM use cases" / "slm_research_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_file}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
