# Phase 3: Model Infrastructure — Planning Summary

**Status:** ✅ PLANNING COMPLETE & VERIFIED  
**Date:** 2026-05-27  
**Version:** 2.0 (revised after verification)

---

## Overview

Three executable plans created for Phase 3: Model Infrastructure, establishing proper model training pipeline with temporal-aware validation (sklearn Pipeline, TimeSeriesSplit, nested cross-validation).

**Total Deliverables:**
- 3 PLAN.md files (Plan 01, 02, 03)
- 1 VALIDATION.md (Nyquist compliance & test infrastructure)
- 1 CONTEXT.md (phase context & requirements)

---

## Phase Goals

Establish proper model training pipeline with temporal-aware validation:
1. ✅ Wrap model training in sklearn Pipeline (prevents preprocessing leakage)
2. ✅ Replace KFold with TimeSeriesSplit (prevents lookahead bias in validation)
3. ✅ Implement nested cross-validation for hyperparameter tuning
4. ✅ Add permutation importance reporting for feature interpretation
5. ✅ Track train-vs-test gap per position (healthy: 10-20%, overfitting: >20%)
6. ✅ Establish baseline metrics across all 4 seasons (2021-22 through 2024-25)

**All 6 requirements (MI-01 through MI-06) are fully covered.**

---

## Plan Breakdown

### Wave 1: Plan 03-01 — Pipeline Refactoring & Temporal Validation Foundation

**Scope:** 3 tasks (pipeline wrapping, TimeSeriesSplit structure, nested CV infrastructure)

**Requirements Addressed:** MI-01, MI-02, MI-03

**Key Outputs:**
- Refactored `fpl_auto/predictor.py` — All 4 model types wrapped in Pipeline(StandardScaler + model)
- Updated `model.py` — TimeSeriesSplit validation structure (GW-by-GW expanding window)
- Added `fpl_auto/evaluate.py` — Nested CV infrastructure foundation

**Success Criteria:**
- Pipeline wrapping prevents preprocessing leakage
- TimeSeriesSplit respects temporal ordering
- Backward compatibility tests pass (predictions functionally identical)

---

### Wave 2: Plan 03-02 — Nested CV, Permutation Importance & Baseline Metrics

**Scope:** 3 tasks (nested CV implementation, permutation importance reporting, baseline metrics generation)

**Requirements Addressed:** MI-02, MI-03, MI-04, MI-05, MI-06

**Key Outputs:**
- `model.py` — `evaluate_with_nested_cv()`, `compute_baseline_metrics()` functions
- `fpl_auto/evaluate.py` — `display_permutation_importance()` function
- `.planning/phases/03-model-infrastructure/BASELINE_METRICS.json` — 4-season baseline reference
- Tests — 5 new test classes validating baseline computation

**Success Criteria:**
- Nested CV (inner: GridSearchCV; outer: TimeSeriesSplit) computes hyperparameters correctly
- Permutation importance per position shows top 10 features
- Baseline metrics recorded for all 4 seasons (RMSE, MAE, train-vs-test gap)
- Train-vs-test gap tracked (healthy: 10-20%, overfitting alert: >20%)

---

### Wave 3: Plan 03-03 — Manager Integration & Final Verification

**Scope:** 2 tasks (integration testing, temporal integrity audit, backward compatibility verification)

**Requirements Addressed:** MI-06

**Key Outputs:**
- Integration tests validating manager.py works with new Pipeline models
- Temporal integrity audit confirming no lookahead bias introduced
- Backward compatibility verification (tolerance bounds: 0.01% floating-point variance)
- `.planning/phases/03-model-infrastructure/PHASE_3_VERIFICATION.md` — Comprehensive verification report

**Success Criteria:**
- manager.run_season() completes successfully with new Pipeline models
- Full-season simulation produces valid results
- Predictions match baseline within 0.01% tolerance (floating-point variance expected)
- No temporal violations detected in final system
- All 6 requirements verified as satisfied

---

## Verification Status

| Check | Status | Notes |
|-------|--------|-------|
| ✅ All 6 requirements mapped | PASS | MI-01 through MI-06 fully covered |
| ✅ Tasks executable | PASS | Clear action steps, measurable success criteria |
| ✅ Dependencies documented | PASS | 03-01 → 03-02 → 03-03 (linear sequence) |
| ✅ Test coverage specified | PASS | Unit, integration, backward compatibility, temporal integrity |
| ✅ Blockers resolved | PASS | 2 blockers fixed (tolerance bounds, VALIDATION.md) |
| ✅ Warnings addressed | PASS | 2 warnings fixed (baseline pseudocode, full-season test) |
| ✅ VALIDATION.md exists | PASS | Complete test infrastructure & Nyquist compliance |
| ✅ No deletions | PASS | All requirements & tasks retained |

---

## Effort Estimate

| Wave | Plan | Tasks | Estimated Effort | Notes |
|------|------|-------|------------------|-------|
| 1 | 03-01 | 3 | ~30-40 hours | Pipeline refactoring, moderate complexity |
| 2 | 03-02 | 3 | ~40-50 hours | Baseline generation (15-20 min per season), testing |
| 3 | 03-03 | 2 | ~20-30 hours | Integration testing, verification |
| — | — | **8 total** | **~90-120 hours** | Parallelizable within waves (3 tasks per wave) |

---

## How to Execute

### Run Plan 03-01 (Wave 1):
```bash
/gsd-execute-phase 03-model-infrastructure --plan 03-01
```

### After 03-01 completes, run Plan 03-02 (Wave 2):
```bash
/gsd-execute-phase 03-model-infrastructure --plan 03-02
```

### After 03-02 completes, run Plan 03-03 (Wave 3):
```bash
/gsd-execute-phase 03-model-infrastructure --plan 03-03
```

### Or execute all three in sequence:
```bash
/gsd-execute-phase 03
```

---

## Deliverables

After execution completes, the following artifacts will be generated:

1. **Refactored Code:**
   - `fpl_auto/predictor.py` — Pipeline-wrapped models
   - `model.py` — TimeSeriesSplit + nested CV validation
   - `fpl_auto/evaluate.py` — Permutation importance & baseline reporting

2. **Reference Metrics:**
   - `.planning/phases/03-model-infrastructure/BASELINE_METRICS.json` — 4-season baseline (RMSE, MAE, gap_ratio per position)
   - `.planning/phases/03-model-infrastructure/PHASE_3_VERIFICATION.md` — Comprehensive verification report

3. **Test Suite:**
   - 31 total tests (26 existing + 5 new)
   - All tests passing with new Pipeline models
   - Full-season integration test validating manager.py compatibility

---

## Key Design Decisions

1. **Pipeline Wrapping:** StandardScaler inside Pipeline (not before split) prevents preprocessing leakage
2. **TimeSeriesSplit:** Expanding window validation respects temporal ordering
3. **Nested CV:** Inner loop tunes hyperparameters; outer loop measures generalization
4. **Tolerance Bounds:** 0.01% floating-point variance acceptable after scaler internals change
5. **Backward Compatibility:** New models produce functionally identical predictions (within tolerance)

---

## Risk Mitigation

**Identified Risks & Mitigations:**
- **Risk:** Floating-point differences after refactoring break integration tests
  - **Mitigation:** Tolerance bounds (0.01%) explicitly documented; regression tests use `assertAlmostEqual`
  
- **Risk:** Manager.py expects different model API
  - **Mitigation:** Backward compatibility tests verify API unchanged
  
- **Risk:** Baseline metrics computation is incorrect
  - **Mitigation:** Pseudocode explicit; tests validate aggregation logic; per-season audits documented

---

## Next Steps

1. ✅ Review this summary and CONTEXT.md
2. ✅ Confirm no additional dependencies or constraints
3. ⏭️ Execute Plan 03-01: `/gsd-execute-phase 03-model-infrastructure --plan 03-01`
4. ⏭️ Execute Plan 03-02 (depends on 03-01)
5. ⏭️ Execute Plan 03-03 (depends on 03-02)
6. ⏭️ Verify PHASE_3_VERIFICATION.md confirms all 6 requirements satisfied
7. ⏭️ Proceed to Phase 4: Feature Engineering

---

*Planning completed: 2026-05-27*  
*Verification passed: 2026-05-27 (v2.0)*
