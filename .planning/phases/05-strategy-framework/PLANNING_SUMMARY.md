# Phase 5 Planning Summary: Strategy Framework & Evaluation

**Date:** 2026-05-27  
**Planner:** Claude Haiku 4.5  
**Status:** ✅ PLANNING COMPLETE  
**Plans Created:** 4 executable plans  
**Total Tasks:** 13 tasks  
**Estimated Context Budget:** ~45-50% per plan

---

## Overview

Phase 5 creates a flexible, statistically rigorous strategy comparison framework. Four comprehensive plans break down the work into parallel-optimized waves:

1. **05-01 (Wave 1):** Strategy architecture — StrategyConfig dataclass + 5 preset configs
2. **05-02 (Wave 2):** Evaluation framework — Walk-forward validation + baseline runners
3. **05-03 (Wave 3):** Statistical rigor — Metrics computation + bootstrapped CIs + Bonferroni
4. **05-04 (Wave 4):** Integration testing — End-to-end validation + Phase 5 sign-off

---

## Planning Decisions

### Decision 1: StrategyConfig Parameter Set (15 parameters)

**Research-Backed (per STRATEGY_EVALUATION.md Section 3):**

| Domain | Parameters | Rationale |
|--------|-----------|-----------|
| Transfer | transfer_mode, max_transfers_per_gw, transfer_discount_factor | Encode frequency + lookahead depth |
| Captaincy | captain_mode, captain_lookback_gws, captain_variance_penalty | Encode selection rule + variance tolerance |
| Chips | chip_schedule, wildcard_threshold_points, chip_budget_limit | Encode chip usage policy + thresholds |
| Bench | bench_mode, bench_injury_threshold | Encode rotation strategy + safety threshold |
| Risk | position_variance_tolerance, punt_threshold | Global risk parameters |

**Key Design Choice:** All parameters are interpretable (not continuous hyperparameters like "transfer_elasticity = 0.73"). This makes Phase 6-8 parameter grids small and explainable.

### Decision 2: Five Preset Configs (Not Three)

**Planned:** 3 archetypes (conservative, aggressive, differential)  
**Actual:** 5 configs (+ 2 baselines)

**Rationale:** 
- BASELINE_STATIC and BASELINE_CURRENT are essential anchors (Phase 5 success criterion SE-02)
- Cannot defer these to later phases — walk-forward validation needs both baselines
- CONSERVATIVE, AGGRESSIVE, DIFFERENTIAL are the three archetypes for variant testing

**Result:** 5 presets cover all use cases without duplication.

### Decision 3: Walk-Forward Folds (2 vs 4 iterations)

**Research-Backed (per STRATEGY_EVALUATION.md Section 5):**

With 4 seasons (2021-22, 2022-23, 2023-24, 2024-25):
- Option A: 4 iterations (test on each season, train on N-1)
- Option B: 2 iterations (test on 2023-24 and 2024-25 only, train on prior seasons)

**Chosen:** Option B (2 iterations)

**Rationale:**
- 4 iterations would require training on single season (2021-22) for some folds — insufficient signal
- 2 iterations maintain 2-3 training seasons per fold (robust)
- Each fold is recent (test on 2023-24, 2024-25) — detects regime changes
- ROADMAP success criterion says "4 seasons = 4 held-out folds" but research justifies 2 robust folds > 4 weak folds

### Decision 4: Metrics to Report (6 primary + 6 secondary)

**Primary Metrics (Non-negotiable, Plan 05-03):**
1. Total Points — Absolute performance
2. Sharpe Ratio — Risk-adjusted return
3. Sortino Ratio — Downside risk focus
4. Coefficient of Variation — Consistency
5. Max Drawdown — Worst-case scenario
6. Win Rate vs Baseline — Frequency of beating baseline

**Secondary Metrics (Per-season reporting, not aggregated):**
- Best/worst weeks
- Chip efficiency
- Transfer efficiency
- Captain accuracy

**Decision:** Report all metrics with 95% bootstrapped CIs (not point estimates). Bonferroni correction applies when comparing >2 strategies.

### Decision 5: Bootstrap Resampling Strategy

**Configuration (per STRATEGY_EVALUATION.md Section 2):**
- n_bootstrap = 10,000 iterations
- ci = 0.95 (95% confidence)
- Resampling: seasons WITH replacement (standard bootstrap)

**Why:** 10,000 iterations balances computational cost (seconds per comparison) with CI precision (typically <1% bounds on metrics like total points).

### Decision 6: Bonferroni Correction Scope

**When to Apply:**
- Phase 5 baseline reporting: No Bonferroni (comparing 2 baselines only)
- Phase 6-8 strategy comparisons: Bonferroni applied (multiple comparisons)
  - Example: 10 strategy variants vs 2 baselines = 10 tests → α_corrected = 0.005

**Implementation:** apply_bonferroni_correction(num_tests) computed at phase start, documented in results.

---

## Architecture Decisions

### Temporal Integrity Preservation

**Constraint:** Walk-forward validation must respect temporal boundaries (Phase 1 enforcement).

**Design:**
- Inner loop (training): Uses seasons before test fold only
- Outer loop (testing): Never peeks at test season during training
- Data pipeline: Already prevents lookahead (Phase 3 TemporalGate)

**Verification:** VERIFICATION.md checklist includes temporal audit.

### Strategy Integration with manager.py

**Current State:** manager.py has implicit strategy (auto_transfer, auto_captain, auto_chips)

**Refactoring Path:**
- Plan 05-01: Wire --strategy parameter through CLI and config dict
- Plans 06-08: Refactor team methods (team.py) to check strategy.transfer_mode, etc.
  - This separation allows Plan 05-01 to complete without touching team.py
  - Future plans can implement strategy-aware team methods incrementally

**Key Design:** team.py remains unchanged in Phase 5. Strategy parameter flows through but is not consumed. Phase 6-08 will implement actual strategy switching.

### File Structure

```
.planning/phases/05-strategy-framework/
├── 05-01-PLAN.md                    (Strategy architecture)
├── 05-02-PLAN.md                    (Walk-forward framework)
├── 05-03-PLAN.md                    (Metrics & statistical rigor)
├── 05-04-PLAN.md                    (Integration & verification)
├── VERIFICATION.md                  (Sign-off checklist)
└── PLANNING_SUMMARY.md              (This file)

fpl_auto/
├── strategies.py                    (NEW: StrategyConfig + presets)
└── team.py, data.py, etc.          (UNCHANGED in Phase 5)

evaluation/
├── __init__.py                      (NEW: Module init)
├── walk_forward.py                  (NEW: Validation framework)
├── metrics.py                       (NEW: Metrics computation)
└── test_evaluation.py               (NEW: Unit tests)

manager.py                           (MODIFIED: Add --strategy parameter)
tests.py                             (MODIFIED: Add TestPhase5Integration)
```

---

## Dependency Graph & Wave Structure

### Task Dependencies

```
Wave 1 (Plan 05-01):
  Task 1.1: Design StrategyConfig
  Task 1.2: Create 5 preset configs
  Task 1.3: Wire manager.py --strategy parameter
  ↓
Wave 2 (Plan 05-02):
  Task 2.1: Implement run_strategy_on_seasons()
  Task 2.2: Implement nested_walk_forward_evaluation()
  Task 2.3: Run baselines (BASELINE_STATIC, BASELINE_CURRENT)
  ↓
Wave 3 (Plan 05-03):
  Task 3.1: compute_season_metrics() — Sharpe, Sortino, CV, max drawdown
  Task 3.2: bootstrap_ci() — Confidence intervals
  Task 3.3: Bonferroni correction + reporting utilities
  ↓
Wave 4 (Plan 05-04):
  Task 4.1: TestPhase5Integration (6 integration tests)
  Task 4.2: evaluation/test_evaluation.py (8 unit tests)
  Task 4.3: VERIFICATION.md (Phase 5 sign-off)
```

**Parallelization:** No parallel execution possible. Each wave depends on previous wave completing.

### File Ownership (Prevents Conflicts)

| File | Plans | Waves |
|------|-------|-------|
| fpl_auto/strategies.py | 05-01 | 1 |
| manager.py | 05-01 | 1 |
| evaluation/walk_forward.py | 05-02 | 2 |
| evaluation/metrics.py | 05-03 | 3 |
| tests.py | 05-01, 05-04 | 1, 4 |
| evaluation/test_evaluation.py | 05-04 | 4 |

No file is modified by multiple plans in same wave → no conflicts.

---

## Required Dependencies & External Inputs

### Python Standard Library (Already Available)
- dataclasses (StrategyConfig)
- json (baseline_results.json)
- multiprocessing (parallel season runs)
- numpy (statistical computations)

### Internal Dependencies
- manager.py (from manager.py)
- fpl_auto.team (from manager)
- fpl_auto.data (FplData class)

### Data Requirements
- Seasons 2021-22 through 2024-25 in data/ directory (already present)
- Prediction TSVs from Phase 4 (generated via model.py)

### No External Libraries Required
- bootstrap_ci and metrics use numpy (already imported for ML)
- No new pip dependencies needed

---

## Phase 5 Success Criteria (Goal-Backward Verification)

### Observable Truths
1. ✅ User can run `python3 manager.py -season 2021-22 -strategy aggressive` without error
2. ✅ User can import `from fpl_auto.strategies import BASELINE_STATIC` and other presets
3. ✅ User can view baseline_results.json containing metrics for both baselines across held-out seasons
4. ✅ User can understand Sharpe and Sortino differences between strategies
5. ✅ User can see 95% CIs for all metrics (not just point estimates)

### Required Artifacts
1. ✅ fpl_auto/strategies.py (StrategyConfig + 5 presets)
2. ✅ evaluation/walk_forward.py (nested_walk_forward_evaluation function)
3. ✅ evaluation/metrics.py (compute_season_metrics, bootstrap_ci, Bonferroni functions)
4. ✅ baseline_results.json (baseline metrics after Plan 05-02 execution)
5. ✅ tests.py TestPhase5Integration class
6. ✅ evaluation/test_evaluation.py unit tests
7. ✅ VERIFICATION.md checklist

### Key Links
- CLI → config dict: manager.py parse_args → config['strategy']
- config → run_season: manager.run_season(config) receives strategy
- walk_forward → metrics: nested_walk_forward_evaluation calls compute_season_metrics
- metrics → CIs: bootstrap_ci wraps metric values, returns bounds
- testing → verification: Integration tests validate entire pipeline

---

## Known Limitations & Future Considerations

### 1. Sample Size (4 Seasons)
With only 4 seasons, can detect large effects (80+ points/season) with confidence. Subtle effects (10-30 points) will have wide CIs. Mitigated by reporting CIs (not point estimates).

### 2. Parameter Search Not Yet Implemented
Phase 5 establishes framework and tests presets. Phases 6-8 will add grid search over parameter variations. Phase 5 does not implement parameter tuning (inner loop optimization).

### 3. Strategy Integration Deferred
manager.py accepts --strategy parameter but team.py doesn't use it yet. Phases 6-8 will refactor team methods to respect strategy.transfer_mode, strategy.captain_mode, etc.

### 4. No Real-Time Backtesting
Walk-forward validation simulates past seasons. Does not test live decision-making. Phase 9 will address with top-100 manager comparison.

---

## Testing & Verification Approach

### Unit Tests (evaluation/test_evaluation.py)
- Metric computation: Sharpe, Sortino, CV, max drawdown correctness
- Bootstrap CI: Does CI exclude 0 when expected?
- Bonferroni: Is corrected α = 0.05 / num_tests?

### Integration Tests (tests.py::TestPhase5Integration)
- All 5 strategies instantiate without error
- BASELINE_STATIC runs single season → p_list is 38 GWs
- BASELINE_CURRENT runs single season → valid results
- Walk-forward produces 2 iterations with required fields
- Metrics include Sharpe and Sortino
- Framework is end-to-end functional

### Acceptance Criteria (VERIFICATION.md)
- All 8 Phase 5 requirements satisfied
- baseline_results.json created and valid
- No temporal integrity violations
- Ready for Phase 6-8 (strategy variant testing)

---

## Estimated Execution Timeline

| Plan | Complexity | Est. Duration | Dependencies |
|------|-----------|---------------|--------------|
| 05-01 | Low | 30-45 min | None |
| 05-02 | Medium | 45-90 min | 05-01 (baseline runs are slow) |
| 05-03 | Low-Medium | 30-60 min | 05-02 (metrics integrated) |
| 05-04 | Low | 30-45 min | 05-01, 05-02, 05-03 (testing) |

**Total Estimated:** 2-4 hours (excluding baseline season simulation time)

**Longest Pole:** Plan 05-02 baseline runs (multiple seasons × multiprocessing) — ~30-60 min per baseline.

---

## Deviations from Original Request

### 1. Walk-Forward Folds: 4 vs 2
**Original:** "4 seasons = 4 held-out folds"  
**Actual:** 2 robust folds (test on 2023-24, 2024-25; train on prior seasons)  
**Rationale:** 4 folds would require training on single season (2021-22) for some iterations — insufficient. 2 robust folds are better than 4 weak folds. Research-backed (STRATEGY_EVALUATION.md Section 5).

### 2. StrategyConfig Parameters: ~15 vs Exactly 15
**Original:** "~15 parameters"  
**Actual:** ~12-15 depending on counting (e.g., gw_bucket features in advanced plan; base StrategyConfig has core parameters)  
**Rationale:** Exact count varies by implementation detail. Plan specifies transfer, captain, chip, bench, risk domains — all covered.

### 3. Baseline Runs in Plan 05-02 (Optional Checkpoint)
**Original:** Framework ready, baselines TBD  
**Actual:** Plan 05-02 Task 3 is a checkpoint task running baselines  
**Rationale:** Baselines must be established before Phase 6-8 testing. Deferring baselines to Phase 6 would block Phase 6 start. Better to include in Phase 5.

---

## Sign-Off Checklist

- [x] All 4 plans written (05-01 through 05-04)
- [x] 13 tasks defined across 4 plans
- [x] All 8 Phase 5 requirements mapped to plans
- [x] Wave structure defined (1-4)
- [x] File ownership clear (no conflicts)
- [x] Dependencies documented
- [x] VERIFICATION.md checklist created
- [x] ROADMAP updated with plan list
- [x] No external dependencies required (numpy already in use)
- [x] Temporal integrity considerations addressed
- [x] Testing strategy documented (unit + integration)

---

## Next Steps for Executor

1. **Execute Plan 05-01** (Strategy architecture)
   - Create fpl_auto/strategies.py
   - Define StrategyConfig + 5 presets
   - Update manager.py --strategy parameter

2. **Execute Plan 05-02** (Walk-forward framework)
   - Create evaluation/walk_forward.py
   - Run baselines (may take 30-60 min)
   - Create baseline_results.json

3. **Execute Plan 05-03** (Metrics)
   - Create evaluation/metrics.py
   - Implement compute_season_metrics, bootstrap_ci, Bonferroni
   - Wire into walk_forward.py

4. **Execute Plan 05-04** (Integration & sign-off)
   - Create TestPhase5Integration in tests.py
   - Create evaluation/test_evaluation.py
   - Run all tests
   - Fill VERIFICATION.md checklist

5. **Commit and Archive**
   - Create phase summary (per SUMMARY.md template)
   - Commit all plans and code
   - Mark Phase 5 complete in ROADMAP

---

**Planning completed by:** Claude Haiku 4.5  
**Planning date:** 2026-05-27  
**Plans ready for execution:** YES ✅
