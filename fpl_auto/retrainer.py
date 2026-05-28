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

        # Attempt Understat merge
        try:
            understat_df = self._fetch_understat_data(gw)
            if understat_df is not None and len(understat_df) > 0:
                # Merge on player_id (FPL primary, Understat left-join)
                fpl_df = fpl_df.merge(
                    understat_df[['player_id', 'xg', 'xa', 'shots', 'key_passes']],
                    on='player_id',
                    how='left'
                )
                logger.info(f"GW{gw}: Merged {len(understat_df)} Understat records")
            else:
                logger.warning(f"GW{gw}: Understat unavailable, using FPL data only")
                fpl_df['xg'] = np.nan
                fpl_df['xa'] = np.nan
                fpl_df['shots'] = np.nan
                fpl_df['key_passes'] = np.nan
        except Exception as e:
            logger.warning(f"GW{gw}: Understat merge failed ({e}), using FPL data only")
            fpl_df['xg'] = np.nan
            fpl_df['xa'] = np.nan
            fpl_df['shots'] = np.nan
            fpl_df['key_passes'] = np.nan

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
