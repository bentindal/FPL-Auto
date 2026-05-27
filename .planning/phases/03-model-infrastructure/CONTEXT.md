# Phase 3: Model Infrastructure — Planning Context

**Phase:** 03-model-infrastructure  
**Date:** 2026-05-27  
**Depends on:** Phase 1 (Temporal Integrity), Phase 2 (Model Diagnostics)

---

## Goal

Establish proper model training pipeline with temporal-aware validation. Replace KFold with TimeSeriesSplit, wrap training in sklearn Pipeline (prevent preprocessing leakage), implement nested cross-validation, and establish baseline performance metrics.

---

## Requirements (MI-01 through MI-06)

1. **MI-01**: Wrap model training in sklearn Pipeline (prevents preprocessing data leakage)
2. **MI-02**: Replace KFold with TimeSeriesSplit (required for temporal data, prevents lookahead in validation)
3. **MI-03**: Implement nested cross-validation for hyperparameter tuning
4. **MI-04**: Add permutation importance reporting (interpret feature contributions)
5. **MI-05**: Track per-position performance breakdown and train-vs-test gap (10-20% is healthy; >20% signals overfitting)
6. **MI-06**: Establish baseline metrics using improved validation (current approach with TimeSeriesSplit + nested CV)

---

## Success Criteria

1. All model training uses sklearn Pipeline (prevents preprocessing leakage)
2. TimeSeriesSplit replaces KFold across all position models
3. Nested cross-validation implemented for hyperparameter tuning (inner loop: CV for params; outer loop: temporal test fold)
4. Permutation importance reporting available for each position; top 10 features documented
5. Baseline metrics established: per-position RMSE/MAE, train-vs-test gap tracked (10-20% healthy, >20% signals overfitting)
6. Baseline model performance on all 4 seasons (2021-22 through 2024-25) recorded as reference

---

## Research Summary

From MODEL_IMPROVEMENT.md:

- **TimeSeriesSplit is critical**: KFold causes future-data leakage (training sees matches it's supposed to predict)
- **Pipeline-based preprocessing**: StandardScaler must be inside CV fold to prevent leakage
- **Permutation importance** (not tree feature_importances_): More reliable for interpreting model decisions
- **Per-position performance**: GK, DEF, MID, FWD models should be tracked separately
- **Train-vs-test gap metric**: Healthy range is 10-20%; >20% indicates overfitting; <10% may indicate underfitting

---

## Key Decisions

- **Validation strategy**: TimeSeriesSplit with expanding window (GW 1-19 → predict GW 20, GW 1-20 → predict GW 21, etc.)
- **Hyperparameter tuning**: Nested CV (inner: GridSearchCV with TimeSeriesSplit; outer: TimeSeriesSplit for final test)
- **Feature importance**: Use permutation_importance from sklearn.inspection
- **Baseline setup**: Current approach (gradientboost, randomforest, linear, neuralnetwork) with improved validation
- **Output metrics**: RMSE, MAE, R², train-vs-test gap per position and per season

---

## Constraints & Dependencies

- Phase 1 (Temporal Integrity) must be complete — TemporalGate already enforces temporal boundaries
- Phase 2 (Model Diagnostics) informs what features might be important
- Must preserve current model types (gradientboost, randomforest, linear, neuralnetwork)
- No breaking changes to model.py or manager.py APIs (backward compatible)

---

## High-Level Approach

1. **Refactor model.py**: 
   - Wrap each position's model training in sklearn.Pipeline (StandardScaler → model)
   - Replace KFold with TimeSeriesSplit
   - Implement nested CV for hyperparameter search

2. **Add diagnostics**:
   - Permutation importance per position
   - Train-vs-test gap tracking
   - Per-season baseline metrics (4 seasons = 4 test folds)

3. **Output baseline report**:
   - RMSE/MAE per position per season
   - Train-vs-test gap diagnosis
   - Top 10 permutation importance features per position
   - Recommendations for phase 4 (feature engineering)

---

## Success Definition

- [ ] model.py refactored to use Pipeline + TimeSeriesSplit + nested CV
- [ ] Permutation importance computed and reported
- [ ] Baseline metrics (RMSE, MAE, train-vs-test gap) established across 4 seasons
- [ ] Per-position breakdown available for comparison
- [ ] No regression in manager.py predictions (manager.run_season still works with new models)
