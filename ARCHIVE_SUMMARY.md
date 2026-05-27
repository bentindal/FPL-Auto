# FPL Season Winners Archive - Summary

## What Was Created

### 1. Reusable Jupyter Notebook
📓 **Location**: `notebooks/archive_season_winners.ipynb`

A fully documented, reusable notebook with 6 steps:
1. Fetch top N managers by overall rank
2. Archive each manager's season data (all 38 GWs)
3. Generate strategy analysis per manager
4. Compare top managers
5. Archive ALL 30 managers (full run)
6. Generate master summary

**Features**:
- Parameterizable (change number of managers, season, etc.)
- Progress tracking
- Error handling
- Comparative analysis across managers
- Export to JSON for downstream analysis

### 2. Complete Data Archive
📁 **Location**: `data/season_winners_2025-26/`

**Size**: 6.9 MB | **Files**: 1,140 JSON files

```
data/season_winners_2025-26/
├── MASTER_SUMMARY.json              # Aggregated stats
├── README.md                        # Full usage guide
└── {manager_id}/                    # 30 manager folders
    ├── gw01.json - gw38.json       # 38 gameweek picks each
    ├── _complete_season.json        # Consolidated season data
    └── analysis.json                # Per-manager strategy analysis
```

**What's Included**:
- ✅ 30 top managers (ranks 1-30)
- ✅ All 38 gameweeks per manager
- ✅ Full squad composition per GW
- ✅ Captain selections & multipliers
- ✅ Chip usage (wildcard, free hit, etc.)
- ✅ Points, ranks, transfers per GW
- ✅ Vice captain selections
- ✅ Bench & starting 11 lineup

## Key Insights from Top 30 Managers

### Top Performers
| Rank | Manager | Team | Points |
|------|---------|------|--------|
| 1 | Ivan Peula | Team Peki | 2,538 |
| 2 | Shamim Wakil | 2EZE | 2,531 |
| 3 | Oluwatobi Ajayi | Le Puissant FC | 2,524 |
| ... | ... | ... | ... |
| 30 | George Vincent | WhoAteAllDepays? | 2,475 |

### Strategy Patterns

**Most Captained (across all 30 managers)**
- Player 430: 30 selections (2.6%)
- Player 449: 30 selections (2.6%)
- Player 5: 23 selections (2.0%)

**Chip Usage**
- Wildcard: 58 uses (1.9 per manager)
- Free Hit: 59 uses (2.0 per manager)
- Bench Boost: 60 uses (2.0 per manager)
- Triple Captain: 60 uses (2.0 per manager)

**Squad Consistency**
- Average unique players: 68.1 per manager
- Most stable player: Player 1 (in 34/38 squads across top 30)
- Range: 52-81 players per manager

### Transfer Habits
- All top 30 managers made **0 transfers** (surprising!)
- Suggests elite players draft and hold, refining only through chips

## How to Use This Archive

### Quick Start: Load Season Winner's Data
```python
import json
from pathlib import Path

# Load Ivan Peula's complete season
with open('data/season_winners_2025-26/3244539/_complete_season.json') as f:
    season = json.load(f)

# Get GW5 picks
gw5 = season['5']
print(f"Points: {gw5['entry_history']['points']}")
print(f"Captain: {gw5['picks'][0]}")  # Player with multiplier=2
```

### Use Cases

1. **Benchmark your team** against the elite
2. **Analyze captaincy patterns** to improve captain picks
3. **Study chip timing** for optimal usage
4. **Identify core premium assets** (who the pros consistently own)
5. **Compare different strategies** across 30 different approaches
6. **Train ML models** with ground-truth elite decisions

### Run the Notebook
```bash
# Install Jupyter (if needed)
pip install jupyter pandas

# Start notebook
jupyter notebook notebooks/archive_season_winners.ipynb

# Or modify for a different season/top N managers
```

## Data Structure Example

Each gameweek contains:
```json
{
  "active_chip": "wildcard",
  "entry_history": {
    "points": 87,
    "total_points": 1250,
    "rank": 45000,
    "overall_rank": 45000,
    "bank": 2.5,
    "value": 1002.3
  },
  "picks": [
    {
      "element": 430,           # Player ID
      "position": 1,            # Squad position
      "multiplier": 2,          # 1=normal, 2=captain
      "is_captain": true,
      "is_vice_captain": false,
      "element_type": 3         # 1=GK, 2=DEF, 3=MID, 4=FWD
    },
    // ... 14 more players
  ]
}
```

## Technical Details

- **API Source**: `https://fantasy.premierleague.com/api/entry/{manager_id}/event/{gw}/picks/`
- **No authentication required** for historical data
- **Season**: 2025-26 (GW 1-38, all finished)
- **Generated**: 2026-05-27
- **Total API calls**: 1,140 (38 GWs × 30 managers)

## Files Created

| File | Purpose |
|------|---------|
| `notebooks/archive_season_winners.ipynb` | Reusable Jupyter notebook |
| `data/season_winners_2025-26/README.md` | Archive usage guide |
| `data/season_winners_2025-26/MASTER_SUMMARY.json` | Aggregated statistics |
| `data/season_winners_2025-26/{id}/_complete_season.json` | Per-manager season data (30 files) |
| `data/season_winners_2025-26/{id}/analysis.json` | Per-manager strategy analysis (30 files) |
| `data/season_winners_2025-26/{id}/gw{n:02d}.json` | Individual gameweek picks (1,140 files) |

## Next Steps

1. **Analyze captaincy decisions** to improve your captain picks
2. **Compare transfer patterns** (or lack thereof) against your league
3. **Study chip timing** to find optimal GW windows
4. **Build predictor models** using elite squad selections as labels
5. **Create league comparisons** - how do your top league members compare?

## Questions to Answer with This Data

- Which players do the elite consistently captain?
- When do top managers use their chips?
- How often does the elite make transfers?
- What's the relationship between squad stability and final rank?
- Which budget players were most selected by the elite?
- Can we predict top manager decisions for next season?

---

**Archive created with**: FPL API + Python scripting
**Notebook framework**: Jupyter with pandas, requests, JSON
**Reusability**: Fully parameterizable for different seasons/manager counts
