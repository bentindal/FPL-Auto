# FPL-Auto Handoff

## What this project is
Fully autonomous FPL team manager. Two entry points:
- `model.py` — trains sklearn models per position, writes prediction TSVs to `predictions/{season}/GW{n}/[GK|DEF|MID|FWD].tsv`
- `manager.py` — reads those TSVs, simulates a full season week-by-week (transfers, subs, chips, captain)

## Python interpreter
`/Library/Frameworks/Python.framework/Versions/3.10/bin/python3` — this is the one with all deps installed.

---

## What was done this session

### Bugs fixed
- Mutable default arg `players=[]` in `team.__init__` — all instances shared lists
- `force=False` hardcoded inside `add_player`, silently ignoring the parameter
- Double captain 2× multiplier (applied in both `get_all_xp` and `team_xp`)
- Missing duplicate player check in `transfer_in_allowed`
- Off-by-one in max-per-position check (`>= max+1` → `>= max`)
- Squad-full check wrong (`>= 16` → `>= SQUAD_SIZE=15`)
- `swap_players_who_didnt_play` crashing when same sub processed twice

### Refactor
- `team.py`: 1705 → ~700 lines. All 15× repeated 4-position branches replaced with `_pos_squad_list(pos)`, `_all_xi_players()`, `_all_squad_players()` helpers
- `fpl_auto/predictor.py`: new file — all ML code extracted from `data.py`. Clean `Predictor` class: `.fit(training_data)`, `.predict(features)`, `.to_dataframes()`
- `data.py`: ML imports and `get_model()` removed — pure data loading only
- `model.py`: updated to use `Predictor`, model type driven through `Predictor.TYPES`
- `manager.py`: fully restructured — `run_season(config)` is a standalone function, supports `-seasons` for parallel runs via `multiprocessing.Pool`

### Tests
- Expanded from 6 → 22 tests covering: transfer validation, squad rules, substitutions, captaincy, duplicate detection, mutable default isolation, position constants
- All 22 passing
- Run with: `/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m unittest tests -v`

### Performance optimisations
Key data source distinction (important):
- `_xp_dicts` — single-GW raw predictions from TSVs. Used **only** in `suggest_subs` (correct: bench weakest for next game)
- `_all_xp_dicts` — multi-GW discounted lookahead from `all_xp`. Used everywhere strategic: captain, transfers, chips, `team_xp`

Optimisations applied:
1. `fpl_data._gw_cache` — gw CSV reads cached by `(season, week_num)`
2. `fpl_data._fixtures_cache` — `fixtures.csv` cached by season ← **this was the big win** (19,498 reads → 1)
3. `_all_xp_dicts` built once in `__init__`, `player_xp` uses dict lookup instead of rebuilding per call
4. `_pos_cache` — `player_pos` lookups cached per instance
5. `_pos_squad_list` — replaced dict-literal-per-call with if/elif chain
6. `suggest_transfer_in` — `get_club_counts` + `gw_prices` pre-computed once, passed through to `transfer_in_allowed`
7. `multiprocessing.Pool` — multiple seasons run in parallel via `-seasons 2021-22 2022-23 2023-24`

---

## Benchmarks

| Run | Code state | Time | Points | Notes |
|---|---|---|---|---|
| Baseline | Original pre-refactor | 3m 28s | 1713 | |
| Post-refactor | Bug fixes applied | 3m 18s | 1811 | +98 pts from bug fixes |
| Wrong xp source | `_xp_dicts` (single GW) used everywhere | 3m 37s | 1758 | Behavioural regression |
| Fixtures cached | `_fixtures_cache` added | **2m 20s** | 1811 | -58s from baseline |

Profiler output: `profile.out` + `profile_report.txt` on disk.
Profile showed: `get_future_fixtures` → `read_csv` was 54% of all time (19,498 calls, 152s of 284s total).

**Parallel 3-season run** (`-seasons 2021-22 2022-23 2023-24`) was in-flight when this was written — result not yet captured.

---

## What's next / open threads

1. **Parallel benchmark result** — still running. Expected ~2-2.5 min wall time for all 3 seasons simultaneously.
2. **`post_model_weightings` is still slow** — after the fixtures cache fix there's still ~80s of time in `post_model_weightings` building per-player DataFrames. Could vectorise: instead of iterating players in Python, use pandas merge/groupby on the whole predictions DataFrame at once.
3. **Update `benchmarks/2026-05-26.md`** — the file exists but only has the original baseline. Should add the post-optimisation numbers.
4. **Ben's improvement ideas** — not yet discussed. He has ideas for improving prediction quality (mentioned at start of session, deferred until modernisation was done).

---

## Key file map
```
fpl_auto/
  data.py       — data loading, GW + fixtures cache
  predictor.py  — ML model abstraction (new this session)
  team.py       — squad state + all game logic (refactored)
  evaluate.py   — metrics + visualisation (unchanged)
model.py        — CLI: train models, write prediction TSVs
manager.py      — CLI: simulate seasons (-season / -seasons)
tests.py        — 22 unit tests
benchmarks/     — timing records
profile.out     — cProfile binary output
profile_report.txt — human-readable top-30 hotspots
```

## Running things
```bash
PY=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3

# Single season
$PY manager.py -season 2021-22

# Parallel multi-season
$PY manager.py -seasons 2021-22 2022-23 2023-24

# Tests
$PY -m unittest tests -v

# Generate predictions (needed before running manager)
$PY model.py -season 2021-22 -save

# Profile
$PY -m cProfile -o profile.out manager.py -season 2021-22
$PY -c "import pstats; p=pstats.Stats('profile.out'); p.sort_stats('cumulative'); p.print_stats(30)"
```
