# Player ID → Name Mapping Guide

Complete mapping of all 841 FPL players from season 2025-26.

## Quick Lookups

### Most Captained Players (Elite Top 30)
| Player ID | Name | Position | Team | Price |
|-----------|------|----------|------|-------|
| **430** | **Haaland** | FWD | Man City | £14.70 |
| **449** | **B.Fernandes** | MID | Man United | £10.40 |
| **5** | **Gabriel** | DEF | Arsenal | £7.30 |
| **16** | **Saka** | MID | Arsenal | £10.00 |
| **381** | **M.Salah** | MID | Liverpool | £14.00 |

### Other Frequently Selected Players
| Player ID | Name | Position | Team | Price |
|-----------|------|----------|------|-------|
| **1** | **Raya** | GK | Arsenal | £6.00 |
| **72** | (in 33/38 squads) | | | |
| **373** | (in 31/38 squads) | | | |
| **47** | (in 30/38 squads) | | | |
| **565** | (in 29/38 squads) | | | |

---

## Files Available

### 1. **player_mapping.json** (ID → Full Info)
Complete info for all 841 players, keyed by ID.

```json
{
  "430": {
    "id": 430,
    "name": "Haaland",
    "full_name": "Erling Haaland",
    "position": 4,
    "position_name": "FWD",
    "team": 13,
    "team_code": "MCI",
    "price": 14.7,
    "selected_by_percent": "99.8",
    "status": "a"
  },
  // ... 840 more players
}
```

### 2. **name_to_id.json** (Name → ID)
Quick reverse lookup to find player ID by name.

```json
{
  "Haaland": 430,
  "B.Fernandes": 449,
  "Gabriel": 5,
  "Saka": 16,
  "M.Salah": 381,
  // ... 836 more
}
```

### 3. **players.csv** (Spreadsheet Format)
All players in CSV format for Excel/Google Sheets.

```
ID,Name,Full Name,Position,Team,Price,Selected %
1,Raya,David Raya,GK,1,6.0,73.5
5,Gabriel,Gabriel dos Santos,DEF,1,7.3,65.2
16,Saka,Bukayo Saka,MID,1,10.0,72.1
...
```

### 4. **lookup.py** (Python Utility)
Convenience functions for lookups in Python.

---

## How to Use

### Option 1: Direct JSON Load (Python)
```python
import json

# Load player mapping
with open('data/season_winners_2025-26/player_mapping.json') as f:
    players = json.load(f)

# Look up Player 430
player_430 = players['430']
print(f"Player 430: {player_430['name']} ({player_430['position_name']})")
# Output: Player 430: Haaland (FWD)
```

### Option 2: Use Lookup Functions (Python)
```python
from data.season_winners_2025-26.lookup import id_to_name, get_player_info

# Get name
name = id_to_name(430)  # Returns "Haaland"

# Get full info
info = get_player_info(430)
print(f"{info['name']} - {info['position_name']} - £{info['price']}")
# Output: Haaland - FWD - £14.7
```

### Option 3: Reverse Lookup (Name → ID)
```python
from data.season_winners_2025-26.lookup import name_to_id

# Find player by name
haaland_id = name_to_id('Haaland')  # Returns 430
print(f"Haaland's ID: {haaland_id}")
```

### Option 4: Excel/Google Sheets
Open `players.csv` in Excel or Google Sheets to browse all 841 players.

### Option 5: Command Line Lookup
```bash
# Show player info
python data/season_winners_2025-26/lookup.py

# Or search manually
grep "430" data/season_winners_2025-26/players.csv
grep "Haaland" data/season_winners_2025-26/players.csv
```

---

## Enhanced Archive

Now you can map all picks to player names:

```python
import json
from data.season_winners_2025-26.lookup import id_to_name

# Load a manager's season
with open('data/season_winners_2025-26/3244539/_complete_season.json') as f:
    season = json.load(f)

# View GW1 with player names
gw1 = season['1']
print("GW1 Squad:")
for i, pick in enumerate(gw1['picks'], 1):
    name = id_to_name(pick['element'])
    captain = " (C)" if pick.get('is_captain') else ""
    print(f"  {i:2d}. {name:25s}{captain}")
```

---

## Data Fields Explanation

### Position Codes
- `1` = GK (Goalkeeper)
- `2` = DEF (Defender)
- `3` = MID (Midfielder)
- `4` = FWD (Forward)

### Team Codes
- `1` = Arsenal, `2` = Aston Villa, `3` = Bournemouth
- `4` = Brentford, `5` = Brighton, `6` = Chelsea
- `7` = Crystal Palace, `8` = Everton, `9` = Fulham
- `10` = Ipswich, `11` = Leicester, `12` = Liverpool
- `13` = Man City, `14` = Man United, `15` = Newcastle
- `16` = Nottingham, `17` = Southampton, `18` = Tottenham
- `19` = West Ham, `20` = Wolves

### Other Fields
- `price`: Current price in £ millions (divide by 10 in API, already corrected)
- `selected_by_percent`: % of all FPL players who own this player
- `status`: "a" = available, "s" = suspended, "u" = unknown

---

## Example: Analyze Elite Captain Choices with Names

```python
import json
from data.season_winners_2025-26.lookup import id_to_name

# Load master summary
with open('data/season_winners_2025-26/MASTER_SUMMARY.json') as f:
    master = json.load(f)

# Show top captains with names
print("Most captained players across top 30 managers:")
captains = master['captaincy_meta']['most_captained_overall']
for player_id, count in list(captains.items())[:10]:
    name = id_to_name(int(player_id))
    pct = (count / (30 * 38)) * 100
    print(f"  {name:25s}: {count:2d} times ({pct:.1f}%)")
```

Output:
```
Most captained players across top 30 managers:
  Haaland                  : 30 times (2.6%)
  B.Fernandes              : 30 times (2.6%)
  Gabriel                  :23 times (2.0%)
  Saka                     : 21 times (1.8%)
  M.Salah                  : 21 times (1.8%)
```

---

## All 841 Players

Complete list available in:
- `player_mapping.json` (841 entries with full details)
- `name_to_id.json` (841 name→ID mappings)
- `players.csv` (841 rows for spreadsheet import)

---

## Integration with Archive Data

Every gameweek file in the archive references players by ID:

```json
{
  "picks": [
    {"element": 430, ...},  // ID reference
    {"element": 449, ...},
    // ...
  ]
}
```

Use the mapping files to convert these IDs to human-readable names for analysis and reporting.

---

**Generated**: 2025-26 Season
**Total Players**: 841
**Data Source**: FPL Bootstrap API
