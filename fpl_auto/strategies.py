"""
Strategy Configuration System for FPL Automation

Defines StrategyConfig dataclass and five preset strategy archetypes for
systematic comparison and evaluation of different team management approaches.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StrategyConfig:
    """
    Complete FPL strategy configuration with interpretable parameters.

    All parameters have sensible defaults that represent a balanced approach.
    Validation in __post_init__ ensures all parameter choices are valid.
    """

    # Transfer policy
    transfer_mode: str = 'flexible'
    """
    Transfer strategy mode:
    - 'never': No transfers made during season (static squad)
    - 'flexible': Adaptive transfers based on form/injuries (1 per GW typical)
    - 'greedy': Aggressive transfers chasing points (up to 2 per GW)
    """

    max_transfers_per_gw: int = 1
    """
    Maximum number of transfers allowed per gameweek (0-2).
    Controls how aggressively to swap players.
    """

    transfer_discount_factor: float = 0.8
    """
    Discount factor for multi-GW lookahead in transfer decisions (0.6-1.0).
    Lower values (0.6) discount future GWs more, favoring immediate gain.
    Higher values (1.0) weight all future GWs equally.
    """

    transfer_budget_per_gw: float = 1.5
    """
    Points-per-GW budget for transfers (0.0-10.0, default 1.5).
    Semantics: Maximum total xP gain budget allowed per gameweek.
    Reset each GW; cumulative xP gain within a GW cannot exceed this.
    Examples: 0.5 = conservative, 1.5 = baseline, 2.0 = aggressive.
    """

    transfer_window_gw_range: Optional[tuple] = None
    """
    Restrict transfers to GW range [start, end] inclusive (default: None = full season).
    Examples: (1, 10) for early season, (11, 24) for mid, (25, 38) for late.
    None means transfers allowed in entire season (subject to GW > 35 hard stop).
    """

    transfer_xp_threshold: float = 0.15
    """
    Threshold for transfer trigger (default 0.15).
    When transfer_xp_threshold_mode='relative': (new_xp - old_xp) / old_xp > threshold
    When transfer_xp_threshold_mode='absolute': (new_xp - old_xp) >= threshold
    Range: [0.0, 1.0] for relative; [0.0, 50.0] for absolute.
    """

    transfer_xp_threshold_mode: str = 'relative'
    """
    How to interpret transfer_xp_threshold (default 'relative').
    Options: 'relative' | 'absolute'
    'relative': percentage improvement; 0.20 = 20% better required
    'absolute': points improvement; 4.0 = at least 4 points better
    """

    # Captaincy policy
    captain_mode: str = 'highest_xp'
    """
    Captaincy selection mode:
    - 'highest_xp': Captain the player with highest expected points next GW
    - 'highest_value': Captain the highest-priced player (stable points)
    - 'form_based': Captain based on recent performance (contrarian/differential)
    """

    captain_lookback_gws: int = 1
    """
    Number of recent gameweeks to analyze for captain form (1-5).
    Higher values smooth out noise; lower values favor recent hot streaks.
    """

    captain_variance_penalty: float = 0.0
    """
    Penalty applied to high-variance players in captain selection (-0.2 to 0.5).
    Positive values penalize volatile players (prefer consistency).
    Negative values prefer contrarian/volatile picks (differential strategy).
    """

    # Chip usage policy
    chip_schedule: str = 'conservative'
    """
    Chip usage strategy:
    - 'never': Never use chips (preserve for defense against regression)
    - 'conservative': Use chips sparingly when conditions are favorable
    - 'aggressive': Use all chips proactively to maximize points
    - 'doubles-optimized': Activate chips around DOUBLE gameweeks (Phase 7)
    - 'blanks-optimized': Activate chips around BLANK gameweeks (Phase 7)
    """

    wildcard_threshold_points: float = 60.0
    """
    Threshold for wildcard usage (30-80).
    Use wildcard if gap between current squad xP and optimal squad > threshold.
    Lower values = more frequent wildcards; higher values = rare/selective use.
    """

    chip_budget_limit: int = 3
    """
    Maximum number of chips to use across season (0-3).
    Controls overall chip spending (0=never, 3=use all available).
    """

    chip_triple_captain_earliest_gw: int = 20
    """
    Earliest GW to activate Triple Captain (default 10).
    Prevents using TC in the first weeks before double GW opportunities emerge.
    """

    chip_bench_boost_earliest_gw: int = 25
    """
    Earliest GW to activate Bench Boost (default 15).
    Prevents using BB before mid-season double GW opportunities.
    """

    # Initial team selection algorithm
    initial_team_algorithm: str = 'greedy'
    """
    Algorithm for initial squad selection (used at GW1, free hit, wildcard).
    - 'greedy': Two-tier greedy — premium slots by raw xP, fillers by cheapest ≤£6m (default)
    - 'two_tier': Premium slots by raw xP, filler slots by xP/£m ratio
    - 'ilp_xp': ILP maximising total xP (hard budget constraint)
    - 'ilp_ratio': ILP maximising total xP/cost ratio
    - 'ilp_penalised': ILP maximising xP − λ·cost (soft budget penalty, see ilp_lambda)
    - 'ilp_captain': ILP with captain double-counted in objective
    - 'rolling_horizon': Greedy on summed xP from next N prediction files (see ilp_rolling_weeks)
    """

    ilp_lambda: float = 2.0
    """
    Cost-penalty coefficient for 'ilp_penalised' algorithm (default 2.0).
    Objective: maximise Σ(xP_i - lambda * cost_i) * x_i.
    Higher values penalise expensive players more (preserves more budget).
    Sweep [0, 5] to tune; 0 = pure xP ILP, higher = more budget-conscious.
    """

    ilp_rolling_weeks: int = 4
    """
    Number of future prediction files to sum for 'rolling_horizon' algorithm (default 4).
    Reads GW, GW+1, ..., GW+n-1 prediction TSVs and sums xP column-wise.
    """

    rolling_horizon_discount: float = 1.0
    """
    Per-week discount factor for 'rolling_horizon' algorithm (default 1.0 = no discount).
    Week offset i is weighted by discount^i: 1.0, d, d², d³, ...
    Values <1.0 down-weight far-future GWs (e.g. 0.8 matches the main xP discount).
    """

    # Bench policy
    bench_mode: str = 'rotate_low_xp'
    """
    Bench rotation strategy:
    - 'static': Keep same bench players throughout season
    - 'rotate_low_xp': Rotate bench based on next GW xP (play lowest xP players)
    - 'fixture_aware': Rotate based on fixture difficulty
    """

    bench_injury_threshold: float = 0.5
    """
    Injury/fixture tolerance for bench decisions (0.0-1.0).
    Proportion of unavailable players triggering forced rotation.
    """

    # Risk parameters
    position_variance_tolerance: float = 1.0
    """
    Tolerance for position variance (0.8-1.5).
    Controls how much to overweight good players relative to position constraints.
    < 1.0: Conservative (spread risk across positions)
    > 1.0: Aggressive (concentrate in best positions)
    """

    punt_threshold: float = 0.5
    """
    Minimum acceptable xP to keep a player on team (0.0-2.0).
    Players below this threshold are considered for transfer out.
    Lower values = more aggressive; higher values = more conservative.
    """

    bench_composition_variant: str = 'safe'
    """
    Bench composition philosophy:
    - 'safe': Cheap, experienced players (4.0-4.5m price range, established clubs)
    - 'speculative': Higher-variance, younger players (same price, different archetypes)
    - 'balanced': Mixed strategy (Phase 9 extension)
    """

    substitution_mode: str = 'static'
    """
    Substitution trigger strategy:
    - 'static': Rebuild bench by lowest xP every GW (current behavior)
    - 'predictive_swap': Swap starter for bench if bench has >threshold% xP advantage
    """

    substitution_trigger_threshold: float = 0.20
    """
    Threshold for predictive_swap mode (0.0-1.0).
    Swap if bench_xp > starter_xp * (1 + threshold).
    Default 0.20 = 20% advantage required (matches Phase 6 transfer threshold).
    Ignored if substitution_mode='static'.
    """

    def __post_init__(self):
        """Validate all parameters after initialization."""

        # Transfer policy validation
        if self.transfer_mode not in ['never', 'flexible', 'greedy']:
            raise ValueError(
                f"transfer_mode must be 'never', 'flexible', or 'greedy', got {self.transfer_mode}"
            )

        if not (0 <= self.max_transfers_per_gw <= 2):
            raise ValueError(
                f"max_transfers_per_gw must be 0-2, got {self.max_transfers_per_gw}"
            )

        if not (0.6 <= self.transfer_discount_factor <= 1.0):
            raise ValueError(
                f"transfer_discount_factor must be 0.6-1.0, got {self.transfer_discount_factor}"
            )

        # Captaincy policy validation
        if self.captain_mode not in ['highest_xp', 'highest_value', 'form_based']:
            raise ValueError(
                f"captain_mode must be 'highest_xp', 'highest_value', or 'form_based', "
                f"got {self.captain_mode}"
            )

        if not (1 <= self.captain_lookback_gws <= 5):
            raise ValueError(
                f"captain_lookback_gws must be 1-5, got {self.captain_lookback_gws}"
            )

        if not (-0.2 <= self.captain_variance_penalty <= 0.5):
            raise ValueError(
                f"captain_variance_penalty must be -0.2 to 0.5, "
                f"got {self.captain_variance_penalty}"
            )

        # Chip usage policy validation
        if self.chip_schedule not in ['never', 'conservative', 'aggressive', 'doubles-optimized', 'blanks-optimized']:
            raise ValueError(
                f"chip_schedule must be 'never', 'conservative', 'aggressive', "
                f"'doubles-optimized', or 'blanks-optimized', got {self.chip_schedule}"
            )

        if not (30 <= self.wildcard_threshold_points <= 80):
            raise ValueError(
                f"wildcard_threshold_points must be 30-80, "
                f"got {self.wildcard_threshold_points}"
            )

        if not (0 <= self.chip_budget_limit <= 3):
            raise ValueError(
                f"chip_budget_limit must be 0-3, got {self.chip_budget_limit}"
            )

        # Bench policy validation
        if self.bench_mode not in ['static', 'rotate_low_xp', 'fixture_aware']:
            raise ValueError(
                f"bench_mode must be 'static', 'rotate_low_xp', or 'fixture_aware', "
                f"got {self.bench_mode}"
            )

        if not (0.0 <= self.bench_injury_threshold <= 1.0):
            raise ValueError(
                f"bench_injury_threshold must be 0.0-1.0, got {self.bench_injury_threshold}"
            )

        # Risk parameters validation
        if not (0.8 <= self.position_variance_tolerance <= 1.5):
            raise ValueError(
                f"position_variance_tolerance must be 0.8-1.5, "
                f"got {self.position_variance_tolerance}"
            )

        if not (0.0 <= self.punt_threshold <= 2.0):
            raise ValueError(
                f"punt_threshold must be 0.0-2.0, got {self.punt_threshold}"
            )

        # Transfer budget/window/threshold validation (new parameters)
        if self.transfer_budget_per_gw <= 0:
            raise ValueError(
                f"transfer_budget_per_gw must be > 0, got {self.transfer_budget_per_gw}"
            )

        if self.transfer_window_gw_range is not None:
            start, end = self.transfer_window_gw_range
            if not (1 <= start <= 38 and 1 <= end <= 38):
                raise ValueError(
                    f"transfer_window_gw_range bounds must be in [1, 38], "
                    f"got ({start}, {end})"
                )
            if start > end:
                raise ValueError(
                    f"transfer_window_gw_range start must be <= end, "
                    f"got ({start}, {end})"
                )

        if self.transfer_xp_threshold_mode not in ('relative', 'absolute'):
            raise ValueError(
                f"transfer_xp_threshold_mode must be 'relative' or 'absolute', "
                f"got {self.transfer_xp_threshold_mode}"
            )

        if self.transfer_xp_threshold_mode == 'relative':
            if not (0.0 <= self.transfer_xp_threshold <= 1.0):
                raise ValueError(
                    f"transfer_xp_threshold with mode='relative' must be [0.0, 1.0], "
                    f"got {self.transfer_xp_threshold}"
                )
        else:  # absolute mode
            if self.transfer_xp_threshold < 0:
                raise ValueError(
                    f"transfer_xp_threshold with mode='absolute' must be >= 0, "
                    f"got {self.transfer_xp_threshold}"
                )

        # Bench composition policy validation (NEW)
        if self.bench_composition_variant not in ['safe', 'speculative', 'balanced']:
            raise ValueError(
                f"bench_composition_variant must be 'safe', 'speculative', or 'balanced', "
                f"got {self.bench_composition_variant}"
            )

        if self.substitution_mode not in ['static', 'predictive_swap']:
            raise ValueError(
                f"substitution_mode must be 'static' or 'predictive_swap', "
                f"got {self.substitution_mode}"
            )

        if not (0.0 <= self.substitution_trigger_threshold <= 1.0):
            raise ValueError(
                f"substitution_trigger_threshold must be 0.0-1.0, "
                f"got {self.substitution_trigger_threshold}"
            )

        _valid_algorithms = {'greedy', 'two_tier', 'ilp_xp', 'ilp_ratio', 'ilp_penalised', 'ilp_captain', 'rolling_horizon'}
        if self.initial_team_algorithm not in _valid_algorithms:
            raise ValueError(
                f"initial_team_algorithm must be one of {_valid_algorithms}, "
                f"got {self.initial_team_algorithm}"
            )

        if self.ilp_lambda < 0:
            raise ValueError(f"ilp_lambda must be >= 0, got {self.ilp_lambda}")

        if not (1 <= self.ilp_rolling_weeks <= 10):
            raise ValueError(f"ilp_rolling_weeks must be 1-10, got {self.ilp_rolling_weeks}")

        if not (0.0 < self.rolling_horizon_discount <= 1.0):
            raise ValueError(f"rolling_horizon_discount must be in (0, 1], got {self.rolling_horizon_discount}")


# BASELINE STRATEGIES (for comparison and validation)

BASELINE_STATIC = StrategyConfig(
    # Philosophy: Do nothing. Pick a team at GW1 and hold until end of season.
    # Establishes minimum baseline: if xP-informed strategy can't beat static, something is broken.
    transfer_mode='never',
    max_transfers_per_gw=0,
    captain_mode='highest_value',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='never',
    chip_budget_limit=0,
    bench_mode='static',
    bench_injury_threshold=1.0,
    position_variance_tolerance=1.0,
    punt_threshold=1.0,
)

BASELINE_CURRENT = StrategyConfig(
    # Philosophy: Phase 6-8 optimal strategy (CONSERVATIVE_FULL + BENCH_SAFE_STATIC).
    # Empirically validated across all seasons (2021-22, 2022-23, 2023-24): top performer.
    # Transfer: Budget 0.5 (conservative); Window: None (full season); Threshold: 20% relative improvement
    # Captain: highest_value (strategy-sweep winner: +65 avg vs highest_xp, per-GW benchmark)
    # Bench: predictive_swap substitution (strategy-sweep winner: +19 avg vs static)
    # Chips: aggressive schedule (chip benchmark winner: +5 avg vs conservative, full-season)
    # Init: rolling_horizon n=5 (GW-selection benchmark winner: +604 avg vs greedy baseline)
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,  # Matches discount_next_n_gws(n=5, factor=0.8)
    transfer_budget_per_gw=0.5,  # Conservative budget
    transfer_window_gw_range=None,  # Full season availability (critical)
    transfer_xp_threshold=0.20,  # 20% relative improvement required
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_value',  # LOCKED: strategy-sweep winner (+65 avg vs highest_xp)
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='aggressive',  # LOCKED: chip benchmark winner (+5 avg vs conservative)
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    bench_composition_variant='safe',  # LOCKED Phase 8: BENCH_SAFE_STATIC optimal
    substitution_mode='predictive_swap',  # LOCKED: strategy-sweep winner (+19 avg vs static)
    substitution_trigger_threshold=0.20,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
    initial_team_algorithm='rolling_horizon',  # LOCKED: +604 avg over greedy baseline (GW-selection benchmark)
    ilp_rolling_weeks=5,                       # LOCKED: n=5 d=1.0 optimal (rolling_horizon benchmark)
)

# ARCHETYPE STRATEGIES (for systematic comparison)

CONSERVATIVE = StrategyConfig(
    # Philosophy: Prioritize consistency and downside protection over upside.
    # Targets Sharpe ratio optimization; stable weekly returns; low variance.
    # Use case: Risk-averse managers, emphasis on avoiding bad weeks.
    transfer_mode='flexible',
    max_transfers_per_gw=0,  # Rarely transfer; hold through variance
    transfer_discount_factor=0.8,
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.3,  # Penalize volatile captains
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=2,  # Use chips sparingly
    bench_mode='static',  # Keep bench stable
    bench_injury_threshold=0.5,
    position_variance_tolerance=0.9,  # Spread risk across positions
    punt_threshold=1.0,  # Don't punt low-xP players; hold for stability
)

AGGRESSIVE = StrategyConfig(
    # Philosophy: Maximize upside and chase points; accept volatility.
    # Targets total-point optimization; high variance; aggressive chips/transfers.
    # Use case: Confidence in xP model; comfortable with bad weeks if upside is higher.
    transfer_mode='greedy',
    max_transfers_per_gw=2,  # Transfer aggressively
    transfer_discount_factor=0.6,  # Longer multi-GW lookahead discount (favor long-term moves)
    captain_mode='highest_xp',
    captain_lookback_gws=3,  # Longer form lookback (capture hot streaks)
    captain_variance_penalty=0.0,  # Embrace captain variance
    chip_schedule='aggressive',
    wildcard_threshold_points=40.0,  # Lower threshold = more wildcard use
    chip_budget_limit=3,  # Use all chips
    bench_mode='fixture_aware',  # Rotate bench actively
    bench_injury_threshold=0.3,  # More aggressive on bench moves
    position_variance_tolerance=1.5,  # Concentrate in best players/positions
    punt_threshold=0.1,  # Punt low-xP players quickly
)

DIFFERENTIAL = StrategyConfig(
    # Philosophy: Beat the crowd via contrarian picks; maximize expected upside in low-ownership areas.
    # Targets differential leagues; high skew; contrarian captain/transfers.
    # Use case: Competitive managers in head-to-head leagues wanting edge vs. average team.
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    captain_mode='form_based',  # Contrarian captaincy (opposite of crowd)
    captain_lookback_gws=5,  # Longer form lookback for contrarian picks
    captain_variance_penalty=-0.2,  # Prefer contrarian/volatile captains
    chip_schedule='aggressive',
    wildcard_threshold_points=50.0,
    chip_budget_limit=3,
    bench_mode='fixture_aware',  # Active bench rotation for differential advantage
    bench_injury_threshold=0.3,
    position_variance_tolerance=1.4,  # Concentrate in differential picks
    punt_threshold=0.2,  # Punt more aggressively to free funds for differential plays
)


# PHASE 6: TRANSFER STRATEGY VARIANTS
# Systematic evaluation across budget (conservative/baseline/aggressive) and window (early/mid/late) dimensions

CONSERVATIVE_EARLY = StrategyConfig(
    # Philosophy: Low-risk transfers in early season only.
    # Budget: 0.5 (conservative); Window: GW 1-10 (early); Threshold: 20% relative improvement
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,
    transfer_window_gw_range=(1, 10),
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)

CONSERVATIVE_FULL = StrategyConfig(
    # Philosophy: Low-risk transfers throughout season.
    # Budget: 0.5 (conservative); Window: None (full season); Threshold: 20% relative improvement
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)

BASELINE_MID = StrategyConfig(
    # Philosophy: Baseline transfers in mid-season (GW 11-24).
    # Budget: 1.5 (baseline); Window: GW 11-24 (mid); Threshold: 15% relative improvement
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=1.5,
    transfer_window_gw_range=(11, 24),
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)

AGGRESSIVE_LATE = StrategyConfig(
    # Philosophy: Aggressive transfers in late season (GW 25-38).
    # Budget: 2.0 (aggressive); Window: GW 25-38 (late); Threshold: 10% relative improvement
    transfer_mode='greedy',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=2.0,
    transfer_window_gw_range=(25, 38),
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)

AGGRESSIVE_FULL = StrategyConfig(
    # Philosophy: Aggressive transfers throughout season.
    # Budget: 2.0 (aggressive); Window: None (full season); Threshold: 10% relative improvement
    transfer_mode='greedy',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=2.0,
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.10,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)


# PHASE 7a: CAPTAIN STRATEGY VARIANTS
# Test 3 captain modes with fixed transfer baseline (CONSERVATIVE_FULL)

CAPTAIN_HIGHEST_XP = StrategyConfig(
    # Philosophy: Always pick player with highest expected points.
    # Captain mode: highest_xp (standard baseline)
    # Form lookback: 1 GW (most recent only)
    # Variance penalty: 0.0 (no penalty; accept all variance)
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,  # CONSERVATIVE_FULL baseline
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)

CAPTAIN_FORM_BASED = StrategyConfig(
    # Philosophy: Pick player with recent hot streak (contrarian).
    # Captain mode: form_based (rolling average of recent xP)
    # Form lookback: 3 GW (recent form window)
    # Variance penalty: -0.2 (prefer volatile/hot players)
    # Rationale: Exploit recent momentum; expect reversion-to-mean is slower than market prices
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,  # CONSERVATIVE_FULL baseline
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='form_based',
    captain_lookback_gws=3,
    captain_variance_penalty=-0.2,  # Prefer contrarian picks
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)

CAPTAIN_HIGHEST_VALUE = StrategyConfig(
    # Philosophy: Always pick the highest-priced player (most consistent/reliable).
    # Captain mode: highest_value (pick by price)
    # Form lookback: 1 GW (unused; highest_value ignores lookback)
    # Variance penalty: 0.0 (unused; highest_value ignores penalty)
    # Rationale: Expensive players are safer; model predictions more reliable for elite players
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,  # CONSERVATIVE_FULL baseline
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_value',
    captain_lookback_gws=1,  # Unused for highest_value
    captain_variance_penalty=0.0,  # Unused for highest_value
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)


# PHASE 7b: CHIP TIMING STRATEGY VARIANTS
# Test 2 chip timing modes with fixed transfer baseline (CONSERVATIVE_FULL) and captain mode (highest_xp)

CHIP_DOUBLES_OPTIMIZED = StrategyConfig(
    # Philosophy: Maximize chip value by using them around DOUBLE gameweeks.
    # Chip schedule: 'doubles-optimized' (activate GW-1 before and during double GWs)
    # Threshold: 8 points xP gain (from CONTEXT.md D-03)
    # Rationale: Double GWs mean players play twice; chips provide 2x value
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,  # CONSERVATIVE_FULL baseline
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',  # Lock captain mode from Phase 7a findings
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='doubles-optimized',  # NEW: Timing-based chip activation
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)

CHIP_BLANKS_OPTIMIZED = StrategyConfig(
    # Philosophy: Hedge against blank gameweeks by using chips to maximize fill-in squad strength.
    # Chip schedule: 'blanks-optimized' (activate GW-1 before and after blank GWs)
    # Threshold: 8 points xP gain (from CONTEXT.md D-03)
    # Rationale: Blank GWs force squad rotations; chips compensate with high-value lineup
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,  # CONSERVATIVE_FULL baseline
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',  # Lock captain mode from Phase 7a findings
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='blanks-optimized',  # NEW: Timing-based chip activation
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)


# PHASE 8: BENCH COMPOSITION STRATEGY VARIANTS
# Test 2 bench composition modes + 2 substitution modes (2x2 factorial)
# All inherit CONSERVATIVE_FULL transfer + CAPTAIN_HIGHEST_VALUE captain

BENCH_SAFE_STATIC = StrategyConfig(
    # Philosophy: Defensive bench + static rotation
    # Bench composition: 1 GK (cheapest), 2 DEF (established, clean sheet probability), 1 MID (budget)
    # Subs: Rotate by lowest xP every GW (current behavior) — passive
    # Focus: Squad depth, availability, predictability
    # Rationale: Maximizes flexibility to cover injuries without overcommitting capital
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,  # CONSERVATIVE_FULL baseline
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_value',  # CAPTAIN_HIGHEST_VALUE baseline
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',  # Current: rotate by lowest xP
    bench_injury_threshold=0.5,
    bench_composition_variant='safe',  # Safe composition
    substitution_mode='static',  # Static rotation
    substitution_trigger_threshold=0.20,  # Unused in static mode
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)

BENCH_SAFE_PREDICTIVE = StrategyConfig(
    # DEPRECATED: Phase 8 evaluation (multi-season validation) shows predictive swaps degrade
    # performance across all seasons (2021-22: -27 pts, 2022-23: -41 pts, 2023-24: -111 pts).
    # Kept for reference/historical comparison only. DO NOT USE in production.
    # Philosophy: Defensive bench + predictive swaps
    # Bench composition: 1 GK (cheapest), 2 DEF (established, clean sheet probability), 1 MID (budget)
    # Subs: Swap if bench has >20% xP advantage over starter (GW > 5 only) — active
    # Focus: Squad depth, availability, predictability
    # Rationale: Maximizes flexibility to cover injuries without overcommitting capital
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,  # CONSERVATIVE_FULL baseline
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_value',  # CAPTAIN_HIGHEST_VALUE baseline
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',  # Current: rotate by lowest xP
    bench_injury_threshold=0.5,
    bench_composition_variant='safe',  # Safe composition
    substitution_mode='predictive_swap',  # Predictive swap logic
    substitution_trigger_threshold=0.20,  # Trigger if >20% improvement
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)

BENCH_SPECULATIVE_STATIC = StrategyConfig(
    # DEPRECATED: Phase 8 evaluation shows bench composition has zero impact on performance.
    # Kept for reference/historical comparison only. DO NOT USE in production.
    # Philosophy: Speculative bench + static rotation
    # Bench composition: 1 GK, 2 DEF (higher-variance, younger), 1 MID (upside potential)
    # Subs: Rotate by lowest xP every GW (current behavior) — passive
    # Focus: Differential points, younger talent, promoted clubs
    # Rationale: Accept bench volatility for potential breakout performances
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,  # CONSERVATIVE_FULL baseline
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_value',  # CAPTAIN_HIGHEST_VALUE baseline
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',  # Current: rotate by lowest xP
    bench_injury_threshold=0.5,
    bench_composition_variant='speculative',  # Speculative composition
    substitution_mode='static',  # Static rotation
    substitution_trigger_threshold=0.20,  # Unused in static mode
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)

BENCH_SPECULATIVE_PREDICTIVE = StrategyConfig(
    # DEPRECATED: Phase 8 evaluation shows both bench composition and predictive swaps degrade
    # performance (composition 0 pts, swaps -27 to -111 pts). Kept for reference only. DO NOT USE.
    # Philosophy: Speculative bench + predictive swaps
    # Bench composition: 1 GK, 2 DEF (higher-variance, younger), 1 MID (upside potential)
    # Subs: Swap if bench has >20% xP advantage over starter (GW > 5 only) — active
    # Focus: Differential points, younger talent, promoted clubs
    # Rationale: Accept bench volatility for potential breakout performances
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,  # CONSERVATIVE_FULL baseline
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_value',  # CAPTAIN_HIGHEST_VALUE baseline
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',  # Current: rotate by lowest xP
    bench_injury_threshold=0.5,
    bench_composition_variant='speculative',  # Speculative composition
    substitution_mode='predictive_swap',  # Predictive swap logic
    substitution_trigger_threshold=0.20,  # Trigger if >20% improvement
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
)

# PHASE 8 FINAL OPTIMIZED STRATEGY
# Locks all Phase 6-8 optimal decisions: CONSERVATIVE_FULL transfer + CAPTAIN_HIGHEST_VALUE captain + BENCH_SAFE_STATIC

PHASE_8_OPTIMAL = StrategyConfig(
    # Philosophy: Combines Phase 6-10 optimal findings
    # Phase 6: CONSERVATIVE_FULL (budget 0.5, 20% threshold, full season window)
    # Phase 7: CAPTAIN_HIGHEST_VALUE (prefer high-priced stable players)
    # Phase 8: BENCH_SAFE_STATIC (safe composition, static rotation) — multi-season validated
    # Phase 10: two_tier initial team (+38 avg vs greedy baseline)
    # Multi-season validation: Optimal across 2021-22, 2022-23, 2023-24, 2024-25
    # Confidence: VERY HIGH (4-season cross-validation, robust to seasonal variation)
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,  # CONSERVATIVE_FULL locked
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_value',  # CAPTAIN_HIGHEST_VALUE locked (Phase 7 optimal)
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    bench_composition_variant='safe',  # BENCH_SAFE_STATIC locked (Phase 8 optimal)
    substitution_mode='static',  # Static rotation optimal (predictive swaps degrade -27 to -111 pts)
    substitution_trigger_threshold=0.20,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
    initial_team_algorithm='two_tier',  # LOCKED Phase 10: +38 avg over greedy baseline
)

# Backward compatibility aliases (Plan 08-01)
BENCH_SAFE = BENCH_SAFE_STATIC
BENCH_SPECULATIVE = BENCH_SPECULATIVE_STATIC


# INITIAL TEAM ALGORITHM BENCHMARK VARIANTS
# All use BASELINE_CURRENT transfer/captain/chip settings; only initial_team_algorithm differs.
# Run manager.py -seasons 2021-22 2022-23 2023-24 2024-25 for each to compare.

INIT_GREEDY = BASELINE_CURRENT  # Baseline: two-tier greedy (premium by xP, fillers ≤£6m)

INIT_TWO_TIER = StrategyConfig(
    # Fillers by xP/£m ratio instead of cheapest absolute price.
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    bench_composition_variant='safe',
    substitution_mode='static',
    substitution_trigger_threshold=0.20,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
    initial_team_algorithm='two_tier',
)

INIT_ILP_XP = StrategyConfig(
    # ILP maximising total multi-GW xP with hard budget constraint.
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    bench_composition_variant='safe',
    substitution_mode='static',
    substitution_trigger_threshold=0.20,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
    initial_team_algorithm='ilp_xp',
)

INIT_ILP_RATIO = StrategyConfig(
    # ILP maximising xP/cost ratio — value-ratio objective.
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    bench_composition_variant='safe',
    substitution_mode='static',
    substitution_trigger_threshold=0.20,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
    initial_team_algorithm='ilp_ratio',
)

INIT_ILP_PENALISED = StrategyConfig(
    # ILP maximising xP − lambda*cost (lambda=2.0 empirically tuned).
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    bench_composition_variant='safe',
    substitution_mode='static',
    substitution_trigger_threshold=0.20,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
    initial_team_algorithm='ilp_penalised',
    ilp_lambda=2.0,
)

INIT_ILP_CAPTAIN = StrategyConfig(
    # ILP with captain's xP double-counted in objective.
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    bench_composition_variant='safe',
    substitution_mode='static',
    substitution_trigger_threshold=0.20,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
    initial_team_algorithm='ilp_captain',
)

INIT_ROLLING_HORIZON = StrategyConfig(
    # Greedy on summed xP across next 5 actual prediction files (GW+0..GW+4).
    transfer_mode='flexible',
    max_transfers_per_gw=1,
    transfer_discount_factor=0.8,
    transfer_budget_per_gw=0.5,
    transfer_window_gw_range=None,
    transfer_xp_threshold=0.20,
    transfer_xp_threshold_mode='relative',
    captain_mode='highest_xp',
    captain_lookback_gws=1,
    captain_variance_penalty=0.0,
    chip_schedule='conservative',
    wildcard_threshold_points=60.0,
    chip_budget_limit=3,
    bench_mode='rotate_low_xp',
    bench_injury_threshold=0.5,
    bench_composition_variant='safe',
    substitution_mode='static',
    substitution_trigger_threshold=0.20,
    position_variance_tolerance=1.2,
    punt_threshold=0.5,
    initial_team_algorithm='rolling_horizon',
    ilp_rolling_weeks=5,
)


__all__ = [
    'StrategyConfig',
    'BASELINE_STATIC',
    'BASELINE_CURRENT',
    'CONSERVATIVE',
    'AGGRESSIVE',
    'DIFFERENTIAL',
    'CONSERVATIVE_EARLY',
    'CONSERVATIVE_FULL',
    'BASELINE_MID',
    'AGGRESSIVE_LATE',
    'AGGRESSIVE_FULL',
    'CAPTAIN_HIGHEST_XP',
    'CAPTAIN_FORM_BASED',
    'CAPTAIN_HIGHEST_VALUE',
    'CHIP_DOUBLES_OPTIMIZED',
    'CHIP_BLANKS_OPTIMIZED',
    'BENCH_SAFE_STATIC',
    'BENCH_SAFE_PREDICTIVE',  # DEPRECATED (Phase 8: degrades -27 to -111 pts)
    'BENCH_SPECULATIVE_STATIC',  # DEPRECATED (Phase 8: zero impact)
    'BENCH_SPECULATIVE_PREDICTIVE',  # DEPRECATED (Phase 8: both variants degrade)
    'BENCH_SAFE',  # Backward compat alias
    'BENCH_SPECULATIVE',  # Backward compat alias
    'PHASE_8_OPTIMAL',  # LOCKED Phase 6-8 optimal (multi-season validated)
    # Initial team algorithm benchmarks
    'INIT_GREEDY',
    'INIT_TWO_TIER',
    'INIT_ILP_XP',
    'INIT_ILP_RATIO',
    'INIT_ILP_PENALISED',
    'INIT_ILP_CAPTAIN',
    'INIT_ROLLING_HORIZON',
]
