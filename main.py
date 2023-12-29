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

target_season = '2023-24'
target_gameweek = 15
last_gameweek = 18
repeat = 5
modelType = 'linear' # linear, randomforest, xgboost, gradientboost
display_weights = False
plot_predictions = False

fplapi = fplapi_data(target_season)
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
            feature_names, training_data, test_data = vastaav.get_training_data_all(last_gameweek - 6, last_gameweek - 1)
        else:
            feature_names, training_data, test_data = vastaav.get_training_data_all(i - 6, i - 1)

        # Lets train a model
        if modelType == 'linear':
            gk_model = linear_model.LinearRegression()
            def_model = linear_model.LinearRegression()
            mid_model = linear_model.LinearRegression()
            fwd_model = linear_model.LinearRegression()
            
        elif modelType == 'randomforest':
            gk_model = RandomForestRegressor(oob_score = True, n_estimators = 1000, max_features = 5)
            def_model = RandomForestRegressor(oob_score = True, n_estimators = 1000, max_features = 5)
            mid_model = RandomForestRegressor(oob_score = True, n_estimators = 1000, max_features = 5)
            fwd_model = RandomForestRegressor(oob_score = True, n_estimators = 1000, max_features = 5)

        elif modelType == 'xgboost':
            gk_model = xgb.XGBRegressor()
            def_model = xgb.XGBRegressor()
            mid_model = xgb.XGBRegressor()
            fwd_model = xgb.XGBRegressor()

        elif modelType == 'gradientboost':
            loss_function = 'squared_error'
            n_est = 1000 # keep at 1000 whilst in development for speed
            l_rate = 0.2
            gk_model = ensemble.GradientBoostingRegressor(max_features=17, n_estimators=n_est, learning_rate=l_rate, loss=loss_function)
            def_model = ensemble.GradientBoostingRegressor(max_features=17,n_estimators=n_est, learning_rate=l_rate, loss=loss_function)
            mid_model = ensemble.GradientBoostingRegressor(max_features=17,n_estimators=n_est, learning_rate=l_rate, loss=loss_function)
            fwd_model = ensemble.GradientBoostingRegressor(max_features=17,n_estimators=n_est, learning_rate=l_rate, loss=loss_function)

        gk_model.fit(training_data[0][0], training_data[0][1])
        def_model.fit(training_data[1][0], training_data[1][1])
        mid_model.fit(training_data[2][0], training_data[2][1])
        fwd_model.fit(training_data[3][0], training_data[3][1])

        if display_weights:
            ''' NOT WORKING PROPERLY
            - Feature names are not in the same order as the weights
            - Need to find a way to get the feature names in the same order as the weights'''

            # Plot feature weights
            # Get the feature weights from each model
            gk_weights = gk_model.coef_
            def_weights = def_model.coef_
            mid_weights = mid_model.coef_
            fwd_weights = fwd_model.coef_

            # Plot the weights
            plt.title(f'GW{i} feature weights for MID')
            plt.xlabel('Feature')
            plt.ylabel('Weight')
            plt.bar(feature_names, mid_weights)
            plt.xticks(rotation=90)
            plt.tight_layout()
            plt.show()

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
            # Plot predictions vs actual points for GWi
            # Colour code by position
            plt.title(f'GW{i} predictions vs actual points')
            plt.xlabel('Predicted points')
            plt.ylabel('Actual points')
            plt.scatter(gk_predictions, test_data[0][1], color='red')
            plt.scatter(def_predictions, test_data[1][1], color='blue')
            plt.scatter(mid_predictions, test_data[2][1], color='green')
            plt.scatter(fwd_predictions, test_data[3][1], color='orange')

            plt.legend(['GK', 'DEF', 'MID', 'FWD'])
            # Plot y=x line to show perfect prediction
            plt.plot([0, 20], [0, 20], color='black')
            plt.show()

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
