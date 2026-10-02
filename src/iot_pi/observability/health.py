"""Runtime health tracking for long-running IoT processes."""

from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic


@dataclass(frozen=True, slots=True)
class HealthSnapshot:
    """Immutable snapshot of runtime health."""

    uptime_seconds: float
    sensor_failures: int
    last_successful_sample: datetime | None
    backlog_size: int


class HealthTracker:
    """Track operational health independently from transport or storage."""

    def __init__(self) -> None:
        """Initialize an empty health tracker."""
        self._started_at = monotonic()
        self._sensor_failures = 0
        self._last_successful_sample: datetime | None = None
        self._backlog_size = 0

    def record_success(self, *, timestamp: datetime | None = None) -> None:
        """Record a successful sample or processing cycle."""
        value = timestamp or datetime.now(UTC)
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone information")
        self._last_successful_sample = value

    def record_sensor_failure(self) -> None:
        """Increment the sensor failure counter."""
        self._sensor_failures += 1

    def set_backlog_size(self, size: int) -> None:
        """Update queue or backlog size."""
        if size < 0:
            raise ValueError("backlog size must not be negative")
        self._backlog_size = size

    def snapshot(self) -> HealthSnapshot:
        """Return the current health state."""
        return HealthSnapshot(
            uptime_seconds=max(0.0, monotonic() - self._started_at),
            sensor_failures=self._sensor_failures,
            last_successful_sample=self._last_successful_sample,
            backlog_size=self._backlog_size,
        )
