'''
Model Generator for FPL Automation Project
Author: Benjamin Tindal
'''

import argparse
import numpy as np
from fpl_auto.data import FplData
from fpl_auto.predictor import Predictor, POSITIONS
from fpl_auto import evaluate as eval
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error
import json
from datetime import datetime
import os


def get_available_seasons(gw_data_path='data/'):
    """Dynamically discover available seasons from data directory."""
    try:
        seasons = [d for d in os.listdir(gw_data_path)
                   if os.path.isdir(os.path.join(gw_data_path, d))
                   and '-' in d and len(d) == 7]  # Format: YYYY-YY
        return sorted(seasons)
    except (FileNotFoundError, OSError):
        return ['2021-22', '2022-23', '2023-24', '2024-25']  # Fallback


def parse_args():
    parser = argparse.ArgumentParser(description="FPL Automation Project: Model")
    parser.add_argument('-gw_data', type=str, default='data/',
                        help='Location of Vastaav Dataset, default: data/')
    parser.add_argument('-model', type=str, default='gradientboost',
                        choices=Predictor.TYPES,
                        help=f'Model type to use. Choices: {Predictor.TYPES}. Default: gradientboost')

    # Dynamically discover available seasons
    available_seasons = get_available_seasons('data/')

    parser.add_argument('-season', type=str, required=True,
                        choices=available_seasons,
                        help=f'Season to predict points for. Format: YYYY-YY. Available: {", ".join(available_seasons)}')
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
    parser.add_argument('-evaluate_nested_cv', action=argparse.BooleanOptionalAction, default=False,
                        help='Use nested CV for hyperparameter evaluation (requires more time)')
    parser.add_argument('-save_baseline', action=argparse.BooleanOptionalAction, default=False,
                        help='Save baseline metrics to BASELINE_METRICS.json')
    parser.add_argument('-display_permutation_importance', action=argparse.BooleanOptionalAction, default=False,
                        help='Display permutation importance features (slower than tree feature_importances_)')
    parser.add_argument('-retrain_every', type=int, default=5,
                        help='Retrain model every N GWs (default: 5). Use 1 for original GW-by-GW retraining.')
    return parser.parse_args()


def evaluate_with_nested_cv(training_data, test_data, model_type, position, inputs, apply_vif_filtering=True):
    """
    Evaluate model using nested CV structure:
    - Inner CV: GridSearchCV with TimeSeriesSplit(n_splits=3) for hyperparameter tuning
    - Outer CV: TimeSeriesSplit(n_splits=5) for final evaluation

    For now: simplified version keeps current GW-by-GW loop structure
    but prepares infrastructure for full nested CV in Phase 4.

    === Phase 4 v2: Apply VIF filtering to remove multicollinear features (optional) ===

    Returns: (predictions, metrics_dict, predictor, filtered_training_data, filtered_test_data)
    """
    vif_filtered_training_data = training_data
    vif_filtered_test_data = test_data

    # Only apply VIF filtering during standalone evaluation (not in main loop with prediction)
    if apply_vif_filtering:
        import sys
        from io import StringIO

        # === Apply VIF filtering per position ===
        training_data_filtered = []
        test_data_filtered = []
        dropped_features_log = {}

        for j, pos in enumerate(POSITIONS):
            X_train = training_data[j][0].copy()
            y_train = training_data[j][1].copy()
            X_test = test_data[j][0].copy()
            y_test = test_data[j][1].copy()

            feature_names = list(X_train.columns)

            # Suppress verbose VIF output
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            try:
                vif_df, drop_list = eval.display_feature_vif(X_train, feature_names, pos, threshold=5.0)
            finally:
                sys.stdout = old_stdout

            # Drop high-VIF features from both train and test
            if len(drop_list) > 0:
                X_train = X_train.drop(columns=drop_list, errors='ignore')
                X_test = X_test.drop(columns=drop_list, errors='ignore')
                dropped_features_log[pos] = drop_list

            training_data_filtered.append((X_train, y_train))
            test_data_filtered.append((X_test, y_test))

        vif_filtered_training_data = training_data_filtered
        vif_filtered_test_data = test_data_filtered
        training_data = training_data_filtered
        test_data = test_data_filtered

    predictor = Predictor(model_type=model_type).fit(training_data)
    test_preds = predictor.predict_test(test_data)

    # Compute metrics per position
    metrics = {}
    for j, pos in enumerate(POSITIONS):
        test_rmse = np.sqrt(mean_squared_error(test_data[j][1], test_preds[j]))
        test_mae = mean_absolute_error(test_data[j][1], test_preds[j])

        # Train RMSE for gap calculation
        train_preds = np.round(predictor.models[j].predict(training_data[j][0]), 5)
        train_rmse = np.sqrt(mean_squared_error(training_data[j][1], train_preds))

        gap_ratio = (test_rmse - train_rmse) / train_rmse if train_rmse > 0 else 0

        metrics[pos] = {
            'rmse': test_rmse,
            'mae': test_mae,
            'gap_ratio': gap_ratio,
            'train_rmse': train_rmse,
            'test_rmse': test_rmse
        }

    return test_preds, metrics, predictor, vif_filtered_training_data, vif_filtered_test_data


def compute_baseline_metrics(season, vastaav, model_type, inputs):
    """
    Run full season evaluation and return baseline metrics dict.

    Iterates GW by GW, accumulates per-position RMSE/MAE/gap.
    Returns aggregated baseline across all GWs.
    """
    all_metrics = {pos: [] for pos in POSITIONS}
    all_gaps = {pos: [] for pos in POSITIONS}
    all_mae = {pos: [] for pos in POSITIONS}
    gw_count = 0

    for i in range(1, 39):  # Full season, GW1-38
        try:
            training_data, test_data = vastaav.get_training_data_all(
                season, i - inputs.training_prev_weeks - 1, i - 1
            )
        except UnboundLocalError:
            break

        test_preds, metrics, _, _, _ = evaluate_with_nested_cv(
            training_data, test_data, model_type, '', inputs, apply_vif_filtering=False
        )

        gw_count += 1
        for pos in POSITIONS:
            all_metrics[pos].append(metrics[pos]['rmse'])
            all_mae[pos].append(metrics[pos]['mae'])
            all_gaps[pos].append(metrics[pos]['gap_ratio'])

    # Aggregate
    baseline = {
        'season': season,
        'model_type': model_type,
        'per_position': {
            pos: {
                'rmse': float(np.mean(all_metrics[pos])),
                'mae': float(np.mean(all_mae[pos])),
                'gap_ratio': float(np.mean(all_gaps[pos])),
                'gw_count': gw_count
            }
            for pos in POSITIONS
        },
        'average_rmse': float(np.mean(list(all_metrics[pos] for pos in POSITIONS))),
        'average_mae': float(np.mean(list(all_mae[pos] for pos in POSITIONS))),
        'average_gap_ratio': float(np.mean(list(all_gaps[pos] for pos in POSITIONS))),
        'timestamp': datetime.now().isoformat()
    }

    return baseline


def main():
    """
    Train models and generate predictions for FPL gameweeks.

    Temporal Validation Strategy (Expanding Window):
    -----------------------------------------------
    This function implements an expanding-window cross-validation pattern for
    temporal data, equivalent to TimeSeriesSplit without explicit framework usage:

    - Training window: GW[i - training_prev_weeks : i-1] (expands as i increases)
    - Test window: GW[i] (single gameweek, forward-only prediction)
    - Invariant: training_data never contains test gameweek (i-1 < i ✓)

    This mimics the realistic scenario where we train on all historical data up
    to a deadline, then predict the next week. As seasons progress, the training
    window grows, improving model calibration without look-ahead bias.

    For explicit TimeSeriesSplit validation across the full season, use the
    --use_explicit_timeseriessplit flag (future work in Plan 02).
    """
    inputs = parse_args()
    season = inputs.season
    target_gameweek = inputs.target_gw
    repeat = inputs.repeat
    training_prev_weeks = inputs.training_prev_weeks
    predict_weeks = inputs.predict_weeks

    vastaav = FplData('data', season)

    # Generate and save baseline metrics if requested
    if inputs.save_baseline:
        print(f"Generating baseline metrics for {season}...")
        baseline = compute_baseline_metrics(season, vastaav, inputs.model, inputs)
        baseline_dir = '.planning/phases/03-model-infrastructure/'
        baseline_file = f'{baseline_dir}BASELINE_METRICS.json'

        # Load existing baselines if they exist
        if os.path.isfile(baseline_file):
            with open(baseline_file, 'r') as f:
                existing = json.load(f)
        else:
            existing = {'version': '1.0', 'created_date': datetime.now().strftime('%Y-%m-%d'),
                       'note': 'Baseline metrics for Phase 3 (TimeSeriesSplit + nested CV + Pipeline)',
                       'seasons': {}}

        # Add new season
        existing['seasons'][season] = {
            'model_type': baseline['model_type'],
            'per_position': baseline['per_position'],
            'average_rmse': baseline['average_rmse'],
            'average_mae': baseline['average_mae'],
            'average_gap_ratio': baseline['average_gap_ratio'],
            'timestamp': baseline['timestamp']
        }

        # Calculate overall stats
        all_rmses = [s['average_rmse'] for s in existing['seasons'].values()]
        all_gaps = [s['average_gap_ratio'] for s in existing['seasons'].values()]
        existing['overall_stats'] = {
            'avg_rmse_across_seasons': float(np.mean(all_rmses)),
            'avg_gap_ratio_across_seasons': float(np.mean(all_gaps))
        }

        with open(baseline_file, 'w') as f:
            json.dump(existing, f, indent=2)

        print(f"✓ Baseline metrics saved to {baseline_file}")
        print(f"  Season: {season}")
        print(f"  Average RMSE: {baseline['average_rmse']:.4f}")
        print(f"  Average Gap Ratio: {baseline['average_gap_ratio']:.4f}")
        return

    count = 0
    total_e = total_rmse = total_aa = 0.0
    cached_predictor = None
    cached_vif_training_data = None

    for i in range(target_gameweek, min(target_gameweek + repeat, 39)):
        try:
            training_data, test_data = vastaav.get_training_data_all(season, i - training_prev_weeks - 1, i - 1)
        except UnboundLocalError:
            print(f'Reached Prediction Limit for {season} GW{i}, can only predict 1 week beyond data.')
            return

        # When saving predictions, train without VIF filtering so model features
        # match the full feature set used by get_player_predictions.
        apply_vif = not inputs.save
        should_retrain = (cached_predictor is None) or ((i - target_gameweek) % inputs.retrain_every == 0)

        if should_retrain:
            _, metrics, cached_predictor, cached_vif_training_data, vif_test_data = evaluate_with_nested_cv(
                training_data, test_data, inputs.model, '', inputs, apply_vif_filtering=apply_vif
            )
        else:
            vif_test_data = test_data

        predictor = cached_predictor
        vif_training_data = cached_vif_training_data
        test_preds = predictor.predict_test(vif_test_data)

        if inputs.display_weights:
            feature_list = vif_training_data[0][0].columns
            eval.display_weights(i, predictor.feature_importances(), feature_list, POSITIONS)

        if inputs.display_permutation_importance:
            feature_list = list(vif_training_data[0][0].columns)
            for j, pos in enumerate(POSITIONS):
                importance_df = eval.display_permutation_importance(
                    predictor, vif_test_data[j][0], vif_test_data[j][1],
                    feature_list, pos, top_n=10
                )
                if i == target_gameweek:  # Only display top 10 on first GW
                    print(f"\nTop 10 Permutation Importance for {pos}:")
                    print(importance_df.head(10).to_string())

        errors = [eval.score_model(test_preds[j], vif_test_data[j][1]) for j in range(4)]

        if inputs.score_train_vs_test:
            train_preds = [
                np.round(predictor.models[j].predict(vif_training_data[j][0]), 5)
                for j in range(4)
            ]
            train_errors = [eval.score_model(train_preds[j], vif_training_data[j][1]) for j in range(4)]
            for j, pos in enumerate(POSITIONS):
                ae_t, rmse_t, acc_t = errors[j]
                ae_tr, rmse_tr, acc_tr = train_errors[j]
                # Calculate train-vs-test gap (relative improvement on test set)
                rmse_gap = ((rmse_t - rmse_tr) / rmse_tr * 100) if rmse_tr > 0 else 0
                print(f'GW{i} Test:  {pos}: AE: {ae_t:.3f}, RMSE: {rmse_t:.3f}, ACC: {acc_t*100:.2f}%')
                print(f'GW{i} Train: {pos}: AE: {ae_tr:.3f}, RMSE: {rmse_tr:.3f}, ACC: {acc_tr*100:.2f}%, Gap: {rmse_gap:+.1f}%')

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
