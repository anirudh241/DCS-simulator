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

    def __init__(self, setpoint_mm=500.0):

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

        valve_position = steam_demand_pct + trim

        return max(
            0.0,
            min(100.0, valve_position),
        )