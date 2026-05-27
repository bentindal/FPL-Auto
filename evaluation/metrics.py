"""
Metrics computation, bootstrapping, and reporting for strategy evaluation.

Provides multi-dimensional metrics (Sharpe, Sortino, consistency, drawdown) with
bootstrapped confidence intervals and multiple-comparison correction for rigorous
strategy comparison.
"""

from typing import Dict, List, Optional
import numpy as np


def compute_season_metrics(
    weekly_points: List[float],
    baseline_weekly_points: Optional[List[float]] = None,
) -> Dict[str, float]:
    """
    Compute multi-dimensional metrics for a single season.

    Calculates risk-adjusted returns (Sharpe, Sortino), consistency measures,
    and drawdown metrics from a season's weekly points.

    Args:
        weekly_points: List of 38 GW point scores (or fewer if incomplete).
        baseline_weekly_points: Optional baseline weekly points for comparison.

    Returns:
        Dict with keys:
        - total_points: Sum of season points
        - mean_gw_points: Average points per GW
        - std_gw_points: Standard deviation of weekly points
        - sharpe_ratio: (mean - rf) / std, where rf=0 for FPL
        - sortino_ratio: (mean - rf) / std(downside), penalizes only weeks below mean
        - coefficient_variation: std / mean (lower = more consistent)
        - max_drawdown: Worst cumulative loss as absolute points
        - best_week: Maximum single-GW score
        - worst_week: Minimum single-GW score
        - vs_baseline_total_points: total_points difference vs baseline (if baseline provided)
        - vs_baseline_win_rate: Proportion of weeks beating baseline (if baseline provided)

    Raises:
        ValueError: If weekly_points is empty.
    """
    if not weekly_points or len(weekly_points) == 0:
        raise ValueError("weekly_points cannot be empty")

    p = np.array(weekly_points, dtype=float)

    total = float(np.sum(p))
    mean = float(np.mean(p))
    std = float(np.std(p))

    # Sharpe ratio: (mean - rf) / std, rf = 0 for FPL
    sharpe = mean / std if std > 0 else 0.0

    # Sortino ratio: (mean - rf) / std(downside)
    # Downside = std of points below mean
    downside_points = [x for x in p if x < mean]
    downside = np.std(downside_points) if downside_points else std
    sortino = mean / downside if downside > 0 else 0.0

    # Coefficient of Variation: std / mean (consistency metric)
    cv = std / mean if mean > 0 else 0.0

    # Max drawdown: worst (peak - current) / peak normalized to absolute points
    cumsum = np.cumsum(p)
    peak = np.maximum.accumulate(cumsum)
    drawdown_points = peak - cumsum  # Absolute drawdown in points
    max_dd = float(np.max(drawdown_points)) if len(drawdown_points) > 0 else 0.0

    metrics = {
        'total_points': total,
        'mean_gw_points': mean,
        'std_gw_points': std,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'coefficient_variation': cv,
        'max_drawdown': max_dd,
        'best_week': float(np.max(p)),
        'worst_week': float(np.min(p)),
    }

    # Optional baseline comparison
    if baseline_weekly_points is not None:
        baseline = np.array(baseline_weekly_points, dtype=float)
        baseline_total = float(np.sum(baseline))
        win_rate = float(np.sum(p >= baseline) / len(p))

        metrics['vs_baseline_total_points'] = total - baseline_total
        metrics['vs_baseline_win_rate'] = win_rate

    return metrics


def bootstrap_ci(
    strategy_a_seasons: List[Dict],
    strategy_b_seasons: Optional[List[Dict]] = None,
    metric_key: str = 'total_points',
    n_bootstrap: int = 10000,
    ci: float = 0.95,
) -> Dict[str, float]:
    """
    Compute bootstrapped confidence intervals for metric comparison.

    Resamples seasons with replacement to estimate 95% confidence intervals around
    metrics. Supports single-strategy (A) or pairwise (A vs B) comparison with
    significance testing.

    Args:
        strategy_a_seasons: List of dicts with metric_key values.
            Each dict should contain metric_key as a top-level key.
            Example: [{'total_points': 2100, 'sharpe_ratio': 0.62}, ...]
        strategy_b_seasons: Optional second strategy for pairwise comparison.
        metric_key: Metric to compute CI for (default 'total_points').
            Should match a key in the input dicts.
        n_bootstrap: Number of resampling iterations (default 10000).
        ci: Confidence level (default 0.95 = 95%).

    Returns:
        Dict with keys:
        - mean_a: Mean of metric for strategy A
        - ci_lower_a: Lower CI bound for A
        - ci_upper_a: Upper CI bound for A
        - mean_b: Mean of metric for strategy B (if B provided)
        - ci_lower_b: Lower CI bound for B (if B provided)
        - ci_upper_b: Upper CI bound for B (if B provided)
        - diff_mean: A - B (if B provided)
        - diff_ci_lower: Lower CI on difference (if B provided)
        - diff_ci_upper: Upper CI on difference (if B provided)
        - significant: Whether CI excludes 0 (if B provided); True if significant

    Raises:
        ValueError: If strategy_a_seasons is empty.
    """
    if not strategy_a_seasons or len(strategy_a_seasons) == 0:
        raise ValueError("strategy_a_seasons cannot be empty")

    # Extract metric values for A
    a_values = np.array([s.get(metric_key, 0.0) for s in strategy_a_seasons], dtype=float)

    # Bootstrap distribution for A
    a_bootstrap = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(a_values, size=len(a_values), replace=True)
        a_bootstrap.append(np.mean(sample))

    a_bootstrap = np.array(a_bootstrap)
    alpha = 1 - ci
    a_mean = float(np.mean(a_values))
    a_lower = float(np.percentile(a_bootstrap, alpha / 2 * 100))
    a_upper = float(np.percentile(a_bootstrap, (1 - alpha / 2) * 100))

    result = {
        'mean_a': a_mean,
        'ci_lower_a': a_lower,
        'ci_upper_a': a_upper,
    }

    # Pairwise comparison if B provided
    if strategy_b_seasons is not None:
        b_values = np.array([s.get(metric_key, 0.0) for s in strategy_b_seasons], dtype=float)

        # Bootstrap distribution for difference (A - B)
        diff_bootstrap = []
        for _ in range(n_bootstrap):
            a_sample = np.random.choice(a_values, size=len(a_values), replace=True)
            b_sample = np.random.choice(b_values, size=len(b_values), replace=True)
            diff_bootstrap.append(np.mean(a_sample) - np.mean(b_sample))

        diff_bootstrap = np.array(diff_bootstrap)
        b_mean = float(np.mean(b_values))
        b_lower = float(np.percentile(diff_bootstrap, alpha / 2 * 100))
        b_upper = float(np.percentile(diff_bootstrap, (1 - alpha / 2) * 100))

        # Significance: CI excludes 0?
        significant = not (b_lower <= 0.0 <= b_upper)

        result.update({
            'mean_b': b_mean,
            'ci_lower_b': b_lower,
            'ci_upper_b': b_upper,
            'diff_mean': a_mean - b_mean,
            'diff_ci_lower': float(np.percentile(diff_bootstrap, alpha / 2 * 100)),
            'diff_ci_upper': float(np.percentile(diff_bootstrap, (1 - alpha / 2) * 100)),
            'significant': significant,
        })

    return result


def apply_bonferroni_correction(
    num_comparisons: int,
    alpha: float = 0.05,
) -> float:
    """
    Apply Bonferroni correction for multiple comparisons.

    Controls family-wise error rate by dividing significance threshold by number
    of tests. Useful when comparing multiple strategies to avoid false positives
    from repeated testing.

    Args:
        num_comparisons: Number of statistical tests (e.g., 10 strategy pairs).
        alpha: Base significance level (default 0.05).

    Returns:
        Corrected alpha threshold: α / num_comparisons.

    Example:
        If testing 10 strategy variants against baseline at α=0.05:
        corrected_alpha = apply_bonferroni_correction(10)  # Returns 0.005
        Only reject null hypothesis if p-value < 0.005 (stricter threshold).

    Raises:
        ValueError: If num_comparisons <= 0.
    """
    if num_comparisons <= 0:
        raise ValueError("num_comparisons must be > 0")

    return alpha / num_comparisons


def format_metrics_table(
    strategy_results: Dict[str, Dict],
) -> str:
    """
    Format multi-strategy results as markdown table.

    Renders comparison results with point estimates and 95% confidence intervals
    for total points, Sharpe ratio, Sortino ratio, consistency (CV), and max drawdown.

    Args:
        strategy_results: Dict mapping strategy names to result dicts.
            Expected structure:
            {
                'strategy_name': {
                    'mean_metrics': {
                        'total_points': 2145.0,
                        'sharpe_ratio': 0.62,
                        'sortino_ratio': 1.23,
                        'coefficient_variation': 0.42,
                        'max_drawdown': 45.2,
                    },
                    'ci_metrics': {
                        'total_points': {
                            'ci_lower_a': 2100.0,
                            'ci_upper_a': 2190.0,
                        },
                        'sharpe_ratio': {
                            'ci_lower_a': 0.55,
                            'ci_upper_a': 0.69,
                        },
                        ...
                    }
                },
                ...
            }

    Returns:
        Markdown-formatted table string with columns:
        Strategy | Total Points | Mean ± 95% CI | Sharpe Ratio | Sortino Ratio | CV | Max Drawdown

    Raises:
        ValueError: If strategy_results is empty.
    """
    if not strategy_results:
        raise ValueError("strategy_results cannot be empty")

    lines = [
        "| Strategy | Total Points | Mean ± 95% CI | Sharpe Ratio | Sortino Ratio | CV | Max Drawdown |",
        "|----------|--------------|---------------|--------------|---------------|----|----|",
    ]

    for name, data in strategy_results.items():
        mean_metrics = data.get('mean_metrics', {})
        ci_metrics = data.get('ci_metrics', {})

        total = mean_metrics.get('total_points', 0.0)
        sharpe = mean_metrics.get('sharpe_ratio', 0.0)
        sortino = mean_metrics.get('sortino_ratio', 0.0)
        cv = mean_metrics.get('coefficient_variation', 0.0)
        mdd = mean_metrics.get('max_drawdown', 0.0)

        # Confidence intervals
        total_ci = ci_metrics.get('total_points', {})
        total_ci_lower = total_ci.get('ci_lower_a', total)
        total_ci_upper = total_ci.get('ci_upper_a', total)

        sharpe_ci = ci_metrics.get('sharpe_ratio', {})
        sharpe_ci_lower = sharpe_ci.get('ci_lower_a', sharpe)
        sharpe_ci_upper = sharpe_ci.get('ci_upper_a', sharpe)

        sortino_ci = ci_metrics.get('sortino_ratio', {})
        sortino_ci_lower = sortino_ci.get('ci_lower_a', sortino)
        sortino_ci_upper = sortino_ci.get('ci_upper_a', sortino)

        cv_ci = ci_metrics.get('coefficient_variation', {})
        cv_ci_lower = cv_ci.get('ci_lower_a', cv)
        cv_ci_upper = cv_ci.get('ci_upper_a', cv)

        mdd_ci = ci_metrics.get('max_drawdown', {})
        mdd_ci_lower = mdd_ci.get('ci_lower_a', mdd)
        mdd_ci_upper = mdd_ci.get('ci_upper_a', mdd)

        # Format cells
        total_cell = f"{total:.0f} [{total_ci_lower:.0f}, {total_ci_upper:.0f}]"
        sharpe_cell = f"{sharpe:.2f} [{sharpe_ci_lower:.2f}, {sharpe_ci_upper:.2f}]"
        sortino_cell = f"{sortino:.2f} [{sortino_ci_lower:.2f}, {sortino_ci_upper:.2f}]"
        cv_cell = f"{cv:.2f} [{cv_ci_lower:.2f}, {cv_ci_upper:.2f}]"
        mdd_cell = f"{mdd:.1f} [{mdd_ci_lower:.1f}, {mdd_ci_upper:.1f}]"

        line = (
            f"| {name} | {total_cell} | {total:.0f} | {sharpe_cell} | "
            f"{sortino_cell} | {cv_cell} | {mdd_cell} |"
        )
        lines.append(line)

    return '\n'.join(lines)
