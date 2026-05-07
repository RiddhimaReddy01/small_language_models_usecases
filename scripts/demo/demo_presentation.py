#!/usr/bin/env python3
"""
Clean, audience-ready presentation demo.
Four sequential scenes demonstrating SDDF routing and consensus mechanisms.

Run: python scripts/demo/demo_presentation.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sddf import FROZEN_TAU_CONSENSUS, get_frozen_threshold
from sddf.runtime_routing import consensus_routing_ratio, tier_from_consensus_ratio


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
MODEL_RUNS = PROJECT_ROOT / "model_runs"
UC_EMPIRICAL_FILE = MODEL_RUNS / "uc_empirical_routing.json"


# ============================================================================
# UTILITIES
# ============================================================================

def load_uc_data() -> Dict[str, Dict[str, Any]]:
    """Load UC empirical routing data."""
    if not UC_EMPIRICAL_FILE.exists():
        raise FileNotFoundError(f"Data file not found: {UC_EMPIRICAL_FILE}")
    with open(UC_EMPIRICAL_FILE) as f:
        return json.load(f)


def print_header(scene_num: int, title: str):
    """Print formatted scene header."""
    print("\n" + "=" * 80)
    print(f"SCENE {scene_num}: {title}")
    print("=" * 80)


def print_bar(value: float, max_val: float = 1.0, width: int = 40, label: str = ""):
    """Print a simple text bar chart (ASCII-safe)."""
    filled = int(width * value / max_val)
    bar = "=" * filled + "-" * (width - filled)
    pct = 100 * value / max_val
    return f"[{bar}] {pct:5.1f}% {label}"


# ============================================================================
# SCENE 1: FROZEN THRESHOLDS
# ============================================================================

def scene1_frozen_thresholds():
    """Print Table 6.3: Frozen tau^consensus values with visual bars."""
    print_header(1, "Frozen Thresholds (Paper Table 6.3)")

    print("\nFrozen tau^consensus per Task Family:")
    print("-" * 60)
    print(f"{'Task Family':<25} {'tau':>8} {'Strictness':>25}")
    print("-" * 60)

    for task in sorted(FROZEN_TAU_CONSENSUS.keys()):
        tau = FROZEN_TAU_CONSENSUS[task]
        bar = print_bar(tau, 1.0, 20, "(stricter)" if tau > 0.7 else "(moderate)" if tau > 0.3 else "(lenient)")
        print(f"{task:<25} {tau:>8.4f} {bar}")

    print("-" * 60)
    print("\nInterpretation:")
    print("  - Strictness = threshold difficulty for SLM routing")
    print("  - Higher tau = harder for SLM to handle => more likely to route to LLM")
    print("  - Example: code_generation tau=1.00 => SLM almost always routes to LLM")
    print("  -         maths tau=0.33 => SLM routes to LLM when failure prob > 33%")


# ============================================================================
# SCENE 2: SINGLE QUERY ROUTING
# ============================================================================

def scene2_query_routing():
    """Step-by-step trace of single query routing decision."""
    print_header(2, "Single Query Routing (Paper Section 7.2)")

    task_family = "classification"
    tau = get_frozen_threshold(task_family)

    print(f"\nTask: {task_family}")
    print(f"Frozen threshold tau = {tau:.4f}")
    print("\nRouting logic: if p_fail < tau => SLM, else => LLM\n")

    test_queries = [
        ("Easy query (low complexity)", 0.2),
        ("Medium query (moderate complexity)", 0.5),
        ("Hard query (high complexity)", 0.8),
    ]

    for desc, p_fail in test_queries:
        comparison = "<" if p_fail < tau else ">="
        decision = "SLM" if p_fail < tau else "LLM"
        confidence = "confident" if abs(p_fail - tau) > 0.2 else "borderline"

        print(f"  {desc}:")
        print(f"    p_fail = {p_fail:.2f} {comparison} tau={tau:.4f}")
        print(f"    => Route to {decision:>4s}  ({confidence})")
        print()


# ============================================================================
# SCENE 3: CONSENSUS MECHANISM
# ============================================================================

def scene3_consensus_mechanism():
    """Compare consensus across models (UC5 perfect, UC2 divergent, UC6 low)."""
    print_header(3, "Consensus Aggregation (Paper Section 7.3)")

    uc_data = load_uc_data()

    # Three showcase UCs
    showcase = {
        "UC5": {
            "name": "Automated Code Review",
            "label": "PERFECT CONSENSUS",
            "color": "OK"
        },
        "UC2": {
            "name": "Invoice Field Extraction",
            "label": "DIVERGENT (HIGH VARIANCE)",
            "color": "WN"
        },
        "UC6": {
            "name": "Clinical Triage",
            "label": "LOW CONSENSUS (NEEDS LLM)",
            "color": "XX"
        },
    }

    for uc_id, meta in showcase.items():
        if uc_id not in uc_data:
            continue

        uc_info = uc_data[uc_id]
        per_model_rho = uc_info["per_model_rho"]
        rho_bar = uc_info["rho_bar"]
        tier = uc_info["tier"]

        print(f"\n[{meta['color']}] {uc_id}: {meta['name']}")
        print(f"  Label: {meta['label']}")
        print(f"  Task: {uc_info['task_family']}")
        print()

        # Per-model routing ratios
        print("  Per-model routing ratios (rho):")
        for model, rho in sorted(per_model_rho.items()):
            bar = print_bar(rho, 1.0, 20, "")
            print(f"    {model:<15}: {bar}")

        # Consensus
        print()
        print(f"  Consensus rho_bar = mean([rho_0.5b, rho_3b, rho_7b]) = {rho_bar:.4f}")
        print(f"  => Assigned tier: {tier}")

        # Explanation
        if rho_bar >= 0.50:
            reason = f"rho_bar={rho_bar:.4f} >= 0.50 => high confidence in SLM"
        elif rho_bar < 0.30:
            reason = f"rho_bar={rho_bar:.4f} < 0.30 => low confidence, route to LLM"
        else:
            reason = f"rho_bar={rho_bar:.4f} in [0.30, 0.50] => mixed, use per-query routing"

        print(f"  Reason: {reason}")
        print()


# ============================================================================
# SCENE 4: ALL 8 UC DECISIONS
# ============================================================================

def scene4_all_uc_decisions():
    """Print tier assignment for all 8 UCs."""
    print_header(4, "All 8 Use Case Tier Assignments")

    uc_data = load_uc_data()
    uc_names = sorted(uc_data.keys())

    print("\nUse Case Tier Assignments:")
    print("-" * 90)
    print(f"{'UC':<5} {'Name':<30} {'Task Family':<20} {'rho_bar':<10} {'Tier':<8} {'Confidence':<10}")
    print("-" * 90)

    tier_counts = {"SLM": 0, "HYBRID": 0, "LLM": 0}

    for uc in uc_names:
        info = uc_data[uc]
        name = info["name"][:28]
        task = info["task_family"][:18]
        rho_bar = info["rho_bar"]
        tier = info["tier"]
        tier_counts[tier] += 1

        # Confidence indicator
        if rho_bar >= 0.70:
            confidence = "High"
        elif rho_bar >= 0.50:
            confidence = "Moderate"
        elif rho_bar > 0.30:
            confidence = "Moderate"
        else:
            confidence = "Low"

        print(f"{uc:<5} {name:<30} {task:<20} {rho_bar:>8.4f} {tier:<8} {confidence:<10}")

    print("-" * 90)
    print(f"\nSummary:")
    print(f"  - SLM tier:   {tier_counts['SLM']}/8 use cases (100% SLM, no LLM fallback)")
    print(f"  - HYBRID:     {tier_counts['HYBRID']}/8 use cases (smart per-query routing)")
    print(f"  - LLM tier:   {tier_counts['LLM']}/8 use cases (always use LLM)")
    print()
    print(f"  Coverage: {tier_counts['SLM']}/8 = {100*tier_counts['SLM']/8:.1f}% of workload can use SLM exclusively")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run all 4 scenes."""
    print("\n" + "=" * 80)
    print("SDDF PRESENTATION DEMO: Frozen Thresholds, Query Routing & Consensus")
    print("=" * 80)

    try:
        scene1_frozen_thresholds()
        scene2_query_routing()
        scene3_consensus_mechanism()
        scene4_all_uc_decisions()

        print("\n" + "=" * 80)
        print("Demo Complete!")
        print("=" * 80)
        return 0

    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
