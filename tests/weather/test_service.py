"""Tests for weather-station orchestration."""

from datetime import UTC, datetime
from pathlib import Path

from iot_pi.weather.sensors import SimulatedTemperatureHumiditySensor
from iot_pi.weather.service import WeatherStation
from iot_pi.weather.storage import SQLiteWeatherStore


def test_station_samples_and_persists_observation(tmp_path: Path) -> None:
    """A weather sample should be stored locally."""
    sensor = SimulatedTemperatureHumiditySensor(seed=1)
    store = SQLiteWeatherStore(tmp_path / "weather.db")
    station = WeatherStation(
        sensor,
        store,
        sample_interval_seconds=5.0,
        clock=lambda: datetime(2026, 10, 1, tzinfo=UTC),
    )

    station.open()
    try:
        observation = station.sample_once()
        assert observation.timestamp == datetime(2026, 10, 1, tzinfo=UTC)
        assert store.count() == 1
    finally:
        station.close()


def test_station_run_uses_configured_sampling_interval(tmp_path: Path) -> None:
    """Periodic execution should sleep between observations only."""
    sleeps: list[float] = []
    sensor = SimulatedTemperatureHumiditySensor(seed=1)
    store = SQLiteWeatherStore(tmp_path / "weather.db")
    station = WeatherStation(
        sensor,
        store,
        sample_interval_seconds=2.5,
        sleeper=sleeps.append,
    )

    station.open()
    try:
        completed = station.run(samples=3)
        assert completed == 3
        assert store.count() == 3
        assert sleeps == [2.5, 2.5]
    finally:
        station.close()
