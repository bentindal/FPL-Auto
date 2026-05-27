---
phase: 01-temporal-integrity
plan: 01
date: 2026-05-27
status: complete
subsystem: temporal integrity enforcement
tags: [foundation, architecture, lookahead-prevention, data-access-control]
duration: 45 minutes
completed_date: 2026-05-27
---

# Phase 1 Plan 01: Temporal Integrity Foundation Summary

**One-liner:** Established temporal integrity enforcement by creating TemporalGate validation class, fixing model training lookahead bias, and documenting data access temporal contracts.

## Objectives Met

✓ Implemented TemporalGate class to validate data access boundaries during backtesting
✓ Fixed model.py line 58 to exclude current gameweek from training data
✓ Documented temporal semantics in FplData key methods for Phase 2 integration
✓ Created foundation for automated violation detection tests

## Executed Tasks

### Task 1: Create TemporalGate Validation Class

**File created:** `fpl_auto/temporal.py` (138 lines)

**Delivered:**
- `TemporalViolationError` exception class inheriting from Exception
- `TemporalGate` class with:
  - `__init__(season: str, decision_gameweek: int)` constructor
  - `safe_read_historical_form(target_gw: int) -> bool` - validates `target_gw < decision_gameweek`
  - `safe_read_predictions(target_gw: int) -> bool` - validates `target_gw == decision_gameweek`
  - `safe_read_fixture_metadata() -> bool` - always returns True (fixtures known pre-season)
  - `_access_log: list` - maintains tuple records (data_type, accessed_gw, decision_gw, allowed)
  - `audit_trail() -> list` - returns access log for testing
  - `__repr__() -> str` - shows violation count and access summary

**Verification:**
- ✓ Boundary checks: `safe_read_historical_form(9)` during GW10 returns True
- ✓ Violation detection: `safe_read_historical_form(10)` during GW10 raises TemporalViolationError
- ✓ Prediction checks: `safe_read_predictions(10)` during GW10 returns True
- ✓ Prediction boundary: `safe_read_predictions(11)` during GW10 raises TemporalViolationError
- ✓ Fixture access: `safe_read_fixture_metadata()` always returns True
- ✓ Audit trail: violations logged with (data_type, gw, decision_gw, allowed)

**Commit:** `20ccdc48` — feat(01-temporal-integrity): create TemporalGate class with safe_read_* methods

---

### Task 2: Fix Model Training Lookahead Violation

**File modified:** `model.py` line 58

**Before:**
```python
training_data, test_data = vastaav.get_training_data_all(season, i - training_prev_weeks, i)
```

**After:**
```python
training_data, test_data = vastaav.get_training_data_all(season, i - training_prev_weeks - 1, i - 1)
```

**Impact:** Models now train on strictly historical data GW(i-20) through GW(i-1), excluding the target GW(i). This eliminates lookahead bias where models had access to actual points of the gameweek they were predicting.

**Verification:**
- ✓ Line 58 contains corrected `get_training_data_all(season, i - training_prev_weeks - 1, i - 1)`
- ✓ model.py compiles without syntax errors
- ✓ Training boundary semantics align with temporal rule: no current-GW data in training set

**Commit:** `4c8d5d02` — fix(01-temporal-integrity): exclude current GW from model training data

---

### Task 3: Document Temporal Semantics in FplData

**File modified:** `fpl_auto/data.py` (4 methods documented)

**Changes:**

1. **`get_gw_data(season, week_num)`** (lines 54-66)
   - Added 12-line docstring documenting: "During GW(N) decisions, only access GW(1) through GW(N-1)"
   - References future TemporalGate integration in Phase 2

2. **`actual_points_dict(season, week_num)`** (lines 234-248)
   - Added 14-line docstring documenting: "Only call for PAST gameweeks, never read GW(N) during GW(N) decisions"
   - Clarifies semantic contract: this method reads actual results, not predictions

3. **`get_predictions(gw, pos)`** (lines 46-59)
   - Added 15-line docstring documenting: "Predictions must be pre-trained, during GW(N) only read GW(N), never GW(N+1) or later"
   - Emphasizes overnight pre-training requirement

4. **`get_training_data_all(season, from_gw, to_gw)`** (lines 185-187)
   - Added 2-line inline comment documenting: "to_gw is INCLUSIVE; MUST call with (i - 20, i - 1) not (i - 19, i)"
   - References the model.py fix and explains the lookahead prevention

**Verification:**
- ✓ All four methods contain temporal rule documentation
- ✓ data.py compiles without syntax errors
- ✓ Docstrings follow existing project conventions
- ✓ Temporal contracts clearly stated for Phase 2 TemporalGate integration

**Commit:** `ed42af71` — docs(01-temporal-integrity): add temporal semantics to FplData methods

---

## Deviations from Plan

None — plan executed exactly as written. All three tasks completed with full specification compliance.

---

## Technical Details

### Temporal Boundary Model

| Data Type | Access Rule | Usage |
|-----------|-------------|-------|
| Historical form (past GW stats) | `target_gw < decision_gameweek` | Team decisions, performance analysis |
| Predictions (xP estimates) | `target_gw == decision_gameweek` | Gameweek strategy (captain, transfers) |
| Fixture metadata | Always allowed | Multi-GW lookahead, opponent difficulty |
| Current GW actual points | Never during GW(N) decisions | Only revealed after deadline |

### Architecture Integration Point

TemporalGate is fully self-contained and **not yet integrated** with FplData. Phase 2 will:
1. Wrap `fpl_data.get_gw_data()` calls in `Team.__init__` with `TemporalGate.safe_read_historical_form()`
2. Validate prediction reads with `safe_read_predictions()`
3. Build violation audit trails for testing and debugging

### Files Modified

| File | Lines Added | Lines Modified | Status |
|------|------------|-----------------|--------|
| `fpl_auto/temporal.py` | 138 | 0 | NEW |
| `model.py` | 0 | 1 | FIXED |
| `fpl_auto/data.py` | 67 | 5 | DOCUMENTED |

---

## Verification Checklist

- ✓ TemporalGate class created with all required methods
- ✓ TemporalViolationError exception implemented and tested
- ✓ safe_read_* methods enforce correct boundaries
- ✓ audit_trail() captures access logs for testing
- ✓ model.py line 58 corrected to exclude GW(i) from training
- ✓ All files compile without syntax errors
- ✓ FplData methods documented with temporal contracts
- ✓ No breaking changes to existing API
- ✓ Foundation ready for Phase 2 Team integration

---

## Dependencies for Phase 2

Phase 2 (Team Integration) requires:
- TemporalGate class ✓ (ready in `fpl_auto/temporal.py`)
- Temporal semantics documentation ✓ (ready in `fpl_auto/data.py` docstrings)
- Model training lookahead fix ✓ (ready in `model.py`)

Next phase will integrate TemporalGate into `Team.__init__` to intercept `fpl_data` calls and raise violations when strategies access out-of-bounds gameweeks.

---

## Key Insights

1. **Lookahead Bias Eliminated:** The model.py fix (from `i` to `i-1`) ensures models never train on the outcome they're predicting. This is foundational to fair backtesting.

2. **Temporal Semantics Explicit:** By documenting these rules in method docstrings, we create a contract that any future refactoring or optimization must respect.

3. **Audit Trail Ready:** TemporalGate's access log will allow Phase 2 to generate detailed violation reports for debugging strategies that accidentally violate temporal boundaries.

---

## Self-Check: PASSED

- ✓ `fpl_auto/temporal.py` exists with TemporalGate class (138 lines)
- ✓ `model.py` line 58 shows corrected `get_training_data_all(season, i - training_prev_weeks - 1, i - 1)`
- ✓ `fpl_auto/data.py` contains temporal docstrings for all four key methods
- ✓ All three commits exist: `20ccdc48`, `4c8d5d02`, `ed42af71`
- ✓ All verifications passed: TemporalGate tests, syntax checks, docstring grepping
