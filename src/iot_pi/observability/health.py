"""Runtime health tracking for long-running IoT processes."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite
from time import monotonic
from typing import Any

HealthObserver = Callable[["HealthSnapshot"], None]


@dataclass(frozen=True, slots=True)
class HealthSnapshot:
    """Immutable snapshot of runtime health."""

    uptime_seconds: float
    sensor_failures: int
    last_successful_sample: datetime | None
    backlog_size: int

    def __post_init__(self) -> None:
        """Validate health metric bounds."""
        if not isfinite(self.uptime_seconds) or self.uptime_seconds < 0:
            raise ValueError("uptime_seconds must be a non-negative finite number")
        if isinstance(self.sensor_failures, bool) or self.sensor_failures < 0:
            raise ValueError("sensor_failures must be a non-negative integer")
        if isinstance(self.backlog_size, bool) or self.backlog_size < 0:
            raise ValueError("backlog_size must be a non-negative integer")
        if (
            self.last_successful_sample is not None
            and self.last_successful_sample.tzinfo is None
        ):
            raise ValueError("last_successful_sample must include timezone information")

    def to_dict(self) -> dict[str, Any]:
        """Return the stable JSON-ready health schema."""
        return {
            "uptime_seconds": self.uptime_seconds,
            "sensor_failures": self.sensor_failures,
            "last_successful_sample": (
                None
                if self.last_successful_sample is None
                else self.last_successful_sample.astimezone(UTC).isoformat()
            ),
            "backlog_size": self.backlog_size,
        }

    def to_json(self) -> str:
        """Serialize the health snapshot using the stable schema."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, payload: str) -> "HealthSnapshot":
        """Parse and validate a serialized health snapshot."""
        raw = json.loads(payload)
        if not isinstance(raw, dict):
            raise ValueError("health payload must be a JSON object")

        uptime_seconds = raw.get("uptime_seconds")
        sensor_failures = raw.get("sensor_failures")
        last_successful_sample = raw.get("last_successful_sample")
        backlog_size = raw.get("backlog_size")

        if not isinstance(uptime_seconds, (int, float)):
            raise ValueError("uptime_seconds must be numeric")
        if not isinstance(sensor_failures, int) or isinstance(sensor_failures, bool):
            raise ValueError("sensor_failures must be an integer")
        if not isinstance(backlog_size, int) or isinstance(backlog_size, bool):
            raise ValueError("backlog_size must be an integer")
        if last_successful_sample is not None and not isinstance(
            last_successful_sample,
            str,
        ):
            raise ValueError("last_successful_sample must be an ISO-8601 string or null")

        parsed_timestamp = (
            None
            if last_successful_sample is None
            else datetime.fromisoformat(last_successful_sample)
        )

        return cls(
            uptime_seconds=float(uptime_seconds),
            sensor_failures=sensor_failures,
            last_successful_sample=parsed_timestamp,
            backlog_size=backlog_size,
        )


class HealthTracker:
    """Track operational health independently from transport or storage."""

    def __init__(self, *, observer: HealthObserver | None = None) -> None:
        """Initialize an empty health tracker."""
        self._started_at = monotonic()
        self._sensor_failures = 0
        self._last_successful_sample: datetime | None = None
        self._backlog_size = 0
        self._observer = observer

    def record_success(self, *, timestamp: datetime | None = None) -> None:
        """Record a successful sample or processing cycle."""
        value = timestamp or datetime.now(UTC)
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone information")
        self._last_successful_sample = value
        self._emit()

    def record_sensor_failure(self) -> None:
        """Increment the sensor failure counter."""
        self._sensor_failures += 1
        self._emit()

    def set_backlog_size(self, size: int) -> None:
        """Update queue or backlog size."""
        if size < 0:
            raise ValueError("backlog size must not be negative")
        self._backlog_size = size
        self._emit()

    def snapshot(self) -> HealthSnapshot:
        """Return the current health state."""
        return HealthSnapshot(
            uptime_seconds=max(0.0, monotonic() - self._started_at),
            sensor_failures=self._sensor_failures,
            last_successful_sample=self._last_successful_sample,
            backlog_size=self._backlog_size,
        )

    def _emit(self) -> None:
        """Send the current snapshot to the configured observer."""
        if self._observer is not None:
            self._observer(self.snapshot())
