'''
Team Manager for FPL Automation Project
Author: Benjamin Tindal
'''

import argparse
import fpl_auto.team as team
import json
from fpl_auto import evaluate as eval

def parse_args():
    parser = argparse.ArgumentParser(description="FPL Automation Project: Team Manager")
    parser.add_argument('-season', type=str, required=True, help='Season to simulate. Format: YYYY-YY e.g 2021-22')
    parser.add_argument('-start_gw', type=int, default=1, help='Gameweek to start on, default 1')
    parser.add_argument('-repeat_until', type=int, default=38, help='How many weeks to repeat testing over, default: 38')
    parser.add_argument('-starting_team', type=str, default="auto",
                        choices=[
                            "auto", "custom_1", "custom_2"], 
                        help='Initial team to use: auto = generate own team, custom_1 = use my team at GW1, custom_2 = use my team at GW18, default: auto')
    
    parser.add_argument('-plot_p_minus_xp',
                        action=argparse.BooleanOptionalAction, default=False, help='Plot P minus XP graph for each GW, default: False')
    parser.add_argument('-plot_score_comparison',
                        action=argparse.BooleanOptionalAction, default=False, help='Plot P each week categorised by performance, default: False')
    parser.add_argument('-plot_average_comparison',
                        action=argparse.BooleanOptionalAction, default=False, help='Plot P vs AVG P, IMPORTANT: only works for current season, default: False')
    args = parser.parse_args()
    
    return args

inputs = parse_args()
season = inputs.season
start_gw = inputs.start_gw
repeat = inputs.repeat_until - 1

def get_team_from_manager_id(manager_id):
    target_url = f'https://fantasy.premierleague.com/api/my-team/{manager_id}/'
    print(f'First, sign in on the official FPL website, then go to the following url and copy the response and set it as var r: {target_url}')
    r = '{"picks":[{"element":409,"position":1,"selling_price":40,"multiplier":1,"purchase_price":39,"is_captain":false,"is_vice_captain":false},{"element":430,"position":2,"selling_price":67,"multiplier":1,"purchase_price":68,"is_captain":false,"is_vice_captain":false},{"element":506,"position":3,"selling_price":56,"multiplier":1,"purchase_price":55,"is_captain":false,"is_vice_captain":false},{"element":220,"position":4,"selling_price":47,"multiplier":1,"purchase_price":46,"is_captain":false,"is_vice_captain":false},{"element":353,"position":5,"selling_price":77,"multiplier":1,"purchase_price":75,"is_captain":false,"is_vice_captain":false},{"element":526,"position":6,"selling_price":80,"multiplier":1,"purchase_price":79,"is_captain":false,"is_vice_captain":false},{"element":362,"position":7,"selling_price":56,"multiplier":1,"purchase_price":56,"is_captain":false,"is_vice_captain":true},{"element":19,"position":8,"selling_price":88,"multiplier":2,"purchase_price":87,"is_captain":true,"is_vice_captain":false},{"element":343,"position":9,"selling_price":68,"multiplier":1,"purchase_price":67,"is_captain":false,"is_vice_captain":false},{"element":60,"position":10,"selling_price":86,"multiplier":1,"purchase_price":83,"is_captain":false,"is_vice_captain":false},{"element":85,"position":11,"selling_price":70,"multiplier":1,"purchase_price":69,"is_captain":false,"is_vice_captain":false},{"element":597,"position":12,"selling_price":48,"multiplier":0,"purchase_price":50,"is_captain":false,"is_vice_captain":false},{"element":5,"position":13,"selling_price":49,"multiplier":0,"purchase_price":49,"is_captain":false,"is_vice_captain":false},{"element":92,"position":14,"selling_price":43,"multiplier":0,"purchase_price":43,"is_captain":false,"is_vice_captain":false},{"element":473,"position":15,"selling_price":38,"multiplier":0,"purchase_price":38,"is_captain":false,"is_vice_captain":false}],"chips":[{"status_for_entry":"available","played_by_entry":[],"name":"wildcard","number":1,"start_event":21,"stop_event":38,"chip_type":"transfer"},{"status_for_entry":"available","played_by_entry":[],"name":"freehit","number":1,"start_event":2,"stop_event":38,"chip_type":"transfer"},{"status_for_entry":"available","played_by_entry":[],"name":"bboost","number":1,"start_event":1,"stop_event":38,"chip_type":"team"},{"status_for_entry":"available","played_by_entry":[],"name":"3xc","number":1,"start_event":1,"stop_event":38,"chip_type":"team"}],"transfers":{"cost":4,"status":"cost","limit":1,"made":1,"bank":99,"value":931}}'
    # Convert r to pds object
    r = json.loads(r)
    r = r['picks']
    t = team.team(season, start_gw, 100)
    for player in r:
        player_name = t.id_to_name(player['element'])
        t.add_player(player_name, t.positions_list[player_name], (player['purchase_price'] / 10))
    
    return t

def my_team_at_gw1():
    t = team.team(season, start_gw)
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

def main():
    if inputs.starting_team == 'custom_1':
        t = my_team_at_gw1()
    elif inputs.starting_team == 'custom_2':
        t = get_team_from_manager_id(1) # 1 is my manager id
    else:
        t = team.team(season, start_gw, 100)
        t.initial_team_generator() #t = t.select_ideal_team(2, 12, 3, 12, 2, 7, 2, 5.5) 

    p_list = []
    xp_list = []
    all_p = []

    for i in range(start_gw, start_gw + repeat + 1):
        # --- BEFORE DEADLINE ---
        t.auto_subs()
        t.auto_captain()
        t.auto_chips()
        team_xp = t.team_xp()

        # --- AFTER DEADLINE ---
        team_p = t.team_p()
        t.display()
        # Week Results
        t.result_summary()
        
        if team_p != 0:
            p_list.append(team_p)
            xp_list.append(team_xp)
            all_p.append(t.p_list())
        # Set team to next week
        if i != start_gw + repeat:
            t.return_subs_to_team()
            t.auto_transfer() # Make a transfer
            try:
                t = team.team(season, i + 1, t.budget, t.transfers_left + 1, [t.gks, t.defs, t.mids, t.fwds], t.chips_used, t.chip_triple_captain_available, t.chip_bench_boost_available, t.chip_free_hit_available, t.chip_wildcard_available, t.free_hit_team)
            except FileNotFoundError:
                print(f'GW{i + 1} not found')
                break
    
    # Sum the p_list and xp_list and report results
    print('==============================')
    p_sum = sum(p_list)
    xp_sum = sum(xp_list)
    print(f'p_sum: {p_sum}')
    print(f'avg_p: {p_sum / len(p_list):.2f}')
    print(f'xp_sum: {xp_sum:.0f}')
    print(f'avg_xp: {xp_sum / len(p_list):.2f}')
    print(t.chips_used)

    # Plots
    if inputs.plot_p_minus_xp:
        eval.plot_p_minus_xp(p_list, xp_list, start_gw, start_gw + repeat)
    if inputs.plot_score_comparison:
        eval.plot_score_comparison(p_list, t.chips_used, start_gw, start_gw + repeat, season)
    if inputs.plot_average_comparison:
        eval.plot_average_comparison(p_list, t.get_avg_score(), start_gw, start_gw + repeat)
        good, bad = eval.score_model_against_list(p_list, t.get_avg_score())
        print(f'Good: {good}, Poor: {bad} = {good / (good + bad) * 100:.2f}%')

if __name__ == '__main__':
    main()