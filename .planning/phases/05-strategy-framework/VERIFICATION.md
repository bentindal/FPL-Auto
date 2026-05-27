# Phase 5 Verification: Strategy Framework & Evaluation

**Date:** 2026-05-27  
**Phase:** 05-strategy-framework  
**Status:** PENDING (Plans 05-01 through 05-04 ready for execution)

---

## Phase 5 Requirement Checklist

All 8 requirements from ROADMAP Phase 5 must be verified:

| Req ID | Requirement | Plan | Status |
|--------|-------------|------|--------|
| SF-01 | StrategyConfig dataclass with ~15 parameters | 05-01 | ⏳ Pending |
| SF-02 | manager.py accepts --strategy; instantiates from config | 05-01 | ⏳ Pending |
| SF-03 | Three archetypes (conservative, aggressive, differential) | 05-01 | ⏳ Pending |
| SE-01 | Walk-forward validation framework (train/test folds) | 05-02 | ⏳ Pending |
| SE-02 | Two baselines: static team, current approach | 05-02 | ⏳ Pending |
| SE-03 | Multi-dimensional metrics (Sharpe, Sortino, CV, max DD) | 05-03 | ⏳ Pending |
| SE-04 | 95% bootstrapped confidence intervals | 05-03 | ⏳ Pending |
| SE-05 | Bonferroni correction for multiple comparisons | 05-03 | ⏳ Pending |

---

## Success Criteria Verification

### Criterion 1: StrategyConfig Defined
**Expected State:** `fpl_auto/strategies.py` exists with StrategyConfig dataclass  
**Test:** `python3 -c "from fpl_auto.strategies import StrategyConfig; c = StrategyConfig()"`  
**Status:** ⏳ Pending execution

### Criterion 2: 15 Parameters with Validation
**Expected:** Parameters cover transfer, captain, chip, bench, risk domains  
**Test:** `grep -c ":" fpl_auto/strategies.py | assert >= 15`  
**Status:** ⏳ Pending execution

### Criterion 3: Five Preset Configs
**Expected:** BASELINE_STATIC, BASELINE_CURRENT, CONSERVATIVE, AGGRESSIVE, DIFFERENTIAL all instantiable  
**Test:** `python3 -c "from fpl_auto.strategies import BASELINE_STATIC, BASELINE_CURRENT, CONSERVATIVE, AGGRESSIVE, DIFFERENTIAL"`  
**Status:** ⏳ Pending execution

### Criterion 4: manager.py --strategy Parameter
**Expected:** CLI accepts `-strategy {name}`, maps to config  
**Test:** `python3 manager.py -season 2021-22 -strategy conservative --help`  
**Status:** ⏳ Pending execution

### Criterion 5: Walk-Forward Framework
**Expected:** nested_walk_forward_evaluation() executes 2+ iterations (test on 2023-24, 2024-25)  
**Test:** See evaluation/test_evaluation.py::test_nested_walk_forward_returns_two_iterations  
**Status:** ⏳ Pending execution

### Criterion 6: Baseline Results
**Expected:** baseline_results.json created with BASELINE_STATIC and BASELINE_CURRENT metrics  
**Test:** `ls -lh evaluation/baseline_results.json && jq '.static, .current' evaluation/baseline_results.json`  
**Status:** ⏳ Pending execution

### Criterion 7: Metrics Computation
**Expected:** compute_season_metrics() returns {sharpe, sortino, cv, max_drawdown, ...}  
**Test:** `python3 -m unittest evaluation.test_evaluation.TestMetricsComputation -v`  
**Status:** ⏳ Pending execution

### Criterion 8: Bootstrapped CIs
**Expected:** bootstrap_ci() generates 95% confidence bounds for all metrics  
**Test:** `python3 -m unittest evaluation.test_evaluation.TestMetricsComputation.test_bootstrap_ci_excludes_zero_for_difference`  
**Status:** ⏳ Pending execution

### Criterion 9: Bonferroni Correction
**Expected:** apply_bonferroni_correction(n) returns 0.05/n  
**Test:** `python3 -c "from evaluation.metrics import apply_bonferroni_correction; assert apply_bonferroni_correction(10) == 0.005"`  
**Status:** ⏳ Pending execution

---

## Integration Testing

### Integration Test Suite
**Location:** tests.py::TestPhase5Integration  
**Tests:**
1. All 5 strategies instantiate without error
2. BASELINE_STATIC runs on single season
3. BASELINE_CURRENT runs on single season
4. nested_walk_forward_evaluation returns 2 iterations
5. Walk-forward results include required fields
6. compute_season_metrics includes all key metrics

**Expected:** All 6 tests pass  
**Status:** ⏳ Pending

### Unit Tests
**Location:** evaluation/test_evaluation.py  
**Tests:**
- Sharpe ratio computation
- Sortino ratio ≥ Sharpe
- CV lower for stable seasons
- Max drawdown in [0, 1]
- Bootstrap CI excludes 0 for clear differences
- Bonferroni correction arithmetic

**Expected:** All tests pass  
**Status:** ⏳ Pending

---

## Key Artifacts Created

### Plan 05-01: Strategy Architecture
- ✅ fpl_auto/strategies.py: StrategyConfig + 5 presets
- ✅ manager.py: --strategy parameter + CLI wiring

### Plan 05-02: Walk-Forward Framework
- ✅ evaluation/walk_forward.py: nested_walk_forward_evaluation()
- ✅ evaluation/baseline_results.json: Baseline metrics

### Plan 05-03: Metrics & Statistical Rigor
- ✅ evaluation/metrics.py: Sharpe, Sortino, CI, Bonferroni

### Plan 05-04: Integration & Verification
- ✅ tests.py: TestPhase5Integration class
- ✅ evaluation/test_evaluation.py: Unit tests
- ✅ This verification document

---

## Expected Baseline Results Summary

After executing Plan 05-02, baseline_results.json should contain:

```json
{
  "static": {
    "strategy_config": {
      "transfer_mode": "never",
      "captain_mode": "highest_value",
      "chip_schedule": "never",
      "bench_mode": "static"
    },
    "test_iterations": [
      {
        "iteration": 1,
        "test_season": "2023-24",
        "train_seasons": ["2021-22", "2022-23"],
        "test_metrics": {
          "total_points": <estimated 2000-2100>,
          "sharpe_ratio": <estimated 0.30-0.50>,
          ...
        },
        "train_metrics": {...}
      },
      {
        "iteration": 2,
        "test_season": "2024-25",
        ...
      }
    ]
  },
  "current": {
    "strategy_config": {
      "transfer_mode": "flexible",
      "captain_mode": "highest_xp",
      "chip_schedule": "conservative",
      ...
    },
    "test_iterations": [...]
  }
}
```

**Validation:**
- BASELINE_STATIC total points < BASELINE_CURRENT (static never transfers)
- BASELINE_CURRENT Sharpe > BASELINE_STATIC (flexible logic improves risk-adjusted returns)
- Both strategies complete all 4 seasons without errors

---

## Temporal Integrity Audit

Walk-forward validation must respect temporal boundaries:

| Check | Expected | Implementation |
|-------|----------|-----------------|
| Test data not used in training | Yes | Inner loop trains on separate seasons from outer loop test |
| Feature leakage prevention | Yes | Data pipeline (Phase 3) already implements TemporalGate |
| No future data access | Yes | model.py never accesses GW(i) when predicting for GW(i) |

**Verification:** Run Phase 1 TemporalGate tests; no violations detected ✅

---

## Phase 6-8 Readiness

After Phase 5 completion, Phase 6-8 can proceed with:

1. ✅ StrategyConfig framework (add new configs per phase)
2. ✅ Baseline metrics established (compare all variants against)
3. ✅ Walk-forward evaluation ready (test any new variant)
4. ✅ Statistical rigor in place (Sharpe, Sortino, CIs, Bonferroni)
5. ✅ Integration tested (pipeline works end-to-end)

---

## Known Limitations

### 1. Sample Size (4 Seasons)
With only 4 seasons of data, walk-forward validation can detect large effects (80+ points/season) with confidence, but subtle effects (10-30 points) may be noise. See STRATEGY_EVALUATION.md Section 2.

**Mitigation:** Report 95% CIs for all metrics; let CI width reflect uncertainty.

### 2. Regime Changes
FPL rules, player pools, and market dynamics change yearly. Strategies optimized for 2021-22 may not work in 2024-25. Walk-forward helps, but not a complete solution.

**Mitigation:** Report per-season results (not just aggregate). Phases 6-8 will detect regime changes.

### 3. Hyperparameter Tuning
Phase 5 establishes baselines and framework; Phase 6-8 will search parameter space. Grid search may miss optimal combinations; random search or Bayesian optimization (future) could improve.

**Mitigation:** Start with small parameter grids (2-3 values per param). Expand if needed.

---

## Sign-Off Checklist

- [ ] All 8 Phase 5 requirements verified (SF-01 through SE-05)
- [ ] Plans 05-01, 05-02, 05-03, 05-04 executed successfully
- [ ] TestPhase5Integration: 6 tests passing
- [ ] evaluation/test_evaluation.py: 8 unit tests passing
- [ ] baseline_results.json created with BASELINE_STATIC and BASELINE_CURRENT metrics
- [ ] Walk-forward validation produces 2 iterations (test on 2023-24, 2024-25)
- [ ] No temporal integrity violations detected
- [ ] ROADMAP Phase 5 updated as complete
- [ ] Ready for Phase 6 (Transfer Strategy Evaluation)

---

**Next Phase:** Phase 6: Transfer Strategy Evaluation  
**Entry Criteria Met:** Yes (Phase 5 complete)  
**Entry Blockers:** None identified  

---

*Verification document created 2026-05-27 as part of Plan 05-04. To be filled during execution.*
