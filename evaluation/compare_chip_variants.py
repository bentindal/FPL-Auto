#!/usr/bin/env python3
"""
Phase 7b: Chip Timing Variant Evaluation

Runs both chip timing variants through nested_walk_forward_evaluation().
Compares against BASELINE_CURRENT (Phase 6 optimal transfer strategy).
Analyzes chip usage patterns (timing, count, effectiveness).
Outputs variant_results_7b.json with all metrics and 95% CIs.
"""

import json
from typing import Dict, List, Any
from datetime import datetime
import sys
import os

from fpl_auto.strategies import (
    BASELINE_CURRENT,
    CHIP_DOUBLES_OPTIMIZED,
    CHIP_BLANKS_OPTIMIZED,
)
from evaluation.walk_forward import nested_walk_forward_evaluation
from evaluation.metrics import bootstrap_ci, apply_bonferroni_correction, compute_season_metrics

# Phase 7b variant definitions
CHIP_VARIANTS = {
    'CHIP_DOUBLES_OPTIMIZED': CHIP_DOUBLES_OPTIMIZED,
    'CHIP_BLANKS_OPTIMIZED': CHIP_BLANKS_OPTIMIZED,
}

BASELINE_RESULTS_PATH = 'evaluation/baseline_results.json'
VARIANT_RESULTS_PATH = 'evaluation/variant_results_7b.json'

def analyze_chip_usage(chips_used: List, test_season: str) -> Dict[str, Any]:
    """
    Analyze chip usage pattern from test iteration.

    Args:
        chips_used: List of [chip_type, gw] pairs from test iteration
        test_season: Season string for fixture-based blank/double GW info

    Returns:
        Dict with chip usage analysis (count by type, timing accuracy, etc.)
    """
    # Initialize counters
    chip_counts = {
        'Triple Captain': 0,
        'Wildcard': 0,
        'Bench Boost': 0,
        'Free Hit': 0,
    }
    total_chips = 0
    chips_in_blanks = 0
    chips_in_doubles = 0

    # Get blank/double GWs for this season (using arbitrary team instance)
    # Note: This is season-specific; blank/double GWs vary year to year
    try:
        from fpl_auto.team import Team
        temp_team = Team(season=test_season, gameweek=1)
        blank_gws = set(temp_team.get_blank_gameweeks())
        double_gws = set(temp_team.get_double_gameweeks())
    except Exception:
        blank_gws = set()
        double_gws = set()

    # Count chips and analyze timing
    for chip_type, gw in chips_used:
        if chip_type in chip_counts:
            chip_counts[chip_type] += 1
            total_chips += 1

            # Check if chip was used in target window
            if gw in blank_gws or (gw - 1 in blank_gws) or (gw + 1 in blank_gws):
                chips_in_blanks += 1
            if gw in double_gws or (gw - 1 in double_gws) or (gw + 1 in double_gws):
                chips_in_doubles += 1

    timing_accuracy = (chips_in_doubles if total_chips > 0 else 0.0) / total_chips if total_chips > 0 else 0.0

    return {
        'total_chips': total_chips,
        'by_type': chip_counts,
        'timing_accuracy': float(timing_accuracy),
        'in_blank_gws': chips_in_blanks,
        'in_double_gws': chips_in_doubles,
    }

def run_chip_variant_evaluation():
    """
    Run walk-forward evaluation for both chip timing variants.

    Procedure:
    1. Load BASELINE_CURRENT results from baseline_results.json
    2. For each chip variant:
       a. Run nested_walk_forward_evaluation(variant_config)
       b. Compute metrics via compute_season_metrics() for each test iteration
       c. Analyze chip usage patterns
       d. Bootstrap 95% CIs for each metric
    3. Compare each variant vs BASELINE_CURRENT (check CI overlap)
    4. Output variant_results_7b.json with full breakdown + chip analysis
    """

    print("=" * 80)
    print("Phase 7b: Chip Timing Variant Evaluation")
    print("=" * 80)

    # Step 1: Load baseline results
    print("\n[1/4] Loading baseline results (BASELINE_CURRENT)...")
    if not os.path.exists(BASELINE_RESULTS_PATH):
        print(f"  ERROR: {BASELINE_RESULTS_PATH} not found")
        sys.exit(1)

    with open(BASELINE_RESULTS_PATH, 'r') as f:
        baseline_results = json.load(f)

    baseline_iterations = baseline_results.get('current', {}).get('test_iterations', [])
    if not baseline_iterations:
        print("  ERROR: baseline_results.json missing 'current.test_iterations'")
        sys.exit(1)

    print(f"  ✓ Loaded baseline results ({len(baseline_iterations)} test iterations)")

    # Compute baseline metrics for comparison
    baseline_metrics_list = []
    for iteration in baseline_iterations:
        metrics = iteration.get('test_metrics', {})
        baseline_metrics_list.append({
            'test_season': iteration.get('test_season', 'unknown'),
            **metrics
        })
    print(f"  ✓ Computed baseline metrics (Sharpe: {baseline_metrics_list[0]['sharpe_ratio']:.2f})")

    # Step 2: Run walk-forward for each variant
    print("\n[2/4] Running walk-forward evaluation for both chip timing variants...")
    variant_results = {}

    # Bonferroni correction for 2 variants
    num_comparisons = len(CHIP_VARIANTS)
    bonferroni_alpha = apply_bonferroni_correction(num_comparisons)
    print(f"  Using Bonferroni-corrected α = {bonferroni_alpha:.4f}")

    for variant_name, variant_config in CHIP_VARIANTS.items():
        print(f"\n  [{variant_name}] Running nested walk-forward...")

        try:
            # Run walk-forward (returns list of iteration dicts with 'test_results' key)
            test_iterations_raw = nested_walk_forward_evaluation(variant_config)

            if not test_iterations_raw:
                print(f"    WARNING: No results returned for {variant_name}")
                continue

            print(f"    ✓ Completed {len(test_iterations_raw)} test iterations")

            # Compute metrics for each test iteration
            variant_metrics_list = []
            for iteration in test_iterations_raw:
                test_results = iteration.get('test_results', {})

                # Get p_list from test_results, compute metrics if not already present
                p_list = test_results.get('p_list', [])
                if p_list:
                    metrics = compute_season_metrics(p_list)
                else:
                    # If p_list not available, use pre-computed test_metrics
                    metrics = iteration.get('test_metrics', {})

                # Analyze chip usage
                chip_analysis = analyze_chip_usage(
                    test_results.get('chips_used', []),
                    iteration.get('test_season', 'unknown')
                )

                variant_metrics_list.append({
                    'test_season': iteration.get('test_season', 'unknown'),
                    **metrics,
                    'chip_usage': chip_analysis,
                })

            if not variant_metrics_list:
                print(f"    WARNING: Could not compute metrics for {variant_name}")
                continue

            print(f"    ✓ Computed metrics (mean Sharpe: {sum(m.get('sharpe_ratio', 0) for m in variant_metrics_list) / len(variant_metrics_list):.2f})")
            print(f"    ✓ Analyzed chip usage ({sum(m['chip_usage']['total_chips'] for m in variant_metrics_list)} total chips)")

            # Bootstrap 95% CIs for key metrics
            ci_total_points = bootstrap_ci(
                variant_metrics_list,
                baseline_metrics_list,
                metric_key='total_points',
                n_bootstrap=10000,
                ci=0.95
            )

            ci_sharpe = bootstrap_ci(
                variant_metrics_list,
                metric_key='sharpe_ratio',
                n_bootstrap=10000,
                ci=0.95
            )

            # Determine significance (non-overlapping CIs)
            is_significant = (
                (ci_total_points.get('ci_lower_a', 0) > ci_total_points.get('ci_upper_b', 0)) or
                (ci_total_points.get('ci_upper_a', 0) < ci_total_points.get('ci_lower_b', 0))
            ) if 'ci_lower_b' in ci_total_points else False

            # Store results (including chip analysis)
            variant_results[variant_name] = {
                'test_iterations': [
                    {
                        'test_season': m['test_season'],
                        'total_points': m.get('total_points', 0),
                        'sharpe_ratio': m.get('sharpe_ratio', 0),
                        'sortino_ratio': m.get('sortino_ratio', 0),
                        'coefficient_variation': m.get('coefficient_variation', 0),
                        'max_drawdown': m.get('max_drawdown', 0),
                        'chip_usage': m['chip_usage'],
                    }
                    for m in variant_metrics_list
                ],
                'aggregated_metrics': {
                    'mean_total_points': sum(m.get('total_points', 0) for m in variant_metrics_list) / len(variant_metrics_list),
                    'ci_total_points_lower': ci_total_points.get('ci_lower_a', 0),
                    'ci_total_points_upper': ci_total_points.get('ci_upper_a', 0),
                    'mean_sharpe': sum(m.get('sharpe_ratio', 0) for m in variant_metrics_list) / len(variant_metrics_list),
                    'ci_sharpe_lower': ci_sharpe.get('ci_lower_a', 0),
                    'ci_sharpe_upper': ci_sharpe.get('ci_upper_a', 0),
                    'mean_chips_used': sum(sum(m['chip_usage']['by_type'].values()) for m in variant_metrics_list) / len(variant_metrics_list),
                },
                'vs_baseline': {
                    'mean_diff_total_points': ci_total_points.get('diff_mean', 0),
                    'ci_lower': ci_total_points.get('diff_ci_lower', 0),
                    'ci_upper': ci_total_points.get('diff_ci_upper', 0),
                    'significant': ci_total_points.get('significant', False),
                }
            }

            print(f"    ✓ Mean total points: {variant_results[variant_name]['aggregated_metrics']['mean_total_points']:.1f}")

        except Exception as e:
            print(f"    ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Step 3: Comparison analysis
    print("\n[3/4] Comparing chip variants vs BASELINE_CURRENT...")
    for variant_name, results in variant_results.items():
        is_sig = results['vs_baseline']['significant']
        diff = results['vs_baseline']['mean_diff_total_points']
        chips = results['aggregated_metrics']['mean_chips_used']
        sig_str = "SIGNIFICANT" if is_sig else "not significant"
        print(f"  {variant_name}: {diff:+.1f} points ({sig_str}), avg {chips:.1f} chips/season")

    # Step 4: Output results
    print("\n[4/4] Writing results to variant_results_7b.json...")
    output = {
        'metadata': {
            'phase': '07b',
            'evaluation_date': datetime.now().isoformat(),
            'variants': list(CHIP_VARIANTS.keys()),
            'test_seasons': ['2023-24', '2024-25'],
            'train_seasons': ['2021-22', '2022-23'],
            'baseline': 'BASELINE_CURRENT',
            'bonferroni_alpha': bonferroni_alpha,
        },
        'variants': variant_results,
        'baseline_metrics': {
            'mean_total_points': sum(m.get('total_points', 0) for m in baseline_metrics_list) / len(baseline_metrics_list),
            'mean_sharpe': sum(m.get('sharpe_ratio', 0) for m in baseline_metrics_list) / len(baseline_metrics_list),
        }
    }

    with open(VARIANT_RESULTS_PATH, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"  ✓ Results written to {VARIANT_RESULTS_PATH}")
    print("\n" + "=" * 80)
    print("Phase 7b evaluation complete!")
    print("=" * 80)

if __name__ == '__main__':
    run_chip_variant_evaluation()
