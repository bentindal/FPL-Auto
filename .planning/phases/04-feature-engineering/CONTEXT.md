# Phase 4: Feature Engineering — Planning Context

**Phase:** 04-feature-engineering  
**Date:** 2026-05-27  
**Depends on:** Phase 3 (Model Infrastructure)

---

## Goal

Expand predictor feature set from ~20 raw features to 35-50 engineered features, targeting position-specific metrics and rolling statistics. Improve model accuracy through systematic feature engineering and iteration.

---

## Requirements (FE-01 through FE-04)

1. **FE-01**: Expand feature set from ~20 raw features to 35-50 engineered features (documented in feature registry with definitions)
2. **FE-02**: Implement rolling averages, efficiency ratios, and position-specific features and add to pipeline
3. **FE-03**: Track feature correlations; all new features have VIF < 5 before inclusion
4. **FE-04**: Implement iteration workflow: hypothesis → retrain with TimeSeriesSplit → measure RMSE improvement (threshold: >2% per feature addition)

---

## Success Criteria

1. Feature set expanded from ~20 to 35-50 features (documented in feature registry with definitions)
2. Rolling averages, efficiency ratios, and position-specific features implemented and added to pipeline
3. Feature correlations tracked; all new features have VIF < 5 before inclusion
4. Iteration workflow validated: hypothesis → retrain with TimeSeriesSplit → measure RMSE improvement (threshold: >2% per feature addition)
5. Final feature set improves baseline RMSE by at least 5% across all 4 seasons (measured with temporal integrity intact)

---

## Phase 3 Baseline (Reference for Improvement Target)

**Baseline RMSE from Phase 3:** 0.3718 (3-season average)  
**Improvement Target:** ≥5% reduction → Final RMSE ≤ 0.3532 (0.3718 × 0.95)

**Position-Specific Baseline:**
- **GK:** RMSE 0.33-0.39 (least improvement potential)
- **DEF:** RMSE 0.35-0.40 (moderate potential)
- **MID:** RMSE 0.32-0.35 (good potential)
- **FWD:** RMSE 0.38-0.46 (highest improvement potential) ← **Priority for feature engineering**

**Top Existing Features (from Phase 3 permutation importance):**
- GK: clean_sheets, influence, saves
- DEF: minutes, goals_conceded, influence
- MID: influence, minutes, assists
- FWD: influence, minutes, assists

---

## Research Summary

From MODEL_IMPROVEMENT.md:

**High-Impact Feature Categories:**
1. **Form Metrics** — Rolling 5-GW, 10-GW averages of key stats
2. **Efficiency Ratios** — Goals/minutes, clean sheets/minutes, assists/minutes
3. **Position-Specific Features:**
   - GK: shots_faced, save_percentage, minutes_consistency
   - DEF: defensive_actions_per_90, clean_sheet_probability, price_trend
   - MID: key_passes, goal_scoring_opportunities, differential_ownership
   - FWD: shots_on_target, expected_points_trend, injury_rest_status

4. **Team Context** — Team strength ratings, fixture congestion, injury status
5. **Time-Series Features** — Season progression effects (GW 1-10 vs 20-38)

**Current State of Feature Set:**
- ~20 raw features extracted by `get_gw_data()`
- Missing: rolling statistics, efficiency ratios, position-specific engineered features
- Opportunity: Add 15-30 new features through engineering

---

## Current Feature Count & Gaps

**Current Features (~20):**
- Player minutes, price, form (influence, threat, creativity)
- Team stats (strength, fixture difficulty)
- Position (GK, DEF, MID, FWD)
- Recent points

**Missing Categories (to engineer ~15-30 new features):**
- [ ] Rolling 5-GW average of: minutes, influence, threat, creativity, assists, clean_sheets, goals_conceded
- [ ] Rolling 10-GW average of: minutes, influence, threat, creativity
- [ ] Efficiency ratios: goals/minutes, assists/minutes, clean_sheets/minutes, points/price
- [ ] Position-specific: GK (save%), DEF (tackles+blocks per 90), MID (key passes), FWD (shots on target)
- [ ] Season progression: GW_bucket (1-10, 11-20, 21-30, 31-38)
- [ ] Form momentum: trend direction & magnitude
- [ ] Ownership differential: selected% change YoY
- [ ] Injury risk: minutes drop indicator

---

## Technical Constraints

- **Temporal Integrity:** All features computed within TimeSeriesSplit folds (Phase 3 infrastructure)
- **No Future Data:** Rolling averages use only past data relative to prediction GW
- **VIF < 5:** Multicollinearity check required before inclusion
- **Backward Compatible:** Pipeline architecture from Phase 3 must remain intact
- **Measurable Improvement:** RMSE improvement tracked per feature addition (>2% threshold)

---

## Feature Engineering Workflow

1. **Hypothesis:** "Rolling 5-GW average of minutes will improve FWD predictions"
2. **Implementation:** Add feature to pipeline (compute within training fold only)
3. **Retrain:** Run model.py with TimeSeriesSplit, measure RMSE change
4. **Evaluate:** If >2% improvement, keep feature; else, discard or refine
5. **Document:** Add to feature registry with definition and RMSE impact

---

## Expected Outcomes

**By End of Phase 4:**
- ✅ Feature count: ~20 → 35-50 (15-30 new engineered features)
- ✅ Feature registry: Documented definitions + RMSE impact per feature
- ✅ VIF analysis: All features with VIF < 5
- ✅ Baseline improvement: RMSE reduced by ≥5% (Phase 3: 0.3718 → Target: ≤0.3532)
- ✅ Per-position breakdown: RMSE improvement tracked by position (FWD priority)
- ✅ Iteration log: Features tested, accepted/rejected, improvement measured

---

## High-Level Approach

**Wave 1:** Feature expansion & engineering
- Implement rolling statistics (5-GW, 10-GW averages)
- Implement efficiency ratios (goals/min, assists/min, etc.)
- Implement position-specific features
- Add to Pipeline infrastructure

**Wave 2:** Feature validation & optimization
- Compute VIF for all new features
- Remove highly correlated features (VIF ≥ 5)
- Retrain models with TimeSeriesSplit
- Measure RMSE improvement per position

**Wave 3:** Iteration & final baseline
- Log feature engineering decisions
- Generate final RMSE metrics (target: ≥5% improvement)
- Create feature registry (definitions + impact)
- Document best-performing feature combinations

---

## Success Definition

- [ ] Feature count expanded from ~20 to 35-50 (documented in registry)
- [ ] Rolling statistics & efficiency ratios implemented in Pipeline
- [ ] VIF < 5 for all new features (multicollinearity checked)
- [ ] Iteration workflow validated: hypothesis → retrain → measure
- [ ] RMSE improved by ≥5% across all 4 seasons (temporal integrity maintained)
- [ ] Per-position metrics show improvement (especially FWD)
- [ ] Feature registry created (definitions + RMSE impact)
- [ ] No regressions in Phase 3 infrastructure (backward compatible)
