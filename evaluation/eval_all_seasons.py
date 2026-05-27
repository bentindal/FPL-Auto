"""
Comprehensive evaluation of all 5 transfer variants across all 4 available seasons.

Tests each variant (CONSERVATIVE_EARLY, CONSERVATIVE_FULL, BASELINE_MID,
AGGRESSIVE_LATE, AGGRESSIVE_FULL) on seasons 2021-22, 2022-23, 2023-24, 2024-25
to identify regime changes and strategy robustness.

Outputs:
- evaluation/all_seasons_results.json: Raw results
- Printed summary with regime analysis and consistency metrics
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List
from multiprocessing import Pool
import numpy as np

# Add parent to path so we can import manager and fpl_auto
sys.path.insert(0, str(Path(__file__).parent.parent))

from manager import run_season
from fpl_auto.strategies import (
    CONSERVATIVE_EARLY, CONSERVATIVE_FULL, BASELINE_MID,
    AGGRESSIVE_LATE, AGGRESSIVE_FULL
)
from evaluation.metrics import compute_season_metrics


# Strategy variants and seasons
VARIANTS = {
    'CONSERVATIVE_EARLY': CONSERVATIVE_EARLY,
    'CONSERVATIVE_FULL': CONSERVATIVE_FULL,
    'BASELINE_MID': BASELINE_MID,
    'AGGRESSIVE_LATE': AGGRESSIVE_LATE,
    'AGGRESSIVE_FULL': AGGRESSIVE_FULL,
}

SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25']


def run_variant_season(config: dict) -> dict:
    """
    Run a single variant on a single season.

    Args:
        config: Dict with 'season', 'variant_name', 'strategy' keys

    Returns:
        Dict with results: season, variant, total_points, sharpe, sortino, max_drawdown, transfers_made
    """
    season = config['season']
    variant_name = config['variant_name']
    strategy = config['strategy']

    try:
        # Run the season simulation
        result = run_season({
            'season': season,
            'start_gw': 1,
            'repeat': 37,  # 38 GW total (1-38)
            'starting_team': 'auto',
            'quiet': True,
            'strategy': strategy,
        })

        # Extract points data
        p_list = result['p_list']

        if not p_list or len(p_list) == 0:
            return {
                'season': season,
                'variant': variant_name,
                'total_points': 0,
                'sharpe': 0,
                'sortino': 0,
                'max_drawdown': 0,
                'transfers_made': 0,
                'gw_count': 0,
                'error': 'No points data'
            }

        # Compute metrics
        metrics = compute_season_metrics(p_list)

        # Count transfers
        transfers_made = len(result.get('transfer_history', []))

        return {
            'season': season,
            'variant': variant_name,
            'total_points': round(metrics['total_points'], 2),
            'mean_gw_points': round(metrics['mean_gw_points'], 2),
            'std_gw_points': round(metrics['std_gw_points'], 2),
            'sharpe': round(metrics['sharpe_ratio'], 4),
            'sortino': round(metrics['sortino_ratio'], 4),
            'max_drawdown': round(metrics['max_drawdown'], 2),
            'best_week': round(metrics['best_week'], 2),
            'worst_week': round(metrics['worst_week'], 2),
            'transfers_made': transfers_made,
            'gw_count': len(p_list),
        }

    except Exception as e:
        return {
            'season': season,
            'variant': variant_name,
            'total_points': 0,
            'sharpe': 0,
            'sortino': 0,
            'max_drawdown': 0,
            'transfers_made': 0,
            'gw_count': 0,
            'error': str(e)
        }


def main():
    """Main execution: Run all variants across all seasons."""

    print("\n" + "="*80)
    print("COMPREHENSIVE TRANSFER STRATEGY EVALUATION")
    print("="*80)
    print(f"\nVariants: {list(VARIANTS.keys())}")
    print(f"Seasons: {SEASONS}")
    print(f"Total runs: {len(VARIANTS) * len(SEASONS)}\n")

    # Build config list for all combinations
    configs = []
    for season in SEASONS:
        for variant_name, strategy in VARIANTS.items():
            configs.append({
                'season': season,
                'variant_name': variant_name,
                'strategy': strategy,
            })

    # Run in parallel
    print("Starting parallel evaluation (this will take 10-20 minutes)...")
    with Pool(processes=min(8, len(SEASONS) * len(VARIANTS))) as pool:
        results = pool.map(run_variant_season, configs)

    # Organize results by season and variant
    results_by_season = {}
    for result in results:
        season = result['season']
        variant = result['variant']

        if season not in results_by_season:
            results_by_season[season] = {}

        # Store with metrics
        results_by_season[season][variant] = {
            'total_points': result['total_points'],
            'sharpe': result['sharpe'],
            'sortino': result['sortino'],
            'max_drawdown': result['max_drawdown'],
            'mean_gw_points': result.get('mean_gw_points', 0),
            'std_gw_points': result.get('std_gw_points', 0),
            'best_week': result.get('best_week', 0),
            'worst_week': result.get('worst_week', 0),
            'transfers_made': result['transfers_made'],
            'gw_count': result['gw_count'],
        }

        if 'error' in result:
            results_by_season[season][variant]['error'] = result['error']

    # Save to JSON
    output_path = '/Users/bentindal/Desktop/coding/FPL-Auto/evaluation/all_seasons_results.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results_by_season, f, indent=2)

    print(f"\nResults saved to {output_path}")

    # Print summary tables
    print_summary_tables(results_by_season)

    # Analyze regime changes and consistency
    analyze_regime_changes(results_by_season)


def print_summary_tables(results_by_season: Dict):
    """Print formatted tables of results by season."""

    print("\n" + "="*80)
    print("PER-SEASON RESULTS")
    print("="*80)

    for season in SEASONS:
        if season not in results_by_season:
            continue

        season_results = results_by_season[season]

        print(f"\n{season.upper()}")
        print("-" * 100)
        print(f"{'Variant':<20} {'Points':>10} {'Sharpe':>10} {'Sortino':>10} {'Drawdown':>10} {'Transfers':>10}")
        print("-" * 100)

        # Sort by total points descending
        sorted_variants = sorted(
            season_results.items(),
            key=lambda x: x[1].get('total_points', 0),
            reverse=True
        )

        for variant, metrics in sorted_variants:
            points = metrics.get('total_points', 0)
            sharpe = metrics.get('sharpe', 0)
            sortino = metrics.get('sortino', 0)
            drawdown = metrics.get('max_drawdown', 0)
            transfers = metrics.get('transfers_made', 0)

            # Color code the winner in this season
            is_winner = variant == sorted_variants[0][0]
            marker = " ← BEST" if is_winner else ""

            print(f"{variant:<20} {points:>10.0f} {sharpe:>10.2f} {sortino:>10.2f} {drawdown:>10.1f} {transfers:>10}{marker}")


def analyze_regime_changes(results_by_season: Dict):
    """Analyze regime changes and consistency across seasons."""

    print("\n" + "="*80)
    print("REGIME ANALYSIS AND CONSISTENCY")
    print("="*80)

    # Track best variant per season
    best_per_season = {}
    for season in SEASONS:
        if season in results_by_season:
            season_results = results_by_season[season]
            best = max(season_results.items(), key=lambda x: x[1]['total_points'])
            best_per_season[season] = best[0]

    print("\nBEST VARIANT PER SEASON:")
    print("-" * 50)
    for season in SEASONS:
        best = best_per_season.get(season, 'N/A')
        print(f"  {season}: {best}")

    # Detect regime changes
    best_variants = list(best_per_season.values())
    unique_best = set(best_variants)

    print(f"\nREGIME CHANGES: {len(unique_best)} different best variants across {len(SEASONS)} seasons")
    if len(unique_best) > 1:
        print("  Strategies show regime-dependent performance (not universally best)")
    else:
        print("  Consistent winner across all seasons: " + list(unique_best)[0])

    # Compute consistency metrics
    print("\nCONSISTENCY METRICS (Std Dev of Total Points Across Seasons):")
    print("-" * 50)

    variant_points = {v: [] for v in VARIANTS.keys()}

    for season in SEASONS:
        if season in results_by_season:
            for variant, metrics in results_by_season[season].items():
                variant_points[variant].append(metrics['total_points'])

    consistency = {}
    for variant in VARIANTS.keys():
        if variant_points[variant]:
            points_array = np.array(variant_points[variant])
            consistency[variant] = {
                'mean': float(np.mean(points_array)),
                'std': float(np.std(points_array)),
                'min': float(np.min(points_array)),
                'max': float(np.max(points_array)),
                'cv': float(np.std(points_array) / np.mean(points_array)) if np.mean(points_array) > 0 else 0,
            }

    # Sort by std dev (lower = more consistent)
    sorted_consistency = sorted(consistency.items(), key=lambda x: x[1]['std'])

    print(f"{'Variant':<20} {'Mean':>10} {'StdDev':>10} {'CV':>8} {'Min':>10} {'Max':>10}")
    print("-" * 70)
    for variant, metrics in sorted_consistency:
        print(f"{variant:<20} {metrics['mean']:>10.0f} {metrics['std']:>10.1f} {metrics['cv']:>8.3f} {metrics['min']:>10.0f} {metrics['max']:>10.0f}")

    # Summary insights
    print("\nKEY FINDINGS:")
    print("-" * 50)

    most_consistent = sorted_consistency[0][0]
    least_consistent = sorted_consistency[-1][0]
    print(f"Most consistent variant: {most_consistent} (StdDev: {consistency[most_consistent]['std']:.1f})")
    print(f"Least consistent variant: {least_consistent} (StdDev: {consistency[least_consistent]['std']:.1f})")

    # Check which variants are in top 2 most frequently
    top2_variants = {}
    for season in SEASONS:
        if season in results_by_season:
            season_results = results_by_season[season]
            sorted_variants = sorted(
                season_results.items(),
                key=lambda x: x[1]['total_points'],
                reverse=True
            )
            for variant, _ in sorted_variants[:2]:
                top2_variants[variant] = top2_variants.get(variant, 0) + 1

    print(f"\nTop-2 frequency (robustness across seasons):")
    for variant in sorted(top2_variants, key=top2_variants.get, reverse=True):
        print(f"  {variant}: {top2_variants[variant]}/4 seasons")

    print("\n" + "="*80)


if __name__ == '__main__':
    main()
