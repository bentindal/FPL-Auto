'''
FPL Automation Project
Author: Benjamin Tindal
'''

import numpy as np
import pandas as pd
import requests, json
from pprint import pprint
import json
from fplapi import fplapi_data
from vastaav import vastaav_data
from evaluate import fpl_evaluate
from sklearn import linear_model, tree
import matplotlib.pyplot as plt

target_season = '2023-24'
target_gameweek = 9
last_gameweek = 18
fplapi = fplapi_data(target_season)
vastaav = vastaav_data('../Fantasy-Premier-League/data', target_season)
eval = fpl_evaluate()

def main():
    # Predict points for GWi
    for i in range(target_gameweek, target_gameweek + 10):
        # Retrain model each time
        # Lets sum up the last 3 gameweeks to get a more accurate representation of player performance
        if i >= last_gameweek:
            i = last_gameweek - 1

        __, feature_names, week_data = vastaav.get_training_data(i - 1)

        # Lets train a model
        gk_model = linear_model.LinearRegression()
        gk_model.fit(week_data[0][0], week_data[0][1])

        def_model = linear_model.LinearRegression()
        def_model.fit(week_data[1][0], week_data[1][1])

        mid_model = linear_model.LinearRegression()
        mid_model.fit(week_data[2][0], week_data[2][1])

        fwd_model = linear_model.LinearRegression()
        fwd_model.fit(week_data[3][0], week_data[3][1])

        # Plot the weights to each feature
        weights = np.concatenate((gk_model.coef_, def_model.coef_, mid_model.coef_, fwd_model.coef_))
        feature_names = np.concatenate((feature_names[0], feature_names[1], feature_names[2], feature_names[3]))

        plt.title(f'Feature weights for GW{i}')
        plt.xlabel('Feature')
        plt.ylabel('Weight')
        plt.bar(feature_names, weights)
        plt.xticks(rotation=90)
        plt.show()


        # target_gameweek has not happened yet, so we predict it using past data 
        # Get test data by summing up 3 previous gameweeks
        # week_data = GWi-3 + GWi-2 + GWi-1
        if i == last_gameweek - 1:
            print(f'Predicting FUTURE GW{i}...')
            # Get features from most up to date data
            player_names, feature_names, features = vastaav.get_test_data(last_gameweek - 1)
        else: 
            player_names, feature_names, test_data = vastaav.get_training_data(i)
        
            # Get the features and labels from the test data
            features = [test_data[0][0], test_data[1][0], test_data[2][0], test_data[3][0]]
            labels = [test_data[0][1], test_data[1][1], test_data[2][1], test_data[3][1]] 

        gk_predictions = np.round(gk_model.predict(features[0]), 3)
        def_predictions = np.round(def_model.predict(features[1]), 3)
        mid_predictions = np.round(mid_model.predict(features[2]), 3)
        fwd_predictions = np.round(fwd_model.predict(features[3]), 3)

        # Round predictions to 3dp



        if i < last_gameweek - 1:
            gk_error, gk_square_error, gk_accuracy = eval.score_model(gk_predictions, labels[0])
            def_error, def_square_error, def_accuracy = eval.score_model(def_predictions, labels[1])
            mid_error, mid_square_error, mid_accuracy = eval.score_model(mid_predictions, labels[2])
            fwd_error, fwd_square_error, fwd_accuracy = eval.score_model(fwd_predictions, labels[3])

            # Average the errors
            error = (gk_error + def_error + mid_error + fwd_error) / 4
            ase = (gk_square_error + def_square_error + mid_square_error + fwd_square_error) / 4
            aa = (gk_accuracy + def_accuracy + mid_accuracy + fwd_accuracy) / 4
            print(f'GW{i}, AE: {error:.2f}, ASE: {ase:.2f}, ACC: {aa*100:.2f}%')

        if i < last_gameweek - 1:
            # Output predictions to csv, use player_names as first column, then predictions, then actual points
            # This will allow us to compare predictions to actual points
            csv_gk_predictions = np.column_stack((player_names[0], gk_predictions, labels[0]))
            csv_def_predictions = np.column_stack((player_names[1], def_predictions, labels[1]))
            csv_mid_predictions = np.column_stack((player_names[2], mid_predictions, labels[2]))
            csv_fwd_predictions = np.column_stack((player_names[3], fwd_predictions, labels[3]))
            
            csv_gk_predictions = np.concatenate((np.array([['Name', 'Predicted points', 'Actual Points']]), csv_gk_predictions), axis=0)
        else:
            csv_gk_predictions = np.column_stack((player_names[0], gk_predictions))
            csv_def_predictions = np.column_stack((player_names[1], def_predictions))
            csv_mid_predictions = np.column_stack((player_names[2], mid_predictions))
            csv_fwd_predictions = np.column_stack((player_names[3], fwd_predictions))

            csv_gk_predictions = np.concatenate((np.array([['Name', 'Predicted points']]), csv_gk_predictions), axis=0)
        
        csv_predictions = np.concatenate((csv_gk_predictions, csv_def_predictions, csv_mid_predictions, csv_fwd_predictions), axis=0)

        csv_predictions = pd.DataFrame(csv_predictions[1:], columns=csv_predictions[0])
        csv_predictions.set_index('Name', inplace=True)

        csv_predictions.to_csv(f'predictions/predictions_gw{i}.csv')
        
        '''# Plot predictions vs actual points for GWi
        # Colour code by position
        plt.title(f'GW{i} predictions vs actual points')
        plt.xlabel('Predicted points')
        plt.ylabel('Actual points')
        print(len(gk_predictions))
        print(len(labels[0]))
        plt.scatter(gk_predictions, labels[0], color='red')
        plt.scatter(def_predictions, labels[1], color='blue')
        plt.scatter(mid_predictions, labels[2], color='green')
        plt.scatter(fwd_predictions, labels[3], color='orange')
        plt.legend(['GK', 'DEF', 'MID', 'FWD'])
        # Plot y=x line to show perfect prediction
        plt.plot([0, 20], [0, 20], color='black')
        plt.show()'''






if __name__ == "__main__":
    main()
