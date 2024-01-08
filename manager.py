import matplotlib.pyplot as plt
import fpl_auto.team as team

season = '2023-24'
start_gw = 2
repeat = 18

def my_current_team_at_gw21():
    t = team.team(season, start_gw, 1)
    t.add_player('André Onana', 'GK')
    t.add_player('Gabriel dos Santos Magalhães', 'DEF')
    t.add_player('Pedro Porro', 'DEF')
    t.add_player('Kieran Trippier', 'DEF')
    t.add_player('Cole Palmer', 'MID')
    t.add_player('Jarrod Bowen', 'MID')
    t.add_player('Bukayo Saka', 'MID')
    t.add_player('Phil Foden', 'MID')
    t.add_player('Ollie Watkins', 'FWD')
    t.add_player('Dominic Solanke', 'FWD')
    t.add_player('Julián Álvarez', 'FWD')
    
    t.add_player('Martin Dubravka', 'GK')
    t.add_player('Joachim Andersen', 'DEF')
    t.add_player('Shandon Baptiste', 'MID')
    t.add_player('George Baldock', 'DEF')
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
    t = my_team_at_gw1()
    p_list = [69]
    xp_list = [69]
    for i in range(start_gw, start_gw + repeat + 1):
        print(f'GW{i}')
        # Prepare team
        team_xp = t.team_xp()

        # View team before
        #t.display()
        
        # Now lets score the team
        team_p = t.team_p()
        
        # View team after!
        #t.display()
        print(f'Result: {team_p:.2f}')
        
        xp_list.append(team_xp)
        p_list.append(team_p)
        
        # Lets make a transfer
        out, pos, budget = t.suggest_transfer_out()
        transfer_in = t.suggest_transfer_in(pos, t.budget + budget)
        print(f'Transfer out: {out} {pos} for {transfer_in} {pos}')
        t.transfer(out, transfer_in, pos)

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