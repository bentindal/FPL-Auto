# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
PY=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3

# Run all tests
$PY -m unittest tests -v

# Run a single test class or method
$PY -m unittest tests.TestTransferInAllowed -v
$PY -m unittest tests.TestTransferInAllowed.test_club_rule_max_three -v

# Simulate a full season
$PY manager.py -season 2021-22

# Simulate multiple seasons in parallel
$PY manager.py -seasons 2021-22 2022-23 2023-24

# Generate prediction TSVs (required before running manager for a new season)
$PY model.py -season 2021-22 -save

# Lint
flake8 fpl_auto/ manager.py model.py tests.py

# Profile
$PY -m cProfile -o profile.out manager.py -season 2021-22
$PY -c "import pstats; p=pstats.Stats('profile.out'); p.sort_stats('cumulative'); p.print_stats(30)"
```

## Architecture

Two entry points:

- **`model.py`** — trains sklearn models (one per position), writes predictions to `predictions/{season}/GW{n}/{GK|DEF|MID|FWD}.tsv`
- **`manager.py`** — reads those TSVs, simulates a full season week-by-week. `run_season(config)` is a standalone function called via `multiprocessing.Pool` for parallel runs.

### Data flow

```
model.py -save  →  predictions/{season}/GW{n}/{pos}.tsv
                          ↓
manager.py  →  team.__init__  →  fpl_data.get_predictions(gw, pos)  [cached]
                                          ↓
                                discount_next_n_gws(n=5, factor=0.8)
                                          ↓
                                _all_xp_dicts  →  transfers / captain / chips
```

### `fpl_auto/` package

- **`data.py`** — `fpl_data` class: CSV loading with multi-level caching, fixture-adjusted xP computation (`post_model_weightings`), multi-GW discounting (`discount_next_n_gws`). A module-level `get_fpl_data(location, season)` returns a shared instance per season so caches persist across all 38 GW iterations.
- **`team.py`** — `team` class: full squad state + game logic (transfers, subs, captain, chips, scoring). Instantiated once per GW inside the season loop in `manager.py`.
- **`predictor.py`** — `Predictor` class: wraps sklearn models. `Predictor.TYPES = ('gradientboost', 'linear', 'randomforest', 'neuralnetwork')`. Used only by `model.py`.
- **`evaluate.py`** — metrics and plot helpers. Used by `manager.py` when `-save` or plot flags are passed.

### Critical xP source distinction

`team.__init__` builds **two** separate xP lookup dicts:

- `_xp_dicts` — raw single-GW predictions from TSVs. Used **only** in `suggest_subs` (bench the weakest player for the next game).
- `_all_xp_dicts` — multi-GW discounted lookahead from `discount_next_n_gws`. Used for every strategic decision: captain, transfers, chips, `team_xp`.

Using the wrong source for either causes a measurable points regression.

### Season loop (manager.py)

Each GW: `auto_transfer → auto_subs → auto_captain → auto_chips → team_xp → team_p → result_summary → return_subs_to_team → new team instance for next GW`.

### Caches in `fpl_data`

| Cache | Key | Eliminates |
|---|---|---|
| `_gw_cache` | `(season, week_num)` | repeated per-GW CSV reads |
| `_fixtures_cache` | `season` | 19k+ CSV reads per season |
| `_prediction_cache` | `(gw, pos)` | 152 TSV reads per season |
| `_recent_gw` | — | 38 HTTP requests per season |

All caches live on the shared `fpl_data` instance and persist for the full season run.

### Constants (`team.py`)

```python
POSITIONS = ['GK', 'DEF', 'MID', 'FWD']
MAX_PER_POS = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
MIN_PRICE   = {'GK': 4.0, 'DEF': 4.0, 'MID': 4.5, 'FWD': 4.5}
SQUAD_SIZE  = 15
```

### Data

Historical GW and fixture CSVs live under `data/{season}/`. Sourced from [vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League). Seasons available: `2021-22`, `2022-23`, `2023-24`, `2024-25`.
