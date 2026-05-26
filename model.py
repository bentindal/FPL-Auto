'''
Model Generator for FPL Automation Project
Author: Benjamin Tindal
'''

import argparse
import numpy as np
from fpl_auto.data import fpl_data
from fpl_auto.predictor import Predictor, POSITIONS
from fpl_auto import evaluate as eval
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(description="FPL Automation Project: Model")
    parser.add_argument('-gw_data', type=str, default='data/',
                        help='Location of Vastaav Dataset, default: data/')
    parser.add_argument('-model', type=str, default='gradientboost',
                        choices=Predictor.TYPES,
                        help=f'Model type to use. Choices: {Predictor.TYPES}. Default: gradientboost')
    parser.add_argument('-season', type=str, required=True,
                        choices=['2021-22', '2022-23', '2023-24', '2024-25'],
                        help='Season to predict points for. Format: YYYY-YY e.g 2021-22')
    parser.add_argument('-target_gw', type=int, default=1,
                        help='Gameweek to predict points for, default 1')
    parser.add_argument('-repeat', type=int, default=38,
                        help='How many weeks to repeat testing over, default: 38')
    parser.add_argument('-training_prev_weeks', type=int, default=19,
                        help='How many past weeks of data to use for training, default: 19')
    parser.add_argument('-predict_weeks', type=int, default=4,
                        help='How many past weeks of data to use for predicting, default: 4')
    parser.add_argument('-display_weights', action=argparse.BooleanOptionalAction, default=False,
                        help='Whether to display feature weights, default: False')
    parser.add_argument('-plot_predictions', action=argparse.BooleanOptionalAction, default=False,
                        help='Whether to plot predictions vs actual points, default: False')
    parser.add_argument('-save', '-s', action=argparse.BooleanOptionalAction, default=False,
                        help='Whether to export predictions to tsv, default: False')
    parser.add_argument('-score_train_vs_test', action=argparse.BooleanOptionalAction, default=False,
                        help='Print RMSE, AE etc.. of model on training and test data, default: False')
    return parser.parse_args()


def main():
    inputs = parse_args()
    season = inputs.season
    target_gameweek = inputs.target_gw
    repeat = inputs.repeat
    training_prev_weeks = inputs.training_prev_weeks
    predict_weeks = inputs.predict_weeks

    vastaav = fpl_data('data', season)

    count = 0
    total_e = total_rmse = total_aa = 0.0

    for i in range(target_gameweek, min(target_gameweek + repeat, 39)):
        try:
            training_data, test_data = vastaav.get_training_data_all(season, i - training_prev_weeks, i)
        except UnboundLocalError:
            print(f'Reached Prediction Limit for {season} GW{i}, can only predict 1 week beyond data.')
            return

        predictor = Predictor(model_type=inputs.model).fit(training_data)

        if inputs.display_weights:
            feature_list = training_data[0][0].columns
            eval.display_weights(i, predictor.feature_importances(), feature_list, POSITIONS)

        test_preds = predictor.predict_test(test_data)

        errors = [eval.score_model(test_preds[j], test_data[j][1]) for j in range(4)]

        if inputs.score_train_vs_test:
            train_preds = [
                np.round(predictor.models[j].predict(training_data[j][0]), 5)
                for j in range(4)
            ]
            train_errors = [eval.score_model(train_preds[j], training_data[j][1]) for j in range(4)]
            for j, pos in enumerate(POSITIONS):
                ae_t, rmse_t, acc_t = test_errors = errors[j]
                ae_tr, rmse_tr, acc_tr = train_errors[j]
                print(f'GW{i} Test:  {pos}: AE: {ae_t:.3f}, RMSE: {rmse_t:.3f}, ACC: {acc_t*100:.2f}%')
                print(f'GW{i} Train: {pos}: AE: {ae_tr:.3f}, RMSE: {rmse_tr:.3f}, ACC: {acc_tr*100:.2f}%')

        avg_e   = sum(e[0] for e in errors) / 4
        avg_mse = sum(e[1] for e in errors) / 4
        avg_acc = sum(e[2] for e in errors) / 4
        count += 1
        total_e += avg_e
        total_rmse += avg_mse
        total_aa += avg_acc
        print(f'Count: {count}, AE: {avg_e:.2f}, RMSE: {np.sqrt(avg_mse):.2f}, Accuracy: {avg_acc*100:.2f}%')

        print(f'Generating {season} GW{i} Predictions...', end='\r')
        player_names, predictions = vastaav.get_player_predictions(season, i - predict_weeks, i, predictor.models)
        clean_predictions = predictor.to_dataframes(player_names, predictions)

        if 38 - i > 1:
            clean_predictions = vastaav.post_model_weightings_for_next_gw(clean_predictions, i - 1)

        if inputs.save:
            eval.export_tsv(clean_predictions, season, i)

        if inputs.plot_predictions:
            eval.plot_predictions(
                [p for p in test_preds],
                test_data,
                i,
            )

    if repeat > 1:
        print(
            f'Total Count: {count}, '
            f'Average AE: {total_e/count:.2f}, '
            f'Average RMSE: {np.sqrt(total_rmse/count):.2f}, '
            f'Average ACC: {total_aa/count*100:.2f}%'
        )


if __name__ == '__main__':
    main()
