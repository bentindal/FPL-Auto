# Requirements: FPL-Auto Performance Optimization

**Defined:** 2026-05-27  
**Core Value:** Maximize total points the simulated team achieves across historical seasons through better predictions and smarter strategic decisions

## v1 Requirements

### Temporal Integrity

- [ ] **TI-01**: Remove lookahead bias from model training (models only train on GW(i-20) through GW(i-1), never actual GW(i) points)
- [ ] **TI-02**: Implement TemporalGate validation class to intercept data access and prevent future-data leakage
- [ ] **TI-03**: Document temporal integrity architecture (available data at each gameweek, what's off-limits)
- [ ] **TI-04**: Add automated tests to detect temporal violations (catch lookahead bias in code review)

### Model Diagnostics

- [ ] **MD-01**: Build squad comparison notebook comparing top 100 manager squads to model predictions (GW1 and mid-season)
- [ ] **MD-02**: Compute metrics: total squad xP, points-per-player variance, ROI (points per pound spent)
- [ ] **MD-03**: Identify gaps where top 100 managers pick players with systematically higher xP than model predicts
- [ ] **MD-04**: Use findings to guide feature engineering priorities

### Model Improvement Infrastructure

- [ ] **MI-01**: Wrap model training in sklearn Pipeline (prevents preprocessing data leakage)
- [ ] **MI-02**: Replace KFold with TimeSeriesSplit (required for temporal data, prevents lookahead in validation)
- [ ] **MI-03**: Implement nested cross-validation for hyperparameter tuning
- [ ] **MI-04**: Add permutation importance reporting (interpret feature contributions)
- [ ] **MI-05**: Track per-position performance breakdown and train-vs-test gap (10-20% is healthy; >20% signals overfitting)
- [ ] **MI-06**: Establish baseline metrics using improved validation (current approach with TimeSeriesSplit + nested CV)

### Feature Engineering

- [ ] **FE-01**: Expand feature set from ~20 raw features to 35-50 engineered features
- [ ] **FE-02**: Implement rolling averages, efficiency ratios, and position-specific features
- [ ] **FE-03**: Track feature correlations (VIF < 5 before adding new features)
- [ ] **FE-04**: Implement iteration workflow: hypothesis → retrain → evaluate (>2% RMSE improvement threshold)

### Strategy Framework

- [ ] **SF-01**: Define StrategyConfig dataclass encoding strategy variants (~15 parameters: transfer_mode, captain_mode, chip_schedule, bench_mode, risk_level, etc.)
- [ ] **SF-02**: Modify manager.py to accept `--strategy` parameter and instantiate strategies from StrategyConfig
- [ ] **SF-03**: Implement StrategyConfig variants: conservative, aggressive, differential-focused archetypes

### Strategy Evaluation

- [ ] **SE-01**: Build nested walk-forward validation framework (inner loop: train on 2-3 seasons → tune parameters; outer loop: test on held-out season)
- [ ] **SE-02**: Establish two baselines: (A) static team (never transfer), (B) current approach
- [ ] **SE-03**: Implement multi-dimensional metrics: Sharpe ratio, Sortino ratio, total points, consistency (CV), max drawdown, per-season results
- [ ] **SE-04**: Generate 95% bootstrapped confidence intervals for all metrics (not point estimates)
- [ ] **SE-05**: Apply Bonferroni correction for multiple comparisons (prevent false positives when testing many strategy variants)

### Transfer Strategy Evaluation

- [ ] **TS-01**: Implement transfer frequency variants (conservative, baseline, aggressive)
- [ ] **TS-02**: Implement transfer timing variants (early GW vs late GW decision points)
- [ ] **TS-03**: Evaluate transfer strategies using walk-forward validation framework
- [ ] **TS-04**: Compare against baseline transfer logic

### Captain & Chip Strategy Evaluation

- [ ] **CS-01**: Implement captain selection variants (highest xP vs form-based vs differential-focused)
- [ ] **CS-02**: Implement chip usage schedules (different timing for wildcard, triple captain, bench boost)
- [ ] **CS-03**: Evaluate using walk-forward validation framework
- [ ] **CS-04**: Compare against baseline captain/chip logic

### Bench & Substitution Strategy Evaluation

- [ ] **BS-01**: Implement bench composition variants (high-upside vs safe bench)
- [ ] **BS-02**: Implement substitution logic variants (defensive vs aggressive subs)
- [ ] **BS-03**: Evaluate using walk-forward validation framework
- [ ] **BS-04**: Compare against baseline bench logic

### Performance Validation

- [ ] **PV-01**: Compare final optimized system against top 100 manager historical performance
- [ ] **PV-02**: Verify no lookahead bias in final system (temporal integrity audit)
- [ ] **PV-03**: Generate final metrics report comparing all strategy archetypes
- [ ] **PV-04**: Document winning strategy parameters and decision rules

### Model Retraining & Time-Series Optimization

- [ ] **MR-01**: Implement FPL API + Understat data collection pipeline; populate accumulated_gw.csv for 2024-25 season
- [ ] **MR-02**: Build scheduled retraining orchestrator: every 2 GWs OR on drift detection (15% RMSE threshold using PELT algorithm)
- [ ] **MR-03**: Train position-specific ensemble models (XGBoost + RandomForest per GK/DEF/MID/FWD) using expanding time window (2019-2023 + live GWs)
- [ ] **MR-04**: Implement drift detection using PELT change-point analysis; alert on structural breaks with >15% RMSE degradation
- [ ] **MR-05**: Deploy Apache Airflow DAG orchestrating data collection → validation → retraining → evaluation → prediction export (post-GW Tuesday 19:00 UTC)
- [ ] **MR-06**: Execute live testing on 2024-25 season (GWs 1-5+); validate metrics (RMSE, MAE, R², Spearman), calibrate thresholds, document runbooks

## v2 Requirements

### Advanced Features

- **AF-01**: Ensemble model combining multiple sklearn models (gradientboost + randomforest + linear)
- **AF-02**: Fixture-adjusted xP with dynamic weighting based on opponent strength
- **AF-03**: Form-weighted predictions (recent weeks matter more than old weeks)
- **AF-04**: Real-time season simulation (output weekly recommendations, not just historical backtesting)

### UI & Reporting

- **UI-01**: Dashboard visualizing strategy comparison results
- **UI-02**: Export strategy recommendations in human-readable format
- **UI-03**: Interactive exploration of strategy parameters vs performance

### Monitoring & Validation

- **MON-01**: Automated monthly backtesting on rolling windows (detect strategy drift)
- **MON-01**: Production monitoring (if strategy deployed, track predicted vs actual performance)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time FPL API integration | Out of scope for historical analysis; focus on backtesting |
| Natural language explanations | Numerical metrics sufficient; explain decisions through data |
| Multi-user collaborative simulation | Focus on single-system optimization |
| Mobile/web app | Simulation tools are CLI/notebook-based for now |
| Automated live deployment | Backtesting only; no live trading integration |
| International football integration | FPL only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TI-01 | Phase 1 | Pending |
| TI-02 | Phase 1 | Pending |
| TI-03 | Phase 1 | Pending |
| TI-04 | Phase 1 | Pending |
| MD-01 | Phase 2 | Pending |
| MD-02 | Phase 2 | Pending |
| MD-03 | Phase 2 | Pending |
| MD-04 | Phase 2 | Pending |
| MI-01 | Phase 3 | Pending |
| MI-02 | Phase 3 | Pending |
| MI-03 | Phase 3 | Pending |
| MI-04 | Phase 3 | Pending |
| MI-05 | Phase 3 | Pending |
| MI-06 | Phase 3 | Pending |
| FE-01 | Phase 4 | Pending |
| FE-02 | Phase 4 | Pending |
| FE-03 | Phase 4 | Pending |
| FE-04 | Phase 4 | Pending |
| SF-01 | Phase 5 | Pending |
| SF-02 | Phase 5 | Pending |
| SF-03 | Phase 5 | Pending |
| SE-01 | Phase 5 | Pending |
| SE-02 | Phase 5 | Pending |
| SE-03 | Phase 5 | Pending |
| SE-04 | Phase 5 | Pending |
| SE-05 | Phase 5 | Pending |
| TS-01 | Phase 6 | Pending |
| TS-02 | Phase 6 | Pending |
| TS-03 | Phase 6 | Pending |
| TS-04 | Phase 6 | Pending |
| CS-01 | Phase 7 | Pending |
| CS-02 | Phase 7 | Pending |
| CS-03 | Phase 7 | Pending |
| CS-04 | Phase 7 | Pending |
| BS-01 | Phase 8 | Pending |
| BS-02 | Phase 8 | Pending |
| BS-03 | Phase 8 | Pending |
| BS-04 | Phase 8 | Pending |
| PV-01 | Phase 9 | Pending |
| PV-02 | Phase 9 | Pending |
| PV-03 | Phase 9 | Pending |
| PV-04 | Phase 9 | Pending |
| MR-01 | Phase 10 | Pending |
| MR-02 | Phase 10 | Pending |
| MR-03 | Phase 10 | Pending |
| MR-04 | Phase 10 | Pending |
| MR-05 | Phase 10 | Pending |
| MR-06 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 42 total
- Mapped to phases: 42
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-27*  
*Based on research findings: Temporal Integrity, Model Improvement, Strategy Evaluation, Backtesting Pitfalls*
