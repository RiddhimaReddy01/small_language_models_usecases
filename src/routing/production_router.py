#!/usr/bin/env python3
"""
Production Router: Complete SLM/LLM Routing System

Implements the full pipeline from Phase 0 (Analysis) through Phase 1 (Production)
and Phase 2 (Monitoring).

Architecture:
  1. Phase 0: One-time analysis to compute capability/risk curves and tipping points
  2. Phase 1: Per-request routing based on frozen policies
  3. Phase 2: Daily monitoring for degradation

Usage:
  # Initialize with pre-computed curves and policies
  router = ProductionRouter.load_from_analysis("analysis_results.json")

  # Route a request
  model, decision = router.route(
      input_text="...",
      task="code_generation"
  )

  # Log results for monitoring
  router.log_result(task="code_generation", bin_id=2, model=model, success=True)

  # Check daily for degradation
  alerts = router.daily_monitoring_check()
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Tuple, List, Callable
import statistics
from datetime import datetime, timedelta


@dataclass
class AnalysisResult:
    """One-time analysis result from Phase 0"""
    task: str
    model: str
    capability_curve: Dict[int, float]        # C_m(b) for each bin
    risk_curve: Dict[int, float]               # Risk_m(b) for each bin
    tau_cap: Optional[int]                     # Tipping point: capability
    tau_risk: Optional[int]                    # Tipping point: risk
    zone: str                                  # Q1/Q2/Q3/Q4
    empirical_tau_c: float = 0.80              # Empirical capability threshold
    empirical_tau_r: float = 0.20              # Empirical risk threshold
    timestamp: str = ""                        # When analysis was done


@dataclass
class RoutingDecisionRecord:
    """Decision made for a single request"""
    timestamp: str
    task: str
    input_text: str                            # First 100 chars for reference
    difficulty: float
    bin_id: int
    capability: float                          # C_m(bin)
    risk: float                                # Risk_m(bin)
    zone: str                                  # Q1/Q2/Q3/Q4
    routed_model: str                          # Which model was selected
    expected_success_rate: float               # Estimated P(success)


@dataclass
class MonitoringMetric:
    """Daily monitoring metric"""
    date: str
    task: str
    model: str
    samples_processed: int
    actual_success_rate: float
    tau_cap_baseline: Optional[int]
    tau_cap_current: Optional[int]
    tau_risk_baseline: Optional[int]
    tau_risk_current: Optional[int]
    degradation_detected: bool
    alerts: List[str]


class ProductionRouter:
    """
    Production routing system with complete pipeline support

    Phase 0 (Analysis): Pre-computed offline
    Phase 1 (Production): Fast O(1) routing decisions
    Phase 2 (Monitoring): Daily degradation checks
    """

    def __init__(self):
        """Initialize empty router"""
        self.analyses: Dict[Tuple[str, str], AnalysisResult] = {}  # {(task, model): analysis}
        self.routing_logs: List[RoutingDecisionRecord] = []         # Per-request logs
        self.monitoring_metrics: List[MonitoringMetric] = []        # Daily metrics

    # ========== Phase 0: Analysis ==========

    def add_analysis_result(self, result: AnalysisResult) -> None:
        """Register a completed analysis result"""
        key = (result.task, result.model)
        self.analyses[key] = result

    def load_from_analysis(self, filepath: Path) -> 'ProductionRouter':
        """Load frozen policies from Phase 0 analysis file"""
        with open(filepath, 'r') as f:
            data = json.load(f)

        for item in data.get('analyses', []):
            result = AnalysisResult(
                task=item['task'],
                model=item['model'],
                capability_curve=item['capability_curve'],
                risk_curve=item['risk_curve'],
                tau_cap=item.get('tau_cap'),
                tau_risk=item.get('tau_risk'),
                zone=item['zone'],
                empirical_tau_c=item.get('empirical_tau_c', 0.80),
                empirical_tau_r=item.get('empirical_tau_r', 0.20),
                timestamp=item.get('timestamp', '')
            )
            self.add_analysis_result(result)

        return self

    def get_analysis(self, task: str, model: str) -> Optional[AnalysisResult]:
        """Retrieve analysis for task/model pair"""
        return self.analyses.get((task, model))

    def get_available_models(self, task: str) -> List[str]:
        """List models analyzed for this task"""
        return [model for t, model in self.analyses.keys() if t == task]

    # ========== Phase 1: Production Routing ==========

    def route(
        self,
        input_text: str,
        task: str,
        difficulty_metric: Callable[[str], float],
        preferred_model: str = "qwen"
    ) -> Tuple[str, RoutingDecisionRecord]:
        """
        Route a production request (Phase 1)

        Steps:
        1. Compute difficulty from input
        2. Assign to bin
        3. Get curves for bin
        4. Classify zone
        5. Apply zone policy
        6. Return selected model

        Args:
            input_text: The input to route
            task: Task name
            difficulty_metric: Function to compute difficulty [0, 1]
            preferred_model: SLM model to try first (e.g., "qwen")

        Returns:
            (model_name, decision_record)
        """
        # Step 12: Compute difficulty
        try:
            difficulty = difficulty_metric(input_text)
            difficulty = max(0.0, min(1.0, difficulty))  # Clamp to [0, 1]
        except:
            difficulty = 0.5
            print(f"WARNING: difficulty computation failed, using default 0.5")

        # Step 13: Assign to bin
        bin_id = min(int(difficulty * 4), 4)

        # Step 14: Get curves for bin
        analysis = self.get_analysis(task, preferred_model)
        if not analysis:
            # Fallback: use LLM if no SLM analysis available
            return "llama", RoutingDecisionRecord(
                timestamp=datetime.now().isoformat(),
                task=task,
                input_text=input_text[:100],
                difficulty=difficulty,
                bin_id=bin_id,
                capability=0.0,
                risk=1.0,
                zone="FALLBACK",
                routed_model="llama",
                expected_success_rate=0.95
            )

        capability = analysis.capability_curve.get(bin_id, 0.0)
        risk = analysis.risk_curve.get(bin_id, 0.5)

        # Step 15: Classify zone
        tau_c = analysis.empirical_tau_c
        tau_r = analysis.empirical_tau_r

        zone = self._classify_zone(capability, risk, tau_c, tau_r)

        # Step 16: Apply zone policy
        routed_model = self._apply_zone_policy(
            zone=zone,
            model=preferred_model,
            bin_id=bin_id,
            tau_cap=analysis.tau_cap,
            capability=capability,
            risk=risk
        )

        # Expected success rate for this routing
        if routed_model == preferred_model:
            expected_success = max(0.0, capability * (1 - risk))
        else:
            expected_success = 0.95  # LLM baseline

        # Step 17: Create decision record
        decision = RoutingDecisionRecord(
            timestamp=datetime.now().isoformat(),
            task=task,
            input_text=input_text[:100],
            difficulty=difficulty,
            bin_id=bin_id,
            capability=capability,
            risk=risk,
            zone=zone,
            routed_model=routed_model,
            expected_success_rate=expected_success
        )

        self.routing_logs.append(decision)
        return routed_model, decision

    def _classify_zone(self, capability: float, risk: float, tau_c: float, tau_r: float) -> str:
        """Classify into Q1/Q2/Q3/Q4 based on thresholds"""
        if capability >= tau_c and risk <= tau_r:
            return "Q1"  # High Cap, Low Risk -> SLM
        elif capability >= tau_c and risk > tau_r:
            return "Q2"  # High Cap, High Risk -> SLM + Verify
        elif capability < tau_c and risk <= tau_r:
            return "Q3"  # Low Cap, Low Risk -> Hybrid
        else:
            return "Q4"  # Low Cap, High Risk -> LLM

    def _apply_zone_policy(
        self,
        zone: str,
        model: str,
        bin_id: int,
        tau_cap: Optional[int],
        capability: float,
        risk: float
    ) -> str:
        """Apply zone-specific routing policy"""
        if zone == "Q1":
            # Zone 1: Pure SLM - model is safe on all difficulties
            return model

        elif zone == "Q2":
            # Zone 2: SLM + Verify + Escalate
            # Try SLM first, escalate if verification fails
            # For now, return SLM (verification happens later)
            return model

        elif zone == "Q3":
            # Zone 3: Hybrid - SLM for easy, LLM for hard
            if tau_cap is not None and bin_id <= tau_cap:
                return model  # Easy enough for SLM
            else:
                return "llama"  # Too hard, use LLM

        else:  # zone == "Q4"
            # Zone 4: Pure LLM - model is too weak
            return "llama"

    # ========== Phase 2: Monitoring ==========

    def log_result(
        self,
        task: str,
        model: str,
        bin_id: int,
        success: bool
    ) -> None:
        """Log an actual result for monitoring (Phase 2)"""
        # This would be called after actual inference completes
        # Store in time-series database in production
        pass

    def daily_monitoring_check(self) -> List[str]:
        """
        Daily monitoring check (Phase 2)

        Recompute tipping points from yesterday's data and alert if degraded.
        """
        alerts = []

        # Group logs by task/model/date
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        for (task, model), analysis in self.analyses.items():
            # Collect yesterday's results for this task/model
            yesterday_logs = [
                log for log in self.routing_logs
                if log.task == task and
                datetime.fromisoformat(log.timestamp).date() == yesterday
            ]

            if not yesterday_logs:
                continue  # No new data

            # Recompute tipping points from yesterday's data
            # (simplified - in production would use actual results DB)
            success_rates = {}
            for bin_id in range(5):
                bin_logs = [log for log in yesterday_logs if log.bin_id == bin_id]
                if bin_logs:
                    # Would read actual success from results DB
                    avg_capability = statistics.mean([log.capability for log in bin_logs])
                    success_rates[bin_id] = avg_capability

            # Detect new tipping points
            new_tau_cap = self._detect_tau_cap(success_rates)
            new_tau_risk = self._detect_tau_risk(success_rates)

            # Compare to baseline
            old_tau_cap = analysis.tau_cap
            old_tau_risk = analysis.tau_risk

            if new_tau_cap is not None and old_tau_cap is not None:
                if new_tau_cap < old_tau_cap:
                    alerts.append(
                        f"ALERT: {task}/{model} capability degraded: "
                        f"tau_cap {old_tau_cap} -> {new_tau_cap}"
                    )

            if new_tau_risk is not None and old_tau_risk is not None:
                if new_tau_risk < old_tau_risk:
                    alerts.append(
                        f"ALERT: {task}/{model} risk escalated: "
                        f"tau_risk {old_tau_risk} -> {new_tau_risk}"
                    )

        return alerts

    def _detect_tau_cap(self, success_rates: Dict[int, float]) -> Optional[int]:
        """Detect capability tipping point from success rates"""
        tau_cap = None
        for b in range(5):
            if b in success_rates and success_rates[b] >= 0.80:
                tau_cap = b
        return tau_cap

    def _detect_tau_risk(self, success_rates: Dict[int, float]) -> Optional[int]:
        """Detect risk tipping point from success rates"""
        for b in range(5):
            if b in success_rates and (1 - success_rates[b]) > 0.20:
                return b
        return None

    # ========== Utilities ==========

    def get_routing_summary(self) -> Dict:
        """Get summary of routing decisions made"""
        if not self.routing_logs:
            return {"total_requests": 0}

        by_model = {}
        by_zone = {}
        by_task = {}

        for log in self.routing_logs:
            # By model
            if log.routed_model not in by_model:
                by_model[log.routed_model] = 0
            by_model[log.routed_model] += 1

            # By zone
            if log.zone not in by_zone:
                by_zone[log.zone] = 0
            by_zone[log.zone] += 1

            # By task
            if log.task not in by_task:
                by_task[log.task] = 0
            by_task[log.task] += 1

        return {
            "total_requests": len(self.routing_logs),
            "by_model": by_model,
            "by_zone": by_zone,
            "by_task": by_task,
            "average_difficulty": statistics.mean([log.difficulty for log in self.routing_logs]),
            "average_expected_success": statistics.mean([log.expected_success_rate for log in self.routing_logs])
        }

    def export_to_json(self, filepath: Path) -> None:
        """Export router state to JSON"""
        data = {
            "analyses": [
                {
                    **asdict(analysis),
                    "timestamp": analysis.timestamp or datetime.now().isoformat()
                }
                for analysis in self.analyses.values()
            ],
            "routing_logs": [
                asdict(log)
                for log in self.routing_logs
            ],
            "monitoring_metrics": [
                asdict(metric)
                for metric in self.monitoring_metrics
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def import_from_json(self, filepath: Path) -> 'ProductionRouter':
        """Import router state from JSON"""
        with open(filepath, 'r') as f:
            data = json.load(f)

        for item in data.get('analyses', []):
            result = AnalysisResult(**item)
            self.add_analysis_result(result)

        for item in data.get('routing_logs', []):
            self.routing_logs.append(RoutingDecisionRecord(**item))

        for item in data.get('monitoring_metrics', []):
            self.monitoring_metrics.append(MonitoringMetric(**item))

        return self


# ============================================================================
# Example Usage
# ============================================================================

def example_usage():
    """
    Example: Complete pipeline workflow

    Phase 0: Analysis (done once during setup)
    Phase 1: Production routing (per request)
    Phase 2: Monitoring (daily)
    """
    print("=" * 80)
    print("PRODUCTION ROUTER EXAMPLE")
    print("=" * 80)

    # Initialize router
    router = ProductionRouter()

    # Phase 0: Register analysis results
    # (In practice, these come from generate_complete_analysis.py)
    qwen_analysis = AnalysisResult(
        task="code_generation",
        model="qwen",
        capability_curve={
            0: 0.67,  # Easy: 67% success
            1: 0.80,  # Medium: 80% success
            2: 0.80,  # Med-hard: 80% success
            3: 0.67,  # Hard: 67% success
            4: 0.73   # V.Hard: 73% success
        },
        risk_curve={
            0: 0.33,  # Easy: 33% risk
            1: 0.20,  # Medium: 20% risk
            2: 0.20,  # Med-hard: 20% risk
            3: 0.33,  # Hard: 33% risk
            4: 0.27   # V.Hard: 27% risk
        },
        tau_cap=2,     # Capable through bin 2
        tau_risk=0,    # Risky from bin 0
        zone="Q4",     # Low cap, high risk -> use LLM
        empirical_tau_c=0.80,
        empirical_tau_r=0.20,
        timestamp=datetime.now().isoformat()
    )
    router.add_analysis_result(qwen_analysis)

    llama_analysis = AnalysisResult(
        task="code_generation",
        model="llama",
        capability_curve={0: 0.87, 1: 0.87, 2: 0.80, 3: 0.87, 4: 0.87},
        risk_curve={0: 0.133, 1: 0.133, 2: 0.200, 3: 0.133, 4: 0.133},
        tau_cap=4,     # Capable on everything
        tau_risk=None, # Never risky
        zone="Q1",     # High cap, low risk -> use SLM (but Llama IS the SLM here)
        empirical_tau_c=0.80,
        empirical_tau_r=0.20,
        timestamp=datetime.now().isoformat()
    )
    router.add_analysis_result(llama_analysis)

    print("\nPhase 0: Analysis Complete")
    print(f"  Registered {len(router.analyses)} analyses")
    for (task, model), analysis in router.analyses.items():
        print(f"    {task}/{model}: zone {analysis.zone}")

    # Phase 1: Production routing
    print("\n" + "=" * 80)
    print("PHASE 1: PRODUCTION ROUTING")
    print("=" * 80)

    def code_difficulty(text: str) -> float:
        """Estimate code complexity from prompt length"""
        return min(len(text) / 1000, 1.0)

    test_cases = [
        ("Write a function to reverse a list", 0.1),      # Easy
        ("Implement quicksort with custom comparator", 0.4),  # Medium
        ("Build a distributed consensus algorithm", 0.8),  # Hard
    ]

    for prompt, expected_diff in test_cases:
        model, decision = router.route(
            input_text=prompt,
            task="code_generation",
            difficulty_metric=code_difficulty,
            preferred_model="qwen"
        )

        print(f"\nInput: {prompt[:50]}...")
        print(f"  Difficulty: {decision.difficulty:.2f} (expected: {expected_diff:.2f})")
        print(f"  Bin: {decision.bin_id}")
        print(f"  Capability: {decision.capability:.2f}, Risk: {decision.risk:.2f}")
        print(f"  Zone: {decision.zone}")
        print(f"  Routed to: {model}")
        print(f"  Expected success rate: {decision.expected_success_rate:.1%}")

    # Routing summary
    print("\n" + "=" * 80)
    print("ROUTING SUMMARY")
    print("=" * 80)
    summary = router.get_routing_summary()
    print(f"Total requests: {summary['total_requests']}")
    print(f"By model: {summary['by_model']}")
    print(f"By zone: {summary['by_zone']}")
    print(f"Average difficulty: {summary['average_difficulty']:.2f}")
    print(f"Average expected success: {summary['average_expected_success']:.1%}")

    # Phase 2: Monitoring (simulated)
    print("\n" + "=" * 80)
    print("PHASE 2: DAILY MONITORING")
    print("=" * 80)
    alerts = router.daily_monitoring_check()
    if alerts:
        print("Alerts:")
        for alert in alerts:
            print(f"  {alert}")
    else:
        print("No degradation detected")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    example_usage()
