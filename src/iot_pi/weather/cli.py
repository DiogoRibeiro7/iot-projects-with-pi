"""Command-line interface for the weather station."""

import logging
from argparse import ArgumentParser, BooleanOptionalAction
from pathlib import Path

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
        if config.health_file is None
        else HealthTracker(observer=HealthStateFile(Path(config.health_file)))
    )
    station = WeatherStation(
        sensor,
        store,
        sample_interval_seconds=config.sample_interval_seconds,
        health=health,
    )

    try:
        station.open()
        station.run(samples=config.samples)
    finally:
        station.close()

    return 0
