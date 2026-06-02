'''
Team Manager for FPL Automation Project
Author: Benjamin Tindal
'''

import argparse
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

import fpl_auto.team as team_module
from fpl_auto import evaluate as eval
from fpl_auto.strategies import (
    StrategyConfig, BASELINE_CURRENT, PHASE_8_OPTIMAL,
    INIT_GREEDY, INIT_TWO_TIER, INIT_ILP_XP, INIT_ILP_RATIO,
    INIT_ILP_PENALISED, INIT_ILP_CAPTAIN, INIT_ROLLING_HORIZON,
)


def parse_args():
    parser = argparse.ArgumentParser(description='FPL Automation Project: Team Manager')
    season_group = parser.add_mutually_exclusive_group(required=True)
    season_group.add_argument('-season', type=str,
                              help='Single season to simulate. Format: YYYY-YY e.g. 2021-22')
    season_group.add_argument('-seasons', type=str, nargs='+',
                              help='Multiple seasons to simulate in parallel. e.g. 2021-22 2022-23 2023-24')
    parser.add_argument('-start_gw', type=int, default=1,
                        help='Gameweek to start on, default 1')
    parser.add_argument('-repeat_until', type=int, default=38,
                        help='Last gameweek to simulate (inclusive), default 38')
    parser.add_argument('-starting_team', type=str, default='auto',
                        choices=['auto', 'custom_1'],
                        help='Initial team: auto = generate own team, default: auto')
    parser.add_argument('-strategy', type=str, default='baseline_current',
                        choices=['static', 'baseline_current', 'phase_8_optimal', 'conservative', 'aggressive', 'differential'],
                        help='Strategy to use for season simulation (default: baseline_current; phase_8_optimal = Phase 6-8 locked optimal)')
    parser.add_argument('-benchmark_init', action=argparse.BooleanOptionalAction, default=False,
                        help='Benchmark all 6 initial-team algorithms across the given seasons')
    parser.add_argument('-benchmark_transfer_lockout', action=argparse.BooleanOptionalAction, default=False,
                        help='Sweep no-transfer lockout lengths (GW 1..X) across the given seasons')
    parser.add_argument('-benchmark_gw_selection', action=argparse.BooleanOptionalAction, default=False,
                        help='Per-GW team selection benchmark: fresh squad each GW, no transfers, all 7 algorithms')
    parser.add_argument('-benchmark_rolling_horizon', action=argparse.BooleanOptionalAction, default=False,
                        help='Sweep rolling_horizon n_weeks (1-5) × discount_factor (1.0-0.7)')
    parser.add_argument('-benchmark_strategy_sweep', action=argparse.BooleanOptionalAction, default=False,
                        help='Sweep captain_mode × substitution_mode (per-GW fresh squad)')
    parser.add_argument('-benchmark_chip_schedule', action=argparse.BooleanOptionalAction, default=False,
                        help='Sweep chip_schedule (full-season simulation, chips need season state)')
    parser.add_argument('-save', '-s', action=argparse.BooleanOptionalAction, default=False,
                        help='Export results to JSON + score plot')
    parser.add_argument('-plot_p_minus_xp', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('-plot_score_comparison', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('-plot_average_comparison', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('-plot_xp', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('-project_score', action=argparse.BooleanOptionalAction, default=False)
    return parser.parse_args()


def get_strategy_config(strategy_name: str):
    """
    Instantiate a StrategyConfig by name.

    Args:
        strategy_name: Strategy name from CLI choices
                      ('static', 'baseline_current', 'phase_8_optimal', 'conservative', 'aggressive', 'differential')

    Returns:
        StrategyConfig instance

    Raises:
        ValueError if strategy_name is not recognized
    """
    from fpl_auto.strategies import (
        BASELINE_STATIC, BASELINE_CURRENT, PHASE_8_OPTIMAL, CONSERVATIVE, AGGRESSIVE, DIFFERENTIAL
    )
    strategies = {
        'static': BASELINE_STATIC,
        'baseline_current': BASELINE_CURRENT,
        'phase_8_optimal': PHASE_8_OPTIMAL,  # LOCKED Phase 6-8 optimal (multi-season validated)
        'conservative': CONSERVATIVE,
        'aggressive': AGGRESSIVE,
        'differential': DIFFERENTIAL,
    }
    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    return strategies[strategy_name]


def _make_team_at_gw1(season, start_gw, strategy_config=None):
    t = team_module.Team(season, start_gw, strategy_config=strategy_config)
    t.add_player('Aaron Ramsdale', 'GK')
    t.add_player('Gabriel dos Santos Magalhães', 'DEF')
    t.add_player('Luke Shaw', 'DEF')
    t.add_player('Pervis Estupiñán', 'DEF')
    t.add_player('Marcus Rashford', 'MID')
    t.add_player('Kaoru Mitoma', 'MID')
    t.add_player('Eberechi Eze', 'MID')
    t.add_player('Mohamed Salah', 'MID')
    t.add_player('Erling Haaland', 'FWD')
    t.add_player('João Pedro Junqueira de Jesus', 'FWD')
    t.add_player('Julián Álvarez', 'FWD')
    t.add_player('Alphonse Areola', 'GK')
    t.add_player("Amari'i Bell", 'DEF')
    t.add_player('George Baldock', 'DEF')
    t.add_player('Alexis Mac Allister', 'MID')
    return t


def run_season(config: dict) -> dict:
    """
    Simulate a full season. Designed to be called from a worker process.

    Args:
        config: dict with keys season, start_gw, repeat, starting_team, quiet, strategy

    Returns:
        dict with season results suitable for printing/saving.
    """
    season = config['season']
    start_gw = config['start_gw']
    repeat = config['repeat']
    starting_team = config.get('starting_team', 'auto')
    quiet = config.get('quiet', False)
    strategy_config = config.get('strategy', BASELINE_CURRENT)

    # Ensure strategy_config is a StrategyConfig instance
    if not isinstance(strategy_config, StrategyConfig):
        strategy_config = BASELINE_CURRENT

    # Suppress stdout in worker processes so output doesn't interleave
    if quiet:
        sys.stdout = open(os.devnull, 'w')

    try:
        if starting_team == 'custom_1':
            t = _make_team_at_gw1(season, start_gw, strategy_config)
        else:
            t = team_module.Team(season, start_gw, 100, strategy_config=strategy_config)
            t.initial_team_generator()

        p_list = []
        xp_list = []
        all_p = []

        for i in range(start_gw, start_gw + repeat + 1):
            t.auto_transfer(strategy_config=strategy_config)
            t.auto_subs(strategy_config=strategy_config)
            t.auto_captain()
            t.auto_chips()
            team_xp = t.team_xp()
            team_p = t.team_p()

            t.result_summary()
            p_list.append(team_p)
            xp_list.append(team_xp)

            if i != start_gw + repeat and i != start_gw + repeat:
                if team_p != 0:
                    all_p.append(t.p_list())
                t.return_subs_to_team()
                try:
                    t = team_module.Team(
                        season, i + 1, t.budget, t.transfers_left + 1,
                        [t.gks, t.defs, t.mids, t.fwds, t.subs],
                        t.chips_used, t.transfer_history,
                        t.chip_triple_captain_available, t.chip_bench_boost_available,
                        t.chip_free_hit_available, t.chip_wildcard_available,
                        t.free_hit_team,
                        t.purchase_prices,
                        strategy_config=strategy_config,
                    )
                except FileNotFoundError:
                    break

        return {
            'season': season,
            'p_list': p_list,
            'xp_list': xp_list,
            'chips_used': t.chips_used,
            'transfer_history': t.transfer_history,
        }
    finally:
        if quiet:
            sys.stdout = sys.__stdout__


def _print_season_summary(result: dict):
    season = result['season']
    p_list = result['p_list']
    xp_list = result['xp_list']
    p_sum = sum(p_list)
    xp_sum = sum(xp_list)
    n = len(p_list)
    print(f'\n{"=" * 40}')
    print(f'Season: {season}')
    print(f'  Total P:  {p_sum}  |  Avg P/GW:  {p_sum / n:.2f}')
    print(f'  Total xP: {xp_sum:.0f}  |  Avg xP/GW: {xp_sum / n:.2f}')
    print(f'  Chips: {result["chips_used"]}')


def _safe_run_season(cfg):
    """Wrapper around run_season that catches exceptions for benchmark runs."""
    try:
        return run_season(cfg)
    except Exception as e:
        return {
            'season': cfg['season'], 'p_list': [], 'xp_list': [],
            'chips_used': [], 'transfer_history': [], '_error': str(e),
        }


def run_benchmark_init(seasons: list, start_gw: int, repeat: int):
    """Benchmark all 6 initial-team algorithms across seasons.

    Runs each algorithm × each season in parallel and prints a comparison table.
    """
    algorithms = [
        ('greedy',          INIT_GREEDY),
        ('two_tier',        INIT_TWO_TIER),
        ('ilp_xp',          INIT_ILP_XP),
        ('ilp_ratio',       INIT_ILP_RATIO),
        ('ilp_penalised',   INIT_ILP_PENALISED),
        ('ilp_captain',     INIT_ILP_CAPTAIN),
        ('rolling_horizon', INIT_ROLLING_HORIZON),
    ]

    configs = []
    for algo_name, strategy in algorithms:
        for season in seasons:
            configs.append({
                'season': season,
                'start_gw': start_gw,
                'repeat': repeat,
                'starting_team': 'auto',
                'quiet': True,
                'strategy': strategy,
                '_algo': algo_name,
            })

    print(f'Benchmarking {len(algorithms)} init algorithms × {len(seasons)} seasons '
          f'({len(configs)} runs in parallel)...')

    with Pool(processes=min(len(configs), 12)) as pool:
        all_results = pool.map(_safe_run_season, configs)

    # Attach algo name to results (same order as configs)
    for res, cfg in zip(all_results, configs):
        res['_algo'] = cfg.get('_algo', res.get('_algo', '?'))
        if res.get('_error'):
            print(f"  ERROR [{res['_algo']} / {res['season']}]: {res['_error']}")

    # Build table: algo → season → total_p
    season_totals = {s: {} for s in seasons}
    for res in all_results:
        season_totals[res['season']][res['_algo']] = sum(res['p_list'])

    algo_names = [a[0] for a in algorithms]
    col_w = 16
    header = f"{'Algorithm':<{col_w}}" + ''.join(f"{s:>{col_w}}" for s in seasons) + f"{'AVG':>{col_w}}"
    print('\n' + '=' * len(header))
    print('INITIAL TEAM ALGORITHM BENCHMARK')
    print('=' * len(header))
    print(header)
    print('-' * len(header))

    baseline_avg = None
    rows = []
    for algo in algo_names:
        pts = [season_totals[s].get(algo, 0) for s in seasons]
        avg = sum(pts) / len(pts) if pts else 0
        rows.append((algo, pts, avg))
        if algo == 'greedy':
            baseline_avg = avg

    for algo, pts, avg in rows:
        delta = f'(+{avg - baseline_avg:.0f})' if algo != 'greedy' and baseline_avg else ''
        row = f"{algo:<{col_w}}" + ''.join(f"{p:>{col_w}}" for p in pts) + f"{avg:>{col_w - len(delta)}.0f}{delta}"
        print(row)
    print('=' * len(header))


def run_benchmark_transfer_lockout(seasons: list, start_gw: int, repeat: int):
    """Sweep no-transfer lockout lengths across seasons.

    For each lockout value X, transfers are blocked for GWs 1..X and allowed GW X+1..38.
    X=0 is the unrestricted baseline (full season window).
    """
    from dataclasses import replace as dc_replace
    lockout_values = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12]

    configs = []
    for x in lockout_values:
        window = (x + 1, 38) if x > 0 else None
        strategy = dc_replace(BASELINE_CURRENT, transfer_window_gw_range=window)
        for season in seasons:
            configs.append({
                'season': season,
                'start_gw': start_gw,
                'repeat': repeat,
                'starting_team': 'auto',
                'quiet': True,
                'strategy': strategy,
                '_lockout': x,
            })

    print(f'Benchmarking {len(lockout_values)} lockout lengths × {len(seasons)} seasons '
          f'({len(configs)} runs in parallel)...')

    with Pool(processes=min(len(configs), 16)) as pool:
        all_results = pool.map(_safe_run_season, configs)

    for res, cfg in zip(all_results, configs):
        res['_lockout'] = cfg['_lockout']
        if res.get('_error'):
            print(f"  ERROR [lockout={res['_lockout']} / {res['season']}]: {res['_error']}")

    season_totals = {s: {} for s in seasons}
    for res in all_results:
        season_totals[res['season']][res['_lockout']] = sum(res['p_list'])

    col_w = 14
    header = f"{'Lock GW 1..':<{col_w}}" + ''.join(f"{s:>{col_w}}" for s in seasons) + f"{'AVG':>{col_w}}"
    print('\n' + '=' * len(header))
    print('TRANSFER LOCKOUT BENCHMARK  (no transfers for GWs 1..X)')
    print('=' * len(header))
    print(header)
    print('-' * len(header))

    baseline_avg = None
    rows = []
    for x in lockout_values:
        pts = [season_totals[s].get(x, 0) for s in seasons]
        avg = sum(pts) / len(pts) if pts else 0
        rows.append((x, pts, avg))
        if x == 0:
            baseline_avg = avg

    for x, pts, avg in rows:
        label = f"X={x} (none)" if x == 0 else f"X={x}"
        delta = f'({avg - baseline_avg:+.0f})' if x != 0 and baseline_avg else ''
        row = (f"{label:<{col_w}}"
               + ''.join(f"{p:>{col_w}}" for p in pts)
               + f"{avg:>{col_w - len(delta)}.0f}{delta}")
        print(row)
    print('=' * len(header))

    best_x, _, best_avg = max(rows, key=lambda r: r[2])
    print(f'\nBest: X={best_x} (avg {best_avg:.0f})')


def _gw_selection_worker(config: dict) -> dict:
    season = config['season']
    start_gw = config['start_gw']
    repeat = config['repeat']
    strategy_config = config.get('strategy', BASELINE_CURRENT)
    algo_name = config.get('_algo', '?')

    if config.get('quiet'):
        sys.stdout = open(os.devnull, 'w')

    gw_points = []
    try:
        for gw in range(start_gw, start_gw + repeat + 1):
            try:
                t = team_module.Team(season, gw, 100.0, strategy_config=strategy_config)
                t.initial_team_generator()
                gw_p = t.team_p()
                gw_points.append(gw_p)
            except FileNotFoundError:
                break
        return {'season': season, '_algo': algo_name, 'gw_points': gw_points}
    except Exception as e:
        return {'season': season, '_algo': algo_name, 'gw_points': [], '_error': str(e)}
    finally:
        if config.get('quiet'):
            sys.stdout = sys.__stdout__


def run_benchmark_gw_selection(seasons: list, start_gw: int, repeat: int):
    """Per-GW team selection benchmark.

    Freshly generates a squad each GW (£100m budget, no prior state) with each
    initial-team algorithm, then scores against actual GW points with captain 2×.
    No transfers, no chips. Isolates team-selection signal from transfer noise.
    """
    algorithms = [
        ('greedy',          INIT_GREEDY),
        ('two_tier',        INIT_TWO_TIER),
        ('ilp_xp',          INIT_ILP_XP),
        ('ilp_ratio',       INIT_ILP_RATIO),
        ('ilp_penalised',   INIT_ILP_PENALISED),
        ('ilp_captain',     INIT_ILP_CAPTAIN),
        ('rolling_horizon', INIT_ROLLING_HORIZON),
    ]

    configs = [
        {'season': season, 'start_gw': start_gw, 'repeat': repeat,
         'quiet': True, 'strategy': strategy, '_algo': algo_name}
        for algo_name, strategy in algorithms
        for season in seasons
    ]

    print(f'GW-Selection Benchmark: {len(algorithms)} algorithms × {len(seasons)} seasons '
          f'({len(configs)} runs, {repeat + 1} GWs each)...')

    with Pool(processes=min(len(configs), 12)) as pool:
        all_results = pool.map(_gw_selection_worker, configs)

    for res, cfg in zip(all_results, configs):
        res['_algo'] = cfg['_algo']
        if res.get('_error'):
            print(f"  ERROR [{res['_algo']} / {res['season']}]: {res['_error']}")

    season_totals = {s: {} for s in seasons}
    for res in all_results:
        season_totals[res['season']][res['_algo']] = sum(res['gw_points'])

    algo_names = [a[0] for a in algorithms]
    col_w = 16
    header = (f"{'Algorithm':<{col_w}}"
              + ''.join(f"{s:>{col_w}}" for s in seasons)
              + f"{'AVG':>{col_w}}")
    print('\n' + '=' * len(header))
    print('GW TEAM SELECTION BENCHMARK  (fresh squad each GW, no transfers)')
    print('=' * len(header))
    print(header)
    print('-' * len(header))

    baseline_avg = None
    rows = []
    for algo in algo_names:
        pts = [season_totals[s].get(algo, 0) for s in seasons]
        avg = sum(pts) / len(pts) if pts else 0
        rows.append((algo, pts, avg))
        if algo == 'greedy':
            baseline_avg = avg

    for algo, pts, avg in rows:
        delta = f'({avg - baseline_avg:+.0f})' if algo != 'greedy' and baseline_avg else ''
        row = (f"{algo:<{col_w}}"
               + ''.join(f"{p:>{col_w}}" for p in pts)
               + f"{avg:>{col_w - len(delta)}.0f}{delta}")
        print(row)

    best_algo, _, best_avg = max(rows, key=lambda r: r[2])
    print('=' * len(header))
    print(f'\nBest: {best_algo} (avg {best_avg:.0f})')


def run_benchmark_rolling_horizon(seasons: list, start_gw: int, repeat: int):
    """Sweep rolling_horizon n_weeks (1-5) × discount_factor across seasons.

    Each variant generates a fresh squad each GW (£100m, no transfers) and scores
    against actual GW points. Isolates which look-ahead depth and decay rate maximises
    team-selection quality.
    """
    from dataclasses import replace as dc_replace
    n_weeks_values = [5, 6, 7, 8]

    variants = [
        (f'n={n}', dc_replace(INIT_ROLLING_HORIZON, ilp_rolling_weeks=n, rolling_horizon_discount=1.0))
        for n in n_weeks_values
    ]

    configs = [
        {'season': season, 'start_gw': start_gw, 'repeat': repeat,
         'quiet': True, 'strategy': strategy, '_algo': label}
        for label, strategy in variants
        for season in seasons
    ]

    print(f'Rolling Horizon Benchmark: {len(variants)} variants × {len(seasons)} seasons '
          f'({len(configs)} runs, {repeat + 1} GWs each)...')

    with Pool(processes=min(len(configs), 16)) as pool:
        all_results = pool.map(_gw_selection_worker, configs)

    for res, cfg in zip(all_results, configs):
        res['_algo'] = cfg['_algo']
        if res.get('_error'):
            print(f"  ERROR [{res['_algo']} / {res['season']}]: {res['_error']}")

    season_totals = {s: {} for s in seasons}
    for res in all_results:
        season_totals[res['season']][res['_algo']] = sum(res['gw_points'])

    variant_labels = [v[0] for v in variants]
    col_w = 14
    header = (f"{'Variant':<14}"
              + ''.join(f"{s:>{col_w}}" for s in seasons)
              + f"{'AVG':>{col_w}}")
    print('\n' + '=' * len(header))
    print('ROLLING HORIZON BENCHMARK  (n_weeks × discount_factor, fresh squad each GW)')
    print('=' * len(header))
    print(header)
    print('-' * len(header))

    baseline_label = 'n=5'
    baseline_avg = None
    rows = []
    for label in variant_labels:
        pts = [season_totals[s].get(label, 0) for s in seasons]
        avg = sum(pts) / len(pts) if pts else 0
        rows.append((label, pts, avg))
        if label == baseline_label:
            baseline_avg = avg

    best_label, _, best_avg = max(rows, key=lambda r: r[2])
    for label, pts, avg in rows:
        delta = f'({avg - baseline_avg:+.0f})' if label != baseline_label and baseline_avg else ''
        marker = ' *' if label == best_label else ''
        row = (f"{label:<14}"
               + ''.join(f"{p:>{col_w}}" for p in pts)
               + f"{avg:>{col_w - len(delta) - len(marker)}.0f}{delta}{marker}")
        print(row)
        pass

    print('=' * len(header))
    print(f'\nBest: {best_label} (avg {best_avg:.0f})')


def run_benchmark_strategy_sweep(seasons: list, start_gw: int, repeat: int):
    """Sweep captain_mode × substitution_mode using per-GW fresh-squad methodology.

    Holds initial_team_algorithm='rolling_horizon' (n=5, d=1.0) fixed.
    Isolates which captaincy + sub policies maximise team-selection quality.
    Chips are NOT tested here — they require season state (see run_benchmark_chip_schedule).
    """
    from dataclasses import replace as dc_replace
    captain_modes = ['highest_xp', 'highest_value', 'form_based']
    substitution_modes = ['static', 'predictive_swap']

    variants = [
        (f'cap={cm:<13} sub={sm}',
         dc_replace(BASELINE_CURRENT, captain_mode=cm, substitution_mode=sm))
        for cm in captain_modes
        for sm in substitution_modes
    ]

    configs = [
        {'season': season, 'start_gw': start_gw, 'repeat': repeat,
         'quiet': True, 'strategy': strategy, '_algo': label}
        for label, strategy in variants
        for season in seasons
    ]

    print(f'Strategy Sweep: {len(variants)} (captain × sub) × {len(seasons)} seasons '
          f'({len(configs)} runs, {repeat + 1} GWs each)...')

    with Pool(processes=min(len(configs), 16)) as pool:
        all_results = pool.map(_gw_selection_worker, configs)

    for res, cfg in zip(all_results, configs):
        res['_algo'] = cfg['_algo']
        if res.get('_error'):
            print(f"  ERROR [{res['_algo']} / {res['season']}]: {res['_error']}")

    season_totals = {s: {} for s in seasons}
    for res in all_results:
        season_totals[res['season']][res['_algo']] = sum(res['gw_points'])

    col_w = 14
    label_w = 32
    header = (f"{'Variant':<{label_w}}"
              + ''.join(f"{s:>{col_w}}" for s in seasons)
              + f"{'AVG':>{col_w}}")
    print('\n' + '=' * len(header))
    print('STRATEGY SWEEP  (rolling_horizon n=5, per-GW fresh squad, no transfers/chips)')
    print('=' * len(header))
    print(header)
    print('-' * len(header))

    rows = []
    for label, _ in variants:
        pts = [season_totals[s].get(label, 0) for s in seasons]
        avg = sum(pts) / len(pts) if pts else 0
        rows.append((label, pts, avg))

    rows.sort(key=lambda r: -r[2])  # sort best first
    best_label, _, best_avg = rows[0]
    baseline_avg = next((r[2] for r in rows if 'cap=highest_xp ' in r[0] and 'sub=static' in r[0]), best_avg)

    for label, pts, avg in rows:
        delta = f'({avg - baseline_avg:+.0f})' if avg != baseline_avg else ''
        marker = ' *' if label == best_label else ''
        row = (f"{label:<{label_w}}"
               + ''.join(f"{p:>{col_w}}" for p in pts)
               + f"{avg:>{col_w - len(delta) - len(marker)}.0f}{delta}{marker}")
        print(row)
    print('=' * len(header))
    print(f'\nBest: {best_label.strip()} (avg {best_avg:.0f})')


def run_benchmark_chip_schedule(seasons: list, start_gw: int, repeat: int):
    """Sweep chip_schedule values across seasons using full-season simulation.

    Chips need season state (1 wildcard, 1 bench boost, etc.) so per-GW fresh-squad
    methodology doesn't apply. Uses standard run_season with rolling_horizon n=5 init.
    """
    from dataclasses import replace as dc_replace
    chip_schedules = ['never', 'conservative', 'aggressive', 'doubles-optimized', 'blanks-optimized']

    configs = []
    for sched in chip_schedules:
        strategy = dc_replace(BASELINE_CURRENT, chip_schedule=sched)
        for season in seasons:
            configs.append({
                'season': season, 'start_gw': start_gw, 'repeat': repeat,
                'starting_team': 'auto', 'quiet': True,
                'strategy': strategy, '_chip': sched,
            })

    print(f'Chip Schedule Benchmark: {len(chip_schedules)} schedules × {len(seasons)} seasons '
          f'({len(configs)} full-season runs)...')

    with Pool(processes=min(len(configs), 16)) as pool:
        all_results = pool.map(_safe_run_season, configs)

    for res, cfg in zip(all_results, configs):
        res['_chip'] = cfg['_chip']
        if res.get('_error'):
            print(f"  ERROR [{res['_chip']} / {res['season']}]: {res['_error']}")

    season_totals = {s: {} for s in seasons}
    for res in all_results:
        season_totals[res['season']][res['_chip']] = sum(res['p_list'])

    col_w = 14
    label_w = 22
    header = (f"{'Chip Schedule':<{label_w}}"
              + ''.join(f"{s:>{col_w}}" for s in seasons)
              + f"{'AVG':>{col_w}}")
    print('\n' + '=' * len(header))
    print('CHIP SCHEDULE BENCHMARK  (full-season, rolling_horizon n=5 init)')
    print('=' * len(header))
    print(header)
    print('-' * len(header))

    baseline_avg = None
    rows = []
    for sched in chip_schedules:
        pts = [season_totals[s].get(sched, 0) for s in seasons]
        avg = sum(pts) / len(pts) if pts else 0
        rows.append((sched, pts, avg))
        if sched == 'conservative':
            baseline_avg = avg

    best_sched, _, best_avg = max(rows, key=lambda r: r[2])
    for sched, pts, avg in rows:
        delta = f'({avg - baseline_avg:+.0f})' if sched != 'conservative' and baseline_avg else ''
        marker = ' *' if sched == best_sched else ''
        row = (f"{sched:<{label_w}}"
               + ''.join(f"{p:>{col_w}}" for p in pts)
               + f"{avg:>{col_w - len(delta) - len(marker)}.0f}{delta}{marker}")
        print(row)
    print('=' * len(header))
    print(f'\nBest: {best_sched} (avg {best_avg:.0f})')


def main():
    inputs = parse_args()

    seasons = inputs.seasons if inputs.seasons else [inputs.season]
    parallel = len(seasons) > 1

    if inputs.benchmark_init:
        run_benchmark_init(seasons, inputs.start_gw, inputs.repeat_until - 1)
        return

    if inputs.benchmark_transfer_lockout:
        run_benchmark_transfer_lockout(seasons, inputs.start_gw, inputs.repeat_until - 1)
        return

    if inputs.benchmark_gw_selection:
        run_benchmark_gw_selection(seasons, inputs.start_gw, inputs.repeat_until - 1)
        return

    if inputs.benchmark_rolling_horizon:
        run_benchmark_rolling_horizon(seasons, inputs.start_gw, inputs.repeat_until - 1)
        return

    if inputs.benchmark_strategy_sweep:
        run_benchmark_strategy_sweep(seasons, inputs.start_gw, inputs.repeat_until - 1)
        return

    if inputs.benchmark_chip_schedule:
        run_benchmark_chip_schedule(seasons, inputs.start_gw, inputs.repeat_until - 1)
        return

    # Instantiate strategy config
    strategy_config = get_strategy_config(inputs.strategy)

    configs = [
        {
            'season': s,
            'start_gw': inputs.start_gw,
            'repeat': inputs.repeat_until - 1,
            'starting_team': inputs.starting_team,
            'quiet': parallel,
            'strategy': strategy_config,
        }
        for s in seasons
    ]

    if parallel:
        print(f'Running {len(seasons)} seasons in parallel: {", ".join(seasons)}')
        with Pool(processes=len(seasons)) as pool:
            results = pool.map(run_season, configs)
    else:
        results = [run_season(configs[0])]

    for result in results:
        _print_season_summary(result)

        if inputs.save:
            eval.export_results(
                result['season'], result['p_list'], result['xp_list'],
                result['chips_used'], result['transfer_history'],
            )

        if inputs.plot_p_minus_xp:
            eval.plot_p_minus_xp(result['p_list'], result['xp_list'],
                                 inputs.start_gw, inputs.repeat_until)
        if inputs.plot_score_comparison:
            eval.plot_score_comparison(result['p_list'], result['chips_used'],
                                       inputs.start_gw, result['season'], inputs.project_score)
        if inputs.plot_average_comparison:
            t = team_module.Team(result['season'], inputs.start_gw)
            avg = t.get_avg_score()
            eval.plot_average_comparison(result['p_list'], avg,
                                         inputs.start_gw, inputs.repeat_until)
            good, bad = eval.score_model_against_list(result['p_list'], avg)
            print(f'  vs avg: {good} good, {bad} poor = {good/(good+bad)*100:.1f}%')
        if inputs.plot_xp:
            eval.plotxp(result['season'], result['xp_list'],
                        inputs.start_gw, inputs.repeat_until, result['chips_used'])


if __name__ == '__main__':
    main()
