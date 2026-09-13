import unittest

from models.alarm import AlarmManager, AlarmPriority, AlarmState

class AlarmManagerTests(unittest.TestCase):

    def setUp(self):
        self.manager = AlarmManager()

    def test_normal_level_has_no_alarms(self):
        self.assertFalse(self.manager.update_drum_level(500.0, 0.0))
        self.assertEqual(self.manager.active_alarms, ())
        self.assertEqual(self.manager.records, ())

    def test_high_and_high_high_alarm_sequence(self):
        self.manager.update_drum_level(600.0, 1.0)
        self.assertEqual(len(self.manager.active_alarms), 1)
        self.assertEqual(
            self.manager.active_alarms[0].definition.message,
            "DRUM LEVEL HIGH",
        )

        self.manager.update_drum_level(650.0, 2.0)
        self.assertEqual(len(self.manager.active_alarms), 2)
        self.assertEqual(
            self.manager.highest_priority_alarm.definition.priority,
            AlarmPriority.CRITICAL,
        )

    def test_hysteresis_prevents_alarm_chatter(self):
        self.manager.update_drum_level(600.0, 1.0)
        self.manager.update_drum_level(595.0, 2.0)
        self.assertEqual(len(self.manager.active_alarms), 1)

        self.manager.update_drum_level(590.0, 3.0)
        self.assertEqual(self.manager.active_alarms, ())
        self.assertEqual(self.manager.records[0].state, AlarmState.CLEARED)

    def test_low_and_low_low_use_upper_clear_limits(self):
        self.manager.update_drum_level(350.0, 1.0)
        self.assertEqual(len(self.manager.active_alarms), 2)

        self.manager.update_drum_level(405.0, 2.0)
        self.assertEqual(len(self.manager.active_alarms), 1)
        self.manager.update_drum_level(410.0, 3.0)
        self.assertEqual(self.manager.active_alarms, ())

    def test_acknowledging_does_not_clear_process_alarm(self):
        self.manager.update_drum_level(400.0, 1.0)
        alarm = self.manager.active_alarms[0]

        self.assertTrue(self.manager.acknowledge(alarm.event_id))
        self.assertTrue(alarm.active)
        self.assertEqual(alarm.state, AlarmState.ACTIVE_ACKNOWLEDGED)
        self.assertEqual(self.manager.unacknowledged_alarms, ())

    def test_acknowledge_all_handles_every_active_alarm(self):
        self.manager.update_drum_level(650.0, 1.0)

        self.assertTrue(self.manager.acknowledge_all())
        self.assertEqual(self.manager.unacknowledged_alarms, ())
        self.assertTrue(all(alarm.active for alarm in self.manager.active_alarms))

    def test_cleared_alarm_reactivation_creates_new_occurrence(self):
        self.manager.update_drum_level(400.0, 1.0)
        first_id = self.manager.active_alarms[0].event_id
        self.manager.update_drum_level(410.0, 2.0)
        self.manager.update_drum_level(399.0, 3.0)

        self.assertEqual(len(self.manager.records), 2)
        self.assertNotEqual(self.manager.active_alarms[0].event_id, first_id)

    def test_history_limit_never_discards_active_alarms(self):
        manager = AlarmManager(max_history=1)
        manager.update_drum_level(650.0, 1.0)

        self.assertEqual(len(manager.active_alarms), 2)
        for alarm in manager.active_alarms:
            self.assertTrue(manager.acknowledge(alarm.event_id))


if __name__ == "__main__":
    unittest.main()
