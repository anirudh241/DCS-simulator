"""
Coordinates the entire simulation.

Every simulation tick:

1. Read drum level
2. Compute valve position
3. Update valve
4. Compute feedwater flow
5. Advance drum
"""

from dataclasses import dataclass

from models.drum import Drum
from models.valve import ControlValve
from controllers.level_controller import LevelController, LevelControlSnapshot


@dataclass(frozen=True)
class ControlSample:
    """Controller inputs and resulting valve/process values from a single step."""

    step_number: int
    control: LevelControlSnapshot
    valve_position_pct: float
    feedwater_flow: float
    resulting_level_mm: float


class SimulationEngine:

    def __init__(self):

        self.dt = 0.1
        self.step_number = 0
        self.last_control_sample: ControlSample | None = None

        self.drum = Drum()
        self.valve = ControlValve()

        # Convert the initial feedwater flow into the corresponding
        # valve-opening percentage.
        self.valve.set_position(
            self.drum.feedwater_flow
            / self.valve.max_flow
            * 100.0
        )

        self.controller = LevelController(
            max_feedwater_flow=self.valve.max_flow
        )
        

    def step(self):

        snapshot = self.drum.snapshot()

        valve_position = self.controller.compute_valve_position(
            level_mm=snapshot.level_mm,
            steam_demand_pct=snapshot.steam_demand_pct,
            dt=self.dt,
        )

        self.valve.set_position(valve_position)

        self.drum.update(
            feedwater_flow=self.valve.flow,
            dt=self.dt,
        )

        self.step_number += 1
        self.last_control_sample = ControlSample(
            step_number=self.step_number,
            control=self.controller.last_snapshot,
            valve_position_pct=self.valve.position_pct,
            feedwater_flow=self.valve.flow,
            resulting_level_mm=self.drum.level_mm,
        )

        return self.drum.snapshot()

    def set_steam_demand(self, demand):
        self.drum.set_steam_demand(demand)

    def set_level_setpoint(self, setpoint_mm):
        self.controller.pid.setpoint = float(setpoint_mm)

    def reset(self):
        self.__init__()
