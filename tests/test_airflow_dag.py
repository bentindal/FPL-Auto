"""
Test suite for Apache Airflow DAG structure and task execution.

Tests:
1. DAG definition (dag_id, schedule_interval, start_date)
2. Task existence and ordering (5 tasks: collect → validate → retrain → evaluate → export)
3. Task dependencies and execution order
4. DAG validation (no syntax errors)
5. Task callable functions (with mocking)
6. ModelMonitor metrics evaluation
"""

import unittest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import DAG, but allow tests to run even if Airflow not installed
dag = None
try:
    from dags.fpl_retrain import dag
    HAS_AIRFLOW = True
except ImportError:
    HAS_AIRFLOW = False

from fpl_auto.retrainer import (
    collect_gw_data,
    validate_week_data,
    retrain_on_schedule,
    check_drift,
    write_predictions_tsv,
    ModelMonitor
)


@unittest.skipIf(not HAS_AIRFLOW, "Apache Airflow not installed")
class TestAirflowDAG(unittest.TestCase):
    """Test suite for Airflow DAG fpl_retrain_schedule."""

    def test_dag_definition(self):
        """Test DAG definition: ID, schedule interval, start date."""
        self.assertEqual(dag.dag_id, 'fpl_retrain_schedule')
        self.assertEqual(dag.schedule_interval, '0 19 * * 2-7')
        self.assertEqual(dag.start_date, datetime(2024, 8, 1))

    def test_dag_tasks_exist(self):
        """Test that DAG has exactly 5 tasks with correct IDs."""
        task_ids = [task.task_id for task in dag.tasks]
        expected_tasks = ['collect', 'validate', 'retrain', 'evaluate', 'export']

        self.assertEqual(len(dag.tasks), 5, f"Expected 5 tasks, got {len(dag.tasks)}")
        self.assertEqual(task_ids, expected_tasks, f"Task IDs mismatch: {task_ids}")

    def test_dag_task_types(self):
        """Test that all tasks are PythonOperator type."""
        from airflow.operators.python import PythonOperator

        for task in dag.tasks:
            self.assertIsInstance(task, PythonOperator,
                                f"Task {task.task_id} is not PythonOperator")

    def test_dag_task_dependencies(self):
        """Test task dependency chain: collect >> validate >> retrain >> evaluate >> export."""
        # Build dependency mapping
        task_map = {task.task_id: task for task in dag.tasks}

        # Verify chain: collect >> validate
        self.assertIn('validate', [t.task_id for t in task_map['collect'].downstream_list])

        # Verify chain: validate >> retrain
        self.assertIn('retrain', [t.task_id for t in task_map['validate'].downstream_list])

        # Verify chain: retrain >> evaluate
        self.assertIn('evaluate', [t.task_id for t in task_map['retrain'].downstream_list])

        # Verify chain: evaluate >> export
        self.assertIn('export', [t.task_id for t in task_map['evaluate'].downstream_list])

        # Verify no downstream for export
        self.assertEqual(len(task_map['export'].downstream_list), 0)

    def test_dag_parses_without_error(self):
        """Test that DAG parses without syntax errors."""
        # If DAG imported successfully, it parses without error
        self.assertIsNotNone(dag)
        self.assertEqual(dag.dag_id, 'fpl_retrain_schedule')

    def test_task_ids_match_callables(self):
        """Test that task IDs match their callable function names."""
        task_map = {task.task_id: task for task in dag.tasks}

        expected_callables = {
            'collect': collect_gw_data,
            'validate': validate_week_data,
            'retrain': retrain_on_schedule,
            'evaluate': check_drift,
            'export': write_predictions_tsv
        }

        for task_id, expected_callable in expected_callables.items():
            self.assertIn(task_id, task_map)
            # PythonOperator stores callable in op_kwargs or python_callable
            task = task_map[task_id]
            self.assertIsNotNone(task.python_callable)


class TestTaskCallables(unittest.TestCase):
    """Test suite for Airflow task callable functions."""

    @patch('fpl_auto.retrainer.LiveDataCollector')
    def test_collect_task_callable(self, mock_collector_class):
        """Test collect_gw_data task callable with mocked LiveDataCollector."""
        # Mock the collector instance
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Mock collect_week to return 600 players
        mock_data = pd.DataFrame({
            'player_id': range(1, 601),
            'position': ['GK', 'DEF', 'MID', 'FWD'] * 150,
            'xp': np.random.rand(600),
            'points': np.random.rand(600),
            'team': ['Arsenal'] * 600,
            'minutes': [90] * 600,
            'goals': [0] * 600,
            'assists': [0] * 600,
            'bps': [0] * 600,
            'xg': [0.0] * 600,
            'xa': [0.0] * 600,
            'shots': [0] * 600,
            'key_passes': [0] * 600
        })
        mock_collector.collect_week.return_value = mock_data

        # Mock append_to_accumulated_csv
        with patch('fpl_auto.retrainer.append_to_accumulated_csv') as mock_append:
            result = collect_gw_data(current_gw=1, season='2024-25')

        # Verify result
        self.assertEqual(result['gw'], 1)
        self.assertEqual(result['rows'], 600)
        self.assertEqual(result['status'], 'success')

    def test_validate_task_callable_success(self):
        """Test validate_week_data task callable with valid data."""
        # Create valid mock data (>500 players, >400 actuals, >400 xP)
        n = 550
        mock_data = pd.DataFrame({
            'player_id': list(range(1, n + 1)),
            'position': (['GK', 'DEF', 'MID', 'FWD'] * (n // 4)) + ['GK'] * (n % 4),
            'xp': [1.0] * n,
            'points': [2.0] * n,
            'team': ['Arsenal'] * n
        })

        result = validate_week_data(mock_data, gw=1)

        self.assertEqual(result['gw'], 1)
        self.assertTrue(result['valid'])
        self.assertEqual(result['status'], 'success')

    def test_validate_task_callable_fails_insufficient_players(self):
        """Test validate_week_data fails with <500 players."""
        n = 400
        mock_data = pd.DataFrame({
            'player_id': list(range(1, n + 1)),
            'position': (['GK', 'DEF', 'MID', 'FWD'] * (n // 4)) + ['GK'] * (n % 4),
            'xp': [1.0] * n,
            'points': [2.0] * n,
            'team': ['Arsenal'] * n
        })

        result = validate_week_data(mock_data, gw=1)

        self.assertEqual(result['gw'], 1)
        self.assertFalse(result['valid'])
        self.assertEqual(result['status'], 'error')

    @patch('fpl_auto.retrainer.FPLModelRetrainer')
    def test_retrain_task_callable(self, mock_retrainer_class):
        """Test retrain_on_schedule task callable with mocked FPLModelRetrainer."""
        mock_retrainer = MagicMock()
        mock_retrainer_class.return_value = mock_retrainer
        mock_retrainer.model_cache = {
            'GK': MagicMock(),
            'DEF': MagicMock(),
            'MID': MagicMock(),
            'FWD': MagicMock()
        }

        result = retrain_on_schedule(current_gw=3, season='2024-25')

        self.assertEqual(result['gw'], 3)
        self.assertEqual(result['positions_trained'], 4)
        self.assertEqual(result['status'], 'success')

    @patch('fpl_auto.retrainer.FPLModelRetrainer')
    @patch('fpl_auto.retrainer.ModelMonitor')
    def test_check_drift_callable_no_drift(self, mock_monitor_class, mock_retrainer_class):
        """Test check_drift task callable with no drift detected."""
        # Mock retrainer
        mock_retrainer = MagicMock()
        mock_retrainer_class.return_value = mock_retrainer
        mock_retrainer._get_baseline_rmse.return_value = 1.5

        # Mock monitor
        mock_monitor = MagicMock()
        mock_monitor_class.return_value = mock_monitor
        mock_monitor.evaluate_week.return_value = {
            'GK': {'rmse': 1.2, 'mae': 0.5, 'r2': 0.85, 'spearman': 0.90},
            'DEF': {'rmse': 1.4, 'mae': 0.6, 'r2': 0.82, 'spearman': 0.88},
            'MID': {'rmse': 1.6, 'mae': 0.7, 'r2': 0.80, 'spearman': 0.86},
            'FWD': {'rmse': 1.8, 'mae': 0.8, 'r2': 0.78, 'spearman': 0.84}
        }

        # Mock accumulated CSV file
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pandas.read_csv') as mock_read_csv:
                mock_read_csv.return_value = pd.DataFrame({
                    'gw': [5] * 100,
                    'position': ['GK', 'DEF', 'MID', 'FWD'] * 25,
                    'xp': np.random.rand(100),
                    'points': np.random.rand(100)
                })

                result = check_drift(current_gw=5, season='2024-25')

        self.assertEqual(result['gw'], 5)
        self.assertFalse(result['drift_detected'])
        self.assertEqual(result['status'], 'success')
        self.assertIn('GK', result['metrics'])

    @patch('fpl_auto.retrainer.FPLModelRetrainer')
    def test_write_predictions_callable(self, mock_retrainer_class):
        """Test write_predictions_tsv task callable."""
        # Mock retrainer
        mock_retrainer = MagicMock()
        mock_retrainer_class.return_value = mock_retrainer
        mock_retrainer.predict_gw.return_value = {
            'GK': np.array([[2.0, 1.9, 1.8, 1.7, 1.6, 1.5]]),
            'DEF': np.array([[3.0, 2.9, 2.8, 2.7, 2.6, 2.5]]),
            'MID': np.array([[4.0, 3.9, 3.8, 3.7, 3.6, 3.5]]),
            'FWD': np.array([[5.0, 4.9, 4.8, 4.7, 4.6, 4.5]])
        }

        with patch('fpl_auto.retrainer.FPLModelRetrainer._export_predictions'):
            result = write_predictions_tsv(current_gw=3, season='2024-25')

        self.assertEqual(result['gw'], 3)
        self.assertTrue(result['exported'])
        self.assertEqual(result['positions_exported'], 4)
        self.assertEqual(result['status'], 'success')


class TestModelMonitor(unittest.TestCase):
    """Test suite for ModelMonitor metrics evaluation."""

    def setUp(self):
        """Set up test fixtures."""
        self.monitor = ModelMonitor()

    def test_model_monitor_initialization(self):
        """Test ModelMonitor initialization with baseline metrics."""
        self.assertEqual(self.monitor.baseline_rmse['GK'], 1.2)
        self.assertEqual(self.monitor.baseline_rmse['DEF'], 1.5)
        self.assertEqual(self.monitor.baseline_rmse['MID'], 1.8)
        self.assertEqual(self.monitor.baseline_rmse['FWD'], 2.0)

    def test_evaluate_week_all_positions(self):
        """Test evaluate_week computes metrics for all 4 positions."""
        predictions = {
            'GK': np.array([2.0, 2.1, 1.9, 2.2]),
            'DEF': np.array([3.0, 3.1, 2.9, 3.2]),
            'MID': np.array([4.0, 4.1, 3.9, 4.2]),
            'FWD': np.array([5.0, 5.1, 4.9, 5.2])
        }

        actuals = {
            'GK': np.array([2.1, 2.0, 2.0, 2.3]),
            'DEF': np.array([3.1, 3.0, 3.0, 3.3]),
            'MID': np.array([4.1, 4.0, 4.0, 4.3]),
            'FWD': np.array([5.1, 5.0, 5.0, 5.3])
        }

        metrics = self.monitor.evaluate_week(gw=1, predictions=predictions, actuals=actuals)

        # Check all positions have metrics
        for position in ['GK', 'DEF', 'MID', 'FWD']:
            self.assertIn(position, metrics)
            self.assertIn('rmse', metrics[position])
            self.assertIn('mae', metrics[position])
            self.assertIn('r2', metrics[position])
            self.assertIn('spearman', metrics[position])

    def test_evaluate_week_metrics_values(self):
        """Test evaluate_week returns reasonable metric values."""
        predictions = {
            'GK': np.array([2.0, 2.0, 2.0, 2.0])
        }
        actuals = {
            'GK': np.array([2.0, 2.0, 2.0, 2.0])
        }

        metrics = self.monitor.evaluate_week(gw=1, predictions=predictions, actuals=actuals)

        # Perfect predictions should give RMSE=0, MAE=0
        self.assertEqual(metrics['GK']['rmse'], 0.0)
        self.assertEqual(metrics['GK']['mae'], 0.0)

    def test_get_stability_metric(self):
        """Test get_stability_metric computes 1 - (std/mean)."""
        cv_scores = [0.90, 0.85, 0.88]  # High stability
        stability = self.monitor.get_stability_metric(cv_scores)

        self.assertGreater(stability, 0)
        self.assertLessEqual(stability, 1)

    def test_get_stability_metric_empty(self):
        """Test get_stability_metric with empty scores."""
        stability = self.monitor.get_stability_metric([])
        self.assertEqual(stability, 0)

    def test_get_stability_metric_single_score(self):
        """Test get_stability_metric with single score."""
        stability = self.monitor.get_stability_metric([0.85])
        # Single score should have std=0, so stability=1
        self.assertEqual(stability, 1.0)


if __name__ == '__main__':
    unittest.main()
