from __future__ import annotations

from typing import Literal


Tier = Literal["pure_slm", "hybrid", "llm_only", "disqualified"]
RouteState = Literal["SLM", "HYBRID_ABSTAIN", "BASELINE"]


def enforce_runtime_policy(
    final_tier: Tier,
    proposed_route_state: str,
    allow_pure_slm_escalation: bool = True,
) -> RouteState:
    """
    Enforce S3 final-tier constraints on runtime routing decisions.

    - disqualified / llm_only: never allow SLM path -> BASELINE
    - hybrid: allow SLM or fallback lanes
    - pure_slm: prefer SLM; optional controlled escalation
    """
    route = str(proposed_route_state or "").strip().upper()
    if route not in {"SLM", "HYBRID_ABSTAIN", "BASELINE"}:
        route = "BASELINE"

    if final_tier in {"disqualified", "llm_only"}:
        return "BASELINE"

    if final_tier == "hybrid":
        return "HYBRID_ABSTAIN" if route == "HYBRID_ABSTAIN" else ("BASELINE" if route == "BASELINE" else "SLM")

    # pure_slm
    if route == "SLM":
        return "SLM"
    if allow_pure_slm_escalation:
        return "BASELINE" if route == "BASELINE" else "HYBRID_ABSTAIN"
    return "SLM"
