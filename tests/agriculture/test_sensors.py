"""Tests for smart-agriculture soil sensors."""

from typing import Any

import pytest

from iot_pi.agriculture.sensors import (
    Mcp3008SoilMoistureSensor,
    SequenceSoilMoistureSensor,
    SimulatedSoilMoistureSensor,
)
from iot_pi.hardware.errors import HardwareUnavailableError


class FakeMcp3008:
    """Minimal MCP3008 test double."""

    value = 0.55

    def __init__(self, *, channel: int) -> None:
        self.channel = channel
        self.closed = False

    def close(self) -> None:
        """Record cleanup."""
        self.closed = True


class BrokenMcp3008:
    """MCP3008 test double that fails at initialization."""

    def __init__(self, *, channel: int) -> None:
        raise OSError(f"SPI unavailable for channel {channel}")


def test_simulated_sensor_is_deterministic() -> None:
    """A fixed seed should reproduce the generated moisture stream."""
    first = SimulatedSoilMoistureSensor(seed=7)
    second = SimulatedSoilMoistureSensor(seed=7)

    first.open()
    second.open()
    try:
        assert [first.read() for _ in range(5)] == [second.read() for _ in range(5)]
    finally:
        first.close()
        second.close()


def test_simulated_sensor_requires_open_lifecycle() -> None:
    """Simulator reads before open should fail."""
    sensor = SimulatedSoilMoistureSensor()

    with pytest.raises(HardwareUnavailableError, match="not open"):
        sensor.read()


@pytest.mark.parametrize(
    ("base", "variation"),
    [(-1.0, 5.0), (101.0, 5.0), (50.0, -1.0), (50.0, 101.0)],
)
def test_simulator_rejects_invalid_configuration(
    base: float,
    variation: float,
) -> None:
    """Simulator configuration should remain physically meaningful."""
    with pytest.raises(ValueError):
        SimulatedSoilMoistureSensor(
            base_moisture_percent=base,
            variation_percent=variation,
        )


def test_sequence_sensor_wraps_fixture_readings() -> None:
    """A deterministic fixture should repeat after its last reading."""
    sensor = SequenceSoilMoistureSensor([20.0, 40.0])
    sensor.open()
    try:
        assert [sensor.read(), sensor.read(), sensor.read()] == [20.0, 40.0, 20.0]
    finally:
        sensor.close()


def test_sequence_sensor_validates_fixture_and_lifecycle() -> None:
    """Fixture values and lifecycle should be validated."""
    with pytest.raises(ValueError, match="must not be empty"):
        SequenceSoilMoistureSensor([])
    with pytest.raises(ValueError, match="between 0 and 100"):
        SequenceSoilMoistureSensor([101.0])

    sensor = SequenceSoilMoistureSensor([25.0])
    with pytest.raises(HardwareUnavailableError, match="not open"):
        sensor.read()


@pytest.mark.parametrize(
    ("channel", "dry_raw", "wet_raw"),
    [(-1, 0.8, 0.3), (8, 0.8, 0.3), (0, -0.1, 0.3), (0, 0.8, 1.1), (0, 0.5, 0.5)],
)
def test_mcp3008_sensor_validates_calibration(
    channel: int,
    dry_raw: float,
    wet_raw: float,
) -> None:
    """ADC channel and calibration endpoints must be valid."""
    with pytest.raises(ValueError):
        Mcp3008SoilMoistureSensor(
            channel,
            dry_raw=dry_raw,
            wet_raw=wet_raw,
        )


def test_mcp3008_sensor_calibrates_raw_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raw ADC values should map to a bounded moisture percentage."""
    monkeypatch.setattr(
        "iot_pi.agriculture.sensors._load_mcp3008",
        lambda: FakeMcp3008,
    )
    sensor = Mcp3008SoilMoistureSensor(2, dry_raw=0.8, wet_raw=0.3)

    with pytest.raises(HardwareUnavailableError, match="not open"):
        sensor.read()

    sensor.open()
    sensor.open()
    device: Any = sensor._device
    try:
        assert sensor.read() == 50.0
        assert device.channel == 2
    finally:
        sensor.close()
        sensor.close()

    assert device.closed is True


def test_mcp3008_sensor_wraps_initialization_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SPI initialization failures should map to the public hardware error."""
    monkeypatch.setattr(
        "iot_pi.agriculture.sensors._load_mcp3008",
        lambda: BrokenMcp3008,
    )
    sensor = Mcp3008SoilMoistureSensor()

    with pytest.raises(HardwareUnavailableError, match="unable to initialize"):
        sensor.open()
