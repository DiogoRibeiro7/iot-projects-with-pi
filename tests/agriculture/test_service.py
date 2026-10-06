"""Tests for irrigation controller orchestration."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from iot_pi.agriculture.rules import IrrigationPolicy
from iot_pi.agriculture.safety import (
    IrrigationSafetyConfig,
    IrrigationSafetyGuard,
)
from iot_pi.agriculture.sensors import SequenceSoilMoistureSensor
from iot_pi.agriculture.service import IrrigationController
from iot_pi.agriculture.storage import SQLiteAgricultureStore
from iot_pi.hardware.fake import FakeDigitalOutput
from iot_pi.messaging.fake import InMemoryPublisher
from iot_pi.messaging.models import TelemetryMessage
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


class MutableClock:
    """Deterministic monotonic clock for controller safety tests."""

    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class FailingPublisher:
    """Telemetry publisher that can simulate a downstream failure."""

    def __init__(self) -> None:
        self.fail = True
        self.messages: list[str] = []

    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        """Fail or capture one telemetry publication."""
        if self.fail:
            raise RuntimeError("telemetry unavailable")
        self.messages.append(payload)


def test_controller_enforces_timeout_cooldown_and_restart(
    tmp_path: Path,
) -> None:
    """The controller should persist safety timeout and cooldown decisions."""
    clock = MutableClock()
    pump = FakeDigitalOutput()
    store = SQLiteAgricultureStore(tmp_path / "agriculture.db")
    controller = IrrigationController(
        SequenceSoilMoistureSensor([20.0]),
        pump,
        store,
        policy=IrrigationPolicy(),
        safety_guard=IrrigationSafetyGuard(
            IrrigationSafetyConfig(
                max_run_seconds=10.0,
                cooldown_seconds=10.0,
            ),
            clock=clock,
        ),
    )

    controller.open()
    try:
        started = controller.evaluate_once()
        assert started.pump_on is True
        assert started.reason == "soil_dry"

        clock.value = 10.0
        stopped = controller.evaluate_once()
        assert stopped.pump_on is False
        assert stopped.reason == "safety_max_run_reached"

        clock.value = 15.0
        blocked = controller.evaluate_once()
        assert blocked.pump_on is False
        assert blocked.reason == "safety_cooldown_active"

        clock.value = 20.0
        restarted = controller.evaluate_once()
        assert restarted.pump_on is True
        assert restarted.reason == "soil_dry"

        assert store.count() == 4
    finally:
        controller.close()


def test_controller_forces_off_and_records_event_on_downstream_error(
    tmp_path: Path,
) -> None:
    """A post-actuation failure should de-energize the pump and start cooldown."""
    clock = MutableClock()
    pump = FakeDigitalOutput()
    publisher = FailingPublisher()
    events = SQLiteEventRepository(tmp_path / "events.db")
    controller = IrrigationController(
        SequenceSoilMoistureSensor([20.0]),
        pump,
        SQLiteAgricultureStore(tmp_path / "agriculture.db"),
        policy=IrrigationPolicy(),
        events=events,
        telemetry_publisher=publisher,
        safety_guard=IrrigationSafetyGuard(
            IrrigationSafetyConfig(
                max_run_seconds=60.0,
                cooldown_seconds=10.0,
            ),
            clock=clock,
        ),
    )

    controller.open()
    try:
        with pytest.raises(RuntimeError, match="telemetry unavailable"):
            controller.evaluate_once()

        assert pump.read() is False
        assert events.count() == 2

        publisher.fail = False
        clock.value = 5.0
        blocked = controller.evaluate_once()

        assert blocked.pump_on is False
        assert blocked.reason == "safety_cooldown_active"
        assert publisher.messages
    finally:
        controller.close()


class RecordingDurableRuntime:
    """Capture agriculture telemetry without introducing network failure."""

    def __init__(self) -> None:
        self.messages: list[TelemetryMessage] = []

    def enqueue(self, message: TelemetryMessage) -> int:
        """Record one durable telemetry envelope."""
        self.messages.append(message)
        return 0


def test_controller_emits_typed_durable_telemetry(tmp_path: Path) -> None:
    """Agriculture observations should use the durable runtime when configured."""
    runtime = RecordingDurableRuntime()
    controller = IrrigationController(
        SequenceSoilMoistureSensor([24.0]),
        FakeDigitalOutput(),
        SQLiteAgricultureStore(tmp_path / "agriculture.db"),
        policy=IrrigationPolicy(),
        telemetry_runtime=runtime,  # type: ignore[arg-type]
        device_id="farm-01",
        clock=lambda: datetime(2026, 10, 6, 12, 0, tzinfo=UTC),
    )

    controller.open()
    try:
        result = controller.evaluate_once()
    finally:
        controller.close()

    assert result.pump_on is True
    assert runtime.messages[0].device_id == "farm-01"
    assert runtime.messages[0].event == "irrigation_observation"
    assert runtime.messages[0].data["pump_on"] is True


def test_controller_rejects_direct_and_durable_telemetry_together(
    tmp_path: Path,
) -> None:
    """Only one telemetry delivery mode should be active."""
    with pytest.raises(ValueError, match="mutually exclusive"):
        IrrigationController(
            SequenceSoilMoistureSensor([24.0]),
            FakeDigitalOutput(),
            SQLiteAgricultureStore(tmp_path / "agriculture.db"),
            policy=IrrigationPolicy(),
            telemetry_publisher=InMemoryPublisher(),
            telemetry_runtime=RecordingDurableRuntime(),  # type: ignore[arg-type]
        )
