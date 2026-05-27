# Temporal Integrity Architecture

## Executive Summary

Temporal integrity in FPL-Auto backtesting enforces a critical rule: **strategies may only access data available at their decision point**. This document specifies what data is accessible when, implements the `TemporalGate` enforcement mechanism, and provides testing patterns to prevent lookahead bias bugs before code review. Without these boundaries, strategies can artificially improve scores by "cheating" — reading future form, price changes, and injury news that occurred after the decision deadline.

---

## Data Availability Timeline

The following table shows when key data points become available to the strategy, relative to the gameweek deadline (90 minutes before the first match):

| Data Point | Release Time | Available During GW(N) Decision? | Reference |
|---|---|---|---|
| **Fixture list (full season)** | Pre-season (August 1) | ✅ Yes (fixed pre-season) | TEMPORAL_INTEGRITY.md § 1 |
| **Historical player form** | After each match (~4 hours after match) | ✅ Only GW(1..N-1) form available | TEMPORAL_INTEGRITY.md § 1 |
| **Current player price** | 2:30am UTC daily | ✅ Today's prices (from previous day's update) | TEMPORAL_INTEGRITY.md § 1 |
| **Injury news & updates** | Continuously (press, official sources) | ❌ Future injuries are unknown | TEMPORAL_INTEGRITY.md § 1 |
| **Gameweek points (actual)** | ~2 hours after match ends | ❌ Not available during GW(N) decision | TEMPORAL_INTEGRITY.md § 1 |
| **Pre-trained predictions** | Before season run (generated overnight GW-1 to GW0) | ✅ Only GW(N) predictions ready | model.py § Training boundaries |

**Critical principle:** Data is either "stale by design" (historical form shows what happened, not what will), or "future-proof" (fixtures/prices are fixed).

---

## Safe Access Contracts

### Before GW(N) Deadline (Decision Phase)

**When:** Strategy is deciding transfers, captain, chips for the upcoming gameweek.  
**Locked data:** The decision gameweek is immutable. No lookahead.

**Safe to read (✅):**
- Historical player form: GW(1) through GW(N-1) only
- Pre-trained predictions for GW(N): one-week-ahead model outputs
- Fixture metadata: opponent, difficulty rating, home/away status (all gameweeks)
- Player prices: current prices (locked at previous day's 2:30am UTC update)
- Team composition and squad constraints: current squad state

**NOT safe to read (❌):**
- Gameweek N actual points: not available until 2 hours after final match
- Gameweek N+1 or later form data: future results unknown
- Injury news after deadline: future injuries are unpredictable
- Price changes after decision time: future prices unknown
- Gameweek N team sheets (which players actually play): announced after deadline

### After GW(N) Matches Complete (Scoring Phase)

**When:** Season loop has called `team.team_p()` and collected results, moving to GW(N+1).  
**Locked data:** Historical form for GW(N) is now complete and fixed.

**Safe to read (✅):**
- Actual points scored in GW(N): now observable, used for performance tracking
- Updated player form including GW(N): available for next decision
- Price changes post-deadline: now finalized
- Fixture metadata: unchanged

**NOT safe to read (❌):**
- Gameweek N+2 or later form: future unknowable
- Any predictions used for decisions: must be pre-trained only

---

## Implementation: TemporalGate Class

The `TemporalGate` class (`fpl_auto/temporal.py`) enforces temporal boundaries at the call site. Every data access is logged and checked against the decision gameweek.

### Methods

```python
class TemporalGate:
    def __init__(self, season: str, decision_gameweek: int)
    def safe_read_historical_form(self, target_gw: int) -> bool
    def safe_read_predictions(self, target_gw: int) -> bool
    def safe_read_fixture_metadata(self) -> bool
    def audit_trail(self) -> list
```

**`safe_read_historical_form(target_gw: int) -> bool`**
- **Rule:** `target_gw < decision_gameweek`
- **Raises:** `TemporalViolationError` if target_gw >= decision_gameweek
- **Use case:** Team.__init__ calls to `fpl.get_gw_data(target_gw)` for historical player stats
- **Example:** During GW10 decisions, only GW1-9 form available

**`safe_read_predictions(target_gw: int) -> bool`**
- **Rule:** `target_gw == decision_gameweek`
- **Raises:** `TemporalViolationError` if target_gw != decision_gameweek
- **Use case:** Team.__init__ calls to `fpl.get_predictions(target_gw, position)` for expected points
- **Example:** During GW10 decisions, only GW10 predictions available (generated overnight)

**`safe_read_fixture_metadata() -> bool`**
- **Rule:** Always allowed
- **Returns:** True (no violations possible)
- **Use case:** Fixture opponent, difficulty, home/away lookups
- **Example:** Fixture data is fixed at season start; safe to read at any time

**`audit_trail() -> list`**
- **Returns:** List of tuples: `(data_type, accessed_gw, decision_gw, allowed: bool)`
- **Use case:** Debugging temporal violations; understanding access patterns
- **Example:** `[('historical_form', 5, 10, True), ('predictions', 11, 10, False)]`

### Integration Example (Phase 2)

Once Team class is updated to use TemporalGate, data access will be guarded:

```python
class Team:
    def __init__(self, season, gameweek, ...):
        self.gate = TemporalGate(season, gameweek)
        
        # ✅ Safe: historical form for previous gameweeks
        for gw in range(1, gameweek):
            if self.gate.safe_read_historical_form(gw):
                data = fpl.get_gw_data(season, gw)
        
        # ✅ Safe: predictions for current gameweek
        if self.gate.safe_read_predictions(gameweek):
            self.gk_xp = fpl.get_predictions(gameweek, 'GK')
        
        # ✅ Safe: fixture metadata always
        if self.gate.safe_read_fixture_metadata():
            self.fixture_difficulty = fpl.get_fixture_difficulty(gameweek)
```

If code attempts `gate.safe_read_predictions(gameweek + 1)`, a `TemporalViolationError` is raised immediately with a clear message:

```
TemporalViolationError: Trying to access GW11 predictions during decision for GW10. Only GW10 available.
```

---

## Testing Strategy

Four automated tests in `tests.py` (`TestTemporalIntegrity` class) verify temporal enforcement:

### Test 1: `test_temporal_gate_blocks_future_historical_data()`
**Verifies:** Historical form access is strictly past-only.
- Instantiate `TemporalGate('2023-24', decision_gameweek=10)`
- ✅ `safe_read_historical_form(9)` succeeds (past)
- ❌ `safe_read_historical_form(11)` raises `TemporalViolationError` (future)
- Assert error message includes "GW11" and "GW10" for debugging

**Coverage:** Prevents lookahead bias from reading future player form.

### Test 2: `test_temporal_gate_only_allows_current_predictions()`
**Verifies:** Predictions access is exact-gameweek only (no past or future).
- Instantiate `TemporalGate('2023-24', decision_gameweek=10)`
- ✅ `safe_read_predictions(10)` succeeds (current)
- ❌ `safe_read_predictions(11)` raises error (future)
- ❌ `safe_read_predictions(9)` raises error (past; predictions not pre-generated)

**Coverage:** Prevents using stale predictions or future-trained models.

### Test 3: `test_temporal_gate_fixtures_always_safe()`
**Verifies:** Fixture metadata has no temporal restrictions.
- Instantiate `TemporalGate('2023-24', decision_gameweek=5)`
- ✅ `safe_read_fixture_metadata()` returns True unconditionally

**Coverage:** Confirms fixture data (known pre-season) has no lookahead bias risk.

### Test 4: `test_audit_trail_logs_all_accesses()`
**Verifies:** Audit trail captures all access attempts including violations.
- Instantiate `TemporalGate('2023-24', decision_gameweek=15)`
- Make 3 access calls: successful, successful, violation
- Call `audit_trail()`
- Assert 3 entries with format: `(data_type, accessed_gw, decision_gw, allowed: bool)`
- Verify third entry has `allowed=False`

**Coverage:** Debugging tool to understand access patterns and catch violations in logs.

### Audit Trail Output Example

```python
gate = TemporalGate('2023-24', decision_gameweek=10)
gate.safe_read_historical_form(8)      # ✅ OK
gate.safe_read_historical_form(9)      # ✅ OK
gate.safe_read_predictions(10)         # ✅ OK
try:
    gate.safe_read_historical_form(11) # ❌ Violation
except TemporalViolationError:
    pass

print(gate.audit_trail())
# [('historical_form', 8, 10, True),
#  ('historical_form', 9, 10, True),
#  ('predictions', 10, 10, True),
#  ('historical_form', 11, 10, False)]
```

The audit trail is human-readable and actionable for debugging: immediately see what was accessed, when, and whether it violated boundaries.

---

## Critical Boundaries Enforced

### Model Training Boundary (model.py, lines 56-61)

**Rule:** Train models using data strictly before the target gameweek's deadline.

```python
# Correct: train on GW(i-20) to GW(i-1), predict for GW(i)
training_data, test_data = vastaav.get_training_data_all(
    season, 
    i - training_prev_weeks - 1,  # Start: GW(i-20)
    i - 1                          # End: GW(i-1)
)
predictor.fit(training_data)
predictions_for_gw_i = predictor.predict(test_data)  # GW(i) only
```

**Why:** If training includes GW(i), the model learns "by looking at the answer" — overfitting to information available after the GW(i) decision deadline. This inflates backtested performance.

**Enforcement:** `model.py` line 58 correctly uses `i - training_prev_weeks - 1` to `i - 1` (not including `i`).

### Historical Form Boundary (Team.__init__, lines 57-79)

**Rule:** During GW(N) decisions, read form only for GW(1) through GW(N-1).

```python
# Example: reading GW data during GW10 decision
gw9_form = fpl.get_gw_data(season, 9)  # ✅ OK
gw10_form = fpl.get_gw_data(season, 10) # ❌ Violation (current GW)
gw11_form = fpl.get_gw_data(season, 11) # ❌ Violation (future)
```

**Why:** Current gameweek's form is not yet determined at decision time. Future form is unknowable.

**Enforcement:** Phase 2 will add `gate.safe_read_historical_form(target_gw)` check before `fpl.get_gw_data()`.

### Predictions Boundary (Team.__init__, lines 57-79)

**Rule:** Predictions are pre-trained for GW(N) before the season run; only GW(N) available during GW(N) decision.

```python
# Example: reading predictions during GW10 decision
gk_xp = fpl.get_predictions(10, 'GK')  # ✅ OK (current GW)
gk_xp = fpl.get_predictions(9, 'GK')   # ❌ Violation (past; not pre-trained)
gk_xp = fpl.get_predictions(11, 'GK')  # ❌ Violation (future; not pre-trained)
```

**Why:** Predictions are one-shot per gameweek (trained before deadline). Using future predictions = accidentally learning the answer.

**Enforcement:** Phase 2 will add `gate.safe_read_predictions(target_gw)` check before `fpl.get_predictions()`.

### Fixture Data Boundary (Manager-wide)

**Rule:** Fixture metadata is fixed at season start and safe at any time.

```python
# Always OK, at any decision time
fixture_difficulty = fpl.get_fixture_difficulty(season, any_gw)
opponent = fpl.get_opponent(season, any_gw)
home_away = fpl.get_home_away(season, any_gw)
```

**Why:** Fixtures don't change; they're published pre-season and never updated.

**Enforcement:** Phase 2 will add `gate.safe_read_fixture_metadata()` check for all fixture reads (will always pass).

---

## Violations & Recovery

### When a Violation Occurs

If code attempts to violate boundaries, `TemporalViolationError` is raised immediately:

```
TemporalViolationError: Trying to access GW11 historical_form during decision for GW10. 
Only GW1-9 available.
```

**Action needed:**
1. Read the error message: identifies the data type, target GW, decision GW, and allowed range
2. Understand why: Is this accessing future data? Using stale predictions? Reading mid-deadline data?
3. Fix the code: Move the read to the correct gameweek or phase (decision vs scoring)

### Common Mistakes to Avoid

| Mistake | Wrong Code | Correct Code | Why |
|---------|-----------|--------------|-----|
| Predictions from wrong GW | `get_predictions(10, 'GK')` during GW11 | `get_predictions(11, 'GK')` during GW11 | Predictions are pre-trained; one per GW |
| Including current GW in history | `for gw in range(1, current_gw+1)` | `for gw in range(1, current_gw)` | Current GW not yet complete |
| Reading future form | `get_gw_data(gw=20)` during GW5 | `get_gw_data(gw)` for gw in 1..4 | Future form is unknown |
| Training on current GW | `train_on(i-19, i)` for GW i | `train_on(i-20, i-1)` for GW i | Avoid learning the answer |
| Discounting beyond available | Multi-GW lookahead with undefined later GWs | Only lookahead 5 GWs on defined future (fixtures, pre-predictions) | Real future data doesn't exist yet |

### Reading Audit Trail for Debugging

When a violation is caught in testing, examine the audit trail:

```python
gate.audit_trail()
# [('historical_form', 5, 10, True),
#  ('predictions', 10, 10, True),
#  ('historical_form', 15, 10, False)]  ← This is the violation
```

**Column meanings:**
- **data_type:** What was accessed (historical_form, predictions, fixture_metadata)
- **accessed_gw:** The specific gameweek requested
- **decision_gw:** The current decision context (immutable)
- **allowed:** True if within bounds, False if violation

The violation entry shows exactly when the boundary was crossed, enabling rapid fix.

---

## Integration Roadmap

**Phase 1 (Complete):**
- ✅ TemporalGate class created (fpl_auto/temporal.py)
- ✅ Model training boundary verified (model.py line 58)
- ✅ Automated tests for enforcement (tests.py TestTemporalIntegrity)
- ✅ Architecture documentation (this file)

**Phase 2 (Upcoming):**
- Team.__init__ wraps FplData calls with TemporalGate checks
- All data access guarded: safe_read_historical_form, safe_read_predictions, safe_read_fixture_metadata
- Audit trail available for debugging if needed

**Phase 3+ (Post-integration):**
- Continuous testing via CI (run unittest suite on every commit)
- Monitor audit trails in production backtest logs
- Catch new violations early before they inflate performance metrics

---

## Reference

- **TemporalGate class:** `fpl_auto/temporal.py` (71 lines)
- **Test suite:** `tests.py`, class `TestTemporalIntegrity` (4 tests, 85 lines)
- **Research:** `.planning/research/TEMPORAL_INTEGRITY.md`
- **Architecture verification:** fpl_auto/data.py (caching), model.py (training), team.py (predictions)
