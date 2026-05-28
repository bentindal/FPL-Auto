#!/usr/bin/env python3
"""
Fetch and ingest missing FPL data from two Kaggle datasets:

Part A — calvinrostanto/fantasy-premier-league-2025-2026
  Season-level totals. Back-calculates synthetic GW30-37 CSVs via:
    GW30-37_total = season_total − GW1-29_sum − GW38
  Each synthetic GW gets 1/8th of the remainder, per player.

Part B — reevebarreto/fantasy-premier-league-player-data-2016-2024
  Per-GW data for 2016-17 through 2023-24. Writes vastaav-format GW CSVs
  for seasons 2016-21 (seasons not already present in data/).

Setup:
  pip install "kagglehub[pandas-datasets]==0.3.6"
  export KAGGLE_KEY=<your-key>
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from difflib import get_close_matches

DATA_DIR = Path('data')
MISSING_GWS = list(range(30, 38))   # GW30-37
SEASON_2526 = '2025-26'

# Columns that data.py reads from GW CSV files (get_gw_data _cols list)
REQUIRED_COLS = [
    'name', 'position', 'team', 'assists', 'bps', 'clean_sheets', 'creativity',
    'goals_conceded', 'goals_scored', 'ict_index', 'influence', 'minutes',
    'own_goals', 'penalties_missed', 'penalties_saved', 'red_cards', 'saves',
    'threat', 'total_points', 'yellow_cards', 'selected', 'was_home', 'value',
]

# Numeric stats that can be summed/back-calculated from season totals
BACK_CALC_COLS = [
    'total_points', 'goals_scored', 'assists', 'minutes', 'clean_sheets',
    'goals_conceded', 'own_goals', 'penalties_saved', 'penalties_missed',
    'saves', 'yellow_cards', 'red_cards', 'bonus', 'bps', 'influence',
    'creativity', 'threat', 'ict_index', 'starts',
    'tackles', 'clearances_blocks_interceptions', 'recoveries', 'defensive_contribution',
    'transfers_in', 'transfers_out',
]

CALVINROSTANTO_COL_MAP = {
    'player_name': 'name',
    'club_name': 'team',
    'position_name': 'position',
    'selected_by_percent': 'selected',
    'minutes': 'minutes',
    'points': 'total_points',    # not present — handled via total_points direct
}

REEVEBARRETO_COL_MAP = {
    'minutes_played': 'minutes',
    'points': 'total_points',
    'gameweek': 'GW',
}

# Seasons from reevebarreto not already in data/
HIST_SEASONS_TO_WRITE = ['2016/17', '2017/18', '2018/19', '2019/20', '2020/21']
SEASON_FORMAT = lambda s: s.replace('/', '-')   # '2016/17' -> '2016-17'


def load_kaggle_dataset(dataset_id, file_path=''):
    import kagglehub
    from kagglehub import KaggleDatasetAdapter
    print(f'Loading {dataset_id}...')
    return kagglehub.load_dataset(KaggleDatasetAdapter.PANDAS, dataset_id, file_path)


def load_kaggle_download(dataset_id):
    """Download dataset files and return path (for datasets that need direct file access)."""
    import kagglehub
    path = kagglehub.dataset_download(dataset_id)
    return Path(path)


def load_gw_sum(season, gws):
    """Sum per-player stats across a list of GWs. Returns DataFrame indexed by name."""
    dfs = []
    gw_dir = DATA_DIR / season / 'gws'
    for gw in gws:
        f = gw_dir / f'gw{gw}.csv'
        if not f.exists():
            continue
        df = pd.read_csv(f, low_memory=False)
        num_cols = [c for c in BACK_CALC_COLS if c in df.columns]
        df = df[['name'] + num_cols].copy()
        dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    combined = pd.concat(dfs, ignore_index=True)
    return combined.groupby('name')[BACK_CALC_COLS].sum(min_count=1).reset_index()


def fuzzy_match_names(kaggle_names, vastaav_names):
    """Return dict mapping kaggle_name -> vastaav_name via close match."""
    vastaav_lower = {n.lower(): n for n in vastaav_names}
    mapping = {}
    for kname in kaggle_names:
        kl = kname.lower()
        # Try exact match first
        if kl in vastaav_lower:
            mapping[kname] = vastaav_lower[kl]
            continue
        # Fuzzy match
        matches = get_close_matches(kl, vastaav_lower.keys(), n=1, cutoff=0.75)
        if matches:
            mapping[kname] = vastaav_lower[matches[0]]
    return mapping


def part_a_fill_gw30_37():
    """Back-calculate GW30-37 from calvinrostanto season totals."""
    print('\n=== Part A: Fill GW30-37 from calvinrostanto season totals ===')

    # Check which missing GWs still need files
    gw_dir = DATA_DIR / SEASON_2526 / 'gws'
    still_missing = [gw for gw in MISSING_GWS if not (gw_dir / f'gw{gw}.csv').exists()]
    if not still_missing:
        print('  All GW30-37 files already exist, skipping.')
        return

    # Load season totals from Kaggle
    dl_path = load_kaggle_download('calvinrostanto/fantasy-premier-league-2025-2026')
    season_df = pd.read_csv(dl_path / 'fpl_player_statistics.csv')
    print(f'  Season totals: {len(season_df)} players')

    # Rename to vastaav format
    season_df = season_df.rename(columns={
        'player_name': 'name',
        'club_name': 'team',
        'position_name': 'position',
        'selected_by_percent': 'selected',
        'now_cost': 'value',
    })
    season_df['value'] = (season_df['value'] * 10).round().astype(int)
    season_df['position'] = season_df['position'].replace({'GKP': 'GK'})

    # Join on element (global FPL player ID) to get vastaav canonical names.
    # This replaces fragile fuzzy name matching that drops ~13% of players.
    gw_dir = DATA_DIR / SEASON_2526 / 'gws'
    elem_to_name = {}
    for gw_f in sorted(gw_dir.glob('gw[0-9]*.csv')):
        try:
            ref = pd.read_csv(gw_f, usecols=['element', 'name'])
            elem_to_name.update(ref.drop_duplicates('element').set_index('element')['name'].to_dict())
        except (ValueError, KeyError):
            continue
    if elem_to_name and 'element' in season_df.columns:
        before = len(season_df)
        season_df['name'] = season_df['element'].map(elem_to_name).fillna(season_df['name'])
        matched = season_df['element'].isin(elem_to_name).sum()
        print(f'  Matched {matched}/{before} players via element ID join')
    else:
        # Fallback: fuzzy match (element column absent from calvinrostanto data)
        vastaav_players_df = pd.read_csv(DATA_DIR / SEASON_2526 / 'cleaned_players.csv')
        vastaav_players_df['name'] = vastaav_players_df['first_name'] + ' ' + vastaav_players_df['second_name']
        vastaav_names = vastaav_players_df['name'].tolist()
        name_map = fuzzy_match_names(season_df['name'].tolist(), vastaav_names)
        season_df['name'] = season_df['name'].map(name_map).fillna(season_df['name'])
        print(f'  Matched {len(name_map)}/{len(season_df)} player names (fuzzy fallback)')

    # Sum GW1-29 and GW38 for each player
    gw1_29_sum = load_gw_sum(SEASON_2526, list(range(1, 30)))
    gw38_sum = load_gw_sum(SEASON_2526, [38])
    known_sum = pd.merge(gw1_29_sum, gw38_sum, on='name', how='outer', suffixes=('_1_29', '_38'))

    # Back-calculate GW30-37 totals per player
    remainder_df = pd.merge(season_df, known_sum, on='name', how='left')
    for col in BACK_CALC_COLS:
        if col not in remainder_df.columns:
            continue
        col_129 = f'{col}_1_29' if f'{col}_1_29' in remainder_df.columns else col
        col_38 = f'{col}_38' if f'{col}_38' in remainder_df.columns else None

        season_val = remainder_df[col].fillna(0)
        known_val = remainder_df.get(col_129, pd.Series(0, index=remainder_df.index)).fillna(0)
        if col_38:
            known_val += remainder_df.get(col_38, pd.Series(0, index=remainder_df.index)).fillna(0)

        remainder_df[f'{col}_remainder'] = (season_val - known_val).clip(lower=0)

    # Write one synthetic CSV per missing GW (1/8th of remainder per GW)
    for gw in still_missing:
        row_data = {}
        for col in BACK_CALC_COLS:
            rem_col = f'{col}_remainder'
            if rem_col in remainder_df.columns:
                row_data[col] = (remainder_df[rem_col] / 8).round(2)
            else:
                row_data[col] = 0.0

        gw_df = pd.DataFrame(row_data)
        gw_df['name'] = remainder_df['name'].values
        gw_df['element'] = remainder_df['element'].values if 'element' in remainder_df.columns else 0
        gw_df['team'] = remainder_df['team'].values
        gw_df['position'] = remainder_df['position'].values
        gw_df['value'] = remainder_df['value'].values
        gw_df['selected'] = remainder_df['selected'].values
        gw_df['was_home'] = 0.5       # unknown for back-calculated GWs
        gw_df['xP'] = 0.0
        gw_df['round'] = gw
        gw_df['GW'] = gw

        # Drop rows with no meaningful data (players not in calvinrostanto)
        gw_df = gw_df[gw_df['minutes'] > 0].copy()

        out_path = gw_dir / f'gw{gw}.csv'
        gw_df.to_csv(out_path, index=False)
        print(f'  Wrote {out_path} ({len(gw_df)} rows)')

    print('Part A complete.')


def part_b_historical_seasons():
    """Convert reevebarreto per-GW data to vastaav format for 2016-21 seasons."""
    print('\n=== Part B: Write historical seasons from reevebarreto (2016-21) ===')

    # Check which seasons are already present
    seasons_to_write = [
        s for s in HIST_SEASONS_TO_WRITE
        if not (DATA_DIR / SEASON_FORMAT(s) / 'gws').exists()
    ]
    if not seasons_to_write:
        print('  All historical seasons already present, skipping.')
        return

    dl_path = load_kaggle_download('reevebarreto/fantasy-premier-league-player-data-2016-2024')
    csv_path = dl_path / 'FPL Player Stats(2016-2024).csv'
    print(f'  Loading {csv_path}...')
    df = pd.read_csv(csv_path, low_memory=False)

    # Rename to vastaav format
    df = df.rename(columns=REEVEBARRETO_COL_MAP)

    for season_slash in seasons_to_write:
        season = SEASON_FORMAT(season_slash)
        season_df = df[df['season'] == season_slash].copy()
        if season_df.empty:
            print(f'  No data for {season_slash}, skipping.')
            continue

        season_dir = DATA_DIR / season
        gw_dir = season_dir / 'gws'
        gw_dir.mkdir(parents=True, exist_ok=True)
        print(f'  Writing {season}: {len(season_df)} rows across {season_df["GW"].nunique()} GWs')

        # Write per-GW CSVs
        for gw, gw_df in season_df.groupby('GW'):
            out = gw_dir / f'gw{int(gw)}.csv'
            gw_df.drop(columns=['GW', 'season', 'Unnamed: 0', 'opponent', 'result'],
                       errors='ignore').to_csv(out, index=False)

        # Write minimal cleaned_players.csv so FplData can initialise
        players = (
            season_df[['name', 'position']]
            .drop_duplicates('name')
            .assign(
                first_name=lambda d: d['name'].str.split().str[0],
                second_name=lambda d: d['name'].str.split().str[1:].str.join(' '),
                element_type=lambda d: d['position'],
                goals_scored=0, assists=0, total_points=0, minutes=0,
                goals_conceded=0, creativity=0.0, influence=0.0, threat=0.0,
                bonus=0, bps=0, ict_index=0.0, clean_sheets=0, red_cards=0,
                yellow_cards=0, selected_by_percent=0.0, now_cost=50,
                value_per_m=0.0,
            )
        )
        players.drop(columns=['name', 'position']).to_csv(
            season_dir / 'cleaned_players.csv', index=False
        )

        # Write minimal teams.csv with dummy strength values
        teams = (
            season_df[['team']]
            .drop_duplicates()
            .reset_index(drop=True)
            .assign(
                code=lambda d: d.index + 1,
                draw=0, form='', id=lambda d: d.index + 1, loss=0,
                played=0, points=0, position=0, short_name=lambda d: d['team'].str[:3].str.upper(),
                strength=3, team_division='', unavailable=False, win=0, link_url='',
                strength_overall_home=1200, strength_overall_away=1200,
                strength_attack_home=1200, strength_attack_away=1200,
                strength_defence_home=1200, strength_defence_away=1200,
                pulse_id=lambda d: d.index + 1,
            )
            .rename(columns={'team': 'name'})
        )
        teams.to_csv(season_dir / 'teams.csv', index=False)

        # Stub player_idlist.csv (needed for FplData init check)
        pd.DataFrame({'id': [], 'name': []}).to_csv(
            season_dir / 'player_idlist.csv', index=False
        )

        print(f'    → {season}: GW CSVs, cleaned_players.csv, teams.csv written')

    print('Part B complete.')


def main():
    print('=== fetch_missing_data.py ===')
    print('Requires: pip install "kagglehub[pandas-datasets]==0.3.6"')
    print('Requires: KAGGLE_KEY env var set\n')

    if not os.environ.get('KAGGLE_KEY'):
        print('ERROR: Set KAGGLE_KEY environment variable before running.')
        sys.exit(1)

    part_a_fill_gw30_37()
    part_b_historical_seasons()

    print('\nDone. Next steps:')
    print('  python model.py -season 2025-26 -save -target_gw 1 -repeat 38 -retrain_every 5')
    print('  python manager.py -season 2025-26')


if __name__ == '__main__':
    main()
