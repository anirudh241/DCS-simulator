"""
Generic PID controller.

This class knows nothing about boilers or valves.
It simply calculates a control output from a process variable.

output =
    Kp * error
  + Ki * integral(error)
  + Kd * derivative(error)
"""

from dataclasses import dataclass


@dataclass
class PIDController:
    kp: float
    ki: float
    kd: float

    setpoint: float

    output_min: float = 0.0
    output_max: float = 100.0

    def __post_init__(self):
        self.reset()

    def reset(self):
        """Reset controller memory."""

        self._integral = 0.0
        self._previous_error = 0.0
        self._first_update = True

    def update(self, process_value: float, dt: float) -> float:
        """
        Compute PID output.

        Parameters
        ----------
        process_value
            Current measured value.

        dt
            Time since last update (seconds).

        Returns
        -------
        float
            Controller output.
        """

        if dt <= 0:
            raise ValueError("dt must be > 0")

        error = self.setpoint - process_value

        # ---------- Proportional ----------

        p = self.kp * error

    # ---------- Integral (anti-windup) ----------

        self._integral += error * dt

        # Prevent the integral term from growing without bound.
        # The limits are conservative and can be tuned later.

        INTEGRAL_LIMIT = 1000.0

        self._integral = max(
            -INTEGRAL_LIMIT,
            min(INTEGRAL_LIMIT, self._integral),
        )

        i = self.ki * self._integral

        # ---------- Derivative ----------

        if self._first_update:
            derivative = 0.0
            self._first_update = False
        else:
            derivative = (error - self._previous_error) / dt

        d = self.kd * derivative

        self._previous_error = error

        output = p + i + d

        # ---------- Clamp ----------

        output = max(self.output_min, output)
        output = min(self.output_max, output)

        return output