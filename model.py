'''
Model Generator for FPL Automation Project
Author: Benjamin Tindal
'''

import argparse
import numpy as np
import math
from fpl_auto.data import fpl_data
from fpl_auto import evaluate as eval
import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser(description="FPL Automation Project: Model")
    parser.add_argument('-gw_data', type=str, default='data/',
                        help='Location of Vastaav Dataset, default: data/')
    parser.add_argument('-model', type=str, default="gradientboost",
                        choices=[
                            "linear", "randomforest", "gradientboost"], 
                        help='Model type to use')
    parser.add_argument('-season', type=str, required=True, help='Season to predict points for. Format: YYYY-YY e.g 2021-22')
    parser.add_argument('-target_gw', type=int, default=1, help='Gameweek to predict points for, default 1')
    parser.add_argument('-repeat', type=int, default=38, help='How many weeks to repeat testing over, default: 38')
    parser.add_argument('-training_prev_weeks', type=int, default=10, help='How many past weeks of data to use for training, default: 10')
    parser.add_argument('-predict_weeks', type=int, default=3, help='How many past weeks of data to use for predicting, default: 3')
    parser.add_argument('-future_weeks', type=int, default=3, help='How many future weeks to use for predicting, default: 3')
    parser.add_argument('-display_weights',
                        action=argparse.BooleanOptionalAction, default=False, help='Whether to display feature weights, default: False')
    parser.add_argument('-plot_predictions',
                        action=argparse.BooleanOptionalAction, default=False, help='Whether to plot predictions vs actual points, default: False')
    parser.add_argument('-save', '-s',
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
output_files = inputs.save
# Future weeks to use
future_weeks = inputs.future_weeks

# Initialise classes
# Ensure that the correct location is specified for Vastaav data
vastaav = fpl_data('data', season)


def main():
    count = 0
    total_e = 0
    total_rmse = 0
    total_aa = 0
    
    # Predict points for GWi:
    for i in range(target_gameweek, min(target_gameweek + repeat, 39)):
        # Retrain model each time
        # Lets sum up the last 10 gameweeks to get a more accurate representation of player performance
        training_data, test_data = vastaav.get_training_data_all(
            season, i - training_prev_weeks, i)

        gk_model, def_model, mid_model, fwd_model = vastaav.get_model(modelType, training_data)

        if display_weights:
            feature_list = training_data[0][0].columns
            importances = [gk_model.feature_importances_, def_model.feature_importances_, mid_model.feature_importances_, fwd_model.feature_importances_]
            eval.display_weights(i, importances, feature_list, ['GK', 'DEF', 'MID', 'FWD'])

        gk_predictions = np.round(gk_model.predict(test_data[0][0]), 5)
        def_predictions = np.round(def_model.predict(test_data[1][0]), 5)
        mid_predictions = np.round(mid_model.predict(test_data[2][0]), 5)
        fwd_predictions = np.round(fwd_model.predict(test_data[3][0]), 5)

        """ gk_error, gk_square_error, gk_accuracy = eval.score_model(gk_predictions, test_data[0][1])
        def_error, def_square_error, def_accuracy = eval.score_model(def_predictions, test_data[1][1])
        mid_error, mid_square_error, mid_accuracy = eval.score_model(mid_predictions, test_data[2][1])
        fwd_error, fwd_square_error, fwd_accuracy = eval.score_model(fwd_predictions, test_data[3][1])

        # Average the errors
        error = (gk_error + def_error + mid_error + fwd_error) / 4
        rmse = (gk_square_error + def_square_error + mid_square_error + fwd_square_error) / 4
        aa = (gk_accuracy + def_accuracy + mid_accuracy + fwd_accuracy) / 4"""
        print(f'Predicting GW{i}') #: AE: {error:.3f}, RMSE: {rmse:.3f}, ACC: {aa*100:.2f}%')

        if plot_predictions:
            all_predictions = [gk_predictions, def_predictions, mid_predictions, fwd_predictions]
            eval.plot_predictions(all_predictions, test_data, i)

        count += 1
        """ total_e += error
        total_rmse += rmse
        total_aa += aa """

        # Lets use these models to predict the next gameweek
        models = gk_model, def_model, mid_model, fwd_model
        player_names, predictions = vastaav.get_player_predictions(season, i - predict_weeks, i, models)
        clean_predictions = []
        
        for j in range(4):
            tsv_predictions = np.column_stack((player_names[j], predictions[j]))
            tsv_predictions = np.concatenate((np.array([['Name', 'xP']]), tsv_predictions), axis=0)
            tsv_predictions = pd.DataFrame(tsv_predictions[1:], columns=tsv_predictions[0])
            tsv_predictions.set_index('Name', inplace=True)
            clean_predictions.append(tsv_predictions)

        # Now we have our model predictions, lets do some post-weightings
        weeks_left = 38 - i
        if future_weeks != 0:
            if weeks_left >= future_weeks:
                clean_predictions = vastaav.post_model_weightings(clean_predictions, i-1, future_weeks)
            elif weeks_left < future_weeks and weeks_left > 0:
                clean_predictions = vastaav.post_model_weightings(clean_predictions, i-1, min(1, weeks_left))
        
        if output_files:
            eval.export_tsv(clean_predictions, season, i)
        
    if repeat > 1:
        """ total_e /= count
        total_rmse /= count
        total_aa /= count"""
    
        print(f'Count: {count}')#, Average AE: {total_e:.2f}, Average RMSE: {math.sqrt(total_rmse):.2f}, Average ACC: {total_aa*100:.2f}%')
if __name__ == "__main__":
    main()
