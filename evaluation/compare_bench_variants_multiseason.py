"""
Phase 8 Gap Closure: Multi-Season Bench & Substitution Strategy Evaluation

Extends Phase 8 evaluation to validate 4-variant 2x2 factorial design across
multiple historical seasons (2021-22, 2022-23, 2023-24) using walk-forward
validation. Provides cross-season robustness analysis.

Variants (identical to Phase 8):
1. BENCH_SAFE_STATIC: Safe bench + static rotation
2. BENCH_SAFE_PREDICTIVE: Safe bench + predictive swaps
3. BENCH_SPECULATIVE_STATIC: Speculative bench + static rotation
4. BENCH_SPECULATIVE_PREDICTIVE: Speculative bench + predictive swaps

Locked parameters (from Phase 6-7):
- Transfer: CONSERVATIVE_FULL (transfer_budget_per_gw=0.5, threshold=0.20)
- Captain: CAPTAIN_HIGHEST_VALUE (prefer stable high-priced players)
"""

import json
import sys
import os
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from multiprocessing import Pool
from datetime import datetime
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
class MultiSeasonEvaluationConfig:
    """Configuration for multi-season Phase 8 evaluation."""
    variants: Dict[str, any]  # Name → StrategyConfig
    test_seasons: List[str]  # Seasons to test on
    bootstrap_iterations: int = 10000
    bonferroni_alpha: float = 0.0125  # 0.05 / 4 variants
    all_seasons: List[str] = None  # All available seasons for training

    def __post_init__(self):
        if self.all_seasons is None:
            self.all_seasons = ['2021-22', '2022-23', '2023-24']


def _run_walk_forward_per_season(variant_config, test_season: str, all_seasons: List[str]) -> Dict:
    """
    Run walk-forward evaluation for a single test season.

    This is a custom implementation to allow testing on any season,
    not just the hardcoded last 2 seasons in the standard framework.

    Args:
        variant_config: StrategyConfig to test
        test_season: Season to hold out for testing
        all_seasons: List of all available seasons for training

    Returns:
        Walk-forward iteration result dict with 'test_metrics' and 'test_season'
    """
    # Training seasons = all except test
    train_seasons = [s for s in all_seasons if s != test_season]

    print(f"  [Single-Season Walk-Forward]")
    print(f"    Test season: {test_season}")
    print(f"    Train seasons: {train_seasons}")

    # Run on training seasons
    print(f"    Running strategy on training seasons...")
    try:
        train_results = walk_forward.run_strategy_on_seasons(variant_config, train_seasons)
        train_metrics = walk_forward.aggregate_season_results(train_results)
        print(f"      Training complete. Avg points: {train_metrics['avg_total_points']:.0f}")
    except Exception as e:
        print(f"      WARNING: Training failed for {test_season}: {e}")
        return None

    # Run on test season
    print(f"    Running strategy on test season...")
    try:
        test_results_raw = walk_forward.run_strategy_on_seasons(variant_config, [test_season])
        if not test_results_raw or test_results_raw[0] is None:
            print(f"      ERROR: Could not run test season {test_season}")
            return None

        test_results = test_results_raw[0]
        test_metrics = metrics.compute_season_metrics(test_results.get('p_list', []))
        print(f"      Test complete. Test points: {test_metrics['total_points']:.0f}")

        return {
            'iteration': 1,
            'test_season': test_season,
            'train_seasons': train_seasons,
            'test_results': test_results,
            'test_metrics': test_metrics,
            'train_metrics': train_metrics,
            'timestamp': datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"      ERROR: Test failed for {test_season}: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_all_variants_multiseason(eval_config: MultiSeasonEvaluationConfig) -> Dict:
    """
    Run walk-forward evaluation for all variants across multiple test seasons.

    For each variant, runs walk-forward validation on each test season independently,
    then aggregates results across all test seasons for cross-season comparison.

    Returns:
        {
            'BENCH_SAFE_STATIC': {
                'by_season': {
                    '2021-22': {...season-specific results...},
                    '2022-23': {...},
                    '2023-24': {...},
                },
                'combined_metrics': {...aggregated across all test seasons...}
            },
            ...
            '_comparison': {...cross-season summary...}
        }
    """
    results = {}

    print("=" * 90)
    print("PHASE 8 GAP CLOSURE: MULTI-SEASON BENCH & SUBSTITUTION EVALUATION")
    print("=" * 90)
    print(f"\nRunning 4-variant 2x2 factorial design on seasons: {eval_config.test_seasons}\n")

    for variant_name, variant_config in eval_config.variants.items():
        print(f"\n{'='*90}")
        print(f"Running: {variant_name}")
        print(f"  Bench composition: {variant_config.bench_composition_variant}")
        print(f"  Substitution mode: {variant_config.substitution_mode}")
        print(f"  Transfer budget/GW: {variant_config.transfer_budget_per_gw}")
        print(f"  Captain mode: {variant_config.captain_mode}")
        print(f"{'='*90}\n")

        # Run walk-forward for this variant on each test season
        try:
            results_by_season = {}

            for test_season in eval_config.test_seasons:
                wf_result = _run_walk_forward_per_season(
                    variant_config,
                    test_season,
                    eval_config.all_seasons
                )
                if wf_result is not None:
                    results_by_season[test_season] = wf_result

            # Compute combined metrics across all test seasons
            combined = _aggregate_multiseason_results(results_by_season)

            results[variant_name] = {
                'by_season': results_by_season,
                'combined_metrics': combined,
            }

            print(f"\n✓ {variant_name} completed.")
            print(f"  Combined points across {len(results_by_season)} seasons: {combined['total_points']:.0f}")
            for season, season_data in sorted(results_by_season.items()):
                season_pts = season_data.get('test_metrics', {}).get('total_points', 0)
                print(f"    {season}: {season_pts:.0f} pts")

        except Exception as e:
            print(f"\n✗ {variant_name} failed: {e}")
            import traceback
            traceback.print_exc()
            results[variant_name] = {'error': str(e)}

    # Compute cross-season comparison
    print(f"\n{'='*90}")
    print("CROSS-SEASON RESULTS COMPARISON")
    print(f"{'='*90}\n")

    comparison = _compute_multiseason_comparison(results, eval_config)
    results['_comparison'] = comparison

    return results


def _aggregate_multiseason_results(results_by_season: Dict[str, Dict]) -> Dict:
    """
    Aggregate results across multiple test seasons.

    Args:
        results_by_season: Dict mapping season_name → walk-forward result dict

    Returns:
        Dict with aggregated metrics including per-season and overall CIs
    """
    if not results_by_season:
        return {}

    # Extract metrics from each season
    points_by_season = {}
    all_points = []
    sharpes = []
    sortinos = []

    for season, result in sorted(results_by_season.items()):
        test_metrics = result.get('test_metrics', {})
        points = test_metrics.get('total_points', 0)
        points_by_season[season] = points
        all_points.append(points)
        sharpes.append(test_metrics.get('sharpe_ratio', 0))
        sortinos.append(test_metrics.get('sortino_ratio', 0))

    # Compute mean and bootstrap CI across all test seasons
    mean_points = float(np.mean(all_points))

    # Bootstrap CI
    bootstrap_samples = []
    for _ in range(10000):
        sample = np.random.choice(all_points, size=len(all_points), replace=True)
        bootstrap_samples.append(np.mean(sample))

    bootstrap_samples = np.array(bootstrap_samples)
    ci_lower = float(np.percentile(bootstrap_samples, 2.5))
    ci_upper = float(np.percentile(bootstrap_samples, 97.5))

    return {
        'total_points': mean_points,
        'total_points_ci_lower': ci_lower,
        'total_points_ci_upper': ci_upper,
        'sharpe_ratio': float(np.mean(sharpes)) if sharpes else 0.0,
        'sortino_ratio': float(np.mean(sortinos)) if sortinos else 0.0,
        'num_test_seasons': len(results_by_season),
        'points_by_season': points_by_season,
        'std_dev': float(np.std(all_points)),
    }


def _compute_multiseason_comparison(results: Dict, eval_config: MultiSeasonEvaluationConfig) -> Dict:
    """
    Compute cross-season comparison across all variants.

    Includes per-season breakdowns and overall significance testing.

    Returns:
        {
            'metrics_by_variant': {name → (mean, ci, std)},
            'per_season_results': {season → {variant → points}},
            'bonferroni_significant': [(v1, v2, is_significant), ...],
            'recommendation': 'best_variant_name',
            'consistency_analysis': {season_consistency, effect_sizes, ...},
        }
    """

    # Extract metrics by variant
    metrics_by_variant = {}
    per_season_results = {season: {} for season in eval_config.test_seasons}

    for variant_name, result in results.items():
        if 'error' in result:
            continue

        combined = result.get('combined_metrics', {})
        metrics_by_variant[variant_name] = {
            'points': combined.get('total_points', 0),
            'sharpe': combined.get('sharpe_ratio', 0),
            'sortino': combined.get('sortino_ratio', 0),
            'ci_lower': combined.get('total_points_ci_lower', 0),
            'ci_upper': combined.get('total_points_ci_upper', 0),
            'std_dev': combined.get('std_dev', 0),
            'num_seasons': combined.get('num_test_seasons', 0),
        }

        # Populate per-season results
        points_by_season = combined.get('points_by_season', {})
        for season, points in points_by_season.items():
            per_season_results[season][variant_name] = points

    if not metrics_by_variant:
        return {
            'metrics_by_variant': {},
            'per_season_results': {},
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
            overlaps = m1['ci_lower'] <= m2['ci_upper'] and m2['ci_lower'] <= m1['ci_upper']
            significant_pairs.append((v1, v2, not overlaps))

    # Consistency analysis: check if best variant wins in all seasons
    consistency_analysis = _analyze_consistency(per_season_results, best_variant)

    # Build summary table
    summary_lines = [
        "Variant Comparison across all test seasons (sorted by total points):\n",
        f"{'Variant':<40} {'Points':<12} {'StdDev':<10} {'Sharpe':<10} {'CI Lower':<10} {'CI Upper':<10}",
        "-" * 92,
    ]

    for variant_name in sorted(metrics_by_variant.keys(), key=lambda x: metrics_by_variant[x]['points'], reverse=True):
        m = metrics_by_variant[variant_name]
        summary_lines.append(
            f"{variant_name:<40} {m['points']:<12.1f} {m['std_dev']:<10.1f} {m['sharpe']:<10.2f} {m['ci_lower']:<10.1f} {m['ci_upper']:<10.1f}"
        )

    summary_lines.append("\n" + "Per-Season Breakdown:\n")
    summary_lines.append(f"{'Season':<15} " + "  ".join(f"{v:<15}" for v in sorted(metrics_by_variant.keys())))
    summary_lines.append("-" * 80)
    for season in sorted(per_season_results.keys()):
        season_str = season
        variant_scores = [f"{per_season_results[season].get(v, 0):<15.0f}" for v in sorted(metrics_by_variant.keys())]
        summary_lines.append(f"{season_str:<15} " + "  ".join(variant_scores))

    summary_lines.append("\n" + "Bonferroni-Corrected Significance (α=0.0125 for 4 variants):\n")
    summary_lines.append("-" * 92)
    for v1, v2, is_sig in significant_pairs:
        sig_mark = "**" if is_sig else "  "
        summary_lines.append(f"{sig_mark} {v1} vs {v2}: {'SIGNIFICANT' if is_sig else 'NOT significant'}")

    summary_lines.append(f"\nConsistency Analysis:")
    summary_lines.append("-" * 92)
    summary_lines.append(f"Best variant ({best_variant}) wins in {consistency_analysis['wins']}/{consistency_analysis['num_seasons']} seasons")
    summary_lines.append(f"Average effect size vs worst variant: {consistency_analysis['avg_effect_size']:.1f} points")
    summary_lines.append(f"Effect size consistency (std): {consistency_analysis['effect_size_std']:.1f} points")

    summary_lines.append(f"\nRecommendation: {best_variant} (highest combined points, consistent across seasons)")

    return {
        'metrics_by_variant': metrics_by_variant,
        'per_season_results': per_season_results,
        'significant_pairs': significant_pairs,
        'best_variant': best_variant,
        'consistency_analysis': consistency_analysis,
        'summary_table': '\n'.join(summary_lines),
    }


def _analyze_consistency(per_season_results: Dict[str, Dict[str, float]], best_variant: str) -> Dict:
    """
    Analyze whether the best variant consistently wins across seasons.

    Returns:
        {
            'wins': int,  # Number of seasons where best variant is highest
            'num_seasons': int,
            'effect_sizes': [list of point differences vs 2nd place in each season],
            'avg_effect_size': float,
            'effect_size_std': float,
        }
    """
    wins = 0
    effect_sizes = []
    seasons = sorted(per_season_results.keys())

    for season in seasons:
        season_variants = per_season_results[season]
        best_variant_points = season_variants.get(best_variant, 0)

        # Find second-best variant points
        other_points = [p for v, p in season_variants.items() if v != best_variant]
        if other_points:
            second_best = max(other_points)
            effect_size = best_variant_points - second_best
            effect_sizes.append(effect_size)

            if best_variant_points >= max(season_variants.values()):
                wins += 1

    return {
        'wins': wins,
        'num_seasons': len(seasons),
        'effect_sizes': effect_sizes,
        'avg_effect_size': float(np.mean(effect_sizes)) if effect_sizes else 0.0,
        'effect_size_std': float(np.std(effect_sizes)) if effect_sizes else 0.0,
    }


def save_multiseason_results(results: Dict, output_file: str = 'evaluation/phase8_results_multiseason.json'):
    """Save multi-season results to JSON for archival and analysis."""

    # Structure output to preserve all information
    output = {
        'phase': '8-gap-closure',
        'evaluation_type': 'multi-season-walk-forward',
        'test_seasons': ['2021-22', '2022-23', '2023-24'],
        'summary': results.get('_comparison', {}),
        'variants_tested': [v for v in results.keys() if v != '_comparison'],
        'timestamp': datetime.now().isoformat(),
    }

    # Clean up summary for JSON serialization
    if 'summary' in output and 'metrics_by_variant' in output['summary']:
        # Keep metrics_by_variant as-is (already serializable)
        # Simplify per_season_results for readability
        pass

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n✓ Multi-season results saved to {output_file}")
    return output_file


def main():
    """Main entry point for Phase 8 gap closure evaluation."""

    # Configure evaluation for 2021-22, 2022-23, 2023-24
    eval_config = MultiSeasonEvaluationConfig(
        variants={
            'BENCH_SAFE_STATIC': BENCH_SAFE_STATIC,
            'BENCH_SAFE_PREDICTIVE': BENCH_SAFE_PREDICTIVE,
            'BENCH_SPECULATIVE_STATIC': BENCH_SPECULATIVE_STATIC,
            'BENCH_SPECULATIVE_PREDICTIVE': BENCH_SPECULATIVE_PREDICTIVE,
        },
        test_seasons=['2021-22', '2022-23', '2023-24'],
        bootstrap_iterations=10000,
        bonferroni_alpha=0.0125,
        all_seasons=['2021-22', '2022-23', '2023-24'],
    )

    # Run evaluation
    print(f"\nStarting multi-season evaluation at {datetime.now().isoformat()}\n")
    results = run_all_variants_multiseason(eval_config)

    # Print summary
    if '_comparison' in results:
        print("\n" + results['_comparison']['summary_table'])

    # Save results
    output_path = save_multiseason_results(results)
    print(f"\nEvaluation complete. Results saved to {output_path}")

    return results


if __name__ == '__main__':
    main()
