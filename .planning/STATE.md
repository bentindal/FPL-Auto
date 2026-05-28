# PROJECT STATE: FPL-Auto Performance Optimization

**Last Updated:** 2026-05-28  
**Milestone:** Phase 10 In Progress — Live Retraining Pipeline (10-01, 10-02, 10-03, 10-04 COMPLETE)
**Current Phase:** Phase 10 (Model Retraining & Time-Series Optimization) — ✅ 4/5 PLANS EXECUTED
**Production Strategy:** PHASE_8_OPTIMAL (temporal integrity PASS, risk metrics strong, performance 71.7% vs elite managers) + Phase 10 live retraining integration

---

## Project Reference

**Core Value**: Maximize total points the simulated team achieves across historical seasons through better predictions and smarter strategic decisions.

**Current Focus**: Optimizing captain selection and chip usage; next phase targets bench composition and substitution strategy.

**Key Constraints**:
- Temporal Integrity: Models and strategies can only see data available at each gameweek. No lookahead bias.
- Compatibility: Must integrate with existing manager.py, team.py, data pipeline without breaking changes.
- Reproducibility: All results must be reproducible (seeded, deterministic data loading).

---

## Current Position

**Status**: Phase 10 In Progress (4/5 plans complete)
**Phase**: 10 (Model Retraining & Time-Series Optimization) - Execution in progress, 4/5 plans executed
**Last Completed**: Phase 10 Plan 04 Live Retraining Execution (2026-05-28)  
**Next Milestone**: Phase 10 Plan 05 (Airflow deployment + Phase 11 planning)

**Progress**: 
```
Phases 1-9:    ████████████████████ 100% (EXECUTION COMPLETE)
Phase 10 P01:  ████████████████████ 100% (Live data collection)
Phase 10 P02:  ████████████████████ 100% (Ensemble retraining)
Phase 10 P03:  ████████████████████ 100% (Airflow DAG + drift monitoring)
Phase 10 P04:  ████████████████████ 100% (Live testing & validation)
Phase 10 P05:  ░░░░░░░░░░░░░░░░░░░░ 0% (Deployment planning)
```

**Current Phase Status:**
- Phase 5 (Strategy Framework): ✅ COMPLETE
- Phase 6 (Transfer Strategy Evaluation): ✅ COMPLETE
- Phase 7 (Captain & Chip Evaluation): ✅ COMPLETE
- Phase 8 (Bench & Substitution): ✅ COMPLETE
- Phase 9 (Performance Validation): ✅ EXECUTION COMPLETE
- Phase 10 (Model Retraining & Time-Series Optimization): IN PROGRESS (4/5 plans)
  - Plan 01: Live data collection (FPL API + Understat) ✅ COMPLETE (2026-05-26)
  - Plan 02: Ensemble retraining framework (FPLModelRetrainer class) ✅ COMPLETE (2026-05-27)
  - Plan 03: Airflow DAG + drift monitoring ✅ COMPLETE (2026-05-27)
  - Plan 04: Live retraining execution & validation ✅ COMPLETE (2026-05-28)
    - Integration test suite: 10 tests (test_live_retraining.py), all passing
    - Live metrics report: 20 records (5 GW × 4 positions), drift calibration (15% RMSE threshold)
    - Operational runbook: 8 sections (setup, execution, monitoring, alerts, recovery, maintenance, FAQ)
    - Manager.py integration: 3 dedicated tests validating TSV format, 6-GW lookahead, quality metrics
  - Plan 05: Airflow deployment & Phase 11 planning — IN PROGRESS

---

## Roadmap Summary

**Total Phases**: 10 (Phase 11+ planned)
**Completed**: 9 (PHASES 1-9 COMPLETE)  
**In Progress**: Phase 10 (4/5 plans complete)  

| Phase | Name | Status | Key Finding |
|-------|------|--------|---|
| 1 | Temporal Integrity | ✅ Complete | TemporalGate enforces no-lookahead |
| 2 | Model Diagnostics | ✅ Complete | Squad gap analysis completed |
| 3 | Model Infrastructure | ✅ Complete | Pipeline + TimeSeriesSplit established |
| 4 | Feature Engineering | ✅ Complete | 35-50 features, 5% RMSE improvement |
| 5 | Strategy Framework | ✅ Complete | Walk-forward + bootstrap CI framework |
| 6 | Transfer Evaluation | ✅ Complete | CONSERVATIVE_FULL optimal (+22 pts) |
| 7 | Captain & Chip | ✅ Complete | CAPTAIN_HIGHEST_VALUE wins (+12 pts) |
| 8 | Bench & Substitution | ✅ Complete | BENCH_SAFE_STATIC optimal; predictive swaps degrade (-111 pts) |
| 9 | Performance Validation | ✅ Complete | Temporal integrity PASS, metrics comprehensive, performance 71.7% vs elite managers |
| 10 | Model Retraining & Time-Series | 🔄 In Progress (4/5) | Live 2024-25 pipeline: 2-GW retrain schedule, drift detection (15% RMSE), position-specific ensembles |

**Critical Path**: 1 → 2 → 3 → 4 → 5 → {6, 7, 8} → 9 → 10 → {11, 12}

**Phase 10 Status**: 
- ✅ P01: Live data collection (FPL API + Understat)
- ✅ P02: Ensemble retraining (XGBoost + RF per position)
- ✅ P03: Airflow DAG + drift monitoring
- ✅ P04: Live testing & validation (10 tests, metrics calibration, runbook)
- 🔄 P05: Deployment planning (in progress)

---

## Phase 7 Key Results

### Captain Strategy Variants (Phase 7a)
| Variant | Total Points | Improvement | Significant |
|---------|:---:|:---:|:---:|
| CAPTAIN_HIGHEST_VALUE | 1817 | **+12 pts** | ✅ YES |
| CAPTAIN_FORM_BASED | 1808 | +3 pts | ✅ YES |
| CAPTAIN_HIGHEST_XP | 1805 | 0 pts | NO |

**Winner**: CAPTAIN_HIGHEST_VALUE (locked for Phase 8+)

### Chip Timing Variants (Phase 7b)
| Variant | Total Points | Improvement | Significant |
|---------|:---:|:---:|:---:|
| CHIP_DOUBLES_OPTIMIZED | 1805 | 0 pts | NO |
| CHIP_BLANKS_OPTIMIZED | 1805 | 0 pts | NO |
| BASELINE (conservative) | 1805 | — | — |

**Finding**: Chip timing provides marginal impact; conservative schedule continues as baseline.

---

## Optimization Progress

**Performance Attribution by Phase:**

| Strategy Layer | Phase | Improvement | Mechanism | Status |
|---|---|---|---|---|
| Transfer Strategy | 6 | **+22 pts** | Budget 0.5, threshold 0.20 | Locked (CONSERVATIVE_FULL) |
| Captain Strategy | 7 | **+12 pts** | Prefer high-priced stable players | Locked (CAPTAIN_HIGHEST_VALUE) |
| Chip Timing | 7 | 0 pts | Conservative schedule optimal | Locked (conservative) |
| Bench & Subs | 8 | **0 pts** | Static rotation already optimal; predictive swaps degrade | Locked (no change) |

**Total Optimization So Far:** +34 points (all gains locked; bench/subs plateau reached)

**Remaining Optimization Potential:** Phase 9 validation and alternative optimization vectors (e.g., fixture weighting, injury prediction)

---

## Phase 8 Overview

**Goal**: Evaluate bench composition variants and substitution strategies to maximize points from bench players and improve squad flexibility.

**Locked Parameters** (from Phases 5-7):
- Transfer strategy: CONSERVATIVE_FULL
- Captain mode: CAPTAIN_HIGHEST_VALUE
- Chip schedule: conservative

**Expected Variants:**
1. Bench composition: defender-heavy, forward-heavy, balanced
2. Substitution strategy: predictive (use ML to swap early), reactive (wait for points)

**Evaluation Approach**: Walk-forward validation on 2023-24 / 2024-25 split; 95% bootstrapped CIs with Bonferroni correction.

**Estimated Duration**: 2-3 hours (4 plans, 2 waves)

---

## Session Continuity

**Entry Points for Next Phase:**

1. **To plan Phase 8:**
   ```
   /gsd-plan-phase 8
   ```

2. **To execute Phase 8 directly:**
   ```
   /gsd-execute-phase 8
   ```

3. **To review Phase 7 results:**
   - File: `/Users/bentindal/Desktop/coding/FPL-Auto/.planning/phases/07-captain-chip-evaluation/EXECUTION-REPORT.md`
   - Summary: All 4 plans complete, findings documented, Phase 8 ready

4. **To check full roadmap:**
   - File: `/Users/bentindal/Desktop/coding/FPL-Auto/.planning/ROADMAP.md`

---

## Performance Metrics

### Baseline (Phase 5 Strategy Framework)
- Team xP (static squad, no transfers): 1580 pts / season
- Current approach (with transfers): 1783 pts / season (2023-24)

### Phase 6 Transfer Optimization
- CONSERVATIVE_FULL: 1805 pts / season (+22 vs current)

### Phase 7 Captain & Chip Optimization
- CONSERVATIVE_FULL + CAPTAIN_HIGHEST_VALUE: 1817 pts / season (+12 additional)
- Total optimization: **+34 pts vs baseline**

### Phase 8 Target
- Expected improvement: +5 to +15 pts (bench & substitution strategy)
- Projected Phase 8 result: 1822-1832 pts / season

### Phase 9 Validation
- Final performance vs top 100 managers (target: within 10%)

---

## Recent Commits (Phase 9 Execution Complete)

```
6314d5ce docs(09-02): add execution summary for temporal audit harness plan
23ac0bf4 docs(09-08): add plan summary for LOCKED_STRATEGIES.md update
3727f6ac docs(09-08): update LOCKED_STRATEGIES.md with Phase 9 validation results
a774f0d9 docs(09-07): aggregate Phase 9 validation results into comprehensive final report
723d5f71 feat(09-06): compute percentile ranking vs top 100 managers baseline
```

**Phase 9 Progress**: 8 plans executed, 20+ Phase 9 commits total
**All Phases Complete**: 60+ commits total from Phases 1-9

---

## Known Issues & Blockers

| Issue | Severity | Status | Mitigation |
|-------|----------|--------|-----------|
| 2024-25 season data initialization error | MEDIUM | Pre-existing (affects Phases 6-7) | Documented; limited impact on relative comparison |
| Chip timing marginal returns | LOW | Phase 7b finding | Proceed with Phase 8 focus on bench/subs |

---

## Next Steps: Phase 8

**Immediate Next Action**: Run `/gsd-plan-phase 8` to:
1. Define bench composition and substitution variants
2. Create detailed execution plans
3. Estimate resource requirements
4. Identify dependencies and integration points

**Expected Timeline**: Planning phase (1-2 hours) → Execution phase (2-3 hours)

---

---

## Phase 10: Model Retraining & Time-Series Optimization

**Status:** 🔬 RESEARCH COMPLETE (2026-05-28)

**Key Research Findings:**
- Optimal retraining frequency: every 2-4 GWs (not weekly)
- Drift detection: PELT algorithm with 15% RMSE threshold trigger
- Window strategy: Expanding windows (all historical + live) outperform rolling
- Position-specific ensembles: Separate XGBoost + RandomForest per position (GK/DEF/MID/FWD)
- Data collection: Dual-source (FPL API official + Understat xG/xA)
- Orchestration: Apache Airflow (scheduled) + Prefect (drift-driven retrains)

**Research Document:** `.planning/research/10-MODEL-RETRAINING-RESEARCH.md`

**Phase 10 Milestones (Planned):**
- M1: Data collection pipeline + Airflow skeleton
- M2: Model retraining orchestrator + drift detection
- M3: Live testing on 2024-25 + threshold calibration

**Next Steps:** Phase 10 roadmap creation (requirements → phases) in fresh session with full context.

---

*State updated: 2026-05-28*  
*Phase 9 EXECUTION COMPLETE — All 8 plans executed (wave-based parallelization)*  
*PHASE_8_OPTIMAL validation results: mean=1,823 pts, 95% CI=[1,618, 2,035], sharpe=3.035, sortino=5.054*  
*Temporal integrity: PASS (0 violations). Performance: 71.7% vs elite managers (below 75% threshold).*  
*Production recommendation: PHASE_8_OPTIMAL ready for deployment with documented performance caveat.*  
*Phase 10 RESEARCH COMPLETE — Model retraining strategy defined; ready for roadmap creation*
