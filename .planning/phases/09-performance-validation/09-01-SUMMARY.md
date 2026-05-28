---
phase: 09-performance-validation
plan: 01
subsystem: data-validation
tags: [data-quality, root-cause-analysis, walk-forward-validation, gameweek-data]

requires:
  - phase: 08-bench-substitution-evaluation
    provides: PHASE_8_OPTIMAL strategy config and Phase 8 validation results

provides:
  - Root cause analysis of 2024-25 data initialization error
  - Decision to skip 2024-25 cross-season validation
  - Phase 9 scope adjustment (2023-24-only validation with caveat)
  - Unblocked path to Phase 9 execution

affects:
  - Phase 9 Plans 02-03 (adjusted scope to 2023-24-only)
  - Phase 9 final validation report (caveat documentation)

tech-stack:
  added: []
  patterns:
    - Root cause investigation via code tracing and data structure inspection
    - Pragmatic decision framework for external data dependency failures

key-files:
  created:
    - .planning/phases/09-performance-validation/09-DATA-INVESTIGATION.md
  modified: []

key-decisions:
  - "Incomplete 2024-25 historical gameweek data (only GW1-GW4 available) blocks cross-season validation"
  - "Skip 2024-25 validation and proceed with 2023-24-only Phase 9 per CONTEXT.md pragmatic criteria"
  - "Phase 8 revalidation unnecessary; results already locked and validated"

requirements-completed:
  - PV-01 (partial context for Phase 9)
  - PV-02 (temporal audit scope adjusted to 2023-24)

duration: 35min
completed: 2026-05-28
---

# Phase 9 Plan 01: 2024-25 Data Investigation Summary

**Root cause identified and decision made: skip 2024-25 cross-season validation due to incomplete historical gameweek data; proceed with 2023-24-only Phase 9 validation with documented caveat**

## Performance

- **Duration:** 35 min
- **Started:** 2026-05-28 14:00 UTC
- **Completed:** 2026-05-28 14:35 UTC
- **Tasks:** 2
- **Files modified:** 1 created

## Accomplishments

- **Root Cause Identified:** "Squad has no GK available for bench selection" error traced to empty gameweek data at GW5+
  - Historical GW CSV files exist only for GW1-GW4 in data/2024-25/gws/
  - Any team initialization beyond GW4 attempts to load empty DataFrame
  - Player lookups fail in transfer_in_allowed(), preventing squad building
  
- **Data Structure Analysis:** Verified predictions exist (GW1-GW8 position TSVs complete) but historical GW data incomplete
  - Predictions are pre-trained model outputs (not affected by season incompleteness)
  - Historical GWs are external data source (vaastav/FPL or manual collection) - incomplete for 2024-25
  
- **Decision Implemented:** Skip 2024-25 cross-season validation
  - Rationale: External data dependency (not project-controlled), cannot be fixed via code/regeneration
  - Phase 9 scope adjusted to 2023-24 walk-forward with caveat documentation
  - Aligns with CONTEXT.md pragmatic criteria: "If 2024-25 Data Remains Broken, proceed with 2023-24-only validation"
  
- **Path Unblocked:** Phase 9 execution can now proceed without waiting for external data

## Task Commits

1. **Task 1: Root Cause Investigation** - `d9570591` (docs)
   - Diagnosed error location: team.py:270, trigger at GW5 Free Hit initialization
   - Traced causal chain: missing GW5 data → empty DataFrame → failed player lookups → empty squad
   - Verified via code inspection and data structure checks

2. **Task 2: Decision and Caveat** - `e2161d4d` (docs)
   - Documented final decision: skip 2024-25, proceed with 2023-24-only
   - Added timestamp and implementation status to 09-DATA-INVESTIGATION.md
   - Rationale: external data dependency with timeline risk; Phase 9 pragmatic criteria allow fallback

**Plan metadata:** `e2161d4d` (Task 2 commit includes decision documentation)

## Files Created/Modified

- `.planning/phases/09-performance-validation/09-DATA-INVESTIGATION.md` (created, 164 lines)
  - Complete root cause analysis with causal chain
  - Effort estimates for fix options
  - Final decision with timestamp and rationale
  - Impact assessment on Phase 9 execution

## Decisions Made

1. **Skip 2024-25 Data Fix:** External data dependency (not project-controlled)
   - Rationale: Would require gathering/downloading complete season data from external source
   - Risk: Introduces unknown timeline dependency on data source refresh
   - Mitigation: CONTEXT.md explicitly allows 2023-24-only validation with caveat

2. **Proceed Immediately with Phase 9:** No Phase 8 revalidation needed
   - Phase 8 results already validated on 2023-24 (BENCH_SAFE_STATIC locked as optimal)
   - Cross-season robustness desirable but not critical per pragmatic success criteria
   - Single-season validation acceptable for Phase 9 completion

## Deviations from Plan

None - plan executed exactly as written. Both tasks completed autonomously without deviation rule invocations:
- Task 1 (investigate) completed with root cause identified
- Task 2 (decide) completed with pragmatic decision aligned to CONTEXT.md

## Issues Encountered

None - investigation proceeded smoothly with data available for inspection and analysis.

## Next Phase Readiness

**Phase 9 is unblocked and ready to execute:**
- Walk-forward validation framework (Phase 5) reusable for 2023-24 test season
- Temporal audit scope confirmed for 2023-24 data
- Top 100 manager comparison will use 2023-24 baseline
- Caveat about 2024-25 unavailability will be documented in final Phase 9 report

**Phase 9 Plans 02-03** should adjust scope to:
- Test season: 2023-24 (held-out walk-forward)
- Training seasons: 2021-22, 2022-23
- Historical context: 2019-20 top 100 managers data
- Caveat: 2024-25 cross-season validation deferred due to incomplete gameweek data

---

*Phase: 09-performance-validation*  
*Plan: 01*  
*Completed: 2026-05-28*
