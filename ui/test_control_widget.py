"""The display must never advance or alter the controller it observes."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


class ControlDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.window.alarm_sound.effect.setMuted(True)
        self.addCleanup(self.window.close)

    def test_waiting_and_navigation_are_read_only(self):
        w = self.window
        w.show_control()
        self.assertIn("WAITING", w.control_dashboard.status.text())
        self.assertIsNone(w.engine.last_control_sample)
        w._simulation_tick()
        saved = w.engine.last_control_sample
        for _ in range(3):
            w.show_overview()
            w.show_trends()
            w.show_alarms()
            w.show_control()
        self.assertIs(w.engine.last_control_sample, saved)
        self.assertEqual(w.engine.step_number, 1)
        self.assertTrue(w.control_button.isChecked())

    def test_paused_edits_remain_pending_until_next_step(self):
        w = self.window
        w.show_control()
        w._simulation_tick()
        saved = w.engine.last_control_sample
        original_text = w.control_dashboard.diagram.blocks["inputs"].body.text()
        w.faceplate.level_setpoint.setValue(650)
        w.faceplate.steam_demand.setValue(80)
        self.assertIs(w.engine.last_control_sample, saved)
        self.assertIn("Pending next step", w.control_dashboard.status.text())
        self.assertEqual(w.control_dashboard.diagram.blocks["inputs"].body.text(), original_text)
        w._simulation_tick()
        self.assertNotIn("Pending next step", w.control_dashboard.status.text())
        self.assertIn("650.00", w.control_dashboard.diagram.blocks["inputs"].body.text())

    def test_live_pause_and_limit_indicators(self):
        w = self.window
        w.show_control()
        w.faceplate.level_setpoint.setValue(700)
        w.faceplate.steam_demand.setValue(100)
        w.engine.drum.level_mm = 0
        w.start_simulation()
        w._simulation_tick()
        self.assertIn("LIVE", w.control_dashboard.status.text())
        self.assertIn("TRIM LIMITED", w.control_dashboard.diagram.blocks["pid"].body.text())
        self.assertIn("COMMAND LIMITED", w.control_dashboard.diagram.blocks["command"].body.text())
        w.stop_simulation()
        self.assertIn("PAUSED", w.control_dashboard.status.text())
        self.assertFalse(w.timer.isActive())

    def test_demand_emphasis_only_after_calculation_and_clears(self):
        w = self.window
        w.show_control()
        w._simulation_tick()
        w.faceplate.steam_demand.setValue(80)
        dashboard = w.control_dashboard
        self.assertFalse(dashboard._demand_changed)
        w._simulation_tick()
        saved = w.engine.last_control_sample
        self.assertIn("DEMAND CHANGED", dashboard.diagram.blocks["feedforward"].body.text())
        self.assertTrue(dashboard._emphasis_timer.isActive())
        dashboard._clear_demand_emphasis()
        self.assertNotIn("DEMAND CHANGED", dashboard.diagram.blocks["feedforward"].body.text())
        self.assertIs(w.engine.last_control_sample, saved)

    def test_large_error_emphasis_has_hysteresis(self):
        w = self.window
        w.show_control()
        for error, expected in ((26, True), (23, True), (19, False), (-38, True)):
            w.engine.drum.level_mm = 500 - error
            w._simulation_tick()
            self.assertEqual(w.control_dashboard._large_error, expected)
        self.assertIn("Level above setpoint", w.control_dashboard.diagram.blocks["error"].body.text())


if __name__ == "__main__":
    unittest.main()
