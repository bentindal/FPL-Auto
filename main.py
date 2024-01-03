'''
FPL Automation Project
Author: Benjamin Tindal
'''

import argparse
import numpy as np
import pandas as pd
import math
from pprint import pprint
import json
from vastaav import vastaav_data
from evaluate import fpl_evaluate
import team
from sklearn import linear_model, ensemble
import xgboost as xgb
from sklearn.ensemble import RandomForestRegressor 
import matplotlib.pyplot as plt

def parse_args():
    parser = argparse.ArgumentParser(description="FPL Automation Project through ML and Strategy")
    parser.add_argument('-gw_data', type=str, default='../Fantasy-Premier-League/data',
                        help='Location of Vastaav Dataset, default: ../Fantasy-Premier-League/data')
    parser.add_argument('-model', type=str, default="gradientboost",
                        choices=[
                            "linear", "randomforest", "xgboost", "gradientboost"], 
                        help='Model type to use')
    parser.add_argument('-season', type=str, default='2023-24', help='Season to predict points for, default: 2023-24')
    parser.add_argument('-target_gw', type=int, required=True, help='Gameweek to predict points for, required')
    parser.add_argument('-repeat', type=int, default=1, help='How many weeks to repeat testing over, default: 1')
    parser.add_argument('-training_prev_weeks', type=int, default=10, help='How many past weeks of data to use for training, default: 10')
    parser.add_argument('-predict_weeks', type=int, default=3, help='How many past weeks of data to use for predicting, default: 3')
    parser.add_argument('-display_weights',
                        action=argparse.BooleanOptionalAction, default=False, help='Whether to display feature weights, default: False')
    parser.add_argument('-plot_predictions',
                        action=argparse.BooleanOptionalAction, default=False, help='Whether to plot predictions vs actual points, default: False')
    parser.add_argument('-output_files',
                        action=argparse.BooleanOptionalAction, default=False, help='Whether to export predictions to tsv, default: False')
    
    args = parser.parse_args()
    
    return args

inputs = parse_args()
# Season to predict points for
season = inputs.season
prev_season = f'{int(season[:4])-1}-{int(season[5:])-1}'
# First gameweek to predict points for
target_gameweek = inputs.target_gw
# How many weeks to repeat testing over
repeat = inputs.repeat
# Select a model type [linear, randomforest, xgboost, gradientboost]
modelType = inputs.model
# How many past weeks of data to use for training
training_prev_weeks = inputs.training_prev_weeks
# How many past weeks of data to use for predicting
predict_weeks = inputs.predict_weeks
# Whether to display feature weights
display_weights = inputs.display_weights
# Whether to plot predictions vs actual points
plot_predictions = inputs.plot_predictions
# Whether to export predictions to tsv
output_files = inputs.output_files

# Initialise classes
# Ensure that the correct location is specified for Vastaav data
vastaav = vastaav_data('data', season)
eval = fpl_evaluate()


def main():
    count = 0
    total_e = 0
    total_ase = 0
    total_aa = 0
    generate_data = True
    
    # Predict points for GWi:
    for i in range(target_gameweek, target_gameweek + repeat):
        # Retrain model each time
        # Lets sum up the last 10 gameweeks to get a more accurate representation of player performance
        training_data, test_data = vastaav.get_training_data_all(
            season, i - training_prev_weeks, i)

        gk_model, def_model, mid_model, fwd_model = vastaav.get_model(modelType, training_data)

        if display_weights:
            feature_list = training_data[0][0].columns
            importances = [gk_model.feature_importances_, def_model.feature_importances_, mid_model.feature_importances_, fwd_model.feature_importances_]
            eval.display_weights(i, importances, feature_list, ['GK', 'DEF', 'MID', 'FWD'])

        gk_predictions = np.round(gk_model.predict(test_data[0][0]), 3)
        def_predictions = np.round(def_model.predict(test_data[1][0]), 3)
        mid_predictions = np.round(mid_model.predict(test_data[2][0]), 3)
        fwd_predictions = np.round(fwd_model.predict(test_data[3][0]), 3)

        gk_error, gk_square_error, gk_accuracy = eval.score_model(gk_predictions, test_data[0][1])
        def_error, def_square_error, def_accuracy = eval.score_model(def_predictions, test_data[1][1])
        mid_error, mid_square_error, mid_accuracy = eval.score_model(mid_predictions, test_data[2][1])
        fwd_error, fwd_square_error, fwd_accuracy = eval.score_model(fwd_predictions, test_data[3][1])

        # Average the errors
        error = (gk_error + def_error + mid_error + fwd_error) / 4
        ase = (gk_square_error + def_square_error + mid_square_error + fwd_square_error) / 4
        aa = (gk_accuracy + def_accuracy + mid_accuracy + fwd_accuracy) / 4
        print(f'Predicting GW{i}: AE: {error:.3f}, ASE: {math.sqrt(ase):.3f}, ACC: {aa*100:.2f}%')

        if plot_predictions:
            all_predictions = [gk_predictions, def_predictions, mid_predictions, fwd_predictions]
            eval.plot_predictions(all_predictions, test_data, i)

        count += 1
        total_e += error
        total_ase += ase
        total_aa += aa

        if output_files:
            # Lets use these models to predict the next gameweek
            models = gk_model, def_model, mid_model, fwd_model
            player_names, predictions = vastaav.get_player_predictions(season, i - predict_weeks, i, models)
            eval.export_tsv(player_names, predictions, i)

        t = team.team(season, i)
        t.add_player('André Onana', 'GK')
        t.add_player('Gabriel dos Santos Magalhães', 'DEF')
        t.add_player('Pedro Porro', 'DEF')
        t.add_player('Kieran Trippier', 'DEF')
        t.add_player('Cole Palmer', 'MID')
        t.add_player('Jarrod Bowen', 'MID')
        t.add_player('Bukayo Saka', 'MID')
        t.add_player('Phil Foden', 'MID')
        t.add_player('Ollie Watkins', 'FWD')
        t.add_player('Dominic Solanke', 'FWD')
        t.add_player('Julián Álvarez', 'FWD')
        
        t.add_player('Martin Dubravka', 'GK')
        t.add_player('Joachim Andersen', 'DEF')
        t.add_player('Shandon Baptiste', 'MID')
        t.add_player('George Baldock', 'DEF')
        t.auto_subs()
        t.auto_captain()

        t.display()

        print(f'Team xP: {t.team_xp():.2f}')
        
    if repeat > 1:
        total_e /= count
        total_ase /= count
        total_aa /= count
    
        print(f'Count: {count}, Average AE: {total_e:.2f}, Average ASE: {math.sqrt(total_ase):.2f}, Average ACC: {total_aa*100:.2f}%')

if __name__ == "__main__":
    main()
