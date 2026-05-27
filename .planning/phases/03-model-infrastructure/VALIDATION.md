# Phase 3: Model Infrastructure — Validation Guide

**Created:** 2026-05-27
**Purpose:** Define automated test commands, latency expectations, sampling continuity, and Wave 0 setup requirements for Phase 3 execution.

---

## Test Commands by Plan

### Plan 03-01: Pipeline Refactoring & TimeSeriesSplit Foundation

#### Unit Tests
```bash
# Test Pipeline equivalence and backward compatibility
cd /Users/bentindal/Desktop/coding/FPL-Auto
PY=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3

# Run all Pipeline tests
$PY -m unittest tests.TestPipelineEquivalence -v

# Run backward compatibility tests
$PY -m unittest tests.TestBackwardCompatibility -v

# Expected output: 6+ tests passing
# Latency: < 5 seconds
```

#### Integration Test
```bash
# Verify model.py still runs with new Pipeline models
$PY model.py -season 2021-22 -target_gw 20 -repeat 2 -score_train_vs_test 2>&1 | grep -E "GW|Average"

# Expected output: GW metrics without errors
# Latency: < 30 seconds (depends on -repeat count)
```

### Plan 03-02: TimeSeriesSplit Explicit + Baseline Metrics

#### Baseline Generation (Manual, One-Time)
```bash
# Generate baseline for single season (for testing purposes)
$PY model.py -season 2021-22 -save_baseline

# Full baseline generation (production, ~60 min total)
$PY model.py -season 2021-22 -save_baseline
$PY model.py -season 2022-23 -save_baseline
$PY model.py -season 2023-24 -save_baseline
$PY model.py -season 2024-25 -save_baseline
```

#### Baseline Validation
```bash
# Verify BASELINE_METRICS.json is valid JSON
python3 -c "import json; baseline=json.load(open('.planning/phases/03-model-infrastructure/BASELINE_METRICS.json')); print(f'Seasons: {list(baseline[\"seasons\"].keys())}')"

# Expected: 4 seasons listed (2021-22, 2022-23, 2023-24, 2024-25)
# Latency: < 1 second
```

#### Regression Tests
```bash
# Test baseline metrics schema and values
$PY -m unittest tests.TestBaselineMetrics -v

# Expected: 4 tests passing
# - test_baseline_file_exists
# - test_baseline_schema_valid
# - test_gap_ratio_in_healthy_range
# - test_rmse_values_reasonable
# Latency: < 5 seconds
```

#### Permutation Importance Tests
```bash
# Test permutation importance computation
$PY -m unittest tests.TestPermutationImportance -v

# Expected: 1 test passing (test_permutation_importance_computes_without_error)
# Latency: < 15 seconds (permutation importance computation is expensive)
```

#### End-to-End Test with Baseline
```bash
# Run model training with explicit TimeSeriesSplit metrics
$PY model.py -season 2021-22 -target_gw 20 -repeat 2 -score_train_vs_test -display_permutation_importance 2>&1 | head -50

# Expected output:
# - GW metrics (RMSE, train vs test gap)
# - Permutation importance output (top 10 features per position)
# Latency: < 60 seconds
```

### Plan 03-03: Manager Integration & Phase Verification

#### Manager Integration Tests
```bash
# Test manager.py works with new Pipeline models
$PY -m unittest tests.TestManagerIntegration -v

# Expected: 3 tests passing
# - test_season_simulation_runs_without_error
# - test_full_season_simulation_with_pipeline_models
# - test_predictions_loaded_from_tsv
# Latency: < 5 seconds (except full_season_simulation which may take 30+ seconds)
```

#### Temporal Integrity Tests
```bash
# Test TemporalGate is available and functional
$PY -m unittest tests.TestTemporalIntegrityInManager -v

# Expected: 1 test passing (test_temporal_gate_available)
# Latency: < 2 seconds
```

#### Backward Compatibility Tests (Tolerance-Based)
```bash
# Test Pipeline predictions within 0.01% tolerance
$PY -m unittest tests.TestPipelineBackwardCompatibility -v

# Expected: 3 tests passing
# - test_predictor_fit_and_predict
# - test_feature_importances_extraction
# - test_predictions_within_tolerance_bounds
# Latency: < 10 seconds
```

#### Full Test Suite
```bash
# Run all Phase 3 tests
$PY -m unittest tests -v 2>&1 | tail -20

# Expected: 34/34 tests passing (26 original + 8 new)
# Latency: < 60 seconds
```

---

## Latency Expectations

| Test Category | Command | Expected Latency | Notes |
|---------------|---------|------------------|-------|
| Unit Tests | `-m unittest tests.TestXxx -v` | < 5 sec | Fast, memory-only |
| Integration Tests | `model.py -season ... -target_gw ... -repeat 2` | < 30 sec | Reads/writes data |
| Baseline Generation | `model.py -season ... -save_baseline` | 15-20 min | Full 38-GW loop, all 4 positions |
| Permutation Importance | `model.py -display_permutation_importance` | 10-15 sec | 10 repeats per feature |
| Full Season Simulation | `run_season(config)` | 30-60 sec | 38 GW iterations, all logic |
| Full Test Suite | `tests -v` | < 60 sec | All 34 tests, no I/O waiting |

---

## Sampling Continuity Across Waves

### Wave 0: Setup (Prerequisites)
**Tests run: NONE** — This is setup phase only.

Required state after Wave 0:
- Source files read and understood (no code changes yet)
- Test infrastructure verified (can run `python3 -m unittest tests -v`)
- Baseline reference available (or flagged as missing)

### Wave 1: Plan 03-01 (Pipeline Wrapping)
**Tests run after implementation:**
- `tests.TestPipelineEquivalence` — Verify Pipeline fit/predict equivalence
- `tests.TestBackwardCompatibility` — Verify unchanged external API
- `model.py -season 2021-22 -target_gw 20 -repeat 2` — Integration check

**Sampling continuity:** These tests verify LOW-LEVEL model behavior. They don't depend on baseline metrics or manager.py. Pass rate should be: 6+ unit tests + successful model.py execution.

**If fails:** Stop; debug predictor.py before proceeding.

### Wave 2: Plan 03-02 (Baseline Generation)
**Tests run after implementation:**
- Manual: `model.py -save_baseline` (one-time per season)
- Automated: `tests.TestBaselineMetrics` — Schema validation
- Automated: `tests.TestPermutationImportance` — Permutation computation check
- Integration: `model.py -season ... -display_permutation_importance`

**Sampling continuity:** These tests verify MIDDLE-LEVEL model evaluation infrastructure. They **depend on** successful Plan 03-01 (Pipeline must work). They **enable** Plan 03-03 (baseline metrics must exist). Pass rate should be: 4 + 1 baseline tests passing.

**If fails:** If baseline generation fails, check model.py -target_gw values; if tests fail, check BASELINE_METRICS.json schema.

### Wave 3: Plan 03-03 (Manager Integration)
**Tests run after implementation:**
- `tests.TestManagerIntegration` — manager.run_season() works
- `tests.TestTemporalIntegrityInManager` — TemporalGate functional
- `tests.TestPipelineBackwardCompatibility` — Tolerance-based checks
- `tests -v` — Full suite (34 tests)

**Sampling continuity:** These tests verify HIGH-LEVEL system behavior. They **depend on** both Plan 03-01 (Pipeline) and Plan 03-02 (baseline metrics). They verify that all Model Infrastructure changes work together without breaking manager.py. Pass rate should be: 34/34 tests.

**If fails:** Isolate by running individual test classes; check manager.py imports and config handling.

---

## Wave 0: Test Setup Requirements

**No code changes in Wave 0.** These are prerequisites for execution to begin.

### 1. Verify Test Infrastructure
```bash
cd /Users/bentindal/Desktop/coding/FPL-Auto

# Can we import test framework?
PY=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3
$PY -c "import unittest; print('unittest OK')"

# Can we run tests (even if they fail)?
$PY -m unittest tests.TestTransferInAllowed.test_club_rule_max_three -v

# Expected: Test runs, might pass or fail (doesn't matter; we just verify framework works)
```

### 2. Verify Required Source Files Exist
```bash
# Check all files that Plan 03-01 will modify
test -f fpl_auto/predictor.py && echo "predictor.py OK" || echo "MISSING"
test -f model.py && echo "model.py OK" || echo "MISSING"
test -f tests.py && echo "tests.py OK" || echo "MISSING"
test -f fpl_auto/evaluate.py && echo "evaluate.py OK" || echo "MISSING"
test -f fpl_auto/data.py && echo "data.py OK" || echo "MISSING"

# Expected: All files present
```

### 3. Verify Data Available for Tests
```bash
# Check training data exists
test -d data/2021-22 && echo "2021-22 data OK" || echo "MISSING"
test -f data/2021-22/gameweeks.csv && echo "gameweeks.csv OK" || echo "MISSING"

# Check predictions directory structure (will be created during Plan 03-02)
mkdir -p predictions/2021-22

# Expected: Data directory present, predictions dir created
```

### 4. Check Existing Test Status
```bash
# How many tests currently pass?
$PY -m unittest tests -v 2>&1 | grep "Ran" | head -1

# Expected: "Ran 26 tests" (26 existing tests before Phase 3)
# If different, investigate why
```

### 5. Verify sklearn and Dependencies
```bash
# Check critical dependencies for Phase 3
$PY -c "from sklearn.preprocessing import StandardScaler; from sklearn.pipeline import Pipeline; from sklearn.model_selection import TimeSeriesSplit; print('sklearn OK')"

# Expected: No import errors
```

---

## Verification Checklist for Each Plan

### After Plan 03-01 Implementation (Wave 1)
- [ ] `python3 -m unittest tests.TestPipelineEquivalence -v` passes (6+ tests)
- [ ] `python3 -m unittest tests.TestBackwardCompatibility -v` passes (4+ tests)
- [ ] `python3 model.py -season 2021-22 -target_gw 20 -repeat 2` completes without error
- [ ] Output shows GW metrics (RMSE, AE) without NaN or Inf values
- [ ] No changes to manager.py behavior (verify by spot-check: `from manager import ...` succeeds)

### After Plan 03-02 Implementation (Wave 2)
- [ ] Baseline generation command runs: `python3 model.py -season 2021-22 -save_baseline` (manually once per season)
- [ ] BASELINE_METRICS.json exists at `.planning/phases/03-model-infrastructure/BASELINE_METRICS.json`
- [ ] `python3 -c "import json; json.load(open('.planning/phases/03-model-infrastructure/BASELINE_METRICS.json'))"` succeeds (valid JSON)
- [ ] `python3 -m unittest tests.TestBaselineMetrics -v` passes (4 tests)
- [ ] `python3 -m unittest tests.TestPermutationImportance -v` passes (1 test)
- [ ] Permutation importance output appears when running `python3 model.py -season 2021-22 -target_gw 25 -repeat 1 -display_permutation_importance`

### After Plan 03-03 Implementation (Wave 3)
- [ ] `python3 -m unittest tests.TestManagerIntegration -v` passes (3 tests)
- [ ] `python3 -m unittest tests.TestTemporalIntegrityInManager -v` passes (1 test)
- [ ] `python3 -m unittest tests.TestPipelineBackwardCompatibility -v` passes (3 tests)
- [ ] `python3 -m unittest tests -v 2>&1 | tail -1` shows "OK" (all 34 tests pass)
- [ ] PHASE_3_VERIFICATION.md exists and describes complete Phase 3 state
- [ ] No temporal leakage detected (TemporalGate audit trail clean)

---

## Failure Diagnosis by Plan

### Plan 03-01 Failure: Pipeline Tests Fail
```bash
# 1. Check predictor.py syntax
python3 -m py_compile fpl_auto/predictor.py

# 2. Check if Pipeline import works
python3 -c "from sklearn.pipeline import Pipeline; print('OK')"

# 3. Run a minimal predictor test
python3 -c "
from fpl_auto.predictor import Predictor
import numpy as np
X = np.random.randn(50, 10)
y = np.random.randn(50)
p = Predictor('gradientboost').fit([(X, y)] * 4)
preds = p.predict([X[:5]] * 4)
print(f'Predictions: {len(preds)} positions')
"

# 4. If step 3 fails, check exact error message and debug predictor._build_model()
```

### Plan 03-02 Failure: Baseline Generation Fails
```bash
# 1. Check if model.py has compute_baseline_metrics function
python3 -c "from model import compute_baseline_metrics; print('Function exists')"

# 2. Try generating baseline for just 1 GW to test logic
python3 model.py -season 2021-22 -target_gw 1 -repeat 1 -save_baseline

# 3. If that works, try full season (but with fewer repeats to test faster)
python3 model.py -season 2021-22 -save_baseline 2>&1 | tail -20

# 4. Check if BASELINE_METRICS.json was created
ls -lh .planning/phases/03-model-infrastructure/BASELINE_METRICS.json

# 5. Validate JSON
python3 -c "import json; json.load(open('.planning/phases/03-model-infrastructure/BASELINE_METRICS.json')); print('Valid JSON')"
```

### Plan 03-03 Failure: Manager Integration Tests Fail
```bash
# 1. Check if manager imports
python3 -c "from manager import run_season; print('run_season imports OK')"

# 2. Check if Config class exists
python3 -c "from manager import Config; print('Config imports OK')"

# 3. Try a minimal run_season call with small sample
python3 -c "
from manager import run_season, Config
config = Config(season='2021-22')
# Note: This might fail if manager.py requires additional setup; that's OK for now
print('Config created OK')
"

# 4. Check temporal gate
python3 -c "from fpl_auto.temporal import TemporalGate; print('TemporalGate imports OK')"
```

---

## Test Independence & Isolation

Each test class in Phase 3 is designed to run independently:

- **TestPipelineEquivalence**: Tests only predictor.py behavior (no external dependencies)
- **TestBackwardCompatibility**: Tests unchanged APIs (no data needed)
- **TestBaselineMetrics**: Requires BASELINE_METRICS.json file (must exist)
- **TestPermutationImportance**: Tests evaluate.py function (self-contained with dummy data)
- **TestManagerIntegration**: Requires manager.py and data directory (might skip if not available)
- **TestTemporalIntegrityInManager**: Tests temporal.py imports (requires Phase 1 to exist)
- **TestPipelineBackwardCompatibility**: Tests predictor.py with tolerance bounds (self-contained)

**Isolation benefit:** If TestBaselineMetrics fails but TestPipelineEquivalence passes, the problem is isolated to baseline generation or JSON schema, not the Pipeline itself.

---

## Performance Baseline for Future Phases

Record these baseline values before Phase 4 begins:

```
Phase 3 Completion Snapshot:
- Test suite latency: ~40 seconds (full 34 tests)
- Baseline generation per season: ~15 minutes
- Manager.run_season() latency: 30-60 seconds per season
- Permutation importance per position: 2-3 seconds

These values help Phase 4 detect regressions in model fitting time or test execution time.
```

---

## Next Steps: Phase 4 Preparation

Before Phase 4 begins:

1. **Verify all Phase 3 tests pass**: `python3 -m unittest tests -v` should show 34/34 passing
2. **Commit VALIDATION.md and all test files**: Ensure git history shows Phase 3 completion
3. **Create Phase 4 planning artifacts**: REQUIREMENTS.md should reference BASELINE_METRICS.json
4. **Prepare feature engineering backlog**: Phase 4 will use permutation importance to guide feature candidates
5. **Review PHASE_3_VERIFICATION.md**: Confirm temporal integrity, backward compatibility, and no technical debt
