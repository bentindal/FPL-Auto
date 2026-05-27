"""
Evaluation module for FPL automation strategy comparison.

Provides walk-forward validation, baseline execution, and result aggregation
for systematic strategy comparison across multiple seasons.
"""

# Import metrics utilities from metrics.py
from evaluation.metrics import (
    compute_season_metrics,
    bootstrap_ci,
    apply_bonferroni_correction,
    format_metrics_table,
)

__all__ = [
    'compute_season_metrics',
    'bootstrap_ci',
    'apply_bonferroni_correction',
    'format_metrics_table',
]
