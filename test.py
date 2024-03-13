from fpl_auto import evaluate as eval
from fpl_auto import team
from fpl_auto import data

t = team.team('2023-24')
t.get_n_gws_xp(3)

print(t.player_value('Alexis Mac Allister'))