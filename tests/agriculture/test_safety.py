"""Tests for irrigation actuator safety guardrails."""

import pytest

from iot_pi.agriculture.rules import IrrigationDecision, IrrigationState
from iot_pi.agriculture.safety import (
    IrrigationSafetyConfig,
    IrrigationSafetyGuard,
)


class MutableClock:
    """Deterministic monotonic clock for safety tests."""

    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def on_decision() -> IrrigationDecision:
    """Return a normal irrigation-on decision."""
    return IrrigationDecision(IrrigationState.ON, "soil_dry")


def test_guard_forces_off_after_maximum_run_time() -> None:
    """A pump may not remain energized beyond the configured duration."""
    clock = MutableClock()
    guard = IrrigationSafetyGuard(
        IrrigationSafetyConfig(max_run_seconds=10.0, cooldown_seconds=5.0),
        clock=clock,
    )

    first = guard.apply(on_decision(), current_state=IrrigationState.OFF)
    assert first.desired_state is IrrigationState.ON

    clock.value = 9.9
    hold = guard.apply(on_decision(), current_state=IrrigationState.ON)
    assert hold.desired_state is IrrigationState.ON

    clock.value = 10.0
    forced = guard.apply(on_decision(), current_state=IrrigationState.ON)

    assert forced.desired_state is IrrigationState.OFF
    assert forced.reason == "safety_max_run_reached"


def test_guard_blocks_restart_during_cooldown() -> None:
    """A forced stop should prevent immediate pump reactivation."""
    clock = MutableClock()
    guard = IrrigationSafetyGuard(
        IrrigationSafetyConfig(max_run_seconds=5.0, cooldown_seconds=10.0),
        clock=clock,
    )

    guard.apply(on_decision(), current_state=IrrigationState.OFF)
    clock.value = 5.0
    guard.apply(on_decision(), current_state=IrrigationState.ON)

    clock.value = 14.9
    blocked = guard.apply(on_decision(), current_state=IrrigationState.OFF)
    assert blocked.desired_state is IrrigationState.OFF
    assert blocked.reason == "safety_cooldown_active"

    clock.value = 15.0
    allowed = guard.apply(on_decision(), current_state=IrrigationState.OFF)
    assert allowed.desired_state is IrrigationState.ON


def test_guard_records_normal_policy_stop_for_cooldown() -> None:
    """A moisture-driven stop should also start the cooldown interval."""
    clock = MutableClock()
    guard = IrrigationSafetyGuard(
        IrrigationSafetyConfig(max_run_seconds=60.0, cooldown_seconds=10.0),
        clock=clock,
    )
    guard.apply(on_decision(), current_state=IrrigationState.OFF)

    clock.value = 2.0
    stop = IrrigationDecision(IrrigationState.OFF, "soil_rehydrated")
    assert guard.apply(stop, current_state=IrrigationState.ON) == stop

    clock.value = 5.0
    blocked = guard.apply(on_decision(), current_state=IrrigationState.OFF)
    assert blocked.reason == "safety_cooldown_active"


def test_guard_records_forced_error_stop() -> None:
    """Error-driven shutdown should enforce cooldown before restart."""
    clock = MutableClock()
    guard = IrrigationSafetyGuard(
        IrrigationSafetyConfig(max_run_seconds=60.0, cooldown_seconds=10.0),
        clock=clock,
    )
    guard.apply(on_decision(), current_state=IrrigationState.OFF)

    clock.value = 3.0
    guard.record_forced_stop()

    clock.value = 8.0
    blocked = guard.apply(on_decision(), current_state=IrrigationState.OFF)
    assert blocked.reason == "safety_cooldown_active"


@pytest.mark.parametrize(
    ("max_run", "cooldown"),
    [(0.0, 1.0), (-1.0, 1.0), (1.0, -1.0)],
)
def test_safety_config_rejects_invalid_intervals(
    max_run: float,
    cooldown: float,
) -> None:
    """Safety timing limits must remain valid."""
    with pytest.raises(ValueError):
        IrrigationSafetyConfig(
            max_run_seconds=max_run,
            cooldown_seconds=cooldown,
        )
