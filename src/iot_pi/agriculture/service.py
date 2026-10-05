"""Smart-agriculture irrigation application service."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from iot_pi.agriculture.models import AgricultureObservation
from iot_pi.agriculture.rules import IrrigationPolicy, IrrigationState
from iot_pi.agriculture.safety import IrrigationSafetyGuard
from iot_pi.agriculture.storage import SQLiteAgricultureStore
from iot_pi.hardware.errors import HardwareError
from iot_pi.hardware.interfaces import (
    AnalogSensor,
    Lifecycle,
    Relay,
    TemperatureHumiditySensor,
)
from iot_pi.messaging.agriculture import agriculture_telemetry
from iot_pi.messaging.interfaces import MessagePublisher
from iot_pi.messaging.topics import telemetry_topic
from iot_pi.observability.health import HealthTracker
from iot_pi.observability.storage import SQLiteEventRepository

Clock = Callable[[], datetime]


class IrrigationController:
    """Coordinate soil moisture, optional climate context, and a pump relay."""

    def __init__(
        self,
        soil_sensor: AnalogSensor,
        pump: Relay,
        store: SQLiteAgricultureStore,
        *,
        policy: IrrigationPolicy,
        climate_sensor: TemperatureHumiditySensor | None = None,
        health: HealthTracker | None = None,
        events: SQLiteEventRepository | None = None,
        logger: logging.Logger | None = None,
        clock: Clock | None = None,
        telemetry_publisher: MessagePublisher | None = None,
        device_id: str = "agriculture-pi",
        safety_guard: IrrigationSafetyGuard | None = None,
    ) -> None:
        """Create an irrigation controller."""
        self._soil_sensor = soil_sensor
        self._pump = pump
        self._store = store
        self._policy = policy
        self._climate_sensor = climate_sensor
        self._health = health
        self._events = events
        self._logger = logger or logging.getLogger("iot_pi.agriculture")
        self._clock = clock or (lambda: datetime.now(UTC))
        self._telemetry_publisher = telemetry_publisher
        self._device_id = device_id
        self._safety_guard = safety_guard or IrrigationSafetyGuard()

    def open(self) -> None:
        """Open resources and roll back partial initialization."""
        opened: list[Lifecycle] = []
        try:
            self._soil_sensor.open()
            opened.append(self._soil_sensor)

            if self._climate_sensor is not None:
                self._climate_sensor.open()
                opened.append(self._climate_sensor)

            self._pump.open()
            opened.append(self._pump)
            self._pump.write(False)

            self._store.open()

            if self._events is not None:
                self._events.open()
        except Exception:
            if self._events is not None:
                self._events.close()
            self._store.close()
            for resource in reversed(opened):
                resource.close()
            raise

    def close(self) -> None:
        """De-energize the pump and release all resources."""
        try:
            self._pump.write(False)
        except HardwareError:
            pass
        finally:
            try:
                self._pump.close()
            finally:
                try:
                    if self._climate_sensor is not None:
                        self._climate_sensor.close()
                finally:
                    try:
                        self._soil_sensor.close()
                    finally:
                        try:
                            self._store.close()
                        finally:
                            if self._events is not None:
                                self._events.close()

    def evaluate_once(self) -> AgricultureObservation:
        """Read sensors, apply irrigation and safety rules, persist, and log."""
        try:
            current_state = (
                IrrigationState.ON if self._pump.read() else IrrigationState.OFF
            )

            try:
                soil_moisture = self._soil_sensor.read()
                climate = (
                    self._climate_sensor.read()
                    if self._climate_sensor is not None
                    else None
                )
            except Exception:
                if self._health is not None:
                    self._health.record_sensor_failure()
                raise

            decision = self._policy.evaluate(
                soil_moisture_percent=soil_moisture,
                current_state=current_state,
            )
            decision = self._safety_guard.apply(
                decision,
                current_state=current_state,
            )

            pump_on = decision.desired_state is IrrigationState.ON
            self._pump.write(pump_on)

            observation = AgricultureObservation(
                timestamp=self._clock(),
                soil_moisture_percent=soil_moisture,
                pump_on=pump_on,
                reason=decision.reason,
                temperature_c=None if climate is None else climate.temperature_c,
                relative_humidity_percent=(
                    None if climate is None else climate.relative_humidity_percent
                ),
            )
            self._store.save(observation)

            payload = {
                "soil_moisture_percent": observation.soil_moisture_percent,
                "pump_on": observation.pump_on,
                "reason": observation.reason,
                "temperature_c": observation.temperature_c,
                "relative_humidity_percent": observation.relative_humidity_percent,
            }

            if self._health is not None:
                self._health.record_success(timestamp=observation.timestamp)

            if self._events is not None:
                self._events.append(
                    "irrigation_decision",
                    payload,
                    timestamp=observation.timestamp,
                )

            if self._telemetry_publisher is not None:
                message = agriculture_telemetry(self._device_id, observation)
                self._telemetry_publisher.publish(
                    telemetry_topic(self._device_id, "agriculture"),
                    message.to_json(),
                    qos=1,
                    retain=False,
                )

            self._logger.info(
                json.dumps(
                    {
                        "event": "irrigation_decision",
                        "timestamp": observation.timestamp.isoformat(),
                        **payload,
                    },
                    sort_keys=True,
                )
            )
            return observation
        except Exception:
            try:
                self._pump.write(False)
            except HardwareError:
                pass
            self._safety_guard.record_forced_stop()
            self._record_safety_error_stop()
            raise

    def _record_safety_error_stop(self) -> None:
        """Persist and log an emergency pump shutdown without masking its cause."""
        try:
            timestamp = self._clock()
            payload = {
                "pump_on": False,
                "reason": "safety_error_stop",
            }

            if self._events is not None:
                self._events.append(
                    "irrigation_safety_stop",
                    payload,
                    timestamp=timestamp,
                )

            self._logger.error(
                json.dumps(
                    {
                        "event": "irrigation_safety_stop",
                        "timestamp": timestamp.isoformat(),
                        **payload,
                    },
                    sort_keys=True,
                )
            )
        except Exception:
            self._logger.exception("unable to record irrigation safety stop")
