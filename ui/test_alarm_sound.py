"""Check alarm audio lifecycle without playing sound during tests."""

import unittest
from unittest.mock import Mock

from PySide6.QtMultimedia import QSoundEffect

from models.alarm import AlarmManager
from ui.alarm_sound import AlarmSound


class AlarmSoundTests(unittest.TestCase):
    def setUp(self):
        self.effect = Mock()
        self.sound = AlarmSound(effect=self.effect)
        self.manager = AlarmManager()

    def update(self, level):
        self.manager.update_drum_level(level, 0)
        self.sound.update(self.manager.active_alarms)

    def test_warning_plays_once_per_occurrence(self):
        self.update(610)
        self.effect.play.assert_called_once()
        self.effect.setLoopCount.assert_called_with(1)
        for _ in range(10):
            self.update(610)
        self.effect.play.assert_called_once()
        self.update(500)
        self.update(610)
        self.assertEqual(self.effect.play.call_count, 2)

    def test_critical_repeats_until_acknowledged(self):
        self.update(660)
        self.effect.setLoopCount.assert_called_with(QSoundEffect.Loop.Infinite.value)
        self.update(660)
        self.effect.play.assert_called_once()
        self.effect.stop.reset_mock()
        self.manager.acknowledge_all()
        self.sound.update(self.manager.active_alarms)
        self.effect.stop.assert_called_once()

    def test_silence_does_not_acknowledge_and_new_critical_sounds(self):
        self.update(610)
        self.sound.silence()
        self.assertTrue(self.sound.silenced)
        self.assertEqual(len(self.manager.unacknowledged_alarms), 1)
        self.update(610)
        self.effect.play.assert_called_once()
        self.update(660)
        self.assertEqual(self.effect.play.call_count, 2)
        self.assertFalse(self.sound.silenced)

    def test_critical_clear_stops_and_does_not_replay_old_warning(self):
        self.update(660)
        self.effect.stop.reset_mock()
        self.update(630)
        self.effect.stop.assert_called_once()
        self.effect.play.assert_called_once()

    def test_volume_and_shutdown(self):
        self.sound.set_volume(50)
        self.effect.setVolume.assert_called_with(0.25)
        self.sound.set_volume(0)
        self.effect.setVolume.assert_called_with(0)
        self.sound.stop()
        self.effect.stop.assert_called()


if __name__ == "__main__":
    unittest.main()
