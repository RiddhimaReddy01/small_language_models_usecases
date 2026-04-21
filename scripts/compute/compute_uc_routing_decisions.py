#!/usr/bin/env python3
"""
Compute empirical routing decisions and consensus ratios (ρ̄) for each UC.

For each UC:
1. Load all rows from UC dataset CSV
2. For each row:
   - Map UC → task family
   - Extract 11 linguistic features from item_text
   - Compute p_fail using learned logistic regression (weights, bias)
   - Compare p_fail vs frozen τ of task family
   - Make routing decision: SLM if p_fail < τ, else LLM
3. Aggregate routing decisions
4. Compute ρ̄ = % routed to SLM
5. Assign tier based on ρ̄
6. Save results

Features extracted:
- token_count, type_token_ratio, avg_word_length, sentence_count
- flesch_kincaid_grade, gunning_fog, stopword_ratio, dep_tree_depth_mean
- entity_density, negation_count, sentiment_lexicon_score
"""

import json
import csv
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import re
import sys

# NLP libraries
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

try:
    import textstat
except ImportError:
    print("Warning: textstat not available, readability scores will be 0")
    textstat = None

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    print("Loaded spacy model")
except (ImportError, OSError):
    print("Warning: spacy model not available, using lighter features only")
    nlp = None

from sddf import FROZEN_TAU_CONSENSUS
from sddf.usecase_mapping import get_usecase_info
from sddf.runtime_routing import tier_from_consensus_ratio

# Download required NLTK data
print("Downloading NLTK data...")
for resource in ['punkt', 'averaged_perceptron_tagger', 'stopwords', 'universal_tagset']:
    try:
        nltk.data.find(f'tokenizers/{resource}' if resource == 'punkt' else f'corpora/{resource}' if resource == 'stopwords' else f'taggers/{resource}')
    except LookupError:
        nltk.download(resource, quiet=True)

try:
    STOPWORDS = set(stopwords.words('english'))
except:
    STOPWORDS = set()

# Simple sentiment lexicon
POSITIVE_WORDS = {
    'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'awesome',
    'love', 'best', 'perfect', 'brilliant', 'excellent', 'superb', 'outstanding'
}
NEGATIVE_WORDS = {
    'bad', 'terrible', 'horrible', 'awful', 'hate', 'worst', 'poor', 'fail',
    'error', 'problem', 'issue', 'bug', 'broken', 'crash', 'failure', 'dangerous'
}


# UC to Task Family mapping
UC_TO_TASK_FAMILY = {
    "UC1": "classification",
    "UC2": "information_extraction",
    "UC3": "classification",
    "UC4": "classification",
    "UC5": "code_generation",
    "UC6": "classification",
    "UC7": "summarization",
    "UC8": "text_generation",
}

# UC data source: which CSV directory and which text column to use
UC_DATA_SOURCE = {
    "UC1": {"source": "raw_outputs", "text_column": "item_text"},
    "UC2": {"source": "gold_sets", "text_column": "invoice_text"},
    "UC3": {"source": "raw_outputs", "text_column": "item_text"},
    "UC4": {"source": "raw_outputs", "text_column": "item_text"},
    "UC5": {"source": "raw_outputs", "text_column": "item_text"},
    "UC6": {"source": "gold_sets", "text_column": "presentation"},
    "UC7": {"source": "raw_outputs", "text_column": "item_text"},
    "UC8": {"source": "gold_sets", "text_column": "prompt_text"},
}


def sigmoid(z: np.ndarray) -> np.ndarray:
    """Sigmoid activation function."""
    z = np.clip(z, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-z))


def extract_linguistic_features(text: str) -> Dict[str, float]:
    """Extract 11 linguistic features from text matching SDDF model requirements."""
    if not text:
        return {
            "token_count": 0.0,
            "type_token_ratio": 0.0,
            "avg_word_length": 0.0,
            "sentence_count": 0.0,
            "flesch_kincaid_grade": 0.0,
            "gunning_fog": 0.0,
            "stopword_ratio": 0.0,
            "dep_tree_depth_mean": 0.0,
            "entity_density": 0.0,
            "negation_count": 0.0,
            "sentiment_lexicon_score": 0.0,
        }

    text = str(text).strip()
    if len(text) < 5:
        return {k: 0.0 for k in ["token_count", "type_token_ratio", "avg_word_length", "sentence_count", "flesch_kincaid_grade", "gunning_fog", "stopword_ratio", "dep_tree_depth_mean", "entity_density", "negation_count", "sentiment_lexicon_score"]}

    try:
        # Tokenize
        tokens = word_tokenize(text.lower())
        token_count = len(tokens)

        # Type-token ratio (vocabulary richness)
        unique_tokens = len(set(tokens))
        type_token_ratio = unique_tokens / token_count if token_count > 0 else 0.0

        # Average word length
        words = [t for t in tokens if t.isalpha()]
        avg_word_length = np.mean([len(w) for w in words]) if words else 0.0

        # Sentence count
        sentences = sent_tokenize(text)
        sentence_count = len(sentences)

        # Readability scores
        flesch_kincaid_grade = 0.0
        gunning_fog = 0.0
        if textstat:
            try:
                flesch_kincaid_grade = float(textstat.flesch_kincaid_grade(text))
                gunning_fog = float(textstat.gunning_fog(text))
            except:
                pass

        # Stopword ratio
        stopword_count = sum(1 for t in tokens if t in STOPWORDS)
        stopword_ratio = stopword_count / token_count if token_count > 0 else 0.0

        # Dependency tree depth (using spacy if available)
        dep_tree_depth_mean = 0.0
        entity_density = 0.0
        if nlp:
            try:
                doc = nlp(text[:2000])  # Limit to 2000 chars
                # Avg dependency depth
                depths = [token.depth for token in doc]
                dep_tree_depth_mean = np.mean(depths) if depths else 0.0
                # Entity density
                entity_count = len(doc.ents)
                entity_density = entity_count / len(doc) if len(doc) > 0 else 0.0
            except:
                pass

        # Negation count
        negation_pattern = r"\b(not|no|never|neither|nobody|nothing|nowhere|n't|cannot|can't|won't|wouldn't|shouldn't|couldn't)\b"
        negation_count = len(re.findall(negation_pattern, text))

        # Sentiment lexicon score
        positive_count = sum(1 for w in words if w in POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in NEGATIVE_WORDS)
        sentiment_lexicon_score = (positive_count - negative_count) / max(1, len(words))

        return {
            "token_count": float(token_count),
            "type_token_ratio": float(type_token_ratio),
            "avg_word_length": float(avg_word_length),
            "sentence_count": float(sentence_count),
            "flesch_kincaid_grade": float(flesch_kincaid_grade),
            "gunning_fog": float(gunning_fog),
            "stopword_ratio": float(stopword_ratio),
            "dep_tree_depth_mean": float(dep_tree_depth_mean),
            "entity_density": float(entity_density),
            "negation_count": float(negation_count),
            "sentiment_lexicon_score": float(sentiment_lexicon_score),
        }

    except Exception as e:
        # On any error, return zeros
        return {k: 0.0 for k in ["token_count", "type_token_ratio", "avg_word_length", "sentence_count", "flesch_kincaid_grade", "gunning_fog", "stopword_ratio", "dep_tree_depth_mean", "entity_density", "negation_count", "sentiment_lexicon_score"]}


def load_uc_dataset(uc_num: str) -> List[Dict[str, Any]]:
    """Load CSV data for UC from SLM_Research_Project (gold_sets or raw_outputs)."""
    source_info = UC_DATA_SOURCE.get(uc_num)
    if not source_info:
        raise ValueError(f"No data source configured for {uc_num}")

    source = source_info["source"]
    text_column = source_info["text_column"]

    data_dir = (
        Path.home() / "OneDrive" / "Desktop" / "SLM use cases" /
        "repos" / "SLM_Research_Project" / "data" / source
    )

    if source == "gold_sets":
        # Gold sets have fixed filenames like uc2_invoice_extraction.csv
        csv_file = None
        for f in data_dir.glob(f"{uc_num.lower()}_*.csv"):
            csv_file = f
            break
        if not csv_file:
            raise FileNotFoundError(f"No CSV found for {uc_num} in {data_dir}")
    else:
        # Raw outputs have timestamp-based names
        csv_files = list(data_dir.glob(f"{uc_num.lower()}_raw_*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV found for {uc_num} in {data_dir}")
        csv_file = csv_files[0]

    records = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            # Only process rows with the appropriate text column
            if row.get(text_column):
                records.append(row)
            if len(records) >= 500:  # Collect 500 records
                break

    return records


def load_logistic_regression_model(task_family: str, model_name: str = "qwen2.5_0.5b") -> Dict[str, Any]:
    """Load learned logistic regression model from SDDF artifacts."""
    artifact_dir = (
        Path.home() / "OneDrive" / "Desktop" / "SLM use cases" /
        "model_runs" / "sddf_training_splits_slm_only" / "sddf_pipeline_artifacts_v3" /
        task_family
    )

    if not artifact_dir.exists():
        return None

    # Find the model artifact file - pattern: qwen2.5_0.5b__seed42.json
    artifact_file = artifact_dir / f"{model_name}__seed42.json"

    if not artifact_file.exists():
        # Try with dashes instead of underscores
        artifact_file = artifact_dir / f"{model_name.replace('.', '_')}__seed42.json"

    if not artifact_file.exists():
        return None

    try:
        with open(artifact_file) as f:
            model = json.load(f)
        return model
    except Exception as e:
        return None


def compute_p_fail(features_dict: Dict[str, float], model: Dict[str, Any]) -> float:
    """
    Compute p_fail for a sample using learned logistic regression.

    p_fail = sigmoid(weights · normalized_features + bias)
    """
    feature_names = model.get("features", [])
    weights = np.array(model.get("weights", []))
    bias = float(model.get("bias", 0.0))

    # Use scaler_mean and scaler_scale (from the model) for normalization
    scaler_mean = np.array(model.get("scaler_mean", []))
    scaler_scale = np.array(model.get("scaler_scale", []))

    # If scaler info not available, try old normalization format
    if len(scaler_mean) == 0:
        normalization = model.get("normalization", {})
        scaler_mean = np.array(normalization.get("mean", []))
        scaler_scale = np.array(normalization.get("std", []))

    # Extract features in the order expected by the model
    feature_values = []
    for fname in feature_names:
        val = float(features_dict.get(fname, 0.0))
        feature_values.append(val)

    feature_values = np.array(feature_values)

    # Normalize using the fitted scaler
    if len(scaler_mean) == len(feature_values) and len(scaler_scale) == len(feature_values):
        normalized = (feature_values - scaler_mean) / (scaler_scale + 1e-8)
    else:
        # Fallback: use standard normalization
        normalized = (feature_values - np.mean(feature_values)) / (np.std(feature_values) + 1e-8)

    # Compute logit and sigmoid
    logit = np.dot(weights, normalized) + bias
    p_fail = float(sigmoid(np.array([logit]))[0])

    return p_fail


def compute_uc_routing(uc_num: str, model_names: List[str] | None = None) -> Dict[str, Any]:
    """
    Compute routing decisions and consensus ratio for a UC.

    For each model:
    - Route each row using logistic regression + frozen τ
    - Compute per-model routing ratio ρ
    - Aggregate to consensus ρ̄
    """
    if model_names is None:
        model_names = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]

    task_family = UC_TO_TASK_FAMILY.get(uc_num)
    if not task_family:
        raise ValueError(f"Unknown UC: {uc_num}")

    tau = FROZEN_TAU_CONSENSUS[task_family]

    # Load UC dataset
    try:
        records = load_uc_dataset(uc_num)
    except FileNotFoundError as e:
        return {"error": str(e), "uc": uc_num}

    if not records:
        return {"error": f"No records loaded for {uc_num}", "uc": uc_num}

    # Get the appropriate text column for this UC
    source_info = UC_DATA_SOURCE.get(uc_num)
    text_column = source_info["text_column"]

    # Load models and compute routing per model
    per_model_results = {}
    per_model_rho = {}

    for model_name in model_names:
        model = load_logistic_regression_model(task_family, model_name)
        if model is None:
            continue

        slm_routed = 0
        total = 0

        for record in records:
            try:
                # Extract features from the appropriate text column
                item_text = record.get(text_column, '')
                features_dict = extract_linguistic_features(item_text)
                p_fail = compute_p_fail(features_dict, model)
            except Exception as e:
                # Skip records with extraction errors
                continue

            total += 1
            # Route decision: SLM if p_fail < τ, else LLM
            if p_fail < tau:
                slm_routed += 1

        if total > 0:
            rho = slm_routed / total
            per_model_rho[model_name] = rho
            per_model_results[model_name] = {
                "total_rows": total,
                "slm_routed": slm_routed,
                "llm_routed": total - slm_routed,
                "rho": rho,
            }

    # Consensus aggregation
    if per_model_rho:
        rho_bar = np.mean(list(per_model_rho.values()))
    else:
        rho_bar = 0.0

    # Tier assignment
    tier = tier_from_consensus_ratio(rho_bar)

    # Get UC info
    uc_info = get_usecase_info(uc_num)

    return {
        "uc": uc_num,
        "name": uc_info["name"],
        "task_family": task_family,
        "domain": uc_info["domain"],
        "description": uc_info["description"],
        "tau_frozen": tau,
        "total_rows": sum(r["total_rows"] for r in per_model_results.values()) // len(per_model_results) if per_model_results else 0,
        "per_model_results": per_model_results,
        "per_model_rho": per_model_rho,
        "rho_bar": rho_bar,
        "tier": tier,
        "explanation": (
            f"High SLM routing confidence (rho_bar={rho_bar:.4f} >= 0.70)"
            if rho_bar >= 0.70
            else (
                f"Low SLM routing confidence (rho_bar={rho_bar:.4f} <= 0.30)"
                if rho_bar <= 0.30
                else f"Mixed routing outcomes (0.30 < rho_bar={rho_bar:.4f} < 0.70)"
            )
        ),
    }


def main():
    """Compute routing for all 8 UCs."""
    print("\n" + "=" * 100)
    print("COMPUTE EMPIRICAL UC ROUTING DECISIONS FROM SLM RESEARCH PROJECT DATA")
    print("=" * 100)

    results = {}
    for uc_num in ["UC1", "UC2", "UC3", "UC4", "UC5", "UC6", "UC7", "UC8"]:
        print(f"\nProcessing {uc_num}...")
        try:
            result = compute_uc_routing(uc_num)
            results[uc_num] = result

            if "error" not in result:
                print(
                    f"  Task family: {result['task_family']}")
                print(f"  Frozen tau: {result['tau_frozen']:.4f}")
                print(f"  Total rows: {result['total_rows']}")
                print(f"  Per-model rho: {result['per_model_rho']}")
                print(f"  Consensus rho_bar: {result['rho_bar']:.4f}")
                print(f"  Tier: {result['tier']}")
            else:
                print(f"  ERROR: {result['error']}")
        except Exception as e:
            print(f"  ERROR: {e}")
            results[uc_num] = {"error": str(e), "uc": uc_num}

    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY: EMPIRICAL UC TIER ASSIGNMENTS")
    print("=" * 100)

    tier_counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}
    for uc_num, result in results.items():
        if "error" not in result:
            tier = result["tier"]
            tier_counts[tier] += 1
            print(
                f"\n{uc_num} ({result['name']:30s}) -> {tier:6s} "
                f"(rho_bar={result['rho_bar']:.4f})"
            )

    print(f"\nTier distribution:")
    print(f"  SLM:    {tier_counts['SLM']}")
    print(f"  HYBRID: {tier_counts['HYBRID']}")
    print(f"  LLM:    {tier_counts['LLM']}")

    # Save results
    output_path = Path("model_runs/uc_empirical_routing.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
