"""
Evaluation module for FPL automation strategy comparison.

Provides walk-forward validation, baseline execution, and result aggregation
for systematic strategy comparison across multiple seasons.
"""

from evaluation.walk_forward import (
    run_strategy_on_seasons,
    nested_walk_forward_evaluation,
    aggregate_season_results,
    compute_season_metrics,
)

__all__ = [
    'run_strategy_on_seasons',
    'nested_walk_forward_evaluation',
    'aggregate_season_results',
    'compute_season_metrics',
]
