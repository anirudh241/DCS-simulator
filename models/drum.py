"""
Simplified boiler drum process model.

This is NOT a thermodynamic model.

Instead, it behaves like a real process from the controller's point
of view:

- Steam demand removes water from the drum.
- Feedwater valve adds water.
- Drum level changes accordingly.
- Pressure and temperature follow load slowly.

The model exposes a snapshot() method so the UI never reaches inside
the object directly.
"""

from dataclasses import dataclass


# ----------------------------------------------------
# Initial Conditions
# ----------------------------------------------------

INITIAL_LEVEL = 500.0          # mm
INITIAL_PRESSURE = 165.0       # bar
INITIAL_TEMPERATURE = 540.0    # °C

INITIAL_STEAM_DEMAND = 60.0    # %
INITIAL_VALVE = 60.0           # %

# How strongly valve imbalance changes drum level.
LEVEL_GAIN = 0.6

# Maximum level allowed.
MIN_LEVEL = 0.0
MAX_LEVEL = 1000.0

INITIAL_STEAM_FLOW = 60.0


@dataclass
class DrumSnapshot:
    level_mm: float
    pressure_bar: float
    temperature_c: float
    steam_demand_pct: float
    feedwater_flow: float
    steam_flow: float


class Drum:

    def __init__(self):

        self.level_mm = INITIAL_LEVEL
        self.pressure_bar = INITIAL_PRESSURE
        self.temperature_c = INITIAL_TEMPERATURE

        self.steam_demand_pct = INITIAL_STEAM_DEMAND
        self.feedwater_flow = INITIAL_VALVE
        self.steam_flow = INITIAL_STEAM_FLOW

    def update(self, feedwater_flow: float, dt: float):

        """
        Advance the boiler drum process by dt seconds.
        """

        self.feedwater_flow = feedwater_flow

        # --------------------------------
        # Steam-flow dynamics
        # --------------------------------

        # Actual steam flow cannot instantly follow
        # the operator's requested demand.
        steam_response_rate = 0.8

        self.steam_flow += (
            self.steam_demand_pct
            - self.steam_flow
        ) * steam_response_rate * dt

        # --------------------------------
        # Drum level
        # --------------------------------

        imbalance = (
            self.feedwater_flow
            - self.steam_flow
        )

        self.level_mm += (
            imbalance
            * LEVEL_GAIN
            * dt
        )

        self.level_mm = max(
            MIN_LEVEL,
            min(MAX_LEVEL, self.level_mm)
        )

        # --------------------------------
        # Pressure
        # --------------------------------

        target_pressure = (
            120.0
            + self.steam_flow * 0.75
        )

        self.pressure_bar += (
            target_pressure
            - self.pressure_bar
        ) * 0.03

        # --------------------------------
        # Temperature
        # --------------------------------

        target_temperature = (
            500.0
            + self.steam_flow * 0.7
        )

        self.temperature_c += (
            target_temperature
            - self.temperature_c
        ) * 0.02

    def set_steam_demand(self, demand_pct: float):

        """
        Operator changes plant load.
        """

        self.steam_demand_pct = max(
            0.0,
            min(100.0, demand_pct)
        )

    def snapshot(self):

        return DrumSnapshot(
            level_mm=self.level_mm,
            pressure_bar=self.pressure_bar,
            temperature_c=self.temperature_c,
            steam_demand_pct=self.steam_demand_pct,
            steam_flow=self.steam_flow,
            feedwater_flow=self.feedwater_flow,
        )