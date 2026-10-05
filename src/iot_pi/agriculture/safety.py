"""Stateful actuator safety guardrails for irrigation control."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite

from iot_pi.agriculture.rules import IrrigationDecision, IrrigationState

MonotonicClock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class IrrigationSafetyConfig:
    """Timing limits for irrigation actuator safety."""

    max_run_seconds: float = 300.0
    cooldown_seconds: float = 60.0

    def __post_init__(self) -> None:
        """Validate strictly positive safety intervals."""
        if not isfinite(self.max_run_seconds) or self.max_run_seconds <= 0:
            raise ValueError("max_run_seconds must be a positive finite number")
        if not isfinite(self.cooldown_seconds) or self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be a non-negative finite number")


class IrrigationSafetyGuard:
    """Enforce maximum-on time and minimum-off cooldown intervals."""

    def __init__(
        self,
        config: IrrigationSafetyConfig | None = None,
        *,
        clock: MonotonicClock | None = None,
    ) -> None:
        """Create a safety guard with injectable monotonic time."""
        self._config = config or IrrigationSafetyConfig()
        self._clock = clock or time.monotonic
        self._pump_started_at: float | None = None
        self._last_stopped_at: float | None = None

    def apply(
        self,
        decision: IrrigationDecision,
        *,
        current_state: IrrigationState,
    ) -> IrrigationDecision:
        """Apply actuator timing constraints to an irrigation decision."""
        now = self._clock()

        if current_state is IrrigationState.ON:
            if self._pump_started_at is None:
                self._pump_started_at = now

            if now - self._pump_started_at >= self._config.max_run_seconds:
                self._pump_started_at = None
                self._last_stopped_at = now
                return IrrigationDecision(
                    IrrigationState.OFF,
                    "safety_max_run_reached",
                )

            if decision.desired_state is IrrigationState.OFF:
                self._pump_started_at = None
                self._last_stopped_at = now

            return decision

        if decision.desired_state is IrrigationState.ON:
            if (
                self._last_stopped_at is not None
                and now - self._last_stopped_at < self._config.cooldown_seconds
            ):
                return IrrigationDecision(
                    IrrigationState.OFF,
                    "safety_cooldown_active",
                )

            self._pump_started_at = now

        return decision

    def record_forced_stop(self) -> None:
        """Record an emergency/error stop for future cooldown enforcement."""
        now = self._clock()
        self._pump_started_at = None
        self._last_stopped_at = now
