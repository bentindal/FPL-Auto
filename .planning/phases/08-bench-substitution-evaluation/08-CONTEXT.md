# Phase 8: Bench & Substitution Strategy Evaluation — Planning Context

**Phase:** 08-bench-substitution-evaluation  
**Date:** 2026-05-28  
**Depends on:** Phase 5 (Strategy Framework & Evaluation)  
**Status:** Context captured — ready for research & planning

---

## Goal

Evaluate bench composition and substitution logic variants using the walk-forward validation framework from Phase 5. Identify which bench strategies and substitution rules maximize total points while maintaining squad flexibility and temporal integrity.

---

## Locked Requirements (from ROADMAP)

| Req ID | Requirement |
|--------|-------------|
| BS-01 | Bench composition variants implemented |
| BS-02 | Substitution logic variants implemented |
| BS-03 | All variants tested with walk-forward validation |
| BS-04 | Results compared against baselines (non-overlapping 95% CIs) |

---

## Phase 7 Locked Results

**Transfer Strategy (Phase 6):**
- Optimal: CONSERVATIVE_FULL (transfer_budget_per_gw=0.5, transfer_xp_threshold=0.20)
- Improvement: +22 points vs baseline

**Captain Strategy (Phase 7a):**
- Optimal: CAPTAIN_HIGHEST_VALUE (prefer high-priced stable players)
- Improvement: +12 points vs baseline

**Chip Schedule (Phase 7b):**
- Optimal: conservative (no significant improvement from timing strategies)
- Improvement: 0 points (baseline)

**Phase 8 will build on these locked parameters.**

---

## Research Questions

Before planning, answer these questions to define Phase 8 scope:

### 1. Bench Composition Variants

**Question 1a:** What are the main bench composition philosophies in FPL?
- **Options:**
  1. Safe bench (defensive focus) — minimize risk, prioritize injury coverage
  2. Speculative bench (high-upside) — chase point upside with less-established players
  3. Balanced bench (mixed) — split between safety and upside
  4. Role-based bench (complement starting XI) — fill gaps in starting lineup

**Question 1b:** For each variant, what metrics matter?
- Total bench xP across season
- Bench utilization (how often bench players play)
- Squad depth (flexibility to cover injuries)
- Opportunity cost (capital tied up in underused bench players)

### 2. Substitution Logic Variants

**Question 2a:** When and why would we substitute bench players in?
- **Triggers:**
  1. Predictive (ML-driven) — predict starter underperformance, swap early
  2. Reactive (rules-based) — swap after observing starter points/performance
  3. Defensive (injury response) — swap only on confirmed injury
  4. Opportunistic (upside chase) — swap to bench player with higher xP projection

**Question 2b:** How does substitution timing affect points?
- Early swap (GW1-GW5) — more time for bench player to accumulate points
- Mid-season swap (GW15-GW25) — wait for injury confirmation or clear underperformance
- Late-season swap (GW30+) — minimal impact on total season points

### 3. Integration with Phase 7 Results

**Question 3a:** How do bench composition and substitution strategies interact with captain selection?
- Example: If captain_mode='highest_value' (prefer expensive players), does bench composition follow same principle or differ?
- Example: Can substitution rules exploit captain volatility (swap out captain-eligible player if unlikely captain pick)?

**Question 3b:** Should bench variants be independent or nested under captain variants?
- Option A: Test all bench variants with fixed captain_mode='highest_value'
- Option B: Test bench variants across multiple captain modes (factorial design)

### 4. Evaluation Scope & Structure

**Question 4a:** How many bench composition and substitution variants should we test?
- Recommendation: 2-3 bench variants (safe, balanced, speculative) + 2-3 substitution variants (predictive, reactive, defensive)
- This matches Phase 6-7 pattern (5 transfer variants, 3 captain + 2 chip)

**Question 4b:** Should bench composition and substitution be separate phases or combined?
- Option A: Separate (Phase 8a = bench, Phase 8b = substitution)
- Option B: Combined (4-6 nested variants tested together)

---

## Known Context

### Current Manager.py Implementation

**Bench initialization:**
- `team.py` has `get_bench_players()` — returns players not in starting XI
- No explicit bench composition strategy (current: just select cheapest valid players)
- Bench players are used for `auto_subs()` when starters have injuries/blanks

**Substitution logic:**
- `auto_subs()` method in team.py (line ~480)
- Current logic: swap starter if bench player has better projected xP (single-GW lookahead)
- Issues: no temporal integrity check, may access GW(i) data when predicting GW(i) starter performance

### Phase 5 Framework (locked)

**From evaluation/walk_forward.py:**
- `nested_walk_forward_evaluation(strategy_config)` — handles walk-forward logic
- `train_seasons = [2021-22, 2022-23]`, `test_seasons = [2023-24, 2024-25]`
- Returns 2 test iterations with metrics (total_points, sharpe, sortino, etc.)

**From evaluation/metrics.py:**
- `bootstrap_ci()` — computes 95% CIs via 10,000 bootstrap iterations
- `apply_bonferroni_correction()` — adjusts α for multiple comparisons

**From fpl_auto/strategies.py:**
- `StrategyConfig` dataclass with ~15 parameters
- Existing presets: CONSERVATIVE_FULL (Phase 6), CAPTAIN_HIGHEST_VALUE (Phase 7)
- New Phase 8 presets will add bench_mode, substitution_mode parameters

---

## Candidate Bench Variants

### Bench Composition Variants

| Variant | Philosophy | Key Decision | Budget Strategy |
|---------|-----------|--------------|---|
| BENCH_SAFE | Defensive | Prefer injury-cover + experience | Standard (min price) |
| BENCH_SPECULATIVE | High-upside | Chase differential players | Weighted (spend on high-variance) |
| BENCH_BALANCED | Mixed | Split between safety and upside | Balanced allocation |

### Substitution Logic Variants

| Variant | Trigger | Timing | Condition |
|---------|---------|--------|-----------|
| SUBS_PREDICTIVE | ML-driven | Early (GW1-5) | xP prediction > starter xP |
| SUBS_REACTIVE | Rules-based | Mid (GW10-25) | Observed underperformance |
| SUBS_DEFENSIVE | Injury response | Whenever | Starter unavailable |

---

## Research Priorities

1. **Literature review:** How do successful FPL managers structure benches? What's the empirical edge?
2. **Data analysis:** How often do bench players score more points than starters? By position?
3. **Substitution patterns:** In historical data (2021-24), when would a rules-based substitution policy trigger? What's the impact?
4. **Integration with Phase 7:** Do captain_mode choices constrain bench composition? (e.g., if captain='highest_value', should bench also be conservative?)

---

## Success Criteria (Phase 8 Definition)

Phase 8 will be considered complete when:

1. ✅ **Bench composition variants** — At least 2 variants implemented in team.py with configurable logic
2. ✅ **Substitution logic variants** — At least 2 variants implemented in auto_subs() with temporal integrity
3. ✅ **Walk-forward evaluation** — All variants tested on 2023-24 / 2024-25 split with 95% CIs
4. ✅ **Baseline comparison** — Non-overlapping CIs indicate statistical significance (or lack thereof)
5. ✅ **Cross-phase integration** — Phase 8 variants inherit Phase 6-7 locked parameters (transfer + captain)
6. ✅ **Documentation** — Results summary with per-season breakdown, recommendations for Phase 9

---

## Deferred Ideas (Not This Phase)

- Dynamic bench allocation based on injury predictions (ML model) — future research
- Real-time captaincy + bench co-optimization (simultaneous optimization) — future phase
- Squad value metrics (ROI, return per million spent) — future analysis
- Bench variance analysis (replicate top 100 manager benches) — future research

---

## Next Steps

1. **Research Phase:** Investigate current auto_subs() implementation, bench composition patterns in FPL, substitution heuristics
2. **Planning Phase:** Create detailed plans for Phase 8a (bench composition) and Phase 8b (substitution variants)
3. **Execution Phase:** Implement variants, run walk-forward, generate results report

---

*Context captured 2026-05-28 after Phase 7 completion. Ready for research and planning.*
