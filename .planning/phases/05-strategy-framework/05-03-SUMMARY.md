---
phase: 05-strategy-framework
plan: 03
subsystem: evaluation/metrics
tags: [metrics, bootstrapping, statistics, strategy-comparison]
dependency_graph: |
  requires: [05-02 (walk-forward framework)]
  provides: [metric computation, CI estimation, multi-comparison correction]
  affects: [Phase 06-08 (strategy comparison and selection)]
tech_stack:
  added: [numpy for numerical computation]
  patterns: [functional metrics library, bootstrap resampling]
key_files:
  created: 
    - evaluation/metrics.py (11.9 KB)
  modified:
    - evaluation/__init__.py (updated imports)
    - evaluation/walk_forward.py (refactored to use metrics module)
decisions: []
metrics:
  duration_minutes: 15
  completed_date: "2026-05-27T18:09:52Z"
  tasks_completed: 3
  files_modified: 3
---

# Phase 05 Plan 03: Multi-Dimensional Metrics with Bootstrapping Summary

**One-liner:** Implemented statistical framework for rigorous strategy comparison with Sharpe/Sortino ratios, bootstrapped 95% confidence intervals, and multiple-comparison correction.

## Objective Completion

Successfully implemented all four required functions in `evaluation/metrics.py` to provide a multi-dimensional metrics framework with bootstrapped confidence intervals for strategy evaluation:

### 1. compute_season_metrics() ✓
Computes comprehensive metrics from weekly points:
- **Primary metrics:** total_points, mean_gw_points, std_gw_points
- **Risk-adjusted metrics:** sharpe_ratio, sortino_ratio
- **Consistency metric:** coefficient_variation (std / mean)
- **Drawdown metric:** max_drawdown (worst cumulative loss)
- **Extremes:** best_week, worst_week
- **Optional baseline comparison:** vs_baseline_total_points, vs_baseline_win_rate

**Key implementation details:**
- Sharpe ratio: (mean - rf) / std with rf=0 for FPL
- Sortino ratio: (mean - rf) / std(downside) where downside = std of points below mean
- Coefficient of Variation: measures consistency (lower = more stable)
- Max drawdown: peak-to-current loss in absolute points

**Verified:** Works correctly with random 38-GW seasons; Sharpe ratio computation validated.

### 2. bootstrap_ci() ✓
Generates 95% confidence intervals via 10,000 resampling iterations:
- **Single strategy:** mean_a, ci_lower_a, ci_upper_a
- **Pairwise comparison:** includes mean_b, ci_lower_b, ci_upper_b, diff_mean, diff_ci_lower, diff_ci_upper
- **Significance testing:** significant flag = True if CI excludes 0

**Key implementation details:**
- Accepts list of per-season dicts (from nested_walk_forward_evaluation output)
- Resamples seasons with replacement 10,000 times
- Computes percentile bounds at (α/2, 1-α/2) for 95% CI
- Pairwise difference computed from bootstrap resamples

**Verified:** Correctly identifies significant differences; CI bounds exclude zero when strategies differ.

### 3. apply_bonferroni_correction() ✓
Simple utility for multiple-comparison correction:
- Returns α / num_comparisons (0.05 / 10 = 0.005 for 10 tests)
- Prevents false positives from repeated testing

**Verified:** Returns 0.005 for 10 comparisons; correct for Phase 6-8 use.

### 4. format_metrics_table() ✓
Renders markdown comparison table with metrics and confidence intervals:
- **Columns:** Strategy | Total Points | Mean ± CI | Sharpe Ratio | Sortino Ratio | CV | Max Drawdown
- **Format:** Each metric includes point estimate and 95% CI bounds
- **Suitable for:** Strategy comparison reporting in Phase 6-8

**Verified:** Successfully renders multi-strategy comparison tables.

## Architecture Integration

**Module integration:**
- `evaluation/metrics.py` (NEW): Core metrics functions, 11.9 KB
- `evaluation/__init__.py` (UPDATED): Now imports from metrics.py instead of walk_forward.py
- `evaluation/walk_forward.py` (REFACTORED): Imports compute_season_metrics from metrics.py, removed duplicate definition

**Function signatures match plan exactly:**
- `compute_season_metrics(weekly_points, baseline_weekly_points=None) -> Dict`
- `bootstrap_ci(strategy_a_seasons, strategy_b_seasons=None, metric_key='total_points', n_bootstrap=10000, ci=0.95) -> Dict`
- `apply_bonferroni_correction(num_comparisons, alpha=0.05) -> float`
- `format_metrics_table(strategy_results) -> str`

All functions have comprehensive docstrings and type hints.

## Success Criteria Verification

- ✓ `evaluation/metrics.py` exists with all 4 functions
- ✓ `compute_season_metrics()` returns dict with: total_points, sharpe_ratio, sortino_ratio, coefficient_variation, max_drawdown, best_week, worst_week
- ✓ `bootstrap_ci()` accepts strategy seasons, computes CI bounds via 10,000 resampling iterations
- ✓ `apply_bonferroni_correction(num_tests)` returns α/num_tests
- ✓ `format_metrics_table()` renders comparison results as markdown
- ✓ All functions have type hints and docstrings
- ✓ Integration verified: walk_forward.py uses metrics.compute_season_metrics()

## Testing Summary

All tests passed:

```
Task 1 - compute_season_metrics():
  ✓ Total Points computation
  ✓ Sharpe Ratio: 2.64 (mean / std)
  ✓ Sortino Ratio: 6.82 (mean / std_downside)
  ✓ Coefficient Variation: 0.38 (std / mean)
  ✓ Max Drawdown: 0.00 (no losses in sample)
  ✓ Best/Worst Week: correctly identified

Task 2 - bootstrap_ci():
  ✓ Strategy A CI: [2103, 2163] (n=4 seasons)
  ✓ Strategy B mean: 2073
  ✓ Difference CI: [13, 104] (significant, excludes 0)
  ✓ Significance flag: True

Task 3 - apply_bonferroni_correction():
  ✓ 10 comparisons: 0.005 (0.05 / 10)

Task 3b - format_metrics_table():
  ✓ Markdown table rendered with metrics and CIs
  ✓ Format suitable for reports
```

## Deviations from Plan

None - plan executed exactly as written. All four functions implemented with correct signatures and behavior.

## Known Stubs

None - all functions are fully implemented with no placeholder data.

## Threat Surface Assessment

No new threat surface. All functions operate on already-validated data (weekly_points from manager.run_season). Bootstrap resampling and Bonferroni correction are deterministic with no external inputs.

## Git Commit

- **Commit:** 5e705c7d
- **Message:** feat(05-03): implement multi-dimensional metrics with bootstrapping
- **Files changed:** 3 (1 created, 2 modified)

## Next Steps (Phase 06-08)

The metrics framework is ready for:
1. Nested walk-forward evaluation with strategy comparison
2. Bootstrap CI estimation for strategy performance differences
3. Bonferroni-corrected significance testing across multiple strategy variants
4. Markdown table reporting of comparison results

All four functions are production-ready and tested.
