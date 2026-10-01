"""Tests for pure automation rules."""

import pytest

from iot_pi.home.rules import AutomationPolicy, AutomationState


def test_policy_turns_on_when_hot_and_occupied() -> None:
    """High temperature with occupancy should energize the actuator."""
    decision = AutomationPolicy().evaluate(
        temperature_c=29.0,
        motion_detected=True,
        current_state=AutomationState.OFF,
    )

    assert decision.desired_state is AutomationState.ON
    assert decision.reason == "temperature_high"


def test_policy_turns_off_without_motion() -> None:
    """Occupancy gating should force a safe off state."""
    decision = AutomationPolicy().evaluate(
        temperature_c=35.0,
        motion_detected=False,
        current_state=AutomationState.ON,
    )

    assert decision.desired_state is AutomationState.OFF
    assert decision.reason == "no_motion"


def test_policy_uses_hysteresis() -> None:
    """An active relay should remain on inside the hysteresis band."""
    policy = AutomationPolicy(temperature_on_c=28.0, temperature_off_c=26.0)

    hold = policy.evaluate(
        temperature_c=27.0,
        motion_detected=True,
        current_state=AutomationState.ON,
    )
    off = policy.evaluate(
        temperature_c=25.5,
        motion_detected=True,
        current_state=AutomationState.ON,
    )

    assert hold.desired_state is AutomationState.ON
    assert off.desired_state is AutomationState.OFF


def test_policy_rejects_invalid_threshold_order() -> None:
    """The off threshold must remain below the on threshold."""
    with pytest.raises(ValueError, match="temperature_off_c"):
        AutomationPolicy(temperature_on_c=25.0, temperature_off_c=25.0)
