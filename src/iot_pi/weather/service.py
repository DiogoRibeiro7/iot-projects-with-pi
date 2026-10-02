"""Weather-station application service."""

import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from math import isfinite

from iot_pi.hardware.interfaces import TemperatureHumiditySensor
from iot_pi.observability.health import HealthTracker
from iot_pi.observability.storage import SQLiteEventRepository
from iot_pi.weather.models import WeatherObservation
from iot_pi.weather.storage import SQLiteWeatherStore

Clock = Callable[[], datetime]
Sleeper = Callable[[float], None]


class WeatherStation:
    """Coordinate sensor acquisition, validation, persistence, and logging."""

    def __init__(
        self,
        sensor: TemperatureHumiditySensor,
        store: SQLiteWeatherStore,
        *,
        sample_interval_seconds: float,
        clock: Clock | None = None,
        sleeper: Sleeper | None = None,
        logger: logging.Logger | None = None,
        health: HealthTracker | None = None,
        events: SQLiteEventRepository | None = None,
    ) -> None:
        """Create a weather-station service."""
        if not isfinite(sample_interval_seconds) or sample_interval_seconds <= 0:
            raise ValueError(
                "sample_interval_seconds must be a positive finite number"
            )

        if not isinstance(sensor, TemperatureHumiditySensor):
            raise TypeError("sensor does not satisfy TemperatureHumiditySensor")

        self._sensor = sensor
        self._store = store
        self._sample_interval_seconds = sample_interval_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sleeper = sleeper or time.sleep
        self._logger = logger or logging.getLogger("iot_pi.weather")
        self._health = health
        self._events = events

    def open(self) -> None:
        """Initialize sensor and storage resources safely."""
        self._sensor.open()
        try:
            self._store.open()
            if self._events is not None:
                self._events.open()
        except Exception:
            self._sensor.close()
            self._store.close()
            if self._events is not None:
                self._events.close()
            raise

    def close(self) -> None:
        """Release sensor and storage resources."""
        try:
            self._sensor.close()
        finally:
            try:
                self._store.close()
            finally:
                if self._events is not None:
                    self._events.close()

    def sample_once(self) -> WeatherObservation:
        """Collect, validate, persist, and log one observation."""
        try:
            reading = self._sensor.read()
        except Exception:
            if self._health is not None:
                self._health.record_sensor_failure()
            raise

        observation = WeatherObservation(
            timestamp=self._clock(),
            temperature_c=reading.temperature_c,
            relative_humidity_percent=reading.relative_humidity_percent,
        )
        self._store.save(observation)

        if self._health is not None:
            self._health.record_success(timestamp=observation.timestamp)

        event_payload = {
            "temperature_c": observation.temperature_c,
            "relative_humidity_percent": observation.relative_humidity_percent,
            "pressure_hpa": observation.pressure_hpa,
        }
        if self._events is not None:
            self._events.append(
                "weather_observation",
                event_payload,
                timestamp=observation.timestamp,
            )

        self._logger.info(
            json.dumps(
                {
                    "event": "weather_observation",
                    "timestamp": observation.timestamp.isoformat(),
                    **event_payload,
                },
                sort_keys=True,
            )
        )
        return observation

    def run(self, *, samples: int | None = None) -> int:
        """Run periodic acquisition until the requested sample count is reached."""
        if samples is not None and samples <= 0:
            raise ValueError("samples must be greater than zero when provided")

        completed = 0
        while samples is None or completed < samples:
            self.sample_once()
            completed += 1
            if samples is None or completed < samples:
                self._sleeper(self._sample_interval_seconds)

        return completed
