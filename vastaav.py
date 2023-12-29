import numpy as np
import pandas as pd
import requests
import json
from pprint import pprint
import json
import sklearn
from sklearn import linear_model, ensemble, model_selection
from sklearn.model_selection import train_test_split
import xgboost as xgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import GradientBoostingRegressor

class vastaav_data:
    def __init__(self, data_location, season):
        self.data_location = f'{data_location}'
        self.season = season
        self.prev_season = f'{int(season[:4])-1}-{int(season[5:])-1}'
        self.player_list = self.get_player_list(season).set_index('name').to_dict()
        self.player_id_list = {v: k for k, v in self.player_list['id'].items()}
        self.team_list = self.get_team_list(season)
    
    def get_player_list(self, season):
        player_list = pd.read_csv(f'{self.data_location}/{season}/player_idlist.csv')
        # Merge first_name and second_name columns into one column
        player_list['name'] = player_list['first_name'] + ' ' + player_list['second_name']
        return player_list[['name', 'id']]
    
    def get_team_list(self, season):
        team_list = pd.read_csv(f'{self.data_location}/{season}/teams.csv')
        team_list = team_list[['name', 'strength_overall_home', 'strength_overall_away', 'strength_attack_home', 'strength_attack_away', 'strength_defence_home', 'strength_defence_away']]
        return team_list.set_index('name')
    
    def get_gw_data(self, season, week_num):
        gw_data = pd.read_csv(f'{self.data_location}/{season}/gws/gw{week_num}.csv')
        gw_data = gw_data[['name', 'position', 'team', 'assists', 'bps', 'clean_sheets', 'creativity', 'goals_conceded', 'goals_scored', 'ict_index', 'influence', 'minutes', 'own_goals', 'penalties_missed', 'penalties_saved', 'red_cards', 'saves', 'threat', 'total_points', 'yellow_cards', 'selected', 'was_home']]
        return gw_data.set_index('name')

    def get_pos_data(self, season, week_num, position):
        gw_data = self.get_gw_data(season, week_num)
        gw_data = gw_data[gw_data['position'] == position]
        gw_data = gw_data.drop(['position', 'team', 'ict_index'], axis=1)
        return gw_data
    
    def get_training_data(self, season, week_num):
        gk_features = self.get_pos_data(season, week_num, 'GK')
        def_features = self.get_pos_data(season, week_num, 'DEF')
        mid_features = self.get_pos_data(season, week_num, 'MID')
        fwd_features = self.get_pos_data(season, week_num, 'FWD')

        gk_labels = gk_features['total_points']
        def_labels = def_features['total_points']
        mid_labels = mid_features['total_points']
        fwd_labels = fwd_features['total_points']

        # Drop the remaining columns that are not features
        gk_features = gk_features.drop(['total_points'], axis=1)
        def_features = def_features.drop(['total_points'], axis=1)
        mid_features = mid_features.drop(['total_points'], axis=1)
        fwd_features = fwd_features.drop(['total_points'], axis=1)

        feature_names = list(gk_features.columns)

        # Group features & labels for convenience
        training_gk = (gk_features, gk_labels)
        training_def = (def_features, def_labels)
        training_mid = (mid_features, mid_labels)
        training_fwd = (fwd_features, fwd_labels)

        return training_gk, training_def, training_mid, training_fwd

    def get_training_data_all(self, season, from_gw, to_gw):
        feature_names = []
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
                training_gk = (np.concatenate((training_gk[0], training_gk_new[0])), np.concatenate((training_gk[1], training_gk_new[1])))
                training_def = (np.concatenate((training_def[0], training_def_new[0])), np.concatenate((training_def[1], training_def_new[1])))
                training_mid = (np.concatenate((training_mid[0], training_mid_new[0])), np.concatenate((training_mid[1], training_mid_new[1])))
                training_fwd = (np.concatenate((training_fwd[0], training_fwd_new[0])), np.concatenate((training_fwd[1], training_fwd_new[1])))

        gk_features_train, gk_features_test, gk_labels_train, gk_labels_test = train_test_split(training_gk[0], training_gk[1], test_size=0.2, random_state=42)
        def_features_train, def_features_test, def_labels_train, def_labels_test = train_test_split(training_def[0], training_def[1], test_size=0.2, random_state=42)
        mid_features_train, mid_features_test, mid_labels_train, mid_labels_test = train_test_split(training_mid[0], training_mid[1], test_size=0.2, random_state=42)
        fwd_features_train, fwd_features_test, fwd_labels_train, fwd_labels_test = train_test_split(training_fwd[0], training_fwd[1], test_size=0.2, random_state=42)

        training_gk = (gk_features_train, gk_labels_train)
        training_def = (def_features_train, def_labels_train)
        training_mid = (mid_features_train, mid_labels_train)
        training_fwd = (fwd_features_train, fwd_labels_train)

        test_gk = (gk_features_test, gk_labels_test)
        test_def = (def_features_test, def_labels_test)
        test_mid = (mid_features_test, mid_labels_test)
        test_fwd = (fwd_features_test, fwd_labels_test)

        training_data = [training_gk, training_def, training_mid, training_fwd]
        test_data = [test_gk, test_def, test_mid, test_fwd]

        return training_data, test_data

    def get_model(self, model_type, training_data):
        # Pick a model type
        if model_type == 'linear':
            gk_model = linear_model.LinearRegression()
            def_model = linear_model.LinearRegression()
            mid_model = linear_model.LinearRegression()
            fwd_model = linear_model.LinearRegression()
            
        elif model_type == 'randomforest':
            gk_model = RandomForestRegressor(oob_score = True, n_estimators = 1000, max_features = 5)
            def_model = RandomForestRegressor(oob_score = True, n_estimators = 1000, max_features = 5)
            mid_model = RandomForestRegressor(oob_score = True, n_estimators = 1000, max_features = 5)
            fwd_model = RandomForestRegressor(oob_score = True, n_estimators = 1000, max_features = 5)

        elif model_type == 'xgboost':
            gk_model = xgb.XGBRegressor()
            def_model = xgb.XGBRegressor()
            mid_model = xgb.XGBRegressor()
            fwd_model = xgb.XGBRegressor()

        elif model_type == 'gradientboost':
            loss_function = 'squared_error'
            n_est = 100 # keep at 1000 whilst in development for speed
            l_rate = 0.2
            gk_model = GradientBoostingRegressor(max_features=17, n_estimators=n_est, learning_rate=l_rate, loss=loss_function)
            def_model = GradientBoostingRegressor(max_features=17,n_estimators=n_est, learning_rate=l_rate, loss=loss_function)
            mid_model = GradientBoostingRegressor(max_features=17,n_estimators=n_est, learning_rate=l_rate, loss=loss_function)
            fwd_model = GradientBoostingRegressor(max_features=17,n_estimators=n_est, learning_rate=l_rate, loss=loss_function)

        # Fit training data to model
        gk_model.fit(training_data[0][0], training_data[0][1])
        def_model.fit(training_data[1][0], training_data[1][1])
        mid_model.fit(training_data[2][0], training_data[2][1])
        fwd_model.fit(training_data[3][0], training_data[3][1])

        return gk_model, def_model, mid_model, fwd_model