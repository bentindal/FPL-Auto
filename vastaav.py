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
        self.data_location = f'{data_location}/{season}'
        self.season = season
        self.player_list = self.get_player_list().set_index('name').to_dict()
        self.player_id_list = {v: k for k, v in self.player_list['id'].items()}
        self.team_list = self.get_team_list()
    
    def get_player_list(self):
        player_list = pd.read_csv(f'{self.data_location}/player_idlist.csv')
        # Merge first_name and second_name columns into one column
        player_list['name'] = player_list['first_name'] + ' ' + player_list['second_name']
        return player_list[['name', 'id']]
    
    def get_team_list(self):
        team_list = pd.read_csv(f'{self.data_location}/teams.csv')
        team_list = team_list[['name', 'strength_overall_home', 'strength_overall_away', 'strength_attack_home', 'strength_attack_away', 'strength_defence_home', 'strength_defence_away']]
        return team_list.set_index('name')
    
    def get_gw_data(self, week_num):
        gw_data = pd.read_csv(f'{self.data_location}/gws/gw{week_num}.csv')
        gw_data = gw_data[['name', 'position', 'team', 'assists', 'bps', 'clean_sheets', 'creativity', 'goals_conceded', 'goals_scored', 'ict_index', 'influence', 'minutes', 'own_goals', 'penalties_missed', 'penalties_saved', 'red_cards', 'saves', 'threat', 'total_points', 'yellow_cards', 'selected', 'was_home']]
        return gw_data.set_index('name')

    def get_pos_data(self, week_num, position):
        gw_data = self.get_gw_data(week_num)
        gw_data = gw_data[gw_data['position'] == position]
        gw_data = gw_data.drop(['position', 'team', 'ict_index'], axis=1)
        return gw_data
    
    def get_training_data(self, week_num):
        gk_features = self.get_pos_data(week_num, 'GK')
        def_features = self.get_pos_data(week_num, 'DEF')
        mid_features = self.get_pos_data(week_num, 'MID')
        fwd_features = self.get_pos_data(week_num, 'FWD')

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

        # Convert features and labels to numpy arrays
        gk_features = gk_features.to_numpy()
        def_features = def_features.to_numpy()
        mid_features = mid_features.to_numpy()
        fwd_features = fwd_features.to_numpy()

        gk_labels = gk_labels.to_numpy()
        def_labels = def_labels.to_numpy()
        mid_labels = mid_labels.to_numpy()
        fwd_labels = fwd_labels.to_numpy()

        # Group features & labels for convenience
        training_gk = (gk_features, gk_labels)
        training_def = (def_features, def_labels)
        training_mid = (mid_features, mid_labels)
        training_fwd = (fwd_features, fwd_labels)

        return feature_names, training_gk, training_def, training_mid, training_fwd

    def get_training_data_all(self, from_gw, to_gw):
        feature_names = []
        for i in range(from_gw, to_gw):
            if i == from_gw:
                feature_names, training_gk, training_def, training_mid, training_fwd = self.get_training_data(i)
            else:
                feature_names, training_gk_new, training_def_new, training_mid_new, training_fwd_new = self.get_training_data(i)
                training_gk = (np.concatenate((training_gk[0], training_gk_new[0])), np.concatenate((training_gk[1], training_gk_new[1])))
                training_def = (np.concatenate((training_def[0], training_def_new[0])), np.concatenate((training_def[1], training_def_new[1])))
                training_mid = (np.concatenate((training_mid[0], training_mid_new[0])), np.concatenate((training_mid[1], training_mid_new[1])))
                training_fwd = (np.concatenate((training_fwd[0], training_fwd_new[0])), np.concatenate((training_fwd[1], training_fwd_new[1])))

            feature_names = list(set(feature_names) & set(feature_names))

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

        return feature_names, training_data, test_data

    def get_test_data(self, week_num):
        gk_features = self.get_pos_data(week_num, 'GK')
        def_features = self.get_pos_data(week_num, 'DEF')
        mid_features = self.get_pos_data(week_num, 'MID')
        fwd_features = self.get_pos_data(week_num, 'FWD')

        # Drop the remaining columns that are not features
        gk_features = gk_features.drop(['total_points'], axis=1)
        def_features = def_features.drop(['total_points'], axis=1)
        mid_features = mid_features.drop(['total_points'], axis=1)
        fwd_features = fwd_features.drop(['total_points'], axis=1)

        # Get the player names in a list from each pos
        gk_names_list = list(gk_features.index)
        def_names_list = list(def_features.index)
        mid_names_list = list(mid_features.index)
        fwd_names_list = list(fwd_features.index)

        # Get the feature names in a list from each pos
        gk_feature_names = list(gk_features.columns)
        def_feature_names = list(def_features.columns)
        mid_feature_names = list(mid_features.columns)
        fwd_feature_names = list(fwd_features.columns)

        # Convert features and labels to numpy arrays
        gk_features = gk_features.to_numpy()
        def_features = def_features.to_numpy()
        mid_features = mid_features.to_numpy()
        fwd_features = fwd_features.to_numpy()

        return [gk_names_list, def_names_list, mid_names_list, fwd_names_list], [gk_feature_names, def_feature_names, mid_feature_names, fwd_feature_names], [gk_features, def_features, mid_features, fwd_features]

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
            n_est = 1000 # keep at 1000 whilst in development for speed
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