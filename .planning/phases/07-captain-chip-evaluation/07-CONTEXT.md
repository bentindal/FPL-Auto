# Phase 7: Captain & Chip Strategy Evaluation — Planning Context

**Phase:** 07-captain-chip-evaluation  
**Date:** 2026-05-28  
**Depends on:** Phase 5 (Strategy Framework & Evaluation)  
**Status:** Context captured — ready for research & planning

---

## Goal

Evaluate captain selection and chip usage variants using the walk-forward validation framework from Phase 5. Identify which captain strategies and chip schedules maximize total points while maintaining temporal integrity.

---

## Locked Requirements (from ROADMAP)

| Req ID | Requirement |
|--------|-------------|
| CS-01 | Captain selection variants implemented |
| CS-02 | Chip usage schedules implemented |
| CS-03 | All variants tested with walk-forward validation |
| CS-04 | Results compared against baselines (non-overlapping 95% CIs) |

---

## Implementation Decisions

### 1. Captain Strategy Variants

**Decision:** Test 3 captain modes with fixed parameters  
**Rationale:** Consistent with Phase 6 approach (5 focused variants); captures diversity of captain philosophies without factorial explosion.

**Three Variants:**

| Variant | Mode | Parameters | Rationale |
|---------|------|------------|-----------|
| CAPTAIN_HIGHEST_XP | highest_xp | captain_lookback_gws=1, variance_penalty=0.0 | Baseline: always pick highest expected points |
| CAPTAIN_FORM_BASED | form_based | captain_lookback_gws=3, variance_penalty=-0.2 | Contrarian: favor recent hot streaks, prefer volatile players |
| CAPTAIN_HIGHEST_VALUE | highest_value | captain_lookback_gws=1, variance_penalty=0.0 | Defensive: pick high-priced players (stable, reliable) |

**Implementation Notes:**
- All three variants implemented as StrategyConfig presets (analogous to Phase 6 CONSERVATIVE_FULL, etc.)
- `suggest_captaincy()` in team.py must be extended to support all three modes (currently only implements highest_xp)
- Form-based captain needs both xP-based and points-based implementations (see decision #2)

---

### 2. Form-Based Captain Definition

**Decision:** Implement both xP-based (primary) and points-based (diagnostic) metrics  
**Rationale:** xP-based is consistent with Phase 5 framework; points-based provides historical validation signal.

**Implementation:**

- **xP-based form (primary):**
  - Use 5-GW rolling average of discounted xP (from Phase 5 `discount_next_n_gws(n=5, factor=0.8)`)
  - Reuses existing `_all_xp_dicts` infrastructure
  - Captain selected as: highest rolling xP in most recent 3 GWs, penalized by variance (variance_penalty=-0.2)
  
- **Points-based form (diagnostic):**
  - Calculate recent points scored: sum of actual points in last 3 GWs
  - Used only for diagnostics in results report (not for decision-making)
  - Validates whether form-based captain correlates with historical performance

**Why both?**
- xP-based is model-dependent and forward-looking (respects temporal integrity)
- Points-based is backward-looking (answers: "in hindsight, who was hot?")
- Comparing both reveals if form signal is real or just noise

---

### 3. Chip Usage Variants

**Decision:** Test TWO chip timing strategies, separated from captain variants  
**Rationale:** Clearer attribution of impact; captain and chip effects on total points can be quantified independently.

**Two Variants:**

| Variant | Strategy | Timing | Condition | Rationale |
|---------|----------|--------|-----------|-----------|
| CHIP_DOUBLES_OPTIMIZED | Maximize during doubles | Use chips around DOUBLE gameweeks (e.g., GW10, GW33) | xP gain >= threshold (e.g., 8 points) | Leverage player playing twice |
| CHIP_BLANKS_OPTIMIZED | Hedge during blanks | Use chips around BLANK gameweeks (e.g., GW6, GW28) | xP gain >= threshold (e.g., 8 points) | Compensate for squad sitting out |

**Implementation Details:**

- **Detection:** Identify blank and double gameweeks from fixture data (already available in data pipeline)
- **Timing windows:**
  - CHIP_DOUBLES_OPTIMIZED: Activate chips GW-1 before and during identified double GWs
  - CHIP_BLANKS_OPTIMIZED: Activate chips GW-1 before and after identified blank GWs
  
- **Condition logic (hybrid approach):**
  - Triple Captain: Use if (in timing window) AND (expected xP gain from captain > 8)
  - Wildcard: Use if (current squad xP < optimal squad xP - wildcard_threshold=60) OR (blank GW approaching and squad has 3+ blanked players)
  - Bench Boost: Use if (bench xP > 4) AND (in timing window)
  - Free Hit: Reserved for emergency (large blank GW with many blanked squad members)

- **Chip budget:** chip_budget_limit=3 (use all available chips across season)

---

### 4. Evaluation Scope & Structure

**Decision:** Two-phase evaluation structure (Phase 7a = Captain, Phase 7b = Chips)  
**Rationale:** Separates concerns; allows independent assessment of each strategy component.

**Phase 7a: Captain Strategy Evaluation**
- Test 3 captain variants
- Lock chip_schedule='conservative' (baseline from Phase 6)
- Run walk-forward validation (train on 2-3 seasons, test on 2023-24, 2024-25)
- Compute 95% CIs for total_points, sharpe, sortino, max_drawdown
- Measure: which captain mode produces highest total points?

**Phase 7b: Chip Strategy Evaluation** (follows Phase 7a)
- Test 2 chip variants (doubles-optimized, blanks-optimized)
- Lock captain_mode='highest_xp' (baseline)
- Run walk-forward validation (same train/test split as 7a)
- Compute 95% CIs for all metrics
- Measure: does chip timing matter? Which timing is superior?

---

### 5. Integration with Phase 6 Results

**Decision:** Build on CONSERVATIVE_FULL as the transfer baseline  
**Rationale:** Phase 6 identified CONSERVATIVE_FULL as optimal; Phase 7 variants will test captain/chip improvements ON TOP OF this transfer strategy.

**StrategyConfig inheritance:**
- All Phase 7 variants inherit transfer parameters from CONSERVATIVE_FULL:
  - transfer_budget_per_gw=0.5
  - transfer_window_gw_range=None (full season)
  - transfer_xp_threshold=0.20
  
- Only captain_mode, captain_lookback_gws, captain_variance_penalty, chip_schedule, wildcard_threshold_points vary

---

## Variant Matrix Summary

**Phase 7a (Captain, n=3):**
| Variant | Captain Mode | Lookback | Variance Penalty | Transfer Base | Chip Schedule |
|---------|--------------|----------|------------------|---------------|----|
| CAPTAIN_HIGHEST_XP | highest_xp | 1 | 0.0 | CONSERVATIVE_FULL | conservative |
| CAPTAIN_FORM_BASED | form_based | 3 | -0.2 | CONSERVATIVE_FULL | conservative |
| CAPTAIN_HIGHEST_VALUE | highest_value | 1 | 0.0 | CONSERVATIVE_FULL | conservative |

**Phase 7b (Chips, n=2):**
| Variant | Chip Schedule | Double GW Logic | Blank GW Logic | Transfer Base | Captain Mode |
|---------|---------------|-----------------|-----------------|---------------|----|
| CHIP_DOUBLES_OPTIMIZED | doubles-optimized | Use chips before/during doubles | Standard thresholds | CONSERVATIVE_FULL | highest_xp |
| CHIP_BLANKS_OPTIMIZED | blanks-optimized | Standard thresholds | Use chips before/after blanks | CONSERVATIVE_FULL | highest_xp |

---

## Evaluation Criteria

Each variant will be evaluated against BASELINE_CURRENT (now set to CONSERVATIVE_FULL from Phase 6) using Phase 5 framework:

1. **Per-Season Results:** Total points, Sharpe, Sortino, max drawdown
2. **Confidence Intervals:** 95% bootstrapped CIs (Phase 5 metrics.py)
3. **Significance:** Non-overlapping CIs indicate true difference (vs. noise)
4. **Per-Season Breakdown:** Show regime changes (e.g., works 2023-24, fails 2024-25)
5. **Diagnostic Metrics:**
   - For captain variants: Captain selection consistency (how often each mode differs?)
   - For chip variants: Chip usage count and timing (when were chips deployed?)
   - For form-based: xP-based vs points-based form correlation

---

## Canonical References

**Phase 5 Framework (locked):**
- `evaluation/walk_forward.py` — nested_walk_forward_evaluation() function
- `fpl_auto/evaluate.py` — bootstrap_ci() for 95% CIs
- `fpl_auto/strategies.py` — StrategyConfig structure, CONSERVATIVE_FULL baseline

**Phase 6 Results (locked):**
- `evaluation/all_seasons_results.json` — Per-season performance (2021-22, 2022-23, 2023-24)
- `.planning/phases/06-transfer-strategy-evaluation/RESULTS.md` — Transfer strategy findings
- BASELINE_CURRENT now set to CONSERVATIVE_FULL parameters

**Code Integration Points:**
- `fpl_auto/team.py:suggest_captaincy()` — Extend to support all 3 captain modes
- `fpl_auto/team.py:auto_captain()` — Call suggest_captaincy() with strategy_config param
- `fpl_auto/team.py:auto_chips()` — Extend to support blank/double GW timing
- `fpl_auto/strategies.py` — Add CAPTAIN_* and CHIP_* variant presets
- `manager.py` — CLI support for strategy variants (already supports --strategy)
- `evaluation/eval_all_seasons.py` (Phase 6) — Extend for Phase 7a and Phase 7b

**Data & Fixtures:**
- Fixture data already contains blank GW and double GW information
- `data/{season}/fixtures.csv` — source of blank/double GW info per season

---

## Known Constraints

1. **Temporal Integrity:** Captain and chip decisions must use only data available at each GW (no lookahead). Phase 1 TemporalGate enforces this.

2. **Sample Size:** 4 seasons of data. Walk-forward produces 2 test iterations per variant (test on 2023-24, 2024-25). Small but sufficient for detecting large effects (80+ points/season).

3. **Form-based Captain:** Requires computing rolling form; must use only GW(i-1) data when making GW(i) decision.

4. **Chip Timing:** Blank and double GW definitions may vary year-to-year (fixture changes, rule changes). Must be season-specific.

---

## Deferred Ideas (Not This Phase)

- Multi-objective optimization (Pareto frontier of total points vs captain volatility) — future phase
- Adaptive chip scheduling (ML model to predict best chip timing) — future research spike
- Captain selection using market ownership (contrarian against crowd) — requires external data (not available)
- Real-time captain captaincy suggestions — out of scope (offline analysis only)

---

## Next Steps

1. **Research Phase:** Investigate current auto_captain() and auto_chips() implementation, blank/double GW data availability, integration points
2. **Planning Phase:** Create detailed plans for Phase 7a (captain variants) and Phase 7b (chip variants)
3. **Execution Phase:** Implement variants, run walk-forward, generate results report

---

*Context captured 2026-05-28 after Phase 6 completion. Ready for research and planning.*
