---
phase: 06-transfer-strategy-evaluation
plan: 01
date_completed: 2026-05-27
status: COMPLETE
---

# Phase 6 Plan 1: StrategyConfig Extension & Variant Definitions

## Overview

Extended the StrategyConfig dataclass with 4 new transfer parameters and implemented budget-aware transfer logic in auto_transfer(). Defined 5 preset variant configurations covering a diagonal from conservative-early to aggressive-late strategies. All changes maintain backward compatibility with existing code.

## One-liner

StrategyConfig extended with transfer_budget_per_gw, transfer_window_gw_range, transfer_xp_threshold, transfer_xp_threshold_mode; auto_transfer() now enforces budget/window/threshold constraints; 5 variants defined and validated.

## Deliverables

### Files Modified

| File | Changes |
|------|---------|
| fpl_auto/strategies.py | +189 lines: 4 new StrategyConfig parameters + validation + 5 variant instances |
| fpl_auto/team.py | +76 lines: transfer_budget_spent initialization + budget/window/threshold logic in auto_transfer() |
| tests.py | +114 lines: 16 unit tests for parameter validation and variant instantiation |

### New Parameters Added to StrategyConfig

1. **transfer_budget_per_gw: float = 1.5**
   - Points-per-GW budget for transfers
   - Range: (0.0, 10.0]
   - Reset each GW; cumulative within a GW only
   - Examples: 0.5 (conservative), 1.5 (baseline), 2.0 (aggressive)

2. **transfer_window_gw_range: Optional[Tuple[int, int]] = None**
   - Restrict transfers to GW range [start, end] inclusive
   - Range: None or (1-38, 1-38) with start <= end
   - Examples: (1, 10) for early, (11, 24) for mid, (25, 38) for late

3. **transfer_xp_threshold: float = 0.15**
   - Threshold for transfer trigger
   - Range: [0.0, 1.0] for relative; [0.0, 50.0] for absolute
   - Interpretation depends on transfer_xp_threshold_mode

4. **transfer_xp_threshold_mode: str = 'relative'**
   - How to interpret transfer_xp_threshold
   - Options: 'relative' | 'absolute'
   - 'relative': (new_xp - old_xp) / old_xp > threshold (percentage improvement)
   - 'absolute': (new_xp - old_xp) >= threshold (points improvement)

### 5 Variant Configurations Defined

| Variant | Budget | Window | Threshold | Mode | Use Case |
|---------|--------|--------|-----------|------|----------|
| CONSERVATIVE_EARLY | 0.5 | (1, 10) | 0.20 | relative | Low-risk, early season only |
| CONSERVATIVE_FULL | 0.5 | None | 0.20 | relative | Low-risk, full season |
| BASELINE_MID | 1.5 | (11, 24) | 0.15 | relative | Baseline, mid-season focus |
| AGGRESSIVE_LATE | 2.0 | (25, 38) | 0.10 | relative | High-risk, late season only |
| AGGRESSIVE_FULL | 2.0 | None | 0.10 | relative | High-risk, full season |

All variants inherit captain/chip/bench parameters from BASELINE_CURRENT for consistency.

### auto_transfer() Implementation

**Signature:** `def auto_transfer(self, strategy_config=None, threshold=None):`

**Features:**
- Accepts optional StrategyConfig parameter (backward compatible)
- Budget constraint: tracks transfer_budget_spent, stops when exhausted
- Window constraint: skips transfers outside transfer_window_gw_range
- Threshold constraint: supports relative (%) and absolute (points) modes
- Diagnostic logging: all skipped/executed transfers logged with reasons
- transfer_budget_spent initialized in Team.__init__ and reset per GW

**Constraint Logic:**
1. Window gate: returns early if gameweek outside transfer_window_gw_range
2. Budget gate: stops transfer loop when transfer_budget_spent >= transfer_budget_per_gw
3. Threshold gate: skips transfer if improvement < threshold (relative or absolute)
4. Minimum xp_gain gate: skips if xp_gain < 2 (existing constraint)

## Test Results

### Unit Tests (TestStrategyConfigTransferParameters)

All 16 tests passing:

```
test_accept_positive_budget ..................... PASS
test_accept_valid_relative_threshold ............ PASS
test_accept_valid_window_early .................. PASS
test_accept_valid_window_full ................... PASS
test_all_five_variants_instantiate .............. PASS
test_default_transfer_parameters ................ PASS
test_reject_invalid_threshold_mode .............. PASS
test_reject_invalid_window_start_greater_than_end PASS
test_reject_negative_budget ..................... PASS
test_reject_relative_threshold_above_one ........ PASS
test_reject_relative_threshold_below_zero ....... PASS
test_reject_window_bounds_above_38 .............. PASS
test_reject_window_bounds_below_1 ............... PASS
test_reject_zero_budget ......................... PASS
test_variant_aggressive_full_values ............ PASS
test_variant_conservative_early_values ......... PASS
```

### Validation Verification

- Default StrategyConfig instantiation: ✓ PASS
- Parameter validation in __post_init__: ✓ PASS
- All 5 variants instantiate without error: ✓ PASS
- Variant parameter values correct: ✓ PASS

## Git Commits

| Hash | Message |
|------|---------|
| c41962c9 | feat(06-01): extend StrategyConfig with transfer parameters and define 5 strategy variants |
| dde5790a | feat(06-01): implement budget-aware transfer logic in auto_transfer() |
| d8d9766c | test(06-01): add comprehensive unit tests for StrategyConfig transfer parameters |

## Requirements Covered

- **TS-01 (Transfer frequency variants)**: ✓ transfer_budget_per_gw parameter + 5 variants with budget values 0.5, 1.5, 2.0
- **TS-02 (Transfer timing variants)**: ✓ transfer_window_gw_range parameter + 5 variants with windows (1,10), (11,24), (25,38), None

## Backward Compatibility

✓ Old callers of auto_transfer(threshold=4) still work unchanged
✓ Existing code using StrategyConfig continues to work
✓ No breaking changes to Team class
✓ New variant instances exported from strategies module

## Deviations from Plan

None - plan executed exactly as written.

## Known Issues & Blockers

None. All tasks complete and verified.

## Ready for Next Steps

✓ Plan 02 (Integration tests on single season) can proceed
✓ Plans 03-05 (Walk-forward evaluation) can proceed
✓ Phase 6 exit criteria met: variants defined, constraints wired, tests passing

## Statistics

- **Lines of code added**: 379
- **Files modified**: 3
- **Tests added**: 16 (all passing)
- **Test coverage**: 18 validation test cases total
- **Execution time**: ~15 minutes
- **Status**: COMPLETE

---

*Summary completed: 2026-05-27*
