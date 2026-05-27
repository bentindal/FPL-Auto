# Phase 6: Transfer Strategy Evaluation — Research

**Researched:** 2026-05-27  
**Domain:** Transfer strategy variants (frequency + timing + thresholds) using Phase 5 evaluation framework  
**Confidence:** HIGH

---

## Summary

Phase 6 extends Phase 5's strategy framework to test 5 transfer variants (conservative/baseline/aggressive × early/mid/late windows) using walk-forward validation. The research confirms:

1. **auto_transfer() is ready for extension** — uses 5-GW discounted xP (via `_all_xp_dicts`), applies xP-gain threshold (default 4 points), and can accept budget/window constraints as new parameters.

2. **StrategyConfig structure supports transfer variants** — `transfer_mode` enum is defined ('never', 'flexible', 'greedy') but **not currently used in auto_transfer()**. The config is passed to `run_season()` but not consumed. Phase 6 must wire these parameters into the decision logic.

3. **Walk-forward evaluation framework (Phase 5) is production-ready** — `nested_walk_forward_evaluation()` runs 2 test iterations (2023-24, 2024-25) with training on prior seasons, returns per-season metrics + bootstrapped CIs, and integrates with `metrics.bootstrap_ci()` for significance testing.

4. **Baseline results exist** (`evaluation/baseline_results.json`) — BASELINE_STATIC and BASELINE_CURRENT have been run; ready as comparison anchors.

5. **Temporal integrity enforced** — Phase 1 TemporalGate validates no lookahead; xP calculations use only GW-available data (confirmed via `discount_next_n_gws` checks `gw + n`).

**Primary recommendation:** Implement transfer variants by adding `transfer_budget_per_gw`, `transfer_window_gw_range`, and `transfer_xp_threshold` parameters to StrategyConfig; wire these into auto_transfer() via a new config-aware method; run variants through `nested_walk_forward_evaluation()`.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Transfer frequency model:** Points-per-GW budget (not fixed transfer counts)
- **Transfer timing windows:** Three fixed windows (GW 1-10, 11-24, 25-38)
- **Decision rule:** xP improvement threshold (e.g., 10-20% relative improvement triggers transfer)
- **Variant scope:** 5 focused variants along a conservative→aggressive diagonal
- **Evaluation method:** Walk-forward validation with 95% bootstrapped CIs
- **Significance test:** Non-overlapping CIs indicate true difference

### Claude's Discretion
- Which parameters to add/modify in StrategyConfig
- How to integrate budget constraints into auto_transfer() logic
- Transfer efficiency diagnostic metric implementation

### Deferred Ideas (OUT OF SCOPE)
- Multi-objective optimization (Pareto frontier)
- Transfer timing using game theory / prediction confidence
- Actual FPL -4 point transfer penalties
- Real-time transfer suggestions for upcoming season

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TS-01 | Transfer frequency variants implemented | `transfer_budget_per_gw` parameter design (below) |
| TS-02 | Transfer timing variants implemented | `transfer_window_gw_range` parameter; window filtering logic in auto_transfer() |
| TS-03 | All variants tested with walk-forward validation | Confirmed: walk_forward.py `nested_walk_forward_evaluation()` ready; accepts StrategyConfig |
| TS-04 | Results compared against baselines (non-overlapping CIs) | Confirmed: metrics.py `bootstrap_ci()` + `apply_bonferroni_correction()` ready |

---

## Current auto_transfer() Implementation

**Location:** `fpl_auto/team.py:447-471`

```python
def auto_transfer(self, threshold=4):
    # Early returns: season exceptions, gameweek > 35, no transfers left
    if self.transfers_left <= 0:
        return
    
    # Loop over available transfers (typically 1-2)
    for _ in range(self.transfers_left):
        out, pos, budget = self.suggest_transfer_out()  # Lowest xP player
        if pos == '':
            return
        if budget + self.budget < MIN_PRICE[pos]:
            return
        transfer_in = self.suggest_transfer_in(pos, out, self.budget + budget)
        # CRITICAL: xP improvement threshold check
        if transfer_in != 'No player found to transfer in' and \
           self.player_xp(transfer_in, pos) - self.player_xp(out, pos) >= threshold:
            self.transfer(out, transfer_in, pos)
            if self.squad_size() != SQUAD_SIZE:
                self.remove_excess_players()
        else:
            break
```

**Key observations:**

1. **xP source:** Uses `self.player_xp(player, pos)` which reads from `self._all_xp_dicts[pos]` — the **5-GW discounted lookahead** (confirmed in team.py:79-82). This is correct per CLAUDE.md.

2. **Threshold logic:** Line 466 checks `xp_gain >= threshold` (default 4 points). **Not relative yet** — it's absolute. CONTEXT.md specifies relative (e.g., 20% improvement = `xp_gain / xp_out > 0.20`).

3. **Transfer selection:** `suggest_transfer_out()` benches the weakest player (lowest xP). `suggest_transfer_in()` finds best-xP replacement with `xp_gain >= 2`. Both use `_all_xp_dicts` (multi-GW discounted).

4. **Budget handling:** Selling price accounts for profit-on-sale (team.py:667-675). Buying price is from gw_data. Current code allows infinite transfers as long as budget permits — no concept of "transfer budget per season."

5. **Window constraints:** None. Transfers happen whenever threshold is met and transfers_left > 0.

**Extension points:**

- Add `transfer_budget_per_gw: float` to track cumulative points budget spent
- Add `transfer_window_gw_range: Optional[Tuple[int, int]]` to restrict transfers to window (e.g., (1, 10))
- Add `transfer_xp_threshold_mode: str` enum ('absolute' vs 'relative') to handle `threshold >= 4` vs `threshold > xp_out * 0.20`
- Modify auto_transfer() to check these before making a transfer

---

## StrategyConfig Structure & Integration

**Location:** `fpl_auto/strategies.py:11-231`

**Current state:** StrategyConfig is a dataclass with 14 parameters covering transfer_mode, captain_mode, chip_schedule, bench_mode, and risk parameters. **However, these parameters are NOT currently used in auto_transfer() or manager.py.**

**Current parameters relevant to Phase 6:**

```python
@dataclass
class StrategyConfig:
    transfer_mode: str = 'flexible'  # 'never' | 'flexible' | 'greedy'
    max_transfers_per_gw: int = 1     # Max transfers per GW (0-2)
    transfer_discount_factor: float = 0.8  # Discount for multi-GW lookahead
    # ... (captain, chip, bench, risk params)
```

**What's missing for Phase 6:**

These parameters are defined but never read in auto_transfer(). Phase 6 must add:

1. **transfer_budget_per_gw: float** — Points-per-GW budget (e.g., 0.5 for conservative, 2.0 for aggressive)
   - Stored as budget class field: `self.transfer_budget_spent = 0`
   - Per GW, reset to 0
   - Each transfer costs `xp_gain` points against budget

2. **transfer_window_gw_range: Optional[Tuple[int, int]]** — Restrict transfers to (gw_start, gw_end) inclusive
   - Example: (1, 10) for early window
   - If None, entire season

3. **transfer_xp_threshold: float** — Base threshold for xP gain
   - If mode='absolute': `xp_gain >= threshold`
   - If mode='relative': `xp_gain / xp_out > threshold` (e.g., 0.20 for 20%)

**Preset variants (from CONTEXT.md):**

| Variant | transfer_budget_per_gw | transfer_window | transfer_xp_threshold | transfer_mode |
|---------|-------------------------|-----------------|----------------------|---------------|
| CONSERVATIVE_EARLY | 0.5 | (1, 10) | 0.20 (20% relative) | flexible |
| CONSERVATIVE_FULL | 0.5 | None | 0.20 | flexible |
| BASELINE_MID | 1.5 | (11, 24) | 0.15 (15% relative) | flexible |
| AGGRESSIVE_LATE | 2.0 | (25, 38) | 0.10 (10% relative) | greedy |
| AGGRESSIVE_FULL | 2.0 | None | 0.10 | greedy |

**How to extend StrategyConfig:**

Option A (preferred): Add fields directly to StrategyConfig, validate in __post_init__:
```python
transfer_budget_per_gw: float = 1.5  # Points/GW budget (0.5-3.0)
transfer_window_gw_range: Optional[Tuple[int, int]] = None
transfer_xp_threshold: float = 0.15  # 15% relative improvement
transfer_xp_threshold_mode: str = 'relative'  # 'absolute' or 'relative'
```

Option B: Create a separate TransferConfig dataclass nested in StrategyConfig (cleaner separation).

**Recommendation:** Option A — simpler, fewer imports, consistent with Phase 5 design.

---

## xP Calculation & 5-GW Rolling Average

**Confirmed availability:**

1. **Location:** `fpl_auto/data.py:430-456` → `discount_next_n_gws(predictions, gw, n, discount_factor)`

2. **How it works:**
   - Called in `team.py:66` → `self.all_xp = self._get_n_gws_xp(5, discount_factor=0.8)`
   - Computes fixture-adjusted xP for next n gameweeks, applies exponential discount: `discount_weights = [0.8^i for i in range(n)]`
   - Returns list of DataFrames, one per position, with `Name` + `xP` columns
   - xP values are **summed** across the n GWs (see bug fix in memory: was incorrectly using mean)

3. **Used by auto_transfer():** Yes, via `self._all_xp_dicts[pos]` dict built from `self.all_xp` DataFrames (team.py:79-82)

4. **Temporal integrity:** 
   - `discount_next_n_gws` checks `if gw + n > 38: n = 38 - gw` — no lookahead beyond season
   - Calls `post_model_weightings(predictions, gw, n)` which applies fixture adjustments using only past data relative to gw

**Safe to use?** YES [VERIFIED]. The 5-GW discounted lookahead is already in production, used for captain selection and transfer decisions. It correctly prevents lookahead violations.

---

## Walk-Forward Evaluation Framework (Phase 5)

**Location:** `evaluation/walk_forward.py:154-260`

**Signature:**
```python
def nested_walk_forward_evaluation(
    strategy_config: StrategyConfig,
    all_seasons: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
```

**Returns:** List of 2 iteration dicts (one per test season: 2023-24, 2024-25):

```python
[
    {
        'iteration': 1,
        'test_season': '2023-24',
        'train_seasons': ['2021-22', '2022-23'],
        'test_results': {'season', 'p_list', 'xp_list', 'chips_used', 'transfer_history', 'total_points'},
        'test_metrics': {'total_points', 'mean_gw_points', 'std_gw_points', 'sharpe_ratio', 'sortino_ratio', 'coefficient_variation', 'max_drawdown', 'best_week', 'worst_week'},
        'train_metrics': {'avg_total_points', 'avg_mean_gw_points', ...},
        'timestamp': datetime ISO string,
    },
    ...
]
```

**How it integrates with Phase 6:**

1. Phase 6 creates new StrategyConfig instances (CONSERVATIVE_EARLY, etc.) with Phase 6 parameters
2. Calls `nested_walk_forward_evaluation(config)` for each variant
3. Collects results with test_metrics for each iteration
4. Uses `metrics.bootstrap_ci()` to compute 95% CIs on total_points, sharpe_ratio, etc.
5. Checks if CIs overlap (null hypothesis: strategies are equivalent)

**Key dependency:** `manager.run_season(config)` must read and USE the strategy parameters (currently it accepts config['strategy'] but doesn't pass it to team methods).

---

## Integration Checklist

### Files that need modification:

1. **fpl_auto/strategies.py** — Add 3-4 new parameters to StrategyConfig + create 5 variant instances
2. **fpl_auto/team.py** — Modify `auto_transfer()` to read strategy parameters (or accept them as method args)
3. **manager.py** — Wire strategy config to team instance so auto_transfer() can use it
4. **evaluation/walk_forward.py** — No changes needed (already runs arbitrary StrategyConfig)
5. **tests.py or evaluation/test_evaluation.py** — Add tests for new transfer variants

### Data & environment:

- Baseline results: `evaluation/baseline_results.json` ✓ CONFIRMED EXISTS
- Prediction TSVs: `predictions/{season}/GW{n}/{pos}.tsv` ✓ Required (check with user if present)
- Test seasons: 2021-22, 2022-23, 2023-24, 2024-25 ✓ Available per CLAUDE.md

### Import/module dependencies:

- StrategyConfig already imported in manager.py:59-60 ✓
- walk_forward.py imports StrategyConfig ✓
- No circular imports expected

---

## Known Unknowns & Edge Cases

### 1. Budget Accounting Ambiguity [MEDIUM RISK]

**Question:** How is `transfer_budget_per_gw` spent?

**Current understanding:**
- auto_transfer() loops `for _ in range(self.transfers_left)` (typically 1 or 2 per GW)
- Each transfer has xP cost = `xp_in - xp_out`
- If budget is "1.5 points/GW", does that mean:
  - Option A: "Spend up to 1.5 xP points per GW on transfers" → if xp_gain is 0.8, subtract 0.8 from budget, allow another if budget remains
  - Option B: "Make transfers only if total xp_gain >= 1.5" → single trigger, not cumulative

**Recommendation:** Option A (cumulative budget window). Analogous to FPL transfer tokens.

**Implementation detail:** Track `self.transfer_budget_spent` per GW, reset at GW boundary, check `budget_remaining = transfer_budget_per_gw - transfer_budget_spent` before each transfer.

### 2. Relative vs Absolute Threshold [MEDIUM RISK]

**Current code uses absolute:** `xp_gain >= threshold` (e.g., >= 4 points)

**CONTEXT.md specifies relative:** `(new_xp - old_xp) / old_xp > threshold` (e.g., > 20%)

**Edge case:** If `old_xp = 1.0` and threshold = 0.20 (20%), minimum acceptable `new_xp = 1.2`. But current code would need `xp_gain >= 4`, implying `new_xp >= 5` — much stricter.

**Recommendation:** 
- Add `transfer_xp_threshold_mode: str = 'relative'` to StrategyConfig
- In auto_transfer(), compute:
  ```python
  if threshold_mode == 'relative':
      xp_gain_pct = (xp_in - xp_out) / max(xp_out, 0.1)  # Avoid div-by-zero
      passes = xp_gain_pct > threshold
  else:
      passes = (xp_in - xp_out) >= threshold
  ```

### 3. Gameweek Boundary Handling [LOW RISK]

**Question:** When is `transfer_budget_spent` reset?

**Answer:** At the start of each GW when new Team instance is created (manager.py:142-150). Initialize `team.transfer_budget_spent = 0` in Team.__init__.

**Confirmed safe:** Team class is instantiated fresh each GW, so no carryover risk.

### 4. Fractional Budget Allocation [LOW RISK]

**Question:** E.g., 0.5 pts/GW × 38 GWs = 19 total. Is this precise, or should we accumulate remainders?

**Example:** GW 1 budget 0.5, only made 0.3 xP transfer. Remainder = 0.2. 
- Option A: Lose 0.2 (reset each GW)
- Option B: Carry forward (GW 2 budget = 0.5 + 0.2 = 0.7)

**Recommendation:** Option A (simpler, matches FPL token logic). If needed, could add `transfer_budget_carry_forward: bool = False` parameter in Phase 6+.

### 5. No Transfer Cost for Hits [LOW RISK]

**Constraint from CONTEXT.md:** "Current model assumes infinite budget (no -4 point penalty for transferring out). Phase 6 stays in-scope; deferred: accounting for actual FPL -4 point penalties."

**Implication:** Budget logic only tracks positive xP gain, not -4 point hit costs. This is acceptable for Phase 6 and noted as deferred.

### 6. Transfers After GW 35 [CONFIRMED]

**Current code:** `if self.gameweek > 35: return` (team.py:453)

**Impact on late window (GW 25-38):** Late window includes GW 25-35 (10 GWs), not all of 25-38. GW 36-38 transfers disabled.

**Check:** Is this intentional (FPL rules)? Yes — confirmed in CLAUDE.md constraints.

---

## Code Examples

### Example 1: Absolute vs Relative Threshold

```python
# From team.py:466 (current code — absolute only)
if self.player_xp(transfer_in, pos) - self.player_xp(out, pos) >= threshold:
    self.transfer(out, transfer_in, pos)

# Phase 6 extension (relative + absolute)
xp_in = self.player_xp(transfer_in, pos)
xp_out = self.player_xp(out, pos)
xp_gain = xp_in - xp_out

if self.strategy_config.transfer_xp_threshold_mode == 'relative':
    # Relative improvement: (new - old) / old > threshold
    # Handle div-by-zero: if xp_out near 0, very low bar
    xp_out_safe = max(xp_out, 0.1)
    passes_threshold = (xp_gain / xp_out_safe) > self.strategy_config.transfer_xp_threshold
else:
    # Absolute: new - old >= threshold
    passes_threshold = xp_gain >= self.strategy_config.transfer_xp_threshold

if xp_gain >= 2 and passes_threshold:  # xp_gain >= 2 is pre-filter from suggest_transfer_in
    self.transfer(out, transfer_in, pos)
```

**Source:** [Code pattern from team.py suggest_transfer_in logic + auto_transfer threshold check]

### Example 2: Window-Aware Transfer Decision

```python
def should_transfer_this_gw(self) -> bool:
    """Check if current GW is within transfer window."""
    if not hasattr(self, 'strategy_config') or self.strategy_config.transfer_window_gw_range is None:
        return True  # No window restriction
    
    gw_min, gw_max = self.strategy_config.transfer_window_gw_range
    return gw_min <= self.gameweek <= gw_max

def auto_transfer(self):
    """Modified to respect budget and window constraints."""
    if self.transfers_left <= 0:
        return
    
    # NEW: Check window
    if not self.should_transfer_this_gw():
        return
    
    for _ in range(self.transfers_left):
        # NEW: Check budget
        if self.transfer_budget_spent >= self.strategy_config.transfer_budget_per_gw:
            break
        
        out, pos, budget = self.suggest_transfer_out()
        # ... rest of logic ...
        
        # NEW: Record budget spent
        if transfer_executed:
            self.transfer_budget_spent += xp_gain
```

**Source:** [Derived from team.py:447-471 structure + CONTEXT.md requirements]

### Example 3: Variant Creation (from CONTEXT.md)

```python
# In strategies.py, add new variant:
CONSERVATIVE_EARLY = StrategyConfig(
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,  # NEW
    transfer_window_gw_range=(1, 10),  # NEW
    transfer_xp_threshold=0.20,  # NEW: 20% relative improvement
    transfer_xp_threshold_mode='relative',  # NEW
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=2,
    bench_mode='static',
    bench_injury_threshold=0.5,
    position_variance_tolerance=0.9,
    punt_threshold=1.0,
)
```

---

## State of the Art

| Aspect | Old Approach | Current Approach | Status |
|--------|--------------|------------------|--------|
| Strategy parametrization | Hard-coded threshold values (e.g., threshold=4 in auto_transfer) | StrategyConfig dataclass with 14+ parameters | Phase 5 ✓ |
| Transfer decision logic | Fixed: `xp_gain >= 4` | Configurable: threshold + mode (relative/absolute) + budget + window | Phase 6 (in research) |
| xP lookahead | Single-GW predictions | 5-GW discounted lookahead via discount_factor=0.8 | Phase 4 ✓ |
| Evaluation | Manual season runs; no statistical rigor | Walk-forward validation + bootstrapped CIs + Bonferroni correction | Phase 5 ✓ |
| Strategy variants | None (monolithic manager.py) | 5 preset archetypes + arbitrary custom configs | Phase 5 ✓ |

**Deprecated/outdated:**
- `transfer_mode` parameter exists but not wired to auto_transfer() — Phase 6 will activate it
- Hard-coded thresholds (auto_transfer threshold=4, suggest_transfer_in xp_gain >= 2, etc.) — Phase 6 will parameterize

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The 5-GW discounted xP values are correctly computed via discount_next_n_gws (sum, not mean) | xP Calculation | If wrong, all thresholds miscalibrated; ~+22% gain observed after bug fix in May 2026 |
| A2 | transfer_budget_per_gw should be cumulative within a GW (reset each GW) | Budget Accounting | If wrong, budget logic becomes unclear; could accumulate across seasons |
| A3 | Relative threshold formula: (new - old) / old > threshold (not < or >=) | Relative Threshold | If wrong, variants trigger on opposite condition; test results inverted |
| A4 | Window constraints apply per-GW (GW outside window → no transfers) | Window Handling | If wrong, transfers leak across window boundaries |
| A5 | Team instance is instantiated fresh each GW (team.transfer_budget_spent resets automatically) | Boundary Handling | If wrong, budget carries across GWs unintentionally |

---

## Open Questions

1. **Should transfer_budget_per_gw be season-wide or per-GW?**
   - Current research assumes **per-GW** (more like FPL token system)
   - If season-wide: budget = 0.5 × 38 = 19 total for season, deplete over 38 GWs
   - Recommendation: Per-GW (clearer intent in CONTEXT.md variant names like "CONSERVATIVE_EARLY")

2. **How should "transfer efficiency" diagnostic metric be computed?**
   - CONTEXT.md mentions: "Average points gained per transfer made"
   - Design: Track transfers made + sum xp_gains; report as average per transfer
   - Should this be per-season, per-variant, or both?

3. **Do we need transfer_mode wiring beyond Phase 6 parameters?**
   - transfer_mode values ('flexible', 'greedy') are not yet used
   - Phase 5 design suggests they control max_transfers_per_gw behavior (but not active)
   - Should Phase 6 also wire transfer_mode → max_transfers_per_gw enforcement?

4. **FPL -4 point penalties: Out of scope, but should we add a stub for Phase 6+?**
   - Currently deferred per CONTEXT.md
   - Should test framework check for it, or leave unimplemented?

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Test runner | ✓ | 3.10 | — |
| unittest | Test framework | ✓ | stdlib | pytest (alternative) |
| numpy | Metrics, discounting | ✓ | via venv | — |
| pandas | GW data, predictions | ✓ | via venv | — |
| sklearn | Model training (not Phase 6) | ✓ | via venv | — |
| Predictions TSVs | Auto_transfer xP input | ? | — | Run model.py -save first |

**Missing dependencies:** If prediction TSVs are not present, walk_forward.py will fail when running new seasons. User must run `python model.py -season {season} -save` before Phase 6 execution.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (from tests.py) |
| Config file | None — tests.py monolithic |
| Quick run command | `python -m unittest tests.TestAutoTransfer -v` (if created) |
| Full suite command | `python -m unittest tests -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TS-01 | Transfer frequency variants instantiate without error | unit | `python -c "from fpl_auto.strategies import CONSERVATIVE_EARLY; print('OK')"` | ✓ Phase 5 |
| TS-02 | Transfer window constraint blocks transfers outside window | unit | `python -m unittest tests.TestTransferWindow -v` | ❌ Wave 0 |
| TS-03 | Walk-forward evaluation runs all 5 variants | integration | `python evaluation/walk_forward.py` (with new variants) | ✓ Phase 5 core |
| TS-04 | Results CIs non-overlapping with baseline | integration | `python evaluation/compare_variants.py` (new script) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m unittest tests.TestAutoTransfer -v`
- **Per wave merge:** `python -m unittest tests -v && python evaluation/walk_forward.py`
- **Phase gate:** Full walk-forward results + statistical significance report before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_transfer_variants.py` — unit tests for CONSERVATIVE_EARLY, AGGRESSIVE_FULL, etc.; window constraint verification
- [ ] `tests/test_transfer_budget.py` — cumulative budget tracking across multiple transfers per GW
- [ ] `evaluation/compare_variants.py` — script to load baseline_results.json, run new variants, compute CIs, report significance
- [ ] Framework install: Already in venv; no new dependencies needed

---

## Security Domain

Not applicable — Phase 6 is offline simulation logic; no external APIs, authentication, or user data handling.

---

## Sources

### Primary (HIGH confidence)
- **Context7:** Not used (Python project; Context7 targets JS/TS libraries)
- **Official codebase:** 
  - `fpl_auto/team.py` (auto_transfer, player_xp, xP source) [VERIFIED: read lines 447-471, 261-265, 79-82]
  - `fpl_auto/strategies.py` (StrategyConfig structure) [VERIFIED: read lines 11-231]
  - `fpl_auto/data.py` (discount_next_n_gws) [VERIFIED: read lines 430-456]
  - `evaluation/walk_forward.py` (nested_walk_forward_evaluation) [VERIFIED: read lines 154-260]
  - `evaluation/metrics.py` (bootstrap_ci, compute_season_metrics) [VERIFIED: read lines 13-221]
  - `manager.py` (strategy integration) [VERIFIED: read lines 32-71, 125-160]
  - `evaluation/baseline_results.json` [VERIFIED: exists, parsed structure]
  - `CLAUDE.md` (architecture, constraints) [VERIFIED: read project guidelines]

### Secondary (MEDIUM confidence)
- User memory: feedback_transfer_bugs.md [cited for bug history, confirms discount_next_n_gws fix]
- CONTEXT.md Phase 6 (decision requirements) [cited for variant definitions, decision rules]

### Not needed
- WebSearch, WebFetch — domain is fully specified in codebase and upstream CONTEXT.md

---

## Metadata

**Confidence breakdown:**
- Standard stack (xP calculation, walk-forward framework): **HIGH** — verified in codebase
- Architecture (auto_transfer extension points): **HIGH** — code is clear, bugs documented
- Parameter design (transfer_budget_per_gw, transfer_window, threshold_mode): **MEDIUM** — designed from CONTEXT.md but not yet implemented; requires planner validation
- Edge cases (budget accumulation, div-by-zero, season boundaries): **MEDIUM** — identified but not tested; flagged as unknowns

**Research date:** 2026-05-27  
**Valid until:** 2026-06-27 (30 days; stable domain with no rapid changes expected)

**Next step:** Planner creates detailed implementation plans for:
1. StrategyConfig extension (add 4 new parameters)
2. auto_transfer() modification (wire parameters + implement logic)
3. manager.py wiring (pass strategy config to team)
4. Test framework (unit + integration tests)
5. Variant evaluation script (run 5 variants, compare vs baseline)
