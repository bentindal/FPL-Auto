# Phase 4: Feature Engineering — Planning Summary

**Date:** 2026-05-27  
**Phase:** 04-feature-engineering  
**Status:** Plans Complete (Ready for Execution)  
**Total Plans:** 3 (2 required, 1 optional)

---

## Overview

Phase 4 expands the predictor feature set from ~20 raw features (Phase 3) to 35-50 engineered features. Three coordinated plans implement rolling statistics, efficiency ratios, position-specific features, VIF filtering, and iterative hypothesis validation.

---

## Plan Structure

### Plan 04-01: Feature Engineering Implementation (Wave 1)
**Type:** Execute  
**Autonomy:** Fully autonomous  
**Duration:** ~2-3 hours (implementation + testing)

**Objectives:**
- Implement engineer_features_on_gw_data() with rolling stats, efficiency ratios, and position-specific features (~12-15 new features)
- Implement display_feature_vif() for multicollinearity analysis
- Create comprehensive test suite (5 test methods) verifying temporal integrity and feature bounds
- Generate feature registry documenting all 35-40 features

**Key Outputs:**
- `fpl_auto/data.py`: engineer_features_on_gw_data() function
- `fpl_auto/evaluate.py`: display_feature_vif() function
- `tests.py`: TestFeatureEngineering class (5 methods)
- `.planning/FEATURE_REGISTRY_v1.md`: Feature documentation

**Success Criteria:**
- All 5 tests passing
- Rolling stats computed correctly within temporal boundaries
- Efficiency ratios finite and bounded
- Position-specific features present for all 4 positions
- Feature registry complete with baseline metrics

---

### Plan 04-02: Integration & Baseline Retraining (Wave 2)
**Type:** Execute  
**Autonomy:** Fully autonomous  
**Duration:** ~4-6 hours (integration + 4 season retrains)

**Depends on:** Plan 04-01

**Objectives:**
- Integrate feature engineering into model.py data pipeline
- Apply VIF filtering within TimeSeriesSplit folds (prevent data leakage)
- Retrain models on all 4 seasons (2021-22 through 2024-25)
- Measure RMSE improvements per position and aggregate
- Verify >=5% improvement target achieved

**Key Outputs:**
- Updated `model.py`: engineer_features_on_gw_data() + VIF filtering in CV loop
- `.planning/BASELINE_METRICS_v2.json`: Per-season RMSE delta measurements
- `.planning/FEATURE_IMPORTANCE_v2.md`: Permutation importance post-engineering
- Updated `.planning/FEATURE_REGISTRY_v1.md`: Actual VIF scores and final feature count

**Success Criteria:**
- All 4 seasons retrained without errors
- RMSE improvement >= 5% overall (target: 0.3718 → 0.3532)
- Per-position improvements documented
- Train-vs-test gap healthy (10-20%, not >20%)
- VIF filtering applied per position per fold (no data leakage)

**Expected Outcome:** +5% RMSE improvement, achieving baseline target

---

### Plan 04-03: Advanced Feature Iteration (Wave 3, Optional)
**Type:** Execute with checkpoint  
**Autonomy:** Semi-autonomous (checkpoint after Plan 04-02 evaluation)  
**Duration:** ~2-3 hours per 1-2 iterations (5-10 iterations planned)

**Depends on:** Plan 04-02 (after verification)

**Objectives:**
- Test 5-10 additional advanced features via rigorous iteration workflow
- Each feature tested: hypothesis → implement → retrain (one season) → measure RMSE → keep/drop decision
- Maintain >2% improvement threshold for feature inclusion
- Achieve cumulative >=7% RMSE improvement (exceeds 5% target by >=2%)

**Candidate Features:**
1. Seasonal bucket (GW_bucket: early/mid/late/final)
2. Form momentum (influence trend: 5-GW vs 10-GW delta)
3. Ownership Y-o-Y change (selected% differential vs prior season)
4. Injury risk flag (recent minutes drop indicator)
5. Team form (recent wins proxy)
6. Position scarcity (usage rate relative to squad depth)
7. Strength × Form interaction
8. Fixture × Efficiency interaction
9. Previous GW points (lag feature, high predictive potential)
10. [Future candidate based on FEATURE_IMPORTANCE_v2.md]

**Key Outputs:**
- `.planning/FEATURE_ITERATION_LOG.md`: Detailed log of 5-10 iterations (hypothesis, baseline, measured RMSE delta, decision)
- Updated `.planning/FEATURE_REGISTRY_v1.md`: Performance timeline, advanced features section, comprehensive summary
- Final feature set: 35-50 features, >=7% RMSE improvement documented

**Success Criteria:**
- All 5-10 iterations executed and logged
- Each KEEP decision backed by >2% RMSE improvement
- Each DROP decision documented with reason
- Final RMSE improvement >= 7% cumulative from Phase 3 baseline
- Final feature count 35-50
- All decisions auditable and reproducible

**Expected Outcome:** +8-13% cumulative RMSE improvement (adds 3-8% on top of Plan 04-02), final feature set optimized and documented

**Continuation Criteria:**
After Plan 04-02, checkpoint decision:
- If >=5% improvement achieved: Proceed to Plan 04-03 (optional advanced iteration)
- If <5% improvement: Skip Plan 04-03, finalize Phase 4 at Plan 04-02 level

---

## Feature Categories

### Raw Features (~23)
From `get_gw_data()` and `get_team_list()`: minutes, influence, threat, creativity, assists, goals_scored, clean_sheets, saves, selected, value, strength ratings, etc.

### Engineered Features (Plan 04-01, ~12-15)
- **Rolling stats:** 5-GW and 10-GW averages of minutes, influence, assists, goals_scored, creativity, threat
- **Efficiency ratios:** goals_per_90, assists_per_90, creativity_per_min, threat_per_min
- **Position-specific:** GK (saves_per_90, save%), DEF (clean_sheets_per_90), MID (key_passes_proxy), FWD (shots_on_target_proxy)

### Advanced Features (Plan 04-03, ~5-10)
- Seasonal bucket (categorical)
- Form momentum (trend)
- Ownership Y-o-Y change
- Injury risk flag
- Team form proxy
- Position scarcity ratio
- Strength × Form interaction
- Fixture × Efficiency interaction
- Previous GW points (lag)
- [Candidate based on permutation importance]

### Final Feature Set (35-50 total)
All raw + engineered + kept advanced features. VIF filtered (< 5), iteratively validated (>2% improvement threshold).

---

## RMSE Improvement Targets

| Milestone | RMSE | Delta from Baseline | Notes |
|-----------|------|---------------------|-------|
| Phase 3 Baseline | 0.3718 | — | TimeSeriesSplit baseline |
| Plan 04-02 v1 | ~0.3532 | +5.0% | Rolling stats + efficiency + position-specific |
| Plan 04-03 Final | ~0.3226 | +13.2% | Adds advanced features (cumulative) |
| Target (minimum) | ≤0.3532 | ≥5.0% | Phase 4 success threshold |

---

## Key Decisions & Constraints

### Temporal Integrity
- All rolling stats computed within TimeSeriesSplit folds
- No future GW data accessed in rolling windows
- Unit tests verify temporal boundary enforcement
- Reference: Phase 1 TemporalGate infrastructure maintained

### VIF Filtering
- Threshold: 5.0 (multicollinearity)
- Applied per position per fold (inside CV loop, not global)
- Prevents data leakage and overfitting
- Dropped features logged for auditability

### Iteration Workflow
- Hypothesis-driven: one feature per iteration
- Measurement standard: RMSE delta on single season (2021-22)
- Keep threshold: >2% improvement
- Drop decision documented for rejected features

### Backward Compatibility
- No changes to manager.py API
- Feature engineering called transparently in data pipeline
- Phase 3 tests still passing
- Temporal integrity maintained throughout

---

## Resource Requirements

### Development Time
- Plan 04-01: 2-3 hours (coding + testing)
- Plan 04-02: 4-6 hours (integration + 4 season retrains; retrains run in parallel if possible)
- Plan 04-03: 2-3 hours per 1-2 iterations; ~10-15 hours total for all iterations (can be parallelized or batched)

### Computational Cost
- Plan 04-01: Minimal (unit tests only)
- Plan 04-02: Moderate (4 season retrains, TimeSeriesSplit 5 folds each = 20 CV folds total)
- Plan 04-03: Moderate (5-10 iterations × 5 folds × 19 gameweeks = 50-100 CV folds total)
- Can be distributed across multiple runs; individual season runs complete in ~10-30 minutes each

### Storage
- Feature registry, baseline metrics, iteration logs: ~100 KB total
- Model logs (stdout captures): ~50 MB total

---

## Success Indicators (Checkpoint)

**Plan 04-01 Success:**
✅ All 5 tests passing
✅ Feature registry complete with 35-40 features documented
✅ No temporal integrity violations detected

**Plan 04-02 Success:**
✅ Overall RMSE improvement >= 5% (primary target)
✅ Per-position improvements show GK/DEF/MID/FWD all improving (or close to baseline)
✅ Train-vs-test gap healthy (10-20%, not >20%)
✅ VIF filtering applied, documented in logs

**Plan 04-03 Success (if executed):**
✅ 5-10 advanced features tested with full iteration log
✅ Cumulative RMSE improvement >= 7% (target exceeded)
✅ Final feature registry comprehensive and auditable
✅ All dropped features documented with reasons

---

## Next Phase

**Phase 5: Strategy Framework & Evaluation**

Phase 4 completion feeds Phase 5:
- Improved RMSE baseline (5-13%) means better predictions for strategy evaluation
- Feature engineering methodology establishes data-driven decision-making pattern
- Validated iteration workflow model for future feature refinement

Dependency: Phase 4 Plan 04-02 must complete with >=5% RMSE improvement before Phase 5 starts.

---

## References

**Within Project:**
- `.planning/CONTEXT.md` — Phase 4 context, requirements, constraints
- `.planning/research/MODEL_IMPROVEMENT.md` — Feature engineering patterns, validation, common pitfalls
- `.planning/phases/03-model-infrastructure/03-03-SUMMARY.md` — Phase 3 baseline metrics

**External:**
- scikit-learn documentation: Pipelines, TimeSeriesSplit, VIF, Permutation Importance
- MODEL_IMPROVEMENT.md Examples 1-4: Code templates for implementation

---

**Planning Complete: 2026-05-27**
**Status: Ready for Execution**
**Next: Execute Plan 04-01**
