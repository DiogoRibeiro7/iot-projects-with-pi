"""Tests for weather-station sensor adapters."""

import pytest

from iot_pi.hardware.errors import HardwareUnavailableError
from iot_pi.weather.sensors import SimulatedTemperatureHumiditySensor


def test_simulated_sensor_is_deterministic() -> None:
    """The simulator should reproduce readings for a fixed seed."""
    first = SimulatedTemperatureHumiditySensor(seed=7)
    second = SimulatedTemperatureHumiditySensor(seed=7)

    first.open()
    second.open()
    try:
        assert first.read() == second.read()
    finally:
        first.close()
        second.close()


def test_simulated_sensor_requires_open_lifecycle() -> None:
    """Reading before opening should fail consistently."""
    sensor = SimulatedTemperatureHumiditySensor()

    with pytest.raises(HardwareUnavailableError, match="not open"):
        sensor.read()
