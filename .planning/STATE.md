# PROJECT STATE: FPL-Auto Performance Optimization

**Last Updated:** 2026-05-27  
**Milestone:** Phase 4 Feature Engineering - Infrastructure Complete
**Phase:** Phase 4 (Feature Engineering) - Plan 04-02 Completed with Findings

---

## Project Reference

**Core Value**: Maximize total points the simulated team achieves across historical seasons through better predictions and smarter strategic decisions.

**Current Focus**: Establishing temporal integrity foundation and planning Phase 1 execution.

**Key Constraints**:
- Temporal Integrity: Models and strategies can only see data available at each gameweek. No lookahead bias.
- Compatibility: Must integrate with existing manager.py, team.py, data pipeline without breaking changes.
- Reproducibility: All results must be reproducible (seeded, deterministic data loading).

---

## Current Position

**Status**: Phase 4 execution complete with architectural findings  
**Phase**: 4 (Feature Engineering) - Plan 04-02 Complete
**Last Completed**: Feature engineering infrastructure + VIF filtering (2026-05-27)  
**Next Milestone**: Phase 4-03 (feature refinement) or Phase 5 (strategy framework)

**Progress**: 
```
Phases 1-3: ████████████████████ 100%
Phase 4-01: ████████████████████ 100%
Phase 4-02: ██████████░░░░░░░░░░ 50% (infrastructure done, metrics deferred)
Planning:   ██░░░░░░░░░░░░░░░░░░ 5%
```

**Current Phase Status:**
- Phase 4-01 (Feature Engineering Functions): ✅ COMPLETE
- Phase 4-02 (Integration & Measurement): ⚠️ PARTIAL
  - Infrastructure integration: ✅ Done
  - VIF filtering: ✅ Done & tested
  - Performance metrics: ⚠️ Found critical multicollinearity issue
- Phase 4-03 (Advanced Features): 🔄 BLOCKED pending feature refinement

---

## Roadmap Summary

**Total Phases**: 9  
**Total Requirements**: 36  
**Coverage**: 36/36 (100%)

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 1 | Temporal Integrity | 4 | Pending |
| 2 | Model Diagnostics | 4 | Pending |
| 3 | Model Infrastructure | 6 | Pending |
| 4 | Feature Engineering | 4 | Pending |
| 5 | Strategy Framework & Evaluation | 8 | Pending |
| 6 | Transfer Strategy Evaluation | 4 | Pending |
| 7 | Captain & Chip Evaluation | 4 | Pending |
| 8 | Bench & Substitution Evaluation | 4 | Pending |
| 9 | Performance Validation | 4 | Pending |

**Critical Path**: 1 → 2 → 3 → 4 → 5 → {6, 7, 8} → 9

**Parallelization**: Phases 6, 7, 8 can run in parallel after Phase 5 completes.

---

## Performance Metrics

### Baseline (to be established in Phase 3)

| Metric | Value | Source | Notes |
|--------|-------|--------|-------|
| Model RMSE (avg position) | TBD | Phase 3 | Before feature engineering |
| Train-vs-Test Gap | TBD | Phase 3 | Healthy if 10-20%, overfitting if >20% |
| Top 100 Manager Points (avg season) | TBD | Phase 2 | Diagnostic benchmark |
| Current Approach Points (avg season) | TBD | Phase 5 | Baseline for strategy evaluation |
| Static Team Points (avg season) | TBD | Phase 5 | Conservative baseline (no transfers) |

### Improvement Targets

| Target | Phase | Success Threshold |
|--------|-------|-------------------|
| Model RMSE improvement (feature engineering) | Phase 4 | +5% across 4 seasons |
| Strategy beats static team baseline | Phase 6-8 | Non-overlapping 95% CIs |
| Final system vs top 100 managers | Phase 9 | Within 10% of top 100 average |

---

## Accumulated Context

### Key Decisions Made

| Decision | Rationale | Status |
|----------|-----------|--------|
| Start with temporal integrity | Fix lookahead bias before model improvements (affects all downstream work) | Locked in Phase 1 |
| Use TemporalGate enforcement | Prevent future-data leakage; make violations explicit and auditable | Implementation in Phase 1 |
| TimeSeriesSplit for validation | Required for temporal data; prevents lookahead in cross-validation | Phase 3 foundation |
| Walk-forward validation for strategies | Industry standard in quantitative trading; prevents overfitting | Phase 5+ requirement |
| Bootstrapped CIs, not point estimates | Quantify uncertainty; prevent false confidence in marginal improvements | Phase 5+ requirement |
| Three strategy archetypes | Conservative, aggressive, differential-focused cover spectrum of approaches | Phase 5 implementation |

### Research Findings Applied

**From research/SUMMARY.md:**

1. **Temporal Integrity HIGH priority** → Phase 1 is critical path, blocks all downstream work
2. **Model improvement path identified** → Phases 3-4 follow research sequencing (pipeline → validation → features)
3. **Strategy evaluation framework** → Phases 5-8 implement walk-forward + bootstrapped CIs + Bonferroni correction
4. **Backtesting pitfalls** → All phases incorporate safeguards (no lookahead, proper train/test splits, statistical rigor)

### Known Issues & Blockers

| Issue | Severity | Impact | Mitigation |
|-------|----------|--------|-----------|
| Temporal integrity violation in model.py | CRITICAL | All predictions biased by lookahead | Phase 1 must fix before Phase 3 validation |
| Feature engineering scope (35-50 features) | MEDIUM | Phase 4 may be large; iteration workflow prevents explosion | Enforce >2% improvement threshold |
| Computational cost (4 seasons × strategy variants) | MEDIUM | Phase 5-8 may take hours/days | Use walk-forward (don't grid-search all seasons together) |
| Top 100 manager data completeness | MEDIUM | Phase 2 diagnostic accuracy depends on data quality | Document data lineage in Phase 2 |

### Todos for Upcoming Phases

**Phase 1 Planning:**
- [ ] Identify all data access points in model.py, team.py, data.py
- [ ] Design TemporalGate class API (what methods to intercept?)
- [ ] Write tests for temporal violation detection
- [ ] Document available data at each gameweek (GW1 ≠ GW2 ≠ GW3, etc.)

**Phase 2 Planning:**
- [ ] Verify top 100 manager data completeness (transfer history, squad compositions)
- [ ] Define squad comparison metrics (which KPIs reveal gaps?)
- [ ] Identify target GWs for comparison (GW1, mid-season point)

**Phase 3 Planning:**
- [ ] Audit existing model.py for scikit-learn best practices
- [ ] Design Pipeline structure (preprocessing → scaling → model)
- [ ] Plan nested CV configuration (inner CV folds, outer test fold)

---

## Session Continuity

**Entry Points for Next Session:**

1. **To start Phase 1 planning:**
   ```
   /gsd-plan-phase 1
   ```

2. **To review roadmap:**
   - File: `/Users/bentindal/Desktop/coding/FPL-Auto/.planning/ROADMAP.md`
   - Check: Phase details, success criteria, requirements mapping

3. **To check project status:**
   - Run: `node ./node_modules/@gsd-build/sdk/dist/cli.js query state.load`
   - Returns: Current phase, progress metrics, todos

4. **To update requirements:**
   - File: `/Users/bentindal/Desktop/coding/FPL-Auto/.planning/REQUIREMENTS.md`
   - Section: Traceability (phase mappings), Out of Scope (deferral reasons)

---

## Research Artifacts

All research findings documented in:
- `.planning/research/SUMMARY.md` — Overview, key findings, confidence levels
- `.planning/research/TEMPORAL_INTEGRITY.md` — Violations, enforcement patterns
- `.planning/research/MODEL_IMPROVEMENT.md` — Feature engineering, validation
- `.planning/research/STRATEGY_EVALUATION.md` — Walk-forward, statistical testing
- `.planning/research/BACKTESTING_PITFALLS.md` — Prevention, FPL-specific gotchas

---

*State initialized: 2026-05-27*  
*Roadmap: Complete (9 phases, 36 requirements)*  
*Ready for: Phase 1 Planning*
