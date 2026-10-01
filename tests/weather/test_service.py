"""Tests for weather-station orchestration."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from iot_pi.hardware.interfaces import TemperatureHumidityReading
from iot_pi.weather.sensors import SimulatedTemperatureHumiditySensor
from iot_pi.weather.service import WeatherStation
from iot_pi.weather.storage import SQLiteWeatherStore


class FailingStore(SQLiteWeatherStore):
    """Store test double that fails during startup."""

    def open(self) -> None:
        """Simulate a database initialization failure."""
        raise RuntimeError("database unavailable")


class TrackingSensor:
    """Sensor test double used to verify cleanup."""

    def __init__(self) -> None:
        self.is_open = False

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False

    def read(self) -> TemperatureHumidityReading:
        return TemperatureHumidityReading(20.0, 50.0)


def test_station_samples_and_persists_observation(tmp_path: Path) -> None:
    """A weather sample should be stored locally without altering values."""
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
        persisted = store.latest()

        assert persisted == observation
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


@pytest.mark.parametrize("interval", [0.0, -1.0, float("nan"), float("inf")])
def test_station_rejects_invalid_intervals(
    tmp_path: Path,
    interval: float,
) -> None:
    """Intervals must be positive finite numbers."""
    with pytest.raises(ValueError, match="positive finite"):
        WeatherStation(
            SimulatedTemperatureHumiditySensor(),
            SQLiteWeatherStore(tmp_path / "weather.db"),
            sample_interval_seconds=interval,
        )


def test_station_closes_sensor_when_store_open_fails(tmp_path: Path) -> None:
    """Partial startup failures must not leak an active sensor."""
    sensor = TrackingSensor()
    station = WeatherStation(
        sensor,
        FailingStore(tmp_path / "weather.db"),
        sample_interval_seconds=1.0,
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        station.open()

    assert sensor.is_open is False
