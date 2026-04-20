"""
TRAIN Phase: Paper-Aligned SDDF v3 (Multi-Model)
Train difficulty function for EACH of 3 models separately.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import numpy as np
from sklearn.linear_model import LogisticRegression
from sddf.difficulty import compute_all_features

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

def load_evaluation_results(task: str, model: str, repo_root: str | Path = None):
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
    return 0 if bool(sample.get("correct", True)) else 1

def extract_features_from_sample(sample: dict) -> dict[str, float]:
    if "difficulty_features" in sample and isinstance(sample["difficulty_features"], dict):
        return {fname: float(sample["difficulty_features"].get(fname, 0.0)) for fname in DIFFICULTY_FEATURES}
    text = sample.get("prompt", sample.get("input_text", sample.get("text", "")))
    return compute_all_features(sample, str(text or "").strip())

def prepare_feature_matrix(samples: list[dict]):
    X_list, y_list, sample_ids = [], [], []
    for sample in samples:
        sample_id = sample.get("sample_id", sample.get("id", "unknown"))
        sample_ids.append(sample_id)
        features_dict = extract_features_from_sample(sample)
        x_row = np.array([features_dict.get(fname, 0.0) for fname in DIFFICULTY_FEATURES])
        X_list.append(x_row)
        y_list.append(create_failure_label(sample))
    return np.array(X_list, dtype=float), np.array(y_list, dtype=int), sample_ids

def train_paper_aligned_single_model(task: str, model: str, repo_root: str | Path = None) -> dict[str, Any]:
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
    }

def train_all_tasks_multimodel(repo_root: str | Path = None) -> dict[str, dict[str, dict]]:
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
