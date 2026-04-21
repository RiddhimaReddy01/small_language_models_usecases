#!/usr/bin/env python3
"""
PRODUCTION DEPLOYMENT: SDDF Runtime Router for Use Cases

Complete end-to-end SDDF deployment with:
- Multi-use case support (SMS detection, product review, etc.)
- S3 manager policy enforcement (optional)
- Comprehensive reporting
- JSON export for downstream integration

Usage:
  # Single use case
  python production_deployment.py --use-case classification --sample-size 100 --output results.json

  # Batch process all use cases
  python production_deployment.py --batch --sample-size 50

  # With S3 policy enforcement
  python production_deployment.py --use-case maths --s3-tier hybrid --output results.json
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import asdict
import logging
from datetime import datetime

# Import pipeline
sys.path.insert(0, str(Path(__file__).parent))
from end_to_end_runtime_pipeline import (
    run_end_to_end_pipeline,
    UseCaseResult
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# PRODUCTION DEPLOYMENT
# ============================================================================

class ProductionDeployment:
    """Production deployment manager for SDDF runtime router"""

    TASK_FAMILIES = [
        "classification", "code_generation", "information_extraction",
        "instruction_following", "maths", "retrieval_grounded",
        "summarization", "text_generation"
    ]

    def __init__(self):
        """Initialize deployment manager"""
        self.results: Dict[str, UseCaseResult] = {}
        self.timestamp = datetime.now().isoformat()
        logger.info(f"Production Deployment Manager initialized: {self.timestamp}")

    def enforce_s3_policy(
        self,
        tier_decision: str,
        s3_tier: Optional[str] = None
    ) -> str:
        """
        Enforce S3 manager policy on tier decision.

        Args:
            tier_decision: Computed tier from SDDF (SLM/HYBRID/LLM)
            s3_tier: Manager-predetermined tier constraint (optional)

        Returns:
            Final tier after S3 enforcement
        """
        if not s3_tier:
            return tier_decision  # No constraint

        if s3_tier == "pure_slm":
            return "SLM"  # Manager requires SLM
        elif s3_tier == "llm_only":
            return "LLM"  # Manager requires LLM
        elif s3_tier == "disqualified":
            return "LLM"  # Manager disqualifies SLM
        else:  # s3_tier == "hybrid"
            return tier_decision  # Trust SDDF routing

    def run_use_case(
        self,
        use_case_name: str,
        sample_size: int = 100,
        s3_tier: Optional[str] = None,
    ) -> UseCaseResult:
        """
        Run SDDF pipeline for a single use case.

        Args:
            use_case_name: Task family or use case name
            sample_size: Number of queries to process
            s3_tier: Optional S3 manager policy constraint

        Returns:
            UseCaseResult with routing decisions and tier recommendation
        """
        logger.info(f"Starting deployment for use case: {use_case_name}")

        # Run SDDF pipeline
        result = run_end_to_end_pipeline(
            use_case_name=use_case_name,
            sample_size=sample_size,
        )

        # Apply S3 policy if provided
        if s3_tier:
            original_tier = result.predicted_tier
            result.predicted_tier = self.enforce_s3_policy(
                tier_decision=original_tier,
                s3_tier=s3_tier
            )
            logger.info(
                f"S3 policy applied: {original_tier} -> {result.predicted_tier} "
                f"(constraint: {s3_tier})"
            )

        self.results[use_case_name] = result
        return result

    def run_batch(
        self,
        sample_size: int = 50,
        s3_policies: Optional[Dict[str, str]] = None,
    ) -> Dict[str, UseCaseResult]:
        """
        Run SDDF pipeline for all task families.

        Args:
            sample_size: Queries per use case
            s3_policies: Optional {use_case: s3_tier} mapping

        Returns:
            Results dict {use_case: UseCaseResult}
        """
        logger.info(f"Starting batch deployment for {len(self.TASK_FAMILIES)} use cases")

        s3_policies = s3_policies or {}

        for use_case in self.TASK_FAMILIES:
            s3_tier = s3_policies.get(use_case)
            self.run_use_case(
                use_case_name=use_case,
                sample_size=sample_size,
                s3_tier=s3_tier,
            )

        return self.results

    def generate_report(self) -> Dict:
        """Generate comprehensive deployment report"""
        report = {
            "timestamp": self.timestamp,
            "deployment_summary": {
                "total_use_cases": len(self.results),
                "use_cases_by_tier": self._aggregate_by_tier(),
                "average_rho_bar": self._average_rho_bar(),
            },
            "per_use_case_results": {},
        }

        # Detailed results per use case
        for use_case, result in self.results.items():
            report["per_use_case_results"][use_case] = {
                "tier": result.predicted_tier,
                "rho_bar": result.rho_bar,
                "rho_0_5b": result.rho_0_5b,
                "rho_3b": result.rho_3b,
                "rho_7b": result.rho_7b,
                "total_queries": result.total_queries,
                "task_families_detected": result.task_families_detected,
            }

        return report

    def _aggregate_by_tier(self) -> Dict[str, int]:
        """Count use cases by tier"""
        counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}
        for result in self.results.values():
            counts[result.predicted_tier] += 1
        return counts

    def _average_rho_bar(self) -> float:
        """Calculate average consensus routing ratio"""
        if not self.results:
            return 0.0
        total = sum(r.rho_bar for r in self.results.values())
        return total / len(self.results)

    def save_results(self, output_file: Path):
        """Save deployment results to JSON"""
        report = self.generate_report()

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Results saved to {output_file}")

    def print_summary(self):
        """Print human-readable summary"""
        report = self.generate_report()

        print("\n" + "=" * 80)
        print("PRODUCTION DEPLOYMENT SUMMARY")
        print("=" * 80)

        print(f"\nTimestamp: {report['timestamp']}")
        print(f"Total use cases: {report['deployment_summary']['total_use_cases']}")
        print(f"Average rho_bar: {report['deployment_summary']['average_rho_bar']:.4f}")

        print("\nUse Cases by Tier:")
        for tier, count in report['deployment_summary']['use_cases_by_tier'].items():
            print(f"  {tier:<10} {count}")

        print("\nDetailed Results:")
        print(f"{'Use Case':<30} {'Tier':<10} {'rho_bar':<10} {'Queries':<10}")
        print("-" * 60)

        for use_case, details in sorted(report['per_use_case_results'].items()):
            print(
                f"{use_case:<30} {details['tier']:<10} "
                f"{details['rho_bar']:<10.4f} {details['total_queries']:<10}"
            )

        print("\nDeployment Recommendations:")
        counts = report['deployment_summary']['use_cases_by_tier']

        if counts["SLM"] > 0:
            slm_cases = [
                uc for uc, d in report['per_use_case_results'].items()
                if d['tier'] == 'SLM'
            ]
            print(f"  SLM-tier ({counts['SLM']}): {', '.join(slm_cases)}")
            print(f"    -> Deploy 0.5B model only (fastest + cheapest)")

        if counts["HYBRID"] > 0:
            hybrid_cases = [
                uc for uc, d in report['per_use_case_results'].items()
                if d['tier'] == 'HYBRID'
            ]
            print(f"  HYBRID-tier ({counts['HYBRID']}): {', '.join(hybrid_cases)}")
            print(f"    -> Deploy 0.5B + large model (ensemble/fallback)")

        if counts["LLM"] > 0:
            llm_cases = [
                uc for uc, d in report['per_use_case_results'].items()
                if d['tier'] == 'LLM'
            ]
            print(f"  LLM-tier ({counts['LLM']}): {', '.join(llm_cases)}")
            print(f"    -> Deploy large model only (safe + accurate)")

        print("\n" + "=" * 80)


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Production Deployment: SDDF Runtime Router"
    )
    parser.add_argument("--use-case", default=None, help="Single use case to deploy")
    parser.add_argument("--batch", action="store_true", help="Batch process all use cases")
    parser.add_argument("--sample-size", type=int, default=100, help="Queries per use case")
    parser.add_argument("--s3-tier", default=None,
                       choices=["pure_slm", "hybrid", "llm_only", "disqualified"],
                       help="S3 manager policy constraint")
    parser.add_argument("--output", default=None, help="Output JSON file")
    args = parser.parse_args()

    deployment = ProductionDeployment()

    if args.batch:
        # Batch process all use cases
        deployment.run_batch(sample_size=args.sample_size)
    elif args.use_case:
        # Single use case
        deployment.run_use_case(
            use_case_name=args.use_case,
            sample_size=args.sample_size,
            s3_tier=args.s3_tier,
        )
    else:
        parser.print_help()
        return 1

    # Print summary
    deployment.print_summary()

    # Save results
    if args.output:
        output_file = Path(args.output)
        deployment.save_results(output_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
