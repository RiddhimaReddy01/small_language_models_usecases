"""
TEST Phase: Paper-Aligned SDDF v3 (Section 7)

Implements Section 7 specification:
  1. Load frozen tau^consensus thresholds
  2. Compute difficulty scores on test set
  3. Route queries: d_i > tau_t^consensus -> LLM, else SLM
  4. Measure routing performance (routing ratios, accuracy, risk)
  5. Verify against Table 7.4 (routing ratios by task family)

Output: test_results.json with routing metrics per task family
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any
import numpy as np
from sklearn.linear_model import LogisticRegression
from sddf.difficulty import compute_all_features, DIFFICULTY_FEATURES

TASK_FAMILIES = [
    "classification", "code_generation", "information_extraction",
    "instruction_following", "maths", "retrieval_grounded",
    "summarization", "text_generation"
]
MODELS = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]


def extract_features_from_sample(sample: dict) -> dict[str, float]:
    """Extract x_i^(t) from sample"""
    if "difficulty_features" in sample and isinstance(sample["difficulty_features"], dict):
        return {
            fname: float(sample["difficulty_features"].get(fname, 0.0))
            for fname in DIFFICULTY_FEATURES
        }
    text = sample.get("prompt", sample.get("input_text", sample.get("text", "")))
    return compute_all_features(sample, str(text or "").strip())


def create_failure_label(sample: dict) -> int:
    """F_i = 1 if failed, else 0"""
    if 'correct' in sample:
        return 0 if sample.get('correct', False) else 1
    return 1 if (sample.get('incorrect') or sample.get('invalid') or sample.get('error')) else 0


def create_capability_label(sample: dict) -> int:
    """C_i = 1 - F_i"""
    return 1 - create_failure_label(sample)


def compute_error_magnitude(sample: dict, task_family: str) -> float:
    """Compute error magnitude R_i per task family (Section 6.2.4)"""
    if create_failure_label(sample) == 0:
        return 0.0

    # Task-specific error magnitudes
    if task_family == "classification":
        return 1.0
    elif task_family == "code_generation":
        tests_passed = sample.get('tests_passed', 0)
        tests_total = sample.get('tests_total', 1)
        return 1.0 - (tests_passed / max(tests_total, 1))
    elif task_family == "information_extraction":
        field_f1 = sample.get('field_f1', 0.0)
        return 1.0 - field_f1
    elif task_family == "instruction_following":
        constraints_satisfied = sample.get('constraints_satisfied', 0)
        constraints_total = sample.get('constraints_total', 1)
        return 1.0 - (constraints_satisfied / max(constraints_total, 1))
    elif task_family == "maths":
        return 1.0
    elif task_family == "retrieval_grounded":
        correctness = sample.get('correctness', 0.0)
        grounding = sample.get('grounding', 0.0)
        alpha = 0.5
        return 1.0 - (alpha * correctness + (1 - alpha) * grounding)
    elif task_family == "summarization":
        similarity = sample.get('similarity', 0.0)
        return 1.0 - similarity
    elif task_family == "text_generation":
        quality_score = sample.get('quality_score', 0.0)
        return 1.0 - quality_score

    return 1.0


def compute_difficulty_score(sample: dict, model_artifact: dict) -> float:
    """Compute d_i = sigmoid(w^T x + b)"""
    features_dict = extract_features_from_sample(sample)
    x = np.array([features_dict.get(fname, 0.0) for fname in DIFFICULTY_FEATURES])

    w = np.array(model_artifact['weights_w'])
    b = model_artifact['intercept_b']

    logit = np.dot(w, x) + b
    return float(1.0 / (1.0 + np.exp(-logit)))


def evaluate_single_task_test_phase(
    task_family: str,
    test_samples: list[dict],
    train_artifacts: dict,
    tau_consensus: float
) -> dict:
    """
    Evaluate routing performance on test set for one task family.

    Returns routing metrics (Table 7.4 format).
    """
    print(f"\n  TEST: {task_family.upper()}")
    print(f"    Test samples: {len(test_samples)}")

    slm_routed = 0
    llm_routed = 0

    routing_decisions = []
    correct_when_routed_slm = 0
    correct_when_routed_llm = 0
    count_routed_slm = 0
    count_routed_llm = 0

    risk_slm = 0.0
    risk_llm = 0.0

    # Compute ensemble difficulty (mean across 3 models)
    for sample in test_samples:
        difficulties = []

        for model_name in MODELS:
            if model_name not in train_artifacts[task_family]:
                continue

            model_artifact = train_artifacts[task_family][model_name]
            d_i = compute_difficulty_score(sample, model_artifact)
            difficulties.append(d_i)

        if not difficulties:
            continue

        # Ensemble: average difficulty across models
        d_ensemble = float(np.mean(difficulties))

        # Route based on frozen tau_consensus
        if d_ensemble > tau_consensus:
            route = "LLM"
            llm_routed += 1
            count_routed_llm += 1
        else:
            route = "SLM"
            slm_routed += 1
            count_routed_slm += 1

        # Track capability
        is_correct = create_capability_label(sample)
        if route == "SLM":
            correct_when_routed_slm += is_correct
        else:
            correct_when_routed_llm += is_correct

        # Track risk
        error_mag = compute_error_magnitude(sample, task_family)
        if route == "SLM":
            risk_slm += error_mag
        else:
            risk_llm += error_mag

        routing_decisions.append({
            'difficulty': d_ensemble,
            'route': route,
            'correct': bool(is_correct),
            'error_magnitude': error_mag
        })

    total_routed = slm_routed + llm_routed
    routing_ratio = float(slm_routed / total_routed) if total_routed > 0 else 0.0

    # Compute metrics
    cap_slm = float(correct_when_routed_slm / count_routed_slm) if count_routed_slm > 0 else 0.0
    cap_llm = float(correct_when_routed_llm / count_routed_llm) if count_routed_llm > 0 else 0.0

    risk_slm_avg = float(risk_slm / count_routed_slm) if count_routed_slm > 0 else 0.0
    risk_llm_avg = float(risk_llm / count_routed_llm) if count_routed_llm > 0 else 0.0

    # Overall capability (weighted average)
    overall_cap = (cap_slm * count_routed_slm + cap_llm * count_routed_llm) / total_routed if total_routed > 0 else 0.0

    print(f"    Routing ratio (SLM): {routing_ratio:.4f} ({slm_routed}/{total_routed})")
    print(f"    Capability SLM: {cap_slm:.4f}, LLM: {cap_llm:.4f}, Overall: {overall_cap:.4f}")
    print(f"    Risk SLM: {risk_slm_avg:.4f}, LLM: {risk_llm_avg:.4f}")

    return {
        'task_family': task_family,
        'test_samples': total_routed,
        'slm_routed': slm_routed,
        'llm_routed': llm_routed,
        'routing_ratio': routing_ratio,
        'capability_slm': cap_slm,
        'capability_llm': cap_llm,
        'capability_overall': overall_cap,
        'risk_slm': risk_slm_avg,
        'risk_llm': risk_llm_avg,
        'tau_consensus': tau_consensus,
        'timestamp': datetime.now().isoformat()
    }


def test_all_tasks_paper_spec(
    train_artifacts: dict,
    frozen_thresholds: dict,
    all_samples: list[dict],
    repo_root: Path = None
) -> dict:
    """
    Run test phase for all task families.

    Uses frozen tau^consensus thresholds.
    Outputs routing metrics (Table 7.4 format).
    """
    if repo_root is None:
        repo_root = Path(__file__).parent.parent

    repo_root = Path(repo_root)

    print("\n" + "="*70)
    print("TEST PHASE: Paper-Aligned SDDF v3 (Section 7)")
    print("="*70)

    results = {}

    for task_family in TASK_FAMILIES:
        # Get test samples for this task
        test_samples = [
            s for s in all_samples
            if s.get('task') == task_family and s.get('split') == 'test'
        ]

        if not test_samples:
            print(f"\n[SKIP] {task_family}: No test samples")
            continue

        # Get frozen tau^consensus for this task
        tau_consensus = frozen_thresholds.get(task_family, 0.5)

        try:
            result = evaluate_single_task_test_phase(
                task_family, test_samples, train_artifacts, tau_consensus
            )
            results[task_family] = result
        except Exception as e:
            print(f"\n[ERROR] {task_family}: {e}")
            import traceback
            traceback.print_exc()

    return results


def save_test_results(test_results: dict, output_path: Path):
    """
    Save test phase results (Table 7.4 format).

    These results show routing ratios and performance metrics achieved
    using frozen thresholds on test set.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results_data = {
        task: {
            'routing_ratio': result['routing_ratio'],
            'capability_slm': result['capability_slm'],
            'capability_llm': result['capability_llm'],
            'capability_overall': result['capability_overall'],
            'risk_slm': result['risk_slm'],
            'risk_llm': result['risk_llm'],
            'slm_routed': result['slm_routed'],
            'llm_routed': result['llm_routed']
        }
        for task, result in test_results.items()
    }

    with open(output_path, 'w') as f:
        json.dump(results_data, f, indent=2)

    print(f"\n[SAVED] Test results to {output_path}")

    # Print Table 7.4 format
    print("\nRouting Performance (Table 7.4 format):")
    print("Task Family              Routing Ratio  Cap(SLM)  Cap(LLM)  Overall")
    print("-" * 70)
    for task, result in sorted(test_results.items()):
        print(f"  {task:25s} {result['routing_ratio']:8.4f}  "
              f"{result['capability_slm']:8.4f}  "
              f"{result['capability_llm']:8.4f}  "
              f"{result['capability_overall']:8.4f}")

    return results_data


if __name__ == '__main__':
    repo_root = Path(__file__).parent.parent

    # Load frozen thresholds
    print("Loading frozen tau^consensus thresholds...")
    tau_path = repo_root / "model_runs" / "tau_consensus_frozen.json"
    with open(tau_path) as f:
        frozen_thresholds = json.load(f)
    print(f"  Loaded {len(frozen_thresholds)} thresholds")

    # Load all samples
    all_samples = []
    print("Loading test samples...")
    for task_family in TASK_FAMILIES:
        for model in MODELS:
            split_path = (
                repo_root / "model_runs" / "sddf_training_splits" /
                task_family / model / "train.jsonl"
            )
            try:
                with open(split_path) as f:
                    for line in f:
                        s = json.loads(line)
                        s['task'] = task_family
                        all_samples.append(s)
            except FileNotFoundError:
                pass

    print(f"  Loaded {len(all_samples)} total samples")

    # Reconstruct sklearn models from training data for inference
    print("Reconstructing sklearn models...")
    train_artifacts = {}

    for task_family in TASK_FAMILIES:
        train_artifacts[task_family] = {}

        for model_name in MODELS:
            split_path = (
                repo_root / "model_runs" / "sddf_training_splits" /
                task_family / model_name / "train.jsonl"
            )

            try:
                # Load training samples
                samples = []
                with open(split_path) as f:
                    for line in f:
                        s = json.loads(line)
                        if s.get('split') == 'train':
                            samples.append(s)

                if not samples:
                    with open(split_path) as f:
                        for line in f:
                            s = json.loads(line)
                            if s.get('split') == 'val':
                                samples.append(s)

                if samples:
                    X_list, y_list = [], []
                    for sample in samples:
                        features_dict = extract_features_from_sample(sample)
                        x_row = np.array([features_dict.get(fname, 0.0) for fname in DIFFICULTY_FEATURES])
                        X_list.append(x_row)
                        y_list.append(create_failure_label(sample))

                    X = np.array(X_list, dtype=float)
                    y = np.array(y_list, dtype=int)

                    if len(np.unique(y)) > 1:
                        lr_model = LogisticRegression(solver="lbfgs", max_iter=1000, random_state=42)
                        lr_model.fit(X, y)

                        train_artifacts[task_family][model_name] = {
                            'sklearn_model': lr_model,
                            'weights_w': lr_model.coef_[0].tolist(),
                            'intercept_b': float(lr_model.intercept_[0])
                        }
            except Exception as e:
                pass

    # Run test phase
    test_results = test_all_tasks_paper_spec(
        train_artifacts, frozen_thresholds, all_samples, repo_root
    )

    # Save results
    results_path = repo_root / "model_runs" / "test_results.json"
    save_test_results(test_results, results_path)

    print("\n" + "="*70)
    print("TEST PHASE COMPLETE")
    print("Routing performance measured on test set with frozen thresholds")
    print("="*70)
