# Locked Strategies — Phase 6-8 Optimal Configuration

**Date Locked:** 2026-05-28  
**Validation:** Multi-season cross-validation (2021-22, 2022-23, 2023-24)  
**Confidence Level:** VERY HIGH

---

## PHASE_8_OPTIMAL Strategy (Production)

Combines all Phase 6-8 optimization findings into a single locked strategy for Phase 9 validation.

**Configuration:**

| Dimension | Parameter | Value | Phase | Validation |
|-----------|-----------|-------|-------|-----------|
| **Transfer** | Mode | flexible | 6 | +22 pts improvement |
| | Budget | 0.5 GW | 6 | CONSERVATIVE_FULL optimal |
| | Threshold | 20% relative | 6 | Consistent across seasons |
| | Window | Full season | 6 | Critical parameter |
| **Captain** | Mode | highest_value | 7 | +12 pts improvement |
| | Lookback | 1 GW | 7 | Best recent-form capture |
| | Variance penalty | 0.0 | 7 | No contrarian penalty |
| **Bench** | Composition | safe | 8 | 0 pt difference (vs speculative) |
| | Substitution | static | 8 | Optimal; predictive -111 pts |
| | Trigger threshold | 0.20 | 8 | Unused (static mode) |
| **Chips** | Schedule | conservative | 7 | Minimal value added |
| | Budget | 3 (all) | 7 | Preserve for defense |

**Multi-Season Results:**

| Season | PHASE_8_OPTIMAL | vs Baseline | Stability |
|--------|---|---|---|
| 2021-22 | 1618 pts | Match optimal | ✅ |
| 2022-23 | 2035 pts | Match optimal | ✅ |
| 2023-24 | 1817 pts | Match optimal | ✅ |
| **Mean** | **1823** | **+34 pts** | **Very stable** |

---

## Key Locked Decisions

### Phase 6: Transfer Strategy (CONSERVATIVE_FULL)
- **Finding:** Budget 0.5 with 20% threshold superior to all alternatives
- **Improvement:** +22 points vs baseline
- **Mechanism:** Conservative capital allocation with high improvement bar prevents churn
- **Status:** ✅ LOCKED for Phase 9

### Phase 7: Captain Strategy (CAPTAIN_HIGHEST_VALUE)
- **Finding:** High-priced players outperform xP-based captaincy
- **Improvement:** +12 points vs highest_xp baseline
- **Mechanism:** Model predictions more reliable for elite players; premium players more consistent
- **Status:** ✅ LOCKED for Phase 9

### Phase 8: Bench Strategy (BENCH_SAFE_STATIC)
- **Finding:** Bench composition has zero impact; static rotation optimal
- **Improvement:** +0 pts (neutral); prevents performance degradation
- **Mechanism:** Predictive swap mode removes captain candidates (-27 to -111 pts); composition irrelevant
- **Status:** ✅ LOCKED for Phase 9

---

## Deprecated Strategies

These variants tested in Phases 6-8 are **NOT RECOMMENDED** for production:

| Variant | Reason | Penalty |
|---------|--------|---------|
| BENCH_SAFE_PREDICTIVE | Predictive swaps degrade performance | -27 to -111 pts |
| BENCH_SPECULATIVE_STATIC | Composition has zero impact; adds variance | -0 to -5 pts |
| BENCH_SPECULATIVE_PREDICTIVE | Both effects degrade | -27 to -111 pts |
| CHIP_DOUBLES_OPTIMIZED | Minimal value from chips | -2 to -5 pts |
| CHIP_BLANKS_OPTIMIZED | Minimal value from chips | -2 to -5 pts |
| CAPTAIN_HIGHEST_XP | Underperforms highest_value | -12 pts |
| CAPTAIN_FORM_BASED | Underperforms highest_value | -20+ pts |

---

## Testing PHASE_8_OPTIMAL

Run Phase 8 optimal strategy on any season:

```bash
python manager.py -season 2023-24 -strategy phase_8_optimal
python manager.py -seasons 2021-22 2022-23 2023-24 -strategy phase_8_optimal
```

Expected results: ~1600-2100 points depending on season (variance from fixture difficulty and team form).

---

## Ready for Phase 9: Performance Validation

PHASE_8_OPTIMAL is ready for final system validation against:
- Top 100 real FPL managers (benchmarking)
- Alternative optimization levers (fixture weighting, injury prediction)
- Ensemble combinations (PHASE_8_OPTIMAL + alternative)

**Next:** Implement Phase 9 final validation framework.
