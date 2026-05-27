#!/usr/bin/env python3
"""
Phase 6: Compare transfer strategy variants using walk-forward validation.

Runs all 5 variants through nested_walk_forward_evaluation().
Computes 95% bootstrapped CIs for each variant.
Compares against baselines (BASELINE_STATIC, BASELINE_CURRENT).
Outputs variant_results.json with all metrics.
"""

import json
import os
import sys
from typing import Dict, List, Any

# Ensure the parent directory is in the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fpl_auto.strategies import (
    CONSERVATIVE_EARLY, CONSERVATIVE_FULL, BASELINE_MID,
    AGGRESSIVE_LATE, AGGRESSIVE_FULL
)
from evaluation.walk_forward import nested_walk_forward_evaluation
from evaluation.metrics import bootstrap_ci, apply_bonferroni_correction

VARIANTS = {
    'CONSERVATIVE_EARLY': CONSERVATIVE_EARLY,
    'CONSERVATIVE_FULL': CONSERVATIVE_FULL,
    'BASELINE_MID': BASELINE_MID,
    'AGGRESSIVE_LATE': AGGRESSIVE_LATE,
    'AGGRESSIVE_FULL': AGGRESSIVE_FULL,
}

BASELINE_RESULTS_PATH = 'evaluation/baseline_results.json'
VARIANT_RESULTS_PATH = 'evaluation/variant_results.json'


def run_variant_evaluation():
    """Run walk-forward for all variants and compute CIs."""
    print("=" * 80)
    print("Phase 6: Transfer Variant Evaluation")
    print("=" * 80)

    # Load baseline results
    print("\n[1/3] Loading baseline results...")
    with open(BASELINE_RESULTS_PATH, 'r') as f:
        baselines = json.load(f)
    print(f"  Loaded baselines: {list(baselines.keys())}")

    # Run walk-forward for each variant
    print("\n[2/3] Running walk-forward evaluation for all variants...")
    variant_results = {}

    for variant_name, variant_config in VARIANTS.items():
        print(f"\n  Running {variant_name}...")
        test_iterations = nested_walk_forward_evaluation(variant_config)

        # Extract test metrics per iteration
        test_metrics_per_iteration = [
            iteration['test_metrics']
            for iteration in test_iterations
        ]

        variant_results[variant_name] = {
            'strategy_config': {
                'transfer_mode': variant_config.transfer_mode,
                'transfer_budget_per_gw': variant_config.transfer_budget_per_gw,
                'transfer_window_gw_range': variant_config.transfer_window_gw_range,
                'transfer_xp_threshold': variant_config.transfer_xp_threshold,
                'transfer_xp_threshold_mode': variant_config.transfer_xp_threshold_mode,
                'captain_mode': variant_config.captain_mode,
                'chip_schedule': variant_config.chip_schedule,
            },
            'test_iterations': test_iterations,
            'confidence_intervals': compute_confidence_intervals(test_metrics_per_iteration),
        }

        print(f"    ✓ {variant_name} complete ({len(test_iterations)} iterations)")

    # Compute statistical comparison vs baselines
    print("\n[3/3] Computing statistical comparisons...")
    variant_results['significance_report'] = compute_significance_report(
        variant_results, baselines
    )

    # Save results
    print(f"\nSaving results to {VARIANT_RESULTS_PATH}...")
    with open(VARIANT_RESULTS_PATH, 'w') as f:
        json.dump(variant_results, f, indent=2, default=str)

    print("\n" + "=" * 80)
    print("Phase 6 Evaluation Complete")
    print("=" * 80)

    return variant_results


def compute_confidence_intervals(test_metrics_per_iteration: List[Dict[str, float]]) -> Dict[str, Dict[str, Any]]:
    """Compute 95% bootstrapped CIs for all metrics across iterations.

    Args:
        test_metrics_per_iteration: List of metric dicts, one per iteration

    Returns:
        {metric_name: {ci_lower, ci_upper, mean, n_iterations}}
    """
    confidence_intervals = {}

    # Metrics to compute CIs for
    metrics_to_compare = [
        'total_points', 'sharpe_ratio', 'sortino_ratio', 'max_drawdown',
        'mean_gw_points', 'std_gw_points', 'coefficient_variation'
    ]

    for metric in metrics_to_compare:
        # Collect metric values across all iterations
        metric_values = [
            it.get(metric)
            for it in test_metrics_per_iteration
            if metric in it and it[metric] is not None
        ]

        if len(metric_values) > 0:
            # Compute 95% CI using bootstrap_ci function
            # bootstrap_ci expects list of dicts with the metric as a key
            metric_dicts = [{'value': v} for v in metric_values]
            ci_result = bootstrap_ci(
                metric_dicts,
                metric_key='value',
                ci=0.95,
                n_bootstrap=1000
            )

            confidence_intervals[metric] = {
                'ci_lower': ci_result['ci_lower_a'],
                'ci_upper': ci_result['ci_upper_a'],
                'mean': ci_result['mean_a'],
                'n_iterations': len(metric_values),
            }

    return confidence_intervals


def compute_significance_report(variant_results: Dict, baselines: Dict) -> Dict[str, Any]:
    """Compare variants against baselines using CI overlap.

    Non-overlapping CIs → statistically significant difference.
    Overlapping CIs → difference may be noise.
    """
    report = {
        'method': 'CI overlap (non-overlapping = significant)',
        'variants_vs_baseline_current': {},
        'variants_vs_baseline_static': {},
        'winners': [],
    }

    # Extract baseline CIs for total_points and sharpe_ratio
    baseline_current_ci = extract_ci_from_baseline(baselines, 'current', 'total_points')
    baseline_static_ci = extract_ci_from_baseline(baselines, 'static', 'total_points')

    # Compare each variant
    for variant_name, variant_data in variant_results.items():
        if variant_name == 'significance_report':
            continue

        variant_ci = variant_data['confidence_intervals']

        # Compare total_points vs baselines
        if 'total_points' in variant_ci:
            vs_current = ci_overlap(
                variant_ci['total_points'],
                baseline_current_ci
            )
            vs_static = ci_overlap(
                variant_ci['total_points'],
                baseline_static_ci
            )

            report['variants_vs_baseline_current'][variant_name] = {
                'total_points': {
                    'variant_ci': (variant_ci['total_points']['ci_lower'],
                                  variant_ci['total_points']['ci_upper']),
                    'baseline_ci': (baseline_current_ci['mean'], baseline_current_ci['ci_lower'], baseline_current_ci['ci_upper']),
                    'overlaps': vs_current,
                    'significant': not vs_current,
                }
            }

            report['variants_vs_baseline_static'][variant_name] = {
                'total_points': {
                    'variant_ci': (variant_ci['total_points']['ci_lower'],
                                  variant_ci['total_points']['ci_upper']),
                    'baseline_ci': (baseline_static_ci['mean'], baseline_static_ci['ci_lower'], baseline_static_ci['ci_upper']),
                    'overlaps': vs_static,
                    'significant': not vs_static,
                }
            }

            # Flag winners (non-overlapping AND higher mean)
            if not vs_current and variant_ci['total_points']['mean'] > baseline_current_ci['mean']:
                report['winners'].append({
                    'variant': variant_name,
                    'beats': 'BASELINE_CURRENT',
                    'improvement_points': variant_ci['total_points']['mean'] - baseline_current_ci['mean'],
                    'variant_mean': variant_ci['total_points']['mean'],
                    'baseline_mean': baseline_current_ci['mean'],
                })

            if not vs_static and variant_ci['total_points']['mean'] > baseline_static_ci['mean']:
                report['winners'].append({
                    'variant': variant_name,
                    'beats': 'BASELINE_STATIC',
                    'improvement_points': variant_ci['total_points']['mean'] - baseline_static_ci['mean'],
                    'variant_mean': variant_ci['total_points']['mean'],
                    'baseline_mean': baseline_static_ci['mean'],
                })

    return report


def extract_ci_from_baseline(baselines: Dict, baseline_name: str, metric: str) -> Dict[str, float]:
    """Extract CI from baseline_results.json structure.

    Returns:
        Dict with keys: mean, ci_lower, ci_upper
    """
    baseline_data = baselines.get(baseline_name, {})
    test_iterations = baseline_data.get('test_iterations', [])

    # Collect metric values across iterations
    values = [it['test_metrics'].get(metric) for it in test_iterations
              if metric in it.get('test_metrics', {})]

    if len(values) > 0:
        metric_dicts = [{'value': v} for v in values]
        ci_result = bootstrap_ci(metric_dicts, metric_key='value', ci=0.95, n_bootstrap=1000)
        return {
            'mean': ci_result['mean_a'],
            'ci_lower': ci_result['ci_lower_a'],
            'ci_upper': ci_result['ci_upper_a'],
        }

    return {'mean': 0.0, 'ci_lower': 0.0, 'ci_upper': 0.0}


def ci_overlap(ci1: Dict, ci2: Dict) -> bool:
    """Check if two CIs overlap.

    Returns True if CIs overlap (not significant), False if non-overlapping (significant).

    ci1: {ci_lower, ci_upper, mean}
    ci2: {mean, ci_lower, ci_upper}
    """
    ci1_lower = ci1['ci_lower']
    ci1_upper = ci1['ci_upper']
    ci2_lower = ci2['ci_lower']
    ci2_upper = ci2['ci_upper']

    # CIs don't overlap if one is entirely above the other
    return not (ci1_upper < ci2_lower or ci2_upper < ci1_lower)


if __name__ == '__main__':
    results = run_variant_evaluation()

    # Print summary
    print("\nVariant Summary:")
    for variant_name, variant_data in results.items():
        if variant_name == 'significance_report':
            continue
        cis = variant_data['confidence_intervals']
        if 'total_points' in cis:
            print(f"  {variant_name}: {cis['total_points']['mean']:.0f} ± "
                  f"[{cis['total_points']['ci_lower']:.0f}, {cis['total_points']['ci_upper']:.0f}]")
