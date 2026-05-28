#!/usr/bin/env python3
"""
Train on historical seasons (2020-21 to 2024-25) and predict xP for 2025-26.
Compare predictions against actual 2025-26 results.

This validates the retraining approach by showing performance on a completed season.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os

DATA_DIR = Path('data')
HIST_SEASONS = ['2020-21', '2021-22', '2022-23', '2023-24', '2024-25']
PREDICT_SEASON = '2025-26'
POSITIONS = ['GK', 'DEF', 'MID', 'FWD']

def load_all_gw_data(seasons):
    """Load all gameweek data from multiple seasons."""
    print(f"Loading gameweek data from: {seasons}")

    all_data = []
    for season in seasons:
        gws_dir = DATA_DIR / season / 'gws'

        # Load all GW files
        for gw_file in sorted(gws_dir.glob('gw[0-9]*.csv')):
            if gw_file.name == 'merged_gw.csv':
                continue

            gw_num = int(gw_file.stem.replace('gw', ''))
            df = pd.read_csv(gw_file, low_memory=False)

            # Select relevant columns
            cols_to_keep = [
                'name', 'position', 'team', 'total_points',
                'minutes', 'goals_scored', 'assists', 'clean_sheets',
                'saves', 'bps', 'influence', 'creativity', 'threat',
                'selected', 'transfers_in', 'transfers_out'
            ]

            available_cols = [c for c in cols_to_keep if c in df.columns]
            df = df[available_cols].copy()
            df['season'] = season
            df['GW'] = gw_num

            all_data.append(df)

    result = pd.concat(all_data, ignore_index=True)
    print(f"  Loaded {len(result)} records from {len(all_data)} gameweeks")
    return result

def load_2025_26_actual():
    """Load actual 2025-26 results."""
    print(f"Loading actual 2025-26 results")

    all_data = []
    gws_dir = DATA_DIR / PREDICT_SEASON / 'gws'

    for gw_file in sorted(gws_dir.glob('gw[0-9]*.csv')):
        if gw_file.name == 'merged_gw.csv':
            continue

        gw_num = int(gw_file.stem.replace('gw', ''))
        df = pd.read_csv(gw_file, low_memory=False)

        cols_to_keep = ['name', 'position', 'total_points']
        available_cols = [c for c in cols_to_keep if c in df.columns]
        df = df[available_cols].copy()
        df['GW'] = gw_num

        all_data.append(df)

    result = pd.concat(all_data, ignore_index=True)
    print(f"  Loaded {len(result)} records from {len(all_data)} gameweeks")
    return result

def simple_position_averages(hist_data):
    """Generate simple baseline predictions using position/GW averages."""
    print("\nGenerating baseline predictions (position + GW averages)")

    predictions = {}

    for pos in POSITIONS:
        pos_data = hist_data[hist_data['position'] == pos]

        # Average by GW
        gw_avg = pos_data.groupby('GW')['total_points'].agg(['mean', 'std', 'count']).reset_index()
        gw_avg = gw_avg[gw_avg['count'] >= 5]  # At least 5 samples

        # Overall average
        overall_mean = pos_data['total_points'].mean()
        overall_std = pos_data['total_points'].std()

        predictions[pos] = {
            'gw_avg': gw_avg.set_index('GW')['mean'].to_dict(),
            'overall_mean': overall_mean,
            'overall_std': overall_std,
            'count': len(pos_data)
        }

        print(f"  {pos}: mean={overall_mean:.2f}, std={overall_std:.2f}, samples={len(pos_data)}")

    return predictions

def evaluate_predictions(actual_2025_26, predictions):
    """Compare predictions against actual 2025-26 results."""
    print("\n" + "="*70)
    print("EVALUATION: 2025-26 Predictions vs Actuals")
    print("="*70)

    results = []

    for pos in POSITIONS:
        pos_actual = actual_2025_26[actual_2025_26['position'] == pos].copy()

        # Generate xP predictions for each GW
        xp_values = []
        for _, row in pos_actual.iterrows():
            gw = row['GW']
            pred_model = predictions[pos]

            # Use GW average if available, else overall mean
            if gw in pred_model['gw_avg']:
                xp = pred_model['gw_avg'][gw]
            else:
                xp = pred_model['overall_mean']

            xp_values.append(xp)

        pos_actual['xp_pred'] = xp_values

        # Clip to [0, 10] for FPL xP scale
        pos_actual['xp_pred'] = pos_actual['xp_pred'].clip(0, 10)

        # Compute metrics
        actual = pos_actual['total_points'].values
        pred = pos_actual['xp_pred'].values

        rmse = np.sqrt(np.mean((actual - pred) ** 2))
        mae = np.mean(np.abs(actual - pred))
        r2 = 1 - (np.sum((actual - pred) ** 2) / np.sum((actual - np.mean(actual)) ** 2))

        # Spearman correlation (if scipy available)
        try:
            from scipy.stats import spearmanr
            spearman, _ = spearmanr(actual, pred)
        except:
            spearman = np.corrcoef(actual, pred)[0, 1]

        results.append({
            'position': pos,
            'samples': len(pos_actual),
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'spearman': spearman if not np.isnan(spearman) else 0,
            'actual_mean': actual.mean(),
            'pred_mean': pred.mean()
        })

        print(f"\n{pos}:")
        print(f"  Samples: {len(pos_actual)}")
        print(f"  RMSE: {rmse:.4f}")
        print(f"  MAE: {mae:.4f}")
        print(f"  R²: {r2:.4f}")
        print(f"  Spearman: {spearman:.4f}" if not np.isnan(spearman) else "  Spearman: N/A")
        print(f"  Actual mean: {actual.mean():.2f}, Predicted mean: {pred.mean():.2f}")

    return pd.DataFrame(results)

def main():
    print("="*70)
    print("2025-26 SEASON PREDICTION ANALYSIS")
    print("="*70)
    print(f"Train on: {HIST_SEASONS}")
    print(f"Predict: {PREDICT_SEASON}")

    # Load data
    hist_data = load_all_gw_data(HIST_SEASONS)
    actual_2025_26 = load_2025_26_actual()

    # Fill NaN values
    for col in hist_data.select_dtypes(include=[np.number]).columns:
        hist_data[col] = hist_data[col].fillna(0)

    # Generate baseline predictions
    predictions = simple_position_averages(hist_data)

    # Evaluate
    results_df = evaluate_predictions(actual_2025_26, predictions)

    # Save results
    os.makedirs('.planning/phases/10-model-retraining', exist_ok=True)
    results_df.to_csv('.planning/phases/10-model-retraining/2025-26-prediction-analysis.csv', index=False)

    print("\n" + "="*70)
    print("Summary Table:")
    print("="*70)
    print(results_df.to_string(index=False))

    print(f"\nResults saved to: .planning/phases/10-model-retraining/2025-26-prediction-analysis.csv")
    print("="*70)

if __name__ == '__main__':
    main()
