"""Bounded, UI-independent history for the operator trend displays."""

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class TrendSample:
    """One synchronized sample from the process and its controller."""

    time_seconds: float
    level_mm: float
    setpoint_mm: float
    feedwater_flow: float
    steam_flow: float
    steam_demand_pct: float
    valve_position_pct: float
    pressure_bar: float
    temperature_c: float


class TrendHistory:
    """Keep a fixed amount of simulation history without unbounded growth."""

    def __init__(self, max_samples=7200):
        if max_samples < 1:
            raise ValueError("max_samples must be at least 1")
        self._samples = deque(maxlen=max_samples)

    def __len__(self):
        return len(self._samples)

    def append(self, time_seconds, snapshot, setpoint_mm, valve_position_pct):
        sample = TrendSample(
            time_seconds=float(time_seconds),
            level_mm=snapshot.level_mm,
            setpoint_mm=float(setpoint_mm),
            feedwater_flow=snapshot.feedwater_flow,
            steam_flow=snapshot.steam_flow,
            steam_demand_pct=snapshot.steam_demand_pct,
            valve_position_pct=float(valve_position_pct),
            pressure_bar=snapshot.pressure_bar,
            temperature_c=snapshot.temperature_c,
        )
        self._samples.append(sample)
        return sample

    def clear(self):
        self._samples.clear()

    def series(self, window_seconds):
        """Return plot-ready series, with the newest sample at x = 0."""
        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than zero")

        values = {
            "time": [],
            "level": [],
            "setpoint": [],
            "feedwater": [],
            "steam_flow": [],
            "steam_demand": [],
            "valve": [],
            "pressure": [],
            "temperature": [],
        }
        if not self._samples:
            return values

        latest_time = self._samples[-1].time_seconds
        cutoff = latest_time - float(window_seconds)

        for sample in self._samples:
            if sample.time_seconds < cutoff:
                continue
            values["time"].append(sample.time_seconds - latest_time)
            values["level"].append(sample.level_mm)
            values["setpoint"].append(sample.setpoint_mm)
            values["feedwater"].append(sample.feedwater_flow)
            values["steam_flow"].append(sample.steam_flow)
            values["steam_demand"].append(sample.steam_demand_pct)
            values["valve"].append(sample.valve_position_pct)
            values["pressure"].append(sample.pressure_bar)
            values["temperature"].append(sample.temperature_c)

        return values
