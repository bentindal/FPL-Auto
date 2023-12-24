import numpy as np
import pandas as pd
import requests, json
from pprint import pprint
import json

class fplapi_data:
    def __init__(self, season):
        self.season = season
        self.season_data = self.get_season_data()
        self.player_list = self.get_player_list(self.season_data)
        # Swap keys and values in player_list
        self.player_id_list = {v: k for k, v in self.player_list.items()}
        
        self.team_list = self.get_team_list(self.season_data)

    def get_season_data(self):
        url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        return requests.get(url).json()

    def get_gameweek_data(self, gameweek):
        url = f'https://fantasy.premierleague.com/api/event/{gameweek}/live/'
        return requests.get(url).json()

    def get_player_data(self, player_id):
        url = f'https://fantasy.premierleague.com/api/element-summary/{player_id}/'
        return requests.get(url).json()

    # Get a list of all player combined full name and their IDs
    def get_player_list(self, season_data):
        player_list = {}
        for player in season_data['elements']:
            player_list[f'{player["first_name"]} {player["second_name"]}'] = player['id']
        
        return player_list

    def get_team_list(self, season_data):
        team_list = {}
        for team in season_data['teams']:
            if team['name'] not in team_list:
                team_list[team['name']] = team['id']
        return team_list
        