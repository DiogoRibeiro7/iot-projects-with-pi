"""Command-line interface for the smart-agriculture reference project."""

from __future__ import annotations

import json
import logging
import time
from argparse import ArgumentParser, BooleanOptionalAction
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
from iot_pi.cloud.runtime import (
    DurableTelemetryRuntime,
    build_mqtt_durable_runtime,
)
from iot_pi.config import AgricultureConfig, load_config
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


def build_parser() -> ArgumentParser:
    """Build the agriculture command-line parser."""
    parser = ArgumentParser(description="Run the Raspberry Pi irrigation controller")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--device-id")
    parser.add_argument(
        "--simulation",
        action=BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--simulation-fixture")
    parser.add_argument("--samples", type=int)
    parser.add_argument("--interval", type=float)
    parser.add_argument("--database")
    parser.add_argument("--events-database")
    parser.add_argument("--dry-on", type=float)
    parser.add_argument("--wet-off", type=float)
    parser.add_argument("--max-run-seconds", type=float)
    parser.add_argument("--cooldown-seconds", type=float)
    parser.add_argument("--relay-pin", type=int)
    parser.add_argument("--adc-channel", type=int)
    parser.add_argument("--dry-raw", type=float)
    parser.add_argument("--wet-raw", type=float)
    parser.add_argument(
        "--climate",
        action=BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--dht-pin")
    parser.add_argument("--dht-model", choices=("DHT11", "DHT22"))
    parser.add_argument("--mqtt-host")
    parser.add_argument("--mqtt-port", type=int)
    parser.add_argument("--health-file")
    parser.add_argument("--telemetry-outbox")
    parser.add_argument("--telemetry-batch-size", type=int)
    parser.add_argument("--telemetry-max-retries", type=int)
    parser.add_argument("--telemetry-backoff-seconds", type=float)
    parser.add_argument(
        "--telemetry-tls",
        action=BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--telemetry-topic-prefix")
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
    config = load_config(
        AgricultureConfig,
        path=args.config,
        env_prefix="IOT_AGRICULTURE_",
        cli_overrides={
            "device_id": args.device_id,
            "simulation": args.simulation,
            "simulation_fixture": args.simulation_fixture,
            "samples": args.samples,
            "sample_interval_seconds": args.interval,
            "database": args.database,
            "events_database": args.events_database,
            "dry_on_percent": args.dry_on,
            "wet_off_percent": args.wet_off,
            "max_run_seconds": args.max_run_seconds,
            "cooldown_seconds": args.cooldown_seconds,
            "relay_pin": args.relay_pin,
            "adc_channel": args.adc_channel,
            "dry_raw": args.dry_raw,
            "wet_raw": args.wet_raw,
            "climate": args.climate,
            "dht_pin": args.dht_pin,
            "dht_model": args.dht_model,
            "mqtt_host": args.mqtt_host,
            "mqtt_port": args.mqtt_port,
            "health_file": args.health_file,
            "telemetry_outbox_database": args.telemetry_outbox,
            "telemetry_batch_size": args.telemetry_batch_size,
            "telemetry_max_retries": args.telemetry_max_retries,
            "telemetry_backoff_seconds": args.telemetry_backoff_seconds,
            "telemetry_tls_enabled": args.telemetry_tls,
            "telemetry_topic_prefix": args.telemetry_topic_prefix,
        },
    )
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    soil_sensor: AnalogSensor
    if config.simulation:
        soil_sensor = (
            SequenceSoilMoistureSensor(_load_fixture(Path(config.simulation_fixture)))
            if config.simulation_fixture is not None
            else SimulatedSoilMoistureSensor()
        )
        pump: Relay = FakeDigitalOutput()
    else:
        soil_sensor = Mcp3008SoilMoistureSensor(
            config.adc_channel,
            dry_raw=config.dry_raw,
            wet_raw=config.wet_raw,
        )
        pump = GpioZeroRelay(config.relay_pin)

    climate_sensor: TemperatureHumiditySensor | None = None
    if config.climate:
        climate_sensor = (
            SimulatedTemperatureHumiditySensor()
            if config.simulation
            else DhtTemperatureHumiditySensor(
                config.dht_pin,
                model=config.dht_model,
            )
        )

    store = SQLiteAgricultureStore(Path(config.database))
    events = (
        None
        if config.events_database is None
        else SQLiteEventRepository(Path(config.events_database))
    )
    health = HealthTracker(
        observer=(
            None
            if config.health_file is None
            else HealthStateFile(Path(config.health_file))
        )
    )


    telemetry_runtime: DurableTelemetryRuntime | None = None
    telemetry_publisher: PahoMqttPublisher | None = None
    if config.telemetry_outbox_database is not None:
        assert config.mqtt_host is not None
        telemetry_runtime = build_mqtt_durable_runtime(
            host=config.mqtt_host,
            port=config.mqtt_port,
            device_id=config.device_id,
            outbox_path=Path(config.telemetry_outbox_database),
            batch_size=config.telemetry_batch_size,
            max_retries=config.telemetry_max_retries,
            backoff_seconds=config.telemetry_backoff_seconds,
            tls_enabled=config.telemetry_tls_enabled,
            topic_prefix=config.telemetry_topic_prefix,
            health=health,
        )
    elif config.mqtt_host:
        telemetry_publisher = PahoMqttPublisher(
            config.mqtt_host,
            port=config.mqtt_port,
            client_id=config.device_id,
        )
    controller = IrrigationController(
        soil_sensor,
        pump,
        store,
        policy=IrrigationPolicy(
            dry_on_percent=config.dry_on_percent,
            wet_off_percent=config.wet_off_percent,
        ),
        safety_guard=IrrigationSafetyGuard(
            IrrigationSafetyConfig(
                max_run_seconds=config.max_run_seconds,
                cooldown_seconds=config.cooldown_seconds,
            )
        ),
        climate_sensor=climate_sensor,
        health=health,
        events=events,
        telemetry_publisher=telemetry_publisher,
        telemetry_runtime=telemetry_runtime,
        device_id=config.device_id,
    )

    if telemetry_runtime is not None:
        telemetry_runtime.open()
    elif telemetry_publisher is not None:
        telemetry_publisher.open()

    try:
        controller.open()
        for index in range(config.samples):
            controller.evaluate_once()
            if index < config.samples - 1:
                time.sleep(config.sample_interval_seconds)
    finally:
        controller.close()
        if telemetry_runtime is not None:
            telemetry_runtime.close()
        elif telemetry_publisher is not None:
            telemetry_publisher.close()

    return 0
