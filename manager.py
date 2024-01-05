import team

season = '2023-24'
i = 17

def main():
    t = team.team(season, i)
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
    t.auto_subs()
    t.auto_captain()

    t.display()

    print(f'Team xP: {t.team_xp():.2f}')

if __name__ == '__main__':
    main()