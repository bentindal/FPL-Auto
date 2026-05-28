# Phase 9: Performance Validation — Planning Context

**Phase:** 09-performance-validation  
**Date:** 2026-05-28  
**Depends on:** Phase 6, Phase 7, Phase 8 (all complete)  
**Status:** Context captured — ready for research & planning

---

## Goal

Final system validation. Verify temporal integrity of the complete system. Compare the optimized strategy (locked from Phases 6-8) against historical top 100 manager performance across all available seasons. Document winning parameters and implementation approach.

---

## Locked Requirements (from ROADMAP)

| Req ID | Requirement |
|--------|-------------|
| PV-01 | Final optimized system compared to top 100 manager historical performance across all 4 seasons |
| PV-02 | Temporal integrity audit passes: no lookahead bias detected in final system |
| PV-03 | Final metrics report generated: all strategy archetypes ranked, 95% CIs reported, per-season results shown |
| PV-04 | Winning strategy parameters documented: transfer frequency, captain rules, chip timing, bench composition, risk settings |

---

## Locked Strategies (from Phases 6-8)

### Transfer Strategy (Phase 6)
- **Optimal:** CONSERVATIVE_FULL
- **Parameters:** transfer_budget_per_gw=0.5, transfer_xp_threshold=0.20
- **Improvement:** +22 points vs baseline
- **Status:** ✅ LOCKED

### Captain Strategy (Phase 7a)
- **Optimal:** CAPTAIN_HIGHEST_VALUE
- **Mechanism:** Prefer high-priced stable players for captaincy
- **Improvement:** +12 points vs baseline (on top of Phase 6)
- **Status:** ✅ LOCKED

### Chip Schedule (Phase 7b)
- **Optimal:** Conservative (no significant improvement from timing strategies)
- **Mechanism:** Use standard FPL chip timing defaults
- **Improvement:** 0 points (conservative baseline)
- **Status:** ✅ LOCKED

### Bench & Substitution (Phase 8)
- **Optimal:** BENCH_SAFE_STATIC
- **Mechanism:** Safe bench composition + static substitution (rotate by lowest predicted xP)
- **Improvement:** 0 points (plateau reached; predictive swaps degrade by -111 pts)
- **Status:** ✅ LOCKED

**Total Optimization:** +34 points cumulative across all phases

---

## Discussion-Driven Decisions

### 1. Data Quality & Validation Seasons

**Decision:** Fix 2024-25 data issues, revalidate Phase 8 on both seasons (2023-24, 2024-25), then proceed with Phase 9.

**Rationale:** Phase 8 validation was limited to 2023-24 only due to squad initialization errors in 2024-25. Single-season validation reduces confidence in results. Full cross-season validation ensures robustness before final Phase 9 validation.

**Action:** 
- Investigate 2024-25 season data initialization error (likely in team.py or predictions/{season}/ directory)
- Re-run Phase 8 walk-forward evaluation on both 2023-24 and 2024-25
- Confirm BENCH_SAFE_STATIC remains optimal across both seasons
- Update Phase 8 results with cross-season metrics before Phase 9 begins

**Impact:** Adds 1-2 hours of investigation + re-validation before Phase 9 execution

---

### 2. Validation Methodology

**Decision:** Comprehensive validation approach with aggregate, per-season, and percentile-ranking comparisons against top 100 managers.

**Rationale:** Phase 9 is the final validation. Comprehensive approach surfaces whether strategy is robust across seasons or only works in specific regimes. Percentile ranking contextualizes performance within the full distribution of historical managers.

**Approach:**

1. **Aggregate Validation (all 4 seasons combined)**
   - Total points scored across 2021-22, 2022-23, 2023-24, 2024-25
   - Compare to top 100 managers' average season total (computed from historical archive)
   - Calculate percentile ranking (e.g., "performs at 73rd percentile")

2. **Per-Season Breakdown**
   - Validate each season independently
   - Track consistency across seasons (does strategy work uniformly or fail in certain years?)
   - Identify regime-specific performance (e.g., strong in 2021-22, weak in 2024-25)

3. **Percentile Ranking**
   - Rank our optimized strategy within full top 100 manager distribution for each season
   - Compare aggregate performance to top 100 aggregate

**Metrics to Include:**
- Total points (primary)
- Sharpe ratio (risk-adjusted return)
- Sortino ratio (downside protection)
- Max drawdown
- Season-by-season consistency score (CV across 4 seasons)

**Success Signal:** Strategy achieves ≥75% of top 100 average (pragmatic threshold; see Gray Area 4)

---

### 3. Temporal Integrity Audit

**Decision:** Automated test suite that simulates Phase 9 validation and detects any future-data access.

**Rationale:** Temporal integrity is critical to backtesting validity. Automated detection provides evidence artifacts for validation report and catches violations deterministically.

**Approach:**

1. **Audit Design**
   - Create test harness that runs final Phase 9 simulation with temporal boundary instrumentation
   - At each gameweek (GW 1 through GW 38), intercept all data access calls
   - Verify that NO future data (GW(i+1) onwards) is accessed during GW(i) decisions
   - Log violations and report as PASS/FAIL

2. **Coverage**
   - Audit all critical decision points:
     - Transfer logic (auto_transfer)
     - Captain selection (auto_captain)
     - Chip usage (auto_chips)
     - Bench initialization (bench composition)
     - Substitution logic (auto_subs)
   - Trace model predictions (confirm predictions use only GW(i-20) through GW(i-1) training data)

3. **Evidence Artifact**
   - Write Phase 9 temporal audit report: PASS/FAIL with specific check list
   - Include sample traces from 3-5 gameweeks showing data access timeline
   - Document any caveats or edge cases discovered

**Success Signal:** Automated audit passes all temporal checks; report generated

---

### 4. Success Criteria

**Decision:** Pragmatic success thresholds. Phase 9 considered complete when:

| Criterion | Threshold | Status |
|-----------|-----------|--------|
| **Performance vs Top 100** | ≥75% of top 100 average across all 4 seasons | Must meet |
| **Temporal Integrity Audit** | Audit attempted (automated test suite run); PASS or documented caveats | Must meet |
| **Requirement Coverage** | 2 of 4 Phase 9 requirements (PV-01 through PV-04) fully met | Must meet |
| **Documentation** | LOCKED_STRATEGIES.md updated with Phase 9 results | Must meet |

**Pragmatic Approach Rationale:**
- Strict thresholds (≥95% of top 100) risk uncompleted phase; pragmatic threshold allows reasonable completion
- Temporal audit is critical (non-negotiable); coverage requirement allows practical effort scoping
- Partial requirement completion acceptable for final phase (Phase 10+ can extend)
- Focus on documenting findings, not perfecting every detail

**If 2024-25 Data Remains Broken:**
- Proceed with 2023-24 validation + 2021-22, 2022-23 historical validation
- Document data quality caveat in final report
- Phase 9 still considered complete if other criteria met

---

### 5. Alternative Optimization Levers

**Decision:** Phase 9 focuses purely on validation. Exploration of alternative optimization levers (fixture weighting, injury prediction, captain-bench co-optimization) deferred to Phase 10+.

**Rationale:** Phase 8 identified bench/substitution as plateau (0 improvement). Phase 6-8 optimization is exhausted. Phase 9 should validate locked strategies, not chase new improvements. Phase 10 can explore new directions with fresh discovery mindset.

**Alternatives Noted for Phase 10:**
- Fixture weighting (weight early-season vs late-season fixtures differently)
- Injury prediction models (earlier injury detection → earlier team adjustments)
- Captain-bench co-optimization (simultaneous selection for captain + bench interaction)
- Squad value metrics (points per million spent — efficiency optimization)

---

### 6. Deliverables & Documentation

**Decision:** Minimal deliverables approach. Focus on core artifacts for internal reference and reproduction.

**Artifacts to Create:**

1. **Update LOCKED_STRATEGIES.md** (existing file, extend current contents)
   - Add Phase 9 validation section with final performance metrics
   - Include per-season breakdown table
   - Document percentile ranking vs top 100 managers
   - Confirm all locked parameters and their contribution (+22 / +12 / 0 / 0 = +34 total)

2. **Phase 9 Validation Summary** (new file: 09-VALIDATION-SUMMARY.md)
   - Brief methodology (what was tested, on which seasons, what metrics)
   - Key findings (aggregate performance, per-season consistency, temporal audit results)
   - Caveats (2024-25 data status, single-season validation if applicable)
   - Recommendation for production deployment

3. **EXECUTION-REPORT.md** (standard phase artifact)
   - Plans executed and their outcomes
   - Metrics produced by walk-forward evaluation
   - Temporal audit report embedded or linked

**No Additional Artifacts:**
- Do NOT create separate implementation runbook (code is self-documenting)
- Do NOT create stakeholder presentation (validation summary sufficient)
- Do NOT create code cleanup checklist (Phase 9 focuses on validation, not refactoring)

---

## Research Priorities

1. **2024-25 Data Issue Investigation:** Root cause of squad initialization error. Likely in:
   - team.py team initialization logic (edge case for 2024-25)
   - predictions/2024-25/ missing or malformed files
   - data/2024-25/ incomplete GW/fixture data

2. **Top 100 Manager Historical Data:** Gather aggregate statistics:
   - Average total points across top 100 managers per season (2021-22 through 2024-25)
   - Distribution (median, 75th percentile, max) for percentile ranking comparison

3. **Temporal Gate Verification:** Confirm Phase 1 TemporalGate implementation:
   - Review fpl_auto/temporal.py for correctness
   - List all data access points in manager.py → team.py → model predictions
   - Document expected available data at each decision point

---

## Code Context & Integration Points

### Phase 5 Walk-Forward Framework (locked, reused in Phase 9)
- **File:** evaluation/walk_forward.py
- **Function:** nested_walk_forward_evaluation(strategy_config)
- **Test seasons:** 2023-24, 2024-25 (primary); 2021-22, 2022-23 (historical context)
- **Output:** Dictionary with total_points, sharpe_ratio, sortino_ratio, drawdown metrics

### Phase 1 Temporal Integrity
- **File:** fpl_auto/temporal.py
- **Class:** TemporalGate
- **Purpose:** Intercept and reject future-data access during model predictions and strategy decisions

### Final Strategy Configuration
- **File:** fpl_auto/strategies.py
- **Config:** PHASE_8_OPTIMAL (StrategyConfig with locked parameters)
- **Parameters:** 
  - transfer_mode='conservative_full', transfer_budget_per_gw=0.5, transfer_xp_threshold=0.20
  - captain_mode='highest_value'
  - chip_schedule='conservative'
  - bench_mode='bench_safe', substitution_mode='static'

### Top 100 Manager Data
- **Source:** Top 100 manager archive (currently in project, exact format TBD by researcher)
- **Usage:** Aggregate statistics for percentile ranking comparison
- **File Location:** TBD (likely data/top_100_managers/ or similar)

---

## Success Criteria (Phase 9 Definition)

Phase 9 will be considered complete when:

1. ✅ **2024-25 Data Fixed** — Squad initialization error resolved; Phase 8 revalidated on both seasons
2. ✅ **Comprehensive Validation** — Phase 9 run on all 4 seasons (or 2023-24 + 2021-22, 2022-23 if 2024-25 broken)
3. ✅ **Validation Report** — Aggregate + per-season + percentile-ranking metrics computed and documented
4. ✅ **Temporal Audit** — Automated test suite executed; PASS or documented caveats
5. ✅ **LOCKED_STRATEGIES.md Updated** — Phase 9 results added to existing file
6. ✅ **Validation Summary Written** — Methodology, findings, caveats documented in 09-VALIDATION-SUMMARY.md
7. ✅ **Performance Threshold Met** — Strategy ≥75% of top 100 average (pragmatic threshold)

---

## Deferred Ideas (Not This Phase)

- Alternative optimization levers (fixture weighting, injury prediction, co-optimization) → Phase 10+
- Code refactoring and cleanup → Post-Phase 9 maintenance
- Real-time FPL integration → Out of scope (offline historical analysis only)
- Multi-season ensemble or consensus strategies → Future research

---

## Canonical References

| Reference | Path | Purpose |
|-----------|------|---------|
| Temporal Integrity Design | fpl_auto/temporal.py | Understand TemporalGate implementation |
| Phase 5 Framework | .planning/phases/05-strategy-framework/05-CONTEXT.md | Walk-forward validation methodology |
| Phase 6-8 Results | .planning/phases/06-transfer-strategy-evaluation/, 07-captain-chip-evaluation/, 08-bench-substitution-evaluation/ | Locked parameters and performance metrics |
| LOCKED_STRATEGIES.md | LOCKED_STRATEGIES.md (root) | Current strategy documentation (to be updated) |
| Top 100 Manager Archive | data/top_100_managers/ (TBD by researcher) | Historical performance for comparison |

---

## Next Steps

1. **Research Phase:** 
   - Investigate 2024-25 data initialization error
   - Gather top 100 manager historical statistics
   - Review TemporalGate implementation for audit scope

2. **Planning Phase:** 
   - Create detailed plan for 2024-25 fix and Phase 8 revalidation
   - Design automated temporal audit test harness
   - Plan walk-forward evaluation for Phase 9 (seasons to include, metrics to compute)

3. **Execution Phase:** 
   - Fix 2024-25, revalidate Phase 8
   - Run automated temporal audit
   - Execute Phase 9 validation on all valid seasons
   - Generate validation report and update LOCKED_STRATEGIES.md

---

*Context captured 2026-05-28 after Phase 9 discussion. Ready for research and planning.*
