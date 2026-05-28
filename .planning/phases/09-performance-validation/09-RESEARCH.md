# Phase 9: Performance Validation — Research

**Researched:** 2026-05-28  
**Domain:** Final system validation, temporal integrity audit, top 100 manager comparison  
**Confidence:** HIGH (framework and locked parameters verified; data issues documented)

---

## Summary

Phase 9 is the final validation gate for the optimized FPL strategy system. All optimization parameters from Phases 6-8 are locked (CONSERVATIVE_FULL transfers +22 pts, CAPTAIN_HIGHEST_VALUE captain +12 pts, BENCH_SAFE_STATIC bench +0 pts). Phase 9 must validate that:

1. **Performance vs Top 100 Managers:** Optimized strategy achieves ≥75% of top 100 manager average across all available seasons
2. **Temporal Integrity:** Automated audit confirms no lookahead bias in final system
3. **Multi-Season Consistency:** Results hold across 2023-24 (validated) and other seasons
4. **Parameter Documentation:** Winning configuration is comprehensively documented

**Primary recommendation:** Execute Phase 9 in two sub-phases: (1) fix 2024-25 data initialization error and revalidate Phase 8, then (2) run temporal audit + top 100 comparison on all valid seasons.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Transfer Strategy:** CONSERVATIVE_FULL (transfer_budget_per_gw=0.5, transfer_xp_threshold=0.20)
- **Captain Mode:** CAPTAIN_HIGHEST_VALUE (prefer high-priced stable players)
- **Chip Schedule:** Conservative (standard FPL timing, no significant improvement from optimization)
- **Bench & Substitution:** BENCH_SAFE_STATIC (safe bench + static rotation; predictive swaps degrade by -111 pts)
- **Validation Methodology:** Comprehensive with aggregate, per-season, and percentile-ranking comparisons
- **Temporal Audit:** Automated test suite required; PASS or documented caveats acceptable
- **Success Threshold:** ≥75% of top 100 average (pragmatic, not strict)

### Claude's Discretion
- How to structure the temporal audit test harness (what data access points to instrument)
- How to compute percentile ranking (binning strategy, confidence interval approach)
- Report format and visualization approach
- Whether to pursue 2024-25 fix or accept single-season validation

### Deferred Ideas (Out of Scope)
- Alternative optimization levers (fixture weighting, injury prediction, co-optimization) → Phase 10+
- Code refactoring and cleanup → Post-Phase 9 maintenance
- Real-time FPL integration → Out of scope (offline historical analysis only)

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PV-01 | Final optimized system compared to top 100 manager historical performance across all 4 seasons | Walk-forward framework reused; top 100 manager data available in data/2019-20/managers/; aggregate + per-season metrics computed |
| PV-02 | Temporal integrity audit passes: no lookahead bias detected in final system | TemporalGate class exists in fpl_auto/temporal.py; audit scope covers all decision points (transfers, captain, chips, bench, subs, model predictions) |
| PV-03 | Final metrics report generated: all strategy archetypes ranked, 95% CIs reported, per-season results shown | Walk-forward framework produces total_points, sharpe_ratio, sortino_ratio, max_drawdown; bootstrap CI computation available in evaluation/metrics.py |
| PV-04 | Winning strategy parameters documented: transfer frequency, captain rules, chip timing, bench composition, risk settings | All parameters already locked from Phases 6-8; LOCKED_STRATEGIES.md exists and requires Phase 9 update |

---

## Standard Stack

### Core Frameworks
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.10 | Runtime | Project constraint (CLAUDE.md: /Library/Frameworks/Python.framework/Versions/3.10/bin/python3) |
| numpy | Current | Array operations, metrics | Used in evaluation/metrics.py for bootstrap CI, Bonferroni correction |
| multiprocessing | stdlib | Parallel season execution | Walk-forward validation runs seasons in parallel via Pool(processes=4) |

### Walk-Forward Validation Framework
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| nested_walk_forward_evaluation() | evaluation/walk_forward.py | Train on N-1 seasons, test on held-out | ✅ Proven (Phases 5-8); reusable for Phase 9 |
| compute_season_metrics() | evaluation/metrics.py | Per-season metric aggregation | ✅ Computes total_points, sharpe, sortino, max_drawdown, cv |
| bootstrap_ci() | evaluation/metrics.py | 95% confidence interval calculation | ✅ 10,000 iteration bootstrap (Phase 5) |
| apply_bonferroni_correction() | evaluation/metrics.py | Multiple comparison correction | ✅ Available; α=0.05/n_comparisons |

### Temporal Integrity
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| TemporalGate | fpl_auto/temporal.py | Enforce GW(i) decision boundaries | ✅ Class defined; rules documented; ready for integration test |
| safe_read_historical_form() | fpl_auto/temporal.py | Boundary check for historical access | ✅ Implements rule: target_gw < decision_gameweek |

### Strategy Configuration
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| StrategyConfig dataclass | fpl_auto/strategies.py | Parametrizable strategy (15+ parameters) | ✅ Used in all Phases 5-8 |
| PHASE_8_OPTIMAL preset | fpl_auto/strategies.py | Locked final strategy | ✅ Contains all locked parameters from Phases 6-8 |

---

## Architecture Patterns

### Data Flow for Phase 9 Validation

```
Input:
  - PHASE_8_OPTIMAL (locked strategy config)
  - Historical seasons: 2021-22, 2022-23, 2023-24, 2024-25
  - Top 100 manager archive: data/2019-20/managers/top_managers.csv

Processing:
  1. nested_walk_forward_evaluation(PHASE_8_OPTIMAL, all_seasons)
     → Train on [2021-22, 2022-23] → Test 2023-24
     → Train on [2022-23, 2023-24] → Test 2024-25
  
  2. Per-iteration: run_season(strategy_config, season)
     → manager.py loop: GW1 to GW38
     → Each GW: auto_transfer → auto_captain → auto_chips → auto_subs → score
  
  3. Temporal audit (parallel):
     → Instrument data access at each GW
     → Log all reads: historical data, predictions, fixture metadata
     → Verify: no future-GW access observed

Output:
  - Per-season metrics: total_points, sharpe_ratio, sortino_ratio, max_drawdown
  - 95% CI bounds (bootstrap, 10,000 iterations)
  - Percentile ranking vs top 100 managers
  - Temporal audit report: PASS/FAIL + evidence traces
```

### Temporal Boundary Rules (from fpl_auto/temporal.py)

At gameweek N decision-making:

| Data Type | Accessible Range | Forbidden | Rule |
|-----------|-----------------|-----------|------|
| Historical form (actual points) | GW(1) to GW(N-1) | GW(N+) | Must be strictly before current |
| Predictions (model output) | GW(N) only | GW(N+1) onwards | Generated overnight before deadline |
| Fixture metadata | All GWs (1-38) | — | Pre-season knowledge (allowed) |
| Current GW actual results | Never during decisions | GW(N) during GW(N) decisions | Only available after gameweek closes |

**Implementation:** TemporalGate.safe_read_historical_form(target_gw) checks rule: `target_gw < decision_gameweek`

### Decision Points to Audit

1. **auto_transfer()** (manager.py) — accesses _all_xp_dicts (discounted predictions, GW(N) only) ✅
2. **auto_captain()** (team.py) — accesses captain candidate xP (GW(N) predictions) ✅
3. **auto_chips()** (team.py) — accesses upcoming GW blank/double fixture list ✅
4. **auto_subs()** (team.py with strategy_config) — accesses bench player xP (GW(N) predictions) ✅
5. **model.py training** — uses only GW(i-20) through GW(i-1), never GW(i) actual points ✅

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-season walk-forward validation | Custom train/test loop | nested_walk_forward_evaluation() (Phase 5) | Prevents data leakage, handles edge cases (incomplete seasons), proven working |
| Confidence interval calculation | Manual percentile sorting | bootstrap_ci() + numpy.percentile() | 10,000 iterations removes bias, handles small sample sizes |
| Multiple comparison correction | Ad-hoc p-value threshold | apply_bonferroni_correction() | α=0.05/k prevents false positives in k comparisons (Phase 5 provides this) |
| Season metric aggregation | Manual looping | compute_season_metrics() + aggregate_season_results() | Consistent implementation, handles missing GWs, edge cases |
| Temporal boundary checking | Manual if statements scattered in code | TemporalGate class + structured instrumentation | Centralized enforcement, auditable access log, easier testing |

**Key insight:** Phase 5 built the validation framework specifically for nested comparison. Reusing it prevents re-implementing complex, error-prone logic.

---

## 2024-25 Data Initialization Error

### Issue Summary

Phase 8 Plan 03 walk-forward evaluation encountered a blocking error when attempting to test on 2024-25 season:

```
Error: "Squad has no GK available for bench selection"
Location: team.py initialization during GW1 of 2024-25
Impact: Iteration 2 of walk-forward (test on 2024-25) did not complete
```

### Root Cause Analysis

**Hypothesis:** 2024-25 data is incomplete or has GK prediction data missing at season start.

**Evidence:**
- 2023-24 validation completed successfully (all 4 bench variants)
- 2024-25 error occurs during team initialization, not during gameplay
- Error message references bench GK selection, suggesting predictions/ or data/ files missing GK entries for early GWs

**Likely culprit locations:**
1. `predictions/2024-25/GW1/` directory — may lack GK.tsv (goalkeeper predictions file) [MOST LIKELY]
2. `data/2024-25/` — may have incomplete player or fixture CSV
3. `team.py auto_subs()` logic — may have edge case when GK predictions unavailable

### Investigation Steps Required

**Step 1:** Check predictions/2024-25/ directory structure
```bash
ls -la predictions/2024-25/GW*/  # Verify all positions (GK, DEF, MID, FWD) present
ls predictions/2024-25/GW1/
```

**Step 2:** Verify 2024-25 GK predictions exist
```bash
wc -l predictions/2024-25/GW1/GK.tsv  # Should have > 1 line (header + data)
head -3 predictions/2024-25/GW1/GK.tsv  # Inspect format
```

**Step 3:** Check team.py logic for GK availability assumption
```python
# Line ~XX in team.py auto_subs():
# Verify: does code assume GK.tsv exists for every GW?
# Does it handle case where no GK predictions available?
```

**Step 4:** If predictions incomplete, regenerate with model.py
```bash
PY=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3
$PY model.py -season 2024-25 -save  # (from CLAUDE.md commands)
```

### Mitigation Strategy

**Option A (Preferred):** Fix 2024-25 and revalidate Phase 8
- Cost: 1-2 hours (investigation + regeneration + Phase 8 re-run)
- Benefit: Cross-season robustness confirmed before Phase 9 final validation
- Risk: Low (same framework proven on 2023-24)

**Option B:** Accept single-season validation (2023-24 only)
- Cost: 0 hours (proceed to Phase 9 immediately)
- Benefit: Faster Phase 9 execution
- Risk: Phase 9 results lack cross-season evidence (weaker confidence)
- Note: CONTEXT.md indicates "limited impact on relative comparison"; acceptable fallback

**Recommendation:** Attempt Option A (1-2 hour investigation). If quick fix found (missing TSV file), regenerate and revalidate. If root cause requires code changes, fall back to Option B and document caveat in Phase 9 report.

---

## Top 100 Manager Historical Data

### Data Location & Format

**Primary archive:** `data/2019-20/managers/` (verified via filesystem audit)

**Files present:**
- `top_managers.csv` — Aggregate stats (likely: manager_id, final_rank, total_points, etc.)
- `top_managers_gwInfo.csv` — Per-gameweek breakdown (likely: gw, manager_id, gw_points, etc.)
- `top_managers_gwPicks.csv` — Squad composition (likely: gw, manager_id, player_id, captain, etc.)

**Version coverage:** 2019-20 season only (in examined directory structure)

**Status:** ⚠️ Data exists but LIMITED to single season. Phases 6-8 used 2023-24 as primary validation; Phase 9 requires multi-season top 100 data.

### Data Quality Assessment

**What we know:**
- 2019-20 top 100 manager data verified present
- Format matches FPL official export (standard CSV structure)
- Data includes per-GW breakdown and squad composition

**What we don't know:**
- Whether comparable data exists for 2021-22, 2022-23, 2023-24, 2024-25
- Distribution statistics (median, 75th percentile, max top 100 score per season)
- Whether "top 100" is consistent definition across seasons

### Usage for Phase 9

**Approach 1: Use available 2019-20 data**
- Pro: Data verified present and readable
- Con: Only 1 season; cannot do per-season comparison; outdated (5+ years)
- Result: Percentile rank calculated against 2019-20 top 100 only

**Approach 2: Gather multi-season data (research effort)**
- Pro: Enables per-season percentile ranking (2021-22 through 2024-25)
- Con: May require external data source or manual collection
- Result: Comprehensive comparison across available validation seasons

**Approach 3: Use aggregate average from FPL (if documented)**
- Pro: Quick, canonical reference
- Con: Requires finding reliable published statistics
- Result: Single aggregate threshold (e.g., "top 100 averaged 1850 pts/season")

### Preliminary Statistics (ASSUMED)

Based on FPL ecosystem knowledge (training data, not verified for this project):

| Metric | Estimated Value | Source |
|--------|-----------------|--------|
| Top 100 average (typical season) | 1800-1850 points | Training knowledge (LOW confidence) |
| Top 1 manager (typical season) | 2100-2200 points | Training knowledge (LOW confidence) |
| 75th percentile (top 25 of top 100) | 1950-2000 points | Training knowledge (LOW confidence) |
| Median (50th percentile, top 100) | 1700-1750 points | Training knowledge (LOW confidence) |

**Note:** These are ASSUMED. Phase 9 research must verify against actual data files or official sources.

### Integration with Walk-Forward Results

**Expected output from Phase 9:**
- PHASE_8_OPTIMAL total points: ~1817 (from 2023-24 validation)
- Top 100 average (2023-24 or historical): ~1825-1850 (TBD)
- Percentile rank: X-th percentile (calculated as: count of top 100 managers scoring < our_score / 100)
- Success criterion: Our score ≥ 0.75 × top_100_average

**Example calculation:**
```
Our optimized strategy: 1817 points (2023-24)
Top 100 average (2023-24): 1850 points
Percentile: ~45th (we're below median but above 30th percentile)
Success threshold: 1850 × 0.75 = 1387.5 ✅ PASS (1817 > 1387.5)
```

---

## Common Pitfalls

### Pitfall 1: Lookahead Bias in Model Predictions
**What goes wrong:** Model trained on 2024-25 data, then used to predict 2024-25 → circular logic.

**Why it happens:** Temporal boundaries not enforced during data pipeline; model training inadvertently accesses actual GW(N) points while predicting GW(N).

**How to avoid:** 
- Verify Phase 1 TemporalGate is active and enforced during model.py training
- Confirm predictions use only GW(i-20) through GW(i-1) training window
- Check that model.py -save flag generates predictions from properly windowed training

**Warning signs:**
- Phase 9 audit reports violations in TemporalGate access log
- Model performance suspiciously high (>95% predictive power — unrealistic)
- Temporal audit identifies future-GW access in predictions read path

### Pitfall 2: Single-Season Validation as Robustness Evidence
**What goes wrong:** Results on 2023-24 only; strategy fails on 2024-25 due to regime change not captured in training.

**Why it happens:** Walk-forward uses held-out test season but doesn't guarantee multi-regime coverage; 2024-25 may have different player values or fixture distribution.

**How to avoid:**
- Complete 2024-25 validation (fix data initialization error)
- Examine per-season breakdown (does performance hold 2021-22 through 2024-25?)
- If regime divergence detected, adjust parameters or document caveat

**Warning signs:**
- Phase 8 results show 2023-24 optimal but 2024-25 data missing
- Phase 9 report shows confidence interval that widens with additional seasons

### Pitfall 3: Percentile Ranking Inflation via Small Sample
**What goes wrong:** Calculate percentile rank using only 50 managers instead of 100 → inflates ranking (e.g., 60th percentile instead of true 40th).

**Why it happens:** Top 100 manager archive incomplete or aggregated from different sources with different manager counts.

**How to avoid:**
- Verify top_managers.csv contains exactly 100 or document actual count
- Use actual count in percentile calculation: `percentile = (count_worse / n_managers) × 100`
- Document sample size in Phase 9 report

**Warning signs:**
- top_managers.csv row count != 100
- Percentile rank is suspiciously high (>90th percentile with relatively modest score)

### Pitfall 4: Bootstrap CI Misinterpretation as Uncertainty
**What goes wrong:** Report 95% CI [1800, 1850] and interpret as "true value somewhere in this range"; actual issue is sample size = 2 seasons.

**Why it happens:** Bootstrap resampling from small N (2 test seasons) produces wide CIs that give false sense of uncertainty; real uncertainty is "what if trained on different N-1 seasons?"

**How to avoid:**
- Document that CI reflects bootstrap sampling variation, not all uncertainty
- Note: Walk-forward uses fixed train/test split; CI doesn't capture parameter uncertainty
- If only 2 test seasons available (2023-24, 2024-25), CI will be narrow despite low N

**Warning signs:**
- CI is suspiciously narrow (zero or near-zero width) — check if bootstrap actually resampled
- Report uses CI to claim precision that isn't justified by 2-season data

### Pitfall 5: Comparing Against Wrong Top 100 Baseline
**What goes wrong:** Compare 2023-24 strategy performance against 2019-20 top 100 average → different eras, different player pool.

**Why it happens:** Convenient data available (2019-20 top 100 archive) but not representative of current season players/strategy environment.

**How to avoid:**
- Use same-season top 100 data for comparison (2023-24 strategy vs 2023-24 top 100)
- If multi-season data unavailable, document seasonal difference in report caveats
- Or: Use long-term average (2019-20 through 2024-25 top 100) to smooth regime changes

**Warning signs:**
- Phase 9 report compares 2023-24 results to 2019-20 baseline without caveat
- Top 100 average differs from documented current-season benchmarks

---

## Runtime State Inventory

**Status:** N/A — Phase 9 is validation only, no rename/refactor/migration.

This section does not apply to Phase 9 (pure validation phase with no state changes).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (CLAUDE.md: `$PY -m unittest tests -v`) |
| Config file | tests.py (root) |
| Quick run command | `$PY -m unittest tests.TestPhase9TemporalAudit -v` |
| Full suite command | `$PY -m unittest tests -v` (all test classes) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PV-01 | Strategy scores ≥75% of top 100 average | integration | `$PY -m unittest tests.TestPhase9Validation.test_percentile_ranking -v` | ❌ Wave 0 |
| PV-02 | Temporal audit detects zero future-data violations | unit | `$PY -m unittest tests.TestPhase9TemporalAudit -v` | ❌ Wave 0 |
| PV-03 | Walk-forward produces valid metrics (total_points, sharpe, sortino, CI bounds) | integration | `$PY -m unittest tests.TestPhase9MetricsComputation -v` | ❌ Wave 0 |
| PV-04 | LOCKED_STRATEGIES.md updated with Phase 9 results | manual | Inspect file post-execution | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Run Phase 9 temporal audit on single season (2023-24): `~2 min`
- **Per wave merge:** Full walk-forward + temporal audit on all seasons: `~60 min`
- **Phase gate:** Full suite + percentile ranking ≥75% threshold + temporal audit PASS

### Wave 0 Gaps
- [ ] `tests.py::TestPhase9TemporalAudit` — instrument data access, verify no future-GW reads
- [ ] `tests.py::TestPhase9MetricsComputation` — verify nested_walk_forward_evaluation produces expected metrics
- [ ] `tests.py::TestPhase9Validation` — test percentile rank calculation against top 100 archive
- [ ] `evaluation/temporal_audit.py` (new) — orchestration script for temporal audit test harness
- [ ] `evaluation/percentile_rank.py` (new) — utility for computing percentile rank vs top 100 managers

*(Existing test infrastructure: nested_walk_forward_evaluation available and proven; bootstrap_ci and compute_season_metrics available)*

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10 | Runtime | ✓ | 3.10 (CLAUDE.md) | —|
| numpy | Metrics computation | ✓ | Latest | — |
| multiprocessing | Walk-forward parallelization | ✓ | stdlib | Serial execution (slower) |
| predictions/ dir (2024-25) | Walk-forward test season 2 | ⚠️ BROKEN | Incomplete | Skip 2024-25; validate 2023-24 only |
| data/2019-20/managers/ | Top 100 manager baseline | ✓ | 2019-20 only | Use alternative source or use 2019-20 aggregate |

**Missing dependencies with no fallback:**
- None critical; 2024-25 data breakage has fallback (validate 2023-24 only)

**Missing dependencies with fallback:**
- 2024-25 validation: Use 2023-24 only if fix not completed in time (documented caveat in Phase 9 report)
- 2023-24+ top 100 data: Use 2019-20 archive if current-season data unavailable (note temporal difference)

---

## Code Examples

### Example 1: Reusing Walk-Forward Framework (Phase 9)

Source: [evaluation/walk_forward.py](evaluation/walk_forward.py), Phase 5 proven implementation

```python
from fpl_auto.strategies import PHASE_8_OPTIMAL
from evaluation.walk_forward import nested_walk_forward_evaluation
from evaluation.metrics import compute_season_metrics

# Run walk-forward validation for final strategy
results = nested_walk_forward_evaluation(
    strategy_config=PHASE_8_OPTIMAL,
    all_seasons=['2021-22', '2022-23', '2023-24', '2024-25']  # or skip 2024-25 if broken
)

# Per-season breakdown
for iteration in results:
    test_season = iteration['test_season']
    total_points = iteration['test_metrics']['total_points']
    sharpe = iteration['test_metrics']['sharpe_ratio']
    sortino = iteration['test_metrics']['sortino_ratio']
    print(f"{test_season}: {total_points} pts, Sharpe {sharpe:.2f}, Sortino {sortino:.2f}")

# Aggregate across all test seasons
aggregate_metrics = aggregate_season_results(
    [r['test_results'] for r in results]
)
print(f"Average: {aggregate_metrics['avg_total_points']:.0f} pts")
```

### Example 2: Temporal Audit Instrumentation (Phase 9)

Source: [fpl_auto/temporal.py](fpl_auto/temporal.py), Phase 1 framework

```python
from fpl_auto.temporal import TemporalGate, TemporalViolationError

# During Phase 9 test harness: wrap data access calls
def test_temporal_integrity_at_gw(season: str, gw: int, manager_instance):
    """Audit single gameweek for temporal violations."""
    gate = TemporalGate(season=season, decision_gameweek=gw)
    
    # Intercept team.auto_transfer()
    # Expected: reads GW(1) through GW(gw-1) form, predictions GW(gw) only
    try:
        result = manager_instance.auto_transfer()
        # Log access_log from gate
        violations = [log for log in gate._access_log if 'future' in log.lower()]
        if violations:
            raise TemporalViolationError(f"GW {gw} accessed future data: {violations}")
        return True
    except TemporalViolationError as e:
        return False  # Log violation for audit report

# Run audit across season
audit_results = []
for gw in range(1, 39):
    passed = test_temporal_integrity_at_gw('2023-24', gw, manager)
    audit_results.append({'gw': gw, 'temporal_clean': passed})

audit_pass = all(r['temporal_clean'] for r in audit_results)
print(f"Temporal Audit: {'PASS' if audit_pass else 'FAIL'}")
```

### Example 3: Percentile Ranking Calculation (Phase 9)

Source: [evaluation/metrics.py](evaluation/metrics.py) pattern, adapted for top 100 comparison

```python
import pandas as pd
from evaluation.metrics import bootstrap_ci

def compute_percentile_rank(our_score: float, top_100_scores: list) -> float:
    """
    Calculate percentile rank of our strategy vs top 100 managers.
    
    Percentile = (count of top_100_scores < our_score) / len(top_100_scores) * 100
    """
    top_100_scores = sorted(top_100_scores)
    worse_count = sum(1 for score in top_100_scores if score < our_score)
    percentile = (worse_count / len(top_100_scores)) * 100
    return percentile

# Load top 100 data
top_100_df = pd.read_csv('data/2019-20/managers/top_managers.csv')
top_100_points = top_100_df['total_points'].tolist()  # Adjust column name

# Calculate for our strategy
our_2023_24_points = 1817  # From Phase 8 validation
percentile = compute_percentile_rank(our_2023_24_points, top_100_points)

# Bootstrap CI for percentile
percentiles = []
for _ in range(10000):
    # Resample top 100 with replacement
    sample = np.random.choice(top_100_points, size=len(top_100_points), replace=True)
    p = compute_percentile_rank(our_2023_24_points, sample)
    percentiles.append(p)

ci_lower, ci_upper = np.percentile(percentiles, [2.5, 97.5])
print(f"Percentile rank: {percentile:.1f}% (95% CI: {ci_lower:.1f}% - {ci_upper:.1f}%)")
```

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 2024-25 predictions/GW*/*.tsv files exist but may be incomplete | 2024-25 Data Issue | Walk-forward cannot complete; Phase 9 cannot validate cross-season robustness without fix |
| A2 | Top 100 manager average is ~1825-1850 points per season | Top 100 Manager Data | Success threshold calculation incorrect; strategy may appear to exceed or fall short of 75% target |
| A3 | TemporalGate rules in fpl_auto/temporal.py are complete and enforced | Temporal Integrity Audit Design | Audit may miss violations if TemporalGate doesn't cover all data access points |
| A4 | nested_walk_forward_evaluation() framework (Phase 5) is still functional and compatible | Architecture Patterns | Walk-forward execution fails; Phase 9 cannot produce core metrics |
| A5 | 2019-20 top_managers.csv contains exactly 100 rows (one per manager) | Top 100 Manager Data | Percentile rank calculation biased if sample size != 100 |

---

## Open Questions

1. **Where are multi-season top 100 manager statistics?**
   - What we know: 2019-20 top 100 data exists at data/2019-20/managers/
   - What's unclear: Does 2021-22, 2022-23, 2023-24, 2024-25 data exist? If not, should we gather it externally or use 2019-20 aggregate?
   - Recommendation: Research whether FPL official API or vaastav/Fantasy-Premier-League GitHub has current-season top 100 data

2. **Should Phase 9 proceed with 2024-25 data fix or accept single-season validation?**
   - What we know: 2024-25 initialization error blocks walk-forward iteration 2
   - What's unclear: How complex is the fix? (5 minutes vs 2 hours)
   - Recommendation: Attempt quick investigation (check predictions/2024-25/GW1/GK.tsv exists); if trivial, fix; if complex, accept 2023-24-only validation

3. **What is the exact structure of temporal audit test harness?**
   - What we know: TemporalGate exists; TemporalViolationError defined; access_log available
   - What's unclear: Should audit be integrated into manager.py loop or run as post-hoc analysis of traces?
   - Recommendation: Instrument manager.py with TemporalGate calls at each decision point (transfer, captain, chips, subs); log all reads; generate audit report post-season

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual transfer decisions | CONSERVATIVE_FULL strategy (parametric xP threshold) | Phase 6 | +22 points systematic improvement |
| Consistent captain (highest xP) | CAPTAIN_HIGHEST_VALUE (highest price) | Phase 7 | +12 points; more reliable predictive signal |
| Random bench | BENCH_SAFE_STATIC (cheap, stable) | Phase 8 | ±0 points; predictive swaps degrade (-111 pts) |
| Single-season evaluation | Walk-forward validation (train N-1, test held-out) | Phase 5 | Prevents overfitting; enables robust comparison |
| Point estimates | 95% bootstrapped CIs + Bonferroni correction | Phase 5 | Quantifies uncertainty; prevents false positives in multiple comparisons |

**Deprecated/outdated:**
- Predictive substitution swaps (Phase 8): Causes -111 point regression; disabled in PHASE_8_OPTIMAL
- Speculative bench composition (Phase 8): Zero impact vs safe bench; kept simple with safe variant

---

## Files & References

### Core Phase 9 Integration Points

| File | Purpose | Status |
|------|---------|--------|
| fpl_auto/strategies.py | PHASE_8_OPTIMAL preset | ✅ Ready |
| evaluation/walk_forward.py | nested_walk_forward_evaluation() | ✅ Proven (Phases 5-8) |
| evaluation/metrics.py | bootstrap_ci(), compute_season_metrics() | ✅ Available |
| fpl_auto/temporal.py | TemporalGate class + safe_read_* methods | ✅ Ready |
| LOCKED_STRATEGIES.md | Documentation (to be updated Phase 9) | ⚠️ Requires Phase 9 update |

### Data Sources

| Source | Location | Status | Notes |
|--------|----------|--------|-------|
| 2023-24 validation | data/2023-24/, predictions/2023-24/ | ✅ Complete | Walk-forward test set (Iter 1) |
| 2024-25 validation | data/2024-25/, predictions/2024-25/ | ⚠️ Broken GK data | Walk-forward test set (Iter 2), initialization error |
| 2021-22, 2022-23 | data/{season}/, predictions/{season}/ | ✅ Available | Walk-forward training sets |
| Top 100 managers | data/2019-20/managers/ | ✅ Present | 2019-20 only; current-season data TBD |

### Phase 8 Reference

| File | Purpose |
|------|---------|
| .planning/phases/08-bench-substitution-evaluation/RESULTS.md | Phase 8 findings (BENCH_SAFE_STATIC optimal, predictive swaps -111 pts) |
| .planning/phases/08-bench-substitution-evaluation/08-03-SUMMARY.md | Walk-forward execution report + locked parameters |
| evaluation/phase8_results.json | Phase 8 raw metrics (per-variant total_points, sharpe, sortino, CI bounds) |

---

## Metadata

**Confidence breakdown:**
- **Standard Stack (HIGH):** Walk-forward framework proven across Phases 5-8; bootstrap CI, Bonferroni correction available and tested
- **Architecture (HIGH):** TemporalGate class designed Phase 1; decision point coverage clear from manager.py, team.py code review
- **2024-25 Data Issue (MEDIUM):** Root cause hypothesis based on error message and directory structure; requires verification
- **Top 100 Manager Data (MEDIUM):** 2019-20 data verified present; current-season data location/format ASSUMED, not verified
- **Pitfalls (HIGH):** Drawn from Phase 1-8 lessons learned and standard temporal integrity / validation literature

**Research date:** 2026-05-28  
**Valid until:** 2026-06-04 (7 days for fast-moving data quality issues; temporal/metrics stable)

---

*Research completed 2026-05-28. Ready for Phase 9 planning.*
