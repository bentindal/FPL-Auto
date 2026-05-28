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
from fpl_auto.strategies import StrategyConfig, BASELINE_CURRENT


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
                        choices=['static', 'baseline_current', 'conservative', 'aggressive', 'differential'],
                        help='Strategy to use for season simulation (default: baseline_current)')
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
                      ('static', 'baseline_current', 'conservative', 'aggressive', 'differential')

    Returns:
        StrategyConfig instance

    Raises:
        ValueError if strategy_name is not recognized
    """
    from fpl_auto.strategies import (
        BASELINE_STATIC, BASELINE_CURRENT, CONSERVATIVE, AGGRESSIVE, DIFFERENTIAL
    )
    strategies = {
        'static': BASELINE_STATIC,
        'baseline_current': BASELINE_CURRENT,
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


def main():
    inputs = parse_args()

    seasons = inputs.seasons if inputs.seasons else [inputs.season]
    parallel = len(seasons) > 1

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
