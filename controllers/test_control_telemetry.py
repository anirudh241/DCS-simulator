"""Numerical and lifecycle checks for read-only control telemetry."""

from dataclasses import FrozenInstanceError
import unittest

from controllers.pid import PIDController
from controllers.level_controller import LevelController
from controllers.simulation_engine import SimulationEngine


class ControlTelemetryTests(unittest.TestCase):
    def test_pid_terms_first_step_and_derivative(self):
        pid = PIDController(2, 0.5, 0.1, 10, -100, 100)
        self.assertIsNone(pid.last_snapshot)
        self.assertEqual(pid.update(8, 0.5), 4.5)
        first = pid.last_snapshot
        self.assertEqual((first.proportional, first.integral, first.derivative), (4, 0.5, 0))
        self.assertAlmostEqual(pid.update(9, 0.5), 2.55)
        self.assertAlmostEqual(pid.last_snapshot.derivative, -0.2)
        self.assertEqual(first.process_value, 8)
        with self.assertRaises(FrozenInstanceError):
            first.error = 99
        pid.reset()
        self.assertIsNone(pid.last_snapshot)
        pid.update(9, 0.5)
        self.assertEqual(pid.last_snapshot.derivative, 0)

    def test_trim_and_final_command_limits_are_distinct(self):
        controller = LevelController(setpoint_mm=700)
        self.assertEqual(controller.compute_valve_position(0, 100, 0.1), 100)
        c = controller.last_snapshot
        self.assertTrue(c.pid.output_limited)
        self.assertEqual(c.pid.output, 50)
        self.assertAlmostEqual(c.feedforward_pct, 100 / 120 * 100)
        self.assertTrue(c.command_limited)
        controller = LevelController(setpoint_mm=0)
        self.assertEqual(controller.compute_valve_position(1000, 0, 0.1), 0)
        self.assertEqual(controller.last_snapshot.pid.output, -50)
        self.assertTrue(controller.last_snapshot.command_limited)

    def test_integral_clamp_and_invalid_dt(self):
        pid = PIDController(0, 1, 0, 2000, -5000, 5000)
        pid.update(0, 1)
        self.assertEqual(pid.last_snapshot.integral, 1000)
        self.assertTrue(pid.last_snapshot.integral_limited)
        saved = pid.last_snapshot
        with self.assertRaises(ValueError):
            pid.update(0, 0)
        self.assertIs(pid.last_snapshot, saved)

    def test_engine_sample_preserves_input_and_result(self):
        engine = SimulationEngine()
        self.assertIsNone(engine.last_control_sample)
        engine.set_level_setpoint(650)
        initial_level = engine.drum.level_mm
        result = engine.step()
        saved = engine.last_control_sample
        self.assertEqual(saved.step_number, 1)
        self.assertEqual(saved.control.pid.process_value, initial_level)
        self.assertEqual(saved.control.pid.error, 650 - initial_level)
        self.assertEqual(saved.resulting_level_mm, result.level_mm)
        self.assertEqual(saved.valve_position_pct, saved.control.valve_command_pct)
        self.assertEqual(saved.feedwater_flow, result.feedwater_flow)
        engine.set_level_setpoint(450)
        engine.set_steam_demand(80)
        self.assertIs(engine.last_control_sample, saved)
        self.assertEqual(saved.control.pid.setpoint, 650)
        engine.step()
        self.assertEqual(engine.last_control_sample.control.pid.process_value, result.level_mm)
        engine.reset()
        self.assertIsNone(engine.last_control_sample)
        self.assertEqual(engine.step_number, 0)


if __name__ == "__main__":
    unittest.main()
