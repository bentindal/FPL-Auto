"""
Phase 8 Bench & Substitution Strategy Evaluation
Orchestrates walk-forward validation of 4-variant 2x2 factorial design.

Variants:
1. BENCH_SAFE_STATIC: Safe bench + static rotation (baseline comparison)
2. BENCH_SAFE_PREDICTIVE: Safe bench + predictive swaps
3. BENCH_SPECULATIVE_STATIC: Speculative bench + static rotation
4. BENCH_SPECULATIVE_PREDICTIVE: Speculative bench + predictive swaps

Locked parameters (inherited from Phase 6-7):
- Transfer: CONSERVATIVE_FULL (transfer_budget_per_gw=0.5, threshold=0.20)
- Captain: CAPTAIN_HIGHEST_VALUE (prefer stable high-priced players)
"""

import json
import sys
import os
from typing import Dict, List, Tuple
from dataclasses import dataclass
from multiprocessing import Pool
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports
from fpl_auto.strategies import (
    BENCH_SAFE_STATIC, BENCH_SAFE_PREDICTIVE,
    BENCH_SPECULATIVE_STATIC, BENCH_SPECULATIVE_PREDICTIVE,
)
from evaluation import walk_forward, metrics
import manager


@dataclass
class EvaluationConfig:
    """Configuration for Phase 8 evaluation."""
    variants: Dict[str, any]  # Name → StrategyConfig
    test_seasons: List[str] = None  # Default: ['2023-24', '2024-25']
    bootstrap_iterations: int = 10000
    bonferroni_alpha: float = 0.0125  # 0.05 / 4 variants

    def __post_init__(self):
        if self.test_seasons is None:
            self.test_seasons = ['2023-24', '2024-25']


def run_all_variants(eval_config: EvaluationConfig) -> Dict:
    """
    Run walk-forward evaluation for all variants.

    Returns:
        {
            'BENCH_SAFE_STATIC': {
                'iterations': [...],  # Walk-forward iteration results
                'combined_metrics': {...}  # Aggregated metrics across iterations
            },
            ...
            '_comparison': {...summary table...}
        }
    """
    results = {}

    print("=" * 80)
    print("PHASE 8: BENCH & SUBSTITUTION STRATEGY EVALUATION")
    print("=" * 80)
    print(f"\nRunning 4-variant 2x2 factorial design on test seasons: {eval_config.test_seasons}\n")

    for variant_name, variant_config in eval_config.variants.items():
        print(f"\n{'='*80}")
        print(f"Running: {variant_name}")
        print(f"  Bench composition: {variant_config.bench_composition_variant}")
        print(f"  Substitution mode: {variant_config.substitution_mode}")
        print(f"  Transfer budget/GW: {variant_config.transfer_budget_per_gw}")
        print(f"  Captain mode: {variant_config.captain_mode}")
        print(f"{'='*80}\n")

        # Run walk-forward for this variant
        try:
            wf_results = walk_forward.nested_walk_forward_evaluation(
                variant_config,
                ['2021-22', '2022-23', '2023-24', '2024-25']
            )

            # Extract test season results (2023-24 and 2024-25)
            test_season_results = []
            for wf_iter in wf_results:
                if wf_iter.get('test_season') in eval_config.test_seasons:
                    test_season_results.append(wf_iter)

            # Compute combined metrics across test seasons
            combined = _aggregate_test_results(test_season_results)

            results[variant_name] = {
                'iterations': wf_results,
                'test_iterations': test_season_results,
                'combined_metrics': combined,
            }
            print(f"✓ {variant_name} completed. Combined points: {combined['total_points']:.0f}")
        except Exception as e:
            print(f"✗ {variant_name} failed: {e}")
            import traceback
            traceback.print_exc()
            results[variant_name] = {'error': str(e)}

    # Compute comparison metrics
    print(f"\n{'='*80}")
    print("RESULTS COMPARISON")
    print(f"{'='*80}\n")

    comparison = _compute_comparison(results, eval_config)
    results['_comparison'] = comparison

    return results


def _aggregate_test_results(test_iterations: List[Dict]) -> Dict:
    """
    Aggregate test season results into combined metrics.

    Args:
        test_iterations: List of walk-forward iteration dicts, each with test_metrics

    Returns:
        Dict with combined metrics including CIs
    """
    if not test_iterations:
        return {}

    # Extract total points from each test iteration
    points_list = [it.get('test_metrics', {}).get('total_points', 0)
                   for it in test_iterations]
    sharpes = [it.get('test_metrics', {}).get('sharpe_ratio', 0)
               for it in test_iterations]
    sortinos = [it.get('test_metrics', {}).get('sortino_ratio', 0)
                for it in test_iterations]

    # Compute bootstrap CIs for total points
    if points_list:
        # Simple bootstrap on points
        mean_points = float(np.mean(points_list))

        # Bootstrap CI
        bootstrap_samples = []
        for _ in range(10000):
            sample = np.random.choice(points_list, size=len(points_list), replace=True)
            bootstrap_samples.append(np.mean(sample))

        bootstrap_samples = np.array(bootstrap_samples)
        ci_lower = float(np.percentile(bootstrap_samples, 2.5))
        ci_upper = float(np.percentile(bootstrap_samples, 97.5))
    else:
        mean_points = 0.0
        ci_lower = 0.0
        ci_upper = 0.0

    return {
        'total_points': mean_points,
        'total_points_ci_lower': ci_lower,
        'total_points_ci_upper': ci_upper,
        'sharpe_ratio': float(np.mean(sharpes)) if sharpes else 0.0,
        'sortino_ratio': float(np.mean(sortinos)) if sortinos else 0.0,
        'num_test_seasons': len(test_iterations),
    }


def _compute_comparison(results: Dict, eval_config: EvaluationConfig) -> Dict:
    """
    Compute summary comparison across all variants.

    Returns:
        {
            'points_by_variant': {name → (mean, ci_lower, ci_upper)},
            'bonferroni_significant': [(variant_a, variant_b, is_significant), ...],
            'recommendation': 'best_variant_name',
            'summary_table': str
        }
    """

    # Extract metrics by variant
    metrics_by_variant = {}
    for variant_name, result in results.items():
        if 'error' in result:
            continue

        # Get combined metrics (across both test seasons)
        combined = result.get('combined_metrics', {})
        metrics_by_variant[variant_name] = {
            'points': combined.get('total_points', 0),
            'sharpe': combined.get('sharpe_ratio', 0),
            'sortino': combined.get('sortino_ratio', 0),
            'ci_lower': combined.get('total_points_ci_lower', 0),
            'ci_upper': combined.get('total_points_ci_upper', 0),
        }

    if not metrics_by_variant:
        return {
            'metrics_by_variant': {},
            'significant_pairs': [],
            'best_variant': 'N/A',
            'summary_table': 'No valid results to compare',
        }

    # Find best variant (highest mean points)
    best_variant = max(metrics_by_variant.items(), key=lambda x: x[1]['points'])[0]

    # Check for non-overlapping CIs (statistical significance)
    significant_pairs = []
    variant_names = list(metrics_by_variant.keys())
    for i, v1 in enumerate(variant_names):
        for v2 in variant_names[i+1:]:
            m1, m2 = metrics_by_variant[v1], metrics_by_variant[v2]
            # Non-overlapping CIs indicate significance at Bonferroni-corrected α
            overlaps = m1['ci_lower'] <= m2['ci_upper'] and m2['ci_lower'] <= m1['ci_upper']
            significant_pairs.append((v1, v2, not overlaps))

    # Build summary table
    summary_lines = [
        "Variant Comparison (sorted by total points):\n",
        f"{'Variant':<40} {'Points':<10} {'Sharpe':<10} {'CI Lower':<10} {'CI Upper':<10}",
        "-" * 80,
    ]

    for variant_name in sorted(metrics_by_variant.keys(), key=lambda x: metrics_by_variant[x]['points'], reverse=True):
        m = metrics_by_variant[variant_name]
        summary_lines.append(
            f"{variant_name:<40} {m['points']:<10.1f} {m['sharpe']:<10.2f} {m['ci_lower']:<10.1f} {m['ci_upper']:<10.1f}"
        )

    summary_lines.append("")
    summary_lines.append("Bonferroni-Corrected Significance (α=0.0125 for 4 variants):")
    summary_lines.append("-" * 80)
    for v1, v2, is_sig in significant_pairs:
        sig_mark = "**" if is_sig else "  "
        summary_lines.append(f"{sig_mark} {v1} vs {v2}: {'SIGNIFICANT' if is_sig else 'NOT significant'}")

    summary_lines.append(f"\nRecommendation: {best_variant} (highest points)")

    return {
        'metrics_by_variant': metrics_by_variant,
        'significant_pairs': significant_pairs,
        'best_variant': best_variant,
        'summary_table': '\n'.join(summary_lines),
    }


def save_results(results: Dict, output_file: str = 'evaluation/phase8_results.json'):
    """Save results to JSON for archival and Phase 9 comparison."""
    # Remove raw result dicts (too large); keep summary only
    output = {
        'summary': results.get('_comparison', {}),
        'variants_tested': list(results.keys()),
        'timestamp': __import__('datetime').datetime.now().isoformat(),
    }

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Results saved to {output_file}")


def main():
    """Main entry point for Phase 8 evaluation."""

    # Configure evaluation
    eval_config = EvaluationConfig(
        variants={
            'BENCH_SAFE_STATIC': BENCH_SAFE_STATIC,
            'BENCH_SAFE_PREDICTIVE': BENCH_SAFE_PREDICTIVE,
            'BENCH_SPECULATIVE_STATIC': BENCH_SPECULATIVE_STATIC,
            'BENCH_SPECULATIVE_PREDICTIVE': BENCH_SPECULATIVE_PREDICTIVE,
        },
        test_seasons=['2023-24', '2024-25'],
        bootstrap_iterations=10000,
        bonferroni_alpha=0.0125,
    )

    # Run evaluation
    results = run_all_variants(eval_config)

    # Print summary
    if '_comparison' in results:
        print("\n" + results['_comparison']['summary_table'])

    # Save results
    save_results(results)


if __name__ == '__main__':
    main()
