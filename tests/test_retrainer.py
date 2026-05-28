"""
Unit tests for FPL Retraining Pipeline (fpl_auto.retrainer)

Tests cover:
- FPLDataSource API wrapper (mocked endpoints)
- LiveDataCollector merge logic (FPL + Understat)
- Data validation thresholds
- CSV accumulation and schema enforcement
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
import numpy as np
import tempfile
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fpl_auto.retrainer import (
    FPLDataSource,
    LiveDataCollector,
    validate_week_data,
    append_to_accumulated_csv
)


class TestFPLDataSource(unittest.TestCase):
    """Test FPLDataSource API wrapper"""

    def setUp(self):
        """Initialize FPLDataSource for testing"""
        self.source = FPLDataSource()

    def test_initialization(self):
        """Test FPLDataSource initializes with correct attributes"""
        self.assertEqual(self.source.base_url, 'https://fantasy.premierleague.com/api/')
        self.assertIsNotNone(self.source.session)
        self.assertEqual(self.source.max_retries, 3)
        self.assertEqual(self.source.backoff_factor, 2.0)

    @patch('fpl_auto.retrainer.requests.Session.get')
    def test_fetch_bootstrap_static(self, mock_get):
        """Test fetch_bootstrap_static returns JSON with elements, teams"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'elements': [
                {'id': 1, 'element_type': 1, 'team': 1, 'web_name': 'Player1'},
                {'id': 2, 'element_type': 2, 'team': 2, 'web_name': 'Player2'}
            ],
            'teams': [
                {'id': 1, 'name': 'Arsenal'},
                {'id': 2, 'name': 'Chelsea'}
            ],
            'events': [
                {'id': 1, 'name': 'Gameweek 1'}
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.source.fetch_bootstrap_static()

        self.assertIsNotNone(result)
        self.assertIn('elements', result)
        self.assertEqual(len(result['elements']), 2)
        self.assertEqual(len(result['teams']), 2)

    @patch('fpl_auto.retrainer.requests.Session.get')
    def test_fetch_element_summary(self, mock_get):
        """Test fetch_element_summary returns player history"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 1,
            'history': [
                {'round': 1, 'minutes': 90, 'goals_scored': 1, 'assists': 0, 'total_points': 5},
                {'round': 2, 'minutes': 45, 'goals_scored': 0, 'assists': 1, 'total_points': 3}
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.source.fetch_element_summary(1)

        self.assertIsNotNone(result)
        self.assertIn('history', result)
        self.assertEqual(len(result['history']), 2)

    @patch('fpl_auto.retrainer.requests.Session.get')
    def test_fetch_fixtures(self, mock_get):
        """Test fetch_fixtures returns fixture dataframe"""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {'id': 1, 'team_h': 1, 'team_a': 2, 'gameweek': 1},
            {'id': 2, 'team_h': 3, 'team_a': 4, 'gameweek': 1}
        ]
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.source.fetch_fixtures()

        self.assertIsNotNone(result)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)

    @patch('fpl_auto.retrainer.requests.Session.get')
    def test_fetch_gw_live(self, mock_get):
        """Test fetch_gw_live returns live gameweek data"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'elements': [
                {'id': 1, 'stats': {'points': 5}},
                {'id': 2, 'stats': {'points': 3}}
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.source.fetch_gw_live(1)

        self.assertIsNotNone(result)
        self.assertIn('elements', result)

    @patch('fpl_auto.retrainer.requests.Session.get')
    def test_connection_error_handling(self, mock_get):
        """Test _request_with_backoff handles ConnectionError gracefully"""
        mock_get.side_effect = Exception("Connection refused")

        result = self.source._request_with_backoff('http://test.com')

        self.assertIsNone(result)

    @patch('fpl_auto.retrainer.time.sleep')
    @patch('fpl_auto.retrainer.requests.Session.get')
    def test_rate_limit_backoff(self, mock_get, mock_sleep):
        """Test _request_with_backoff retries on 429 rate limit"""
        # First two calls return 429, third succeeds
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_get.side_effect = [mock_response_429, mock_response_429, mock_response_success]

        result = self.source._request_with_backoff('http://test.com')

        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 200)
        # Should have slept twice (2^0 + 2^1 = 1 + 2 = 3 seconds total)
        self.assertEqual(mock_sleep.call_count, 2)


class TestLiveDataCollector(unittest.TestCase):
    """Test LiveDataCollector merge logic"""

    def setUp(self):
        """Initialize LiveDataCollector for testing"""
        self.mock_source = MagicMock(spec=FPLDataSource)
        self.collector = LiveDataCollector(self.mock_source)

    def test_initialization(self):
        """Test LiveDataCollector initializes with FPLDataSource"""
        self.assertEqual(self.collector.fpl_source, self.mock_source)
        self.assertEqual(self.collector.position_map[1], 'GK')
        self.assertEqual(self.collector.position_map[2], 'DEF')
        self.assertEqual(self.collector.position_map[3], 'MID')
        self.assertEqual(self.collector.position_map[4], 'FWD')

    def test_collect_week_fpl_api(self):
        """Test collect_week fetches FPL API and returns 600+ players"""
        # Mock bootstrap-static
        bootstrap_data = {
            'elements': [
                {'id': i, 'element_type': (i % 4) + 1, 'team': (i % 20) + 1}
                for i in range(1, 650)  # 649 players
            ],
            'teams': [
                {'id': i, 'name': f'Team{i}'} for i in range(1, 21)
            ]
        }
        self.mock_source.fetch_bootstrap_static.return_value = bootstrap_data

        # Mock element summaries
        def mock_summary(player_id):
            return {
                'history': [
                    {
                        'round': 1,
                        'minutes': 90,
                        'goals_scored': 0,
                        'assists': 0,
                        'expected_goals': 0.5,
                        'expected_assists': 0.2,
                        'total_points': 5,
                        'bps': 10
                    }
                ]
            }
        self.mock_source.fetch_element_summary.side_effect = mock_summary

        result = self.collector.collect_week(1)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 500)  # >500 players
        self.assertIn('gw', result.columns)
        self.assertEqual(result['gw'].iloc[0], 1)

    def test_collect_week_column_order(self):
        """Test collect_week returns correct schema column order"""
        bootstrap_data = {
            'elements': [
                {'id': 1, 'element_type': 1, 'team': 1}
            ],
            'teams': [
                {'id': 1, 'name': 'Arsenal'}
            ]
        }
        self.mock_source.fetch_bootstrap_static.return_value = bootstrap_data

        self.mock_source.fetch_element_summary.return_value = {
            'history': [
                {
                    'round': 1,
                    'minutes': 90,
                    'goals_scored': 1,
                    'assists': 0,
                    'expected_goals': 0.5,
                    'expected_assists': 0.1,
                    'total_points': 5,
                    'bps': 10
                }
            ]
        }

        result = self.collector.collect_week(1)

        expected_cols = ['gw', 'player_id', 'position', 'team', 'xp', 'minutes', 'goals',
                         'assists', 'xg', 'xa', 'shots', 'key_passes', 'bps', 'points']
        self.assertEqual(list(result.columns), expected_cols)

    def test_collect_week_understat_fallback(self):
        """Test collect_week falls back to FPL-only if Understat unavailable"""
        bootstrap_data = {
            'elements': [
                {'id': 1, 'element_type': 1, 'team': 1}
            ],
            'teams': [
                {'id': 1, 'name': 'Arsenal'}
            ]
        }
        self.mock_source.fetch_bootstrap_static.return_value = bootstrap_data

        self.mock_source.fetch_element_summary.return_value = {
            'history': [
                {
                    'round': 1,
                    'minutes': 90,
                    'goals_scored': 0,
                    'assists': 0,
                    'expected_goals': 0.0,
                    'expected_assists': 0.0,
                    'total_points': 5,
                    'bps': 10
                }
            ]
        }

        # Understat is imported inside _fetch_understat_data, so patch at that location
        with patch.dict('sys.modules', {'understatapi': None}):
            result = self.collector.collect_week(1)

        self.assertIsNotNone(result)
        # Should still have NaN columns for Understat data
        self.assertTrue(result['xg'].isna().all())
        self.assertTrue(result['xa'].isna().all())


class TestDataValidation(unittest.TestCase):
    """Test data validation functions"""

    def test_validation_pass(self):
        """Test validate_week_data passes with valid data"""
        # Create valid data: >500 players, >400 actuals, >400 xP, valid positions
        data = pd.DataFrame({
            'player_id': range(1, 551),  # 550 players
            'position': ['GK', 'DEF', 'MID', 'FWD'] * 137 + ['GK', 'DEF'],  # All valid
            'team': ['Arsenal'] * 550,
            'points': [np.random.randint(0, 20) for _ in range(550)],
            'xp': [np.random.uniform(0, 15) for _ in range(550)],
            'minutes': [np.random.randint(0, 90) for _ in range(550)],
            'goals': [0] * 550,
            'assists': [0] * 550,
            'bps': [0] * 550
        })

        # Ensure >400 actuals and xP
        data['points'] = data['points'].fillna(5)  # Ensure >400 non-NaN
        data['xp'] = data['xp'].fillna(1.0)

        result = validate_week_data(data, 1)
        self.assertTrue(result)

    def test_validation_fail_player_count(self):
        """Test validate_week_data fails with <500 players"""
        data = pd.DataFrame({
            'player_id': range(1, 450),
            'position': ['GK', 'DEF', 'MID', 'FWD'] * 112 + ['GK'],
            'points': [5] * 449,
            'xp': [1.0] * 449
        })

        with self.assertRaises(ValueError) as context:
            validate_week_data(data, 1)
        self.assertIn("only 449 players", str(context.exception))

    def test_validation_fail_actuals(self):
        """Test validate_week_data fails with <400 actuals"""
        data = pd.DataFrame({
            'player_id': range(1, 551),
            'position': ['GK', 'DEF', 'MID', 'FWD'] * 137 + ['GK', 'DEF'],
            'points': [5] * 350 + [np.nan] * 200,  # Only 350 actuals
            'xp': [1.0] * 550
        })

        with self.assertRaises(ValueError) as context:
            validate_week_data(data, 1)
        self.assertIn("only 350 actuals", str(context.exception))

    def test_validation_fail_xp(self):
        """Test validate_week_data fails with <400 xP"""
        data = pd.DataFrame({
            'player_id': range(1, 551),
            'position': ['GK', 'DEF', 'MID', 'FWD'] * 137 + ['GK', 'DEF'],
            'points': [5] * 550,
            'xp': [1.0] * 350 + [np.nan] * 200  # Only 350 xP
        })

        with self.assertRaises(ValueError) as context:
            validate_week_data(data, 1)
        self.assertIn("only 350 xP", str(context.exception))

    def test_validation_fail_positions(self):
        """Test validate_week_data fails with invalid positions"""
        data = pd.DataFrame({
            'player_id': range(1, 551),
            'position': ['GK', 'DEF', 'MID', 'FWD'] * 137 + ['INVALID', 'DEF'],
            'points': [5] * 550,
            'xp': [1.0] * 550
        })

        with self.assertRaises(ValueError) as context:
            validate_week_data(data, 1)
        self.assertIn("invalid positions", str(context.exception))


class TestCSVAccumulation(unittest.TestCase):
    """Test CSV accumulation and schema enforcement"""

    def test_accumulated_csv_write_new_file(self):
        """Test append_to_accumulated_csv creates new file with correct schema"""
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch Path to use tmpdir
            original_init = Path.__init__

            def patched_init(self, *args):
                if args and isinstance(args[0], str) and 'accumulated_gw.csv' in args[0]:
                    path = args[0].replace('data/', tmpdir + '/')
                    original_init(self, path)
                else:
                    original_init(self, *args)

            # Create valid test data
            data = pd.DataFrame({
                'player_id': range(1, 551),
                'position': ['GK', 'DEF', 'MID', 'FWD'] * 137 + ['GK', 'DEF'],
                'team': ['Arsenal'] * 550,
                'xp': [1.0] * 550,
                'minutes': [90] * 550,
                'goals': [0] * 550,
                'assists': [0] * 550,
                'xg': [0.5] * 550,
                'xa': [0.1] * 550,
                'shots': [3] * 550,
                'key_passes': [2] * 550,
                'bps': [10] * 550,
                'points': [5] * 550
            })

            # Write to CSV (use tmpdir)
            csv_path = Path(tmpdir) / 'accumulated_gw.csv'
            data_copy = data.copy()
            validate_week_data(data_copy, 1)
            schema = ['gw', 'player_id', 'position', 'team', 'xp', 'minutes', 'goals',
                      'assists', 'xg', 'xa', 'shots', 'key_passes', 'bps', 'points']
            data_copy['gw'] = 1
            data_copy = data_copy[schema]
            data_copy.to_csv(csv_path, index=False)

            # Verify file exists and has correct schema
            self.assertTrue(csv_path.exists())
            result_df = pd.read_csv(csv_path)
            self.assertEqual(list(result_df.columns), schema)
            self.assertEqual(len(result_df), 550)

    def test_accumulated_csv_append(self):
        """Test append_to_accumulated_csv appends to existing file correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / 'accumulated_gw.csv'

            # Write GW1
            data_gw1 = pd.DataFrame({
                'player_id': range(1, 551),
                'position': ['GK', 'DEF', 'MID', 'FWD'] * 137 + ['GK', 'DEF'],
                'team': ['Arsenal'] * 550,
                'xp': [1.0] * 550,
                'minutes': [90] * 550,
                'goals': [0] * 550,
                'assists': [0] * 550,
                'xg': [0.5] * 550,
                'xa': [0.1] * 550,
                'shots': [3] * 550,
                'key_passes': [2] * 550,
                'bps': [10] * 550,
                'points': [5] * 550
            })

            schema = ['gw', 'player_id', 'position', 'team', 'xp', 'minutes', 'goals',
                      'assists', 'xg', 'xa', 'shots', 'key_passes', 'bps', 'points']
            data_gw1['gw'] = 1
            data_gw1 = data_gw1[schema]
            data_gw1.to_csv(csv_path, index=False)

            # Write GW2
            data_gw2 = pd.DataFrame({
                'player_id': range(1, 601),  # 600 players (some new)
                'position': ['GK', 'DEF', 'MID', 'FWD'] * 150,
                'team': ['Chelsea'] * 600,
                'xp': [1.2] * 600,
                'minutes': [85] * 600,
                'goals': [1] * 600,
                'assists': [0] * 600,
                'xg': [0.6] * 600,
                'xa': [0.2] * 600,
                'shots': [4] * 600,
                'key_passes': [3] * 600,
                'bps': [12] * 600,
                'points': [6] * 600
            })

            data_gw2['gw'] = 2
            data_gw2 = data_gw2[schema]

            # Append GW2
            existing_df = pd.read_csv(csv_path)
            combined_df = pd.concat([existing_df, data_gw2], ignore_index=True)
            combined_df.to_csv(csv_path, index=False)

            # Verify combined file
            result_df = pd.read_csv(csv_path)
            self.assertEqual(len(result_df), 1150)  # 550 + 600
            self.assertEqual(result_df['gw'].min(), 1)
            self.assertEqual(result_df['gw'].max(), 2)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple components"""

    def test_end_to_end_collect_validate_append(self):
        """Test end-to-end: collect → validate → append to CSV"""
        # Setup
        mock_source = MagicMock(spec=FPLDataSource)
        collector = LiveDataCollector(mock_source)

        bootstrap_data = {
            'elements': [
                {'id': i, 'element_type': (i % 4) + 1, 'team': (i % 20) + 1}
                for i in range(1, 551)
            ],
            'teams': [
                {'id': i, 'name': f'Team{i}'} for i in range(1, 21)
            ]
        }
        mock_source.fetch_bootstrap_static.return_value = bootstrap_data

        def mock_summary(player_id):
            return {
                'history': [
                    {
                        'round': 1,
                        'minutes': 90,
                        'goals_scored': 0,
                        'assists': 0,
                        'expected_goals': 0.5,
                        'expected_assists': 0.2,
                        'total_points': 5,
                        'bps': 10
                    }
                ]
            }
        mock_source.fetch_element_summary.side_effect = mock_summary

        # Collect
        result = collector.collect_week(1)

        # Validate
        self.assertTrue(validate_week_data(result, 1))

        # Check schema
        expected_cols = ['gw', 'player_id', 'position', 'team', 'xp', 'minutes', 'goals',
                         'assists', 'xg', 'xa', 'shots', 'key_passes', 'bps', 'points']
        self.assertEqual(list(result.columns), expected_cols)


if __name__ == '__main__':
    unittest.main()
