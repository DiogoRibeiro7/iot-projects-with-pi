"""Tests for irrigation controller orchestration."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from iot_pi.agriculture.rules import IrrigationPolicy
from iot_pi.agriculture.sensors import SequenceSoilMoistureSensor
from iot_pi.agriculture.service import IrrigationController
from iot_pi.agriculture.storage import SQLiteAgricultureStore
from iot_pi.hardware.fake import FakeDigitalOutput
from iot_pi.messaging.fake import InMemoryPublisher
from iot_pi.observability.health import HealthTracker
from iot_pi.observability.storage import SQLiteEventRepository
from iot_pi.weather.sensors import SimulatedTemperatureHumiditySensor


def test_controller_drives_pump_persistence_events_and_telemetry(
    tmp_path: Path,
) -> None:
    """One irrigation cycle should update every configured output."""
    pump = FakeDigitalOutput()
    health = HealthTracker()
    events = SQLiteEventRepository(tmp_path / "events.db")
    telemetry = InMemoryPublisher()
    store = SQLiteAgricultureStore(tmp_path / "agriculture.db")
    controller = IrrigationController(
        SequenceSoilMoistureSensor([24.0]),
        pump,
        store,
        policy=IrrigationPolicy(),
        climate_sensor=SimulatedTemperatureHumiditySensor(seed=1),
        health=health,
        events=events,
        telemetry_publisher=telemetry,
        device_id="farm-01",
        clock=lambda: datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
    )

    controller.open()
    try:
        result = controller.evaluate_once()

        assert result.soil_moisture_percent == 24.0
        assert result.pump_on is True
        assert result.reason == "soil_dry"
        assert result.temperature_c is not None
        assert pump.read() is True
        assert store.count() == 1
        assert store.latest() == result
        assert events.count() == 1
        assert health.snapshot().last_successful_sample == result.timestamp
        assert telemetry.messages[0].topic == "iot/farm-01/telemetry/agriculture"
        assert '"pump_on":true' in telemetry.messages[0].payload
    finally:
        controller.close()

    assert pump._state is False


def test_controller_works_without_optional_climate_or_telemetry(
    tmp_path: Path,
) -> None:
    """The minimal local controller should need only soil, pump, and storage."""
    controller = IrrigationController(
        SequenceSoilMoistureSensor([50.0]),
        FakeDigitalOutput(),
        SQLiteAgricultureStore(tmp_path / "agriculture.db"),
        policy=IrrigationPolicy(),
    )

    controller.open()
    try:
        result = controller.evaluate_once()
        assert result.pump_on is False
        assert result.temperature_c is None
        assert result.relative_humidity_percent is None
    finally:
        controller.close()


class FailingSoilSensor(SequenceSoilMoistureSensor):
    """Sensor fixture that fails during reads."""

    def read(self) -> float:
        """Simulate a hardware failure."""
        raise RuntimeError("soil sensor failed")


def test_controller_records_sensor_failures(tmp_path: Path) -> None:
    """Read failures should update health state."""
    health = HealthTracker()
    controller = IrrigationController(
        FailingSoilSensor([20.0]),
        FakeDigitalOutput(),
        SQLiteAgricultureStore(tmp_path / "agriculture.db"),
        policy=IrrigationPolicy(),
        health=health,
    )

    controller.open()
    try:
        with pytest.raises(RuntimeError, match="soil sensor failed"):
            controller.evaluate_once()
        assert health.snapshot().sensor_failures == 1
    finally:
        controller.close()


def test_store_persists_across_reopen(tmp_path: Path) -> None:
    """Agriculture observations should survive connection restart."""
    path = tmp_path / "agriculture.db"
    controller = IrrigationController(
        SequenceSoilMoistureSensor([25.0]),
        FakeDigitalOutput(),
        SQLiteAgricultureStore(path),
        policy=IrrigationPolicy(),
    )

    controller.open()
    try:
        expected = controller.evaluate_once()
    finally:
        controller.close()

    store = SQLiteAgricultureStore(path)
    store.open()
    try:
        assert store.count() == 1
        assert store.latest() == expected
    finally:
        store.close()


def test_store_requires_open_lifecycle(tmp_path: Path) -> None:
    """Closed stores should reject persistence operations."""
    store = SQLiteAgricultureStore(tmp_path / "agriculture.db")

    with pytest.raises(RuntimeError, match="not open"):
        store.count()
    with pytest.raises(RuntimeError, match="not open"):
        store.latest()

    store.open()
    store.open()
    store.close()
    store.close()
