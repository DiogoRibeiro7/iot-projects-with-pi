"""Home-automation application service."""

import json
import logging
from enum import Enum

from iot_pi.hardware.interfaces import DigitalInput, Relay, TemperatureHumiditySensor
from iot_pi.home.rules import AutomationDecision, AutomationPolicy, AutomationState
from iot_pi.observability.health import HealthTracker
from iot_pi.observability.storage import SQLiteEventRepository


class OverrideMode(str, Enum):
    """Manual override mode."""

    AUTO = "auto"
    FORCE_ON = "on"
    FORCE_OFF = "off"


class HomeAutomationController:
    """Coordinate environmental input, motion state, and relay output."""

    def __init__(
        self,
        climate_sensor: TemperatureHumiditySensor,
        motion_sensor: DigitalInput,
        relay: Relay,
        *,
        policy: AutomationPolicy,
        logger: logging.Logger | None = None,
        health: HealthTracker | None = None,
        events: SQLiteEventRepository | None = None,
    ) -> None:
        """Create a controller from abstract hardware dependencies."""
        self._climate_sensor = climate_sensor
        self._motion_sensor = motion_sensor
        self._relay = relay
        self._policy = policy
        self._logger = logger or logging.getLogger("iot_pi.home")
        self._health = health
        self._events = events
        self._override = OverrideMode.AUTO

    def open(self) -> None:
        """Open resources with rollback if a later resource fails."""
        opened: list[object] = []
        try:
            self._climate_sensor.open()
            opened.append(self._climate_sensor)
            self._motion_sensor.open()
            opened.append(self._motion_sensor)
            self._relay.open()
            opened.append(self._relay)
            self._relay.write(False)
            if self._events is not None:
                self._events.open()
        except Exception:
            if self._events is not None:
                self._events.close()
            for resource in reversed(opened):
                resource.close()  # type: ignore[attr-defined]
            raise

    def close(self) -> None:
        """Switch the actuator off and release all resources."""
        try:
            self._relay.write(False)
        finally:
            try:
                self._relay.close()
            finally:
                try:
                    self._motion_sensor.close()
                finally:
                    try:
                        self._climate_sensor.close()
                    finally:
                        if self._events is not None:
                            self._events.close()

    def set_override(self, mode: OverrideMode) -> None:
        """Set the manual override mode."""
        self._override = mode

    def evaluate_once(self) -> AutomationDecision:
        """Read sensors, evaluate rules, and apply the relay state."""
        try:
            reading = self._climate_sensor.read()
            motion = self._motion_sensor.read()
        except Exception:
            if self._health is not None:
                self._health.record_sensor_failure()
            raise

        current_state = (
            AutomationState.ON if self._relay.read() else AutomationState.OFF
        )

        if self._override is OverrideMode.FORCE_ON:
            decision = AutomationDecision(AutomationState.ON, "manual_override_on")
        elif self._override is OverrideMode.FORCE_OFF:
            decision = AutomationDecision(AutomationState.OFF, "manual_override_off")
        else:
            decision = self._policy.evaluate(
                temperature_c=reading.temperature_c,
                motion_detected=motion,
                current_state=current_state,
            )

        self._relay.write(decision.desired_state is AutomationState.ON)

        payload = {
            "temperature_c": reading.temperature_c,
            "relative_humidity_percent": reading.relative_humidity_percent,
            "motion_detected": motion,
            "relay_state": decision.desired_state.value,
            "reason": decision.reason,
            "override": self._override.value,
        }

        if self._health is not None:
            self._health.record_success()

        if self._events is not None:
            self._events.append("automation_decision", payload)

        self._logger.info(
            json.dumps(
                {
                    "event": "automation_decision",
                    **payload,
                },
                sort_keys=True,
            )
        )
        return decision
