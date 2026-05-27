# FPL-Auto: Performance Optimization System

## What This Is

A system for improving Fantasy Premier League (FPL) season simulations by enhancing player xP predictions and evaluating multiple decision-making strategies (transfers, captaincy, chip usage, bench selection). The goal is to maximize total points scored across historical seasons while maintaining temporal integrity — only using data available at each gameweek.

## Core Value

Maximize total points the simulated team achieves across historical seasons through better predictions and smarter strategic decisions.

## Requirements

### Validated

- ✓ Existing simulation framework (manager.py, team.py, data pipeline)
- ✓ Historical season data (2021-22 through 2024-25)
- ✓ Top 100 manager season archive (source of performance signal)
- ✓ Multi-GW discounting and xP prediction infrastructure

### Active

- [ ] Diagnose model prediction weaknesses through squad comparison analysis
- [ ] Improve xP model accuracy via feature engineering and retraining
- [ ] Build flexible strategy experimentation framework
- [ ] Implement and evaluate transfer decision strategies
- [ ] Implement and evaluate chip usage strategies
- [ ] Implement and evaluate captaincy strategies
- [ ] Implement and evaluate bench/substitution strategies
- [ ] Compare strategy archetypes (conservative vs aggressive vs differential-focused)
- [ ] Measure and validate improvements against historical baseline

### Out of Scope

- Real-time FPL integration (simulations are offline, historical analysis only)
- Natural language explanations of strategy choices (numerical comparison sufficient)
- Multi-player collaborative simulation
- Mobile app or public-facing UI

## Context

**Technical Environment:**
- Python 3.10+ with sklearn models (gradientboost, linear, randomforest, neuralnetwork)
- Season-by-season predictions cached in TSV format
- Existing xP computation with fixture-adjusted weighting and multi-GW discounting
- GW-by-GW simulation loop with weekly decision points

**Data Sources:**
- FPL historical data (fixtures, player stats, prices) from vaastav/Fantasy-Premier-League
- Top 100 manager squad compositions and transfer history for each season
- Generated ML predictions (one per position per GW)

**Key Insight:**
Top 100 managers systematically outperform the current simulation. Comparing their squad choices to model predictions will reveal what signal is being missed.

## Constraints

- **Temporal Integrity**: Models and strategies can only see data available at that gameweek. No lookahead bias (e.g., future injury news, future form). Critical for fair historical backtesting.
- **Compatibility**: Must work with existing data pipeline and codebase. Avoid breaking changes to manager.py or team.py core logic.
- **Reproducibility**: Results must be reproducible across runs (seeded randomness, deterministic data loading).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Start with model diagnostics (squad comparison) | Top 100 performance gap suggests models are weak before strategy improvements help | — Pending |
| Compare multiple strategy archetypes, not just tweak current | Early exploration showed current strategy has room for fundamental improvement | — Pending |
| Maintain temporal integrity as hard constraint | Without it, backtesting is meaningless (will overfit to hindsight) | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-27 after initialization*
