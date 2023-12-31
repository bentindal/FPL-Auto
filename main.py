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
from fplapi import fplapi_data
from vastaav import vastaav_data
from evaluate import fpl_evaluate
from sklearn import linear_model, ensemble
import xgboost as xgb
from sklearn.ensemble import RandomForestRegressor 
import matplotlib.pyplot as plt

def parse_args():
    parser = argparse.ArgumentParser(description="FPL Automation Project through ML and Strategy")
    parser.add_argument('-model', type=str, default="gradientboost",
                        choices=[
                            "linear", "randomforest", "xgboost", "gradientboost"])
    
    parser.add_argument('-season', type=str, default='2023-24')
    
    parser.add_argument('-target_gw', type=int)

    parser.add_argument('-repeat', type=int, default=1)

    parser.add_argument('-training_prev_weeks', type=int, default=10)

    parser.add_argument('-last_gw', type=int, default=19)

    parser.add_argument('-display_weights',
                        action=argparse.BooleanOptionalAction, default=False)
    
    parser.add_argument('-plot_predictions',
                        action=argparse.BooleanOptionalAction, default=False)
    
    parser.add_argument('-export_csv',
                        action=argparse.BooleanOptionalAction, default=False)
    
    

    
    
    args = parser.parse_args()
    
    
    return args

inputs = parse_args()
# Season to predict points for
season = inputs.season
prev_season = f'{int(season[:4])-1}-{int(season[5:])-1}'
# First gameweek to predict points for
target_gameweek = inputs.target_gw
# Last gameweek data is available for
last_gameweek = inputs.last_gw
# How many weeks to repeat testing over
repeat = inputs.repeat
# Select a model type [linear, randomforest, xgboost, gradientboost]
modelType = inputs.model
# How many past weeks of data to use for training
training_prev_weeks = inputs.training_prev_weeks
# Whether to display feature weights
display_weights = inputs.display_weights
# Whether to plot predictions vs actual points
plot_predictions = inputs.plot_predictions
# Whether to export predictions to csv
export_csv = inputs.export_csv

# Initialise classes
fplapi = fplapi_data(season)
# Ensure that the correct location is specified for Vastaav data
vastaav = vastaav_data('../Fantasy-Premier-League/data', season)
eval = fpl_evaluate()


def main():
    count = 0
    total_e = 0
    total_ase = 0
    total_aa = 0
    
    # Predict points for GWi
    for i in range(target_gameweek, target_gameweek + repeat):
        # Retrain model each time
        # Lets sum up the last 10 gameweeks to get a more accurate representation of player performance
        if i > last_gameweek:
            print(f'Predicting GW{i+1}: n/a')
            training_data, test_data = vastaav.get_training_data_all(
                season, last_gameweek - training_prev_weeks, last_gameweek)
        else:
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

        if i <= last_gameweek:
            gk_error, gk_square_error, gk_accuracy = eval.score_model(gk_predictions, test_data[0][1])
            def_error, def_square_error, def_accuracy = eval.score_model(def_predictions, test_data[1][1])
            mid_error, mid_square_error, mid_accuracy = eval.score_model(mid_predictions, test_data[2][1])
            fwd_error, fwd_square_error, fwd_accuracy = eval.score_model(fwd_predictions, test_data[3][1])

            # Average the errors
            error = (gk_error + def_error + mid_error + fwd_error) / 4
            ase = (gk_square_error + def_square_error + mid_square_error + fwd_square_error) / 4
            aa = (gk_accuracy + def_accuracy + mid_accuracy + fwd_accuracy) / 4
            print(f'Predicting GW{i+1}: AE: {error:.3f}, ASE: {math.sqrt(ase):.3f}, ACC: {aa*100:.2f}%')

        '''if i <= last_gameweek:
            # Output predictions to csv, use player_names as first column, then predictions, then actual points
            # This will allow us to compare predictions to actual points
            csv_gk_predictions = np.column_stack((player_names[0], gk_predictions, labels[0]))
            csv_def_predictions = np.column_stack((player_names[1], def_predictions, labels[1]))
            csv_mid_predictions = np.column_stack((player_names[2], mid_predictions, labels[2]))
            csv_fwd_predictions = np.column_stack((player_names[3], fwd_predictions, labels[3]))
            
            csv_gk_predictions = np.concatenate((np.array([['Name', 'xP', 'P']]), csv_gk_predictions), axis=0)
        else:
            csv_gk_predictions = np.column_stack((player_names[0], gk_predictions))
            csv_def_predictions = np.column_stack((player_names[1], def_predictions))
            csv_mid_predictions = np.column_stack((player_names[2], mid_predictions))
            csv_fwd_predictions = np.column_stack((player_names[3], fwd_predictions))

            csv_gk_predictions = np.concatenate((np.array([['Name', 'xP']]), csv_gk_predictions), axis=0)
        
        csv_predictions = np.concatenate((csv_gk_predictions, csv_def_predictions, csv_mid_predictions, csv_fwd_predictions), axis=0)

        csv_predictions = pd.DataFrame(csv_predictions[1:], columns=csv_predictions[0])
        csv_predictions.set_index('Name', inplace=True)

        csv_predictions.to_csv(f'predictions/predictions_{modelType}_gw{i}.csv')
        '''
        
        if plot_predictions:
            all_predictions = [gk_predictions, def_predictions, mid_predictions, fwd_predictions]
            eval.plot_predictions(all_predictions, test_data, i)

        if i <= last_gameweek:
            count += 1
            total_e += error
            total_ase += ase
            total_aa += aa

        if export_csv:
            # Lets use these models to predict the next gameweek
            models = gk_model, def_model, mid_model, fwd_model
            player_names, predictions = vastaav.get_player_predictions(season, i, models)
            # Output predictions to csv, use player_names as first column, then predictions
            csv_gk_predictions = np.column_stack((player_names[0], predictions[0]))
            csv_def_predictions = np.column_stack((player_names[1], predictions[1]))
            csv_mid_predictions = np.column_stack((player_names[2], predictions[2]))
            csv_fwd_predictions = np.column_stack((player_names[3], predictions[3]))

            csv_combined = np.concatenate((csv_gk_predictions, csv_def_predictions, csv_mid_predictions, csv_fwd_predictions), axis=0)
            # Add headers
            csv_combined = np.concatenate((np.array([['Name', 'xP']]), csv_combined), axis=0)

            csv_predictions = pd.DataFrame(csv_combined[1:], columns=csv_combined[0])
            csv_predictions.set_index('Name', inplace=True)

            csv_predictions.to_csv(f'predictions/predictions_{modelType}_gw{i+1}.csv')
            print(f'GW{i+1} predictions saved to csv')

    total_e /= count
    total_ase /= count
    total_aa /= count

    print(f'Count: {count}, Average AE: {total_e:.2f}, Average ASE: {math.sqrt(total_ase):.2f}, Average ACC: {total_aa*100:.2f}%')

if __name__ == "__main__":
    main()
