# FPL Season Winners Archive 2025-26

Complete week-by-week data for the top 30 Fantasy Premier League managers of the 2025-26 season.

## Quick Stats

| Metric | Value |
|--------|-------|
| **Managers archived** | 30 |
| **Gameweeks** | 38 |
| **Total data files** | 1,140 (38 GWs × 30 managers) |
| **Total size** | 6.9 MB |
| **#1 Manager** | Ivan Peula (Team Peki) - 2,538 points |
| **Rank range** | 1-30 |

## Directory Structure

```
season_winners_2025-26/
├── MASTER_SUMMARY.json              # Aggregated stats across all 30 managers
├── README.md                        # This file
├── {manager_id}/                    # One folder per manager (30 total)
│   ├── gw01.json - gw38.json       # Individual gameweek picks (38 files)
│   ├── _complete_season.json        # All 38 GWs in one file
│   └── analysis.json                # Strategy analysis for this manager
```

## Data Structure

### Gameweek File (e.g., `gw01.json`)

```json
{
  "active_chip": "bboost|wildcard|freehit|3xc|null",
  "entry_history": {
    "event": 1,
    "points": 83,
    "total_points": 83,
    "rank": 118578,
    "overall_rank": 118578,
    "bank": 10,
    "value": 1000,
    "event_transfers": 0,
    "event_transfers_cost": 0
  },
  "picks": [
    {
      "element": 366,              # Player ID from FPL API
      "position": 1,               # Squad position (1-15)
      "multiplier": 1 | 2,         # 1=normal, 2=captain
      "is_captain": true|false,
      "is_vice_captain": true|false,
      "element_type": 1|2|3|4      # 1=GK, 2=DEF, 3=MID, 4=FWD
    }
    // ... 15 players per gameweek
  ]
}
```

### Analysis File (`analysis.json`)

```json
{
  "manager": {
    "rank": 1,
    "manager_id": 3244539,
    "player_name": "Ivan Peula",
    "team_name": "Team Peki",
    "points": 2538
  },
  "captaincy": {
    "top_choices": {
      "430": 13,          # Player 430 captained 13 times
      "449": 7,
      // ... top 10 captains
    },
    "total_gameweeks": 38
  },
  "chip_usage": {
    "wildcard": {
      "gameweeks": [4, 38],
      "count": 2
    },
    // ... other chips
  },
  "squad": {
    "total_unique_players": 81,
    "most_selected": {
      "1": 34,            # Player 1 in squad 34/38 gameweeks
      "72": 33,
      // ... top 15 squad members
    }
  },
  "transfers": {
    "total": 0,
    "gameweeks_with_transfers": 0
  }
}
```

### Master Summary (`MASTER_SUMMARY.json`)

Aggregated statistics across all 30 managers:
- All top managers' metadata
- Most captained players overall
- Chip usage patterns
- Squad consistency metrics

## Key Findings

### Top Captaincy Choices
Most captained players across the top 30 managers:

1. **Player 430** — 30 selections (2.6%)
2. **Player 449** — 30 selections (2.6%)
3. **Player 5** — 23 selections (2.0%)
4. **Player 16** — 21 selections (1.8%)
5. **Player 381** — 21 selections (1.8%)

### Chip Usage Patterns

| Chip | Total Uses | Per Manager | GW Preferences |
|------|-----------|-------------|---|
| Wildcard | 58 | 1.9 | Early & late season |
| Free Hit | 59 | 2.0 | Mid-season |
| Bench Boost | 60 | 2.0 | Distributed |
| Triple Captain | 60 | 2.0 | Mid & late season |

### Squad Consistency

- **Average unique players per manager**: 68.1
- **Range**: 52-81 players
- **Most selected**: Player 1 (in 34/38 squads across top 30)

## How to Use

### 1. Load a Single Manager's Full Season

```python
import json
from pathlib import Path

manager_id = 3244539  # Ivan Peula
data_dir = Path('season_winners_2025-26')

with open(data_dir / str(manager_id) / '_complete_season.json') as f:
    season_data = json.load(f)  # Keys: 1-38 (gameweeks)

# Access a specific gameweek
gw5_picks = season_data['5']['picks']
```

### 2. Load Strategy Analysis

```python
with open(data_dir / str(manager_id) / 'analysis.json') as f:
    analysis = json.load(f)

print(analysis['captaincy']['top_choices'])
print(analysis['chip_usage'])
print(analysis['squad']['most_selected'])
```

### 3. Compare Multiple Managers

```python
from pathlib import Path
import json

data_dir = Path('season_winners_2025-26')

managers = {}
for mgr_dir in data_dir.glob('*/analysis.json'):
    with open(mgr_dir) as f:
        analysis = json.load(f)
        manager_id = analysis['manager']['manager_id']
        managers[manager_id] = analysis

# Compare captaincy strategies
for mgr_id, analysis in managers.items():
    print(f"{analysis['manager']['player_name']}: {analysis['captaincy']['top_choices']}")
```

### 4. Load Master Summary

```python
with open(data_dir / 'MASTER_SUMMARY.json') as f:
    master = json.load(f)

# Get all top managers
for mgr in master['top_managers']:
    print(f"Rank {mgr['rank']}: {mgr['player_name']} ({mgr['points']} pts)")

# Get most captained players across all managers
print(master['captaincy_meta']['most_captained_overall'])
```

## Use Cases

1. **Captaincy Analysis**: Identify which players top managers consistently chose as captain
2. **Chip Strategy**: Understand optimal timing for wildcard, free hit, etc.
3. **Squad Building**: See which budget/premium players top teams relied on
4. **Transfer Patterns**: Analyze how stable elite teams were (or weren't)
5. **Predictive Modeling**: Use top manager decisions as ground truth for your own predictions
6. **Benchmarking**: Compare your team selections against the elite

## Player ID Mapping

The `element` field in picks refers to player IDs in the FPL API. To convert to player names:

```python
# Get player data from FPL bootstrap
import requests
bootstrap = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/').json()
players = {p['id']: p['web_name'] for p in bootstrap['elements']}

# Now you can look up names
player_id = 430
print(f"Player {player_id} = {players[player_id]}")
```

## Notes

- All data is from the official FPL API (no authentication required for historical data)
- GW data is frozen (entries cannot be changed after the deadline)
- Transfer cost is not included in the current archive (transfers field shows 0)
- Position multipliers: 1 = bench/normal, 2 = captain
- Element types: 1 = GK, 2 = DEF, 3 = MID, 4 = FWD

## Reusing the Notebook

The Jupyter notebook `notebooks/archive_season_winners.ipynb` can be used to:
- Archive a different season (modify year in output paths)
- Archive top N managers (change `get_top_managers(30)` to any number)
- Archive specific manager IDs
- Generate custom analysis summaries

## Generated

- **Date**: 2026-05-27
- **Season**: 2025-26 (GW 1-38)
- **Source**: https://fantasy.premierleague.com/api/

## License

FPL data is provided by the official Fantasy Premier League API. Use subject to FPL terms of service.
