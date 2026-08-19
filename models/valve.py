"""
Control valve model.

Converts valve opening (%) into feedwater flow.

This is intentionally simple for Phase 1.
Later we can add:
- valve travel time
- stiction
- hysteresis
- actuator failure
"""

from dataclasses import dataclass


@dataclass
class ControlValve:

    # Provides 20% reserve capacity so the controller can raise
    # drum level even when steam demand is already at 100%.
    max_flow: float = 120.0

    def __post_init__(self):

        self.position_pct = 0.0

    def set_position(self, position_pct: float):

        self.position_pct = max(
            0.0,
            min(100.0, position_pct),
        )

    @property
    def flow(self) -> float:
        """
        Feedwater flow.

        Phase 1:
            Linear valve characteristic.

        Later:
            Equal-percentage characteristic.
        """

        return self.max_flow * self.position_pct / 100.0