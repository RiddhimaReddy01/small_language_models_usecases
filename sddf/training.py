"""
TRAIN Phase: Paper-Aligned SDDF v3 (Section 6.2)

Wrapper around train_paper_aligned_multimodel.py that:
  1. Trains logistic regression models per task family & model
  2. Computes difficulty scores d_i = σ(w_t^T x_i^(t))
  3. Extracts failure labels F_i
  4. Computes risk R_i
  5. Saves frozen model artifacts

Output: model_artifacts_frozen.json (w_t, b, feature_names per task family)
"""

from pathlib import Path
import json
import numpy as np
from datetime import datetime
from sddf.train_paper_aligned_multimodel import (
    train_all_tasks_multimodel,
    TASK_FAMILIES,
    MODELS
)


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
