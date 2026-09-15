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


@dataclass(frozen=True)
class PIDSnapshot:
    """Values captured during one calculation; reading them never advances PID."""

    setpoint: float
    process_value: float
    error: float
    dt: float
    kp: float
    ki: float
    kd: float
    proportional: float
    integral: float
    derivative: float
    integral_accumulator: float
    integral_limited: bool
    raw_output: float
    output: float
    output_min: float
    output_max: float

    @property
    def output_limited(self):
        return self.raw_output != self.output


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
        self.last_snapshot: PIDSnapshot | None = None

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
        accumulated_error = self._integral

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
        raw_output = output

        # ---------- Clamp ----------

        output = max(self.output_min, output)
        output = min(self.output_max, output)

        self.last_snapshot = PIDSnapshot(
            setpoint=self.setpoint, process_value=process_value, error=error,
            dt=dt, kp=self.kp, ki=self.ki, kd=self.kd,
            proportional=p, integral=i, derivative=d,
            integral_accumulator=self._integral,
            integral_limited=accumulated_error != self._integral,
            raw_output=raw_output, output=output,
            output_min=self.output_min, output_max=self.output_max,
        )

        return output
