"""Tests for weather-station sensor adapters."""

import pytest

from iot_pi.hardware.errors import HardwareUnavailableError
from iot_pi.weather.sensors import SimulatedTemperatureHumiditySensor


def test_simulated_sensor_is_deterministic() -> None:
    """A fixed seed should reproduce the complete generated stream."""
    first = SimulatedTemperatureHumiditySensor(seed=7)
    second = SimulatedTemperatureHumiditySensor(seed=7)

    first.open()
    second.open()
    try:
        first_readings = [first.read() for _ in range(5)]
        second_readings = [second.read() for _ in range(5)]
        assert first_readings == second_readings
    finally:
        first.close()
        second.close()


def test_simulated_sensor_seed_affects_generated_stream() -> None:
    """Different seeds should produce different simulated observations."""
    first = SimulatedTemperatureHumiditySensor(seed=7)
    second = SimulatedTemperatureHumiditySensor(seed=8)

    first.open()
    second.open()
    try:
        assert [first.read() for _ in range(3)] != [second.read() for _ in range(3)]
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize(
    ("temperature", "humidity"),
    [(-80.0, 55.0), (80.0, 55.0), (21.0, 0.0), (21.0, 100.0)],
)
def test_simulated_sensor_rejects_unsafe_baselines(
    temperature: float,
    humidity: float,
) -> None:
    """Simulator baselines must leave room for random variation."""
    with pytest.raises(ValueError):
        SimulatedTemperatureHumiditySensor(
            base_temperature_c=temperature,
            base_humidity_percent=humidity,
        )


def test_simulated_sensor_requires_open_lifecycle() -> None:
    """Reading before opening should fail consistently."""
    sensor = SimulatedTemperatureHumiditySensor()

    with pytest.raises(HardwareUnavailableError, match="not open"):
        sensor.read()
