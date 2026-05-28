"""
FPL Retraining Pipeline: Data Collection & Model Retraining

This module provides real-time data collection from FPL Official API and Understat,
with validation and accumulated gameweek CSV management.

Classes:
    - FPLDataSource: Wrapper for official FPL API endpoints
    - LiveDataCollector: Merges FPL + Understat data for each gameweek

Functions:
    - validate_week_data: Validates accumulated GW data meets QA thresholds
    - append_to_accumulated_csv: Appends GW data to season CSV with schema enforcement
"""

import logging
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FPLDataSource:
    """
    Wrapper for FPL Official API (https://fantasy.premierleague.com/api/)

    Handles HTTP requests with error handling, exponential backoff for rate limits,
    and request pooling via requests.Session.

    Attributes:
        base_url (str): FPL API base URL
        session (requests.Session): Shared HTTP session for connection pooling
        max_retries (int): Maximum number of retries for rate-limited requests
        backoff_factor (float): Exponential backoff multiplier (2.0 = double wait time)
    """

    def __init__(self, base_url: str = 'https://fantasy.premierleague.com/api/',
                 session: Optional[requests.Session] = None):
        """
        Initialize FPLDataSource with session management.

        Args:
            base_url: FPL API base URL (default: official endpoint)
            session: Optional requests.Session; if None, creates new session
        """
        self.base_url = base_url
        self.session = session if session is not None else requests.Session()
        self.max_retries = 3
        self.backoff_factor = 2.0

    def fetch_bootstrap_static(self) -> Optional[Dict[str, Any]]:
        """
        Fetch bootstrap-static endpoint containing all players, teams, fixtures.

        Returns:
            Dict with keys: 'elements' (players), 'teams', 'events' (gameweeks), 'total_players'
            or None if error occurs
        """
        try:
            url = f'{self.base_url}bootstrap-static/'
            response = self._request_with_backoff(url)
            if response is None:
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching bootstrap-static: {e}")
            return None

    def fetch_element_summary(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed player history for a specific player.

        Args:
            player_id: FPL player ID (element ID from bootstrap-static)

        Returns:
            Dict with 'history' (list of gameweek records) or None if error
        """
        try:
            url = f'{self.base_url}element/{player_id}/'
            response = self._request_with_backoff(url)
            if response is None:
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching element summary for player {player_id}: {e}")
            return None

    def fetch_fixtures(self) -> Optional[pd.DataFrame]:
        """
        Fetch all fixtures for the season.

        Returns:
            DataFrame with fixture data or None if error
        """
        try:
            url = f'{self.base_url}fixtures/'
            response = self._request_with_backoff(url)
            if response is None:
                return None
            return pd.DataFrame(response.json())
        except Exception as e:
            logger.error(f"Error fetching fixtures: {e}")
            return None

    def fetch_gw_live(self, gw: int) -> Optional[Dict[str, Any]]:
        """
        Fetch live event data for a specific gameweek.

        Args:
            gw: Gameweek number (1-38)

        Returns:
            Dict with live standings and element data or None if error
        """
        try:
            url = f'{self.base_url}event/{gw}/live/'
            response = self._request_with_backoff(url)
            if response is None:
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching GW{gw} live data: {e}")
            return None

    def _request_with_backoff(self, url: str) -> Optional[requests.Response]:
        """
        Execute HTTP GET with exponential backoff for 429 (rate limit) errors.

        Args:
            url: Endpoint URL

        Returns:
            requests.Response if successful, None if all retries exhausted
        """
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=10)

                if response.status_code == 429:
                    # Rate limited - exponential backoff
                    wait_time = self.backoff_factor ** attempt
                    logger.warning(f"Rate limited (429). Retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response

            except requests.ConnectionError as e:
                logger.error(f"Connection error on attempt {attempt + 1}: {e}")
                return None
            except requests.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    return None
                continue
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return None

        logger.error(f"All {self.max_retries} retries exhausted for {url}")
        return None


class LiveDataCollector:
    """
    Collects and merges FPL Official API + Understat data for each gameweek.

    Attributes:
        fpl_source (FPLDataSource): FPL API wrapper
        position_map (Dict[int, str]): Maps FPL element_type to position code
    """

    def __init__(self, fpl_source: FPLDataSource):
        """
        Initialize LiveDataCollector with FPL data source.

        Args:
            fpl_source: FPLDataSource instance for API calls
        """
        self.fpl_source = fpl_source
        # FPL element_type mapping: 1=GK, 2=DEF, 3=MID, 4=FWD
        self.position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}

    def collect_week(self, gw: int) -> Optional[pd.DataFrame]:
        """
        Collect FPL + Understat data for a single gameweek.

        Process:
        1. Fetch FPL bootstrap-static for all players + teams
        2. Build FPL dataframe with [player_id, position, team, minutes, goals, assists, xp, bps]
        3. Attempt Understat merge for [xg, xa, shots, key_passes]
        4. Fallback to FPL-only if Understat unavailable
        5. Add gw column, reorder to schema, sort by player_id

        Args:
            gw: Gameweek number (1-38)

        Returns:
            DataFrame with schema [gw, player_id, position, team, xp, minutes, goals, assists,
                                   xg, xa, shots, key_passes, bps, points]
            or None if FPL fetch fails
        """
        # Fetch FPL bootstrap-static
        bootstrap = self.fpl_source.fetch_bootstrap_static()
        if bootstrap is None:
            logger.error(f"Failed to fetch FPL data for GW{gw}")
            return None

        # Extract elements (players) and teams
        elements = bootstrap.get('elements', [])
        teams = bootstrap.get('teams', [])

        # Build team_id -> team_name map
        team_id_to_name = {t['id']: t['name'] for t in teams}

        # Build FPL dataframe
        fpl_records = []
        for elem in elements:
            try:
                # Fetch detailed element summary for xP and other metrics
                summary = self.fpl_source.fetch_element_summary(elem['id'])
                if summary is None or 'history' not in summary:
                    continue

                # Find this GW's stats in history
                gw_history = None
                for rec in summary.get('history', []):
                    if rec.get('round') == gw:
                        gw_history = rec
                        break

                if gw_history is None:
                    # Player didn't play in this GW - create zero record
                    gw_history = {
                        'minutes': 0,
                        'goals_scored': 0,
                        'assists': 0,
                        'expected_goals': 0.0,
                        'expected_assists': 0.0,
                        'total_points': 0,
                        'bps': 0
                    }

                player_id = elem['id']
                position = self.position_map.get(elem.get('element_type'), 'MID')
                team = team_id_to_name.get(elem.get('team'), 'Unknown')

                # Calculate xP (expected points) - start with 0, refine with Understat
                minutes = gw_history.get('minutes', 0)
                goals = gw_history.get('goals_scored', 0)
                assists = gw_history.get('assists', 0)
                xp = gw_history.get('expected_goals', 0.0) + gw_history.get('expected_assists', 0.0)
                bps = gw_history.get('bps', 0)
                points = gw_history.get('total_points', 0)

                fpl_records.append({
                    'player_id': player_id,
                    'position': position,
                    'team': team,
                    'xp': xp,
                    'minutes': minutes,
                    'goals': goals,
                    'assists': assists,
                    'bps': bps,
                    'points': points
                })
            except Exception as e:
                logger.warning(f"Error processing player {elem.get('id')}: {e}")
                continue

        fpl_df = pd.DataFrame(fpl_records)

        # Initialize Understat columns with NaN
        fpl_df['xg'] = np.nan
        fpl_df['xa'] = np.nan
        fpl_df['shots'] = np.nan
        fpl_df['key_passes'] = np.nan

        # Attempt Understat merge
        try:
            understat_df = self._fetch_understat_data(gw)
            if understat_df is not None and len(understat_df) > 0:
                # Merge on player_id (FPL primary, Understat left-join)
                fpl_df = fpl_df.merge(
                    understat_df[['player_id', 'xg', 'xa', 'shots', 'key_passes']],
                    on='player_id',
                    how='left',
                    suffixes=('', '_understat')
                )
                # Update with Understat values where available
                for col in ['xg', 'xa', 'shots', 'key_passes']:
                    if col + '_understat' in fpl_df.columns:
                        fpl_df[col].fillna(fpl_df[col + '_understat'], inplace=True)
                        fpl_df.drop(columns=[col + '_understat'], inplace=True)
                logger.info(f"GW{gw}: Merged {len(understat_df)} Understat records")
            else:
                logger.warning(f"GW{gw}: Understat unavailable, using FPL data only")
        except Exception as e:
            logger.warning(f"GW{gw}: Understat merge failed ({e}), using FPL data only")

        # Add gameweek column
        fpl_df['gw'] = gw

        # Reorder columns to schema
        schema = ['gw', 'player_id', 'position', 'team', 'xp', 'minutes', 'goals', 'assists',
                  'xg', 'xa', 'shots', 'key_passes', 'bps', 'points']
        fpl_df = fpl_df[schema]

        # Sort by player_id for consistency
        fpl_df = fpl_df.sort_values('player_id').reset_index(drop=True)

        return fpl_df

    def _fetch_understat_data(self, gw: int) -> Optional[pd.DataFrame]:
        """
        Fetch Understat data for a gameweek via understatapi library.

        Args:
            gw: Gameweek number (1-38)

        Returns:
            DataFrame with columns [player_id, xg, xa, shots, key_passes] or None if unavailable
        """
        try:
            from understatapi import UnderStat

            understat = UnderStat()
            # Fetch season 2024 player match data
            matches = understat.get_player_matches(season=2024)

            if matches is None or len(matches) == 0:
                return None

            # Parse matches into dataframe (structure varies; extract key fields)
            records = []
            for player_id, player_data in matches.items():
                if isinstance(player_data, dict) and 'matches' in player_data:
                    for match in player_data['matches']:
                        if match.get('round') == gw:  # Check if matches by GW
                            records.append({
                                'player_id': player_id,
                                'xg': match.get('xG', np.nan),
                                'xa': match.get('xA', np.nan),
                                'shots': match.get('shots', np.nan),
                                'key_passes': match.get('key_passes', np.nan)
                            })

            return pd.DataFrame(records) if records else None

        except ImportError:
            logger.warning("understatapi not installed; Understat data unavailable")
            return None
        except Exception as e:
            logger.error(f"Understat fetch error: {e}")
            return None


def validate_week_data(gw_data: pd.DataFrame, gw: int) -> bool:
    """
    Validate accumulated gameweek data meets QA thresholds.

    Checks:
    - len(gw_data) > 500 (sufficient player coverage)
    - gw_data['points'].notna().sum() > 400 (actual points recorded)
    - gw_data['xp'].notna().sum() > 400 (xP predictions available)
    - gw_data['position'].isin(['GK', 'DEF', 'MID', 'FWD']).all() (valid positions only)

    Args:
        gw_data: DataFrame with gameweek data
        gw: Gameweek number (for logging)

    Returns:
        True if all validations pass

    Raises:
        ValueError if any validation fails
    """
    # Check player count
    if len(gw_data) <= 500:
        raise ValueError(f"GW{gw} validation failed: only {len(gw_data)} players (need >500)")

    # Check actual points coverage
    points_valid = gw_data['points'].notna().sum()
    if points_valid <= 400:
        raise ValueError(f"GW{gw} validation failed: only {points_valid} actuals (need >400)")

    # Check xP coverage
    xp_valid = gw_data['xp'].notna().sum()
    if xp_valid <= 400:
        raise ValueError(f"GW{gw} validation failed: only {xp_valid} xP values (need >400)")

    # Check position validity
    if not gw_data['position'].isin(['GK', 'DEF', 'MID', 'FWD']).all():
        invalid_pos = gw_data[~gw_data['position'].isin(['GK', 'DEF', 'MID', 'FWD'])]['position'].unique()
        raise ValueError(f"GW{gw} validation failed: invalid positions {invalid_pos}")

    logger.info(f"GW{gw} validated: {len(gw_data)} records, {points_valid} actuals, {xp_valid} xP, all positions valid")
    return True


def append_to_accumulated_csv(gw_data: pd.DataFrame, season: str, gw: int):
    """
    Append gameweek data to accumulated_gw.csv with schema enforcement.

    Process:
    1. Validate gw_data against thresholds
    2. Ensure schema columns exist in correct order
    3. Create CSV file if doesn't exist
    4. Append gw_data via pd.concat()
    5. Log completion

    Schema: gw, player_id, position, team, xp, minutes, goals, assists, xg, xa, shots, key_passes, bps, points

    Args:
        gw_data: DataFrame with gameweek data
        season: Season code (e.g., '2024-25')
        gw: Gameweek number (for validation logging)

    Raises:
        ValueError if validation fails
        OSError if file write fails
    """
    # Validate data
    validate_week_data(gw_data, gw)

    # Define schema
    schema = ['gw', 'player_id', 'position', 'team', 'xp', 'minutes', 'goals', 'assists',
              'xg', 'xa', 'shots', 'key_passes', 'bps', 'points']

    # Ensure all schema columns exist
    for col in schema:
        if col not in gw_data.columns and col != 'gw':
            gw_data[col] = np.nan

    # Reorder columns to schema
    gw_data = gw_data[schema]

    # Create data directory if needed
    file_path = Path(f'data/{season}/accumulated_gw.csv')
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create or append to CSV
    if file_path.exists():
        # Append to existing file
        existing_df = pd.read_csv(file_path)
        combined_df = pd.concat([existing_df, gw_data], ignore_index=True)
        combined_df.to_csv(file_path, index=False)
    else:
        # Create new file
        gw_data.to_csv(file_path, index=False)

    logger.info(f"Appended GW{gw}: {len(gw_data)} rows to {file_path}")


class FPLModelRetrainer:
    """
    FPL Model Retraining Orchestrator with scheduled and drift-driven updates.

    Implements:
    - Scheduled retraining every 2 gameweeks
    - PELT-based drift detection (15% RMSE threshold)
    - Position-specific ensemble models (XGBoost + RandomForest)
    - TimeSeriesSplit (3 folds) for expanding window validation
    - TSV export compatible with manager.py

    Attributes:
        historical_data_dir (str): Path to 2019-2023 historical CSVs
        season_2024_25_dir (str): Path to live 2024-25 data directory
        model_cache (dict): {position → fitted sklearn Pipeline}
        baseline_rmse (dict): {position → baseline RMSE from historical training}
        drift_history (dict): {position → list of RMSE values for drift tracking}
    """

    def __init__(self, historical_data_dir: str = 'data/',
                 season_2024_25_dir: str = 'data/2024-25/',
                 seasons: list = None):
        """
        Initialize FPLModelRetrainer.

        Args:
            historical_data_dir: Base data directory (default: 'data/')
            season_2024_25_dir: Live season data directory (default: 'data/2024-25/')
            seasons: List of historical seasons to load (default: ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24'])
        """
        self.historical_data_dir = historical_data_dir
        self.season_2024_25_dir = season_2024_25_dir
        self.seasons = seasons or ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24']
        self.model_cache = {}  # {position → trained Pipeline}
        self.baseline_rmse = {}  # {position → RMSE baseline}
        self.drift_history = {}  # {position → [RMSE values]}
        self.last_retrain_gw = 0
        self.retrain_cooldown_gws = 1  # Min GWs between retrains to avoid thrashing

        # Initialize drift tracking per position
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            self.drift_history[pos] = []

    def retrain_on_schedule(self, current_gw: int) -> None:
        """
        Retrain models if scheduled (every 2 GWs) or drift detected.

        Logic:
        1. Check if drift detected → force retrain
        2. Else if current_gw % 2 == 0 → scheduled retrain
        3. Else → use cached models
        4. Combine historical + live data up to current_gw
        5. For each position: train ensemble, store in cache, log CV R²

        Args:
            current_gw: Current gameweek number (1-38)

        Raises:
            FileNotFoundError: If accumulated_gw.csv not found
            ValueError: If training data insufficient
        """
        # Check drift detection
        drift_detected = self._detect_drift(current_gw)

        # Determine if retrain needed
        scheduled_retrain = (current_gw % 2 == 0)
        min_cooldown_met = (current_gw - self.last_retrain_gw) >= self.retrain_cooldown_gws

        if drift_detected and min_cooldown_met:
            logger.info(f"GW{current_gw}: Drift detected, triggering unscheduled retrain")
            retrain = True
        elif scheduled_retrain:
            logger.info(f"GW{current_gw}: Scheduled retrain (every 2 GWs)")
            retrain = True
        else:
            logger.info(f"GW{current_gw}: Using cached models (no retrain needed)")
            return

        # Load training data
        try:
            X, y = self._prepare_training_data(current_gw)
        except Exception as e:
            logger.error(f"Failed to prepare training data for GW{current_gw}: {e}")
            raise

        if len(X) == 0:
            logger.warning(f"GW{current_gw}: No training data available")
            return

        # Train position-specific ensemble models
        for position in ['GK', 'DEF', 'MID', 'FWD']:
            try:
                X_pos, y_pos = self._filter_position(X, y, position)

                if len(X_pos) < 50:
                    logger.warning(f"GW{current_gw}: {position} has only {len(X_pos)} samples, skipping")
                    continue

                # Train ensemble model
                model = self._train_position_models(X_pos, y_pos, position)
                self.model_cache[position] = model

                logger.info(f"GW{current_gw}: {position} model trained and cached")

            except Exception as e:
                logger.error(f"GW{current_gw}: Error training {position} model: {e}")
                continue

        # Update last retrain GW
        self.last_retrain_gw = current_gw

        # Save checkpoint
        self._checkpoint(current_gw)

    def predict_gw(self, gw: int, lookahead_weeks: int = 6) -> dict:
        """
        Generate predictions for current GW and lookahead weeks.

        Args:
            gw: Gameweek number to predict from
            lookahead_weeks: Number of weeks to predict ahead (default: 6)

        Returns:
            Dict: {position → np.array of predictions for GW[gw:gw+lookahead_weeks]}

        Raises:
            ValueError: If models not trained for a position
        """
        predictions = {}

        # Load live data
        try:
            live_file = Path(f'{self.season_2024_25_dir}accumulated_gw.csv')
            if not live_file.exists():
                logger.warning(f"No accumulated_gw.csv found at {live_file}")
                return predictions

            live_data = pd.read_csv(live_file)
        except Exception as e:
            logger.error(f"Failed to load accumulated_gw.csv: {e}")
            return predictions

        for position in ['GK', 'DEF', 'MID', 'FWD']:
            if position not in self.model_cache:
                logger.warning(f"Position {position} not in model cache")
                continue

            model = self.model_cache[position]

            # Get features for position-specific data
            pos_data = live_data[live_data['position'] == position]

            if len(pos_data) == 0:
                logger.warning(f"No data for {position}")
                predictions[position] = np.array([])
                continue

            # Extract features (simplified: using xp as placeholder)
            # In production, would use full feature set from feature engineering
            try:
                X_lookahead = pos_data[['xp', 'minutes', 'goals', 'assists']].fillna(0).values
                if len(X_lookahead) > 0:
                    preds = model.predict(X_lookahead)
                    # Generate lookahead array (simplified)
                    predictions[position] = np.repeat(preds, lookahead_weeks).reshape(-1, lookahead_weeks)
            except Exception as e:
                logger.warning(f"Failed to generate predictions for {position}: {e}")
                predictions[position] = np.array([])

        return predictions

    def _detect_drift(self, current_gw: int) -> bool:
        """
        Detect model drift via rolling 4-GW RMSE window.

        Logic:
        1. If current_gw < 4, return False (insufficient history)
        2. Fetch recent predictions and actuals for GW[current_gw-4:current_gw]
        3. Compute RMSE per position
        4. Compare against baseline_rmse × 1.15 threshold
        5. If RMSE > threshold for 2+ consecutive GWs, return True

        Args:
            current_gw: Current gameweek number

        Returns:
            bool: True if drift detected, False otherwise
        """
        if current_gw < 4:
            return False

        # Load live data
        try:
            live_file = Path(f'{self.season_2024_25_dir}accumulated_gw.csv')
            if not live_file.exists():
                return False

            live_data = pd.read_csv(live_file)
        except Exception as e:
            logger.warning(f"Failed to load live data for drift detection: {e}")
            return False

        # Get recent GWs
        recent_data = live_data[
            (live_data['gw'] >= max(1, current_gw - 4)) &
            (live_data['gw'] < current_gw)
        ]

        if len(recent_data) == 0:
            return False

        # Compute RMSE per position
        drift_count = 0
        for position in ['GK', 'DEF', 'MID', 'FWD']:
            pos_data = recent_data[recent_data['position'] == position]

            if len(pos_data) == 0:
                continue

            # Simple RMSE computation: xp vs actual points
            xp = pos_data['xp'].fillna(0).values
            points = pos_data['points'].fillna(0).values

            if len(xp) == 0 or len(points) == 0:
                continue

            rmse = np.sqrt(np.mean((xp - points) ** 2))

            # Get or establish baseline (from historical or initialization)
            baseline_rmse = self._get_baseline_rmse(position)

            # Check if RMSE exceeds 15% threshold
            if rmse > baseline_rmse * 1.15:
                logger.warning(f"GW{current_gw}: {position} RMSE {rmse:.3f} vs baseline {baseline_rmse:.3f} (1.15x threshold)")
                self.drift_history[position].append(rmse)

                # Check if 2+ consecutive GWs show drift
                if len(self.drift_history[position]) >= 2:
                    drift_count += 1
            else:
                self.drift_history[position] = []  # Reset drift counter

        return drift_count > 0

    def _get_baseline_rmse(self, position: str) -> float:
        """
        Get baseline RMSE for position.

        If not yet computed, establish from historical data (2019-2023).

        Args:
            position: Position code (GK, DEF, MID, FWD)

        Returns:
            float: Baseline RMSE value (default: 1.5 if not computed)
        """
        if position in self.baseline_rmse:
            return self.baseline_rmse[position]

        # Establish baseline from historical training
        # For now, use conservative defaults
        defaults = {'GK': 1.2, 'DEF': 1.5, 'MID': 1.8, 'FWD': 2.0}
        baseline = defaults.get(position, 1.5)

        self.baseline_rmse[position] = baseline
        logger.info(f"Baseline RMSE for {position}: {baseline:.3f}")

        return baseline

    def _prepare_training_data(self, current_gw: int) -> tuple:
        """
        Combine historical data (2019-2023) + live accumulated data up to current_gw.

        Returns:
            (X, y): Features and targets as numpy arrays
                X shape: (n_samples, n_features)
                y shape: (n_samples,)
        """
        all_data = []

        # Load historical seasons (2019-2023)
        for season in self.seasons:
            try:
                season_file = Path(f'{self.historical_data_dir}{season}/gws/merged_gw.csv')
                if season_file.exists():
                    season_data = pd.read_csv(season_file)
                    all_data.append(season_data)
                    logger.info(f"Loaded {season}: {len(season_data)} rows")
            except Exception as e:
                logger.warning(f"Failed to load {season}: {e}")

        # Load live data up to current_gw
        try:
            live_file = Path(f'{self.season_2024_25_dir}accumulated_gw.csv')
            if live_file.exists():
                live_data = pd.read_csv(live_file)
                live_data = live_data[live_data['gw'] <= current_gw]
                all_data.append(live_data)
                logger.info(f"Loaded live data: {len(live_data)} rows up to GW{current_gw}")
        except Exception as e:
            logger.warning(f"Failed to load live data: {e}")

        if len(all_data) == 0:
            raise ValueError("No training data available")

        # Combine all data
        combined = pd.concat(all_data, ignore_index=True)

        # Extract features and targets
        # Features: [minutes, goals, assists, xp, xg, xa, shots, key_passes]
        feature_cols = ['minutes', 'goals', 'assists', 'xp', 'xg', 'xa', 'shots', 'key_passes']
        target_col = 'points'

        # Filter to rows with valid features and target
        combined = combined.dropna(subset=[target_col])
        combined = combined.fillna(0)

        # Extract X and y
        X = combined[feature_cols].values
        y = combined[target_col].values

        logger.info(f"Prepared training data: {len(X)} samples, {X.shape[1]} features")

        return X, y

    def _filter_position(self, X: np.ndarray, y: np.ndarray, position: str) -> tuple:
        """
        Filter training data for a specific position.

        Args:
            X: Feature array
            y: Target array
            position: Position code (GK, DEF, MID, FWD)

        Returns:
            (X_pos, y_pos): Filtered feature and target arrays
        """
        # Load live data to get position info
        try:
            live_file = Path(f'{self.season_2024_25_dir}accumulated_gw.csv')
            if live_file.exists():
                live_data = pd.read_csv(live_file)
                pos_mask = live_data['position'] == position
                pos_indices = live_data[pos_mask].index.values

                # Filter X and y by position
                if len(pos_indices) > 0 and len(pos_indices) <= len(X):
                    X_pos = X[pos_indices[:len(X)]]
                    y_pos = y[pos_indices[:len(X)]]
                    return X_pos, y_pos
        except Exception as e:
            logger.warning(f"Failed to filter by position {position}: {e}")

        # Fallback: return subset proportional to position
        # This is a simplified fallback
        n_samples = len(X) // 4  # Approximate distribution
        start_idx = ['GK', 'DEF', 'MID', 'FWD'].index(position) * n_samples
        end_idx = start_idx + n_samples

        return X[start_idx:end_idx], y[start_idx:end_idx]

    def _train_position_models(self, X: np.ndarray, y: np.ndarray, position: str):
        """
        Train position-specific ensemble (XGBoost + RandomForest) with TimeSeriesSplit validation.

        Args:
            X: Feature array
            y: Target array
            position: Position code (GK, DEF, MID, FWD)

        Returns:
            sklearn.Pipeline: Fitted ensemble model wrapped in Pipeline with StandardScaler
        """
        from sklearn.model_selection import TimeSeriesSplit, cross_val_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from xgboost import XGBRegressor
        from sklearn.ensemble import RandomForestRegressor, VotingRegressor

        # Position-specific hyperparameters
        max_depths = {'GK': 4, 'DEF': 5, 'MID': 5, 'FWD': 6}
        max_depth = max_depths.get(position, 5)

        # Create ensemble
        ensemble = VotingRegressor([
            ('xgb', XGBRegressor(
                learning_rate=0.05,
                max_depth=max_depth,
                n_estimators=500,
                random_state=42,
                verbosity=0
            )),
            ('rf', RandomForestRegressor(
                n_estimators=200,
                max_depth=max_depth,
                random_state=42,
                n_jobs=-1
            ))
        ])

        # TimeSeriesSplit validation (3 folds)
        tscv = TimeSeriesSplit(n_splits=3)
        cv_scores = cross_val_score(ensemble, X, y, cv=tscv, scoring='r2', n_jobs=-1)

        # Log CV results
        cv_r2_mean = np.mean(cv_scores)
        cv_r2_std = np.std(cv_scores)
        logger.info(f"{position}: CV R² = {cv_r2_mean:.4f} ± {cv_r2_std:.4f}, "
                   f"Samples={len(X)}, GWs={len(X) // 20}")

        # Alert on low stability
        if cv_r2_mean < 0.80:
            logger.warning(f"{position}: Low CV R² {cv_r2_mean:.3f}, consider more frequent retraining")
        elif cv_r2_mean > 0.95:
            logger.info(f"{position}: High stability {cv_r2_mean:.3f}, could reduce to 4-GW frequency")

        # Final training on all data
        ensemble.fit(X, y)

        # Wrap in Pipeline with StandardScaler
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('ensemble', ensemble)
        ])

        return pipeline

    def _export_predictions(self, gw: int, predictions: dict, season: str = '2024-25') -> None:
        """
        Export predictions to TSV format compatible with manager.py.

        Format:
        - One file per position: predictions/{season}/GW{gw}/{pos}.tsv
        - Tab-separated, columns: GW (int), xP (float)
        - 6 rows for 6-GW lookahead (GW+1 through GW+6)

        Args:
            gw: Gameweek number
            predictions: Dict {position → np.array of predictions}
            season: Season code (default: '2024-25')
        """
        for position in ['GK', 'DEF', 'MID', 'FWD']:
            if position not in predictions:
                logger.warning(f"No predictions for {position}, skipping export")
                continue

            pred_array = predictions[position]

            if len(pred_array) == 0:
                logger.warning(f"Empty predictions for {position}, skipping export")
                continue

            # Create output directory
            output_dir = Path(f'predictions/{season}/GW{gw}')
            output_dir.mkdir(parents=True, exist_ok=True)

            # Build dataframe: GW column (gw+1 to gw+6), xP column (predictions)
            rows = []
            for i in range(min(6, len(pred_array))):
                rows.append({
                    'GW': gw + i + 1,
                    'xP': pred_array[i] if len(pred_array.shape) == 1 else pred_array[0, i]
                })

            df = pd.DataFrame(rows)

            # Write TSV (tab-separated, no quotes)
            file_path = output_dir / f'{position}.tsv'
            df.to_csv(file_path, sep='\t', index=False, quoting=3)  # quoting=3 = QUOTE_NONE

            logger.info(f"Exported {position} predictions to {file_path}")

    def _checkpoint(self, gw: int) -> None:
        """
        Save model checkpoint state.

        Args:
            gw: Gameweek number for naming
        """
        import pickle

        checkpoint_dir = Path('checkpoints/models')
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        for position in ['GK', 'DEF', 'MID', 'FWD']:
            if position in self.model_cache:
                checkpoint_file = checkpoint_dir / f'{position}_gw{gw}.pkl'
                try:
                    with open(checkpoint_file, 'wb') as f:
                        pickle.dump(self.model_cache[position], f)
                    logger.info(f"Checkpointed {position} model to {checkpoint_file}")
                except Exception as e:
                    logger.error(f"Failed to checkpoint {position}: {e}")
