# /init — FPL-Auto project orientation

Read the following files to get full context before starting work:

1. `HANDOFF.md` — architecture, bugs fixed, refactor summary, key file map, run commands
2. `benchmarks/2026-05-26.md` — full benchmark history including all optimisation results
3. `fpl_auto/data.py` — data loading, caching, post-model weightings
4. `fpl_auto/team.py` — squad state + all game logic
5. `fpl_auto/predictor.py` — pluggable ML model abstraction

## Key facts to remember

- Python: `/Library/Frameworks/Python.framework/Versions/3.10/bin/python3`
- Run a season: `python3 manager.py -season 2021-22`
- Run 3 seasons in parallel: `python3 manager.py -seasons 2021-22 2022-23 2023-24`
- Run tests: `python3 -m unittest tests -v` (22 tests, all passing)
- Generate predictions: `python3 model.py -season 2021-22 -save`

## Current performance (post-optimisation)

- Single season (~8s), 3 seasons parallel (~12s wall time)
- 2021-22: 1827 pts | 2022-23: 1839 pts | 2023-24: 1392 pts

## Critical architecture distinction

- `_xp_dicts` — single-GW raw predictions from TSVs. Used **only** in `suggest_subs`.
- `_all_xp_dicts` — multi-GW discounted lookahead from `discount_next_n_gws`. Used everywhere strategic: captain, transfers, chips, `team_xp`.

Using the wrong source for either degrades results significantly.

## Data flow

```
model.py -save  →  predictions/{season}/GW{n}/{pos}.tsv
                        ↓
manager.py  →  team.__init__  →  fpl.get_predictions(gw, pos)
                                        ↓
                              discount_next_n_gws (5 GW lookahead, 0.8 discount)
                                        ↓
                              _all_xp_dicts  →  transfers / captain / chips
```
