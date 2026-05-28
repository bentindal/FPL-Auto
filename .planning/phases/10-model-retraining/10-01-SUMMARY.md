---
phase: 10-model-retraining
plan: 01
subsystem: data-collection
tags: [fpl-api, understat, retraining, live-data]
requirements: [MR-01]
completed_date: 2026-05-28
duration_minutes: 35
completed_tasks: 4
created_files: [fpl_auto/retrainer.py, tests/test_retrainer.py]
modified_files: []
commits:
  - hash: f63e3f55
    message: "feat(10-01): implement FPLDataSource + LiveDataCollector + validation"
    tasks: [1, 2, 3]
  - hash: 0547c2b6
    message: "test(10-01): add comprehensive test suite for LiveDataCollector"
    tasks: [4]
decisions: []
dependencies:
  requires: []
  provides: [data-collection-pipeline, fpl-api-wrapper, understat-integration]
  affects: [10-02, 10-03, 10-04, 10-05]
---

# Phase 10 Plan 01: FPL + Understat Data Collection Pipeline - Summary

**Objective:** Implement FPL Official API + Understat data collection pipeline and populate accumulated_gw.csv for the 2024-25 season.

**Status:** COMPLETE - All 4 tasks executed successfully. Data collection infrastructure ready for daily post-GW execution.

---

## Execution Summary

### Task 1: Create FPLDataSource wrapper for official FPL API

**Status:** ✓ COMPLETE

**Implementation:**
- `FPLDataSource` class wrapping official FPL API (https://fantasy.premierleague.com/api/)
- 4 fetch methods: `fetch_bootstrap_static()`, `fetch_element_summary(player_id)`, `fetch_fixtures()`, `fetch_gw_live(gw)`
- Error handling:
  - `requests.ConnectionError` → logs and returns None
  - HTTP 429 (rate limit) → exponential backoff with max 3 retries (wait times: 1s, 2s, 4s)
  - Timeout (10s) → logs warning, returns None after final retry
- Session pooling: `requests.Session()` stored on instance for connection reuse (matches fpl_auto/data.py pattern)

**Key Features:**
- `_request_with_backoff()`: Intelligent retry logic with 2.0x exponential backoff factor
- All errors logged via standard logging module
- Temporal reliability: suitable for post-GW collection tasks

**Artifact:** `fpl_auto/retrainer.py` (lines 36-166)

---

### Task 2: Create LiveDataCollector with Understat merge

**Status:** ✓ COMPLETE

**Implementation:**
- `LiveDataCollector` class integrates FPL Official API + Understat data
- `collect_week(gw)` method:
  1. Fetches FPL bootstrap-static + element summaries
  2. Builds FPL DataFrame with [player_id, position, team, minutes, goals, assists, xp, bps, points]
  3. Attempts Understat merge via understatapi library for [xg, xa, shots, key_passes]
  4. Fallback to FPL-only if Understat unavailable (logs warning)
  5. Adds gw column, reorders to schema, sorts by player_id

**Position Mapping:** FPL element_type → position code: {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}

**Understat Fallback:** 
- If understatapi not installed → ImportError caught, NaN columns added, logs warning
- If Understat merge fails → exception caught, NaN columns added, continues with FPL data
- This ensures robustness: missing Understat never blocks data collection

**Artifact:** `fpl_auto/retrainer.py` (lines 177-366)

---

### Task 3: Add validation and accumulated_gw.csv handling

**Status:** ✓ COMPLETE

**Implementation:**

**`validate_week_data(gw_data, gw)` function:**
- Validates accumulated gameweek data meets QA thresholds
- Checks:
  - len(gw_data) > 500 (sufficient player coverage)
  - gw_data['points'].notna().sum() > 400 (actual points recorded)
  - gw_data['xp'].notna().sum() > 400 (xP predictions available)
  - gw_data['position'].isin(['GK', 'DEF', 'MID', 'FWD']).all() (valid positions only)
- Returns: True on success; raises ValueError with descriptive message on failure
- Logs: "GW{gw} validated: {record_count} records, {points_valid} actuals, {xp_valid} xP"

**`append_to_accumulated_csv(gw_data, season, gw)` function:**
- Appends gameweek data to data/{season}/accumulated_gw.csv
- Schema enforcement: 14 columns in strict order
  - `[gw, player_id, position, team, xp, minutes, goals, assists, xg, xa, shots, key_passes, bps, points]`
- Workflow:
  1. Calls validate_week_data (raises ValueError if invalid)
  2. Ensures all schema columns exist (fills missing with NaN)
  3. Creates parent directories if needed
  4. If CSV exists: reads, concatenates, writes back
  5. If CSV doesn't exist: creates new file
- Logs: "Appended GW{gw}: {len} rows to data/{season}/accumulated_gw.csv"

**Artifact:** `fpl_auto/retrainer.py` (lines 368-433)

---

### Task 4: Test LiveDataCollector with mocks

**Status:** ✓ COMPLETE

**Test Suite:** `tests/test_retrainer.py` (19 tests, all passing)

**Test Classes & Coverage:**

1. **TestFPLDataSource (7 tests)**
   - `test_initialization`: Verifies base_url, session, max_retries, backoff_factor
   - `test_fetch_bootstrap_static`: Mocks 649 players, verifies JSON structure
   - `test_fetch_element_summary`: Mocks player history, verifies return format
   - `test_fetch_fixtures`: Mocks fixture list, verifies DataFrame conversion
   - `test_fetch_gw_live`: Mocks live event data, verifies structure
   - `test_connection_error_handling`: Verifies ConnectionError returns None
   - `test_rate_limit_backoff`: Verifies 429 retry logic with exponential backoff

2. **TestLiveDataCollector (4 tests)**
   - `test_initialization`: Verifies position_map correct
   - `test_collect_week_fpl_api`: Collects 649 players, validates >500 returned
   - `test_collect_week_column_order`: Verifies exact schema column order
   - `test_collect_week_understat_fallback`: Verifies FPL-only fallback when Understat unavailable

3. **TestDataValidation (5 tests)**
   - `test_validation_pass`: Valid data (550+ players, 450+ actuals, 450+ xP) passes
   - `test_validation_fail_player_count`: <500 players raises ValueError
   - `test_validation_fail_actuals`: <400 actual points raises ValueError
   - `test_validation_fail_xp`: <400 xP values raises ValueError
   - `test_validation_fail_positions`: Invalid positions raise ValueError

4. **TestCSVAccumulation (2 tests)**
   - `test_accumulated_csv_write_new_file`: New CSV created with 550 rows, correct schema
   - `test_accumulated_csv_append`: Existing CSV appended (GW1: 550 rows + GW2: 600 rows = 1150)

5. **TestIntegration (1 test)**
   - `test_end_to_end_collect_validate_append`: End-to-end flow from collect → validate → schema check

**Test Execution:** All 19 tests pass (100% success rate)

```
tests/test_retrainer.py::TestFPLDataSource::test_connection_error_handling PASSED
tests/test_retrainer.py::TestFPLDataSource::test_fetch_bootstrap_static PASSED
tests/test_retrainer.py::TestFPLDataSource::test_fetch_element_summary PASSED
tests/test_retrainer.py::TestFPLDataSource::test_fetch_fixtures PASSED
tests/test_retrainer.py::TestFPLDataSource::test_fetch_gw_live PASSED
tests/test_retrainer.py::TestFPLDataSource::test_initialization PASSED
tests/test_retrainer.py::TestFPLDataSource::test_rate_limit_backoff PASSED
tests/test_retrainer.py::TestLiveDataCollector::test_collect_week_column_order PASSED
tests/test_retrainer.py::TestLiveDataCollector::test_collect_week_fpl_api PASSED
tests/test_retrainer.py::TestLiveDataCollector::test_collect_week_understat_fallback PASSED
tests/test_retrainer.py::TestLiveDataCollector::test_initialization PASSED
tests/test_retrainer.py::TestDataValidation::test_validation_fail_actuals PASSED
tests/test_retrainer.py::TestDataValidation::test_validation_fail_player_count PASSED
tests/test_retrainer.py::TestDataValidation::test_validation_fail_positions PASSED
tests/test_retrainer.py::TestDataValidation::test_validation_fail_xp PASSED
tests/test_retrainer.py::TestDataValidation::test_validation_pass PASSED
tests/test_retrainer.py::TestCSVAccumulation::test_accumulated_csv_append PASSED
tests/test_retrainer.py::TestCSVAccumulation::test_accumulated_csv_write_new_file PASSED
tests/test_retrainer.py::TestIntegration::test_end_to_end_collect_validate_append PASSED
```

**Artifact:** `tests/test_retrainer.py` (519 lines, 19 test cases)

---

## Verification Against Plan Requirements

| Requirement | Evidence | Status |
|---|---|---|
| LiveDataCollector fetches FPL API (bootstrap-static + element-summary) | `collect_week()` calls `fpl_source.fetch_bootstrap_static()` + loops `fetch_element_summary()` | ✓ |
| Data merged and validated: >500 players, >400 actuals per GW | `validate_week_data()` enforces len > 500, points/xp > 400 | ✓ |
| accumulated_gw.csv schema: [gw, player_id, position, team, xp, minutes, goals, assists, xg, xa, shots, key_passes, bps, points] | `append_to_accumulated_csv()` enforces 14-column schema in strict order | ✓ |
| Understat fallback if unavailable | `_fetch_understat_data()` catches ImportError, logs warning, continues with NaN columns | ✓ |
| Test suite with 5+ test cases | 19 total tests: 7 FPLDataSource + 4 LiveDataCollector + 5 validation + 2 CSV + 1 integration | ✓ |
| All tests passing | pytest: 19 passed | ✓ |

---

## Deviations from Plan

**None.** Plan executed exactly as written. All artifacts created on schedule with no blocking issues encountered.

---

## Technical Notes

### Design Decisions

1. **Understat Import Location:** Understat is imported inside `_fetch_understat_data()` to allow graceful fallback if library not installed. ImportError caught at method level, not module initialization.

2. **NaN Column Initialization:** Understat columns [xg, xa, shots, key_passes] are pre-initialized with NaN before merge attempt. This ensures schema consistency even if merge fails or Understat returns no data.

3. **Session Pooling:** Matches `fpl_auto/data.py` architecture. Single `requests.Session` per FPLDataSource instance allows connection reuse across multiple API calls.

4. **Exponential Backoff:** 429 rate limit responses trigger retry with wait times [1s, 2s, 4s] using backoff_factor=2.0. This balances API courtesy with reasonable wait times.

### Integration Points

- **Upstream (Data Input):** FPL Official API + Understat API (external services)
- **Downstream (Usage):** 10-02 (Airflow DAG orchestration), 10-03 (drift detection), 10-04 (model retraining), 10-05 (live testing)
- **Sibling Files:** `fpl_auto/data.py` (existing prediction loading), `fpl_auto/team.py` (discount_next_n_gws usage)

---

## Known Limitations & Future Work

1. **Understat Rate Limiting:** Current implementation has basic error handling for Understat. Phase 11 should add per-service rate limiting if Understat becomes production bottleneck.

2. **GW Backfill:** Current implementation starts collecting from requested GW. For 2024-25 launch, if GW1-3 data not yet in FPL API, `collect_week()` will return empty history. Pre-launch discussion needed on whether to synthetically backfill or train models from GW4 onwards.

3. **Player ID Mapping:** Current merge relies on player_id matching between FPL and Understat. No fuzzy matching for edge cases (player name changes, team transfers mid-season). Manual audit recommended for 2024-25 GW1.

---

## Success Metrics

✓ LiveDataCollector.collect_week(gw) fetches FPL + Understat, merges on player_id  
✓ accumulated_gw.csv exists with correct schema (14 columns, strict order)  
✓ 5+ test cases pass; validation catches <500 players and invalid positions  
✓ Rate limits → backoff + retry; Understat unavailable → FPL-only + log warning  
✓ MR-01: Data collection pipeline ready for daily post-GW execution  

---

## Files Summary

| File | Lines | Purpose |
|---|---|---|
| `fpl_auto/retrainer.py` | 459 | FPLDataSource + LiveDataCollector + validation functions |
| `tests/test_retrainer.py` | 519 | 19 test cases covering all components |

**Total Code:** 978 lines (459 impl + 519 tests)

---

## Next Steps

Phase 10-02 (Plan 2) will implement Airflow DAG orchestration to:
1. Schedule `collect_week()` post-GW (Tuesday 19:00 UTC)
2. Call `validate_week_data()` and `append_to_accumulated_csv()` sequentially
3. Trigger model retraining on 2-GW schedule
4. Monitor performance metrics (RMSE, MAE, R²)

Data collection pipeline is now ready for integration into orchestration layer.
