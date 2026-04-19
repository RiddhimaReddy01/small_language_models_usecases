"""
VALIDATION Phase: Paper-Aligned SDDF v3 (Section 6.3)

Implements Section 6.3 specification:
  1. Feature Extraction (6.3.1): Extract x_i^(t) and compute d_i on validation set
  2. Capability & Risk Curves (6.3.1): C_m(d) and R_m(d) via binning + isotonic regression
  3. Constraint Definition (6.3.2): C_dyn = C_baseline - ε_C, R_dyn = R̄_val + ε_R
  4. Threshold Selection (6.3.3): τ_m* = max d where C_m(d) ≥ C_dyn AND R_m(d) ≤ R_dyn
  5. Consensus Threshold (6.3.3): τ_t^consensus = mean(τ_m*) across 3 models, FROZEN

Output: tau_consensus_frozen.json with τ^consensus per task family (Table 6.3)
These thresholds are FROZEN and used in test phase.
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sddf.difficulty import compute_all_features, DIFFICULTY_FEATURES
from sklearn.linear_model import LogisticRegression

TASK_FAMILIES = [
    "classification", "code_generation", "information_extraction",
    "instruction_following", "maths", "retrieval_grounded",
    "summarization", "text_generation"
]
MODELS = ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]

# Helper functions
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

def create_risk_label(sample: dict, task_family: str) -> float:
    """R_i = ErrorMagnitude_i if failed, else 0"""
    if not create_failure_label(sample):
        return 0.0
    return compute_error_magnitude(sample, task_family)

def compute_error_magnitude(sample: dict, task_family: str) -> float:
    """Compute ErrorMagnitude_i per Section 6.2.4"""
    if not create_failure_label(sample):
        return 0.0
    if task_family == 'classification':
        return 1.0 if sample.get('incorrect') else 0.0
    elif task_family == 'code_generation':
        tests_passed = sample.get('tests_passed', 0)
        tests_total = sample.get('tests_total', 1)
        return 1.0 - (tests_passed / tests_total) if tests_total > 0 else 1.0
    elif task_family == 'information_extraction':
        field_f1 = sample.get('field_f1_score', 0.0)
        return 1.0 - field_f1
    elif task_family == 'instruction_following':
        if sample.get('hard_violation', False):
            return 1.0
        constraints_sat = sample.get('constraints_satisfied', 0)
        constraints_total = sample.get('constraints_total', 1)
        return 1.0 - (constraints_sat / constraints_total) if constraints_total > 0 else 1.0
    elif task_family == 'summarization':
        similarity = sample.get('rouge_score', sample.get('similarity_score', 0.0))
        return 1.0 - similarity
    return 0.5

def compute_difficulty_score(sample: dict, model_artifact: dict) -> float:
    """Compute d_i = sigmoid(w^T x + b)"""
    features_dict = extract_features_from_sample(sample)
    x = np.array([features_dict.get(fname, 0.0) for fname in DIFFICULTY_FEATURES])
    if 'sklearn_model' in model_artifact:
        prob = model_artifact['sklearn_model'].predict_proba(x.reshape(1, -1))[0, 1]
        return float(prob)
    w = np.array(model_artifact.get('weights_w', []))
    b = model_artifact.get('intercept_b', 0.0)
    if len(w) == 0:
        return 0.5
    z = np.dot(w, x) + b
    return float(1.0 / (1.0 + np.exp(-np.clip(z, -500, 500))))

# ─────────────────────────────────────────────────────────────────────────────
# Section 6.3.1: Build Capability & Risk Curves
# ─────────────────────────────────────────────────────────────────────────────

def build_capability_curve(val_rows: list[dict], model_artifact: dict,
                          task_family: str, n_bins: int = 10) -> dict:
    """
    Build C_m(d) capability curve per Section 6.3.1.

    Args:
        val_rows: validation split samples
        model_artifact: w_t, b from training
        task_family: task family name
        n_bins: number of bins for difficulty discretization

    Returns:
        capability_curve: {
            'task_family': str,
            'bin_edges': list,
            'bin_capabilities': list,  # Ĉ_{m,t,k} per bin
            'bin_counts': list,
            'C_m': callable,  # Smooth interpolator C_m(d)
            'C_m_mono': list  # Monotonic (non-decreasing) estimates
        }
    """

    # Compute difficulty d_i for all validation samples
    difficulties = np.array([
        compute_difficulty_score(row, model_artifact)
        for row in val_rows
    ])

    # Extract capability labels (1 if correct, 0 if failed)
    capabilities = np.array([
        create_capability_label(row) for row in val_rows
    ])

    # Partition into K bins
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(difficulties, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    # Compute Ĉ_{m,t,k} = accuracy per bin
    bin_capabilities = []
    bin_counts = []

    for k in range(n_bins):
        mask = bin_indices == k
        if mask.sum() == 0:
            bin_capabilities.append(0.5)  # Default if empty bin
            bin_counts.append(0)
        else:
            cap = capabilities[mask].mean()
            bin_capabilities.append(float(cap))
            bin_counts.append(int(mask.sum()))

    # Apply isotonic regression: monotone non-decreasing
    bin_cap_mono = IsotonicRegression(
        increasing=True,  # C_m(d) increases with lower difficulty
        out_of_bounds='clip'
    )
    bin_cap_mono.fit(np.arange(n_bins), bin_capabilities)
    bin_cap_smooth = bin_cap_mono.predict(np.arange(n_bins))

    # Create smooth interpolator C_m(d)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    def C_m(d: float) -> float:
        """Smooth capability curve C_m(d)"""
        if d <= bin_centers[0]:
            return float(bin_cap_smooth[0])
        if d >= bin_centers[-1]:
            return float(bin_cap_smooth[-1])
        idx = np.searchsorted(bin_centers, d)
        if idx == 0:
            return float(bin_cap_smooth[0])
        if idx >= len(bin_centers):
            return float(bin_cap_smooth[-1])
        # Linear interpolation
        w = (d - bin_centers[idx-1]) / max(1e-6, bin_centers[idx] - bin_centers[idx-1])
        w = np.clip(w, 0, 1)
        return float((1-w) * bin_cap_smooth[idx-1] + w * bin_cap_smooth[idx])

    return {
        'task_family': task_family,
        'n_bins': n_bins,
        'bin_edges': bin_edges.tolist(),
        'bin_capabilities': bin_capabilities,
        'bin_cap_smooth': bin_cap_smooth.tolist(),
        'bin_counts': bin_counts,
        'C_m': C_m,  # Keep callable for threshold selection
        'difficulties_for_debug': difficulties.tolist()[:10]  # First 10 for inspection
    }


def build_risk_curve(val_rows: list[dict], model_artifact: dict,
                     task_family: str, n_bins: int = 10) -> dict:
    """
    Build R_m(d) risk curve per Section 6.3.1.

    Args:
        val_rows: validation split samples
        model_artifact: w_t, b from training
        task_family: task family name
        n_bins: number of bins

    Returns:
        risk_curve: {
            'task_family': str,
            'bin_edges': list,
            'bin_risks': list,  # R̂_{m,t,k} per bin
            'bin_counts': list,
            'R_m': callable,  # Smooth interpolator R_m(d)
            'R_m_mono': list  # Monotonic (non-increasing) estimates
        }
    """

    # Compute difficulty d_i for all validation samples
    difficulties = np.array([
        compute_difficulty_score(row, model_artifact)
        for row in val_rows
    ])

    # Extract risk values
    risks = np.array([
        create_risk_label(row, task_family) for row in val_rows
    ])

    # Partition into K bins
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(difficulties, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    # Compute R̂_{m,t,k} = mean risk per bin
    bin_risks = []
    bin_counts = []

    for k in range(n_bins):
        mask = bin_indices == k
        if mask.sum() == 0:
            bin_risks.append(0.5)  # Default if empty bin
            bin_counts.append(0)
        else:
            risk = risks[mask].mean()
            bin_risks.append(float(risk))
            bin_counts.append(int(mask.sum()))

    # Apply isotonic regression: monotone non-increasing
    # (Risk decreases with lower difficulty)
    bin_risk_mono = IsotonicRegression(
        increasing=False,  # R_m(d) decreases with lower difficulty
        out_of_bounds='clip'
    )
    bin_risk_mono.fit(np.arange(n_bins), bin_risks)
    bin_risk_smooth = bin_risk_mono.predict(np.arange(n_bins))

    # Create smooth interpolator R_m(d)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    def R_m(d: float) -> float:
        """Smooth risk curve R_m(d)"""
        if d <= bin_centers[0]:
            return float(bin_risk_smooth[0])
        if d >= bin_centers[-1]:
            return float(bin_risk_smooth[-1])
        idx = np.searchsorted(bin_centers, d)
        if idx == 0:
            return float(bin_risk_smooth[0])
        if idx >= len(bin_centers):
            return float(bin_risk_smooth[-1])
        # Linear interpolation
        w = (d - bin_centers[idx-1]) / max(1e-6, bin_centers[idx] - bin_centers[idx-1])
        w = np.clip(w, 0, 1)
        return float((1-w) * bin_risk_smooth[idx-1] + w * bin_risk_smooth[idx])

    return {
        'task_family': task_family,
        'n_bins': n_bins,
        'bin_edges': bin_edges.tolist(),
        'bin_risks': bin_risks,
        'bin_risk_smooth': bin_risk_smooth.tolist(),
        'bin_counts': bin_counts,
        'R_m': R_m,  # Keep callable for threshold selection
        'mean_risk': float(risks.mean())
    }


# ─────────────────────────────────────────────────────────────────────────────
# Section 6.3.2 & 6.3.3: Constraint Definition & Threshold Selection
# ─────────────────────────────────────────────────────────────────────────────

def select_routing_threshold(cap_curve: dict, risk_curve: dict,
                            c_baseline: float = 0.85,
                            epsilon_c: float = 0.05,
                            epsilon_r: float = 0.05) -> dict:
    """
    Select τ_m* per Section 6.3.2 & 6.3.3.

    Args:
        cap_curve: output from build_capability_curve()
        risk_curve: output from build_risk_curve()
        c_baseline: target capability level (e.g., 0.85)
        epsilon_c: capability margin (e.g., 0.05)
        epsilon_r: risk margin (e.g., 0.05)

    Returns:
        threshold: {
            'task_family': str,
            'model_name': str,
            'C_dyn': float,
            'R_dyn': float,
            'tau_star': float,
            'provenance': 'strict_feasible_max' | 'fallback_min_violation',
            'feasible_region': {'start': float, 'end': float},
            'C_at_tau': float,
            'R_at_tau': float
        }
    """

    # Define constraints (Section 6.3.2)
    C_dyn = c_baseline - epsilon_c
    R_dyn = risk_curve['mean_risk'] + epsilon_r

    # Access curve functions
    C_m = cap_curve['C_m']
    R_m = risk_curve['R_m']

    # Scan for feasible region
    difficulties = np.linspace(0, 1, 1000)
    feasible_region = []

    for d in difficulties:
        c_d = C_m(d)
        r_d = R_m(d)

        # Check both constraints
        if c_d >= C_dyn and r_d <= R_dyn:
            feasible_region.append(d)

    # Select threshold (Section 6.3.3)
    if feasible_region:
        # Highest d in feasible region
        tau_star = max(feasible_region)
        provenance = 'strict_feasible_max'
    else:
        # Fallback: minimize violations
        violations = []
        for d in difficulties:
            c_d = C_m(d)
            r_d = R_m(d)
            cap_violation = max(0, C_dyn - c_d)
            risk_violation = max(0, r_d - R_dyn)
            violations.append(cap_violation + risk_violation)

        tau_star = difficulties[np.argmin(violations)]
        provenance = 'fallback_min_violation'

    return {
        'task_family': cap_curve['task_family'],
        'C_dyn': float(C_dyn),
        'R_dyn': float(R_dyn),
        'tau_star': float(tau_star),
        'provenance': provenance,
        'feasible_region': {
            'start': float(feasible_region[0]) if feasible_region else None,
            'end': float(feasible_region[-1]) if feasible_region else None,
            'size': len(feasible_region)
        },
        'C_at_tau': float(C_m(tau_star)),
        'R_at_tau': float(R_m(tau_star))
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Validation Pipeline (Per Task Family)
# ─────────────────────────────────────────────────────────────────────────────

def validate_single_task_paper_spec(task_family: str,
                                    train_artifacts: dict,
                                    val_samples: list[dict],
                                    c_baseline: float = 0.85,
                                    epsilon_c: float = 0.05,
                                    epsilon_r: float = 0.05) -> dict:
    """
    Complete validation pipeline for ONE task family across 3 SLM models.

    Per Section 6.3:
      1. Build C_m(d) and R_m(d) curves per model
      2. Define constraints C_dyn, R_dyn
      3. Select τ_m* per model
      4. Compute consensus τ^consensus across 3 models
      5. Return frozen threshold

    Args:
        task_family: 'classification', 'code_generation', etc.
        train_artifacts: output from training phase
        val_samples: validation split (with split='val')
        c_baseline: target capability (default 0.85)
        epsilon_c: capability margin (default 0.05)
        epsilon_r: risk margin (default 0.05)

    Returns:
        validation_result: {
            'task_family': str,
            'tau_per_model': {'qwen2.5_0.5b': ..., '3b': ..., '7b': ...},
            'tau_consensus': float,  # FROZEN threshold per task family
            'thresholds': {...},     # Per-model details
            'timestamp': str
        }
    """

    print(f"\nVAL: {task_family.upper()}")
    print(f"  Validation samples: {len(val_samples)}")

    thresholds_by_model = {}
    tau_values = []

    if task_family not in train_artifacts:
        raise ValueError(f"Task family {task_family} not in train_artifacts")

    # Process each SLM model
    for model_name in MODELS:
        print(f"    [{model_name}] Building curves...")

        if model_name not in train_artifacts[task_family]:
            print(f"      SKIP: Model not reconstructed for {task_family}")
            continue

        model_artifact = train_artifacts[task_family][model_name]

        # Build C_m(d) curve
        cap_curve = build_capability_curve(
            val_samples, model_artifact, task_family
        )

        # Build R_m(d) curve
        risk_curve = build_risk_curve(
            val_samples, model_artifact, task_family
        )

        # Select τ_m* threshold
        threshold = select_routing_threshold(
            cap_curve, risk_curve,
            c_baseline=c_baseline,
            epsilon_c=epsilon_c,
            epsilon_r=epsilon_r
        )
        threshold['model_name'] = model_name

        thresholds_by_model[model_name] = threshold
        tau_values.append(threshold['tau_star'])

        print(f"      tau*={threshold['tau_star']:.4f} "
              f"(C={threshold['C_at_tau']:.3f}, "
              f"R={threshold['R_at_tau']:.3f}, "
              f"{threshold['provenance']})")

    # Compute consensus tau^consensus across 3 models (Section 6.3.3)
    tau_consensus = float(np.mean(tau_values))

    print(f"  FROZEN tau^consensus = {tau_consensus:.4f}")

    return {
        'task_family': task_family,
        'tau_per_model': {
            model: thresh['tau_star']
            for model, thresh in thresholds_by_model.items()
        },
        'tau_consensus': tau_consensus,  # This is FROZEN
        'thresholds': thresholds_by_model,
        'timestamp': datetime.now().isoformat()
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Validation Phase (All Task Families)
# ─────────────────────────────────────────────────────────────────────────────

def validate_all_tasks_paper_spec(train_artifacts: dict,
                                  all_samples: list[dict],
                                  repo_root: Path = None) -> dict:
    """
    Run validation phase for all task families.

    Outputs frozen τ^consensus per task family (Table 6.3 format).
    """

    if repo_root is None:
        repo_root = Path(__file__).parent.parent

    repo_root = Path(repo_root)

    print("\n" + "="*70)
    print("VALIDATION PHASE: Paper-Aligned SDDF v3 (Section 6.3)")
    print("="*70)

    results = {}

    for task_family in TASK_FAMILIES:
        # Get validation samples for this task
        val_samples = [
            s for s in all_samples
            if s.get('task') == task_family and s.get('split') == 'val'
        ]

        if not val_samples:
            print(f"\n[SKIP] {task_family}: No validation samples")
            continue

        try:
            result = validate_single_task_paper_spec(
                task_family, train_artifacts, val_samples
            )
            results[task_family] = result
        except Exception as e:
            print(f"\n[ERROR] {task_family}: {e}")
            import traceback
            traceback.print_exc()

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Save Frozen Thresholds
# ─────────────────────────────────────────────────────────────────────────────

def save_frozen_thresholds(validation_results: dict, output_path: Path):
    """
    Save frozen τ^consensus thresholds (Table 6.3 format).

    These thresholds are FROZEN after validation and used in test phase.
    They are NEVER retrained.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frozen_thresholds = {
        task: result['tau_consensus']
        for task, result in validation_results.items()
    }

    with open(output_path, 'w') as f:
        json.dump(frozen_thresholds, f, indent=2)

    print(f"\n[SAVED] Frozen tau^consensus thresholds to {output_path}")

    # Print Table 6.3 format
    print("\nFrozen tau^consensus (Table 6.3 format):")
    print("Task Family              tau^consensus")
    print("-" * 40)
    for task, tau in sorted(frozen_thresholds.items()):
        print(f"  {task:25s} {tau:.4f}")

    return frozen_thresholds


if __name__ == '__main__':
    # Example: Load training artifacts and run validation
    repo_root = Path(__file__).parent.parent

    # Load all samples from training splits
    all_samples = []
    print("Loading validation samples...")
    for task_family in TASK_FAMILIES:
        for model in MODELS:
            split_path = (
                repo_root / "model_runs" / "sddf_training_splits" /
                task_family / model / "train.jsonl"
            )
            try:
                with open(split_path) as f:
                    for line in f:
                        all_samples.append(json.loads(line))
            except FileNotFoundError:
                pass

    # Reconstruct sklearn models from frozen artifacts by refitting on training data
    print("Reconstructing sklearn models...")
    train_artifacts_with_models = {}

    for task_family in TASK_FAMILIES:
        train_artifacts_with_models[task_family] = {}

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
                    # Fallback to val samples
                    with open(split_path) as f:
                        for line in f:
                            s = json.loads(line)
                            if s.get('split') == 'val':
                                samples.append(s)

                if samples:
                    # Prepare feature matrix
                    X_list, y_list = [], []
                    for sample in samples:
                        features_dict = extract_features_from_sample(sample)
                        x_row = np.array([features_dict.get(fname, 0.0) for fname in DIFFICULTY_FEATURES])
                        X_list.append(x_row)
                        y_list.append(create_failure_label(sample))

                    X = np.array(X_list, dtype=float)
                    y = np.array(y_list, dtype=int)

                    # Refit logistic regression
                    if len(np.unique(y)) > 1:  # Only if we have both classes
                        lr_model = LogisticRegression(solver="lbfgs", max_iter=1000, random_state=42)
                        lr_model.fit(X, y)

                        train_artifacts_with_models[task_family][model_name] = {
                            'sklearn_model': lr_model,
                            'weights_w': lr_model.coef_[0].tolist(),
                            'intercept_b': float(lr_model.intercept_[0])
                        }
            except Exception as e:
                print(f"  Warning: Could not reconstruct {task_family}/{model_name}: {e}")

    # Run validation
    val_results = validate_all_tasks_paper_spec(
        train_artifacts_with_models, all_samples, repo_root
    )

    # Save frozen thresholds
    frozen_path = repo_root / "model_runs" / "tau_consensus_frozen.json"
    save_frozen_thresholds(val_results, frozen_path)

    print("\n" + "="*70)
    print("VALIDATION PHASE COMPLETE")
    print("Frozen thresholds saved and ready for test phase")
    print("="*70)
