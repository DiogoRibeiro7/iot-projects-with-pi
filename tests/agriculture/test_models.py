"""Tests for agriculture observation validation."""

from datetime import UTC, datetime

import pytest

from iot_pi.agriculture.models import AgricultureObservation


def observation(**overrides: object) -> AgricultureObservation:
    """Create a valid observation with selected overrides."""
    values: dict[str, object] = {
        "timestamp": datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
        "soil_moisture_percent": 35.0,
        "pump_on": False,
        "reason": "moisture_sufficient",
        "temperature_c": 21.0,
        "relative_humidity_percent": 55.0,
    }
    values.update(overrides)
    return AgricultureObservation(**values)  # type: ignore[arg-type]


def test_observation_accepts_valid_climate_context() -> None:
    """A complete climate context should be preserved."""
    value = observation()

    assert value.temperature_c == 21.0
    assert value.relative_humidity_percent == 55.0


@pytest.mark.parametrize("moisture", [-1.0, 101.0])
def test_observation_rejects_invalid_soil_moisture(moisture: float) -> None:
    """Soil moisture must remain in percentage bounds."""
    with pytest.raises(ValueError, match="soil_moisture_percent"):
        observation(soil_moisture_percent=moisture)


def test_observation_rejects_empty_reason() -> None:
    """Decision reason must remain meaningful."""
    with pytest.raises(ValueError, match="reason"):
        observation(reason=" ")


def test_observation_requires_paired_climate_values() -> None:
    """Temperature and humidity context must be provided together."""
    with pytest.raises(ValueError, match="must be set together"):
        observation(relative_humidity_percent=None)


@pytest.mark.parametrize(
    ("temperature", "humidity"),
    [(81.0, 50.0), (20.0, 101.0)],
)
def test_observation_rejects_invalid_climate_values(
    temperature: float,
    humidity: float,
) -> None:
    """Climate values should use the shared supported ranges."""
    with pytest.raises(ValueError):
        observation(
            temperature_c=temperature,
            relative_humidity_percent=humidity,
        )
