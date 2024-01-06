import matplotlib.pyplot as plt
import team
import time

season = '2023-24'
start_gw = 5
repeat = 16
before_transfer = []
after_transfer = []

def main():
    t = team.team(season, start_gw, 5)

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

    for i in range(start_gw, start_gw + repeat):
        #t.auto_subs()
        #t.auto_captain()
        #t.display()
        print(f'SquadSize: {t.squad_size}')
        print(f'Team xP (before transfer): {t.team_xp():.2f}')
        print(f'Actual P (before transfer): {t.team_p():.2f}')
        before_transfer.append(t.team_p())
        out, pos, budget = t.suggest_transfer_out()
        print(f'Transfer out: {out} {pos}')

        transfer_in = t.suggest_transfer_in(pos, t.budget + budget)
        print(f'Transfer in: {transfer_in} {pos}')
        
        t.transfer(out, transfer_in, pos)
        
        t.auto_subs()
        t.auto_captain()
        t.display()
        print(f'SquadSize: {t.squad_size}')
        print(f'Budget: {t.budget:.2f}')
        #t.auto_chips
        print(f'Team xP (after transfer): {t.team_xp():.2f}')
        print(f'Actual P (after transfer): {t.team_p():.2f}')
        after_transfer.append(t.team_p())
        


        #time.sleep(10)

        if i != 20:
            t = team.team(season, i + 1, t.budget, t.gks, t.defs, t.mids, t.fwds, t.subs)

    gameweeks = range(start_gw, start_gw + repeat)

    plt.plot(gameweeks, after_transfer, label='After Transfer')
    plt.plot(gameweeks, before_transfer, label='Before Transfer')
    plt.xlabel('Gameweek')
    plt.ylabel('Points')
    plt.title('Points Comparison')
    plt.legend()
    plt.show()
    
if __name__ == '__main__':
    main()