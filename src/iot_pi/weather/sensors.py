"""Weather-station sensor adapters."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Any

from iot_pi.hardware.errors import HardwareUnavailableError
from iot_pi.hardware.interfaces import (
    TemperatureHumidityReading,
    TemperatureHumiditySensor,
)


@dataclass(slots=True)
class SimulatedTemperatureHumiditySensor:
    """Deterministic simulator for local development and CI."""

    seed: int = 42
    base_temperature_c: float = 21.0
    base_humidity_percent: float = 55.0
    _random: Random | None = None

    def open(self) -> None:
        """Initialize the deterministic random generator."""
        if self._random is None:
            self._random = Random(self.seed)

    def close(self) -> None:
        """Release simulator state."""
        self._random = None

    def read(self) -> TemperatureHumidityReading:
        """Generate one plausible environmental reading."""
        if self._random is None:
            raise HardwareUnavailableError("simulated sensor is not open")

        temperature = self.base_temperature_c + self._random.uniform(-1.0, 1.0)
        humidity = self.base_humidity_percent + self._random.uniform(-3.0, 3.0)
        return TemperatureHumidityReading(
            temperature_c=round(temperature, 2),
            relative_humidity_percent=round(humidity, 2),
        )


class DhtTemperatureHumiditySensor:
    """DHT11/DHT22 adapter using Adafruit CircuitPython libraries."""

    def __init__(self, pin_name: str, *, model: str = "DHT22") -> None:
        """Create an unopened DHT sensor adapter."""
        normalized = model.upper()
        if normalized not in {"DHT11", "DHT22"}:
            raise ValueError("model must be either 'DHT11' or 'DHT22'")

        self._pin_name = pin_name
        self._model = normalized
        self._device: Any | None = None

    def open(self) -> None:
        """Initialize the DHT sensor lazily on Raspberry Pi hardware."""
        if self._device is not None:
            return

        try:
            import adafruit_dht
            import board
        except (ImportError, OSError) as exc:
            raise HardwareUnavailableError(
                "DHT dependencies are unavailable; install the 'dht' extra on a Raspberry Pi"
            ) from exc

        try:
            pin = getattr(board, self._pin_name)
        except AttributeError as exc:
            raise HardwareUnavailableError(
                f"unknown Raspberry Pi board pin: {self._pin_name}"
            ) from exc

        sensor_type = adafruit_dht.DHT22 if self._model == "DHT22" else adafruit_dht.DHT11
        try:
            self._device = sensor_type(pin)
        except (RuntimeError, ValueError, OSError) as exc:
            raise HardwareUnavailableError("unable to initialize DHT sensor") from exc

    def close(self) -> None:
        """Release the DHT device."""
        if self._device is not None:
            self._device.exit()
            self._device = None

    def read(self) -> TemperatureHumidityReading:
        """Read temperature and relative humidity from the sensor."""
        if self._device is None:
            raise HardwareUnavailableError("DHT sensor is not open")

        try:
            temperature = self._device.temperature
            humidity = self._device.humidity
        except (RuntimeError, OSError) as exc:
            raise HardwareUnavailableError("unable to read DHT sensor") from exc

        if temperature is None or humidity is None:
            raise HardwareUnavailableError("DHT sensor returned a missing reading")

        return TemperatureHumidityReading(
            temperature_c=float(temperature),
            relative_humidity_percent=float(humidity),
        )


def assert_temperature_sensor(sensor: TemperatureHumiditySensor) -> None:
    """Validate structural conformance for callers constructing adapters dynamically."""
    if not isinstance(sensor, TemperatureHumiditySensor):
        raise TypeError("sensor does not satisfy TemperatureHumiditySensor")
