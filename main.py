'''
FPL Automation Project
Author: Benjamin Tindal
'''

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

# Season to predict points for
target_season = '2023-24'
# First gameweek to predict points for
target_gameweek = 15
# Last gameweek data is available for
last_gameweek = 19
# How many weeks to repeat testing over
repeat = 5
# Select a model type [linear, randomforest, xgboost, gradientboost]
modelType = 'linear'
# How many past weeks of data to use for training
training_prev_weeks = 5
# Whether to display feature weights CURRENTLY NOT WORKING
display_weights = False
# Whether to plot predictions vs actual points
plot_predictions = True

# Initialise classes

fplapi = fplapi_data(target_season)
# Ensure that the correct location is specified for Vastaav data
vastaav = vastaav_data('../Fantasy-Premier-League/data', target_season)
eval = fpl_evaluate()

def main():
    count = 0
    total_e = 0
    total_ase = 0
    total_aa = 0
    
    # Predict points for GWi
    for i in range(target_gameweek, target_gameweek + repeat):
        # Retrain model each time
        # Lets sum up the last 3 gameweeks to get a more accurate representation of player performance
        if i > last_gameweek:
            print(f'GW{i}: n/a')
            feature_names, training_data, test_data = vastaav.get_training_data_all(
                last_gameweek - training_prev_weeks - 1, last_gameweek - 1)
        else:
            feature_names, training_data, test_data = vastaav.get_training_data_all(
                i - training_prev_weeks - 1, i - 1)

        gk_model, def_model, mid_model, fwd_model = vastaav.get_model(modelType, training_data)

        if display_weights:
            ''' NOT WORKING PROPERLY
            - Feature names are not in the same order as the weights
            - Need to find a way to get the feature names in the same order as the weights'''

            eval.display_weights(gk_model, feature_names[0], 'GK')

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
            print(f'GW{i}: AE: {error:.3f}, ASE: {math.sqrt(ase):.3f}, ACC: {aa*100:.2f}%')

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
    
    total_e /= count
    total_ase /= count
    total_aa /= count

    print(f'Count: {count}, Average AE: {total_e:.2f}, Average ASE: {math.sqrt(total_ase):.2f}, Average ACC: {total_aa*100:.2f}%')

if __name__ == "__main__":
    main()
