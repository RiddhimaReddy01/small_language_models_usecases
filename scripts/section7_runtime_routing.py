#!/usr/bin/env python3
"""
SECTION 7: Runtime Query-Level Routing (Query → SLM/LLM Decision)

Uses:
- Ground truth evaluation data from /data/ground_truth/*.jsonl
- Pre-trained logistic regression models from SDDF v3 artifacts
- Frozen thresholds τ per (task_family, model_size)

Paper Section 7.2: route_m(x_j) = SLM if p̂_fail(x_j) < τ_m, else LLM
Paper Section 7.3: ρ̄ = (1/3) * Σ ρ^(m)  →  Tier: SLM if ≥0.70, LLM if ≤0.30, else HYBRID

Run: python section7_runtime_routing.py
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class QueryRoutingResult:
    """Single query routing decision"""
    query_id: str
    task_family: str
    model_size: str
    failure_probability: float
    frozen_threshold: float
    routed_to: str  # "SLM" or "LLM"
    correct_answer_slm: bool  # ground truth


@dataclass
class UseCaseAggregation:
    """Aggregated routing results for entire use case"""
    task_family: str
    total_queries: int

    rho_0_5b: float  # fraction routed to SLM
    rho_3b: float
    rho_7b: float
    rho_bar: float   # consensus (ρ̄)

    predicted_tier: str  # "SLM", "HYBRID", "LLM"

    # Per-model routing results
    routing_results_0_5b: List[QueryRoutingResult]
    routing_results_3b: List[QueryRoutingResult]
    routing_results_7b: List[QueryRoutingResult]


# ============================================================================
# STEP 1: LOAD SDDF V3 LOGISTIC REGRESSION MODELS
# ============================================================================

class SDDFv3ModelLoader:
    """Load pre-trained logistic regression models from SDDF v3 artifacts"""

    def __init__(self, artifacts_dir: Path):
        self.artifacts_dir = Path(artifacts_dir)
        self.models = {}  # {task_family: {model_size: {weights, bias, scaler, tau}}}

    def load_all_models(self):
        """Load all (task_family, model_size) combinations for seed=42"""
        task_families = [
            "classification",
            "code_generation",
            "information_extraction",
            "instruction_following",
            "maths",
            "retrieval_grounded",
            "summarization",
            "text_generation",
        ]
        model_sizes = ["0.5b", "3b", "7b"]

        for task in task_families:
            self.models[task] = {}
            for size in model_sizes:
                model_file = (
                    self.artifacts_dir / task /
                    f"qwen2.5_{size}__seed42.json"
                )

                if not model_file.exists():
                    logger.warning(f"Model file not found: {model_file}")
                    continue

                try:
                    with open(model_file, encoding='utf-8') as f:
                        model_data = json.load(f)

                    self.models[task][size] = {
                        "features": model_data["features"],
                        "weights": np.array(model_data["weights"]),
                        "bias": model_data["bias"],
                        "scaler_mean": np.array(model_data["scaler_mean"]),
                        "scaler_scale": np.array(model_data["scaler_scale"]),
                        "tau": model_data["tau"],
                    }
                    logger.info(f"✓ Loaded {task} (qwen2.5_{size})")
                except Exception as e:
                    logger.error(f"Failed to load {model_file}: {e}")

    def get_model(self, task_family: str, model_size: str) -> Optional[Dict]:
        """Get model parameters for (task_family, model_size)"""
        if task_family not in self.models:
            return None
        return self.models[task_family].get(model_size)


# ============================================================================
# STEP 2: FEATURE EXTRACTION FROM QUERY
# ============================================================================

class FeatureExtractor:
    """Extract features from query text"""

    def __init__(self, feature_names: List[str]):
        self.feature_names = feature_names

    def extract(self, prompt_text: str, reference_output: str = "") -> Dict[str, float]:
        """
        Extract features from prompt.
        Uses simplified feature computation (can be enhanced with textstat, spacy, etc.)
        """
        text = prompt_text + " " + reference_output
        tokens = text.split()
        sentences = [s.strip() for s in text.split('.') if s.strip()]

        features = {}

        # Token-based features
        features["token_count"] = len(tokens)
        features["sentence_count"] = len(sentences)
        features["avg_sentence_length"] = (
            len(tokens) / max(len(sentences), 1)
        )
        features["avg_word_length"] = (
            np.mean([len(w) for w in tokens]) if tokens else 0
        )
        features["type_token_ratio"] = (
            len(set(tokens)) / max(len(tokens), 1)
        )

        # Linguistic features
        features["stopword_ratio"] = self._count_stopwords(text) / max(len(tokens), 1)
        features["entity_density"] = len(self._extract_entities(text)) / max(len(tokens), 1)

        # Readability
        features["flesch_kincaid_grade"] = self._flesch_kincaid(text)
        features["gunning_fog"] = self._gunning_fog(text)

        # Negation
        features["negation_count"] = self._count_words(text, ["not", "no", "never"])

        # Task-specific features (filled with defaults if not relevant)
        features["sentiment_lexicon_score"] = self._sentiment_score(text)
        features["dep_tree_depth_mean"] = np.random.uniform(2, 4)  # placeholder
        features["code_symbol_density"] = (
            len([w for w in tokens if any(c in w for c in ['{', '}', '(', ')'])])
            / max(len(tokens), 1)
        )
        features["digit_ratio"] = (
            sum(1 for w in tokens if any(c.isdigit() for c in w)) / max(len(tokens), 1)
        )
        features["algorithm_keyword_density"] = (
            self._count_words(text, ["loop", "function", "sort", "search", "tree"])
            / max(len(tokens), 1)
        )
        features["constraint_keyword_density"] = (
            self._count_words(text, ["must", "cannot", "only", "always", "never"])
            / max(len(tokens), 1)
        )
        features["modal_verb_ratio"] = (
            self._count_words(text, ["can", "could", "should", "would"])
            / max(len(sentences), 1)
        )
        features["entity_count"] = len(self._extract_entities(text))
        features["entity_type_count"] = len(set(self._extract_entities(text)))
        features["noun_ratio"] = np.random.uniform(0.15, 0.35)  # placeholder
        features["relation_keyword_density"] = (
            self._count_words(text, ["between", "after", "before", "during"])
            / max(len(tokens), 1)
        )
        features["slot_marker_density"] = (
            self._count_words(text, ["field", "value", "slot", "key"])
            / max(len(tokens), 1)
        )
        features["bm25_query_context_max"] = np.random.uniform(0.5, 0.95)
        features["bm25_query_context_mean"] = np.random.uniform(0.4, 0.8)
        features["context_token_count"] = len(tokens)
        features["query_token_count"] = len(tokens)
        features["context_query_overlap_ratio"] = 0.7
        features["embedding_query_context_cosine"] = np.random.uniform(0.5, 0.95)
        features["imperative_root_ratio"] = (
            self._count_words(text, ["do", "make", "check", "verify"])
            / max(len(sentences), 1)
        )
        features["format_keyword_density"] = (
            self._count_words(text, ["format", "schema", "structure"])
            / max(len(tokens), 1)
        )
        features["list_marker_density"] = (
            self._count_words(text, ["list", "bullet", "number", "step"])
            / max(len(tokens), 1)
        )
        features["step_marker_density"] = (
            self._count_words(text, ["step", "then", "next", "finally"])
            / max(len(sentences), 1)
        )
        features["math_symbol_density"] = (
            len([w for w in tokens if any(c in w for c in ['=', '+', '-', '*', '/'])])
            / max(len(tokens), 1)
        )
        features["equation_marker_density"] = (
            self._count_words(text, ["equation", "solve", "calculate"])
            / max(len(tokens), 1)
        )
        features["quantity_mention_density"] = (
            self._count_words(text, ["how many", "how much", "count", "number"])
            / max(len(tokens), 1)
        )
        features["source_token_count"] = len(tokens)
        features["compression_ratio_proxy"] = 0.5
        features["summary_instruction_density"] = (
            self._count_words(text, ["summarize", "summary", "brief", "short"])
            / max(len(tokens), 1)
        )
        features["discourse_marker_density"] = (
            self._count_words(text, ["however", "therefore", "because", "also"])
            / max(len(tokens), 1)
        )
        features["creativity_keyword_density"] = (
            self._count_words(text, ["creative", "imagine", "story", "unique"])
            / max(len(tokens), 1)
        )
        features["topic_keyword_density"] = (
            self._count_words(text, ["about", "regarding", "concerning"])
            / max(len(tokens), 1)
        )
        features["question_mark_density"] = text.count("?") / max(len(sentences), 1)
        features["citation_marker_density"] = (
            self._count_words(text, ["source", "cite", "reference", "quote"])
            / max(len(tokens), 1)
        )

        return features

    @staticmethod
    def _count_stopwords(text: str) -> int:
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'is', 'are', 'be'}
        return sum(1 for word in text.lower().split() if word in stopwords)

    @staticmethod
    def _count_words(text: str, words: List[str]) -> int:
        text_lower = text.lower()
        return sum(1 for w in words if w in text_lower)

    @staticmethod
    def _extract_entities(text: str) -> List[str]:
        """Extract capitalized words as entities"""
        return [w for w in text.split() if w and w[0].isupper() and len(w) > 1]

    @staticmethod
    def _sentiment_score(text: str) -> float:
        positive = sum(text.lower().count(w) for w in ['good', 'great', 'excellent', 'positive'])
        negative = sum(text.lower().count(w) for w in ['bad', 'poor', 'terrible', 'negative'])
        total = positive + negative
        if total == 0:
            return 0.5
        return positive / (positive + negative)

    @staticmethod
    def _flesch_kincaid(text: str) -> float:
        words = text.split()
        sentences = [s for s in text.split('.') if s.strip()]
        syllables = sum(text.count(v) for v in 'aeiou')

        if not words or not sentences:
            return 0.0

        return max(0, 0.39 * (len(words) / len(sentences)) +
                      11.8 * (syllables / len(words)) - 15.59)

    @staticmethod
    def _gunning_fog(text: str) -> float:
        words = text.split()
        sentences = [s for s in text.split('.') if s.strip()]
        complex_words = sum(1 for w in words if len(w) > 6)

        if not words or not sentences:
            return 0.0

        return max(0, 0.4 * (len(words) / len(sentences) +
                             100 * (complex_words / len(words))))


# ============================================================================
# STEP 3: LOGISTIC REGRESSION INFERENCE
# ============================================================================

def sigmoid(x: np.ndarray) -> np.ndarray:
    """Logistic sigmoid function"""
    return 1 / (1 + np.exp(-np.clip(x, -500, 500)))


def compute_failure_probability(
    features_dict: Dict[str, float],
    feature_names: List[str],
    weights: np.ndarray,
    bias: float,
    scaler_mean: np.ndarray,
    scaler_scale: np.ndarray,
) -> float:
    """
    Paper Section 6.2.2: d_i = σ(w_t^T x_i)

    Steps:
    1. Extract features in order
    2. Scale: (x - mean) / scale
    3. Compute logit: w^T * x_scaled + bias
    4. Apply sigmoid: σ(logit) = p̂_fail
    """
    # Extract feature values in order
    x = np.array([features_dict.get(fname, 0.0) for fname in feature_names])

    # Scale
    x_scaled = (x - scaler_mean) / np.clip(scaler_scale, 1e-10, None)

    # Logit
    logit = np.dot(weights, x_scaled) + bias

    # Sigmoid
    p_fail = sigmoid(np.array([logit]))[0]

    return float(p_fail)


# ============================================================================
# STEP 4: QUERY ROUTING
# ============================================================================

def route_query(
    query_id: str,
    task_family: str,
    prompt: str,
    reference: dict,
    model_loader: SDDFv3ModelLoader,
) -> List[QueryRoutingResult]:
    """
    Paper Section 7.2: Route a single query across 3 SLM models

    For each model m:
        p̂_fail = compute_failure_probability(features)
        route = SLM if p̂_fail < τ_m, else LLM
    """

    results = []

    # Get reference answer
    ref_text = ""
    if isinstance(reference, dict):
        ref_text = json.dumps(reference)

    for model_size in ["0.5b", "3b", "7b"]:
        # Load model
        model_data = model_loader.get_model(task_family, model_size)
        if not model_data:
            logger.warning(f"No model for {task_family}/{model_size}")
            continue

        # Extract features
        extractor = FeatureExtractor(model_data["features"])
        features = extractor.extract(prompt, ref_text)

        # Compute failure probability
        p_fail = compute_failure_probability(
            features_dict=features,
            feature_names=model_data["features"],
            weights=model_data["weights"],
            bias=model_data["bias"],
            scaler_mean=model_data["scaler_mean"],
            scaler_scale=model_data["scaler_scale"],
        )

        # Get frozen threshold
        tau = model_data["tau"]

        # Route
        routed = "SLM" if p_fail < tau else "LLM"

        result = QueryRoutingResult(
            query_id=query_id,
            task_family=task_family,
            model_size=model_size,
            failure_probability=p_fail,
            frozen_threshold=tau,
            routed_to=routed,
            correct_answer_slm=reference.get("correct", False) if isinstance(reference, dict) else False,
        )
        results.append(result)

        logger.info(
            f"  {model_size:3s} | p̂_fail={p_fail:.4f} τ={tau:.4f} | "
            f"{'✓ SLM' if routed == 'SLM' else '✗ LLM'}"
        )

    return results


# ============================================================================
# STEP 5: USE-CASE AGGREGATION
# ============================================================================

def aggregate_routing_results(
    task_family: str,
    routing_results: List[QueryRoutingResult],
) -> UseCaseAggregation:
    """
    Paper Section 7.3: Aggregate query-level routes to use-case level

    ρ^(m) = (1/N) * Σ_j 𝟙[route_m(x_j) = SLM]
    ρ̄ = (1/3) * Σ_m ρ^(m)

    Tier: SLM if ρ̄ ≥ 0.70, LLM if ρ̄ ≤ 0.30, else HYBRID
    """

    # Group by model size
    by_model = {"0.5b": [], "3b": [], "7b": []}
    for result in routing_results:
        by_model[result.model_size].append(result)

    # Compute ρ per model
    rho_per_model = {}
    for model_size, results in by_model.items():
        n_slm = sum(1 for r in results if r.routed_to == "SLM")
        rho = n_slm / max(len(results), 1)
        rho_per_model[model_size] = rho
        logger.info(
            f"{task_family:20s} ({model_size}) | "
            f"{n_slm:2d}/{len(results):2d} → SLM (ρ = {rho:.4f})"
        )

    # Consensus ρ̄
    rho_bar = np.mean(list(rho_per_model.values()))

    # Determine tier
    if rho_bar >= 0.70:
        predicted_tier = "SLM"
    elif rho_bar <= 0.30:
        predicted_tier = "LLM"
    else:
        predicted_tier = "HYBRID"

    logger.info(f"  → ρ̄ = {rho_bar:.4f}  PREDICTED TIER: {predicted_tier}\n")

    return UseCaseAggregation(
        task_family=task_family,
        total_queries=len(routing_results),
        rho_0_5b=rho_per_model.get("0.5b", 0.0),
        rho_3b=rho_per_model.get("3b", 0.0),
        rho_7b=rho_per_model.get("7b", 0.0),
        rho_bar=rho_bar,
        predicted_tier=predicted_tier,
        routing_results_0_5b=by_model["0.5b"],
        routing_results_3b=by_model["3b"],
        routing_results_7b=by_model["7b"],
    )


# ============================================================================
# MAIN: Load data, route, aggregate
# ============================================================================

def main():
    """
    End-to-end Section 7 runtime routing on actual UC dataset
    """

    print("\n" + "="*90)
    print("SECTION 7: RUNTIME QUERY ROUTING")
    print("="*90)

    # Paths
    base_path = Path.home() / "OneDrive" / "Desktop" / "SLM use cases"
    artifacts_dir = base_path / "model_runs" / "sddf_training_splits_slm_only" / "sddf_pipeline_artifacts_v3"
    data_dir = base_path / "data" / "ground_truth"

    # Load models
    logger.info("\n1. Loading SDDF v3 models...")
    model_loader = SDDFv3ModelLoader(artifacts_dir)
    model_loader.load_all_models()

    # Route queries per task family
    logger.info("\n2. Routing queries per task family...")
    aggregations = {}

    for task_family in [
        "classification",
        "information_extraction",
        "code_generation",
        "text_generation",
        "maths",
        "summarization",
        "instruction_following",
        "retrieval_grounded",
    ]:
        data_file = data_dir / f"{task_family}.jsonl"

        if not data_file.exists():
            logger.warning(f"Data file not found: {data_file}")
            continue

        # Load queries
        queries = []
        with open(data_file, encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 20:  # Limit to first 20 for speed
                    break
                queries.append(json.loads(line))

        logger.info(f"\n{task_family.upper()} ({len(queries)} queries)")
        logger.info("-" * 90)

        # Route all queries
        all_results = []
        for q in queries:
            sample_id = q.get("sample_id", f"{task_family}_{len(all_results):04d}")
            results = route_query(
                query_id=sample_id,
                task_family=task_family,
                prompt=q.get("prompt", ""),
                reference=q.get("reference", {}),
                model_loader=model_loader,
            )
            all_results.extend(results)

        # Aggregate
        agg = aggregate_routing_results(task_family, all_results)
        aggregations[task_family] = agg

    # Summary
    print("\n" + "="*90)
    print("SUMMARY: USE-CASE ROUTING TIERS")
    print("="*90)
    print(f"\n{'Task Family':<25} {'rho_bar':<10} {'Tier':<10}")
    print("-" * 50)
    for task_family, agg in aggregations.items():
        print(f"{task_family:<25} {agg.rho_bar:<10.4f} {agg.predicted_tier:<10}")

    # Save results
    output_file = Path("section7_routing_results.json")
    output = {
        task_family: {
            "total_queries": agg.total_queries,
            "rho_0_5b": agg.rho_0_5b,
            "rho_3b": agg.rho_3b,
            "rho_7b": agg.rho_7b,
            "rho_bar": agg.rho_bar,
            "predicted_tier": agg.predicted_tier,
        }
        for task_family, agg in aggregations.items()
    }

    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    logger.info(f"\n✓ Results saved to {output_file}")


if __name__ == "__main__":
    main()
