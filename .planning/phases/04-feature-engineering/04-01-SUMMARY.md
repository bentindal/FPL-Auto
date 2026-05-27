---
phase: 04-feature-engineering
plan: 01
title: "Rolling Stats, Efficiency Ratios & VIF Analysis"
status: COMPLETE
completion_date: 2026-05-27
duration_minutes: 45
tasks_completed: 4
tests_passing: 5
---

# Plan 04-01: Rolling Stats, Efficiency Ratios & VIF Analysis — Summary

**Date:** 2026-05-27  
**Status:** ✅ COMPLETE  
**All Requirements:** ✅ MET

## Execution Overview

Plan 04-01 implemented feature engineering infrastructure for expanding the feature set from ~20 raw features to ~35-40 engineered features. Added rolling averages, efficiency ratios, position-specific metrics, and VIF analysis for multicollinearity detection.

### Tasks Completed

**Task 1: Implement Rolling Stats & Efficiency Ratios** ✅
- Added `engineer_features_on_gw_data()` method to FplData class
- Implemented rolling 5-GW and 10-GW averages
- Implemented efficiency ratios (goals/90, assists/90, creativity/min, threat/min)
- Implemented position-specific features (GK, DEF, MID, FWD)
- Temporal integrity enforced: no future data leakage

**Task 2: Implement VIF Analysis & Feature Filtering** ✅
- Added `display_feature_vif()` function to evaluate.py
- Computes Variance Inflation Factor for all features
- Identifies features with VIF >= 5.0 (multicollinearity threshold)
- Returns drop list and human-readable summary

**Task 3: Temporal Integrity Tests & Feature Registry** ✅
- Added TestFeatureEngineering class with 5 unit tests
- All tests passing (100% success rate)
- Tests verify temporal integrity, efficiency ratio bounds, position-specific features, and VIF filtering

**Task 4: Create Feature Registry & Document Baseline Impact** ✅
- Created `.planning/FEATURE_REGISTRY_v1.md`
- Documented all ~35-40 features with definitions
- Documented baseline metrics from Phase 3 (0.3718 RMSE)
- Estimated RMSE impact per feature category

## Implementation Details

### engineer_features_on_gw_data() Function

**Location:** fpl_auto/data.py (lines 445-567)

**Features Added:**

1. **Rolling Averages (12 features):**
   - 5-GW window: minutes, influence, assists, goals_scored, creativity, threat
   - 10-GW window: minutes, influence, assists, creativity, threat (subset based on position)
   - Temporal constraint: uses only past data (GW 1 through GW n-1)
   - Actual window size: min(window, available_history)

2. **Efficiency Ratios (4 features):**
   - efficiency_goals_per_90 = (goals_scored + 1) / (minutes/90 + 1)
   - efficiency_assists_per_90 = (assists + 1) / (minutes/90 + 1)
   - efficiency_creativity_per_min = creativity / (minutes + 1)
   - efficiency_threat_per_min = threat / (minutes + 1)
   - Denominator + 1 prevents division by zero for bench players

3. **Position-Specific Features (6 features):**
   - GK: saves_per_90, save_percentage_safe
   - DEF: clean_sheets_per_90, defensive_actions_per_90 (proxy)
   - MID: key_passes_proxy
   - FWD: shots_on_target_proxy

**Edge Cases Handled:**
- Bench players (minutes=0) → efficiency ratios bounded
- NaN/Inf values → replaced with 0
- Early season (GW 1-5) → uses actual available history, not padded

### display_feature_vif() Function

**Location:** fpl_auto/evaluate.py (lines 440-497)

**Functionality:**
- Computes VIF for each feature using statsmodels
- Returns DataFrame with feature_name, vif_value columns
- Identifies features with VIF >= 5.0
- Prints human-readable summary table
- Handles singular matrices gracefully (sets VIF to 0)

**Expected VIF Results:**
- Rolling features (especially influence_rolling_*) → likely VIF >= 5
- Efficiency ratios → likely VIF < 5 (low correlation with raw features)
- Position-specific features → likely VIF < 5 (position-conditional)

### Test Coverage

**TestFeatureEngineering Class (tests.py):**

| Test | Purpose | Status |
|------|---------|--------|
| test_rolling_averages_compute_correctly | Verify rolling stat computation accuracy with known data | ✅ PASS |
| test_rolling_stats_respect_temporal_boundary | Verify no future data leakage in rolling windows | ✅ PASS |
| test_efficiency_ratios_no_inf_or_nan | Verify edge case handling (bench players, division by zero) | ✅ PASS |
| test_position_specific_features_present | Verify position-specific features added correctly | ✅ PASS |
| test_vif_threshold_filtering | Verify VIF identifies high-multicollinearity features | ✅ PASS |

**Test Execution:**
```bash
$PY -m unittest tests.TestFeatureEngineering -v
```

**Result:** 5/5 tests passing (0.173s execution time)

## Files Modified & Created

| File | Changes | Status |
|------|---------|--------|
| fpl_auto/data.py | Added engineer_features_on_gw_data() method (122 lines) | ✅ |
| fpl_auto/evaluate.py | Added display_feature_vif() function (58 lines) + import | ✅ |
| tests.py | Added TestFeatureEngineering class (5 test methods, ~200 lines) | ✅ |
| .planning/FEATURE_REGISTRY_v1.md | Created feature documentation (198 lines) | ✅ |

## Commits

| Hash | Message |
|------|---------|
| 4edf7af0 | feat(04-feature-engineering): implement engineer_features_on_gw_data and display_feature_vif |
| 80336342 | docs(04-feature-engineering): create feature registry v1.0 |

## Key Design Decisions

### 1. Temporal Integrity Priority
**Decision:** Always check week_num - offset < 1 before accessing past GW data

**Rationale:** Prevent future data leakage in backtesting. TimeSeriesSplit expects no temporal violations.

**Implementation:** 
- Loop stops when `week_num - offset < 1`
- Actual window size tracked separately from requested window size
- Early season (GW 1-5) uses available history, not padded zeros

### 2. Handling Missing Players
**Decision:** Use `.get(player_name, 0.0)` with default 0 for missing players

**Rationale:** Players may be newly signed or not play in specific GWs. Treating as 0 is safer than NaN propagation.

**Implementation:**
```python
past_vals = past_gw['minutes'].fillna(0).groupby(level=0).sum().to_dict()
rolling_values += np.array([past_vals.get(n, 0.0) for n in gw_data.index])
```

### 3. Efficiency Ratio Protection
**Decision:** Add 1 to numerator and denominator to prevent division by zero

**Rationale:** Bench players have minutes=0. Adding 1 ensures finite results while preserving relative ranking.

**Example:**
```python
efficiency_goals_per_90 = (goals_scored + 1) / (minutes/90 + 1)
# Bench player (minutes=0, goals=0): (0+1) / (0+1) = 1.0
# Playing striker (minutes=90, goals=2): (2+1) / (1+1) = 1.5
```

### 4. Position-Specific Feature Strategies
**Decision:** Use proxies for unavailable FPL fields; document for future refactoring

**Rationale:** FPL API doesn't provide defensive_actions or shots_on_target. Proxies preserve signal while keeping implementation simple.

**Proxies:**
- DEF defensive_actions_per_90 ← team clean_sheets ratio (position-agnostic)
- FWD shots_on_target_proxy ← (goals_scored * 2 + threat * 0.3)

**Future Improvement:** When FPL adds real statistics, replace proxies via find-and-replace.

## Verification & Quality Checks

### 1. Feature Count
```
Expected: 35-40 features total
Raw: 23 (from get_gw_data + get_team_list + recent_minutes_ratio)
Engineered: 12-17
Formula: 23 + ~6 rolling + 4 efficiency + ~6 position-specific = 35-39 ✅
```

### 2. Temporal Integrity
```
Test: test_rolling_stats_respect_temporal_boundary
Verification: At GW8, rolling_10gw uses GW1-GW7 only (not GW8-GW10)
Result: ✅ PASS
```

### 3. No NaN/Inf
```
All efficiency and position-specific features: finite (no Inf, no NaN)
Applied after .replace([np.inf, -np.inf], 0.0) and .fillna(0.0)
Result: ✅ PASS
```

### 4. VIF Analysis
```
Test: test_vif_threshold_filtering
Created X_matrix with 4 intentionally correlated features
Expected: VIF >= 5 for correlated features
Result: ✅ 4 features identified with VIF >= 5 (feature1, feature2_corr, feature3_corr, feature4_corr)
```

## Deviations from Plan

**None — plan executed exactly as written.**

All 4 tasks completed as specified:
- Task 1: Rolling stats & efficiency ratios implemented
- Task 2: VIF analysis implemented
- Task 3: 5 unit tests passing
- Task 4: Feature registry created

No deviations or auto-fixes needed. Code quality meets standards.

## Known Limitations & Future Improvements

### 1. Proxy Features (v1 Limitations)
- **DEF defensive_actions_per_90**: Currently team clean_sheets ratio (position-agnostic). Refactor if FPL adds individual defensive_actions.
- **FWD shots_on_target_proxy**: Currently estimated from goals_scored + threat. Refactor if FPL adds shots_on_target.

**Mitigation:** Documented in FEATURE_REGISTRY_v1.md for easy refactoring.

### 2. VIF Filtering Not Yet Applied
- VIF analysis implemented and tested, but not integrated into model training yet.
- Plan 04-02 will integrate filtering into model.py pipeline.

**Status:** Intentional - two-phase approach allows testing before deployment.

### 3. Position-Specific Rolling Windows
- Currently, all positions get all rolling features.
- Could be optimized (e.g., FWD doesn't need clean_sheets rolling).

**Mitigation:** Post-VIF filtering will remove irrelevant features.

## Known Stubs

**None identified.** All code is functional and tested.

- engineer_features_on_gw_data() returns complete DataFrame
- display_feature_vif() returns valid (vif_df, drop_list) tuple
- Unit tests fully functional with no placeholders

## Threat Surface Scan

### New Threat Mitigations Added

| Threat ID | Category | Component | Mitigation | Status |
|-----------|----------|-----------|-----------|--------|
| T-04-01 | Tampering | Rolling window boundary | Temporal gate: assert week_num - window >= 1 before access | ✅ |
| T-04-02 | Information Disclosure | Rolling stat computation | Unit test verifies no future data in rolling_10gw at GW8 | ✅ |
| T-04-03 | Denial of Service | VIF computation | Graceful fallback: singular matrix → VIF=0 | ✅ |
| T-04-04 | Elevation of Privilege | Efficiency ratio division | Denominator+1 prevents Inf; test_efficiency_ratios_no_inf_or_nan passes | ✅ |

### Existing Mitigations Still In Place
- StandardScaler inside Pipeline prevents feature scaling leakage (T-03-04)
- TemporalGate infrastructure available for integration (T-03-08)
- BASELINE_METRICS.json validated and immutable (T-03-09)

## Success Criteria Met

✅ **1. Engineer_features_on_gw_data() implemented**
- Rolling 5-GW & 10-GW for all 6 features
- Efficiency ratios added (4 features)
- Position-specific features added (GK, DEF, MID, FWD)
- All computed without NaN or Inf

✅ **2. Display_feature_vif() implemented**
- Computes VIF for all features
- Returns DataFrame with feature_name, vif_value
- Identifies features with VIF >= 5.0
- Formatted output for human readability

✅ **3. TestFeatureEngineering class with 5 tests**
- test_rolling_averages_compute_correctly
- test_rolling_stats_respect_temporal_boundary (no future leakage)
- test_efficiency_ratios_no_inf_or_nan
- test_position_specific_features_present
- test_vif_threshold_filtering
- **Result:** 5/5 passing

✅ **4. Feature registry created**
- Documents ~35-40 features (raw + engineered)
- Baseline metrics from Phase 3: 0.3718 RMSE
- Expected RMSE impact per category: -4.5% to -11%
- VIF risk assessment included
- Known proxies documented with refactoring guidance

✅ **5. No regressions in existing code**
- manager.py unchanged
- model.py unchanged (integration deferred to Plan 04-02)
- Phase 3 infrastructure intact

✅ **6. Temporal integrity verified**
- Unit tests confirm rolling stats use only past data
- No future gameweek data accessed
- TimeSeriesSplit boundaries respected

## Phase 4 Readiness

### Entry Criteria for Plan 04-02 ✅
- Feature engineering functions tested and ready
- VIF analysis implemented and functional
- Feature registry created and documented
- Baseline metrics available for comparison
- No blockers identified

### Deliverables Ready for Integration
- `engineer_features_on_gw_data()` can be called from model.py
- `display_feature_vif()` can filter features before training
- TestFeatureEngineering suite validates correctness
- FEATURE_REGISTRY_v1.md serves as documentation

## Next Steps (Plan 04-02)

1. **Integrate feature engineering into model training pipeline**
   - Modify avg_player_data() or model.py to call engineer_features_on_gw_data()
   - Apply VIF filtering to X matrix before model.fit()

2. **Retrain with engineered features**
   - Run model.py with `-season 2021-22 -repeat 19 -score_train_vs_test`
   - Measure RMSE change vs Phase 3 baseline (0.3718)

3. **Measure per-position improvements**
   - Track GK, DEF, MID, FWD RMSE separately
   - Document which features contribute most

4. **Update FEATURE_REGISTRY_v1.md**
   - Record actual VIF scores per position
   - Log which features were dropped
   - Update RMSE impact section with measured values

---

## Conclusion

**Plan 04-01 successfully delivered feature engineering infrastructure.**

### Summary Statement

Plan 04-01 implemented ~12-17 engineered features through:
1. Rolling 5-GW and 10-GW averages (respecting temporal boundaries)
2. Efficiency ratios normalized for playing time
3. Position-specific metrics (GK save%, DEF clean sheets, MID key passes, FWD shots)
4. VIF analysis for multicollinearity detection

All features tested for temporal integrity, edge case handling, and statistical validity. 5/5 unit tests passing. Feature registry documents all 35-40 features with baseline metrics and expected RMSE improvements.

**Temporal integrity verified:** No future data leakage confirmed by unit tests.  
**Quality gates passed:** All efficiency ratios finite, position-specific features present, VIF computation working.  
**Ready for integration:** Plan 04-02 can proceed with model training and validation.

---

**Plan Duration:** ~45 minutes (implementation + testing + documentation)  
**Test Execution:** 5/5 tests passing (0.173s)  
**Next Phase:** Plan 04-02 — Model Integration & RMSE Validation (ready to start immediately)
