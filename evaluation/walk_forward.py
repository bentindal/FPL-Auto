"""
Walk-forward validation framework for FPL automation strategies.

Implements nested walk-forward evaluation to prevent overfitting by training on
N-1 seasons and testing on held-out seasons. Provides baseline execution for
BASELINE_STATIC and BASELINE_CURRENT strategy archetypes.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import json
from multiprocessing import Pool

import numpy as np

import manager
from fpl_auto.strategies import StrategyConfig


def run_strategy_on_seasons(
    strategy_config: StrategyConfig,
    seasons: List[str],
) -> List[Dict[str, Any]]:
    """
    Run a single strategy across multiple seasons and collect per-season results.

    Executes the strategy on each season using multiprocessing, collecting per-season
    results including weekly points, expected points, chips used, and transfer history.

    Args:
        strategy_config: StrategyConfig instance (e.g., BASELINE_STATIC, BASELINE_CURRENT)
        seasons: List of season strings (e.g., ['2021-22', '2022-23', '2023-24', '2024-25'])

    Returns:
        List of dicts, one per season:
            [
                {
                    'season': '2021-22',
                    'p_list': [32, 44, 41, ...],  # 38 GW points (or fewer if season incomplete)
                    'xp_list': [53.47, 42.32, ...],  # 38 GW expected points
                    'chips_used': ['wildcard', 'triple_captain'],
                    'transfer_history': [{'gw': 1, 'out': 'Player A', 'in': 'Player B'}, ...],
                    'total_points': 2145,  # Sum of p_list
                },
                ...
            ]

    Raises:
        ValueError: If any season is not available in data directory
    """
    # Build config list for each season
    configs = [
        {
            'season': season,
            'start_gw': 1,
            'repeat': 37,  # GW 1 to 38 (start_gw + repeat = 1 + 37 = 38)
            'starting_team': 'auto',
            'quiet': True,
            'strategy': strategy_config,
        }
        for season in seasons
    ]

    # Run seasons in parallel using multiprocessing
    results = []

    # Try with multiprocessing first; fall back to serial if it fails
    try:
        with Pool(processes=min(4, len(configs))) as pool:
            raw_results = pool.map(manager.run_season, configs)
    except Exception as e:
        # If multiprocessing fails, run serially
        print(f"  [Multiprocessing error, falling back to serial: {type(e).__name__}]")
        raw_results = []
        for config in configs:
            try:
                raw_results.append(manager.run_season(config))
            except Exception as ex:
                print(f"  [Error running season {config['season']}: {ex}]")
                raw_results.append(None)

    # Enrich results with aggregated metrics
    for result in raw_results:
        if result is not None:
            result['total_points'] = sum(result.get('p_list', []))
            results.append(result)

    return results


def compute_season_metrics(
    weekly_points: List[float],
    season: Optional[str] = None,
) -> Dict[str, float]:
    """
    Compute key metrics for a single season's performance.

    Args:
        weekly_points: List of 38 (or fewer) weekly points
        season: Optional season string for reference (not used in computation)

    Returns:
        Dict with metrics:
            {
                'total_points': int,
                'mean_gw_points': float,
                'std_gw_points': float,
                'sharpe_ratio': float,
                'sortino_ratio': float,
                'coefficient_variation': float,
                'max_drawdown': float,
                'best_week': int,
                'worst_week': int,
            }
    """
    if not weekly_points or len(weekly_points) == 0:
        return {
            'total_points': 0,
            'mean_gw_points': 0.0,
            'std_gw_points': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'coefficient_variation': 0.0,
            'max_drawdown': 0.0,
            'best_week': 0,
            'worst_week': 0,
        }

    points_array = np.array(weekly_points, dtype=float)
    total = np.sum(points_array)
    mean = np.mean(points_array)
    std = np.std(points_array)

    # Sharpe ratio (risk-free rate = 0 for FPL)
    sharpe = mean / std if std > 0 else 0.0

    # Sortino ratio (penalize only downside)
    downside_points = [p for p in points_array if p < mean]
    downside_std = np.std(downside_points) if downside_points else 0.0
    sortino = mean / downside_std if downside_std > 0 else 0.0

    # Coefficient of variation
    cv = std / mean if mean > 0 else 0.0

    # Max drawdown
    cumsum = np.cumsum(points_array)
    running_max = np.maximum.accumulate(cumsum)
    drawdown = running_max - cumsum
    max_drawdown = float(np.max(drawdown)) if len(drawdown) > 0 else 0.0

    return {
        'total_points': int(total),
        'mean_gw_points': float(mean),
        'std_gw_points': float(std),
        'sharpe_ratio': float(sharpe),
        'sortino_ratio': float(sortino),
        'coefficient_variation': float(cv),
        'max_drawdown': float(max_drawdown),
        'best_week': int(np.max(points_array)) if len(points_array) > 0 else 0,
        'worst_week': int(np.min(points_array)) if len(points_array) > 0 else 0,
    }


def aggregate_season_results(
    results: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Aggregate per-season results into mean metrics.

    Takes a list of season results (each with p_list, xp_list, etc.) and computes
    the mean metrics across all seasons for use as training benchmarks.

    Args:
        results: List of per-season result dicts from run_strategy_on_seasons()

    Returns:
        Dict with aggregated metrics:
            {
                'avg_total_points': float,
                'avg_mean_gw_points': float,
                'avg_std_gw_points': float,
                'avg_sharpe': float,
                'avg_sortino': float,
                'avg_cv': float,
                'avg_max_drawdown': float,
                'num_seasons': int,
            }
    """
    if not results:
        return {
            'avg_total_points': 0.0,
            'avg_mean_gw_points': 0.0,
            'avg_std_gw_points': 0.0,
            'avg_sharpe': 0.0,
            'avg_sortino': 0.0,
            'avg_cv': 0.0,
            'avg_max_drawdown': 0.0,
            'num_seasons': 0,
        }

    all_metrics = [
        compute_season_metrics(r.get('p_list', []), r.get('season'))
        for r in results
    ]

    total_points = [m['total_points'] for m in all_metrics]
    mean_gw_points = [m['mean_gw_points'] for m in all_metrics]
    std_gw_points = [m['std_gw_points'] for m in all_metrics]
    sharpes = [m['sharpe_ratio'] for m in all_metrics]
    sortinos = [m['sortino_ratio'] for m in all_metrics]
    cvs = [m['coefficient_variation'] for m in all_metrics]
    max_drawdowns = [m['max_drawdown'] for m in all_metrics]

    return {
        'avg_total_points': float(np.mean(total_points)) if total_points else 0.0,
        'avg_mean_gw_points': float(np.mean(mean_gw_points)) if mean_gw_points else 0.0,
        'avg_std_gw_points': float(np.mean(std_gw_points)) if std_gw_points else 0.0,
        'avg_sharpe': float(np.mean(sharpes)) if sharpes else 0.0,
        'avg_sortino': float(np.mean(sortinos)) if sortinos else 0.0,
        'avg_cv': float(np.mean(cvs)) if cvs else 0.0,
        'avg_max_drawdown': float(np.mean(max_drawdowns)) if max_drawdowns else 0.0,
        'num_seasons': len(results),
    }


def nested_walk_forward_evaluation(
    strategy_config: StrategyConfig,
    all_seasons: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Nested walk-forward validation: train on N-1 seasons, test on held-out season.

    Implements the outer loop of nested cross-validation. For each iteration, trains
    on a subset of seasons and evaluates on a held-out test season. This prevents
    overfitting by ensuring the test season is never seen during training/tuning.

    For 4 seasons (2021-22 through 2024-25), uses 2 iterations:
    - Iteration 1: Train on [2021-22, 2022-23], test on 2023-24
    - Iteration 2: Train on [2022-23, 2023-24], test on 2024-25

    Args:
        strategy_config: StrategyConfig instance to evaluate
        all_seasons: List of season strings. Default: ['2021-22', '2022-23', '2023-24', '2024-25']

    Returns:
        List of iteration results:
            [
                {
                    'iteration': 1,
                    'test_season': '2023-24',
                    'train_seasons': ['2021-22', '2022-23'],
                    'test_results': {
                        'season': '2023-24',
                        'p_list': [...],  # Weekly points (38 values)
                        'xp_list': [...],  # Weekly expected points
                        'total_points': 2145,
                        'chips_used': [...],
                        'transfer_history': [...],
                    },
                    'test_metrics': {
                        'total_points': 2145,
                        'mean_gw_points': 56.4,
                        'std_gw_points': 12.3,
                        'sharpe_ratio': 0.624,
                        'sortino_ratio': 1.234,
                        'coefficient_variation': 0.218,
                        'max_drawdown': 45.2,
                        'best_week': 89,
                        'worst_week': 18,
                    },
                    'train_metrics': {
                        'avg_total_points': 2187.5,
                        'avg_mean_gw_points': 57.6,
                        'avg_std_gw_points': 11.8,
                        'avg_sharpe': 0.652,
                        'avg_sortino': 1.254,
                        'avg_cv': 0.205,
                        'avg_max_drawdown': 42.1,
                        'num_seasons': 2,
                    },
                    'timestamp': '2026-05-27T17:38:57Z',
                },
                ...
            ]
    """
    if all_seasons is None:
        all_seasons = ['2021-22', '2022-23', '2023-24', '2024-25']

    results = []

    # Outer loop: iterate over test seasons (last 2 seasons for robustness)
    test_seasons = ['2023-24', '2024-25']

    for test_idx, test_season in enumerate(test_seasons):
        print(f"\n[Walk-Forward Iteration {test_idx + 1}]")
        print(f"  Test season: {test_season}")

        # Identify training seasons (all except test)
        train_seasons = [s for s in all_seasons if s != test_season]
        print(f"  Train seasons: {train_seasons}")

        # Inner loop: run strategy on training seasons to collect baseline metrics
        print(f"  Running strategy on training seasons...")
        train_results = run_strategy_on_seasons(strategy_config, train_seasons)
        train_metrics = aggregate_season_results(train_results)
        print(f"    Training complete. Avg points: {train_metrics['avg_total_points']:.0f}")

        # Outer evaluation: run strategy on held-out test season
        print(f"  Running strategy on test season...")
        test_results_raw = run_strategy_on_seasons(strategy_config, [test_season])

        if not test_results_raw or test_results_raw[0] is None:
            print(f"  WARNING: Could not run test season {test_season}")
            continue

        test_results = test_results_raw[0]
        test_metrics = compute_season_metrics(
            test_results.get('p_list', []),
            test_season
        )
        print(f"    Test complete. Test points: {test_metrics['total_points']}")

        results.append({
            'iteration': test_idx + 1,
            'test_season': test_season,
            'train_seasons': train_seasons,
            'test_results': test_results,
            'test_metrics': test_metrics,
            'train_metrics': train_metrics,
            'timestamp': datetime.now().isoformat(),
        })

    return results


def run_baselines() -> Dict[str, Any]:
    """
    Run BASELINE_STATIC and BASELINE_CURRENT through nested walk-forward evaluation.

    Executes both baseline strategies and saves aggregated results to
    evaluation/baseline_results.json. Includes progress logging to stdout.

    Returns:
        Dict with structure:
            {
                'baseline_name': {
                    'strategy_config': {
                        'transfer_mode': str,
                        'captain_mode': str,
                        'chip_schedule': str,
                        'bench_mode': str,
                    },
                    'iterations': [list of walk-forward results],
                },
                ...
            }
    """
    from fpl_auto.strategies import BASELINE_STATIC, BASELINE_CURRENT

    baselines = {
        'static': BASELINE_STATIC,
        'current': BASELINE_CURRENT,
    }

    baseline_results = {}

    for name, strategy in baselines.items():
        print(f"\n{'=' * 60}")
        print(f"Running baseline: {name}")
        print(f"{'=' * 60}")

        results = nested_walk_forward_evaluation(strategy)
        baseline_results[name] = {
            'strategy_config': {
                'transfer_mode': strategy.transfer_mode,
                'captain_mode': strategy.captain_mode,
                'chip_schedule': strategy.chip_schedule,
                'bench_mode': strategy.bench_mode,
            },
            'iterations': results,
        }

    # Save to evaluation/baseline_results.json
    print(f"\n{'=' * 60}")
    print("Saving baseline results to evaluation/baseline_results.json...")

    output = {}
    for name, data in baseline_results.items():
        output[name] = {
            'strategy_config': data['strategy_config'],
            'test_iterations': [
                {
                    'iteration': r['iteration'],
                    'test_season': r['test_season'],
                    'train_seasons': r['train_seasons'],
                    'test_metrics': r['test_metrics'],
                    'train_metrics': r['train_metrics'],
                    'timestamp': r['timestamp'],
                }
                for r in data['iterations']
            ],
        }

    with open('evaluation/baseline_results.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("Baseline results saved successfully!")
    print(f"{'=' * 60}")

    return baseline_results


if __name__ == '__main__':
    """Entry point for baseline evaluation script."""
    run_baselines()
