"""
Routing module - core framework and production router

Main components:
  - ProductionRouter: Production-ready routing system (Phase 0-1-2)
  - GeneralizedRoutingFramework: Task-agnostic analysis framework
  - TaskSpec: Task specification dataclass
"""

from .production_router import ProductionRouter, AnalysisResult, RoutingDecisionRecord
from .framework import GeneralizedRoutingFramework, TaskSpec, RoutingDecision

__all__ = [
    "ProductionRouter",
    "GeneralizedRoutingFramework",
    "TaskSpec",
    "AnalysisResult",
    "RoutingDecisionRecord",
    "RoutingDecision"
]
