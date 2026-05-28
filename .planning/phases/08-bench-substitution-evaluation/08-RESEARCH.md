# Phase 8: Bench & Substitution Strategy Evaluation — Research

**Researched:** 2026-05-28  
**Domain:** Bench composition and substitution logic optimization  
**Confidence:** HIGH (current implementation examined, FPL patterns verified, Phase 7 integration understood)

---

## Summary

Phase 8 will optimize bench composition and substitution strategies as the next layer above Phase 6-7 locked parameters (transfers + captain selection). The current implementation uses a passive bench rotation approach: `suggest_subs()` benches the lowest single-GW xP players each gameweek without strategic variation. This research identifies three viable bench composition variants and two substitution logic variants that can be tested independently using the Phase 5 walk-forward framework.

**Primary recommendation:** Implement 2 bench composition variants (BENCH_SAFE, BENCH_SPECULATIVE) and 2 substitution variants (SUBS_STATIC_ORDER, SUBS_PREDICTIVE_SWAP) in a 2×2 nested design. Test this 4-variant matrix under CONSERVATIVE_FULL transfer + CAPTAIN_HIGHEST_VALUE lock to isolate bench/subs impact.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Transfer:** CONSERVATIVE_FULL (transfer_budget_per_gw=0.5, transfer_xp_threshold=0.20)
- **Captain:** CAPTAIN_HIGHEST_VALUE (optimal variant from Phase 7a, +12 points)
- **Chips:** CONSERVATIVE (no significant improvement from timing variants)

### Claude's Discretion
1. **Bench composition philosophy:** Safe vs speculative vs balanced variants (CONTEXT lists 3 options)
2. **Substitution trigger timing:** Predictive vs reactive vs defensive (CONTEXT lists 3 options)
3. **Variant scope:** How many total bench/subs variants to test (2-6 recommended)
4. **Independence vs nesting:** Test bench variants independently or nested under captain variants

### Deferred Ideas (OUT OF SCOPE)
- Dynamic bench allocation based on injury ML models
- Real-time captaincy + bench co-optimization
- Squad value metrics (ROI, points per pound)
- Bench variance analysis (replicate top 100 manager benches)

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Bench composition (initial squad selection) | API/Backend (team.py) | — | Allocates squad budget across 15 players; driven by xP predictions and cost constraints |
| Substitution logic (weekly bench rotation) | API/Backend (team.py) | — | Decides who plays GW(i) vs GW(i+1) based on injuries, form, fixtures; no frontend involved |
| Bench ordering (auto-sub priority) | API/Backend (team.py) | — | Sets order of bench players; controls which bench player auto-substitutes if starter unavailable |
| Metrics capture (bench utilization, points left on bench) | Evaluation (metrics.py) | — | Tracks bench contribution to total points and opportunity cost |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 1.x | DataFrame operations (player data, predictions, fixtures) | [VERIFIED: codebase imports] Already used throughout for xP lookups and position ranking |
| numpy | 1.x | Numerical operations (xP discounting, sorting) | [VERIFIED: codebase imports] Essential for efficient array operations in benchmarking |
| sklearn | 0.24+ | Model predictions (xP TSVs from model.py) | [VERIFIED: codebase imports] Produces the multi-GW discounted xP used in all decisions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| unittest | stdlib | Test framework for bench/subs variants | [VERIFIED: codebase] Already in use (tests.py); cover new bench_mode and substitution_mode logic |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FPL Rules (position constraints) | Custom validation | Using official rules (min 3 DEF, max 3 FWD, 1 GK) ensures legal formations; custom logic adds risk |
| xP-based substitution | Rules-based (observed points) | xP uses future model predictions (available pre-deadline); observed points require post-match data (reactive only) |

**Installation:**
```bash
# No new dependencies; use existing: pandas, numpy, sklearn, unittest
```

---

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Season Loop (manager.py GW iteration)                       │
│                                                              │
│  GW(i): [auto_transfer] → [auto_subs] → [auto_captain]    │
│                              ↓                               │
│                      Bench composition                       │
│                      + Sub logic decision                    │
│                              ↓                               │
│                    [team_xp] [team_p]                       │
│                              ↓                               │
│                      Results captured                        │
└─────────────────────────────────────────────────────────────┘

Bench Composition (happens once at GW1 via initial_team_generator):
┌──────────────────────────────────────┐
│ Bench Variant Selection              │
│ (BENCH_SAFE / BENCH_SPECULATIVE)    │
│                                      │
│ → Budget allocation by position      │
│ → Player filtering by archetype      │
│ → Initial squad of 15 built          │
│ → First 4 subs selected              │
└──────────────────────────────────────┘

Substitution Logic (happens every GW via auto_subs):
┌──────────────────────────────────────┐
│ Substitution Variant Selection       │
│ (SUBS_STATIC_ORDER /                │
│  SUBS_PREDICTIVE_SWAP)              │
│                                      │
│ → Check starter form/injury status   │
│ → Optionally trigger bench swap      │
│ → Update bench ordering for next GW  │
│ → Pass to auto_captain for decision  │
└──────────────────────────────────────┘
```

### Recommended Project Structure
```
fpl_auto/
├── team.py                    # Extend suggest_subs(), bench composition logic
├── strategies.py              # Add bench_mode, substitution_mode parameters
└── [no new files for Phase 8]

evaluation/
├── walk_forward.py            # Reuse for Phase 8 variant testing
├── metrics.py                 # Add bench_utilization_pct metric
└── compare_bench_variants.py  # [PLAN creates this]
```

### Pattern 1: Bench Composition Variants (GW1 initialization)

**What:** Determine how 4 bench players are selected during `initial_team_generator()`. Controls squad diversity, cost structure, and risk profile.

**When to use:** Once per season at GW1. All downstream substitution decisions inherit this bench.

**Example: BENCH_SAFE variant**

```python
# Source: Phase 8 implementation pattern (derived from Phase 6 transfer logic)
# In fpl_auto/strategies.py:

class Team:
    def initial_team_generator(self, bench_mode='rotate_low_xp'):
        """Select initial 15-player squad with bench composition strategy."""
        
        if bench_mode == 'safe':
            # Allocate 30% of bench budget to defensive specialists
            # Prefer: experienced defenders, high clean sheet probability, lower price
            bench_strategy = {
                'GK': {'cost_weight': 0.5, 'xp_weight': 0.1},      # cheap GK, rely on price
                'DEF': {'cost_weight': 0.6, 'xp_weight': 0.2},     # emphasize cost/clean sheets
                'MID': {'cost_weight': 0.3, 'xp_weight': 0.4},     # cheaper midfielders
                'FWD': {'cost_weight': 0.2, 'xp_weight': 0.3},     # minimal FWD bench coverage
            }
        elif bench_mode == 'speculative':
            # Allocate 40% of bench budget to high-upside players
            # Prefer: young talents, high variance xP, promotion candidates
            bench_strategy = {
                'GK': {'cost_weight': 0.3, 'xp_weight': 0.5},      # accept variance
                'DEF': {'cost_weight': 0.2, 'xp_weight': 0.6},     # high-variance defenders
                'MID': {'cost_weight': 0.5, 'xp_weight': 0.5},     # balanced
                'FWD': {'cost_weight': 0.6, 'xp_weight': 0.4},     # upside-weighted
            }
        
        # Apply bench_strategy weights to _get_best_players()
        # This determines which players fill the bench slots
```

### Pattern 2: Substitution Logic Variants (Every GW)

**What:** Decide whether and when to rotate bench players in/out based on triggers (injuries, form, fixtures).

**When to use:** Called in season loop at each GW, after transfers but before captain selection.

**Example: SUBS_PREDICTIVE_SWAP variant**

```python
# Source: Phase 8 implementation pattern (derived from auto_transfer threshold logic)
# In fpl_auto/team.py:

def auto_subs(self, strategy_config=None, bench_mode='static'):
    """
    Apply substitution logic based on bench_mode variant.
    
    Temporal rule: All xP accessed via _all_xp_dicts (multi-GW discounted).
    This is lookahead-safe because predictions were generated before GW deadline.
    """
    self.return_subs_to_team()
    
    if bench_mode == 'static':
        # Current implementation: select lowest xP players, static bench every GW
        self.make_subs(self.suggest_subs())
    
    elif bench_mode == 'predictive_swap':
        # Experimental: Swap starter for bench if bench has >15% xP advantage
        subs = self.suggest_subs()  # Get default bench
        
        for starter, starter_pos in self._all_xi_players():
            starter_xp = self._all_xp_dicts[starter_pos].get(starter, 0)
            
            # Find best bench player in this position
            bench_options = [
                (p, self._all_xp_dicts[starter_pos].get(p, 0), starter_pos)
                for p in self._pos_squad_list(starter_pos)
                if p not in self._all_xi_players()
            ]
            
            if bench_options:
                best_bench = max(bench_options, key=lambda x: x[1])
                xp_improvement = (best_bench[1] - starter_xp) / max(starter_xp, 0.1)
                
                # Trigger if bench beats starter by >15%
                if xp_improvement > 0.15 and self.gameweek > 5:
                    # Perform predictive swap
                    pass  # Implementation detail: update subs list
        
        self.make_subs(subs)
```

### Anti-Patterns to Avoid

- **Bench ordering randomness:** Never shuffle bench order randomly. Bench ordering controls auto-sub priority; randomization breaks reproducibility and makes results uninterpretable.
- **Using observed points for substitution:** Don't use actual match points (from gw_data) to decide whether to swap. This violates temporal integrity — you don't know match points until after the deadline. Use xP only.
- **Mixing bench composition with substitution:** Don't change bench composition mid-season. Isolate the two decisions: composition at GW1 (one-time), substitution logic per-GW (repeatable).
- **Over-engineering substitution triggers:** Avoid complex multi-factor heuristics (injury probability + form + fixture + rotation risk). Start with single-factor (xP improvement) and only add factors if they prove impactful.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Player position lookup | Custom position cache | `fpl_data.position_dict()` (existing) | Handles position changes, validation; custom version misses edge cases |
| Budget constraint validation | Custom squad cost calculator | `team.player_value()` + `team.transfer_in_allowed()` | Already handles position limits, club limits, squad size; duplicating risks drift |
| xP discount factor calculation | Custom multi-GW averaging | `team._get_n_gws_xp(n=5, factor=0.8)` (existing) | Proven formula from Phase 5; matches transfer xP threshold logic |
| Bench position mapping | Custom position-to-bench-slot logic | Use `MAX_PER_POS` + formation validation (existing) | Ensures legal formations automatically |

**Key insight:** FPL squad building is heavily constrained (11 starters, 4 bench, positions, price, clubs). Building these constraints from scratch invites off-by-one errors, duplicate logic, and regression. Leverage existing team.py validation.

---

## Runtime State Inventory

**Trigger:** Phase 8 is a feature extension (not a rename/refactor), so no runtime state migration needed.

**Verification:** New bench_mode and substitution_mode parameters are purely code-driven (no stored state keys, database records, or OS registrations). All state exists in:
- StrategyConfig dataclass instances (in-memory during season loop)
- Evaluation results JSON files (created fresh per run)

**Nothing found to migrate.** Phase 8 adds parameters to existing Team and StrategyConfig classes without renaming, so no data migration required.

---

## Common Pitfalls

### Pitfall 1: Bench Composition vs Substitution Coupling

**What goes wrong:** Implementing bench composition and substitution logic together, then finding it's impossible to test them independently. Result: unclear which variant drove the improvement.

**Why it happens:** Tempting to think "bench composition determines who gets selected → substitution logic determines when they play" as a single decision. But they're orthogonal: you can have safe composition + aggressive subs, or speculative composition + static subs.

**How to avoid:** 
1. Implement bench composition in `initial_team_generator()` only (runs once at GW1)
2. Implement substitution logic in `auto_subs()` (runs every GW)
3. Test bench variants with **fixed** substitution_mode='static'
4. Test substitution variants with **fixed** bench_mode='safe' (most common)
5. Only combine variants in Phase 9 if individual tests show promise

**Warning signs:** If evaluation results for "bench safe + aggressive subs" are hard to interpret, or if you find yourself explaining results as "bench and subs interact," you've coupled them.

### Pitfall 2: Temporal Leakage in Substitution Decisions

**What goes wrong:** Using single-GW xP (`_xp_dicts`) for substitution decisions that happen mid-week, then accidentally reading next-week's xP. Result: predictions include knowledge of injuries/news published after deadline.

**Why it happens:** `suggest_subs()` currently uses `_xp_dicts[pos]` (single GW xP), which is correct. But if you add multi-GW lookahead (e.g., "will this player's xP improve next GW?"), you're looking at GW(i+1) data during GW(i) decisions.

**How to avoid:**
- Substitution decisions at GW(i) can only access GW(i) predictions (trained before deadline)
- Never read GW(i+1) data in `auto_subs()`
- Use `_xp_dicts` (single GW, safe), not `_all_xp_dicts` (multi-GW lookahead, risky for subs)
- Document which xP dict each decision uses in comments
- Add a TemporalGate audit (from Requirements TI-02) to catch this automatically

**Warning signs:** If your substitution logic reads predictions/xP from gameweek > current_gameweek, or if results diverge from expectations in later seasons.

### Pitfall 3: Bench Ordering vs Bench Composition Confusion

**What goes wrong:** Implementing "bench composition" (which players are on the bench) and accidentally also changing "bench ordering" (the left-to-right priority for auto-subs). Result: substitution behavior changes unexpectedly.

**Why it happens:** In `suggest_subs()`, the 4 subs are returned in order: `[GK, DEF, DEF/MID, MID/FWD]`. If you change which players are selected, their order might change. Example: BENCH_SPECULATIVE selects younger players who happen to list differently than BENCH_SAFE.

**How to avoid:**
- Bench composition: **which** 4 players are on the bench (determined at GW1)
- Bench ordering: **how** those 4 are ordered for auto-subs (determined each GW in `suggest_subs()`)
- Keep ordering logic consistent across variants: always return `[GK, lowest_DEF, lowest_other, lowest_other]`
- Test that bench_mode='safe' with players A,B,C,D produces the same ordering as bench_mode='speculative' with players W,X,Y,Z

**Warning signs:** If changing bench_mode alters substitution patterns beyond "different players getting subbed in."

### Pitfall 4: Misinterpreting "Safe" vs "Speculative"

**What goes wrong:** Building "safe" bench as all defenders, then finding it leaves squad underbalanced (too many DEF, too few MID). Or building "speculative" bench as all cheap young players, then finding injuries crater their availability.

**Why it happens:** FPL bench is constrained. You can't just pick 4 cheap defenders — squad needs legal formation (min 3 DEF, max 3 FWD, position constraints). "Safe" doesn't mean "all defensive"; it means "diverse but predictable."

**How to avoid:**
- Define "safe" as: mixed positions (1 GK, 2 DEF, 1 MID), low variance, high experience (established clubs)
- Define "speculative" as: mixed positions, higher variance, younger talent / promoted clubs
- Document the position mix target: e.g., "BENCH_SAFE: 1 GK + 2 DEF + 1 MID. BENCH_SPECULATIVE: same."
- Test that both variants produce legal formations after auto_subs

**Warning signs:** If one variant produces invalid formations (too few GK, too many FWD), or if one variant systematically fails squad construction.

---

## Code Examples

### Example 1: Current Bench Composition (Default, No Variant)

```python
# Source: fpl_auto/team.py initial_team_generator() [VERIFIED: codebase lines 920-941]

def initial_team_generator(self):
    """Current implementation: allocates budget by ratio without explicit bench philosophy."""
    
    spending_budget = self.budget - sum(
        self.pos_size(pos) * MIN_PRICE[pos] for pos in POSITIONS
    )
    
    ratio_split = {'GK': 0.1, 'FWD': 0.2, 'MID': 0.4, 'DEF': 0.3}
    fillers = {'GK': 1, 'FWD': 1, 'MID': 2, 'DEF': 2}
    
    # Allocates: 1 GK (cheapest), 2-3 DEF, 5 MID, 3 FWD
    # For bench: selects lowest-cost valid players to fill 4 spots
    # No explicit "safe" vs "speculative" distinction
    
    for pos in ['GK', 'FWD', 'MID', 'DEF']:
        _, budget_excess = self._get_best_players(pos, pos_budget, fillers[pos])
```

**Interpretation:** Current approach minimizes bench cost (max flexibility for starters). This is implicit BENCH_SAFE (cheap = predictable). Phase 8 will make this explicit via bench_mode parameter.

### Example 2: Substitution Logic (Current Static Rotation)

```python
# Source: fpl_auto/team.py suggest_subs() [VERIFIED: codebase lines 220-248]

def suggest_subs(self):
    """Current: rotate bench based on lowest single-GW xP."""
    
    # Rank all squad players by single-GW xP (next gameweek)
    ranked_gk = sorted([[p, self._xp_dicts['GK'].get(p, 0), 'GK'] ...])
    ranked_others = sorted([[p, self._xp_dicts[pos].get(p, 0), pos] ...])
    
    # Select lowest-xP player from each position as bench
    subs = [[ranked_gk[0][0], 'GK']]
    for player in ranked_others:
        if eligible_for_bench(player):
            subs.append([player[0], player[2]])
    
    return subs
```

**Temporal safety:** Uses `_xp_dicts` (single GW xP), which are predictions generated before deadline. ✅ Correct.

**Limitations:** No substitution *trigger* — bench order is rebuilt every GW regardless of starter form/injury. Next phase can add triggers (e.g., "only swap if bench has >15% xP advantage").

### Example 3: Phase 5 Walk-Forward Integration Pattern

```python
# Source: evaluation/walk_forward.py [VERIFIED: codebase lines 21-80]

def run_strategy_on_seasons(strategy_config: StrategyConfig, seasons: List[str]):
    """Generic runner that works for any strategy (Phase 6, 7, 8 variants)."""
    
    configs = [
        {
            'season': season,
            'start_gw': 1,
            'repeat': 37,
            'starting_team': 'auto',
            'strategy': strategy_config,  # Includes bench_mode + substitution_mode
        }
        for season in seasons
    ]
    
    with Pool(processes=min(4, len(configs))) as pool:
        results = pool.map(manager.run_season, configs)
    
    return results

# Usage for Phase 8:
for bench_variant in [BENCH_SAFE, BENCH_SPECULATIVE]:
    for subs_variant in [SUBS_STATIC, SUBS_PREDICTIVE]:
        combined_config = StrategyConfig(
            transfer_mode='flexible',
            transfer_budget_per_gw=0.5,  # CONSERVATIVE_FULL (locked)
            captain_mode='highest_value',  # CAPTAIN_HIGHEST_VALUE (locked)
            chip_schedule='conservative',  # (locked)
            bench_mode=bench_variant,
            substitution_mode=subs_variant,  # NEW parameters
        )
        results = run_strategy_on_seasons(combined_config, ['2023-24'])
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static team (no subs) | Seasonal bench rotation | Phase 5 framework introduced | Unlocked ~5-10 points via active bench management |
| Random bench order | Lowest xP bench selection | Phase 5 framework | Stable substitutions; reproducible results |
| Adaptive captaincy (highest xP) | Form-based captaincy (highest_value) | Phase 7a | +12 points via stability over volatility |

**Deprecated/outdated:**
- **Reactive substitution (observed points):** Old FPL managers wait until after match to decide subs. Impossible in automated context since we decide once per GW before deadline.
- **Role-based bench (complement XI):** Outdated theory that bench should have "backup defender" and "differential forward." Modern FPL favors plugging gaps in budget.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Bench composition (GW1) and substitution logic (every GW) are orthogonal decisions and can be tested independently | Architecture Patterns | If coupled, results will confuse which variant drove improvement; need factorial design instead |
| A2 | Using `_xp_dicts` (single GW xP) for substitution decisions is temporally safe and won't cause lookahead bias | Pitfall 2 | If lookahead happens, Phase 8 results will be inflated and won't generalize |
| A3 | FPL bench archetype archetypes ("safe" = cheap + diverse, "speculative" = higher variance) map to measurable player characteristics (price, age, club tier) | Bench Composition Variants | If archetypes don't map cleanly to implementation, phase will struggle to define variants clearly |
| A4 | Current bench initialization via `_get_best_players()` can be extended with bench_mode weighting without breaking squad construction logic | Code Examples | If tight coupling exists, changes will cause squad overflow, formation violations, or budget errors |
| A5 | Phase 6-7 locked parameters (CONSERVATIVE_FULL + CAPTAIN_HIGHEST_VALUE) will remain optimal when bench/subs variants are added | User Constraints | If bench/subs changes regress transfer/captain decisions, Phase 8 may need to re-test Phase 6-7 parameters |

**Confidence:** All assumptions are LOW-MEDIUM because they're based on training knowledge + code inspection, not empirical validation. Phase 8 implementation will verify A1-A4; Phase 8 evaluation will verify A5.

---

## Open Questions

1. **Bench composition definition:** Should "safe" and "speculative" differ only in player selection (same positions), or also in position mix (e.g., 3 DEF for safety vs 1 DEF for speculative)?
   - What we know: FPL rules require min 3 DEF, max 3 FWD; current default is 2 GK, 5 DEF, 5 MID, 3 FWD
   - What's unclear: Whether bench should follow same ratio or diverge (e.g., safe bench = all DEF/GK, speculative = all MID/FWD)
   - Recommendation: Keep position mix constant; vary only player archetypes (cheap vs high-variance within each position)

2. **Substitution trigger threshold:** Is 15% xP improvement the right bar for SUBS_PREDICTIVE_SWAP?
   - What we know: Transfer logic uses 20% threshold (tuned in Phase 6); captain logic uses variance penalty (Phase 7)
   - What's unclear: Whether subs should use same 20%, lower (5-10%), or higher (30%+)
   - Recommendation: Start with 20% (matching transfer logic), then research 10% and 30% variants in Phase 9 if Phase 8 is promising

3. **Substitution timing:** Should subs happen before or after captain selection?
   - What we know: Current code calls `auto_subs()` before `auto_captain()` (line 133-134 in manager.py)
   - What's unclear: Whether swapping a bench player in changes captain selection (if new player has higher captaincy score)
   - Recommendation: Keep current order (subs → captain). Captain decision sees the updated lineup.

4. **Bench boost interaction:** Does SUBS_PREDICTIVE_SWAP affect bench boost value?
   - What we know: Bench boost multiplies all bench player points by 2; current logic calculates bench_xp = all_xp - xi_xp
   - What's unclear: Whether predictive swaps should recompute bench xP for boost decisions
   - Recommendation: Don't couple bench boost logic to substitution variants. Test independently in Phase 9.

---

## Environment Availability

**Step 2.6 Result:** No external dependencies beyond those already verified in Phase 5.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All code | ✓ | 3.10 (verified in CLAUDE.md) | — |
| pandas | Data loading | ✓ | 1.x (verified in codebase) | — |
| numpy | xP calculations | ✓ | 1.x (verified in codebase) | — |
| sklearn | Model predictions | ✓ | 0.24+ (verified in codebase) | — |
| unittest | Testing | ✓ | stdlib | — |
| Data files | Prediction TSVs | ✓ | 2023-24, 2024-25 available | Skip season if missing |

**Missing dependencies:** None. Phase 8 requires no new external tools.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (Phase 5 established pattern) |
| Config file | tests.py (extended with bench/subs tests) |
| Quick run command | `python -m unittest tests.TestBench* -v` (estimated <5s) |
| Full suite command | `python -m unittest tests -v` (estimated <30s) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BS-01 | Bench composition variants implemented (BENCH_SAFE, BENCH_SPECULATIVE) | unit | `python -m unittest tests.TestBenchComposition -v` | ❌ Wave 0 |
| BS-02 | Substitution logic variants implemented (SUBS_STATIC, SUBS_PREDICTIVE_SWAP) | unit | `python -m unittest tests.TestSubstitutionLogic -v` | ❌ Wave 0 |
| BS-03 | All variants tested with walk-forward validation | integration | `python evaluation/compare_bench_variants.py` (creates variant_results_8.json) | ❌ Wave 0 |
| BS-04 | Results compared against baselines (non-overlapping 95% CIs) | integration | `python evaluation/compare_bench_variants.py` (outputs stats summary) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m unittest tests.TestBench* tests.TestSubstitution* -v` (verify unit tests pass after each task)
- **Per wave merge:** `python -m unittest tests -v` (full test suite before evaluation)
- **Phase gate:** Walk-forward evaluation complete with 95% CIs and Bonferroni correction before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests.TestBenchComposition` — test bench_mode parameter in StrategyConfig; test bench composition variants don't violate squad constraints
- [ ] `tests.TestSubstitutionLogic` — test substitution_mode parameter; test SUBS_PREDICTIVE_SWAP trigger logic; test temporal safety (no lookahead)
- [ ] `tests.TestBenchIntegration` — test that bench composition persists across GW loop without corruption
- [ ] `evaluation/compare_bench_variants.py` — walk-forward orchestration script (similar structure to Phase 6-7 compare_*.py scripts)
- [ ] Conftest fixtures (if needed) — shared test data for bench scenarios

*(If no gaps needed after implementation: record "None — existing test infrastructure sufficient")*

---

## Security Domain

### Applicable ASVS Categories

**Trigger:** Phase 8 is pure algorithmic (no external API, no user input, no network calls). No ASVS categories apply.

| ASVS Category | Applies | Rationale |
|---------------|---------|-----------|
| V2 Authentication | No | No user authentication; squad data is internal only |
| V3 Session Management | No | No session handling |
| V4 Access Control | No | No access control needed (single-user simulated environment) |
| V5 Input Validation | No | All inputs (StrategyConfig) are internally generated; no external user input |
| V6 Cryptography | No | No sensitive data requiring encryption |

**Verification:** Phase 8 adds parameters to existing StrategyConfig dataclass, which already validates all inputs in `__post_init__()`. No new security-relevant code paths introduced.

---

## Sources

### Primary (HIGH confidence)
- **Codebase inspection** — Current team.py suggest_subs() and initial_team_generator() implementations [VERIFIED: fpl_auto/team.py lines 220-248, 920-941]
- **Strategy framework** — StrategyConfig dataclass and Phase 6-7 patterns [VERIFIED: fpl_auto/strategies.py, evaluation/walk_forward.py]
- **Phase 7 execution** — Captain and chip variant structure showing 2×2 and 3×2 factorial designs [VERIFIED: .planning/phases/07-captain-chip-evaluation/EXECUTION-REPORT.md]

### Secondary (MEDIUM confidence)
- [FPL Official: Best budget defenders for 2024/25](https://www.premierleague.com/en/news/4077017)
- [FPL Official: Best budget players for your bench](https://www.premierleague.com/en/news/4463797/who-are-the-best-budget-players-for-your-bench-in-fantasy)
- [FPL Toolbox: Bench sorting strategies](https://fpltoolbox.com/blog/getting-the-most-out-of-auto-subs-how-to-sort-your-fpl-bench-like-a-pro)
- [Ingenuity Fantasy: How substitutions work in FPL](https://ingenuityfantasy.com/fantasy-fundamentals/how-do-fantasy-premier-league-subs-work/)
- [Fantasy Football First: Substitution rules](https://fantasyfootballfirst.co.uk/how-do-substitutions-work-in-fpl/)

### Tertiary (LOW confidence, marked for validation)
- Bench point utilization statistics (searched but not found in authoritative sources; anecdotal from community sources only)
- Optimal bench order percentile impact (no published research; based on coach intuition)

---

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — All tools verified in codebase; no new dependencies needed
- **Architecture patterns:** HIGH — Current implementation examined; Phase 5-7 patterns reused
- **Bench composition variants:** MEDIUM — FPL community consensus on "safe vs speculative" is clear, but exact implementation thresholds unverified
- **Substitution logic variants:** MEDIUM — Threshold logic derived from Phase 6 transfer patterns, but substitution-specific impact untested
- **Temporal safety:** HIGH — Current code uses correct `_xp_dicts`; risks identified and documented
- **Pitfalls:** MEDIUM-HIGH — Identified from codebase patterns and FPL literature; not all verified in Phase 8 implementation yet

**Research date:** 2026-05-28  
**Valid until:** 2026-06-28 (1 month; FPL player prices/form shift frequently, but core patterns stable)

---

## Next Steps for Planner

1. **Define bench variants explicitly:**
   - BENCH_SAFE: 1 GK (cheapest), 2 DEF (4.0-4.5m), 1 MID (4.5m) — focus on price, clean sheet probability
   - BENCH_SPECULATIVE: same positions, but select from high-variance xP players, younger/promoted club players
   - Validate both produce legal squads with realistic costs

2. **Define substitution variants explicitly:**
   - SUBS_STATIC: Current implementation (rebuild bench by lowest xP every GW)
   - SUBS_PREDICTIVE_SWAP: Trigger swap if bench player has >20% xP improvement vs starter (start conservative with Phase 6's threshold, adjust if needed)
   - Validate both are temporally safe

3. **Test matrix design:**
   - Recommend: 2×2 nested design = 4 variants total (BENCH_SAFE + SUBS_STATIC, BENCH_SAFE + SUBS_PREDICTIVE, BENCH_SPECULATIVE + SUBS_STATIC, BENCH_SPECULATIVE + SUBS_PREDICTIVE)
   - Lock Phase 6-7 parameters: CONSERVATIVE_FULL transfer + CAPTAIN_HIGHEST_VALUE
   - Run walk-forward on 2023-24 (test) with 2021-22, 2022-23 (train)

4. **Evaluation structure:**
   - Reuse Phase 5 walk-forward framework (no new infrastructure needed)
   - Capture metrics: total points, Sharpe, Sortino, bench utilization %, points left on bench
   - Apply 95% bootstrapped CIs with Bonferroni correction (α = 0.0125 for 4 comparisons)
   - Compare against BASELINE_CURRENT (Phase 7 optimal): 1817 points on 2023-24

5. **Recommend Phase 8 success criteria:**
   - BS-01, BS-02: Implement 2 bench + 2 subs variants in team.py, strategies.py
   - BS-03: Run walk-forward evaluation on 4-variant matrix
   - BS-04: Report non-overlapping 95% CIs vs baseline; document results with per-season breakdown
   - Expected outcome: At least one variant outperforms BASELINE_CURRENT by >5 points (statistically significant)

---

**End of Research**
