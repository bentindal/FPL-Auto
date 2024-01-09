import matplotlib.pyplot as plt
import fpl_auto.team as team
import json
import requests
import pandas as pd

season = '2023-24'
start_gw = 1
repeat = 20

def get_team_from_manager_id(manager_id):
    target_url = f'https://fantasy.premierleague.com/api/my-team/{manager_id}/'
    print(f'Go to the following url and copy the response as var r: {target_url}')
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
    t = get_team_from_manager_id(3413300)
    
    p_list = []
    xp_list = []

    for i in range(start_gw, start_gw + repeat + 1):
        # Prepare team
        team_xp = t.team_xp()

        # Deadline reached! Now lets score the team
        team_p = t.team_p()
        
        t.display()
        print(f'P: {team_p:.2f}, XP: {team_xp:.2f}')
        
        xp_list.append(team_xp)
        p_list.append(team_p)

        print('-----------------------------')
        # Lets make a transfer
        t.auto_transfer()

        print('-----------------------------')
        

        if i != start_gw + repeat:
            t = team.team(season, i + 1, t.budget, t.gks, t.defs, t.mids, t.fwds)
        
    
    # Sum the p_list and xp_list and report results
    print('==============================')
    p_sum = sum(p_list)
    xp_sum = sum(xp_list)
    print(f'p_sum: {p_sum}')
    print(f'xp_sum: {xp_sum:.0f}')

if __name__ == '__main__':
    main()