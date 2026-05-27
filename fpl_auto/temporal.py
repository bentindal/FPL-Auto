"""
Temporal Integrity Enforcement Module for FPL Automation

This module provides the TemporalGate class, which enforces temporal boundaries
during backtesting to prevent strategies from accessing future data.

Key concept: During decision-making for gameweek N, code should only access:
- Historical data for GW(1) through GW(N-1)
- Predictions for GW(N) (generated overnight before deadline)
- Never future gameweeks GW(N+1) or later
- Never the current GW actual results during strategic decisions

Future integration: Phase 2 will wrap FplData calls in Team.__init__ with TemporalGate.
"""


class TemporalViolationError(Exception):
    """Raised when code attempts to access data outside temporal boundaries."""
    pass


class TemporalGate:
    """
    Enforces temporal boundaries during backtesting.

    During decision-making for gameweek N, TemporalGate restricts access to:
    - Historical data: GW(1) to GW(N-1) only
    - Predictions: GW(N) only
    - Fixture metadata: all gameweeks (known pre-season)

    All access attempts are logged to _access_log for audit trails and testing.
    """

    def __init__(self, season: str, decision_gameweek: int):
        """
        Initialize TemporalGate for a specific gameweek decision.

        Args:
            season: Season code (e.g., '2023-24')
            decision_gameweek: The gameweek for which decisions are being made (1-38)
        """
        self.season = season
        self.decision_gameweek = decision_gameweek
        self._access_log = []

    def safe_read_historical_form(self, target_gw: int) -> bool:
        """
        Check if reading historical form data for target_gw is allowed.

        Rule: target_gw must be strictly before decision_gameweek.
        Historical form includes stats, points, player metrics from completed gameweeks.

        Args:
            target_gw: The gameweek being accessed

        Returns:
            True if access is allowed

        Raises:
            TemporalViolationError: If target_gw >= decision_gameweek
        """
        allowed = target_gw < self.decision_gameweek
        self._access_log.append(('historical_form', target_gw, self.decision_gameweek, allowed))

        if not allowed:
            raise TemporalViolationError(
                f"Trying to access GW{target_gw} historical_form during decision for GW{self.decision_gameweek}. "
                f"Only GW1-{self.decision_gameweek - 1} available."
            )
        return allowed

    def safe_read_predictions(self, target_gw: int) -> bool:
        """
        Check if reading predictions for target_gw is allowed.

        Rule: target_gw must equal decision_gameweek.
        Predictions are pre-trained before the gameweek deadline and represent
        expected points for the upcoming gameweek.

        Args:
            target_gw: The gameweek being predicted

        Returns:
            True if access is allowed

        Raises:
            TemporalViolationError: If target_gw != decision_gameweek
        """
        allowed = target_gw == self.decision_gameweek
        self._access_log.append(('predictions', target_gw, self.decision_gameweek, allowed))

        if not allowed:
            raise TemporalViolationError(
                f"Trying to access GW{target_gw} predictions during decision for GW{self.decision_gameweek}. "
                f"Only GW{self.decision_gameweek} available."
            )
        return allowed

    def safe_read_fixture_metadata(self) -> bool:
        """
        Check if reading fixture metadata is allowed.

        Rule: Always allowed. Fixtures are known before the season starts and
        do not contain actual outcomes (difficulty ratings are static).

        Returns:
            Always True
        """
        self._access_log.append(('fixture_metadata', None, self.decision_gameweek, True))
        return True

    def audit_trail(self) -> list:
        """
        Return the full access log for this gate.

        Returns:
            List of tuples (data_type, accessed_gw, decision_gw, allowed: bool)
            Example: [('historical_form', 5, 10, True), ('predictions', 11, 10, False)]
        """
        return self._access_log

    def __repr__(self) -> str:
        """
        Summary of gate activity for debugging.

        Returns:
            String showing violation count and access summary
        """
        total_accesses = len(self._access_log)
        violations = sum(1 for _, _, _, allowed in self._access_log if not allowed)

        if total_accesses == 0:
            return f"TemporalGate(season={self.season}, gw={self.decision_gameweek}, accesses=0)"

        return (
            f"TemporalGate(season={self.season}, gw={self.decision_gameweek}, "
            f"accesses={total_accesses}, violations={violations})"
        )
