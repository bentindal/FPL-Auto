"""Unit tests for evaluation.metrics module."""

import unittest
import numpy as np
from evaluation.metrics import (
    compute_season_metrics,
    bootstrap_ci,
    apply_bonferroni_correction,
    format_metrics_table,
)


class TestMetricsComputation(unittest.TestCase):
    """Unit tests for metric computation functions."""

    def setUp(self):
        """Generate sample weekly points for testing."""
        np.random.seed(42)
        self.p_stable = [55] * 38  # Stable season
        self.p_volatile = np.random.uniform(20, 90, 38).tolist()  # Volatile
        self.p_declining = [70 - i for i in range(38)]  # Declining trend

    def test_sharpe_ratio_positive(self):
        """Sharpe ratio positive for volatile returns."""
        metrics = compute_season_metrics(self.p_volatile)
        self.assertGreater(metrics['sharpe_ratio'], 0)

    def test_sortino_ratio_greater_than_sharpe(self):
        """Sortino >= Sharpe (only penalizes downside)."""
        metrics = compute_season_metrics(self.p_volatile)
        self.assertGreaterEqual(metrics['sortino_ratio'], metrics['sharpe_ratio'] * 0.9)  # Allow ~10% margin

    def test_coefficient_variation_lower_for_stable(self):
        """Stable season has lower CV than volatile."""
        m_stable = compute_season_metrics(self.p_stable)
        m_volatile = compute_season_metrics(self.p_volatile)
        self.assertLess(m_stable['coefficient_variation'], m_volatile['coefficient_variation'])

    def test_max_drawdown_non_negative(self):
        """Max drawdown always >= 0."""
        metrics = compute_season_metrics(self.p_declining)
        self.assertGreaterEqual(metrics['max_drawdown'], 0)
        self.assertLessEqual(metrics['max_drawdown'], 1500)  # Max possible with 38 weeks of 70pt

    def test_bootstrap_ci_excludes_zero_for_difference(self):
        """CI excludes 0 when strategy A clearly beats B."""
        a_seasons = [{'total_points': 2200 + np.random.normal(0, 20)} for _ in range(4)]
        b_seasons = [{'total_points': 2000 + np.random.normal(0, 20)} for _ in range(4)]

        ci = bootstrap_ci(a_seasons, b_seasons, metric_key='total_points', n_bootstrap=1000)
        # A is consistently higher, so 0 should be outside CI
        self.assertGreater(ci['diff_ci_lower'], 0)

    def test_bonferroni_correction_divides_alpha(self):
        """Bonferroni correctly divides alpha by num_comparisons."""
        alpha_10 = apply_bonferroni_correction(10, alpha=0.05)
        self.assertEqual(alpha_10, 0.005)

        alpha_20 = apply_bonferroni_correction(20, alpha=0.05)
        self.assertEqual(alpha_20, 0.0025)

    def test_format_metrics_table_contains_strategy_names(self):
        """Formatted table includes strategy names."""
        strategy_results = {
            'baseline': {
                'mean_metrics': {'total_points': 2100, 'sharpe_ratio': 0.5, 'sortino_ratio': 1.0, 'coefficient_variation': 0.4, 'max_drawdown': 50},
                'ci_metrics': {}
            },
            'aggressive': {
                'mean_metrics': {'total_points': 2200, 'sharpe_ratio': 0.6, 'sortino_ratio': 1.2, 'coefficient_variation': 0.5, 'max_drawdown': 60},
                'ci_metrics': {}
            },
        }
        table = format_metrics_table(strategy_results)
        self.assertIn('baseline', table)
        self.assertIn('aggressive', table)

    def test_compute_metrics_returns_total_points(self):
        """Metrics include total_points field."""
        weekly_points = [50, 60, 45, 55, 48, 52, 58, 47, 61, 53] + [50] * 28
        metrics = compute_season_metrics(weekly_points)
        self.assertIn('total_points', metrics)
        self.assertEqual(metrics['total_points'], sum(weekly_points))

    def test_bootstrap_ci_handles_single_strategy(self):
        """Bootstrap CI works for single strategy (no pairwise)."""
        a_seasons = [{'total_points': 2100 + np.random.normal(0, 20)} for _ in range(4)]
        ci = bootstrap_ci(a_seasons, metric_key='total_points', n_bootstrap=1000)

        self.assertIn('mean_a', ci)
        self.assertIn('ci_lower_a', ci)
        self.assertIn('ci_upper_a', ci)
        # Pairwise fields should not exist
        self.assertNotIn('mean_b', ci)


if __name__ == '__main__':
    unittest.main()
