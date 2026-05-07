"""
TRAIN Phase: Paper-Aligned SDDF v3 (Section 6.2)

Trains logistic regression models per task family & model:
  1. Trains logistic regression models per task family & model
  2. Computes difficulty scores d_i = σ(w_t^T x_i^(t))
  3. Extracts failure labels F_i
  4. Computes risk R_i
  5. Saves frozen model artifacts

Output: model_artifacts_frozen.json (w_t, b, feature_names per task family)
"""

from __future__ import annotations
from pathlib import Path
import json
import numpy as np
from datetime import datetime
from typing import Any
from sklearn.linear_model import LogisticRegression
from sddf.difficulty import compute_all_features

# ============================================================================
# CONSTANTS
# ============================================================================

DIFFICULTY_FEATURES = [
    "n_in", "entropy", "reasoning_proxy", "constraint_count",
    "parametric_dependence", "dependency_distance",
    "reasoning_x_constraint", "length_x_entropy", "knowledge_x_reasoning",
    "classification_ambiguity", "classification_negation_density", "classification_domain_shift",
    "math_numeric_density", "math_symbol_density", "math_precision_cues",
    "instruction_format_strictness", "instruction_prohibition_count",
    "instruction_step_count", "instruction_conflict_cues",
]

TASK_FAMILIES = ["classification", "code_generation", "information_extraction",
                 "instruction_following", "maths", "retrieval_grounded", "summarization", "text_generation"]
MODELS = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def load_evaluation_results(task: str, model: str, repo_root: str | Path = None):
    """Load train/val/test splits for a specific task and model."""
    if repo_root is None:
        repo_root = Path(__file__).parent.parent
    base_path = Path(repo_root) / "model_runs" / "sddf_training_splits" / task / model
    splits = {}
    for split in ["train", "val", "test"]:
        samples = []
        with open(base_path / f"{split}.jsonl") as f:
            for line in f:
                samples.append(json.loads(line))
        splits[split] = samples
    return splits["train"], splits["val"], splits["test"]


def create_failure_label(sample: dict) -> int:
    """Extract failure label (0=success, 1=failure) from sample."""
    return 0 if bool(sample.get("correct", True)) else 1


def extract_features_from_sample(sample: dict) -> dict[str, float]:
    """Extract difficulty features from a single sample."""
    if "difficulty_features" in sample and isinstance(sample["difficulty_features"], dict):
        return {fname: float(sample["difficulty_features"].get(fname, 0.0)) for fname in DIFFICULTY_FEATURES}
    text = sample.get("prompt", sample.get("input_text", sample.get("text", "")))
    return compute_all_features(sample, str(text or "").strip())


def prepare_feature_matrix(samples: list[dict]):
    """Prepare feature matrix, labels, and sample IDs from samples."""
    X_list, y_list, sample_ids = [], [], []
    for sample in samples:
        sample_id = sample.get("sample_id", sample.get("id", "unknown"))
        sample_ids.append(sample_id)
        features_dict = extract_features_from_sample(sample)
        x_row = np.array([features_dict.get(fname, 0.0) for fname in DIFFICULTY_FEATURES])
        X_list.append(x_row)
        y_list.append(create_failure_label(sample))
    return np.array(X_list, dtype=float), np.array(y_list, dtype=int), sample_ids

# ============================================================================
# CORE TRAINING FUNCTIONS
# ============================================================================

def train_paper_aligned_single_model(task: str, model: str, repo_root: str | Path = None) -> dict[str, Any]:
    """Train logistic regression for difficulty prediction on a single task/model pair."""
    print(f"\nTRAIN: {task.upper()} [{model}]")
    train_samples, val_samples, test_samples = load_evaluation_results(task, model, repo_root)
    X_train, y_train, train_ids = prepare_feature_matrix(train_samples)
    X_val, y_val, val_ids = prepare_feature_matrix(val_samples)
    X_test, y_test, test_ids = prepare_feature_matrix(test_samples)

    lr_model = LogisticRegression(solver="lbfgs", max_iter=1000, random_state=42)
    lr_model.fit(X_train, y_train)

    d_train = lr_model.predict_proba(X_train)[:, 1]
    d_val = lr_model.predict_proba(X_val)[:, 1]
    d_test = lr_model.predict_proba(X_test)[:, 1]

    return {
        "task": task, "model": model,
        "sklearn_model": lr_model,
        "scores_val": {sid: float(d) for sid, d in zip(val_ids, d_val)},
        "scores_test": {sid: float(d) for sid, d in zip(test_ids, d_test)},
        "val_samples": val_samples, "test_samples": test_samples,
        "val_failure_labels": {sid: int(y) for sid, y in zip(val_ids, y_val)},
        "test_failure_labels": {sid: int(y) for sid, y in zip(test_ids, y_test)},
        "metrics": {"val_capability": float(1.0 - np.mean(y_val)), "test_capability": float(1.0 - np.mean(y_test))},
        "feature_names": DIFFICULTY_FEATURES,
    }


def train_all_tasks_multimodel(repo_root: str | Path = None) -> dict[str, dict[str, dict]]:
    """Train logistic regression models for all task families and models."""
    results = {}
    for task in TASK_FAMILIES:
        results[task] = {}
        for model in MODELS:
            try:
                result = train_paper_aligned_single_model(task, model, repo_root)
                results[task][model] = result
            except Exception as e:
                print(f"ERROR {task}/{model}: {e}")
    return results

# ============================================================================
# SERIALIZATION FUNCTIONS
# ============================================================================

def save_frozen_artifacts(training_results: dict, output_path: Path):
    """
    Save frozen model artifacts (w_t, b, feature_names) from training results.

    These artifacts are used in validation and test phases.
    They should NEVER be retrained after this point.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frozen_artifacts = {}

    for task_family, model_dict in training_results.items():
        frozen_artifacts[task_family] = {}

        for model_name, result in model_dict.items():
            sklearn_model = result['sklearn_model']

            frozen_artifacts[task_family][model_name] = {
                'task_family': task_family,
                'model_name': model_name,
                'weights_w': sklearn_model.coef_[0].tolist(),
                'intercept_b': float(sklearn_model.intercept_[0]),
                'feature_names': result.get('feature_names', []),
                'n_features': len(sklearn_model.coef_[0]),
                'sklearn_classes': sklearn_model.classes_.tolist(),
                'sklearn_n_iter': int(sklearn_model.n_iter_[0]),
                'training_timestamp': datetime.now().isoformat()
            }

    with open(output_path, 'w') as f:
        json.dump(frozen_artifacts, f, indent=2)

    print(f"\n[SAVED] Frozen model artifacts to {output_path}")
    return frozen_artifacts


def save_training_summary(training_results: dict, output_path: Path):
    """
    Save training summary (metrics across splits).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {}

    for task_family, model_dict in training_results.items():
        summary[task_family] = {}

        for model_name, result in model_dict.items():
            summary[task_family][model_name] = {
                'val_capability': result['metrics'].get('val_capability', 0.0),
                'test_capability': result['metrics'].get('test_capability', 0.0),
                'task': result['task'],
                'model': result['model'],
                'timestamp': datetime.now().isoformat()
            }

    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"[SAVED] Training summary to {output_path}")


if __name__ == '__main__':
    repo_root = Path(__file__).parent.parent

    print("\n" + "="*70)
    print("TRAIN PHASE: Paper-Aligned SDDF v3 (Section 6.2)")
    print("="*70)

    # Train all task families & models
    results = train_all_tasks_multimodel(repo_root)

    # Save frozen artifacts
    artifacts_path = repo_root / "model_runs" / "model_artifacts_frozen.json"
    save_frozen_artifacts(results, artifacts_path)

    # Save summary
    summary_path = repo_root / "model_runs" / "training_summary.json"
    save_training_summary(results, summary_path)

    print("\n" + "="*70)
    print("TRAIN PHASE COMPLETE")
    print("Frozen artifacts saved and ready for validation phase")
    print("="*70)
