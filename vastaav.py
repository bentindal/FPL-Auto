import numpy as np
import pandas as pd
import requests
import json
from pprint import pprint
import json

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

        # Get the 'total_points' label from next gameweek
        gk_labels = self.get_pos_data(week_num + 1, 'GK')
        def_labels = self.get_pos_data(week_num + 1, 'DEF')
        mid_labels = self.get_pos_data(week_num + 1, 'MID')
        fwd_labels = self.get_pos_data(week_num + 1, 'FWD')

        # Keep only players that are in both the features and labels
        gk_features = gk_features[gk_features.index.isin(gk_labels.index)]
        def_features = def_features[def_features.index.isin(def_labels.index)]
        mid_features = mid_features[mid_features.index.isin(mid_labels.index)]
        fwd_features = fwd_features[fwd_features.index.isin(fwd_labels.index)]

        gk_labels = gk_labels[gk_labels.index.isin(gk_features.index)]['total_points']
        def_labels = def_labels[def_labels.index.isin(def_features.index)]['total_points']
        mid_labels = mid_labels[mid_labels.index.isin(mid_features.index)]['total_points']
        fwd_labels = fwd_labels[fwd_labels.index.isin(fwd_features.index)]['total_points']

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
        gk_feature_list = list(gk_features.columns)
        def_feature_list = list(def_features.columns)
        mid_feature_list = list(mid_features.columns)
        fwd_feature_list = list(fwd_features.columns)

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

        return [gk_names_list, def_names_list, mid_names_list, fwd_names_list], [gk_feature_list, def_feature_list, mid_feature_list, fwd_feature_list], [training_gk, training_def, training_mid, training_fwd]

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
        gk_feature_list = list(gk_features.columns)
        def_feature_list = list(def_features.columns)
        mid_feature_list = list(mid_features.columns)
        fwd_feature_list = list(fwd_features.columns)

        # Convert features and labels to numpy arrays
        gk_features = gk_features.to_numpy()
        def_features = def_features.to_numpy()
        mid_features = mid_features.to_numpy()
        fwd_features = fwd_features.to_numpy()

        return [gk_names_list, def_names_list, mid_names_list, fwd_names_list], [gk_feature_list, def_feature_list, mid_feature_list, fwd_feature_list], [gk_features, def_features, mid_features, fwd_features]
