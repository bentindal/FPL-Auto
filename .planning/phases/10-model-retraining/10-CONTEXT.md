# Phase 10: Model Retraining & Time-Series Optimization - Context

**Gathered:** 2026-05-28  
**Status:** Ready for planning  
**Source:** Research Complete (10-MODEL-RETRAINING-RESEARCH.md)

---

<domain>

## Phase Boundary

**What this phase delivers:** A production-grade model retraining pipeline that automatically updates position-specific ensemble models every 2-4 gameweeks, detects performance drift using PELT change-point analysis, and exports predictions compatible with manager.py. The system operates on an expanding time-window (cumulative historical + live data) with position-specific XGBoost + RandomForest ensembles trained via TimeSeriesSplit.

**End-to-end flow:**
1. **Data Collection** — FPL API (official) + Understat (advanced metrics) fetch weekly post-GW; accumulated_gw.csv grows
2. **Scheduled Retraining** — Every 2 GWs (default) or triggered by 15% RMSE drift alarm
3. **Model Training** — Position-specific ensembles on cumulative historical (2019-2024) + live 2024-25 data
4. **Drift Detection** — PELT algorithm flags structural breaks; triggers unscheduled retrain if persistent
5. **Orchestration** — Apache Airflow DAG executes post-GW (Tuesday 19:00 UTC); Prefect monitors drift in-between
6. **Prediction Export** — TSV files compatible with manager.py consumption (GK/DEF/MID/FWD predictions for GW+1 through GW+6)

**Exit Criteria:** System runs automated retraining on 2024-25 season (GWs 1-5+), metrics tracked, thresholds validated, runbooks documented.

</domain>

---

<decisions>

## Implementation Decisions

### Retraining Frequency
- **Decision:** Retrain every 2 gameweeks (scheduled baseline) with event-driven override
- **Rationale:** Research (Arxiv 2505.00356) demonstrates 2-4 GW frequency optimal on 40K+ series; more frequent retraining introduces noise; less frequent misses structural changes. Weekly retraining costs 75%+ more compute with <2% accuracy gain
- **Override Condition:** If RMSE on rolling 4-GW window exceeds baseline by >15% for 2+ consecutive GWs, trigger unscheduled retrain (minimum 1 GW cooldown to avoid thrashing)

### Window Strategy
- **Decision:** Expanding window (all historical + accumulated live GWs)
- **Rationale:** Models trained on 2019-2024 baseline (190 GWs) capture seasonal patterns. New GWs accumulate naturally. Early seasons provide stability; recent GWs capture drift. Expanding window superior to rolling for stable domains like FPL
- **Minimum Training Size:** 190 GWs (5 seasons: 2019-2023) before tuning on 2024-25 live data

### Drift Detection Algorithm
- **Decision:** PELT (Pruned Exact Linear Time) with 15% RMSE threshold
- **Rationale:** O(n) complexity, proven on financial/forecasting tasks, detects change points without predefined thresholds. 15% accounts for ~5-10% weekly noise in FPL, requires structural change (injuries/formations/fixtures)
- **Trigger Condition:** RMSE > baseline_rmse × 1.15 AND persists 2+ GWs AND position's RMSE > 1.5 × baseline_std_dev
- **Alternative (lower priority):** ADWIN for continuous monitoring; DDM not recommended (binary assumption doesn't fit regression)

### Position-Specific Models
- **Decision:** Separate XGBoost + RandomForest ensemble per position (GK/DEF/MID/FWD)
- **Rationale:** Position-specific patterns (saves for GK, clean sheets for DEF, goals for FWD). Single model captures neither. Ensemble reduces variance vs single model
- **Validation:** TimeSeriesSplit (3 folds) for fast CV; final train on all data after validation passes

### Data Collection Strategy
- **Decision:** Dual-source (FPL Official API + Understat) for live 2024-25; Vaastav archive for 2019-2023
- **FPL API Endpoints:** bootstrap-static, element-summary/{id}, fixtures (daily frequency post-GW)
- **Understat:** understatapi library for xG, xA, shots, key passes (free tier)
- **Data Format:** accumulated_gw.csv with columns [gw, player_id, position, team, xp, minutes, goals, assists, xg, xa, shots, key_passes, bps, points]
- **QA Check:** Validate each GW has >500 players, >400 actuals, >400 xP, valid positions

### Orchestration Platform
- **Decision:** Apache Airflow (scheduled) + Prefect (drift-driven, optional)
- **Rationale:** Airflow mature, declarative DAGs, enterprise-grade for batch retraining. Prefect lighter, better for event-driven (drift). Hybrid approach recommended
- **Airflow Schedule:** Post-GW Tuesday 19:00 UTC (times 2-7, accounting for match window variations)
- **Tasks:** collect → validate → retrain → evaluate → export

### Monitoring Metrics
- **Primary:** RMSE per position (detect drift), MAE (prediction accuracy), R² (3-week rolling)
- **Secondary:** Bias (systematic over/under-prediction), Spearman correlation (ranking quality for captain selection)
- **Alert Thresholds:** RMSE >15% baseline triggers drift; MAE >0.8 pts/player; R² <0.80; rank correlation <0.85
- **Dashboard:** Real-time metrics per position tracked post-GW

### Lookahead Discount Factor
- **Decision:** Maintain existing manager.py discount_next_n_gws(factor=0.8, n=6)
- **Rationale:** GW+1 predictions most accurate; GW+6 highly uncertain. Discount reduces weighting for distant GWs. Retraining every 2 GWs primarily benefits GW+1; GW+6 stable under discount
- **Integration:** Manager.py consumes predictions unchanged; no modification to discount logic required

### Claude's Discretion

**Implementation approach choices not locked by research:**

- **Hyperparameters:** Research suggests GB (learning_rate=0.05, max_depth=5, n_estimators=500) as baseline. Specific tuning per position (GK vs FWD) deferred to implementation task
- **Ensemble voting:** Research recommends median of 50 trees; implementation will test weighted voting vs simple average
- **External feature flags:** Fixture difficulty (FPL API), injury status, seasonal phase — deferred to Phase 11 (enhancement post-launch)
- **Backfill strategy:** For 2024-25 historical gap (pre-live season), implementation will decide whether to synthetically backfill or train fresh from GW1
- **Model persistence:** Whether to save checkpoint models per GW or only latest (trade-off: disk space vs recovery)

</decisions>

---

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning:**

### Research & Strategy
- `.planning/research/10-MODEL-RETRAINING-RESEARCH.md` — Full research including retraining frequency study (Arxiv 2505.00356), drift detection methods (PELT ref: 2506.14133), FPL-specific considerations, tool stack recommendations, implementation pseudocode

### Architecture & Existing Code
- `CLAUDE.md` — Commands for model.py (-save), data layout, `discount_next_n_gws()` signature
- `fpl_auto/data.py` — `fpl_data` class, prediction caching, TSV prediction format consumed by team.py
- `manager.py` — Entry point for predictions, season loop structure, team instantiation
- `fpl_auto/team.py` — `_all_xp_dicts` usage (lookahead discount already integrated)
- `fpl_auto/predictor.py` — Predictor class, sklearn regressor pattern to replicate

### Phase Dependencies
- `.planning/phases/03-model-infrastructure/03-01-CONTEXT.md` — TimeSeriesSplit baseline, Pipeline pattern, baseline metrics
- `.planning/phases/04-feature-engineering/04-01-CONTEXT.md` — Feature registry, VIF thresholds, feature rollout schedule
- `.planning/phases/05-strategy-framework/05-01-CONTEXT.md` — StrategyConfig design, walk-forward validation pattern

### Tools
- [Skforecast documentation](https://skforecast.org/) — Walk-forward validation helpers, multi-step forecasting for 6-GW lookahead
- [Apache Airflow documentation](https://airflow.apache.org/) — DAG definitions, task dependencies, scheduling
- [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) — Expanding window CV pattern

</canonical_refs>

---

<specifics>

## Specific Ideas from Research

### Retraining Schedule (First Season 2024-25)
```
GW1 released:  Train on 2019-2023 + GW1 (195 GWs); predict GW2-7
GW3 released:  Train on 2019-2023 + GW1-3 (197 GWs); predict GW4-9
GW5 released:  Train on 2019-2023 + GW1-5 (199 GWs); predict GW6-11
... every 2 GWs through GW38
```

### Position-Specific Hyperparameters (from research)
```
GK: XGBoost focused on saves, high regularization (max_depth=4)
DEF: XGBoost + RandomForest ensemble, clean sheet emphasis
MID: Balanced goals/assists, default depth=5
FWD: Goal-heavy features, deep tree tolerance (max_depth=6)
```

### Drift Detection in Practice
```
Monitor RMSE per position over 4-GW rolling window.
Baseline established from 2019-2023 training.
If RMSE(GW[t-4:t]) > baseline × 1.15:
  → Investigate cause (injuries? formation shift? fixture spike?)
  → If confirmed structural, retrain immediately
  → Log anomaly for post-season audit
```

### Data QA Checks
- Each GW validates: >500 players, >400 actuals, >400 xP, positions ∈ [GK, DEF, MID, FWD]
- FPL + Understat merge on player_id; conflicts logged
- Vaastav CSVs used raw for 2019-2023; no post-hoc updates expected during season

### Metric Thresholds (Validated on 2024-25 live data)
- Drift trigger: RMSE >15% above rolling 4-GW mean
- Minimum retraining interval: 7 days (1 GW) to avoid thrashing
- Cross-fold stability indicator: if R² std-dev / mean < 0.15 (high stability), keep 2-GW frequency; if <0.10 (very high), could reduce to 4-GW

</specifics>

---

<deferred>

## Deferred Ideas

### Phase 10 Out-of-Scope (Planned for Phase 11+)

1. **Fixture difficulty weighting** — FPL API provides 1-5 scale per opponent; not integrated in Phase 10 baseline
2. **Injury/suspension prediction** — FPL API shows current status; predictive models deferred
3. **Seasonal phase features** — GW number, burn-out patterns; lower priority vs recency
4. **Form volatility features** — Could add rolling std-dev; captured implicitly in recent-GW emphasis
5. **Advanced ensemble techniques** — Stacking, meta-learning; baseline voting/median sufficient for Phase 10
6. **Real-time updates during matches** — Phase 10 batch post-GW; live partial updates (GW event/live) Phase 11
7. **Multi-model consensus** — Phase 10 position-specific; consensus across models Phase 11
8. **Automated threshold tuning** — Drift thresholds calibrated manually on 2024-25; automated meta-learning Phase 11

All deferred items inherit Phase 10's temporal integrity constraint and expanding-window foundation.

</deferred>

---

*Phase: 10-model-retraining*  
*Context gathered: 2026-05-28 via Research Complete*  
*Ready for planning: Yes*
