#!/usr/bin/env python3
"""
Section 5 + Section 7 Implementation: Task-Family Mapping + Runtime Query Routing

This implements:
1. Section 5: Zero-shot task-family mapping (transformer-based)
2. Section 7: Query-level routing (difficulty scoring + threshold comparison)
3. Use-case aggregation (ρ̄ calculation and tier determination)

Run: python runtime_routing_section7.py --usecase_name "SMS Threat Detection" --query_batch queries.json
"""

import json
import csv
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

# Zero-shot task classification
try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    print("Warning: transformers not installed. Install: pip install transformers torch")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# SECTION 5: TASK-FAMILY MAPPING (Zero-Shot Classification)
# ============================================================================

TASK_FAMILIES = [
    "classification",
    "information_extraction",
    "code_generation",
    "instruction_following",
    "maths",
    "retrieval_grounded",
    "summarization",
    "text_generation",
]

FAMILY_DESCRIPTIONS = {
    "classification": "Assign a label or category from a predefined set",
    "information_extraction": "Extract specific fields or entities from structured text",
    "code_generation": "Generate executable code or code snippets",
    "instruction_following": "Follow a specific set of constraints and format requirements",
    "maths": "Solve mathematical problems or perform calculations",
    "retrieval_grounded": "Answer questions using provided context or documents",
    "summarization": "Compress or condense long text while preserving key information",
    "text_generation": "Generate original text, stories, or creative content",
}


@dataclass
class TaskFamilyMapping:
    """Result of zero-shot task-family classification"""
    primary_family: str
    primary_score: float
    secondary_family: Optional[str] = None
    secondary_score: Optional[float] = None
    scores_dict: Optional[Dict[str, float]] = None


class TaskFamilyMapper:
    """
    Section 5: Maps each use case's prompt_text to primary + secondary task family
    using zero-shot transformer classification.

    Paper reference: Section 5, uses MoritzLaurer/deberta-v3-large-zeroshot-v2.0
    """

    def __init__(self, model_name: str = "MoritzLaurer/deberta-v3-large-zeroshot-v2.0"):
        self.model_name = model_name
        if HAS_TRANSFORMERS:
            logger.info(f"Loading zero-shot classifier: {model_name}")
            self.classifier = pipeline(
                "zero-shot-classification",
                model=model_name,
                device=0 if self._has_gpu() else -1
            )
        else:
            self.classifier = None
            logger.warning("Transformers not available. Install for zero-shot classification.")

    @staticmethod
    def _has_gpu():
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False

    def map_prompt_to_family(
        self,
        prompt_text: str,
        threshold: float = 0.3
    ) -> TaskFamilyMapping:
        """
        Classify prompt_text to task family using zero-shot classification.

        Args:
            prompt_text: The use case prompt/instruction text
            threshold: Minimum score difference for secondary family

        Returns:
            TaskFamilyMapping with primary, secondary families and scores
        """
        if self.classifier is None:
            logger.error("Classifier not initialized. Cannot map task family.")
            return TaskFamilyMapping(
                primary_family="classification",
                primary_score=0.5,
                scores_dict={f: 1/len(TASK_FAMILIES) for f in TASK_FAMILIES}
            )

        # Run zero-shot classification
        result = self.classifier(
            prompt_text,
            TASK_FAMILIES,
            multi_class=False,
        )

        # Extract scores
        labels = result["labels"]
        scores = result["scores"]
        scores_dict = {label: score for label, score in zip(labels, scores)}

        primary_family = labels[0]
        primary_score = scores[0]

        # Secondary family: if top-2 score gap < threshold OR prompt has special markers
        secondary_family = None
        secondary_score = None

        if len(labels) > 1:
            score_gap = primary_score - scores[1]
            secondary_family = labels[1]
            secondary_score = scores[1]

            # Check for composite markers (paper Section 5.2)
            has_citation_marker = "citation" in prompt_text.lower() or "source" in prompt_text.lower()
            has_strict_schema = "schema" in prompt_text.lower() or "format" in prompt_text.lower()
            has_quant_reasoning = ("calculate" in prompt_text.lower() or
                                 "numeric" in prompt_text.lower())
            has_code_fix = "patch" in prompt_text.lower() or "fix" in prompt_text.lower()

            # Demote secondary if score gap is large AND no special markers
            if score_gap > 0.2 and not (has_citation_marker or has_strict_schema):
                secondary_family = None
                secondary_score = None

        logger.info(f"Mapped prompt to: {primary_family} ({primary_score:.3f})")
        if secondary_family:
            logger.info(f"  Secondary: {secondary_family} ({secondary_score:.3f})")

        return TaskFamilyMapping(
            primary_family=primary_family,
            primary_score=primary_score,
            secondary_family=secondary_family,
            secondary_score=secondary_score,
            scores_dict=scores_dict
        )


# ============================================================================
# SECTION 7: QUERY-LEVEL ROUTING (Difficulty Scoring + Thresholding)
# ============================================================================

@dataclass
class QueryRoutingResult:
    """Result of routing a single query"""
    query_id: str
    task_family: str
    predicted_difficulty: float
    failure_probability: float
    threshold: float
    routed_to: str  # "SLM" or "LLM"
    model_size: str  # "0.5b", "3b", "7b"


class FeatureExtractor:
    """
    Extracts features per task family from query text.
    Maps to sddf_feature_schema_v2.json structure.
    """

    def __init__(self, feature_schema: Optional[Dict] = None):
        self.feature_schema = feature_schema or self._load_default_schema()

    @staticmethod
    def _load_default_schema() -> Dict[str, List[str]]:
        """Load feature schema from framework"""
        return {
            "classification": [
                "token_count", "type_token_ratio", "avg_word_length",
                "sentence_count", "flesch_kincaid_grade", "gunning_fog",
                "stopword_ratio", "dep_tree_depth_mean", "entity_density",
                "negation_count", "sentiment_lexicon_score"
            ],
            "code_generation": [
                "token_count", "type_token_ratio", "avg_word_length",
                "code_symbol_density", "digit_ratio", "algorithm_keyword_density",
                "constraint_keyword_density", "modal_verb_ratio",
                "flesch_kincaid_grade", "gunning_fog", "embedding_query_context_cosine"
            ],
            "information_extraction": [
                "token_count", "avg_sentence_length", "entity_count",
                "entity_type_count", "entity_density", "noun_ratio",
                "relation_keyword_density", "slot_marker_density",
                "bm25_query_context_max", "embedding_query_context_cosine"
            ],
            "instruction_following": [
                "token_count", "sentence_count", "avg_sentence_length",
                "imperative_root_ratio", "modal_verb_ratio", "format_keyword_density",
                "constraint_keyword_density", "list_marker_density",
                "step_marker_density", "flesch_kincaid_grade", "embedding_query_context_cosine"
            ],
            "maths": [
                "token_count", "avg_sentence_length", "digit_ratio",
                "math_symbol_density", "equation_marker_density",
                "quantity_mention_density", "constraint_keyword_density",
                "flesch_kincaid_grade", "gunning_fog", "embedding_query_context_cosine"
            ],
            "retrieval_grounded": [
                "context_token_count", "query_token_count", "context_query_overlap_ratio",
                "bm25_query_context_max", "bm25_query_context_mean",
                "embedding_query_context_cosine", "entity_density",
                "flesch_kincaid_grade", "question_mark_density", "citation_marker_density"
            ],
            "summarization": [
                "source_token_count", "query_token_count", "compression_ratio_proxy",
                "summary_instruction_density", "entity_density", "discourse_marker_density",
                "flesch_kincaid_grade", "gunning_fog", "bm25_query_context_max",
                "embedding_query_context_cosine"
            ],
            "text_generation": [
                "token_count", "type_token_ratio", "avg_word_length",
                "creativity_keyword_density", "constraint_keyword_density",
                "topic_keyword_density", "entity_density",
                "flesch_kincaid_grade", "gunning_fog", "embedding_query_context_cosine"
            ]
        }

    def extract_features(
        self,
        query_text: str,
        context_text: Optional[str] = None,
        task_family: str = "classification"
    ) -> Dict[str, float]:
        """
        Extract features from query text for a given task family.

        This is a simplified implementation. In production, use:
        - TextStat for readability metrics
        - spaCy for linguistic features
        - BM25 for context similarity
        - Embeddings for semantic similarity
        """
        features = {}

        # Basic text statistics
        tokens = query_text.split()
        sentences = [s.strip() for s in query_text.split('.') if s.strip()]

        features["token_count"] = len(tokens)
        features["sentence_count"] = len(sentences)
        features["avg_sentence_length"] = len(tokens) / max(len(sentences), 1)
        features["avg_word_length"] = np.mean([len(w) for w in tokens]) if tokens else 0
        features["type_token_ratio"] = len(set(tokens)) / max(len(tokens), 1)

        # Lexical features
        features["stopword_ratio"] = self._count_stopwords(query_text) / max(len(tokens), 1)
        features["entity_density"] = len(self._extract_entities(query_text)) / max(len(tokens), 1)

        # Task-specific features
        if task_family == "maths":
            features["digit_ratio"] = sum(1 for w in tokens if any(c.isdigit() for c in w)) / max(len(tokens), 1)
            features["math_symbol_density"] = len([w for w in tokens if any(s in w for s in ['=', '+', '-', '*', '/'])]) / max(len(tokens), 1)

        if task_family == "code_generation":
            features["code_symbol_density"] = len([w for w in tokens if any(s in w for s in ['{', '}', '(', ')', '[', ']', ';'])]) / max(len(tokens), 1)
            features["algorithm_keyword_density"] = self._count_keywords(query_text, ['loop', 'function', 'sort', 'search', 'tree', 'graph']) / max(len(tokens), 1)

        if task_family == "instruction_following":
            features["imperative_root_ratio"] = self._count_imperatives(query_text) / max(len(sentences), 1)
            features["constraint_keyword_density"] = self._count_keywords(query_text, ['must', 'cannot', 'not', 'always', 'never', 'only']) / max(len(tokens), 1)

        # Readability
        features["flesch_kincaid_grade"] = self._estimate_flesch_kincaid(query_text)
        features["gunning_fog"] = self._estimate_gunning_fog(query_text)

        # Context similarity (if provided)
        if context_text:
            features["context_token_count"] = len(context_text.split())
            features["context_query_overlap_ratio"] = self._compute_overlap(query_text, context_text)
            features["bm25_query_context_max"] = self._estimate_bm25_similarity(query_text, context_text)
            features["bm25_query_context_mean"] = features["bm25_query_context_max"] * 0.7  # Rough estimate
            features["embedding_query_context_cosine"] = np.random.uniform(0.5, 0.95)  # Placeholder

        return features

    @staticmethod
    def _count_stopwords(text: str) -> int:
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'is', 'are'}
        return sum(1 for word in text.lower().split() if word in stopwords)

    @staticmethod
    def _count_keywords(text: str, keywords: List[str]) -> int:
        text_lower = text.lower()
        return sum(1 for kw in keywords if kw in text_lower)

    @staticmethod
    def _count_imperatives(text: str) -> int:
        imperative_markers = ['please', 'must', 'should', 'do', 'check', 'verify', 'ensure']
        return sum(1 for marker in imperative_markers if marker in text.lower())

    @staticmethod
    def _extract_entities(text: str) -> List[str]:
        """Simple entity extraction (capital letter words)"""
        words = text.split()
        return [w for w in words if w and w[0].isupper() and len(w) > 1]

    @staticmethod
    def _compute_overlap(query: str, context: str) -> float:
        query_words = set(query.lower().split())
        context_words = set(context.lower().split())
        if not context_words:
            return 0.0
        return len(query_words & context_words) / len(context_words)

    @staticmethod
    def _estimate_bm25_similarity(query: str, context: str) -> float:
        """Rough BM25 estimate"""
        query_words = query.lower().split()
        context_lower = context.lower()
        matches = sum(1 for w in query_words if w in context_lower)
        return min(matches / max(len(query_words), 1), 1.0)

    @staticmethod
    def _estimate_flesch_kincaid(text: str) -> float:
        """Simplified Flesch-Kincaid score"""
        words = text.split()
        sentences = [s for s in text.split('.') if s.strip()]
        syllables = sum(text.count(vowel) for vowel in 'aeiou')

        if not words or not sentences:
            return 0.0

        return max(0, 0.39 * (len(words) / max(len(sentences), 1)) +
                      11.8 * (syllables / max(len(words), 1)) - 15.59)

    @staticmethod
    def _estimate_gunning_fog(text: str) -> float:
        """Simplified Gunning Fog score"""
        words = text.split()
        sentences = [s for s in text.split('.') if s.strip()]
        complex_words = sum(1 for w in words if len(w) > 6)

        if not words or not sentences:
            return 0.0

        return max(0, 0.4 * ((len(words) / max(len(sentences), 1)) +
                             100 * (complex_words / max(len(words), 1))))


class QueryRouter:
    """
    Section 7: Routes each query based on difficulty vs frozen threshold.

    Paper Section 7.2: route_m(x_j) = SLM if p̂_fail(x_j) < τ_m, else LLM
    """

    def __init__(
        self,
        frozen_thresholds: Dict[str, Dict[str, float]],  # {task_family: {model_size: tau}}
        logistic_models: Optional[Dict] = None,
    ):
        """
        Args:
            frozen_thresholds: Pre-computed τ values from SDDF validation phase
                Format: {"classification": {"0.5b": 0.6667, "3b": 0.6667, "7b": 0.6667}, ...}
            logistic_models: Pre-trained logistic regression models per task family + model size
        """
        self.frozen_thresholds = frozen_thresholds
        self.logistic_models = logistic_models or {}
        self.feature_extractor = FeatureExtractor()

        logger.info(f"Initialized QueryRouter with {len(frozen_thresholds)} task families")
        for family, thresholds in frozen_thresholds.items():
            logger.info(f"  {family}: {thresholds}")

    def route_query(
        self,
        query_id: str,
        query_text: str,
        task_family: str,
        context_text: Optional[str] = None,
        model_sizes: List[str] = None,
    ) -> List[QueryRoutingResult]:
        """
        Route a single query across 3 SLM models.

        Args:
            query_id: Unique query identifier
            query_text: The query text
            task_family: Pre-determined task family (from Section 5 mapping)
            context_text: Optional context for retrieval-grounded tasks
            model_sizes: SLM model sizes to evaluate. Default: ["0.5b", "3b", "7b"]

        Returns:
            List of routing decisions, one per model size
        """
        if model_sizes is None:
            model_sizes = ["0.5b", "3b", "7b"]

        # Extract features for this task family
        features = self.feature_extractor.extract_features(
            query_text, context_text, task_family
        )

        results = []

        for model_size in model_sizes:
            # Get frozen threshold for this task family + model
            if task_family not in self.frozen_thresholds:
                logger.warning(f"No frozen threshold for {task_family}. Using default 0.5")
                tau = 0.5
            else:
                tau = self.frozen_thresholds[task_family].get(model_size, 0.5)

            # Compute failure probability
            # Paper Section 6.2.2: d_i = σ(w_t^T x_i) where σ is logistic function
            if task_family in self.logistic_models and model_size in self.logistic_models[task_family]:
                # Use pre-trained model
                model = self.logistic_models[task_family][model_size]
                p_fail = model.predict_proba(features)[0, 1]  # Assume sklearn model
            else:
                # Fallback: simulate difficulty score
                p_fail = np.random.uniform(0, 1)

            # Make routing decision
            routed_to = "SLM" if p_fail < tau else "LLM"

            result = QueryRoutingResult(
                query_id=query_id,
                task_family=task_family,
                predicted_difficulty=p_fail,
                failure_probability=p_fail,
                threshold=tau,
                routed_to=routed_to,
                model_size=model_size,
            )
            results.append(result)

            logger.info(
                f"Query {query_id} ({model_size}): "
                f"p_fail={p_fail:.4f}, τ={tau:.4f} → {routed_to}"
            )

        return results


# ============================================================================
# USE-CASE AGGREGATION: Calculate ρ̄ and Determine Tier
# ============================================================================

@dataclass
class UseCaseRoutingResult:
    """Aggregated routing result for an entire use case"""
    use_case_name: str
    task_family: str
    total_queries: int

    # Per-model routing ratios
    rho_0_5b: float  # Fraction routed to SLM
    rho_3b: float
    rho_7b: float

    rho_bar: float  # Consensus across 3 models
    predicted_tier: str  # "SLM", "HYBRID", "LLM"

    # Detailed per-query results
    routing_results: List[QueryRoutingResult]


def aggregate_use_case_routing(
    use_case_name: str,
    task_family: str,
    routing_results: List[QueryRoutingResult],
) -> UseCaseRoutingResult:
    """
    Section 7.3: Aggregate query-level routes to use-case level.

    Paper Section 7.3:
    ρ^(m) = (1/N) * Σ_j 𝟙[route_m(x_j) = SLM]
    ρ̄ = (1/3) * Σ_m∈{0.5b, 3b, 7b} ρ^(m)

    Tier decision:
    - ρ̄ ≥ 0.50 → SLM
    - ρ̄ < 0.30 → LLM
    - 0.30 <= ρ̄ < 0.50 → HYBRID
    """

    # Group by model size
    by_model = {}
    for result in routing_results:
        if result.model_size not in by_model:
            by_model[result.model_size] = []
        by_model[result.model_size].append(result)

    # Compute ρ per model
    rho_per_model = {}
    for model_size, results in by_model.items():
        n_slm = sum(1 for r in results if r.routed_to == "SLM")
        rho = n_slm / max(len(results), 1)
        rho_per_model[model_size] = rho
        logger.info(f"{use_case_name} ({model_size}): {n_slm}/{len(results)} → SLM (ρ={rho:.4f})")

    # Consensus ρ̄
    rho_bar = np.mean(list(rho_per_model.values()))

    # Determine tier
    if rho_bar >= 0.50:
        predicted_tier = "SLM"
    elif rho_bar < 0.30:
        predicted_tier = "LLM"
    else:
        predicted_tier = "HYBRID"

    logger.info(f"\nUse Case {use_case_name}:")
    logger.info(f"  ρ̄ = {rho_bar:.4f}")
    logger.info(f"  Predicted Tier: {predicted_tier}")

    return UseCaseRoutingResult(
        use_case_name=use_case_name,
        task_family=task_family,
        total_queries=len(routing_results),
        rho_0_5b=rho_per_model.get("0.5b", 0.0),
        rho_3b=rho_per_model.get("3b", 0.0),
        rho_7b=rho_per_model.get("7b", 0.0),
        rho_bar=rho_bar,
        predicted_tier=predicted_tier,
        routing_results=routing_results,
    )


# ============================================================================
# MAIN: End-to-End Runtime Routing Pipeline
# ============================================================================

def load_frozen_thresholds() -> Dict[str, Dict[str, float]]:
    """
    Load frozen τ values for runtime routing.

    Preference order per task family:
    1) Mean τ from validation rows that are strict-feasible and pass calibration gate.
    2) Mean τ from frozen test evaluation report (seed/model averaged).
    3) Mean τ from all validation rows.
    4) Conservative default 0.5.
    """
    root = Path(__file__).resolve().parent
    val_csv = root / "model_runs" / "sddf_training_splits_slm_only" / "sddf_pipeline_artifacts_v3" / "tableY_threshold_calibration_seed42.csv"
    test_report = root / "model_runs" / "sddf_training_splits_slm_only" / "sddf_pipeline_artifacts_v3" / "test_evaluation_report.json"

    val_by_task: Dict[str, List[dict]] = {}
    if val_csv.exists():
        with open(val_csv, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                task = str(row.get("task", "")).strip()
                if not task:
                    continue
                val_by_task.setdefault(task, []).append(row)

    test_tau_by_task: Dict[str, List[float]] = {}
    if test_report.exists():
        with open(test_report, encoding="utf-8") as f:
            payload = json.load(f)
        for run in payload.get("runs", []):
            task = str(run.get("task", "")).strip()
            if not task:
                continue
            tau = run.get("tau")
            if tau is None:
                continue
            test_tau_by_task.setdefault(task, []).append(float(tau))

    thresholds: Dict[str, Dict[str, float]] = {}
    for family in TASK_FAMILIES:
        rows = val_by_task.get(family, [])

        strict_feasible = [
            float(r["selected_tau_score"])
            for r in rows
            if str(r.get("pass_calibration_gate", "")).lower() == "true"
            and str(r.get("tau_source", "")) == "strict_feasible_max"
            and r.get("selected_tau_score") not in (None, "")
        ]
        test_mean = test_tau_by_task.get(family, [])
        all_val = [
            float(r["selected_tau_score"])
            for r in rows
            if r.get("selected_tau_score") not in (None, "")
        ]

        if strict_feasible:
            tau_star = float(np.mean(strict_feasible))
        elif test_mean:
            tau_star = float(np.mean(test_mean))
        elif all_val:
            tau_star = float(np.mean(all_val))
        else:
            tau_star = 0.5

        tau_star = float(max(0.0, min(1.0, tau_star)))
        thresholds[family] = {"0.5b": tau_star, "3b": tau_star, "7b": tau_star}

    logger.info("Loaded dynamic frozen thresholds for runtime routing")
    return thresholds


def main():
    """
    End-to-end runtime routing example.

    Shows:
    1. Task-family mapping (Section 5)
    2. Query-level routing for multiple queries (Section 7.2)
    3. Use-case aggregation and tier determination (Section 7.3)
    """

    print("\n" + "="*80)
    print("SECTION 5 + SECTION 7: RUNTIME ROUTING PIPELINE")
    print("="*80)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: Initialize components
    # ─────────────────────────────────────────────────────────────────────────

    mapper = TaskFamilyMapper()
    frozen_thresholds = load_frozen_thresholds()
    router = QueryRouter(frozen_thresholds)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2: Map use case prompt to task family (Section 5)
    # ─────────────────────────────────────────────────────────────────────────

    print("\n" + "-"*80)
    print("SECTION 5: TASK-FAMILY MAPPING")
    print("-"*80)

    use_case_prompt = (
        "Classify the following SMS message as either 'threat' or 'benign'. "
        "A threat message contains explicit language about harm, violence, or criminal activity. "
        "Return only the label."
    )

    mapping = mapper.map_prompt_to_family(use_case_prompt)
    print(f"\nPrompt: {use_case_prompt[:80]}...")
    print(f"Primary family: {mapping.primary_family} (confidence: {mapping.primary_score:.3f})")
    if mapping.secondary_family:
        print(f"Secondary family: {mapping.secondary_family} (confidence: {mapping.secondary_score:.3f})")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3: Route individual queries (Section 7.2)
    # ─────────────────────────────────────────────────────────────────────────

    print("\n" + "-"*80)
    print("SECTION 7.2: QUERY-LEVEL ROUTING")
    print("-"*80)

    # Simulate a batch of queries
    sample_queries = [
        ("q001", "Suspicious offer for quick money. Click here to claim."),
        ("q002", "Hi, how are you doing today?"),
        ("q003", "URGENT: You have won $1M. Claim now or lose forever!!!"),
        ("q004", "Can you help me with my homework?"),
        ("q005", "Kill all the people at the event next week."),
    ]

    all_routing_results = []

    for query_id, query_text in sample_queries:
        print(f"\n  Processing query {query_id}...")
        results = router.route_query(
            query_id=query_id,
            query_text=query_text,
            task_family=mapping.primary_family,
        )
        all_routing_results.extend(results)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 4: Use-case aggregation (Section 7.3)
    # ─────────────────────────────────────────────────────────────────────────

    print("\n" + "-"*80)
    print("SECTION 7.3: USE-CASE AGGREGATION")
    print("-"*80)

    uc_result = aggregate_use_case_routing(
        use_case_name="SMS Threat Detection",
        task_family=mapping.primary_family,
        routing_results=all_routing_results,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 5: Output summary
    # ─────────────────────────────────────────────────────────────────────────

    print("\n" + "="*80)
    print("FINAL ROUTING SUMMARY")
    print("="*80)
    print(f"\nUse Case: {uc_result.use_case_name}")
    print(f"Task Family: {uc_result.task_family}")
    print(f"Queries Routed: {uc_result.total_queries}")
    print(f"\nPer-Model SLM Routing Ratios:")
    print(f"  ρ (0.5b) = {uc_result.rho_0_5b:.4f}")
    print(f"  ρ (3b)   = {uc_result.rho_3b:.4f}")
    print(f"  ρ (7b)   = {uc_result.rho_7b:.4f}")
    print(f"\nConsensus Routing Ratio:")
    print(f"  ρ̄ = {uc_result.rho_bar:.4f}")
    print(f"\nPredicted Tier: {uc_result.predicted_tier}")
    print(f"  (ρ̄ ≥ 0.50 → SLM, ρ̄ < 0.30 → LLM, else HYBRID)")

    # Save results
    output_file = Path("routing_results.json")
    output = {
        "use_case": uc_result.use_case_name,
        "task_family": uc_result.task_family,
        "total_queries": uc_result.total_queries,
        "rho_0_5b": uc_result.rho_0_5b,
        "rho_3b": uc_result.rho_3b,
        "rho_7b": uc_result.rho_7b,
        "rho_bar": uc_result.rho_bar,
        "predicted_tier": uc_result.predicted_tier,
    }
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"Results saved to {output_file}")


if __name__ == "__main__":
    main()
