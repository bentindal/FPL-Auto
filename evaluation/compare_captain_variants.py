#!/usr/bin/env python3
"""
Phase 7a: Captain Strategy Variant Evaluation

Runs all 3 captain variants through nested_walk_forward_evaluation().
Compares against BASELINE_CURRENT (Phase 6 optimal transfer strategy).
Outputs variant_results_7a.json with all metrics and 95% CIs.

Test setup:
- Train seasons: 2021-22, 2022-23
- Test seasons: 2023-24, 2024-25
- Locked transfer params: CONSERVATIVE_FULL (Phase 6 optimal)
- Locked chip_schedule: 'conservative'
"""

import json
from typing import Dict, List, Any
from datetime import datetime
import sys
import os

from fpl_auto.strategies import (
    BASELINE_CURRENT,
    CAPTAIN_HIGHEST_XP,
    CAPTAIN_FORM_BASED,
    CAPTAIN_HIGHEST_VALUE,
)
from evaluation.walk_forward import nested_walk_forward_evaluation
from evaluation.metrics import bootstrap_ci, apply_bonferroni_correction, compute_season_metrics

# Phase 7a variant definitions
CAPTAIN_VARIANTS = {
    'CAPTAIN_HIGHEST_XP': CAPTAIN_HIGHEST_XP,
    'CAPTAIN_FORM_BASED': CAPTAIN_FORM_BASED,
    'CAPTAIN_HIGHEST_VALUE': CAPTAIN_HIGHEST_VALUE,
}

BASELINE_RESULTS_PATH = 'evaluation/baseline_results.json'
VARIANT_RESULTS_PATH = 'evaluation/variant_results_7a.json'


def run_captain_variant_evaluation():
    """
    Run walk-forward evaluation for all 3 captain variants.

    Procedure:
    1. Load BASELINE_CURRENT results from baseline_results.json
    2. For each captain variant:
       a. Run nested_walk_forward_evaluation(variant_config)
       b. Compute metrics via compute_season_metrics() for each test iteration
       c. Bootstrap 95% CIs for each metric
    3. Compare each variant vs BASELINE_CURRENT (check CI overlap)
    4. Output variant_results_7a.json with full breakdown
    """

    print("=" * 80)
    print("Phase 7a: Captain Strategy Variant Evaluation")
    print("=" * 80)

    # Step 1: Load baseline results
    print("\n[1/4] Loading baseline results (BASELINE_CURRENT)...")
    if not os.path.exists(BASELINE_RESULTS_PATH):
        print(f"  ERROR: {BASELINE_RESULTS_PATH} not found")
        print("  Make sure Phase 5 has completed and baseline_results.json exists")
        sys.exit(1)

    with open(BASELINE_RESULTS_PATH, 'r') as f:
        baseline_results = json.load(f)

    # Extract BASELINE_CURRENT results (test iterations)
    baseline_iterations = baseline_results.get('current', {}).get('test_iterations', [])
    if not baseline_iterations:
        print("  ERROR: baseline_results.json missing 'current.test_iterations'")
        sys.exit(1)

    print(f"  ✓ Loaded baseline results ({len(baseline_iterations)} test iteration(s))")

    # Compute baseline metrics for comparison
    baseline_metrics_list = []
    for iteration in baseline_iterations:
        test_metrics = iteration.get('test_metrics', {})
        baseline_metrics_list.append({
            'test_season': iteration.get('test_season', 'unknown'),
            'total_points': test_metrics.get('total_points', 0),
            'sharpe_ratio': test_metrics.get('sharpe_ratio', 0),
            'sortino_ratio': test_metrics.get('sortino_ratio', 0),
            'coefficient_variation': test_metrics.get('coefficient_variation', 0),
            'max_drawdown': test_metrics.get('max_drawdown', 0),
        })

    if baseline_metrics_list:
        baseline_sharpe = baseline_metrics_list[0]['sharpe_ratio']
        print(f"  ✓ Computed baseline metrics (Sharpe: {baseline_sharpe:.2f})")

    # Step 2: Run walk-forward for each variant
    print("\n[2/4] Running walk-forward evaluation for all 3 captain variants...")
    variant_results = {}

    # Bonferroni correction for 3 variants
    num_comparisons = len(CAPTAIN_VARIANTS)
    bonferroni_alpha = apply_bonferroni_correction(num_comparisons)
    print(f"  Using Bonferroni-corrected α = {bonferroni_alpha:.4f}")

    for variant_name, variant_config in CAPTAIN_VARIANTS.items():
        print(f"\n  [{variant_name}] Running nested walk-forward...")

        try:
            # Run walk-forward (returns 2 test iterations for test seasons 2023-24, 2024-25)
            test_iterations = nested_walk_forward_evaluation(variant_config)

            if not test_iterations:
                print(f"    WARNING: No results returned for {variant_name}")
                continue

            print(f"    ✓ Completed {len(test_iterations)} test iteration(s)")

            # Compute metrics for each test iteration (extract from test_metrics)
            variant_metrics_list = []
            for iteration in test_iterations:
                # Get metrics from the test_metrics field in the iteration
                test_metrics = iteration.get('test_metrics', {})
                variant_metrics_list.append({
                    'test_season': iteration.get('test_season', 'unknown'),
                    'total_points': test_metrics.get('total_points', 0),
                    'sharpe_ratio': test_metrics.get('sharpe_ratio', 0),
                    'sortino_ratio': test_metrics.get('sortino_ratio', 0),
                    'coefficient_variation': test_metrics.get('coefficient_variation', 0),
                    'max_drawdown': test_metrics.get('max_drawdown', 0),
                })

            if variant_metrics_list:
                mean_sharpe = sum(m['sharpe_ratio'] for m in variant_metrics_list) / len(variant_metrics_list)
                print(f"    ✓ Computed metrics (mean Sharpe: {mean_sharpe:.2f})")

            # Bootstrap 95% CIs for key metrics
            # For variant vs baseline comparison
            try:
                ci_total_points = bootstrap_ci(
                    variant_metrics_list,
                    baseline_metrics_list,
                    metric_key='total_points',
                    n_bootstrap=10000,
                    ci=0.95
                )
            except Exception as e:
                print(f"    WARNING: Could not compute total_points CI: {e}")
                ci_total_points = {}

            try:
                ci_sharpe = bootstrap_ci(
                    variant_metrics_list,
                    baseline_metrics_list,
                    metric_key='sharpe_ratio',
                    n_bootstrap=10000,
                    ci=0.95
                )
            except Exception as e:
                print(f"    WARNING: Could not compute sharpe_ratio CI: {e}")
                ci_sharpe = {}

            try:
                ci_sortino = bootstrap_ci(
                    variant_metrics_list,
                    baseline_metrics_list,
                    metric_key='sortino_ratio',
                    n_bootstrap=10000,
                    ci=0.95
                )
            except Exception as e:
                print(f"    WARNING: Could not compute sortino_ratio CI: {e}")
                ci_sortino = {}

            # Determine significance (non-overlapping CIs)
            # Significant if CI for difference excludes 0
            is_significant = ci_total_points.get('significant', False)

            # Compute aggregated metrics
            mean_total_points = sum(m['total_points'] for m in variant_metrics_list) / len(variant_metrics_list) if variant_metrics_list else 0
            mean_sharpe = sum(m['sharpe_ratio'] for m in variant_metrics_list) / len(variant_metrics_list) if variant_metrics_list else 0
            mean_sortino = sum(m['sortino_ratio'] for m in variant_metrics_list) / len(variant_metrics_list) if variant_metrics_list else 0

            # Store results
            variant_results[variant_name] = {
                'test_iterations': [
                    {
                        'test_season': m['test_season'],
                        'total_points': m['total_points'],
                        'sharpe_ratio': m['sharpe_ratio'],
                        'sortino_ratio': m['sortino_ratio'],
                        'coefficient_variation': m['coefficient_variation'],
                        'max_drawdown': m['max_drawdown'],
                    }
                    for m in variant_metrics_list
                ],
                'aggregated_metrics': {
                    'mean_total_points': mean_total_points,
                    'ci_total_points_lower': ci_total_points.get('ci_lower_a', 0),
                    'ci_total_points_upper': ci_total_points.get('ci_upper_a', 0),
                    'mean_sharpe': mean_sharpe,
                    'ci_sharpe_lower': ci_sharpe.get('ci_lower_a', 0),
                    'ci_sharpe_upper': ci_sharpe.get('ci_upper_a', 0),
                    'mean_sortino': mean_sortino,
                    'ci_sortino_lower': ci_sortino.get('ci_lower_a', 0),
                    'ci_sortino_upper': ci_sortino.get('ci_upper_a', 0),
                },
                'vs_baseline': {
                    'mean_diff_total_points': ci_total_points.get('diff_mean', 0),
                    'ci_lower': ci_total_points.get('diff_ci_lower', 0),
                    'ci_upper': ci_total_points.get('diff_ci_upper', 0),
                    'significant': is_significant,
                }
            }

            print(f"    ✓ Mean total points: {mean_total_points:.1f}")

        except Exception as e:
            print(f"    ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Step 3: Comparison analysis
    print("\n[3/4] Comparing variants vs BASELINE_CURRENT...")
    for variant_name, results in variant_results.items():
        is_sig = results['vs_baseline']['significant']
        diff = results['vs_baseline']['mean_diff_total_points']
        sig_str = "SIGNIFICANT" if is_sig else "not significant"
        print(f"  {variant_name}: {diff:+.1f} points ({sig_str})")

    # Step 4: Output results
    print("\n[4/4] Writing results to variant_results_7a.json...")

    # Compute baseline metrics summary
    baseline_mean_total = sum(m['total_points'] for m in baseline_metrics_list) / len(baseline_metrics_list) if baseline_metrics_list else 0
    baseline_mean_sharpe = sum(m['sharpe_ratio'] for m in baseline_metrics_list) / len(baseline_metrics_list) if baseline_metrics_list else 0
    baseline_mean_sortino = sum(m['sortino_ratio'] for m in baseline_metrics_list) / len(baseline_metrics_list) if baseline_metrics_list else 0

    output = {
        'metadata': {
            'phase': '07a',
            'evaluation_date': datetime.now().isoformat(),
            'variants': list(CAPTAIN_VARIANTS.keys()),
            'test_seasons': ['2023-24', '2024-25'],
            'train_seasons': ['2021-22', '2022-23'],
            'baseline': 'BASELINE_CURRENT',
            'bonferroni_alpha': bonferroni_alpha,
        },
        'variants': variant_results,
        'baseline_metrics': {
            'mean_total_points': baseline_mean_total,
            'mean_sharpe': baseline_mean_sharpe,
            'mean_sortino': baseline_mean_sortino,
        }
    }

    with open(VARIANT_RESULTS_PATH, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"  ✓ Results written to {VARIANT_RESULTS_PATH}")
    print("\n" + "=" * 80)
    print("Phase 7a evaluation complete!")
    print("=" * 80)


if __name__ == '__main__':
    run_captain_variant_evaluation()
