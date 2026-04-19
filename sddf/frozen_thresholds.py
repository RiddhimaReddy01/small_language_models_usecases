"""
Frozen Thresholds from Paper Table 6.3 (Section 6.3.3)

These are the consensus τ^consensus values computed across the three SLM candidates
{qwen2.5_0.5b, qwen2.5_3b, qwen2.5_7b} in the paper's original experiments.

These values are FROZEN and should be used directly in runtime routing, not re-learned.

Reference: "A Unified Framework for Enterprise SLM Deployment: S³ Policy and SDDF
Empirical Validation", Table 6.3 (Threshold Selection section)
"""

from __future__ import annotations

# Paper Table 6.3: Frozen consensus thresholds per task family
FROZEN_TAU_CONSENSUS: dict[str, float] = {
    "classification": 0.6667,
    "code_generation": 0.6667,
    "information_extraction": 1.0000,
    "instruction_following": 1.0000,
    "maths": 0.3333,
    "retrieval_grounded": 1.0000,
    "summarization": 0.2972,
    "text_generation": 0.9333,
}


def get_frozen_threshold(task_family: str) -> float:
    """
    Get frozen τ^consensus for a task family.

    Args:
        task_family: One of the 8 task families

    Returns:
        Frozen consensus threshold from paper Table 6.3

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
