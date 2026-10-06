"""Command-line interface for the weather station."""

import logging
from argparse import ArgumentParser, BooleanOptionalAction
from pathlib import Path

from iot_pi.cloud.runtime import (
    DurableTelemetryRuntime,
    build_mqtt_durable_runtime,
)
from iot_pi.config import WeatherConfig, load_config
from iot_pi.observability.health import HealthTracker
from iot_pi.observability.state import HealthStateFile
from iot_pi.weather.sensors import (
    DhtTemperatureHumiditySensor,
    SimulatedTemperatureHumiditySensor,
)
from iot_pi.weather.service import WeatherStation
from iot_pi.weather.storage import SQLiteWeatherStore


def build_parser() -> ArgumentParser:
    """Build the weather-station command-line parser."""
    parser = ArgumentParser(description="Run the Raspberry Pi weather station")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--device-id")
    parser.add_argument("--database")
    parser.add_argument("--interval", type=float)
    parser.add_argument("--samples", type=int)
    parser.add_argument(
        "--simulation",
        action=BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--pin")
    parser.add_argument("--model", choices=("DHT11", "DHT22"))
    parser.add_argument("--health-file")
    parser.add_argument("--mqtt-host")
    parser.add_argument("--mqtt-port", type=int)
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


def main() -> int:
    """Run the weather-station CLI."""
    args = build_parser().parse_args()
    config = load_config(
        WeatherConfig,
        path=args.config,
        env_prefix="IOT_WEATHER_",
        cli_overrides={
            "device_id": args.device_id,
            "database": args.database,
            "sample_interval_seconds": args.interval,
            "samples": args.samples,
            "simulation": args.simulation,
            "pin": args.pin,
            "model": args.model,
            "health_file": args.health_file,
            "mqtt_host": args.mqtt_host,
            "mqtt_port": args.mqtt_port,
            "telemetry_outbox_database": args.telemetry_outbox,
            "telemetry_batch_size": args.telemetry_batch_size,
            "telemetry_max_retries": args.telemetry_max_retries,
            "telemetry_backoff_seconds": args.telemetry_backoff_seconds,
            "telemetry_tls_enabled": args.telemetry_tls,
            "telemetry_topic_prefix": args.telemetry_topic_prefix,
        },
    )

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    sensor = (
        SimulatedTemperatureHumiditySensor()
        if config.simulation
        else DhtTemperatureHumiditySensor(config.pin, model=config.model)
    )
    store = SQLiteWeatherStore(Path(config.database))
    health = (
        None
        if (
            config.health_file is None
            and config.telemetry_outbox_database is None
        )
        else HealthTracker(
            observer=(
                None
                if config.health_file is None
                else HealthStateFile(Path(config.health_file))
            )
        )
    )
    telemetry_runtime: DurableTelemetryRuntime | None = None
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

    station = WeatherStation(
        sensor,
        store,
        sample_interval_seconds=config.sample_interval_seconds,
        health=health,
        telemetry_runtime=telemetry_runtime,
        device_id=config.device_id,
    )

    if telemetry_runtime is not None:
        telemetry_runtime.open()

    try:
        station.open()
        station.run(samples=config.samples)
    finally:
        station.close()
        if telemetry_runtime is not None:
            telemetry_runtime.close()

    return 0
