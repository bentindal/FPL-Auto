from fpl_auto import data as d

d = d.fpl_data('data', '2023-24')

player_name = 'Aaron Ramsdale'
week_num = 1

player_fixtures = d.get_future_fixtures_for_player(player_name, week_num)

print(player_fixtures)