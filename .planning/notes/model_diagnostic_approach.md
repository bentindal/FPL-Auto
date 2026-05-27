---
name: model_diagnostic_approach
description: Testing strategy for identifying where xP models are weak by comparing top 100 manager squads to predictions
metadata:
  type: note
  date: 2026-05-27
---

# Model Diagnostic Approach

## Hypothesis

The xP models are weak in certain areas. Top 100 managers, through real skill and domain experience, pick players that the model systematically underrates.

## Testing strategy

Compare top 100 manager squad composition against what the model predicts, at two key points in the season:

1. **GW1** — Initial team selection, before managers have made any transfers. Pure squad-building skill.
2. **Mid-season** — After ~15 GWs of transfers. Shows which players managers identified as improving or declining.

## Metrics

- **Total squad xP** — If top 100 squads have 10%+ higher xP, the model is missing value
- **Points-per-player variance** — Are top managers' picks more consistent in quality, or do they take bigger swings?
- **ROI** — Points earned per pound spent. Higher ROI suggests better value identification

## Decision tree

- If findings are clear (e.g., "top 100 squads have 15% higher xP"), identify what signal is missing and improve feature engineering
- If findings are mixed, drill deeper — slice by position, form, fixture, price range
- If no clear gap, consider whether the model is already close to optimal and focus on strategy (transfers, captain, chips) instead

## Data source

`data/season_winners_2025-26/` — GW-by-GW squad CSVs, transfer history, player mappings
