"""Non-blocking audible annunciation, tracked by alarm occurrence IDs."""

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect

from models.alarm import AlarmPriority


class AlarmSound(QObject):
    def __init__(self, parent=None, effect=None):
        super().__init__(parent)
        self.effect = effect if effect is not None else QSoundEffect(self)
        self.effect.setVolume(0.25)
        self.effect.setSource(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "assets" / "alarm_buzzer.wav")))
        self._seen = set()
        self._silenced = set()
        self._sounding_ids = set()
        self._critical = False

    def update(self, records):
        active = {r.event_id: r for r in records if r.active and not r.acknowledged}
        ids = set(active)
        new = ids - self._seen
        self._seen = ids
        self._silenced.intersection_update(ids)
        eligible = ids - self._silenced
        critical = {i for i in eligible if active[i].definition.priority == AlarmPriority.CRITICAL}
        if critical:
            if not self._critical:
                self.effect.stop()
                self.effect.setLoopCount(QSoundEffect.Loop.Infinite.value)
                self.effect.play()
            self._critical = True
            self._sounding_ids = critical
        elif new & eligible:
            self.effect.stop()
            self.effect.setLoopCount(1)  # The WAV itself contains two short pulses.
            self.effect.play()
            self._critical = False
            self._sounding_ids = new & eligible
        elif self._critical or not (self._sounding_ids & eligible):
            self.stop()

    def silence(self):
        """Silence current occurrences only; future alarms can sound again."""
        self._silenced.update(self._seen)
        self.stop()

    @property
    def silenced(self):
        return bool(self._seen) and self._seen <= self._silenced

    def stop(self):
        self.effect.stop()
        self._critical = False
        self._sounding_ids.clear()

    def set_volume(self, percent):
        self.effect.setVolume((max(0, min(100, percent)) / 100.0) ** 2)
