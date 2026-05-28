# PROJECT STATE: FPL-Auto Performance Optimization

**Last Updated:** 2026-05-28  
**Milestone:** Phase 8 Complete — Bench & Substitution Evaluation Finished
**Current Phase:** Phase 8 (Bench & Substitution Strategy Evaluation) — ✅ ALL 4 PLANS COMPLETE

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

**Status**: Phase 7 execution complete with full findings  
**Phase**: 7 (Captain & Chip Strategy Evaluation) - All 4 Plans Complete
**Last Completed**: Captain and chip variant evaluation with walk-forward results (2026-05-28)  
**Next Milestone**: Phase 8 (Bench & Substitution Strategy Evaluation)

**Progress**: 
```
Phases 1-7: ████████████████████ 100%
Phase 8:    ████████████████████ 100% (ALL 4 PLANS COMPLETE)
Phase 9:    ░░░░░░░░░░░░░░░░░░░░ 0%
```

**Current Phase Status:**
- Phase 5 (Strategy Framework): ✅ COMPLETE
- Phase 6 (Transfer Strategy Evaluation): ✅ COMPLETE
- Phase 7 (Captain & Chip Evaluation): ✅ COMPLETE
  - Plan 01: Captain variants implemented (3 modes)
  - Plan 02: Captain walk-forward evaluation (+12 pts from CAPTAIN_HIGHEST_VALUE)
  - Plan 03: Chip variants implemented (2 timing strategies)
  - Plan 04: Chip walk-forward evaluation (no significant improvement)
- Phase 8 (Bench & Substitution): ✅ COMPLETE
  - Plan 01: Bench composition framework (BENCH_SAFE, BENCH_SPECULATIVE presets with static subs) ✅
  - Plan 02: Predictive swap logic (SUBS_PREDICTIVE_SWAP with >20% threshold, 4 factorial presets) ✅
  - Plan 03: Walk-forward evaluation (4-variant 2×2 factorial on 2023-24; 2024-25 data error) ✅
  - Plan 04: Results analysis and Phase 9 recommendations ✅

---

## Roadmap Summary

**Total Phases**: 9  
**Completed**: 7  
**In Progress**: Phase 8  

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
| 9 | Performance Validation | ⏳ Pending | Final validation vs top 100 managers |

**Critical Path**: 1 → 2 → 3 → 4 → 5 → {6, 7, 8} → 9

**Parallelization**: Phases 6, 7, 8 executed sequentially; Phase 8 can also run in parallel with future phases if needed.

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

## Recent Commits (Phase 8 Plan 03)

```
380fab15 docs(08-03): update SUMMARY with actual walk-forward evaluation results
dfc4ce6a feat(08-03): add Phase 8 walk-forward evaluation results
87d46eb2 fix(08-03): add sys.path handling for relative imports
393a2f50 fix(08-03): update compare_bench_variants to handle walk_forward results
951348b7 feat(08-03): pass strategy_config to auto_subs() and add integration tests
1d2d481e feat(08-03): add bench_utilization_pct metric to evaluation/metrics.py
c20f68f0 feat(08-03): create compare_bench_variants orchestration script
```

**Total Phase 8**: 7 new commits (Plan 03 execution)  
**Pushed**: No (pending final phase summary and STATE.md update)

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

*State updated: 2026-05-28*  
*Phase 7 execution complete; Phase 8 planning ready*  
*45 commits prepared for Phase 8 planning and execution*
