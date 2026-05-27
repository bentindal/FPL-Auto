---
title: Build squad comparison notebook
date: 2026-05-27
priority: high
---

# Build squad comparison notebook

Compare top 100 manager squads against model predictions to identify where the model is weak.

## Metrics to compute

- **Total squad xP** — sum of xP for all 15 players in squad
- **Points-per-player variance** — how consistently top managers pick high-value players
- **ROI** — points gained vs. price spent per player

## Comparison points

- **GW1 squads** — initial team builds (before any transfers)
- **Mid-season squads** — after managers have made transfers (e.g., GW15-20 range)

## Output format

Jupyter notebook with visual comparisons (charts, tables) showing where top 100 squads outperform model predictions.

## Next step

Use findings to inform feature engineering and model retraining. If top 100 managers systematically pick players with significantly higher xP, identify what signal is being missed.

## Data available

`/Users/bentindal/Desktop/coding/FPL-Auto/data/season_winners_2025-26/` — GW-by-GW squad CSVs with transfer history, plus utility scripts (`lookup.py`, `player_mapping.json`, etc.)
