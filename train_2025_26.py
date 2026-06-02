#!/usr/bin/env python3
"""
Train position-specific ensemble models on past 5 seasons (2020-21 through 2024-25)
and generate predictions for 2025-26 season for validation.
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path
import sys

# Configuration
SEASONS_TO_TRAIN = ['2020-21', '2021-22', '2022-23', '2023-24', '2024-25']
PREDICT_SEASON = '2025-26'
POSITIONS = ['GK', 'DEF', 'MID', 'FWD']
DATA_DIR = Path('/Users/bentindal/Desktop/coding/FPL-Auto/data')
OUTPUT_DIR = Path('/Users/bentindal/Desktop/coding/FPL-Auto/predictions') / PREDICT_SEASON

def load_historical_data():
    """Load cleaned historical data for training seasons."""
    print("Loading historical data from cleaned_merged_seasons.csv...")

    df = pd.read_csv(DATA_DIR / 'cleaned_merged_seasons.csv')

    # Filter to training seasons
    df['season'] = df['season_x'].astype(str)
    df = df[df['season'].isin(SEASONS_TO_TRAIN)].copy()

    print(f"  Loaded {len(df)} records across seasons: {SEASONS_TO_TRAIN}")
    print(f"  Seasons in data: {df['season'].unique()}")
    print(f"  Columns: {list(df.columns)}")

    return df

def load_2025_26_data():
    """Load actual 2025-26 data for validation."""
    print("\nLoading 2025-26 actual results...")

    gws_dir = DATA_DIR / PREDICT_SEASON / 'gws'
    season_data = []

    # Load all GW files
    gw_files = sorted([f for f in gws_dir.glob('gw*.csv') if f.name != 'merged_gw.csv'])

    for gw_file in gw_files:
        gw_num = int(gw_file.stem.replace('gw', ''))
        df = pd.read_csv(gw_file)
        df['GW'] = gw_num
        df['season'] = PREDICT_SEASON
        season_data.append(df)

    result = pd.concat(season_data, ignore_index=True)
    print(f"  Loaded {len(result)} records from {len(gw_files)} gameweeks")
    print(f"  Columns: {list(result.columns)}")

    return result

def prepare_training_data(df):
    """Prepare data for model training."""
    print("\nPreparing training data...")

    # Select relevant features
    feature_cols = [
        'minutes', 'goals_scored', 'assists', 'clean_sheets',
        'saves', 'total_points', 'bps', 'influence', 'creativity', 'threat',
        'ict_index', 'selected', 'transfers_in', 'transfers_out'
    ]

    # Filter to available columns
    available_cols = [col for col in feature_cols if col in df.columns]

    X = df[available_cols + ['position', 'GW', 'season']].copy()
    y = df['total_points'].copy()

    # Fill NaN values
    for col in available_cols:
        X[col] = X[col].fillna(0)

    print(f"  Features: {available_cols}")
    print(f"  Records: {len(X)} (y: {len(y)})")
    print(f"  Target distribution:")
    print(f"    Min: {y.min()}, Max: {y.max()}, Mean: {y.mean():.2f}, Std: {y.std():.2f}")

    return X, y, available_cols

def train_position_models(X, y, feature_cols):
    """Train position-specific ensemble models."""
    print("\nTraining position-specific ensemble models...")

    models = {}

    try:
        from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline

        position_hyperparams = {
            'GK': {'gb_depth': 4, 'rf_depth': 4},
            'DEF': {'gb_depth': 5, 'rf_depth': 5},
            'MID': {'gb_depth': 5, 'rf_depth': 5},
            'FWD': {'gb_depth': 6, 'rf_depth': 6}
        }

        for pos in POSITIONS:
            print(f"\n  Training {pos}...")

            # Filter to position
            pos_mask = X['position'] == pos
            X_pos = X[pos_mask][feature_cols]
            y_pos = y[pos_mask]

            if len(X_pos) == 0:
                print(f"    WARNING: No data for {pos}, skipping")
                continue

            print(f"    Samples: {len(X_pos)}, Mean target: {y_pos.mean():.2f}")

            # Create ensemble pipeline
            params = position_hyperparams[pos]

            # GradientBoosting component
            gb = GradientBoostingRegressor(
                learning_rate=0.05,
                max_depth=params['gb_depth'],
                n_estimators=500,
                random_state=42
            )

            # RandomForest component
            rf = RandomForestRegressor(
                max_depth=params['rf_depth'],
                n_estimators=500,
                random_state=42,
                n_jobs=-1
            )

            # Train both
            gb.fit(X_pos, y_pos)
            rf.fit(X_pos, y_pos)

            # Store models and training info
            models[pos] = {
                'gb': gb,
                'rf': rf,
                'mean': y_pos.mean(),
                'std': y_pos.std(),
                'samples': len(X_pos)
            }

            # Evaluate on training set
            gb_pred = gb.predict(X_pos)
            rf_pred = rf.predict(X_pos)
            ensemble_pred = (gb_pred + rf_pred) / 2

            from sklearn.metrics import mean_squared_error, r2_score
            gb_rmse = np.sqrt(mean_squared_error(y_pos, gb_pred))
            rf_rmse = np.sqrt(mean_squared_error(y_pos, rf_pred))
            ens_rmse = np.sqrt(mean_squared_error(y_pos, ensemble_pred))

            print(f"    GB RMSE:  {gb_rmse:.4f}")
            print(f"    RF RMSE:  {rf_rmse:.4f}")
            print(f"    Ens RMSE: {ens_rmse:.4f}")
            print(f"    R²:       {r2_score(y_pos, ensemble_pred):.4f}")

        print(f"\n  ✓ Trained {len(models)} position models")
        return models

    except ImportError as e:
        print(f"  ERROR: sklearn not installed: {e}")
        print(f"  Skipping model training")
        return None

def generate_2025_26_predictions(data_2025_26, models, feature_cols):
    """Generate predictions for 2025-26 season."""
    if models is None:
        print("\nSkipping prediction generation (no models)")
        return None

    print("\nGenerating 2025-26 predictions...")

    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    from scipy.stats import spearmanr

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    predictions_summary = []

    for pos in POSITIONS:
        if pos not in models:
            print(f"  {pos}: No model, skipping")
            continue

        print(f"\n  {pos}:")

        # Filter to position
        pos_mask = data_2025_26['position'] == pos
        X_pred = data_2025_26[pos_mask][feature_cols].fillna(0)
        y_actual = data_2025_26[pos_mask]['total_points']

        if len(X_pred) == 0:
            print(f"    No 2025-26 data for {pos}")
            continue

        print(f"    Samples: {len(X_pred)}")

        # Generate ensemble predictions
        gb_pred = models[pos]['gb'].predict(X_pred)
        rf_pred = models[pos]['rf'].predict(X_pred)
        ensemble_pred = (gb_pred + rf_pred) / 2

        # Clip to valid range [0, 10] for xP-style predictions
        ensemble_pred = np.clip(ensemble_pred, 0, 10)

        # Compute metrics
        rmse = np.sqrt(mean_squared_error(y_actual, ensemble_pred))
        mae = mean_absolute_error(y_actual, ensemble_pred)
        r2 = r2_score(y_actual, ensemble_pred)

        try:
            spearman, _ = spearmanr(y_actual, ensemble_pred)
        except:
            spearman = 0

        predictions_summary.append({
            'position': pos,
            'samples': len(X_pred),
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'spearman': spearman
        })

        print(f"    RMSE:     {rmse:.4f}")
        print(f"    MAE:      {mae:.4f}")
        print(f"    R²:       {r2:.4f}")
        print(f"    Spearman: {spearman:.4f}")

    # Summary table
    if predictions_summary:
        summary_df = pd.DataFrame(predictions_summary)
        print("\n" + "="*70)
        print("PREDICTION SUMMARY: 2025-26 Season")
        print("="*70)
        print(summary_df.to_string(index=False))
        print("="*70)

        # Save summary
        summary_df.to_csv(OUTPUT_DIR / 'prediction_metrics.csv', index=False)
        print(f"\nMetrics saved to: {OUTPUT_DIR / 'prediction_metrics.csv'}")

    return summary_df

def main():
    print("="*70)
    print("2025-26 SEASON PREDICTION (VALIDATION)")
    print("Training on: " + ", ".join(SEASONS_TO_TRAIN))
    print("="*70)

    # Load data
    hist_data = load_historical_data()
    data_2025_26 = load_2025_26_data()

    # Prepare
    X, y, feature_cols = prepare_training_data(hist_data)

    # Train
    models = train_position_models(X, y, feature_cols)

    # Predict
    summary = generate_2025_26_predictions(data_2025_26, models, feature_cols)

    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70)

if __name__ == '__main__':
    main()
