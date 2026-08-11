"""
Coordinates the entire simulation.

Every simulation tick:

1. Read drum level
2. Compute valve position
3. Update valve
4. Compute feedwater flow
5. Advance drum
"""

from models.drum import Drum
from models.valve import ControlValve
from controllers.level_controller import LevelController


class SimulationEngine:

    def __init__(self):

        self.dt = 0.1

        self.drum = Drum()
        self.valve = ControlValve()
        self.controller = LevelController()

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

        return self.drum.snapshot()

    def set_steam_demand(self, demand):
        self.drum.set_steam_demand(demand)

    def set_level_setpoint(self, setpoint_mm):
        self.controller.pid.setpoint = float(setpoint_mm)

    def reset(self):
        self.__init__()