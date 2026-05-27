# Research Summary: FPL-Auto Performance Optimization

**Completed:** 2026-05-27 | **Milestone:** Project Initialization

## Overview

Research across 4 dimensions (Temporal Integrity, Strategy Evaluation, Model Improvement, Backtesting Pitfalls) reveals a clear path forward: fix temporal integrity violations first, then systematically improve models and strategies using validated methodologies from quantitative trading.

## Key Findings

### 1. Temporal Integrity Issues (HIGH Priority)

**Critical Violation Found:** Model training uses actual gameweek points — this is lookahead bias.

- **In:** `model.py` lines 56-61 trains on GW(i) actual points to predict GW(i)
- **Fix:** Train only on GW(i-20) through GW(i-1)
- **Enforcement:** Implement `TemporalGate` class to intercept all data access and prevent future data leakage
- **Current lookahead:** 5-GW discount in `team.py` is *intentional* for strategy decisions (acceptable if clearly separated from scoring)

**Recommendation:** Make temporal violations explicit and auditable before any model improvements.

### 2. Model Improvement Path (MEDIUM Priority, but foundational)

**Prerequisites:**
- Wrap model training in `sklearn.pipeline.Pipeline` (prevents preprocessing leakage)
- Use `TimeSeriesSplit` instead of KFold (critical for temporal data — prevents lookahead)
- Implement nested cross-validation for hyperparameter tuning

**Workflow:**
1. Establish baseline with current models + TimeSeriesSplit validation
2. Engineer features incrementally (expand from ~20 to 35-50)
3. Target features: rolling averages, position-specific metrics, efficiency ratios
4. Iteration threshold: >2% RMSE improvement per feature addition
5. Track train-vs-test gap (should be 10-20%; >20% signals overfitting)

**Tools:**
- Use permutation importance (not `feature_importances_`) for interpretability
- Report per-position performance breakdown
- Monitor feature correlations (VIF < 5 before adding)

**Expected Impact:** Modest improvements (5-15%) once temporal violations are fixed; beyond that requires domain expertise in feature selection.

### 3. Strategy Evaluation Framework (HIGH Priority)

**Statistical Approach:**
- Use nested walk-forward validation across 4 seasons
- Establish two baselines: (A) static team, (B) current approach
- Strategies must beat both baselines to be considered improvements
- Sample size: 4 seasons detects large improvements (~100 points) with high confidence; cannot reliably detect subtle tweaks

**Reporting:**
- Multi-dimensional metrics: Sharpe ratio, Sortino ratio, total points, consistency (CV)
- Report 95% bootstrapped confidence intervals (not point estimates)
- Include per-season results (detects regime changes; e.g., strategy good in 2021-22 but fails in 2023-24)

**Implementation:**
- Define strategies as `StrategyConfig` dataclasses (~15 parameters: transfer_mode, captain_mode, chip_schedule, etc.)
- Grid search over parameter space (~100-200 combinations manageable)
- Regularize against overfitting: Apply Bonferroni correction for multiple comparisons

**Pitfall:** Without walk-forward validation, backtests look great but strategies fail forward (~90% fail rate in practice). Nested validation is non-negotiable.

### 4. Backtesting Pitfalls (CRITICAL Foundation)

**Five Pitfall Categories:**

1. **Lookahead Bias** (hardest to detect) — Uses unavailable data at decision time
   - Prevention: Enforce temporal boundaries, audit every data access, separate "available" vs "decided" data
   - Current risk: HIGH (model.py violation identified)

2. **Survivor Bias** — Missing players, price drops, transfers from historical records
   - Prevention: Preserve full transfer history, document data lineage, validate player availability drift
   - Current risk: MEDIUM (depends on data source completeness)

3. **Overfitting** — Strategies match noise, fail in live testing
   - Prevention: Walk-forward validation (non-negotiable), regularization, simplicity audit
   - Current risk: HIGH without proper validation framework

4. **Data Quality** — Missing values, name inconsistencies, duplicates, stale snapshots
   - Prevention: Schema validation on load, name normalization, immutable storage, time-series drift checks
   - Current risk: MEDIUM (existing CSV pipeline may have quality gaps)

5. **FPL-Specific Gotchas** — Price timing, injury announcements, chip constraints, blank gameweeks
   - Current risk: HIGH (2024-25 rule changes, price cascades on transfers)

## Confidence Assessment

| Research Dimension | Confidence | Key Dependencies |
|---|---|---|
| Temporal integrity solutions | HIGH | Requires code audit and TemporalGate implementation |
| Model improvement patterns | HIGH | TimeSeriesSplit + nested CV (scikit-learn standard) |
| Strategy evaluation framework | HIGH | Walk-forward validation methodology (industry standard) |
| Backtesting pitfall detection | HIGH | Code-level audits and data validation |
| FPL-specific gotchas | MEDIUM-HIGH | Requires external verification against 2024-25 rule changes |

## Recommended Sequencing

**Phase 1 (Foundation):** Fix temporal violations and establish baseline models
- Implement TemporalGate class
- Wrap model.py training in Pipelines
- Replace KFold with TimeSeriesSplit
- Establish baseline metrics (current approach on all 4 seasons)

**Phase 2 (Model Improvement):** Systematically improve xP predictions
- Feature engineering iterations (target 35-50 engineered features)
- Per-position performance analysis
- Hyperparameter tuning with nested CV
- Track improvements vs baseline

**Phase 3 (Strategy Evaluation):** Test multiple decision-making strategies
- Define StrategyConfig variants (conservative, aggressive, differential-focused)
- Implement walk-forward validation framework
- Evaluate strategies with bootstrapped CIs and per-season breakdown
- Validate against top 100 manager performance

**Phase 4 (Integration):** Compare final optimized system to historical benchmarks
- A/B test against top 100 manager approach
- Verify no lookahead bias in final system
- Document decision rules and strategy parameters

## Open Questions for Planning

1. **Data completeness:** How complete is the top 100 manager transfer history? Any survivors bias?
2. **Rule changes:** How do 2024-25 chip rule changes affect strategy comparison?
3. **Computational budget:** How long does a full 4-season simulation run? Affects strategy search scope.
4. **Feature data availability:** What position-specific data is available (e.g., saves, defensive actions)?

## Files Generated

- `.planning/research/TEMPORAL_INTEGRITY.md` — Violations found, enforcement patterns, timing architecture
- `.planning/research/MODEL_IMPROVEMENT.md` — Feature engineering, validation strategies, sklearn pitfalls
- `.planning/research/STRATEGY_EVALUATION.md` — Walk-forward validation, statistical testing, parametrization
- `.planning/research/BACKTESTING_PITFALLS.md` — Pitfall detection, prevention, FPL-specific gotchas

---
*Research completed: 2026-05-27*
