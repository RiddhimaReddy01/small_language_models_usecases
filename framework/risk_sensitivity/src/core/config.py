"""
SDDF Risk Sensitivity Configuration

Centralized configuration for thresholds, paths, and learned parameters
"""

import os
from pathlib import Path
import json

# ========== PROJECT ROOT ==========
# Support environment variable override
PROJECT_ROOT = Path(os.getenv(
    'SLM_PROJECT_ROOT',
    Path(__file__).parent.parent.parent.parent.parent
))

# Validate project root exists
if not (PROJECT_ROOT / "data/benchmark").exists():
    raise RuntimeError(
        f"Project root not found at {PROJECT_ROOT}\n"
        "Set SLM_PROJECT_ROOT environment variable to correct location"
    )

# ========== PATHS ==========
PATHS = {
    'project_root': PROJECT_ROOT,
    'benchmark_output': PROJECT_ROOT / "data/benchmark/benchmark_output",
    'benchmark_fixed': PROJECT_ROOT / "data/benchmark/benchmark_output_fixed",
    'benchmark_fixed_all': PROJECT_ROOT / "data/benchmark/benchmark_output_fixed_all",
    'config': PROJECT_ROOT / "data/config",
    'learned_weights': PROJECT_ROOT / "data/config/learned_sddf_weights.json",
    'output_plots': PROJECT_ROOT / "framework/risk_sensitivity/outputs/plots",
    'learned_thresholds': PROJECT_ROOT / "framework/risk_sensitivity/data/config/learned_thresholds.json",
}

# ========== HARD-CODED THRESHOLDS (Default) ==========
# These are used when learned thresholds are not available
DEFAULT_THRESHOLDS = {
    'capability_threshold': 0.8,      # τ_cau: capability drops below 0.8
    'risk_threshold': 0.3,            # τ_risk: risk exceeds 0.3
}

# ========== LEARNED THRESHOLDS (Per-Task, Data-Driven) ==========
# These are computed from analysis results and updated per run
# Format: {task: {'capability_threshold': float, 'risk_threshold': float}}
LEARNED_THRESHOLDS = {
    # Will be loaded from JSON if available, otherwise use defaults
    'text_generation': {'capability_threshold': 0.80, 'risk_threshold': 0.30},
    'code_generation': {'capability_threshold': 0.80, 'risk_threshold': 0.30},
    'classification': {'capability_threshold': 0.85, 'risk_threshold': 0.25},
    'maths': {'capability_threshold': 0.85, 'risk_threshold': 0.25},
    'summarization': {'capability_threshold': 0.80, 'risk_threshold': 0.30},
    'retrieval_grounded': {'capability_threshold': 0.80, 'risk_threshold': 0.30},
    'instruction_following': {'capability_threshold': 0.80, 'risk_threshold': 0.30},
    'information_extraction': {'capability_threshold': 0.80, 'risk_threshold': 0.30},
}

# ========== THRESHOLD FUNCTIONS ==========

def load_learned_thresholds() -> dict:
    """
    Load learned thresholds from JSON file if available

    Returns:
        Dictionary of {task: {threshold_type: value}}
    """
    threshold_file = PATHS['learned_thresholds']

    if threshold_file.exists():
        try:
            with open(threshold_file) as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"Warning: Could not load learned thresholds: {e}")

    # Return defaults if file doesn't exist
    return LEARNED_THRESHOLDS

def get_capability_threshold(task_type: str, use_learned: bool = True) -> float:
    """
    Get capability threshold for a task

    Args:
        task_type: Name of task (e.g., 'code_generation')
        use_learned: Use learned thresholds (True) or defaults (False)

    Returns:
        Capability threshold value (0-1)
    """
    if use_learned:
        thresholds = load_learned_thresholds()
    else:
        thresholds = LEARNED_THRESHOLDS

    return thresholds.get(task_type, {}).get(
        'capability_threshold',
        DEFAULT_THRESHOLDS['capability_threshold']
    )

def get_risk_threshold(task_type: str, use_learned: bool = True) -> float:
    """
    Get risk threshold for a task

    Args:
        task_type: Name of task (e.g., 'code_generation')
        use_learned: Use learned thresholds (True) or defaults (False)

    Returns:
        Risk threshold value (0-1)
    """
    if use_learned:
        thresholds = load_learned_thresholds()
    else:
        thresholds = LEARNED_THRESHOLDS

    return thresholds.get(task_type, {}).get(
        'risk_threshold',
        DEFAULT_THRESHOLDS['risk_threshold']
    )

def save_learned_thresholds(thresholds: dict) -> None:
    """
    Save learned thresholds to JSON file

    Args:
        thresholds: Dictionary of {task: {threshold_type: value}}
    """
    threshold_file = PATHS['learned_thresholds']
    threshold_file.parent.mkdir(parents=True, exist_ok=True)

    with open(threshold_file, 'w') as f:
        json.dump(thresholds, f, indent=2)

    print(f"Saved learned thresholds to {threshold_file}")

# ========== MODEL CONFIGURATION ==========
MODELS = [
    'qwen2.5_1.5b',
    'phi3_mini',
    'tinyllama_1.1b',
    'llama_llama-3.3-70b-versatile',
]

MODEL_LABELS = {
    'qwen2.5_1.5b': 'Qwen 2.5 1.5B',
    'phi3_mini': 'Phi-3 Mini',
    'tinyllama_1.1b': 'TinyLlama 1.1B',
    'llama_llama-3.3-70b-versatile': 'Llama 3.3 70B',
}

TASK_TYPES = [
    "text_generation",
    "code_generation",
    "classification",
    "maths",
    "summarization",
    "retrieval_grounded",
    "instruction_following",
    "information_extraction"
]

# ========== COMPONENT CONFIGURATION ==========
# SDDF component weights (learned from optimization)
SDDF_COMPONENTS = {
    'learned': True,  # Use learned weights from optimization
    'weights': {
        'n_in': 1/6,
        'H': 1/6,
        'R_hat': 1/6,
        'Gamma': 1/6,
        'alpha': 1/6,
        'D': 1/6,
    }
}
