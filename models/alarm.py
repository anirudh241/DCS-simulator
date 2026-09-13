"""Process-alarm definitions and lifecycle management.

The alarm model is deliberately independent of Qt. It can therefore be
tested without starting the HMI and reused by future displays or loggers.
"""

from dataclasses import dataclass
from enum import Enum, IntEnum


class AlarmDirection(Enum):
    """The side of a limit that places an alarm in the active state."""

    HIGH = "high"
    LOW = "low"


class AlarmPriority(IntEnum):
    """Alarm priority in increasing order of operational importance."""

    WARNING = 1
    CRITICAL = 2


class AlarmState(Enum):
    """Operator-visible states supported by the simulator."""

    ACTIVE_UNACKNOWLEDGED = "ACTIVE UNACKNOWLEDGED"
    ACTIVE_ACKNOWLEDGED = "ACTIVE ACKNOWLEDGED"
    CLEARED = "CLEARED"


@dataclass(frozen=True)
class AlarmDefinition:
    """Configuration for one process alarm."""

    key: str
    tag: str
    message: str
    direction: AlarmDirection
    limit: float
    priority: AlarmPriority
    hysteresis: float = 10.0
    unit: str = "mm"

    def is_active(self, value):
        if self.direction is AlarmDirection.HIGH:
            return value >= self.limit
        return value <= self.limit

    def should_clear(self, value):
        if self.direction is AlarmDirection.HIGH:
            return value <= self.limit - self.hysteresis
        return value >= self.limit + self.hysteresis


@dataclass
class AlarmRecord:
    """One occurrence of an alarm, retained after it clears."""

    event_id: int
    definition: AlarmDefinition
    activated_at: float
    value: float
    acknowledged: bool = False
    active: bool = True
    cleared_at: float | None = None

    @property
    def state(self):
        if not self.active:
            return AlarmState.CLEARED
        if self.acknowledged:
            return AlarmState.ACTIVE_ACKNOWLEDGED
        return AlarmState.ACTIVE_UNACKNOWLEDGED


DRUM_LEVEL_ALARMS = (
    AlarmDefinition(
        key="drum_level_high_high",
        tag="01LAHH001",
        message="DRUM LEVEL HIGH-HIGH",
        direction=AlarmDirection.HIGH,
        limit=650.0,
        priority=AlarmPriority.CRITICAL,
    ),
    AlarmDefinition(
        key="drum_level_high",
        tag="01LAH001",
        message="DRUM LEVEL HIGH",
        direction=AlarmDirection.HIGH,
        limit=600.0,
        priority=AlarmPriority.WARNING,
    ),
    AlarmDefinition(
        key="drum_level_low",
        tag="01LAL001",
        message="DRUM LEVEL LOW",
        direction=AlarmDirection.LOW,
        limit=400.0,
        priority=AlarmPriority.WARNING,
    ),
    AlarmDefinition(
        key="drum_level_low_low",
        tag="01LALL001",
        message="DRUM LEVEL LOW-LOW",
        direction=AlarmDirection.LOW,
        limit=350.0,
        priority=AlarmPriority.CRITICAL,
    ),
)


class AlarmManager:
    """Detect limits and maintain alarm acknowledgement/history state."""

    def __init__(self, definitions=DRUM_LEVEL_ALARMS, max_history=500):
        if max_history < 1:
            raise ValueError("max_history must be at least 1")

        self._definitions = tuple(definitions)
        self._max_history = max_history
        self._records = []
        self._active_by_key = {}
        self._next_event_id = 1

    @property
    def records(self):
        """Return newest occurrences first without exposing the list itself."""
        return tuple(reversed(self._records))

    @property
    def active_alarms(self):
        return tuple(
            sorted(
                self._active_by_key.values(),
                key=self._display_order,
            )
        )

    @property
    def unacknowledged_alarms(self):
        return tuple(
            alarm for alarm in self.active_alarms if not alarm.acknowledged
        )

    @property
    def highest_priority_alarm(self):
        alarms = self.unacknowledged_alarms or self.active_alarms
        return alarms[0] if alarms else None

    def update_drum_level(self, level_mm, time_seconds):
        """Evaluate all drum-level limits and return whether state changed."""
        changed = False
        value = float(level_mm)
        timestamp = float(time_seconds)

        for definition in self._definitions:
            active_record = self._active_by_key.get(definition.key)

            if active_record is None:
                if definition.is_active(value):
                    self._activate(definition, value, timestamp)
                    changed = True
                continue

            active_record.value = value
            if definition.should_clear(value):
                active_record.active = False
                active_record.cleared_at = timestamp
                del self._active_by_key[definition.key]
                changed = True

        if changed:
            self._trim_history()
        return changed

    def acknowledge(self, event_id):
        """Acknowledge one active occurrence by its stable event id."""
        alarm = next(
            (record for record in self._records if record.event_id == event_id),
            None,
        )
        if alarm is None or not alarm.active or alarm.acknowledged:
            return False

        alarm.acknowledged = True
        return True

    def acknowledge_all(self):
        """Acknowledge every currently active, unacknowledged alarm."""
        changed = False
        for alarm in self._active_by_key.values():
            if not alarm.acknowledged:
                alarm.acknowledged = True
                changed = True
        return changed

    def _activate(self, definition, value, timestamp):
        alarm = AlarmRecord(
            event_id=self._next_event_id,
            definition=definition,
            activated_at=timestamp,
            value=value,
        )
        self._next_event_id += 1
        self._records.append(alarm)
        self._active_by_key[definition.key] = alarm
        self._trim_history()

    def _trim_history(self):
        """Discard old cleared events while never orphaning an active alarm."""
        overflow = len(self._records) - self._max_history
        if overflow <= 0:
            return

        retained = []
        for record in self._records:
            if overflow > 0 and not record.active:
                overflow -= 1
                continue
            retained.append(record)
        self._records = retained

    @staticmethod
    def _display_order(alarm):
        return (
            -int(alarm.definition.priority),
            alarm.acknowledged,
            -alarm.activated_at,
        )
