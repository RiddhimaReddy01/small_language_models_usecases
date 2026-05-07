#!/usr/bin/env python3
"""
END-TO-END SDDF RUNTIME PIPELINE

Complete implementation:
1. Load use case queries
2. Section 5: Classify each query to task family
3. Section 7: Route each query via SDDF (3 models)
4. Aggregate: Compute ρ̄ consensus and determine tier

Run: python end_to_end_runtime_pipeline.py --use-case classification --sample-size 100
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import logging
import random

# Import Section 5 classifier
sys.path.insert(0, str(Path(__file__).parent))
from section5_task_classifier import TaskFamilyClassifier, TaskClassificationResult

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class QueryRoutingDecision:
    """Routing decision for a single query, single model"""
    query_id: str
    task_family: str
    model_size: str
    failure_probability: float
    threshold: float
    routed_to: str  # "SLM" or "LLM"


@dataclass
class QueryResult:
    """Complete result for a single query across all 3 models"""
    query_id: str
    query_text: str
    classified_task: str
    classification_confidence: float

    # Per-model routing
    routing_0_5b: QueryRoutingDecision
    routing_3b: QueryRoutingDecision
    routing_7b: QueryRoutingDecision

    # Consensus
    slm_count: int  # How many models routed to SLM


@dataclass
class UseCaseResult:
    """Aggregated result for entire use case"""
    use_case_name: str
    total_queries: int
    task_families_detected: Dict[str, int]

    # Per-model routing ratios
    rho_0_5b: float  # fraction routed to SLM
    rho_3b: float
    rho_7b: float

    # Consensus
    rho_bar: float  # ρ̄ = (ρ_0.5b + ρ_3b + ρ_7b) / 3
    predicted_tier: str  # "SLM" / "HYBRID" / "LLM"

    # Details
    query_results: List[QueryResult]


# ============================================================================
# LOAD GROUND TRUTH DATA
# ============================================================================

def load_use_case_queries(use_case_name: str, sample_size: int = None) -> List[Dict]:
    """
    Load queries from ground truth JSONL files.

    Args:
        use_case_name: e.g., "classification", "maths", "code_generation"
        sample_size: How many queries to load (None = all)

    Returns:
        List of query dicts with 'sample_id' and 'prompt' fields
    """
    data_dir = Path.home() / "OneDrive" / "Desktop" / "SLM use cases" / "data" / "ground_truth"

    file_path = data_dir / f"{use_case_name}.jsonl"

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"Ground truth file for '{use_case_name}' not found")

    queries = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    queries.append(record)

                    if sample_size and len(queries) >= sample_size:
                        break
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        raise

    logger.info(f"Loaded {len(queries)} queries from {use_case_name}")
    return queries


# ============================================================================
# FEATURE EXTRACTION (Task-Specific)
# ============================================================================

def extract_features(query_text: str, task_family: str) -> Dict[str, float]:
    """
    Extract task-family-specific features from query.

    This is a SIMPLIFIED implementation. Production would use:
    - spaCy for NLP features
    - TextStat for readability
    - BM25 for retrieval features
    - Embeddings for semantic features

    For now: basic statistical features
    """
    text_lower = query_text.lower()
    tokens = query_text.split()

    # Generic features
    features = {
        "token_count": float(len(tokens)),
        "char_count": float(len(query_text)),
        "avg_token_length": float(sum(len(t) for t in tokens) / max(1, len(tokens))),
        "punctuation_count": float(sum(1 for c in query_text if c in '.,!?;:')),
        "question_mark": float(1.0 if '?' in query_text else 0.0),
        "uppercase_ratio": float(sum(1 for c in query_text if c.isupper()) / max(1, len(query_text))),
    }

    # Task-specific features
    if task_family == "classification":
        sentiment_words = ["good", "bad", "positive", "negative", "best", "worst"]
        features["sentiment_lexicon_score"] = float(
            sum(1 for word in sentiment_words if word in text_lower) / 6.0
        )

    elif task_family == "code_generation":
        code_keywords = ["function", "code", "python", "javascript", "java", "write", "implement"]
        features["code_keyword_density"] = float(
            sum(1 for kw in code_keywords if kw in text_lower) / 7.0
        )

    elif task_family == "maths":
        math_symbols = ["x", "=", "+", "-", "*", "/", "^", "solve"]
        features["math_symbol_density"] = float(
            sum(1 for sym in math_symbols if sym in text_lower) / 8.0
        )

    elif task_family == "summarization":
        features["length_indicator"] = float(min(1.0, len(tokens) / 100.0))

    elif task_family == "retrieval_grounded":
        retrieval_words = ["based", "document", "according", "provided", "from"]
        features["retrieval_marker_count"] = float(
            sum(1 for word in retrieval_words if word in text_lower) / 5.0
        )

    elif task_family == "instruction_following":
        instruction_words = ["follow", "step", "format", "output", "require"]
        features["instruction_marker_count"] = float(
            sum(1 for word in instruction_words if word in text_lower) / 5.0
        )

    elif task_family == "information_extraction":
        extraction_words = ["extract", "find", "identify", "entity", "name"]
        features["extraction_marker_count"] = float(
            sum(1 for word in extraction_words if word in text_lower) / 5.0
        )

    elif task_family == "text_generation":
        generation_words = ["write", "create", "compose", "story", "creative"]
        features["generation_marker_count"] = float(
            sum(1 for word in generation_words if word in text_lower) / 5.0
        )

    return features


# ============================================================================
# LOAD SDDF MODELS & ROUTE QUERY
# ============================================================================

def load_sddf_models(artifacts_dir: Path) -> Dict:
    """Load all 24 pre-trained logistic regression models"""
    models = {}

    task_families = [
        "classification", "code_generation", "information_extraction",
        "instruction_following", "maths", "retrieval_grounded",
        "summarization", "text_generation"
    ]
    model_sizes = ["0.5b", "3b", "7b"]

    for task in task_families:
        models[task] = {}
        for size in model_sizes:
            model_file = artifacts_dir / task / f"qwen2.5_{size}__seed42.json"

            if not model_file.exists():
                logger.warning(f"Model not found: {model_file}")
                continue

            try:
                with open(model_file, 'r', encoding='utf-8') as f:
                    model_data = json.load(f)

                    # Weights and scaler are lists (ordered by feature index)
                    weights_list = model_data.get("weights", [])
                    scaler_mean_list = model_data.get("scaler_mean", [])
                    scaler_scale_list = model_data.get("scaler_scale", [])
                    feature_names = model_data.get("features", [])

                    # Convert lists to dicts keyed by feature name
                    weights_dict = {
                        fname: float(w)
                        for fname, w in zip(feature_names, weights_list)
                    }
                    scaler_mean_dict = {
                        fname: float(m)
                        for fname, m in zip(feature_names, scaler_mean_list)
                    }
                    scaler_scale_dict = {
                        fname: float(s)
                        for fname, s in zip(feature_names, scaler_scale_list)
                    }

                    models[task][size] = {
                        "weights": weights_dict,
                        "bias": 0.0,  # Logistic regression implicit bias (absorbed into constant)
                        "scaler_mean": scaler_mean_dict,
                        "scaler_scale": scaler_scale_dict,
                        "tau": float(model_data.get("tau", 0.5)),
                        "feature_names": feature_names,
                    }
            except Exception as e:
                logger.warning(f"Error loading {model_file}: {e}")

    logger.info(f"Loaded {sum(len(v) for v in models.values())} SDDF models")
    return models


def compute_failure_probability(
    features: Dict[str, float],
    weights: Dict[str, float],
    bias: float,
    scaler_mean: Dict[str, float],
    scaler_scale: Dict[str, float]
) -> float:
    """
    Compute p̂_fail = sigmoid(w^T·x_scaled + bias)

    Args:
        features: {feature_name: value}
        weights: {feature_name: weight}
        bias: intercept
        scaler_mean: {feature_name: mean}
        scaler_scale: {feature_name: scale}

    Returns:
        Failure probability in [0, 1]
    """
    import math

    # Scale features: (x - mean) / scale
    logit = bias
    for feat_name, weight in weights.items():
        if feat_name in features:
            x = features[feat_name]
            mean = scaler_mean.get(feat_name, 0.0)
            scale = scaler_scale.get(feat_name, 1.0)

            # Avoid division by zero
            if scale > 0:
                x_scaled = (x - mean) / scale
            else:
                x_scaled = 0.0

            logit += weight * x_scaled

    # Sigmoid: 1 / (1 + exp(-logit))
    try:
        p_fail = 1.0 / (1.0 + math.exp(-logit))
    except (OverflowError, ValueError):
        p_fail = 1.0 if logit > 0 else 0.0

    return float(p_fail)


def route_query(
    query_id: str,
    query_text: str,
    task_family: str,
    model_size: str,
    features: Dict[str, float],
    model_data: Dict
) -> QueryRoutingDecision:
    """Route a single query for a single model"""

    # Compute failure probability
    p_fail = compute_failure_probability(
        features=features,
        weights=model_data["weights"],
        bias=model_data["bias"],
        scaler_mean=model_data["scaler_mean"],
        scaler_scale=model_data["scaler_scale"]
    )

    tau = model_data["tau"]
    routed_to = "SLM" if p_fail < tau else "LLM"

    return QueryRoutingDecision(
        query_id=query_id,
        task_family=task_family,
        model_size=model_size,
        failure_probability=p_fail,
        threshold=tau,
        routed_to=routed_to
    )


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_end_to_end_pipeline(
    use_case_name: str,
    sample_size: int = 100,
) -> UseCaseResult:
    """
    Run complete end-to-end SDDF routing pipeline for a use case.

    Args:
        use_case_name: e.g., "classification", "maths"
        sample_size: Number of queries to process

    Returns:
        UseCaseResult with aggregated routing decisions
    """

    print("\n" + "=" * 80)
    print(f"END-TO-END SDDF RUNTIME PIPELINE: {use_case_name.upper()}")
    print("=" * 80)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Load data and models
    # ─────────────────────────────────────────────────────────────────────────

    print("\n[STEP 1] Loading data and models...")

    queries = load_use_case_queries(use_case_name, sample_size)

    artifacts_dir = (
        Path.home() / "OneDrive" / "Desktop" / "SLM use cases" /
        "model_runs" / "sddf_training_splits_slm_only" / "sddf_pipeline_artifacts_v3"
    )

    sddf_models = load_sddf_models(artifacts_dir)

    # Initialize Section 5 classifier
    classifier = TaskFamilyClassifier()
    logger.info("Initialized Section 5 task classifier")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: Process each query
    # ─────────────────────────────────────────────────────────────────────────

    print(f"\n[STEP 2] Processing {len(queries)} queries...")
    print(f"{'ID':<8} | {'Task Family':<20} | {'0.5b':<6} | {'3b':<6} | {'7b':<6} | {'Consensus':<10}")
    print("-" * 70)

    query_results = []
    task_family_counts = {}

    for i, query_record in enumerate(queries):
        query_id = query_record.get("sample_id", f"query_{i:04d}")
        query_text = query_record.get("prompt", "")

        if not query_text:
            continue

        # SECTION 5: Classify query
        classification_result = classifier.classify(query_text)
        task_family = classification_result.primary_task_family
        classification_confidence = classification_result.confidence

        # Track task family distribution
        task_family_counts[task_family] = task_family_counts.get(task_family, 0) + 1

        # Extract features for this task family
        features = extract_features(query_text, task_family)

        # SECTION 7: Route via SDDF for each model
        routing_decisions = {}
        slm_count = 0

        for model_size in ["0.5b", "3b", "7b"]:
            if task_family not in sddf_models or model_size not in sddf_models[task_family]:
                logger.warning(f"Model not available: {task_family}/{model_size}")
                routing_decisions[model_size] = QueryRoutingDecision(
                    query_id=query_id,
                    task_family=task_family,
                    model_size=model_size,
                    failure_probability=0.5,
                    threshold=0.5,
                    routed_to="LLM"  # Default to safe option
                )
            else:
                model_data = sddf_models[task_family][model_size]
                routing_decision = route_query(
                    query_id=query_id,
                    query_text=query_text,
                    task_family=task_family,
                    model_size=model_size,
                    features=features,
                    model_data=model_data
                )
                routing_decisions[model_size] = routing_decision

                if routing_decision.routed_to == "SLM":
                    slm_count += 1

        # Record query result
        query_result = QueryResult(
            query_id=query_id,
            query_text=query_text[:60] + "..." if len(query_text) > 60 else query_text,
            classified_task=task_family,
            classification_confidence=classification_confidence,
            routing_0_5b=routing_decisions["0.5b"],
            routing_3b=routing_decisions["3b"],
            routing_7b=routing_decisions["7b"],
            slm_count=slm_count
        )
        query_results.append(query_result)

        # Print progress
        r_0_5b = "SLM" if routing_decisions["0.5b"].routed_to == "SLM" else "LLM"
        r_3b = "SLM" if routing_decisions["3b"].routed_to == "SLM" else "LLM"
        r_7b = "SLM" if routing_decisions["7b"].routed_to == "SLM" else "LLM"

        print(
            f"{query_id:<8} | {task_family:<20} | {r_0_5b:<6} | {r_3b:<6} | {r_7b:<6} | {slm_count}/3"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Aggregate results
    # ─────────────────────────────────────────────────────────────────────────

    print(f"\n[STEP 3] Aggregating results across {len(query_results)} queries...")

    slm_count_0_5b = sum(1 for qr in query_results if qr.routing_0_5b.routed_to == "SLM")
    slm_count_3b = sum(1 for qr in query_results if qr.routing_3b.routed_to == "SLM")
    slm_count_7b = sum(1 for qr in query_results if qr.routing_7b.routed_to == "SLM")

    rho_0_5b = slm_count_0_5b / len(query_results) if query_results else 0.0
    rho_3b = slm_count_3b / len(query_results) if query_results else 0.0
    rho_7b = slm_count_7b / len(query_results) if query_results else 0.0

    rho_bar = (rho_0_5b + rho_3b + rho_7b) / 3.0

    # Tier decision
    if rho_bar >= 0.50:
        predicted_tier = "SLM"
    elif rho_bar < 0.30:
        predicted_tier = "LLM"
    else:
        predicted_tier = "HYBRID"

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Display results
    # ─────────────────────────────────────────────────────────────────────────

    print("\n" + "-" * 80)
    print("AGGREGATION RESULTS")
    print("-" * 80)

    print(f"\nPer-Model Routing Ratios (rho):")
    print(f"  rho_0.5b = {slm_count_0_5b}/{len(query_results)} = {rho_0_5b:.4f}")
    print(f"  rho_3b   = {slm_count_3b}/{len(query_results)} = {rho_3b:.4f}")
    print(f"  rho_7b   = {slm_count_7b}/{len(query_results)} = {rho_7b:.4f}")

    print(f"\nConsensus Routing Ratio (rho_bar):")
    print(f"  rho_bar = (rho_0.5b + rho_3b + rho_7b) / 3 = {rho_bar:.4f}")

    print(f"\nTier Decision:")
    print(f"  if rho_bar >= 0.50 -> SLM")
    print(f"  if rho_bar < 0.30 -> LLM")
    print(f"  else               -> HYBRID")
    print(f"\n  Result: {predicted_tier} (rho_bar = {rho_bar:.4f})")

    print(f"\nTask Family Distribution:")
    for task, count in sorted(task_family_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {task:<25} {count:>3} queries")

    print("\n" + "=" * 80)

    return UseCaseResult(
        use_case_name=use_case_name,
        total_queries=len(query_results),
        task_families_detected=task_family_counts,
        rho_0_5b=rho_0_5b,
        rho_3b=rho_3b,
        rho_7b=rho_7b,
        rho_bar=rho_bar,
        predicted_tier=predicted_tier,
        query_results=query_results,
    )


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="End-to-End SDDF Runtime Pipeline")
    parser.add_argument("--use-case", default="classification", help="Use case name")
    parser.add_argument("--sample-size", type=int, default=100, help="Number of queries to process")
    parser.add_argument("--output", default=None, help="Save results to JSON file")
    args = parser.parse_args()

    result = run_end_to_end_pipeline(
        use_case_name=args.use_case,
        sample_size=args.sample_size,
    )

    # Save results if requested
    if args.output:
        output_file = Path(args.output)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to JSON-serializable format
        result_dict = {
            "use_case_name": result.use_case_name,
            "total_queries": result.total_queries,
            "task_families_detected": result.task_families_detected,
            "rho_0_5b": result.rho_0_5b,
            "rho_3b": result.rho_3b,
            "rho_7b": result.rho_7b,
            "rho_bar": result.rho_bar,
            "predicted_tier": result.predicted_tier,
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2)

        logger.info(f"Results saved to {output_file}")
