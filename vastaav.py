import numpy as np
import pandas as pd
import requests, json
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
        # Drop all columns except for team name and team id
        team_list = team_list[['name', 'strength_overall_home', 'strength_overall_away', 'strength_attack_home', 'strength_attack_away', 'strength_defence_home', 'strength_defence_away']]
        return team_list.set_index('name')
    
    def get_gw_data(self, week_num):
        gw_data = pd.read_csv(f'{self.data_location}/gws/gw{week_num}.csv')
        # Drop all columns except for player name and position
        gw_data = gw_data[['name', 'position', 'team', 'assists', 'bps', 'clean_sheets', 'creativity', 'goals_conceded', 'goals_scored', 'ict_index', 'influence', 'minutes', 'own_goals', 'penalties_missed', 'penalties_saved', 'red_cards', 'saves', 'threat', 'total_points', 'yellow_cards', 'selected', 'was_home']]
        return gw_data.set_index('name')

    def get_pos_data(self, week_num, position, training=False):
        gw_data = self.get_gw_data(week_num)
        # Drop all players that are not of the specified position
        gw_data = gw_data[gw_data['position'] == position]

        # Goalkeepers
        # Drop goals_scored, assists, threat
        # Add based on team: strength_defence_home, strength_defence_away
        if position == 'GK':
            gw_data = gw_data.drop(['goals_scored', 'assists', 'threat'], axis=1)
            '''for index, row in gw_data.iterrows():
                if row['was_home']:
                    gw_data.at[index, 'team'] = self.team_list.loc[row['team']]['strength_defence_home']
                else:
                    gw_data.at[index, 'team'] = self.team_list.loc[row['team']]['strength_defence_away']'''
        # Defenders
        # Drop penalties_saved, saves
        # Add based on team: strength_defence_home, strength_defence_away
        elif position == 'DEF':
            gw_data = gw_data.drop(['penalties_saved', 'saves'], axis=1)
            '''for index, row in gw_data.iterrows():
                if row['was_home']:
                    gw_data.at[index, 'team'] = self.team_list.loc[row['team']]['strength_defence_home']
                else:
                    gw_data.at[index, 'team'] = self.team_list.loc[row['team']]['strength_defence_away']'''
        # Midfielders
        # Drop penalties_saved, saves, clean_sheets
        # Add based on team: strength_overall_home, strength_overall_away
        elif position == 'MID':
            gw_data = gw_data.drop(['penalties_saved', 'saves', 'clean_sheets'], axis=1)
            '''for index, row in gw_data.iterrows():
                if row['was_home']:
                    gw_data.at[index, 'team'] = self.team_list.loc[row['team']]['strength_overall_home']
                else:
                    gw_data.at[index, 'team'] = self.team_list.loc[row['team']]['strength_overall_away']'''
        # Forwards
        # Drop penalties_saved, saves, clean_sheets, goals_conceded
        # Add based on team: strength_attack_home, strength_attack_away
        elif position == 'FWD':
            gw_data = gw_data.drop(['penalties_saved', 'saves', 'clean_sheets', 'goals_conceded'], axis=1)
            '''for index, row in gw_data.iterrows():
                if row['was_home']:
                    gw_data.at[index, 'team'] = self.team_list.loc[row['team']]['strength_attack_home']
                else:
                    gw_data.at[index, 'team'] = self.team_list.loc[row['team']]['strength_attack_away']'''
            
        else:
            print(f'Invalid position: {position}')
            quit()

        return gw_data
    
    def get_training_data(self, week_num):
        gk_features = self.get_pos_data(week_num, 'GK', True)
        def_features = self.get_pos_data(week_num, 'DEF', True)
        mid_features = self.get_pos_data(week_num, 'MID', True)
        fwd_features = self.get_pos_data(week_num, 'FWD', True)

        # Remove all players that have not played
        gk_features = gk_features[gk_features['minutes'] > 0]
        def_features = def_features[def_features['minutes'] > 0]
        mid_features = mid_features[mid_features['minutes'] > 0]
        fwd_features = fwd_features[fwd_features['minutes'] > 0]
        
        # Seperate labels from features
        gk_labels = gk_features['total_points']
        def_labels = def_features['total_points']
        mid_labels = mid_features['total_points']
        fwd_labels = fwd_features['total_points']

        # Drop the name column
        gk_features = gk_features.drop(['was_home', 'team', 'position', 'total_points'], axis=1)
        def_features = def_features.drop(['was_home', 'team', 'position', 'total_points'], axis=1)
        mid_features = mid_features.drop(['was_home', 'team', 'position', 'total_points'], axis=1)
        fwd_features = fwd_features.drop(['was_home', 'team', 'position', 'total_points'], axis=1)

        # Make sure there are no NaN values
        gk_features = gk_features.fillna(0)
        def_features = def_features.fillna(0)
        mid_features = mid_features.fillna(0)
        fwd_features = fwd_features.fillna(0)

        # Check for NaN values in labels
        if gk_labels.isnull().values.any():
            print('NaN values in gk_labels')
            quit()
        if def_labels.isnull().values.any():
            print('NaN values in def_labels')
            quit()
        if mid_labels.isnull().values.any():
            print('NaN values in mid_labels')
            quit()
        if fwd_labels.isnull().values.any():
            print('NaN values in fwd_labels')
            quit()

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

        return training_gk, training_def, training_mid, training_fwd
    
