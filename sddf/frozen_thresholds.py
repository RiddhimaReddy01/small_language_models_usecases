"""
Frozen τ^consensus from SDDF v3 Training

Consensus thresholds learned empirically from SDDF v3 training across three SLM models
(qwen2.5_0.5b, qwen2.5_3b, qwen2.5_7b). These frozen thresholds are used at runtime
to route queries: if difficulty < τ, send to SLM; else escalate to LLM.

Computation: tau_consensus = mean(tau_0.5b, tau_3b, tau_7b) per task family
"""

from __future__ import annotations

# Paper Table IV: Learned consensus thresholds per task family
# Source: Validation phase with capability/risk curves and constraints
FROZEN_TAU_CONSENSUS: dict[str, float] = {
    "classification": 0.6667,           # Mean C(τ*) = 0.3145, Mean R(τ*) = 0.3428
    "code_generation": 0.6667,          # Mean C(τ*) = 0.3044, Mean R(τ*) = 0.3478
    "information_extraction": 1.0000,   # Mean C(τ*) = 0.7037, Mean R(τ*) = 0.1481
    "instruction_following": 1.0000,    # Mean C(τ*) = 0.7133, Mean R(τ*) = 0.1433
    "maths": 0.3333,                    # Mean C(τ*) = 0.1439, Mean R(τ*) = 0.4280
    "retrieval_grounded": 1.0000,       # Mean C(τ*) = 0.5159, Mean R(τ*) = 0.2421
    "summarization": 0.2972,            # Mean C(τ*) = 0.8350, Mean R(τ*) = 0.0825
    "text_generation": 0.9333,          # Mean C(τ*) = 0.8479, Mean R(τ*) = 0.0761
}


def get_frozen_threshold(task_family: str) -> float:
    """
    Get learned τ^consensus for a task family from SDDF v3 training.

    Args:
        task_family: One of the 8 task families

    Returns:
        Learned consensus threshold from SDDF v3 (seed42), not Paper Table 6.3

    Raises:
        ValueError if task_family not found
    """
    if task_family not in FROZEN_TAU_CONSENSUS:
        raise ValueError(
            f"Unknown task family: {task_family}. "
            f"Valid families: {sorted(FROZEN_TAU_CONSENSUS.keys())}"
        )
    return FROZEN_TAU_CONSENSUS[task_family]


def validate_task_family(task_family: str) -> bool:
    """Check if task_family has a frozen threshold."""
    return task_family in FROZEN_TAU_CONSENSUS


def all_frozen_thresholds() -> dict[str, float]:
    """Return copy of all frozen thresholds."""
    return dict(FROZEN_TAU_CONSENSUS)
