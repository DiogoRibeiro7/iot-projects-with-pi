"""Tests for home-automation orchestration."""

import pytest

from iot_pi.hardware.fake import FakeDigitalInput, FakeDigitalOutput
from iot_pi.home.rules import AutomationPolicy, AutomationState
from iot_pi.home.service import HomeAutomationController, OverrideMode
from iot_pi.observability.health import HealthTracker
from iot_pi.weather.sensors import SimulatedTemperatureHumiditySensor


def build_controller() -> tuple[HomeAutomationController, FakeDigitalOutput]:
    """Create a deterministic controller for tests."""
    relay = FakeDigitalOutput()
    controller = HomeAutomationController(
        SimulatedTemperatureHumiditySensor(
            seed=1,
            base_temperature_c=29.0,
            base_humidity_percent=50.0,
        ),
        FakeDigitalInput(state=True),
        relay,
        policy=AutomationPolicy(),
    )
    return controller, relay

def test_controller_applies_policy_decision() -> None:
    """The controller should propagate policy state to the relay."""
    controller, relay = build_controller()

    controller.open()
    try:
        decision = controller.evaluate_once()

        assert decision.desired_state is AutomationState.ON
        assert relay.read() is True
    finally:
        controller.close()


def test_manual_override_forces_output_state() -> None:
    """Manual override should take precedence over automatic rules."""
    controller, relay = build_controller()
    controller.set_override(OverrideMode.FORCE_OFF)

    controller.open()
    try:
        decision = controller.evaluate_once()

        assert decision.desired_state is AutomationState.OFF
        assert decision.reason == "manual_override_off"
        assert relay.read() is False
    finally:
        controller.close()


def test_close_deenergizes_relay() -> None:
    """Controller shutdown should always leave the relay off."""
    controller, relay = build_controller()

    controller.open()
    controller.evaluate_once()
    controller.close()

    assert relay._state is False


class FailingMotionInput(FakeDigitalInput):
    """Motion input that fails during initialization."""

    def open(self) -> None:
        """Simulate a GPIO initialization failure."""
        raise RuntimeError("motion unavailable")


class FailingClimateSensor(SimulatedTemperatureHumiditySensor):
    """Climate sensor that fails while reading."""

    def read(self):
        """Simulate a sensor read failure."""
        raise RuntimeError("climate unavailable")


def test_open_rolls_back_already_open_resources() -> None:
    """Partial startup failure should close the climate sensor again."""
    climate = SimulatedTemperatureHumiditySensor()
    controller = HomeAutomationController(
        climate,
        FailingMotionInput(),
        FakeDigitalOutput(),
        policy=AutomationPolicy(),
    )

    with pytest.raises(RuntimeError, match="motion unavailable"):
        controller.open()

    with pytest.raises(RuntimeError, match="not open"):
        climate.read()


def test_sensor_failure_updates_health_tracker() -> None:
    """Sensor exceptions should be reflected in shared health state."""
    health = HealthTracker()
    controller = HomeAutomationController(
        FailingClimateSensor(),
        FakeDigitalInput(state=True),
        FakeDigitalOutput(),
        policy=AutomationPolicy(),
        health=health,
    )
    controller.open()

    try:
        with pytest.raises(RuntimeError, match="climate unavailable"):
            controller.evaluate_once()
        assert health.snapshot().sensor_failures == 1
    finally:
        controller.close()


def test_manual_force_on_override() -> None:
    """Force-on override should bypass the automatic policy."""
    controller, relay = build_controller()
    controller.set_override(OverrideMode.FORCE_ON)

    controller.open()
    try:
        decision = controller.evaluate_once()

        assert decision.desired_state is AutomationState.ON
        assert decision.reason == "manual_override_on"
        assert relay.read() is True
    finally:
        controller.close()
