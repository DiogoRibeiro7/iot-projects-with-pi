"""Health snapshot persistence and publishing observers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from iot_pi.messaging.interfaces import MessagePublisher
from iot_pi.messaging.topics import state_topic
from iot_pi.observability.health import HealthSnapshot

HealthObserver = Callable[[HealthSnapshot], None]


class HealthStateFile:
    """Persist the latest health snapshot as an atomic JSON file."""

    def __init__(self, path: Path) -> None:
        """Create a state-file observer."""
        self._path = path

    def __call__(self, snapshot: HealthSnapshot) -> None:
        """Write one snapshot atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        temporary.write_text(snapshot.to_json() + "\n", encoding="utf-8")
        temporary.replace(self._path)

    def read(self) -> HealthSnapshot:
        """Read the most recently persisted snapshot."""
        return HealthSnapshot.from_json(self._path.read_text(encoding="utf-8"))


class MqttHealthStatePublisher:
    """Publish retained device health through an existing message publisher."""

    def __init__(
        self,
        publisher: MessagePublisher,
        *,
        device_id: str,
        qos: int = 1,
    ) -> None:
        """Create a retained health-state publisher."""
        if not device_id.strip():
            raise ValueError("device_id must not be empty")
        if qos not in {0, 1, 2}:
            raise ValueError("qos must be 0, 1, or 2")

        self._publisher = publisher
        self._device_id = device_id
        self._qos = qos

    def __call__(self, snapshot: HealthSnapshot) -> None:
        """Publish the health snapshot as retained MQTT state."""
        self._publisher.publish(
            state_topic(self._device_id, "health"),
            snapshot.to_json(),
            qos=self._qos,
            retain=True,
        )


class CompositeHealthObserver:
    """Forward each health snapshot to multiple observers."""

    def __init__(self, *observers: HealthObserver) -> None:
        """Create a composite observer."""
        self._observers = observers

    def __call__(self, snapshot: HealthSnapshot) -> None:
        """Forward one snapshot to every configured observer."""
        for observer in self._observers:
            observer(snapshot)
