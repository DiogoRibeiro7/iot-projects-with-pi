"""Tests for home-automation orchestration."""

from iot_pi.hardware.fake import FakeDigitalInput, FakeDigitalOutput
from iot_pi.home.rules import AutomationPolicy, AutomationState
from iot_pi.home.service import HomeAutomationController, OverrideMode
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
