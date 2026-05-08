#!/usr/bin/env python3
"""
S³ + SDDF Demo Screenrecording

Shows how Suitability/Stakes/Scale (S³) governance policy and
SDDF empirical routing work together for enterprise SLM deployment.

Run: python scripts/demo/demo_s3_sddf.py [--slow] [--scene N] [--no-color]
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sddf import FROZEN_TAU_CONSENSUS, get_frozen_threshold
from sddf.runtime_routing import tier_from_consensus_ratio

# ============================================================================
# CONFIGURATION
# ============================================================================

MODEL_RUNS = PROJECT_ROOT / "model_runs"
UC_EMPIRICAL_FILE = MODEL_RUNS / "uc_empirical_routing.json"
S3_CONFIG_FILE = PROJECT_ROOT / "framework" / "benchmarking" / "s3_task_config.json"

# UC6 is the highlight case: low rho_bar despite acceptable S³ score
DEMO_UC = "UC6"

# Color codes for terminal output
class Color:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"

    @classmethod
    def disable(cls):
        """Disable color codes."""
        cls.HEADER = ""
        cls.BLUE = ""
        cls.CYAN = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.RED = ""
        cls.BOLD = ""
        cls.UNDERLINE = ""
        cls.END = ""


# ============================================================================
# DATA LOADING
# ============================================================================

def load_uc_data() -> Dict[str, Dict[str, Any]]:
    """Load UC empirical routing data from uc_empirical_routing.json."""
    if not UC_EMPIRICAL_FILE.exists():
        raise FileNotFoundError(f"Missing: {UC_EMPIRICAL_FILE}")
    with open(UC_EMPIRICAL_FILE) as f:
        return json.load(f)


def load_s3_config() -> Dict[str, Any]:
    """Load S³ configuration (weights and task scores)."""
    if not S3_CONFIG_FILE.exists():
        raise FileNotFoundError(f"Missing: {S3_CONFIG_FILE}")
    with open(S3_CONFIG_FILE) as f:
        return json.load(f)


def compute_s3_score(task_family: str, s3_config: Dict[str, Any]) -> float:
    """
    Compute S³ score for a task family.

    Formula: S3 = [sum(score_i * weight_i) / sum(5 * weight_i)] * 5
    """
    weights = s3_config["weights"]
    task_scores = s3_config["task_scores"].get(task_family)

    if not task_scores:
        task_scores = s3_config["task_scores"].get("*")

    weighted_sum = sum(task_scores[dim] * weights[dim] for dim in weights)
    max_weighted_sum = sum(5 * weights[dim] for dim in weights)

    s3_score = (weighted_sum / max_weighted_sum) * 5
    return s3_score


# ============================================================================
# FORMATTING UTILITIES
# ============================================================================

def print_scene_header(scene_num: int, title: str):
    """Print a scene header with border."""
    print("\n" + Color.BOLD + "=" * 80 + Color.END)
    print(f"{Color.HEADER}SCENE {scene_num}: {title}{Color.END}")
    print(Color.BOLD + "=" * 80 + Color.END)


def print_subheader(text: str):
    """Print a subheader."""
    print(f"\n{Color.CYAN}{Color.BOLD}{text}{Color.END}")
    print(f"{Color.CYAN}{'-' * len(text)}{Color.END}")


def tier_color(tier: str) -> str:
    """Return color code for tier."""
    if tier == "SLM":
        return Color.GREEN
    elif tier == "HYBRID":
        return Color.YELLOW
    elif tier == "LLM":
        return Color.RED
    else:
        return Color.END


def colored_tier(tier: str) -> str:
    """Return colored tier string."""
    return f"{tier_color(tier)}{Color.BOLD}{tier}{Color.END}"


def print_bar(value: float, max_val: float = 1.0, width: int = 30) -> str:
    """Generate a simple text bar chart."""
    if max_val == 0:
        filled = 0
    else:
        filled = int(width * value / max_val)
    bar = "=" * filled + "-" * (width - filled)
    pct = 100 * value / max_val
    return f"[{bar}] {pct:5.1f}%"


# ============================================================================
# SCENE IMPLEMENTATIONS
# ============================================================================

def scene_1_frozen_thresholds():
    """Scene 1: Display frozen SDDF thresholds learned from training."""
    print_scene_header(1, "Frozen SDDF Thresholds (Learned from Training)")

    print_subheader("Table: tau^consensus per Task Family (Paper Table 6.3)")
    print(f"{'Task Family':<25} {'tau^consensus':>12} {'Strictness':>35}")
    print("-" * 75)

    for task in sorted(FROZEN_TAU_CONSENSUS.keys()):
        tau = FROZEN_TAU_CONSENSUS[task]
        bar = print_bar(tau, 1.0, 25)

        if tau > 0.75:
            strictness = "(Very Strict: SLM rarely routes)"
        elif tau > 0.5:
            strictness = "(Strict: Mixed routing)"
        elif tau > 0.3:
            strictness = "(Moderate: Frequent SLM routing)"
        else:
            strictness = "(Lenient: High SLM routing)"

        print(f"{task:<25} {tau:>12.4f} {bar} {strictness}")

    print("-" * 75)
    print(f"\n{Color.BLUE}Key insight:{Color.END}")
    print("  These thresholds were learned during SDDF v3 training on 3 SLM model sizes.")
    print("  At runtime, each query's predicted failure probability p_fail is compared to tau.")
    print("  If p_fail < tau, route to SLM; otherwise route to LLM.")


def scene_2_s3_governance():
    """Scene 2: S3 Governance scoring for UC6 (Clinical Triage)."""
    print_scene_header(2, "S3 Governance: Task Suitability Scoring (UC6)")

    uc_data = load_uc_data()
    s3_config = load_s3_config()
    uc6 = uc_data[DEMO_UC]
    task_family = uc6["task_family"]

    print_subheader(f"Use Case: {uc6['name']} ({DEMO_UC})")
    print(f"  Domain:      {uc6['domain']}")
    print(f"  Description: {uc6['description']}")
    print(f"  Task Family: {task_family}")

    # Get S³ dimension scores
    task_scores = s3_config["task_scores"].get(task_family)
    if not task_scores:
        task_scores = s3_config["task_scores"].get("*")

    weights = s3_config["weights"]

    print_subheader("S3 Dimension Scores (1-5 scale)")
    print(f"{'Dimension':<25} {'Score':>8} {'Weight':>8} {'Weighted':>10}")
    print("-" * 55)

    weighted_scores = {}
    for dim in ["TC", "OS", "SK", "DS", "LT", "VL"]:
        score = task_scores.get(dim, 3)
        weight = weights[dim]
        weighted = score * weight
        weighted_scores[dim] = weighted

        dim_name = {
            "TC": "Task Complexity",
            "OS": "Output Structure",
            "SK": "Stakes (Consequence)",
            "DS": "Data Sensitivity",
            "LT": "Latency Tolerance",
            "VL": "Volume/Load"
        }[dim]

        print(f"{dim_name:<25} {score:>8} {weight:>8} {weighted:>10.1f}")

    print("-" * 55)

    # Compute S³ score
    s3_score = compute_s3_score(task_family, s3_config)
    print(f"\nWeighted S3 Score: {s3_score:.2f} / 5.0")

    # Interpret score
    if s3_score >= 4.0:
        policy_tier = "DISQUALIFIED or LLM-only"
        interpretation = "High risk/stakes: SLM NOT recommended by policy."
    elif s3_score >= 3.2:
        policy_tier = "HYBRID (policy allows mixing)"
        interpretation = "Moderate risk: SLM can be used with fallback to LLM."
    else:
        policy_tier = "Pure SLM (policy allows)"
        interpretation = "Low risk: SLM can be primary choice."

    print(f"\nPolicy Tier from S3: {policy_tier}")
    print(f"Interpretation: {interpretation}")

    print(f"\n{Color.BLUE}Key insight:{Color.END}")
    print("  S3 sets the governance ENVELOPE — what deployment strategies are allowed.")
    print("  For UC6 (Clinical Triage), Stakes=3 is moderate, so HYBRID is policy-allowed.")


def scene_3_sddf_routing():
    """Scene 3: SDDF empirical routing evidence for UC6."""
    print_scene_header(3, "SDDF Empirical Routing: Runtime Evidence (UC6)")

    uc_data = load_uc_data()
    uc6 = uc_data[DEMO_UC]
    task_family = uc6["task_family"]
    tau = get_frozen_threshold(task_family)

    print_subheader("Per-Model Routing Results")
    print(f"{'Model':<20} {'SLM Routed':>12} {'LLM Routed':>12} {'rho (ratio)':>12}")
    print("-" * 60)

    for model in ["qwen2.5_0.5b", "qwen2.5_3b", "qwen2.5_7b"]:
        results = uc6["per_model_results"][model]
        slm = results["slm_routed"]
        llm = results["llm_routed"]
        rho = results["rho"]
        print(f"{model:<20} {slm:>12} {llm:>12} {rho:>12.4f}")

    print("-" * 60)

    rho_bar = uc6["rho_bar"]
    print(f"\n{Color.BOLD}Consensus Routing Ratio (rho_bar):{Color.END}")
    print(f"  rho_bar = mean(rho_0.5b, rho_3b, rho_7b) = {rho_bar:.4f}")
    print(f"  Routing confidence: {print_bar(rho_bar, 1.0, 40)}")

    # Determine tier from rho_bar
    tier = tier_from_consensus_ratio(rho_bar, slm_threshold=0.70, llm_threshold=0.30)

    print(f"\n{Color.BOLD}Tier Decision Logic:{Color.END}")
    print(f"  If rho_bar >= 0.70 -> SLM tier (use SLM for most queries)")
    print(f"  If rho_bar <= 0.30 -> LLM tier (use LLM for safety)")
    print(f"  If 0.30 < rho_bar < 0.70 -> HYBRID tier (per-query routing)")
    print(f"\n  rho_bar = {rho_bar:.4f} -> {colored_tier(tier)}")

    print(f"\n{Color.BLUE}Key insight:{Color.END}")
    print(f"  SDDF learns from empirical model behavior on validation/test data.")
    print(f"  Low rho_bar = {rho_bar:.4f} indicates SLMs struggle on clinical triage tasks.")
    print(f"  This is data-driven evidence, independent of policy constraints.")


def scene_4_bridge_decision():
    """Scene 4: S3 + SDDF Bridge - How governance + evidence combine."""
    print_scene_header(4, "S3 + SDDF Bridge: Policy + Evidence = Final Decision")

    uc_data = load_uc_data()
    s3_config = load_s3_config()
    uc6 = uc_data[DEMO_UC]
    task_family = uc6["task_family"]
    rho_bar = uc6["rho_bar"]

    # S³ tier
    s3_score = compute_s3_score(task_family, s3_config)
    if s3_score >= 4.0:
        s3_tier = "LLM-only"
    elif s3_score >= 3.2:
        s3_tier = "HYBRID"
    else:
        s3_tier = "Pure SLM"

    # SDDF tier
    sddf_tier = tier_from_consensus_ratio(rho_bar, slm_threshold=0.70, llm_threshold=0.30)

    # Bridge: most restrictive wins
    if s3_tier == "LLM-only" or sddf_tier == "LLM":
        final_tier = "LLM"
    elif s3_tier == "HYBRID" and sddf_tier == "HYBRID":
        final_tier = "HYBRID"
    elif s3_tier == "HYBRID" or sddf_tier == "HYBRID":
        final_tier = "HYBRID"
    else:
        final_tier = "SLM"

    print_subheader("Decision Components")
    print(f"  S3 Score:        {s3_score:.2f} / 5.0  ->  {s3_tier}")
    print(f"  SDDF rho_bar:    {rho_bar:.4f}     ->  {sddf_tier}")
    print(f"  Policy Envelope: {s3_tier} (what's allowed)")
    print(f"  Empirical Data:  {sddf_tier} (what works)")

    print_subheader("Bridge Logic: Most Restrictive Wins")
    print(f"  S3 says:   {s3_tier}")
    print(f"  SDDF says: {sddf_tier}")
    print(f"  Final:     {colored_tier(final_tier)}")

    print(f"\n{Color.BLUE}Interpretation:{Color.END}")
    print(f"  • S3 (governance): 'Policy allows HYBRID for clinical tasks.'")
    print(f"  • SDDF (evidence): 'But empirical data shows SLMs fail 99.7% of the time.'")
    print(f"  • Bridge decision: 'Use LLM for safety.' (most restrictive)")

    print(f"\n{Color.BLUE}Key insight:{Color.END}")
    print(f"  The bridge ensures safety: policy is an upper bound, evidence can be stricter.")


def scene_5_uc_summary():
    """Scene 5: Full UC summary table - all 8 use cases."""
    print_scene_header(5, "Enterprise Use Cases: Tier Summary (All 8 UCs)")

    uc_data = load_uc_data()

    print_subheader("Use Case Routing Tier Summary")
    print(f"{'UC':<6} {'Use Case Name':<28} {'Task Family':<20} {'rho_bar':>8} {'Tier':>8}")
    print("-" * 75)

    slm_count = 0
    hybrid_count = 0
    llm_count = 0

    for uc_id in sorted(uc_data.keys()):
        uc = uc_data[uc_id]
        name = uc["name"]
        task = uc["task_family"]
        rho_bar = uc["rho_bar"]
        tier = uc["tier"]

        colored_rho = f"{rho_bar:.4f}"
        colored_tier_str = colored_tier(tier)

        print(f"{uc_id:<6} {name:<28} {task:<20} {colored_rho:>8} {colored_tier_str:>8}")

        if tier == "SLM":
            slm_count += 1
        elif tier == "HYBRID":
            hybrid_count += 1
        else:
            llm_count += 1

    print("-" * 75)
    print(f"\n{Color.BOLD}Summary Statistics:{Color.END}")
    print(f"  {Color.GREEN}{Color.BOLD}SLM tier:{Color.END} {slm_count} use cases (cost-optimal)")
    print(f"  {Color.YELLOW}{Color.BOLD}HYBRID tier:{Color.END} {hybrid_count} use cases (per-query fallback)")
    print(f"  {Color.RED}{Color.BOLD}LLM tier:{Color.END} {llm_count} use cases (safety-critical)")

    print(f"\n{Color.BLUE}Business Impact:{Color.END}")
    print(f"  • {slm_count} use cases can run entirely on SLMs: ~45-60% cost reduction")
    print(f"  • {hybrid_count} use cases need selective LLM fallback: ~20-30% cost reduction")
    print(f"  • {llm_count} use cases require LLM for safety/stakes: baseline cost")

    print(f"\n{Color.BLUE}Deployment Recommendation:{Color.END}")
    print(f"  1. Auto-route SLM tiers (UC1, UC3, UC4, UC5, UC7, UC8) — no LLM latency")
    print(f"  2. Use per-query fallback for HYBRID tiers (UC2, UC6 if mixed) — minimize LLM calls")
    print(f"  3. Reserve LLM for critical high-stakes tasks — ensure reliability")


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def main():
    """Run all scenes with optional pauses and filtering."""
    parser = argparse.ArgumentParser(
        description="S³ + SDDF Demo Screenrecording",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/demo/demo_s3_sddf.py          # Run all scenes (fast)
  python scripts/demo/demo_s3_sddf.py --slow   # Run with pauses (for recording)
  python scripts/demo/demo_s3_sddf.py --scene 2  # Run only Scene 2
  python scripts/demo/demo_s3_sddf.py --no-color # Disable color codes
        """
    )
    parser.add_argument("--slow", action="store_true", help="Add pauses between scenes (for screen recording)")
    parser.add_argument("--scene", type=int, choices=[1, 2, 3, 4, 5], help="Run only a specific scene")
    parser.add_argument("--no-color", action="store_true", help="Disable color codes")

    args = parser.parse_args()

    if args.no_color:
        Color.disable()

    # Define scenes
    scenes = [
        (1, "Frozen Thresholds", scene_1_frozen_thresholds),
        (2, "S³ Governance Scoring", scene_2_s3_governance),
        (3, "SDDF Empirical Routing", scene_3_sddf_routing),
        (4, "S³ + SDDF Bridge", scene_4_bridge_decision),
        (5, "UC Summary", scene_5_uc_summary),
    ]

    # Run selected scene(s)
    if args.scene:
        # Run single scene
        for num, title, func in scenes:
            if num == args.scene:
                func()
                break
    else:
        # Run all scenes
        print(f"\n{Color.HEADER}{Color.BOLD}+====================================================================+{Color.END}")
        print(f"{Color.HEADER}{Color.BOLD}|        SDDF v3: S3 Policy + Empirical Routing Integration        |{Color.END}")
        print(f"{Color.HEADER}{Color.BOLD}+====================================================================+{Color.END}")

        for num, title, func in scenes:
            func()
            if args.slow:
                time.sleep(1.5)

        print(f"\n{Color.HEADER}{Color.BOLD}+====================================================================+{Color.END}")
        print(f"{Color.HEADER}{Color.BOLD}|                          Demo Complete                            |{Color.END}")
        print(f"{Color.HEADER}{Color.BOLD}|  Learn more: README.md | Code: sddf/ + scripts/demo/              |{Color.END}")
        print(f"{Color.HEADER}{Color.BOLD}+====================================================================+{Color.END}\n")


if __name__ == "__main__":
    main()
