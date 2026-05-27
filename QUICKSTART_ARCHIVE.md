# Quick Start: FPL Season Winners Archive

## What You Now Have

✅ **Reusable Jupyter Notebook**: `notebooks/archive_season_winners.ipynb`
✅ **Complete Archive**: `data/season_winners_2025-26/` (6.9 MB, 1,140 files)
✅ **Full Documentation**: `data/season_winners_2025-26/README.md`

---

## 5-Minute Start

### Load the Season Winner's Data
```python
import json
from pathlib import Path

# Open Ivan Peula's (rank #1) complete season
data_path = Path('data/season_winners_2025-26/3244539/_complete_season.json')
with open(data_path) as f:
    season = json.load(f)

# Check GW1 performance
gw1 = season['1']
print(f"GW1 Points: {gw1['entry_history']['points']}")
print(f"GW1 Captain: {next(p['element'] for p in gw1['picks'] if p.get('is_captain'))}")
print(f"GW1 Rank: {gw1['entry_history']['rank']}")
```

### Get All Top 30 Managers
```python
import json
from pathlib import Path

master = json.load(open('data/season_winners_2025-26/MASTER_SUMMARY.json'))
for mgr in master['top_managers']:
    print(f"Rank {mgr['rank']:2d}: {mgr['player_name']:25s} - {mgr['points']} pts")
```

### Analyze Elite Captaincy Decisions
```python
# Which players did the elite captain most?
master = json.load(open('data/season_winners_2025-26/MASTER_SUMMARY.json'))
captains = master['captaincy_meta']['most_captained_overall']

print("Most captained players across top 30 managers:")
for player_id, count in list(captains.items())[:5]:
    pct = (count / (30 * 38)) * 100
    print(f"  Player {player_id}: {count} times ({pct:.1f}%)")
```

---

## Common Use Cases

### 1. Get All of Manager X's Captaincy Choices
```python
import json

mgr_id = 3244539  # Ivan Peula
analysis = json.load(open(f'data/season_winners_2025-26/{mgr_id}/analysis.json'))

print(f"Top captains for {analysis['manager']['player_name']}:")
for player_id, count in list(analysis['captaincy']['top_choices'].items())[:5]:
    print(f"  Player {player_id}: {count} gameweeks")
```

### 2. See How Often Each Player Was Selected
```python
import json

mgr_id = 3244539
analysis = json.load(open(f'data/season_winners_2025-26/{mgr_id}/analysis.json'))

print(f"Core squad for {analysis['manager']['player_name']}:")
most_selected = analysis['squad']['most_selected']
for player_id, gw_count in list(most_selected.items())[:10]:
    print(f"  Player {player_id}: {gw_count}/38 gameweeks")
```

### 3. Check Chip Usage Patterns
```python
import json

master = json.load(open('data/season_winners_2025-26/MASTER_SUMMARY.json'))

print("Chip usage across top 30 managers:")
for chip in ['wildcard', 'freehit', 'bboost', '3xc']:
    # Count uses in each manager's analysis
    uses = 0
    for mgr in master['top_managers']:
        try:
            analysis = json.load(open(f"data/season_winners_2025-26/{mgr['manager_id']}/analysis.json"))
            if chip in analysis['chip_usage']:
                uses += analysis['chip_usage'][chip]['count']
        except:
            pass
    print(f"  {chip.upper()}: {uses} total uses ({uses/30:.1f} per manager)")
```

### 4. Find Your Rival's Top Manager Data
```python
import json

# First, find their manager ID from their FPL team URL
# Format: https://fantasy.premierleague.com/entry/{manager_id}/
manager_id = 3244539  # Example

data_dir = f'data/season_winners_2025-26/{manager_id}'
season = json.load(open(f'{data_dir}/_complete_season.json'))
analysis = json.load(open(f'{data_dir}/analysis.json'))

# Now you have all their picks for every gameweek!
for gw in range(1, 39):
    picks = season[str(gw)]['picks']
    points = season[str(gw)]['entry_history']['points']
    print(f"GW {gw:2d}: {points} pts, squad: {[p['element'] for p in picks[:11]]}")
```

---

## File Locations

| What | Where |
|------|-------|
| Reusable notebook | `notebooks/archive_season_winners.ipynb` |
| Archive directory | `data/season_winners_2025-26/` |
| All managers summary | `data/season_winners_2025-26/MASTER_SUMMARY.json` |
| Manager X's data | `data/season_winners_2025-26/{manager_id}/` |
| Manager X's GW1 picks | `data/season_winners_2025-26/{manager_id}/gw01.json` |
| Manager X's analysis | `data/season_winners_2025-26/{manager_id}/analysis.json` |
| Archive guide | `data/season_winners_2025-26/README.md` |
| This summary | `ARCHIVE_SUMMARY.md` |

---

## Modify the Notebook for Different Seasons

The Jupyter notebook can be reused for:

1. **Different number of managers**: Change `get_top_managers(30)` to any number
2. **Different seasons**: Modify `archive_manager_season(..., season='2024-25')`
3. **Specific managers**: Call `archive_manager_season(manager_id, name)` directly
4. **Different number of gameweeks**: Change `num_gws=38` parameter

---

## Player ID Reference

To convert player IDs to player names:

```python
import requests

# Get the mapping
bootstrap = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/').json()
players = {p['id']: p['web_name'] for p in bootstrap['elements']}

# Use it
player_430_name = players[430]  # e.g., "Erling Haaland"
```

---

## Key Findings

The top 30 managers:
- **Captained Player 430** 30 times (most consistent choice)
- **Captained Player 449** 30 times (close second)
- **Made 0 transfers total** (!)
- **Used 68.1 unique players** on average
- **Used all 4 chips** roughly equally (1.9-2.0 times each)

---

## Next Steps

1. **Load the season winner's data** and compare your team
2. **Analyze captaincy patterns** to improve your captain picks
3. **Study squad selections** to identify underrated players
4. **Examine chip timing** to find optimal GW windows
5. **Build an ML model** using elite decisions as training data

---

## Helpful Commands

```bash
# See all manager directories
ls -la data/season_winners_2025-26/ | grep "^d"

# Count total files
find data/season_winners_2025-26 -type f -name "*.json" | wc -l

# Check archive size
du -sh data/season_winners_2025-26/

# View one manager's analysis
cat data/season_winners_2025-26/3244539/analysis.json | python -m json.tool
```

---

**Ready to use! Start with the Python examples above, then dive into `data/season_winners_2025-26/README.md` for full details.**
