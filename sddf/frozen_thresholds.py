"""
Frozen τ^consensus from SDDF v3 Training

Consensus thresholds learned empirically from SDDF v3 training across three SLM models
(qwen2.5_0.5b, qwen2.5_3b, qwen2.5_7b). These frozen thresholds are used at runtime
to route queries: if difficulty < τ, send to SLM; else escalate to LLM.

Computation: tau_consensus = mean(tau_0.5b, tau_3b, tau_7b) per task family
"""

from __future__ import annotations

# SDDF v3 Learned consensus thresholds per task family (seed42)
FROZEN_TAU_CONSENSUS: dict[str, float] = {
    "classification": 0.6667,           # consensus of [1.00, 0.50, 0.50]
    "code_generation": 1.0000,          # consensus of [1.00, 1.00, 1.00]
    "information_extraction": 0.9167,   # consensus of [0.75, 1.00, 1.00]
    "instruction_following": 0.9167,    # consensus of [0.75, 1.00, 1.00]
    "maths": 0.3333,                    # consensus of [1.00, 0.00, 0.00]
    "retrieval_grounded": 0.9167,       # consensus of [0.75, 1.00, 1.00]
    "summarization": 1.0000,            # consensus of [1.00, 1.00, 1.00]
    "text_generation": 1.0000,          # consensus of [1.00, 1.00, 1.00]
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
