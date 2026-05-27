# ROADMAP: FPL-Auto Performance Optimization

**Project:** FPL-Auto Performance Optimization System  
**Created:** 2026-05-27  
**Granularity:** Standard (8-9 phases, 3-5 plans each)  
**Total v1 Requirements:** 36  
**Coverage:** 36/36 (100%)

---

## Phases

- [x] **Phase 1: Temporal Integrity** - Fix lookahead bias and implement enforcement mechanism
- [ ] **Phase 2: Model Diagnostics** - Understand prediction gaps by comparing to top 100 managers
- [x] **Phase 3: Model Infrastructure** - Establish proper validation pipeline (TimeSeriesSplit, nested CV)
- [x] **Phase 4: Feature Engineering** - Expand and improve predictor features
- [ ] **Phase 5: Strategy Framework & Evaluation** - Define parametrizable strategies and validation framework
- [ ] **Phase 6: Transfer Strategy Evaluation** - Test transfer frequency and timing variants
- [ ] **Phase 7: Captain & Chip Strategy Evaluation** - Test captain selection and chip usage variants
- [ ] **Phase 8: Bench & Substitution Strategy Evaluation** - Test bench composition and substitution logic variants
- [ ] **Phase 9: Performance Validation** - Final comparison against top 100 managers and lookahead audit

---

## Phase Details

### Phase 1: Temporal Integrity
**Goal**: System enforces temporal boundaries — models and strategies only access data available at each gameweek. No lookahead bias.

**Depends on**: Nothing (foundation phase)

**Requirements**: TI-01, TI-02, TI-03, TI-04

**Success Criteria** (what must be TRUE):
1. Model training uses only GW(i-20) through GW(i-1); never actual GW(i) points
2. TemporalGate class successfully intercepts and rejects future-data access during test runs
3. Temporal architecture documented: what data is available at each gameweek, what's forbidden
4. Automated tests pass that detect temporal violations (e.g., accessing GW(i) for prediction at GW(i))

**Plans**:
- [x] 01-01-PLAN.md — Create TemporalGate class and fix model training lookahead (TI-01, TI-02)
- [x] 01-02-PLAN.md — Add temporal violation detection tests and architecture documentation (TI-03, TI-04)

---

### Phase 2: Model Diagnostics
**Goal**: Identify specific prediction gaps by comparing model predictions to top 100 manager squad choices.

**Depends on**: Phase 1

**Requirements**: MD-01, MD-02, MD-03, MD-04

**Success Criteria** (what must be TRUE):
1. Squad comparison notebook compares top 100 manager squads to model predictions at GW1 and mid-season
2. Metrics computed: total squad xP, points-per-player variance, ROI (points per pound)
3. Gaps identified: players with systematically higher xP than model predicts vs top 100 selections
4. Feature engineering priorities documented based on gap analysis (which player attributes are being undervalued)

**Plans**: TBD

---

### Phase 3: Model Infrastructure
**Goal**: Establish proper model training pipeline with temporal-aware validation. Replace KFold with TimeSeriesSplit, wrap in sklearn Pipeline, implement nested cross-validation.

**Depends on**: Phase 1, Phase 2

**Requirements**: MI-01, MI-02, MI-03, MI-04, MI-05, MI-06

**Success Criteria** (what must be TRUE):
1. All model training uses sklearn Pipeline (prevents preprocessing leakage)
2. TimeSeriesSplit replaces KFold across all position models
3. Nested cross-validation implemented for hyperparameter tuning (inner loop: CV for params; outer loop: temporal test fold)
4. Permutation importance reporting available for each position; top 10 features documented
5. Baseline metrics established: per-position RMSE/MAE, train-vs-test gap tracked (10-20% healthy, >20% signals overfitting)
6. Baseline model performance on all 4 seasons (2021-22 through 2024-25) recorded as reference

**Plans**:
- [x] 03-01-PLAN.md — Refactor Predictor for Pipeline + TimeSeriesSplit foundation (MI-01, MI-02, MI-03)
- [x] 03-02-PLAN.md — Implement nested CV, permutation importance, baseline metrics (MI-02, MI-03, MI-04, MI-05)
- [x] 03-03-PLAN.md — Verify manager.py backward compatibility and Phase 3 readiness (MI-06)

---

### Phase 4: Feature Engineering
**Goal**: Expand predictor feature set from ~20 to 35-50 engineered features, targeting position-specific metrics and rolling statistics.

**Depends on**: Phase 3

**Requirements**: FE-01, FE-02, FE-03, FE-04

**Success Criteria** (what must be TRUE):
1. Feature set expanded from ~20 to 35-50 features (documented in feature registry with definitions)
2. Rolling averages, efficiency ratios, and position-specific features implemented and added to pipeline
3. Feature correlations tracked; all new features have VIF < 5 before inclusion
4. Iteration workflow validated: hypothesis → retrain with TimeSeriesSplit → measure RMSE improvement (threshold: >2% per feature addition)
5. Final feature set improves baseline RMSE by at least 5% across all 4 seasons (measured with temporal integrity intact)

**Plans**: 04-01, 04-02, 04-03 (2-3 plans)

---

### Phase 5: Strategy Framework & Evaluation
**Goal**: Create flexible, parametrizable strategy system. Implement walk-forward validation framework. Establish baselines (static team, current approach). Prepare for strategy comparison.

**Depends on**: Phase 3, Phase 4

**Requirements**: SF-01, SF-02, SF-03, SE-01, SE-02, SE-03, SE-04, SE-05

**Success Criteria** (what must be TRUE):
1. StrategyConfig dataclass defined with ~15 parameters (transfer_mode, captain_mode, chip_schedule, bench_mode, risk_level, etc.)
2. manager.py accepts `--strategy` parameter; strategies instantiate from StrategyConfig
3. Three strategy archetypes (conservative, aggressive, differential-focused) implemented and working
4. Walk-forward validation framework runs: train on 2-3 seasons → tune → test on held-out season (4 seasons = 4 held-out folds)
5. Two baselines established: (A) static team (never transfer), (B) current approach (existing manager.py logic)
6. Multi-dimensional metrics computed: Sharpe ratio, Sortino ratio, total points, consistency (CV), max drawdown, per-season results
7. 95% bootstrapped confidence intervals generated for all metrics (no point estimates; CIs quantify uncertainty)
8. Bonferroni correction applied to prevent false positives in multiple comparisons

**Plans**: TBD

---

### Phase 6: Transfer Strategy Evaluation
**Goal**: Evaluate transfer frequency and timing variants using walk-forward framework. Compare against baseline.

**Depends on**: Phase 5

**Requirements**: TS-01, TS-02, TS-03, TS-04

**Success Criteria** (what must be TRUE):
1. Transfer frequency variants implemented: conservative (X transfers/season), baseline (current logic), aggressive (Y transfers/season)
2. Transfer timing variants implemented: early GW decision points (weeks 1-10), late GW decision points (weeks 25-38)
3. All variants tested with walk-forward validation (train on 2-3 seasons, test on held-out season)
4. Results compare each variant against both baselines; winners have non-overlapping 95% CIs with baselines
5. Per-season breakdown shows regime changes (e.g., variant works 2021-22 but fails 2023-24)

**Plans**: TBD

---

### Phase 7: Captain & Chip Strategy Evaluation
**Goal**: Evaluate captain selection and chip usage variants. Compare timing, triggers, and decision rules.

**Depends on**: Phase 5

**Requirements**: CS-01, CS-02, CS-03, CS-04

**Success Criteria** (what must be TRUE):
1. Captain selection variants implemented: highest xP, form-based, differential-focused
2. Chip usage schedules implemented: wildcard timing, triple captain triggers, bench boost conditions
3. All variants tested with walk-forward validation (train on 2-3 seasons, test on held-out season)
4. Results compare each variant against both baselines; winners have non-overlapping 95% CIs
5. Per-season breakdown documents performance across all 4 seasons

**Plans**: TBD

---

### Phase 8: Bench & Substitution Strategy Evaluation
**Goal**: Evaluate bench composition and substitution logic variants.

**Depends on**: Phase 5

**Requirements**: BS-01, BS-02, BS-03, BS-04

**Success Criteria** (what must be TRUE):
1. Bench composition variants implemented: high-upside bench (speculative), safe bench (defensive)
2. Substitution logic variants implemented: defensive subs (swap to safety), aggressive subs (chase upside)
3. All variants tested with walk-forward validation (train on 2-3 seasons, test on held-out season)
4. Results compare each variant against both baselines; winners have non-overlapping 95% CIs
5. Per-season breakdown documents performance across all 4 seasons

**Plans**: TBD

---

### Phase 9: Performance Validation
**Goal**: Final system validation. Verify temporal integrity. Compare optimized strategies against top 100 manager historical performance. Document winning parameters.

**Depends on**: Phase 6, Phase 7, Phase 8

**Requirements**: PV-01, PV-02, PV-03, PV-04

**Success Criteria** (what must be TRUE):
1. Final optimized system (best strategies from phases 6-8) compared to top 100 manager historical performance across all 4 seasons
2. Temporal integrity audit passes: no lookahead bias detected in final system (automated tests pass)
3. Final metrics report generated: all strategy archetypes ranked, 95% CIs reported, per-season results shown
4. Winning strategy parameters documented: transfer frequency, captain rules, chip timing, bench composition, risk settings

**Plans**: TBD

---

## Progress Table

| Phase | Goal | Requirements | Plans | Status |
|-------|------|--------------|-------|--------|
| 1. Temporal Integrity | Fix lookahead bias | 4 | 2 | Execution complete |
| 2. Model Diagnostics | Understand gaps | 4 | TBD | Not started |
| 3. Model Infrastructure | Proper validation | 6 | 3 | Execution complete |
| 4. Feature Engineering | Expand features | 4 | TBD | Not started |
| 5. Strategy Framework & Evaluation | Parametrizable strategies | 8 | TBD | Not started |
| 6. Transfer Strategy Evaluation | Evaluate transfers | 4 | TBD | Not started |
| 7. Captain & Chip Evaluation | Evaluate captaincy/chips | 4 | TBD | Not started |
| 8. Bench & Substitution Evaluation | Evaluate bench logic | 4 | TBD | Not started |
| 9. Performance Validation | Final validation | 4 | TBD | Not started |

---

## Notes

- **Parallelization**: Phases 6, 7, 8 can run in parallel after Phase 5 completes. Phase 9 waits for all three.
- **Temporal Integrity**: Enforced from Phase 1 onward. All subsequent phases inherit this constraint.
- **Research Foundation**: Phases 1-5 directly address research recommendations; Phases 6-9 apply validated evaluation framework to strategy variants.
- **Statistical Rigor**: Walk-forward validation (Phase 5 onward) prevents overfitting. Bootstrapped CIs (not point estimates) quantify uncertainty. Bonferroni correction prevents false positives.

---

*Roadmap updated: 2026-05-27 - Phase 1 & Phase 3 execution complete*
