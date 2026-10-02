"""Integration tests for service-level observability hooks."""

from datetime import UTC, datetime
from pathlib import Path

from iot_pi.hardware.fake import FakeDigitalInput, FakeDigitalOutput
from iot_pi.home.rules import AutomationPolicy
from iot_pi.home.service import HomeAutomationController
from iot_pi.observability.health import HealthTracker
from iot_pi.observability.storage import SQLiteEventRepository
from iot_pi.weather.sensors import SimulatedTemperatureHumiditySensor
from iot_pi.weather.service import WeatherStation
from iot_pi.weather.storage import SQLiteWeatherStore


def test_weather_service_updates_health_and_events(tmp_path: Path) -> None:
    """Weather sampling should update shared health and event storage."""
    health = HealthTracker()
    events = SQLiteEventRepository(tmp_path / "events.db")
    station = WeatherStation(
        SimulatedTemperatureHumiditySensor(seed=1),
        SQLiteWeatherStore(tmp_path / "weather.db"),
        sample_interval_seconds=1.0,
        clock=lambda: datetime(2026, 10, 2, 12, 0, tzinfo=UTC),
        health=health,
        events=events,
    )

    station.open()
    try:
        station.sample_once()
        snapshot = health.snapshot()

        assert snapshot.sensor_failures == 0
        assert snapshot.last_successful_sample == datetime(
            2026,
            10,
            2,
            12,
            0,
            tzinfo=UTC,
        )
        assert events.count() == 1
    finally:
        station.close()


def test_home_service_updates_health_and_events(tmp_path: Path) -> None:
    """Home automation decisions should be observable through shared services."""
    health = HealthTracker()
    events = SQLiteEventRepository(tmp_path / "events.db")
    controller = HomeAutomationController(
        SimulatedTemperatureHumiditySensor(
            seed=1,
            base_temperature_c=29.0,
            base_humidity_percent=50.0,
        ),
        FakeDigitalInput(state=True),
        FakeDigitalOutput(),
        policy=AutomationPolicy(),
        health=health,
        events=events,
    )

    controller.open()
    try:
        controller.evaluate_once()

        assert health.snapshot().last_successful_sample is not None
        assert events.count() == 1
    finally:
        controller.close()
