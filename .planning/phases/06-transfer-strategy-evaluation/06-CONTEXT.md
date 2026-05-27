# Phase 6: Transfer Strategy Evaluation — Planning Context

**Phase:** 06-transfer-strategy-evaluation  
**Date:** 2026-05-27  
**Depends on:** Phase 5 (Strategy Framework & Evaluation)  
**Status:** Context captured — ready for research & planning

---

## Goal

Evaluate transfer frequency and timing variants using the walk-forward validation framework from Phase 5. Identify which transfer strategies maximize total points while maintaining temporal integrity.

---

## Locked Requirements (from ROADMAP)

| Req ID | Requirement |
|--------|-------------|
| TS-01 | Transfer frequency variants implemented |
| TS-02 | Transfer timing variants implemented |
| TS-03 | All variants tested with walk-forward validation |
| TS-04 | Results compared against baselines (non-overlapping 95% CIs) |

---

## Implementation Decisions

### 1. Transfer Frequency Definition

**Decision:** Points-per-GW budget model  
**Rationale:** More nuanced than fixed counts; allows strategies to vary spending based on gameweek context.

**How to Implement:**
- Conservative variant: Low points-per-GW budget (e.g., ~0.5-1.0 points/GW = ~19-38 total per season)
- Baseline variant: Current auto_transfer logic points-per-GW equivalent
- Aggressive variant: High points-per-GW budget (e.g., ~2.0-3.0 points/GW = ~76-114 total per season)

**Integration Point:** Extend StrategyConfig.transfer_mode to support budget-based decisions in auto_transfer() method.

---

### 2. Transfer Timing Windows

**Decision:** Three fixed gameweek windows  
**Rationale:** Seasonal phases have distinct dynamics (early form uncertainty, mid-season injuries, late consistency).

**Windows:**
- **Early window:** GW 1-10 (squad settling, early form signal weak)
- **Mid window:** GW 11-24 (form established, injuries accumulate)
- **Late window:** GW 25-38 (form crystallized, minimal remaining impact)

**How to Implement:**
- Create separate strategy variants for each window
- Or: Single variant that only permits transfers during its active window
- Track per-window transfer efficiency as diagnostic metric

---

### 3. Decision Rules: xP Improvement Threshold

**Decision:** Use xP improvement threshold to trigger transfers  
**Rationale:** Objective, model-based, consistent with Phase 5 statistical framework.

**Implementation:**
- Transfer target player in if: `xp_in - xp_out > threshold` (e.g., 10-20% improvement)
- Apply to each available transfer within budget window
- Vary threshold by variant (conservative = higher threshold, aggressive = lower)
- Calculate xP using 5-GW rolling average (from Phase 5 framework)

**Decision Rule Formula:**
```
transfer_triggered = (new_player_xp_5gw - current_player_xp_5gw) / current_player_xp_5gw > transfer_threshold
```

---

### 4. Variant Scope: Narrow (3-5 Focused Variants)

**Decision:** Test 3-5 focused variants rather than full grid  
**Rationale:** Faster execution, clearer interpretation, can expand to Phase 6+ if needed.

**Proposed Variant Matrix:**

| Variant | Frequency Budget | Timing | Threshold | Config Name |
|---------|------------------|--------|-----------|-------------|
| 1 | Conservative (0.5 pts/GW) | Early (GW 1-10) | High (20%) | CONSERVATIVE_EARLY |
| 2 | Conservative (0.5 pts/GW) | Full Season | High (20%) | CONSERVATIVE_FULL |
| 3 | Baseline (current equiv.) | Mid (GW 11-24) | Medium (15%) | BASELINE_MID |
| 4 | Aggressive (2.0 pts/GW) | Late (GW 25-38) | Low (10%) | AGGRESSIVE_LATE |
| 5 | Aggressive (2.0 pts/GW) | Full Season | Low (10%) | AGGRESSIVE_FULL |

**Grid:** Covers diagonal from low-risk (conservative + early) to high-risk (aggressive + late). Avoids full 3×3 explosion.

---

## Evaluation Criteria

Each variant will be evaluated against BASELINE_STATIC and BASELINE_CURRENT using Phase 5 framework:

1. **Per-Season Results:** Total points, Sharpe, Sortino, max drawdown
2. **Confidence Intervals:** 95% bootstrapped CIs (Phase 5 metrics.py)
3. **Significance:** Non-overlapping CIs indicate true difference (vs. noise)
4. **Per-Season Breakdown:** Show regime changes (e.g., works 2021-22, fails 2024-25)
5. **Transfer Efficiency Metric** (diagnostic): Average points gained per transfer made

---

## Canonical References

**Phase 5 Framework (locked):**
- `.planning/phases/05-strategy-framework/VERIFICATION.md` — Phase 5 sign-off, framework ready
- `.planning/phases/05-strategy-framework/05-01-PLAN.md` — StrategyConfig structure
- `.planning/phases/05-strategy-framework/05-02-PLAN.md` — Walk-forward validation
- `.planning/phases/05-strategy-framework/05-03-PLAN.md` — Metrics with CIs

**Code Integration Points:**
- `fpl_auto/strategies.py` — Extend StrategyConfig.transfer_mode (or add new transfer_budget param)
- `fpl_auto/team.py` — Modify auto_transfer() to respect budget + window constraints
- `manager.py` — CLI support for strategy variants (already supports --strategy)
- `evaluation/walk_forward.py` — Test new variants using existing nested_walk_forward_evaluation()

**Data & Baselines:**
- `evaluation/baseline_results.json` — Baseline metrics from Phase 5 (BASELINE_STATIC, BASELINE_CURRENT)

---

## Known Constraints

1. **Temporal Integrity:** Transfer decisions must use only data available at each GW (no lookahead). Phase 1 TemporalGate enforces this.

2. **Sample Size:** 4 seasons of data. Walk-forward produces 2 test iterations per variant (test on 2023-24, 2024-25). Small but sufficient for detecting large effects (80+ points/season).

3. **Transfer Cost Model:** Current model assumes infinite budget (no -4 point penalty for transferring out). Phase 6 stays in-scope; deferred: accounting for actual FPL -4 point penalties.

4. **Regime Changes:** FPL rules, player pools, market dynamics change yearly. Strategy optimized for 2021-22 may not generalize to 2024-25. Handled by: per-season breakdown in results.

---

## Deferred Ideas (Not This Phase)

- Multi-objective optimization (Pareto frontier of total points vs. transfer count) — future phase
- Transfer timing using game theory / prediction confidence — future research spike
- Accounting for actual FPL -4 point transfer penalties — clarify with user whether to include
- Real-time transfer suggestions for upcoming season — out of scope (offline analysis only)

---

## Next Steps

1. **Research Phase:** Investigate existing auto_transfer() implementation, identify extension points, confirm xP 5-GW calculation available
2. **Planning Phase:** Create 3-4 detailed plans (architecture, variants, evaluation, testing)
3. **Execution Phase:** Implement variants, run walk-forward, generate results report

---

*Context captured 2026-05-27 after Phase 5 completion. Ready for research and planning.*
