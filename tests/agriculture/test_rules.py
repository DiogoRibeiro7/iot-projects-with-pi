"""Tests for pure irrigation rules."""

import pytest

from iot_pi.agriculture.rules import IrrigationPolicy, IrrigationState


def test_policy_starts_irrigation_when_soil_is_dry() -> None:
    """Dry soil should start irrigation when the pump is off."""
    decision = IrrigationPolicy().evaluate(
        soil_moisture_percent=25.0,
        current_state=IrrigationState.OFF,
    )

    assert decision.desired_state is IrrigationState.ON
    assert decision.reason == "soil_dry"


def test_policy_keeps_pump_off_when_moisture_is_sufficient() -> None:
    """Moist soil should not start irrigation."""
    decision = IrrigationPolicy().evaluate(
        soil_moisture_percent=35.0,
        current_state=IrrigationState.OFF,
    )

    assert decision.desired_state is IrrigationState.OFF
    assert decision.reason == "moisture_sufficient"


def test_policy_uses_hysteresis_until_soil_is_rehydrated() -> None:
    """An active pump should remain on until the wet threshold is reached."""
    policy = IrrigationPolicy(dry_on_percent=30.0, wet_off_percent=45.0)

    hold = policy.evaluate(
        soil_moisture_percent=38.0,
        current_state=IrrigationState.ON,
    )
    stop = policy.evaluate(
        soil_moisture_percent=46.0,
        current_state=IrrigationState.ON,
    )

    assert hold.desired_state is IrrigationState.ON
    assert hold.reason == "hysteresis_hold"
    assert stop.desired_state is IrrigationState.OFF
    assert stop.reason == "soil_rehydrated"


@pytest.mark.parametrize(
    ("dry_on", "wet_off"),
    [(-1.0, 45.0), (30.0, 101.0), (45.0, 45.0), (60.0, 50.0)],
)
def test_policy_rejects_invalid_thresholds(
    dry_on: float,
    wet_off: float,
) -> None:
    """Thresholds must be valid percentages with a non-empty hysteresis band."""
    with pytest.raises(ValueError):
        IrrigationPolicy(dry_on_percent=dry_on, wet_off_percent=wet_off)


@pytest.mark.parametrize("moisture", [-1.0, 101.0])
def test_policy_rejects_invalid_readings(moisture: float) -> None:
    """Runtime sensor values must remain within percentage bounds."""
    with pytest.raises(ValueError, match="soil_moisture_percent"):
        IrrigationPolicy().evaluate(
            soil_moisture_percent=moisture,
            current_state=IrrigationState.OFF,
        )
