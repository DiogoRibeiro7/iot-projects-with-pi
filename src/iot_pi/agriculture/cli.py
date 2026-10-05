"""Command-line interface for the smart-agriculture reference project."""

from __future__ import annotations

import json
import logging
import time
from argparse import ArgumentParser, ArgumentTypeError
from math import isfinite
from pathlib import Path

from iot_pi.agriculture.rules import IrrigationPolicy
from iot_pi.agriculture.safety import IrrigationSafetyConfig, IrrigationSafetyGuard
from iot_pi.agriculture.sensors import (
    Mcp3008SoilMoistureSensor,
    SequenceSoilMoistureSensor,
    SimulatedSoilMoistureSensor,
)
from iot_pi.agriculture.service import IrrigationController
from iot_pi.agriculture.storage import SQLiteAgricultureStore
from iot_pi.hardware.fake import FakeDigitalOutput
from iot_pi.hardware.gpiozero import GpioZeroRelay
from iot_pi.hardware.interfaces import AnalogSensor, Relay, TemperatureHumiditySensor
from iot_pi.messaging.mqtt import PahoMqttPublisher
from iot_pi.observability.health import HealthTracker
from iot_pi.observability.state import HealthStateFile
from iot_pi.observability.storage import SQLiteEventRepository
from iot_pi.weather.sensors import (
    DhtTemperatureHumiditySensor,
    SimulatedTemperatureHumiditySensor,
)


def _positive_int(value: str) -> int:
    """Parse a strictly positive integer."""
    parsed = int(value)
    if parsed <= 0:
        raise ArgumentTypeError("value must be a positive integer")
    return parsed


def _positive_finite_float(value: str) -> float:
    """Parse a strictly positive finite float."""
    parsed = float(value)
    if not isfinite(parsed) or parsed <= 0:
        raise ArgumentTypeError("value must be a positive finite number")
    return parsed


def _percentage(value: str) -> float:
    """Parse a percentage in the closed interval [0, 100]."""
    parsed = float(value)
    if not isfinite(parsed) or not 0.0 <= parsed <= 100.0:
        raise ArgumentTypeError("value must be between 0 and 100")
    return parsed


def _non_negative_finite_float(value: str) -> float:
    """Parse a non-negative finite float."""
    parsed = float(value)
    if not isfinite(parsed) or parsed < 0:
        raise ArgumentTypeError("value must be a non-negative finite number")
    return parsed


def build_parser() -> ArgumentParser:
    """Build the agriculture command-line parser."""
    parser = ArgumentParser(description="Run the Raspberry Pi irrigation controller")
    parser.add_argument("--simulation", action="store_true")
    parser.add_argument("--simulation-fixture", type=Path)
    parser.add_argument("--samples", type=_positive_int, default=1)
    parser.add_argument("--interval", type=_positive_finite_float, default=60.0)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/agriculture.db"),
    )
    parser.add_argument("--events-database", type=Path)
    parser.add_argument("--dry-on", type=_percentage, default=30.0)
    parser.add_argument("--wet-off", type=_percentage, default=45.0)
    parser.add_argument(
        "--max-run-seconds",
        type=_positive_finite_float,
        default=300.0,
    )
    parser.add_argument(
        "--cooldown-seconds",
        type=_non_negative_finite_float,
        default=60.0,
    )
    parser.add_argument("--relay-pin", type=int, default=27)
    parser.add_argument("--adc-channel", type=int, default=0)
    parser.add_argument("--dry-raw", type=float, default=0.8)
    parser.add_argument("--wet-raw", type=float, default=0.3)
    parser.add_argument("--climate", action="store_true")
    parser.add_argument("--dht-pin", default="D4")
    parser.add_argument("--dht-model", choices=("DHT11", "DHT22"), default="DHT22")
    parser.add_argument("--mqtt-host")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--device-id", default="agriculture-pi")
    parser.add_argument("--health-file", type=Path)
    return parser


def _load_fixture(path: Path) -> list[float]:
    """Load deterministic soil-moisture readings from JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    readings = raw.get("soil_moisture_percent")
    if not isinstance(readings, list) or not readings:
        raise ValueError(
            "simulation fixture must contain a non-empty soil_moisture_percent list"
        )
    return [float(value) for value in readings]


def main() -> int:
    """Run the smart-agriculture reference application."""
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    soil_sensor: AnalogSensor

    if args.simulation:
        soil_sensor = (
            SequenceSoilMoistureSensor(_load_fixture(args.simulation_fixture))
            if args.simulation_fixture is not None
            else SimulatedSoilMoistureSensor()
        )
        pump: Relay = FakeDigitalOutput()
    else:
        soil_sensor = Mcp3008SoilMoistureSensor(
            args.adc_channel,
            dry_raw=args.dry_raw,
            wet_raw=args.wet_raw,
        )
        pump = GpioZeroRelay(args.relay_pin)

    climate_sensor: TemperatureHumiditySensor | None = None
    if args.climate:
        climate_sensor = (
            SimulatedTemperatureHumiditySensor()
            if args.simulation
            else DhtTemperatureHumiditySensor(args.dht_pin, model=args.dht_model)
        )

    telemetry_publisher: PahoMqttPublisher | None = None
    if args.mqtt_host:
        telemetry_publisher = PahoMqttPublisher(
            args.mqtt_host,
            port=args.mqtt_port,
            client_id=args.device_id,
        )

    store = SQLiteAgricultureStore(args.database)
    events = (
        None
        if args.events_database is None
        else SQLiteEventRepository(args.events_database)
    )
    health = HealthTracker(
        observer=(
            None if args.health_file is None else HealthStateFile(args.health_file)
        )
    )

    controller = IrrigationController(
        soil_sensor,
        pump,
        store,
        policy=IrrigationPolicy(
            dry_on_percent=args.dry_on,
            wet_off_percent=args.wet_off,
        ),
        safety_guard=IrrigationSafetyGuard(
            IrrigationSafetyConfig(
                max_run_seconds=args.max_run_seconds,
                cooldown_seconds=args.cooldown_seconds,
            )
        ),
        climate_sensor=climate_sensor,
        health=health,
        events=events,
        telemetry_publisher=telemetry_publisher,
        device_id=args.device_id,
    )

    if telemetry_publisher is not None:
        telemetry_publisher.open()

    try:
        controller.open()
        for index in range(args.samples):
            controller.evaluate_once()
            if index < args.samples - 1:
                time.sleep(args.interval)
    finally:
        controller.close()
        if telemetry_publisher is not None:
            telemetry_publisher.close()

    return 0
