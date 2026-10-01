"""Tests for weather-station domain models."""

from datetime import UTC, datetime

import pytest

from iot_pi.weather.models import WeatherObservation


def test_weather_observation_accepts_valid_values() -> None:
    """Valid environmental observations should be accepted."""
    observation = WeatherObservation(
        timestamp=datetime(2026, 10, 1, tzinfo=UTC),
        temperature_c=21.5,
        relative_humidity_percent=55.0,
        pressure_hpa=1013.2,
    )

    assert observation.temperature_c == 21.5


@pytest.mark.parametrize("temperature", [-81.0, 81.0])
def test_weather_observation_rejects_invalid_temperature(temperature: float) -> None:
    """Extreme temperatures outside the supported range should fail."""
    with pytest.raises(ValueError, match="temperature_c"):
        WeatherObservation(
            timestamp=datetime.now(UTC),
            temperature_c=temperature,
            relative_humidity_percent=50.0,
        )


@pytest.mark.parametrize("humidity", [-1.0, 101.0])
def test_weather_observation_rejects_invalid_humidity(humidity: float) -> None:
    """Relative humidity must remain in the physical percentage range."""
    with pytest.raises(ValueError, match="relative_humidity_percent"):
        WeatherObservation(
            timestamp=datetime.now(UTC),
            temperature_c=20.0,
            relative_humidity_percent=humidity,
        )


@pytest.mark.parametrize("pressure", [299.0, 1201.0])
def test_weather_observation_rejects_invalid_pressure(pressure: float) -> None:
    """Pressure outside the supported atmospheric range should fail."""
    with pytest.raises(ValueError, match="pressure_hpa"):
        WeatherObservation(
            timestamp=datetime.now(UTC),
            temperature_c=20.0,
            relative_humidity_percent=50.0,
            pressure_hpa=pressure,
        )
