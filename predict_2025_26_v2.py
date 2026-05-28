#!/usr/bin/env python3
"""
Improved 2025-26 predictions using recent-form weighted averages.
No sklearn required - pure pandas/numpy approach.

Strategy:
- Train on 2020-25 data
- Weight recent GWs (last 10 GWs) more heavily
- Per-player form tracking
- Compare vs actual 2025-26
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

        for gw_file in sorted(gws_dir.glob('gw[0-9]*.csv')):
            if gw_file.name == 'merged_gw.csv':
                continue

            gw_num = int(gw_file.stem.replace('gw', ''))
            df = pd.read_csv(gw_file, low_memory=False)

            cols_to_keep = [
                'name', 'position', 'team', 'total_points',
                'minutes', 'goals_scored', 'assists', 'clean_sheets',
                'saves', 'bps', 'influence', 'creativity', 'threat',
                'selected', 'transfers_in', 'transfers_out', 'value'
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

        cols_to_keep = ['name', 'position', 'total_points', 'minutes']
        available_cols = [c for c in cols_to_keep if c in df.columns]
        df = df[available_cols].copy()
        df['GW'] = gw_num

        all_data.append(df)

    result = pd.concat(all_data, ignore_index=True)
    print(f"  Loaded {len(result)} records from {len(all_data)} gameweeks")
    return result

def build_form_model(hist_data):
    """Build per-player form models using recent-weighted averages."""
    print("\nBuilding per-player form models (recent-weighted)")

    models = {}

    for pos in POSITIONS:
        pos_data = hist_data[hist_data['position'] == pos].copy()

        # Per-player recent form (last 10 GWs per season)
        player_form = {}

        for player_name in pos_data['name'].unique():
            player_data = pos_data[pos_data['name'] == player_name].sort_values(['season', 'GW'])

            if len(player_data) < 5:
                continue

            # Recent appearances (last 10 GWs globally)
            recent = player_data.tail(10)

            # Exclude zero-minute (benched) appearances for form
            appeared = recent[recent['minutes'] > 0]

            if len(appeared) == 0:
                # Never played recently, use overall
                avg_points = player_data[player_data['minutes'] > 0]['total_points'].mean()
                consistency = player_data[player_data['minutes'] > 0]['total_points'].std()
            else:
                # Weight recent appearances more heavily (exponential decay)
                weights = np.exp(np.linspace(-2, 0, len(appeared)))
                weights = weights / weights.sum()

                avg_points = np.average(
                    appeared['total_points'].values,
                    weights=weights
                )
                consistency = appeared['total_points'].std()

            player_form[player_name] = {
                'avg': avg_points if not np.isnan(avg_points) else 0,
                'std': consistency if not np.isnan(consistency) else 0,
                'appearances': len(appeared),
                'overall_mean': player_data['total_points'].mean()
            }

        models[pos] = {
            'player_form': player_form,
            'position_mean': pos_data['total_points'].mean(),
            'position_std': pos_data['total_points'].std()
        }

        print(f"  {pos}: {len(player_form)} players with form data")

    return models

def predict_2025_26(actual_2025_26, models):
    """Generate predictions for 2025-26 using player form models."""
    print("\nGenerating 2025-26 predictions")

    actual_2025_26 = actual_2025_26.copy()
    predictions = []

    for _, row in actual_2025_26.iterrows():
        player_name = row['name']
        position = row['position']

        model = models[position]

        if player_name in model['player_form']:
            form = model['player_form'][player_name]
            # Use recent form, with fallback to overall mean
            xp = form['avg'] if form['appearances'] >= 3 else form['overall_mean'] * 0.8
        else:
            # Unknown player, use position average
            xp = model['position_mean'] * 0.9

        # Clip to FPL xP scale [0, 10]
        xp = np.clip(xp, 0, 10)
        predictions.append(xp)

    actual_2025_26['xp_pred'] = predictions
    return actual_2025_26

def evaluate(actual_2025_26):
    """Compute evaluation metrics."""
    print("\n" + "="*70)
    print("EVALUATION: 2025-26 Form-Weighted Predictions vs Actuals")
    print("="*70)

    results = []

    for pos in POSITIONS:
        pos_actual = actual_2025_26[actual_2025_26['position'] == pos]

        actual = pos_actual['total_points'].values
        pred = pos_actual['xp_pred'].values

        # Filter out zero-minute appearances (benched players)
        played_mask = pos_actual['minutes'].fillna(0) > 0
        actual_played = actual[played_mask]
        pred_played = pred[played_mask]

        if len(actual_played) == 0:
            continue

        rmse = np.sqrt(np.mean((actual_played - pred_played) ** 2))
        mae = np.mean(np.abs(actual_played - pred_played))

        # R² for played only
        mean_actual = np.mean(actual_played)
        ss_tot = np.sum((actual_played - mean_actual) ** 2)
        ss_res = np.sum((actual_played - pred_played) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Correlation
        if len(actual_played) > 2:
            try:
                from scipy.stats import spearmanr
                spearman, _ = spearmanr(actual_played, pred_played)
            except:
                spearman = np.corrcoef(actual_played, pred_played)[0, 1]
        else:
            spearman = 0

        results.append({
            'position': pos,
            'samples': len(pos_actual),
            'played': len(actual_played),
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'spearman': spearman if not np.isnan(spearman) else 0,
            'actual_mean': actual_played.mean(),
            'pred_mean': pred_played.mean()
        })

        print(f"\n{pos}:")
        print(f"  Total samples: {len(pos_actual)}, Played: {len(actual_played)}")
        print(f"  RMSE: {rmse:.4f}")
        print(f"  MAE: {mae:.4f}")
        print(f"  R²: {r2:.4f}")
        print(f"  Spearman: {spearman:.4f}" if not np.isnan(spearman) else "  Spearman: N/A")
        print(f"  Actual mean: {actual_played.mean():.2f}, Predicted mean: {pred_played.mean():.2f}")

    return pd.DataFrame(results)

def main():
    print("="*70)
    print("2025-26 SEASON PREDICTION (FORM-WEIGHTED)")
    print("="*70)
    print(f"Train on: {HIST_SEASONS}")
    print(f"Predict: {PREDICT_SEASON}")

    # Load data
    hist_data = load_all_gw_data(HIST_SEASONS)
    actual_2025_26 = load_2025_26_actual()

    # Fill NaN values
    for col in ['minutes', 'total_points']:
        hist_data[col] = hist_data[col].fillna(0)
        actual_2025_26[col] = actual_2025_26[col].fillna(0)

    # Build form models
    models = build_form_model(hist_data)

    # Predict
    actual_2025_26 = predict_2025_26(actual_2025_26, models)

    # Evaluate
    results_df = evaluate(actual_2025_26)

    # Save
    os.makedirs('.planning/phases/10-model-retraining', exist_ok=True)
    results_df.to_csv('.planning/phases/10-model-retraining/2025-26-formweighted-analysis.csv', index=False)

    print("\n" + "="*70)
    print("Summary Table:")
    print("="*70)
    print(results_df.to_string(index=False))

    print(f"\nResults saved to: .planning/phases/10-model-retraining/2025-26-formweighted-analysis.csv")
    print("="*70)
    print("\nNext: Use Phase 10 Airflow for live 2026-27 season (August 2026)")

if __name__ == '__main__':
    main()
