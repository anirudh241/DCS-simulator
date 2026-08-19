"""
Boiler drum level controller.

Uses

Valve Position =
    Steam Demand (feedforward)
  + PID Trim (feedback)

This is a simplified version of industrial boiler drum control.
"""

from controllers.pid import PIDController

KP = 0.15
KI = 0.02
KD = 0.05

TRIM_LIMIT = 50.0

class LevelController:

    def __init__(
        self,
        setpoint_mm=500.0,
        max_feedwater_flow=120.0,
    ):

        self.max_feedwater_flow = max_feedwater_flow

        self.pid = PIDController(
            kp=KP,
            ki=KI,
            kd=KD,
            setpoint=setpoint_mm,
            output_min=-TRIM_LIMIT,
            output_max=TRIM_LIMIT,
        )

    @property
    def setpoint_mm(self):
        return self.pid.setpoint

    def compute_valve_position(
        self,
        level_mm,
        steam_demand_pct,
        dt,
    ):

        trim = self.pid.update(level_mm, dt)

        # Convert the required feedwater flow into a valve position.
        #
        # For example:
        # 60 units of steam demand / 120 maximum feedwater
        # = 50% valve opening.
        feedforward_position = (
            steam_demand_pct
            / self.max_feedwater_flow
            * 100.0
        )

        valve_position = feedforward_position + trim

        return max(
            0.0,
            min(100.0, valve_position),
        )