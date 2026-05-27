# Complete FPL Season Winners Archive - Final Manifest

**Status**: ✅ Complete and Corrected  
**Season**: 2025-26 (GW 1-38)  
**Managers**: Top 30 by overall rank  
**Data Quality**: Verified with transfer data corrections

---

## What You Have

### 📊 Raw Gameweek Data
- **Location**: `data/season_winners_2025-26/{manager_id}/gw{n:02d}.json`
- **Files**: 1,140 (38 GWs × 30 managers)
- **Size**: ~6.9 MB
- **Content**: Full squad picks, captain, bench, points, rank, transfers per gameweek

### 📈 Season Consolidation
- **Location**: `data/season_winners_2025-26/{manager_id}/_complete_season.json`
- **Files**: 30 (one per manager)
- **Content**: All 38 gameweeks in a single JSON (easier for analysis)

### 📑 Strategy Analysis (CORRECTED)
- **Location**: `data/season_winners_2025-26/{manager_id}/analysis.json`
- **Files**: 30 (one per manager)
- **Content**:
  - Top 10 captaincy choices with counts
  - Chip usage (wildcard, free hit, boost, triple captain)
  - Squad composition & most-selected players
  - **✓ Transfer statistics (NOW CORRECT)**
  - Performance metrics (best/worst GW, averages)

### 🎯 Master Summary
- **Location**: `data/season_winners_2025-26/MASTER_SUMMARY.json`
- **Content**:
  - All 30 managers' metadata (rank, points, name, team)
  - Most captained players across elite (top 10)
  - Aggregated statistics

### 🔍 Player Mapping (841 players)
- **player_mapping.json** (201 KB) — ID → full info
- **name_to_id.json** (15 KB) — Name → ID lookup
- **players.csv** (35 KB) — Excel/Sheets format

### 🛠️ Utilities
- **lookup.py** — Python convenience functions
- **demo.py** — 6 demo scripts with example analysis
- **regenerate_analysis.py** — Recalculate analysis for all managers

### 📚 Documentation
- **README.md** — Complete archive guide
- **PLAYER_LOOKUP.md** — Player mapping guide
- **QUICKSTART_ARCHIVE.md** — 5-minute getting started
- **TRANSFER_DATA_CORRECTION.md** — Transfer data fix details

---

## Key Statistics

| Metric | Value |
|--------|-------|
| **Managers archived** | 30 |
| **Gameweeks** | 38 |
| **Total JSON files** | 1,140 |
| **Archive size** | 6.9 MB |
| **Players in database** | 841 |
| **Season winner** | Ivan Peula (2,538 pts) |
| **Average transfers** | 37.8 per manager |
| **Most transfers** | Mark Nowell (43) |
| **Least transfers** | Alex Iliev (28) |

---

## Top Insights

### Captaincy
- **Player 430 (Haaland)**: Captained 30 times across top 30 managers (2.6%)
- **Player 449 (B.Fernandes)**: Captained 30 times (2.6%)
- **Player 5 (Gabriel)**: Captained 23 times (2.0%)

### Squad Stability
- **Avg unique players**: 68.1 per manager
- **Most stable player**: Raya (34/38 gameweeks in elite squads)
- **Range**: 52-81 unique players

### Transfer Patterns
- **Total transfers**: 1,135 across all 30 managers
- **Average**: 37.8 per season
- **Winner's transfers**: Ivan Peula made 36 (below average!)
  - **Insight**: Elite play ≠ constant transfers. Strategic selection matters.

### Chip Usage
- **Wildcard**: 58 uses (1.9 per manager)
- **Free Hit**: 59 uses (2.0 per manager)
- **Bench Boost**: 60 uses (2.0 per manager)
- **Triple Captain**: 60 uses (2.0 per manager)

---

## File Structure

```
FPL-Auto/
├── data/season_winners_2025-26/
│   ├── MASTER_SUMMARY.json                    (5.0 KB)
│   ├── README.md
│   ├── PLAYER_LOOKUP.md
│   ├── QUICKSTART_ARCHIVE.md
│   ├── player_mapping.json                    (201 KB)
│   ├── name_to_id.json                        (15 KB)
│   ├── players.csv                            (35 KB)
│   ├── lookup.py
│   ├── demo.py
│   ├── regenerate_analysis.py
│   └── {manager_id}/                          (30 folders)
│       ├── gw01.json - gw38.json             (38 files × 30)
│       ├── _complete_season.json
│       └── analysis.json
│
├── notebooks/
│   └── archive_season_winners.ipynb           (Reusable notebook)
│
├── ARCHIVE_SUMMARY.md
├── QUICKSTART_ARCHIVE.md
├── TRANSFER_DATA_CORRECTION.md
└── COMPLETE_ARCHIVE_MANIFEST.md              (this file)
```

---

## How to Use

### Quick Start (60 seconds)
```python
import json

# Load season winner
with open('data/season_winners_2025-26/3244539/_complete_season.json') as f:
    season = json.load(f)

# View their GW1
gw1 = season['1']
print(f"Points: {gw1['entry_history']['points']}")
print(f"Captain: {next(p['element'] for p in gw1['picks'] if p.get('is_captain'))}")
```

### Analyze Elite Strategy (5 minutes)
```python
import json
from pathlib import Path

# Load analysis for top 3 managers
for mgr_id in [3244539, 1370909, 1761769]:
    analysis = json.load(open(f'data/season_winners_2025-26/{mgr_id}/analysis.json'))
    print(f"{analysis['manager']['player_name']}: {analysis['transfers']['total']} transfers")
```

### Full Data Exploration
See `demo.py` for 6 complete example scripts

---

## Data Quality Assurance

✅ **All 30 managers**: Full 38 gameweeks archived  
✅ **Transfer data**: Corrected and verified (1,135 total)  
✅ **Player mapping**: 841 players with full metadata  
✅ **No authentication required**: Uses official public API  
✅ **Raw data preserved**: Individual GW files always available  

---

## Next Steps

1. **Explore elite captaincy** → Use `player_mapping.json` + analysis data
2. **Study transfer timing** → View `gw_breakdown` in analysis files
3. **Benchmark your team** → Compare against top 30 squad compositions
4. **Build ML models** → Use elite decisions as training labels
5. **Analyze chip strategy** → See when/how elite use chips

---

## Reusability

The **Jupyter notebook** can be adapted to:
- Archive different seasons (e.g., 2024-25)
- Archive more/fewer managers (change `30` to any number)
- Archive specific managers by ID
- Generate custom analyses

---

## Technical Details

- **API Source**: `https://fantasy.premierleague.com/api/`
- **Endpoints Used**:
  - `/entry/{id}/event/{gw}/picks/` — Individual gameweek data
  - `/leagues-classic/1/standings/` — Manager rankings
  - `/bootstrap-static/` — Player metadata
- **No authentication required** for historical data
- **Generated**: 2026-05-27
- **Data as of**: 2026-05-27 (season complete)

---

## Support

**Files with implementation details**:
- `README.md` — Full archive guide with examples
- `PLAYER_LOOKUP.md` — Player mapping documentation
- `QUICKSTART_ARCHIVE.md` — Code examples for common tasks
- `demo.py` — 6 runnable demo scripts

---

**✅ Archive complete and verified**
All data is ready for analysis, modeling, and benchmarking.
