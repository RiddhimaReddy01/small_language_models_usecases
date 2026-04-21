"""
Frozen τ^consensus from Paper Test Phase

These are the official consensus threshold values reported in the paper's test phase results
(Paper Table 6.3, Section 7.3). These thresholds are frozen at runtime and used to route
all queries: if p_fail < τ, send to SLM; else send to LLM.

These values are determined during the testing phase and must NOT be changed at runtime.
They represent the maximum difficulty level where SLM matches LLM performance on both
capability and risk constraints.

Source: Paper Table 6.3 (Test Phase Results)
"""

from __future__ import annotations

# Frozen τ^consensus from Paper Test Phase (Table 6.3)
# These are the official thresholds for runtime routing
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
