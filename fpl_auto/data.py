import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import datetime
import requests
import json

# Module-level cache: one FplData instance per (data_location, season).
# Shared across all team instances within a season run so caches accumulate.
_instance_cache: dict = {}


def get_fpl_data(data_location: str, season: str) -> 'FplData':
    key = (data_location, season)
    if key not in _instance_cache:
        _instance_cache[key] = FplData(data_location, season)
    return _instance_cache[key]


class FplData:
    def __init__(self, data_location, season):
        self.data_location = f'{data_location}'
        self.season = season
        self.prev_season = f'{int(season[:4])-1}-{int(season[5:])-1}'
        self.player_list = self.get_player_list(season)
        self.team_list = self.get_team_list(season)
        self.team_to_id = self.team_list.reset_index().set_index('name').to_dict()['id']
        self.id_to_name = self.id_to_name_dict()
        self._gw_cache: dict = {}           # (season, week_num) -> DataFrame
        self._fixtures_cache: dict = {}     # season -> DataFrame (full fixtures.csv)
        self._prediction_cache: dict = {}   # (gw, pos) -> DataFrame
        self._recent_gw: int = None         # cached to avoid repeated HTTP requests

    def get_player_list(self, season):
        player_list = pd.read_csv(f'{self.data_location}/{season}/cleaned_players.csv')
        player_list['name'] = player_list['first_name'] + ' ' + player_list['second_name']
        player_list = player_list[['name', 'element_type']].set_index('name')
        player_list = player_list.rename(columns={'element_type': 'position'})
        return player_list.to_dict(orient='dict')['position']

    def get_team_list(self, season):
        team_list = pd.read_csv(f'{self.data_location}/{season}/teams.csv')
        team_list = team_list[['name', 'id', 'strength_attack_home', 'strength_attack_away', 'strength_defence_home', 'strength_defence_away']]
        return team_list.set_index('name')

    def get_predictions(self, gw: int, pos: str) -> pd.DataFrame:
        """
        Retrieve pre-trained xP predictions for a gameweek and position.

        Temporal rule: Predictions must be pre-trained on data strictly before the deadline.
        During GW(N) decisions, only read predictions for GW(N) (generated overnight).
        Never read predictions for GW(N+1) or later.

        Args:
            gw: Gameweek (typically matches current decision gameweek)
            pos: Position code ('GK', 'DEF', 'MID', 'FWD')

        Returns:
            DataFrame with columns Name, xP (expected points)
        """
        key = (gw, pos)
        if key not in self._prediction_cache:
            self._prediction_cache[key] = pd.read_csv(
                f'predictions/{self.season}/GW{gw}/{pos}.tsv', sep='\t'
            )
        return self._prediction_cache[key]

    def get_gw_data(self, season, week_num):
        """
        Read gameweek stats (form, price, minutes, etc).

        Temporal rule: During GW(N) decisions, only access GW(1) through GW(N-1).
        Future integration: TemporalGate will enforce this boundary.

        Args:
            season: Season code (e.g. '2023-24')
            week_num: Gameweek number (1-38)

        Returns:
            DataFrame indexed by player name with columns: position, team, total_points, etc
        """
        cache_key = (season, week_num)
        if cache_key in self._gw_cache:
            return self._gw_cache[cache_key]

        _cols = ['name', 'position', 'team', 'assists', 'bps', 'clean_sheets', 'creativity',
                 'goals_conceded', 'goals_scored', 'ict_index', 'influence', 'minutes',
                 'own_goals', 'penalties_missed', 'penalties_saved', 'red_cards', 'saves',
                 'threat', 'total_points', 'yellow_cards', 'selected', 'was_home', 'value']
        try:
            if week_num < 1:
                gw_data = pd.read_csv(f'{self.data_location}/{self.prev_season}/gws/gw{38 + week_num}.csv')
            else:
                gw_data = pd.read_csv(f'{self.data_location}/{season}/gws/gw{week_num}.csv')
        except FileNotFoundError:
            empty = pd.DataFrame(columns=_cols).set_index('name')
            self._gw_cache[cache_key] = empty
            return empty
        gw_data = gw_data[_cols]
        gw_data = gw_data.set_index('name')
        self._gw_cache[cache_key] = gw_data
        return gw_data

    def get_pos_data(self, season, week_num, position):
        gw_data = self.get_gw_data(season, week_num)
        gw_data = gw_data[gw_data['position'] == position]
        gw_data = gw_data.join(self.team_list, on='team')
        gw_data = gw_data.dropna()
        lookback = 3
        recent_minutes = np.zeros(len(gw_data), dtype=float)
        for offset in range(1, lookback + 1):
            past = self.get_gw_data(season, week_num - offset)
            if past.empty:
                continue
            past_mins = (
                pd.to_numeric(past['minutes'], errors='coerce')
                .fillna(0).groupby(level=0).sum().to_dict()
            )
            recent_minutes += np.array([past_mins.get(n, 0.0) for n in gw_data.index])
        gw_data['recent_minutes_ratio'] = np.clip(recent_minutes / (lookback * 90), 0.0, 1.0)
        gw_data = gw_data.drop(['position', 'team', 'ict_index'], axis=1)
        return gw_data

    def get_all_pos_data(self, season, week_num):
        return (
            self.get_pos_data(season, week_num, 'GK'),
            self.get_pos_data(season, week_num, 'DEF'),
            self.get_pos_data(season, week_num, 'MID'),
            self.get_pos_data(season, week_num, 'FWD'),
        )

    def avg_player_data(self, season, from_gw, to_gw):
        """Aggregate per-player stats across a GW range, averaged by player name. Includes feature engineering."""
        if self.season == '2022-23' and from_gw == 7:
            from_gw = 8

        gk_data = self.get_pos_data(season, from_gw, 'GK')
        def_data = self.get_pos_data(season, from_gw, 'DEF')
        mid_data = self.get_pos_data(season, from_gw, 'MID')
        fwd_data = self.get_pos_data(season, from_gw, 'FWD')

        for i in range(from_gw + 1, to_gw + 1):
            if self.season == '2022-23' and i == 7:
                continue
            gk_data = pd.concat((gk_data, self.get_pos_data(season, i, 'GK')))
            def_data = pd.concat((def_data, self.get_pos_data(season, i, 'DEF')))
            mid_data = pd.concat((mid_data, self.get_pos_data(season, i, 'MID')))
            fwd_data = pd.concat((fwd_data, self.get_pos_data(season, i, 'FWD')))

        # === NEW: Apply feature engineering per position before averaging ===
        gk_data = self.engineer_features_on_gw_data(gk_data, season, to_gw, 'GK')
        def_data = self.engineer_features_on_gw_data(def_data, season, to_gw, 'DEF')
        mid_data = self.engineer_features_on_gw_data(mid_data, season, to_gw, 'MID')
        fwd_data = self.engineer_features_on_gw_data(fwd_data, season, to_gw, 'FWD')

        gk_data = gk_data.groupby('name').mean().reset_index().set_index('name')
        def_data = def_data.groupby('name').mean().reset_index().set_index('name')
        mid_data = mid_data.groupby('name').mean().reset_index().set_index('name')
        fwd_data = fwd_data.groupby('name').mean().reset_index().set_index('name')

        for gw_offset in (0, 1):
            non_players = self.non_players(season, from_gw + gw_offset).index
            for df in (gk_data, def_data, mid_data, fwd_data):
                df.loc[df.index.isin(non_players), :] = 0

        return gk_data, def_data, mid_data, fwd_data

    def prune_features(self, features):
        return features.drop(['total_points', 'id', 'bps', 'was_home'], axis=1)

    def prune_all_features(self, features):
        gk_features, def_features, mid_features, fwd_features = features
        return (
            self.prune_features(gk_features),
            self.prune_features(def_features),
            self.prune_features(mid_features),
            self.prune_features(fwd_features),
        )

    def extract_labels(self, features):
        return features['total_points']

    def extract_all_labels(self, features):
        return tuple(self.extract_labels(f) for f in features)

    def get_training_data(self, season, week_num):
        features = self.get_all_pos_data(season, week_num)

        # === NEW: Apply feature engineering to training data ===
        features_engineered = []
        for j, pos in enumerate(['GK', 'DEF', 'MID', 'FWD']):
            engineered = self.engineer_features_on_gw_data(features[j], season, week_num, pos)
            features_engineered.append(engineered)
        features = tuple(features_engineered)

        feature_labels = self.extract_all_labels(features)
        features = self.prune_all_features(features)
        return tuple(zip(features, feature_labels))

    def get_training_data_all(self, season, from_gw, to_gw):
        # Temporal rule: to_gw is INCLUSIVE. When called from model.py with (i - 19, i),
        # this trains on GW(i) actual points. FIX: call with (i - 20, i - 1) to exclude GW(i).
        for i in range(from_gw, to_gw):
            if i == from_gw:
                if i < 1:
                    training_gk, training_def, training_mid, training_fwd = self.get_training_data(self.prev_season, 37 + i)
                else:
                    training_gk, training_def, training_mid, training_fwd = self.get_training_data(season, i)
            else:
                if i < 1:
                    training_gk_new, training_def_new, training_mid_new, training_fwd_new = self.get_training_data(self.prev_season, 38 + i)
                else:
                    training_gk_new, training_def_new, training_mid_new, training_fwd_new = self.get_training_data(season, i)
                training_gk = (pd.concat((training_gk[0], training_gk_new[0])), pd.concat((training_gk[1], training_gk_new[1])))
                training_def = (pd.concat((training_def[0], training_def_new[0])), pd.concat((training_def[1], training_def_new[1])))
                training_mid = (pd.concat((training_mid[0], training_mid_new[0])), pd.concat((training_mid[1], training_mid_new[1])))
                training_fwd = (pd.concat((training_fwd[0], training_fwd_new[0])), pd.concat((training_fwd[1], training_fwd_new[1])))

        gk_features_train, gk_features_test, gk_labels_train, gk_labels_test = train_test_split(training_gk[0], training_gk[1], test_size=0.2, random_state=42)
        def_features_train, def_features_test, def_labels_train, def_labels_test = train_test_split(training_def[0], training_def[1], test_size=0.2, random_state=42)
        mid_features_train, mid_features_test, mid_labels_train, mid_labels_test = train_test_split(training_mid[0], training_mid[1], test_size=0.2, random_state=42)
        fwd_features_train, fwd_features_test, fwd_labels_train, fwd_labels_test = train_test_split(training_fwd[0], training_fwd[1], test_size=0.2, random_state=42)

        training_data = [
            (gk_features_train, gk_labels_train),
            (def_features_train, def_labels_train),
            (mid_features_train, mid_labels_train),
            (fwd_features_train, fwd_labels_train),
        ]
        test_data = [
            (gk_features_test, gk_labels_test),
            (def_features_test, def_labels_test),
            (mid_features_test, mid_labels_test),
            (fwd_features_test, fwd_labels_test),
        ]
        return training_data, test_data

    def get_player_predictions(self, season, from_gw, to_gw, models):
        features = self.avg_player_data(season, from_gw, to_gw - 1)
        player_names = [f.index.values for f in features]
        pruned_features = self.prune_all_features(features)
        predictions = [np.round(m.predict(f), 2) for m, f in zip(models, pruned_features)]
        return player_names, predictions

    def get_price(self, week_num, player, gw_data):
        prices = gw_data[['value']].to_dict()['value']
        if player in prices:
            return prices[player] / 10
        return None

    def actual_points_dict(self, season, week_num):
        """
        Extract player->points mapping for a completed gameweek.

        Temporal rule: Only call for PAST gameweeks. During GW(N) decisions,
        should only read GW(N-1) or earlier. Never read GW(N) during GW(N) decisions.

        Args:
            season: Season code
            week_num: Gameweek number (must be <= current_gameweek - 1)

        Returns:
            Dict mapping player name to actual points scored
        """
        gw_data = self.get_gw_data(season, week_num)
        return gw_data[['total_points']].to_dict()['total_points']

    def position_dict(self, week_num):
        return self.get_gw_data(self.season, week_num).to_dict()['position']

    def get_players_who_didnt_play(self, gameweek):
        gw_data = self.get_gw_data(self.season, gameweek)
        return gw_data[gw_data['minutes'] == 0].to_dict()['minutes']

    def non_players(self, season, gameweek):
        recent_gw = self.get_recent_gw()
        if recent_gw is None or gameweek < recent_gw:
            gw_data = self.get_gw_data(season, gameweek)
            return gw_data[gw_data['minutes'] == 0]
        return pd.DataFrame()

    def post_model_weightings(self, clean_predictions, week_num, next_num_gws):
        """
        Apply post-model weightings to the predictions.

        Vectorised: pre-computes fixture adjustments for all 20 teams once, then
        applies them per player via numpy broadcast instead of per-player pandas filtering.

        Returns list of DataFrames [Name, xP] where xP is a numpy array of length next_num_gws.
        """
        gw_data = self.get_gw_data(self.season, week_num)
        future_fx = self.get_future_fixtures(self.season, week_num)  # already sorted by event

        diff_map = {1: 0.2, 2: 0.05, 3: 0.0, 4: -0.05, 5: -0.2}

        # Pre-compute adjustment vector for each of the 20 teams (not per player)
        team_adjs: dict = {}
        for team_id in set(self.team_to_id.values()):
            mask = (future_fx['team_h'] == team_id) | (future_fx['team_a'] == team_id)
            fixes = future_fx[mask].head(next_num_gws)
            adjs = np.zeros(next_num_gws)
            for i, fx in enumerate(fixes.itertuples()):
                is_home = fx.team_h == team_id
                diff = fx.team_h_difficulty if is_home else fx.team_a_difficulty
                adjs[i] = (0.1 if is_home else -0.1) + diff_map.get(diff, 0.0)
            team_adjs[team_id] = adjs

        player_team = gw_data['team'].to_dict()

        overall_predictions = []
        for pos_df in clean_predictions:
            df = pos_df.reset_index()[['Name', 'xP']].copy()
            names = df['Name'].values
            xp_vals = df['xP'].values.astype(float)

            # Build (n_players × next_num_gws) adjustment matrix
            adj_matrix = np.zeros((len(names), next_num_gws))
            no_team = np.zeros(len(names), dtype=bool)
            for j, name in enumerate(names):
                tid = self.team_to_id.get(player_team.get(name))
                if tid is not None and tid in team_adjs:
                    adj_matrix[j] = team_adjs[tid]
                else:
                    no_team[j] = True

            # Vectorised: xP_matrix[player, gw] = adjusted xP for each future GW
            xp_matrix = xp_vals[:, np.newaxis] + adj_matrix
            xp_matrix[no_team] = 0.0
            xp_matrix = np.round(xp_matrix, 3)

            result = pd.DataFrame({'Name': names, 'xP': list(xp_matrix)})
            overall_predictions.append(result)

        return overall_predictions

    def post_model_weightings_for_next_gw(self, clean_predictions, week_num):
        """Scalar (non-vectorised) single-GW variant used by model.py when saving TSVs."""
        diff_map = {1: 0.2, 2: 0.05, 3: 0.0, 4: -0.05, 5: -0.2}
        gw_data = self.get_gw_data(self.season, week_num)
        overall_predictions = []
        for pos in clean_predictions:
            pos = pos.reset_index()
            post_predictions = []
            for i in range(len(pos)):
                name = pos.loc[i, 'Name']
                p = pos.loc[i, 'xP']

                try:
                    team_name = self.get_player_team(name, week_num, gw_data)
                    team_id = self.team_to_id[team_name]
                    fixture_list = self.get_future_fixtures_for_player(name, week_num, gw_data)[0:1]
                except (KeyError, TypeError):
                    post_predictions.append([name, 0])
                    continue

                fixture = fixture_list.iloc[0]
                home_fixture = fixture['team_h'] == team_id
                difficulty = fixture['team_h_difficulty'] if home_fixture else fixture['team_a_difficulty']

                home_away_p = p * (0.1 if home_fixture else -0.1)
                diff_p = p * diff_map.get(difficulty, 0.0)

                p = round(p + home_away_p + diff_p, 3)
                post_predictions.append([name, p])

            overall_predictions.append(pd.DataFrame(post_predictions, columns=['Name', 'xP']))

        return overall_predictions

    def id_to_name_dict(self):
        players = pd.read_csv(f'{self.data_location}/{self.season}/player_idlist.csv')
        players['name'] = players['first_name'] + ' ' + players['second_name']
        return players.set_index('id')['name'].to_dict()

    def get_recent_gw(self):
        if self._recent_gw is not None:
            return self._recent_gw

        data = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
        data = json.loads(data.content)

        now = datetime.datetime.utcnow()
        for gameweek in data['events']:
            next_deadline_date = datetime.datetime.strptime(gameweek['deadline_time'], '%Y-%m-%dT%H:%M:%SZ')
            if next_deadline_date > now:
                self._recent_gw = gameweek['id'] - 1
                return self._recent_gw

    def get_avg_score_list(self):
        fpl_api = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
        fpl_api = json.loads(fpl_api.content)
        avg_scores = np.zeros(len(fpl_api['events']))
        for i, event in enumerate(fpl_api['events']):
            avg_scores[i] = event['average_entry_score']
        return avg_scores

    def get_future_fixtures(self, season, week_num):
        if season not in self._fixtures_cache:
            df = pd.read_csv(f'{self.data_location}/{season}/fixtures.csv')
            self._fixtures_cache[season] = df.sort_values('event').reset_index(drop=True)
        future_fixtures = self._fixtures_cache[season]
        return future_fixtures[future_fixtures['event'] > week_num]

    def get_future_fixtures_for_team(self, team_name, week_num):
        team_id = self.team_to_id[team_name]
        upcoming_fixtures = self.get_future_fixtures(self.season, week_num)
        team_fixtures = upcoming_fixtures[(upcoming_fixtures['team_a'] == team_id) | (upcoming_fixtures['team_h'] == team_id)]
        return team_fixtures[['event', 'team_h', 'team_a', 'team_h_difficulty', 'team_a_difficulty']]

    def get_future_fixtures_for_player(self, player_name, week_num, gw_data):
        team_name = self.get_player_team(player_name, week_num, gw_data)
        return self.get_future_fixtures_for_team(team_name, week_num)

    def get_player_team(self, player_name, week_num, gw_data):
        try:
            return gw_data.loc[player_name]['team']
        except KeyError:
            return None

    def api_to_json(self):
        res = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
        return json.loads(res.content)

    def get_injuries(self):
        fpl_api = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/')
        fpl_api = json.loads(fpl_api.content)
        with open('fpl_auto/injuries.json', 'w') as f:
            json.dump(fpl_api, f)

    def discount_next_n_gws(self, predictions, gw, n, discount_factor=0.8, sum=True):
        """
        Discount the next n gameweeks and return scalar (mean) or array xP per player.

        Fully vectorised: uses numpy stack + broadcast instead of per-player Python loops.
        """
        if gw + n > 38:
            n = 38 - gw
        if n == 0 or gw >= 36:
            return predictions

        n_next_weeks = self.post_model_weightings(predictions, gw, n)
        discount_weights = np.array([discount_factor ** i for i in range(n)])

        result = []
        for pos_df in n_next_weeks:
            xp_arrays = np.stack(pos_df['xP'].values)   # (n_players, n)
            discounted = xp_arrays * discount_weights     # (n_players, n) broadcast

            df = pos_df[['Name']].copy()
            if sum:
                df['xP'] = np.round(np.sum(discounted, axis=1), 2)
            else:
                df['xP'] = list(discounted)
            result.append(df)

        return result

    def engineer_features_on_gw_data(self, gw_data, season, week_num, position):
        """
        Add engineered features to gameweek data: rolling averages, efficiency ratios,
        and position-specific metrics.

        Temporal rule: Rolling stats use only past data relative to prediction GW.
        No future data access. For GW 1-5, rolling_10gw uses actual available history.

        Args:
            gw_data: DataFrame with position-filtered data (from get_pos_data)
            season: Season code
            week_num: Current gameweek number (1-38)
            position: Position code ('GK', 'DEF', 'MID', 'FWD')

        Returns:
            DataFrame with original columns + engineered features (35-40 columns total)
        """
        gw_data = gw_data.copy()

        # === ROLLING AVERAGES: RESTRICTED (Plan 04-03 Optimization) ===
        # Plan 04-02 discovered high multicollinearity in 5GW rolling features:
        # - influence_rolling_5gw: VIF 7.2 (duplicates raw influence)
        # - minutes_rolling_5gw: VIF 14.21 (duplicates raw minutes)
        # These caused 65-75% performance degradation.
        #
        # Plan 04-03 strategy: Disable 5GW rolling features entirely (except creativity/threat for MID/FWD).
        # Only compute 10GW rolling (longer-term trend, less correlated with current GW).
        # New advanced features (seasonal bucket, form momentum, etc) replace the lost signals.

        # Only compute 10GW rolling for less-problematic columns
        rolling_windows = [10]  # REMOVED 5 from list
        # REMOVED: 'minutes', 'influence', 'goals_scored' — these had high multicollinearity
        # KEPT: 'creativity', 'threat' — these are less directly duplicative
        rolling_columns = ['creativity', 'threat']

        for window in rolling_windows:
            for col in rolling_columns:
                feature_name = f'{col}_rolling_{window}gw'
                rolling_values = np.zeros(len(gw_data), dtype=float)
                actual_window_count = 0

                # Temporal boundary: never access future GWs
                for offset in range(1, window + 1):
                    if week_num - offset < 1:
                        # No past data available
                        continue
                    past_gw = self.get_gw_data(season, week_num - offset)
                    if past_gw.empty:
                        continue

                    # Get column values as numeric, fill NaN with 0
                    past_vals = (
                        pd.to_numeric(past_gw[col], errors='coerce')
                        .fillna(0).groupby(level=0).sum().to_dict()
                    )
                    rolling_values += np.array([past_vals.get(n, 0.0) for n in gw_data.index])
                    actual_window_count += 1

                # Average over the actual number of gameweeks processed
                if actual_window_count > 0:
                    gw_data[feature_name] = rolling_values / actual_window_count
                else:
                    gw_data[feature_name] = 0.0

                # Fill NaN and Inf with 0
                gw_data[feature_name] = gw_data[feature_name].fillna(0.0).replace([np.inf, -np.inf], 0.0)

        # Efficiency ratios (always computed if minutes > 0)
        gw_data['efficiency_goals_per_90'] = (
            (pd.to_numeric(gw_data['goals_scored'], errors='coerce').fillna(0) + 1) /
            (pd.to_numeric(gw_data['minutes'], errors='coerce').fillna(0) / 90.0 + 1)
        )
        gw_data['efficiency_assists_per_90'] = (
            (pd.to_numeric(gw_data['assists'], errors='coerce').fillna(0) + 1) /
            (pd.to_numeric(gw_data['minutes'], errors='coerce').fillna(0) / 90.0 + 1)
        )
        gw_data['efficiency_creativity_per_min'] = (
            pd.to_numeric(gw_data['creativity'], errors='coerce').fillna(0) /
            (pd.to_numeric(gw_data['minutes'], errors='coerce').fillna(0) + 1)
        )
        gw_data['efficiency_threat_per_min'] = (
            pd.to_numeric(gw_data['threat'], errors='coerce').fillna(0) /
            (pd.to_numeric(gw_data['minutes'], errors='coerce').fillna(0) + 1)
        )

        # Fill NaN and Inf with 0
        for col in ['efficiency_goals_per_90', 'efficiency_assists_per_90',
                    'efficiency_creativity_per_min', 'efficiency_threat_per_min']:
            gw_data[col] = gw_data[col].fillna(0.0).replace([np.inf, -np.inf], 0.0)

        # === ADVANCED FEATURES (Plan 04-03): Seasonal, momentum, ownership, interactions, lag ===

        # Feature 1: Seasonal bucket (encode season phase: early/mid/late/final)
        if week_num <= 10:
            gw_data['gw_bucket_early'] = 1.0
            gw_data['gw_bucket_mid'] = 0.0
            gw_data['gw_bucket_late'] = 0.0
            gw_data['gw_bucket_final'] = 0.0
        elif week_num <= 20:
            gw_data['gw_bucket_early'] = 0.0
            gw_data['gw_bucket_mid'] = 1.0
            gw_data['gw_bucket_late'] = 0.0
            gw_data['gw_bucket_final'] = 0.0
        elif week_num <= 30:
            gw_data['gw_bucket_early'] = 0.0
            gw_data['gw_bucket_mid'] = 0.0
            gw_data['gw_bucket_late'] = 1.0
            gw_data['gw_bucket_final'] = 0.0
        else:  # GW 31-38
            gw_data['gw_bucket_early'] = 0.0
            gw_data['gw_bucket_mid'] = 0.0
            gw_data['gw_bucket_late'] = 0.0
            gw_data['gw_bucket_final'] = 1.0

        # Feature 2: Form momentum (trend: recent form vs longer-term)
        # Since influence_rolling features are disabled to avoid multicollinearity,
        # compute form momentum directly from past influence values
        influence_3gw_values = np.zeros(len(gw_data), dtype=float)
        count_3gw = 0
        influence_10gw_values = np.zeros(len(gw_data), dtype=float)
        count_10gw = 0

        for offset in range(1, 11):  # up to 10 GWs
            if week_num - offset < 1:
                continue
            past_gw = self.get_gw_data(season, week_num - offset)
            if past_gw.empty:
                continue
            past_vals = (
                pd.to_numeric(past_gw['influence'], errors='coerce')
                .fillna(0).groupby(level=0).sum().to_dict()
            )
            past_vals_array = np.array([past_vals.get(n, 0.0) for n in gw_data.index])

            # 3GW average (most recent)
            if offset <= 3:
                influence_3gw_values += past_vals_array
                count_3gw += 1

            # 10GW average (longer-term)
            influence_10gw_values += past_vals_array
            count_10gw += 1

        # Form momentum = recent form (3GW avg) - longer term form (10GW avg)
        influence_3gw = influence_3gw_values / count_3gw if count_3gw > 0 else np.zeros(len(gw_data))
        influence_10gw = influence_10gw_values / count_10gw if count_10gw > 0 else np.zeros(len(gw_data))
        gw_data['form_momentum'] = influence_3gw - influence_10gw
        gw_data['form_momentum'] = gw_data['form_momentum'].fillna(0.0).replace([np.inf, -np.inf], 0.0)

        # Feature 3: Ownership signal (selected% as a proxy for popularity/differential)
        # High selection = popular/safe; Low selection = differential/risky
        gw_data['ownership_signal'] = pd.to_numeric(gw_data['selected'], errors='coerce').fillna(0)
        # Normalize to [0, 1] range (FPL selected is 0-100)
        gw_data['ownership_signal'] = np.clip(gw_data['ownership_signal'] / 100.0, 0.0, 1.0)

        # Feature 4: Injury risk flag (minutes drop indicator)
        # If recent minutes < 50% of longer-term average, flag as potential injury/benching
        minutes_5gw = gw_data['minutes_rolling_5gw'].values if 'minutes_rolling_5gw' in gw_data.columns else np.zeros(len(gw_data))
        minutes_10gw = gw_data['minutes_rolling_10gw'].values if 'minutes_rolling_10gw' in gw_data.columns else np.zeros(len(gw_data))

        # Injury risk: 1 if recent minutes < 50% of longer-term, else 0
        gw_data['injury_risk_flag'] = np.where(
            (minutes_10gw > 0) & (minutes_5gw < 0.5 * minutes_10gw),
            1.0,
            0.0
        )

        # Feature 5: Interactions - strength_attack × form (team strength combined with player form)
        # For FWD priority: strong attacking teams with good form players should score more
        if 'strength_attack_home' in gw_data.columns:
            strength_attack = pd.to_numeric(gw_data['strength_attack_home'], errors='coerce').fillna(0)
            influence_current = pd.to_numeric(gw_data['influence'], errors='coerce').fillna(0)
            # Normalize strength (typically 1000-1500 scale in FPL) and influence (0-100 scale)
            strength_attack_norm = np.clip(strength_attack / 1500.0, 0.0, 1.0)
            influence_norm = np.clip(influence_current / 100.0, 0.0, 1.0)
            gw_data['strength_form_interaction'] = strength_attack_norm * influence_norm
        else:
            # If team strength data not available (e.g., in tests), set to 0
            gw_data['strength_form_interaction'] = 0.0

        gw_data['strength_form_interaction'] = gw_data['strength_form_interaction'].fillna(0.0).replace([np.inf, -np.inf], 0.0)

        # Feature 6: Transfers signal (popularity trend, if available)
        # High transfers_in signals increasing popularity
        if 'transfers_in' in gw_data.columns:
            transfers_in = pd.to_numeric(gw_data['transfers_in'], errors='coerce').fillna(0)
            gw_data['transfers_in_signal'] = np.clip(transfers_in / 50000.0, 0.0, 1.0)
        else:
            gw_data['transfers_in_signal'] = 0.0

        # === END ADVANCED FEATURES ===

        # Position-specific features
        if position == 'GK':
            gw_data['saves_per_90'] = (
                pd.to_numeric(gw_data['saves'], errors='coerce').fillna(0) /
                (pd.to_numeric(gw_data['minutes'], errors='coerce').fillna(0) / 90.0 + 1)
            )
            gw_data['save_percentage_safe'] = (
                pd.to_numeric(gw_data['saves'], errors='coerce').fillna(0) /
                (pd.to_numeric(gw_data['saves'], errors='coerce').fillna(0) +
                 pd.to_numeric(gw_data['goals_conceded'], errors='coerce').fillna(0) + 1)
            )
            # Fill NaN and Inf with 0
            gw_data['saves_per_90'] = gw_data['saves_per_90'].fillna(0.0).replace([np.inf, -np.inf], 0.0)
            gw_data['save_percentage_safe'] = gw_data['save_percentage_safe'].fillna(0.0).replace([np.inf, -np.inf], 0.0)

        elif position == 'DEF':
            gw_data['clean_sheets_per_90'] = (
                pd.to_numeric(gw_data['clean_sheets'], errors='coerce').fillna(0) /
                (pd.to_numeric(gw_data['minutes'], errors='coerce').fillna(0) / 90.0 + 1)
            )
            # Defensive actions proxy: use recent clean sheets ratio as proxy
            gw_data['defensive_actions_per_90'] = (
                pd.to_numeric(gw_data['clean_sheets'], errors='coerce').fillna(0) /
                (pd.to_numeric(gw_data['minutes'], errors='coerce').fillna(0) / 90.0 + 1)
            )
            # Fill NaN and Inf with 0
            gw_data['clean_sheets_per_90'] = gw_data['clean_sheets_per_90'].fillna(0.0).replace([np.inf, -np.inf], 0.0)
            gw_data['defensive_actions_per_90'] = gw_data['defensive_actions_per_90'].fillna(0.0).replace([np.inf, -np.inf], 0.0)

        elif position == 'MID':
            gw_data['key_passes_proxy'] = (
                pd.to_numeric(gw_data['assists'], errors='coerce').fillna(0) * 2 +
                pd.to_numeric(gw_data['creativity'], errors='coerce').fillna(0) * 0.5
            )
            gw_data['key_passes_proxy'] = gw_data['key_passes_proxy'].fillna(0.0).replace([np.inf, -np.inf], 0.0)

        elif position == 'FWD':
            gw_data['shots_on_target_proxy'] = (
                pd.to_numeric(gw_data['goals_scored'], errors='coerce').fillna(0) * 2 +
                pd.to_numeric(gw_data['threat'], errors='coerce').fillna(0) * 0.3
            )
            gw_data['shots_on_target_proxy'] = gw_data['shots_on_target_proxy'].fillna(0.0).replace([np.inf, -np.inf], 0.0)

        return gw_data
