"""Command-line interface for the weather station."""

from argparse import ArgumentParser, ArgumentTypeError
import logging
from math import isfinite
from pathlib import Path

from iot_pi.weather.sensors import (
    DhtTemperatureHumiditySensor,
    SimulatedTemperatureHumiditySensor,
)
from iot_pi.weather.service import WeatherStation
from iot_pi.weather.storage import SQLiteWeatherStore


def _positive_finite_float(value: str) -> float:
    """Parse a strictly positive finite floating-point value."""
    parsed = float(value)
    if not isfinite(parsed) or parsed <= 0:
        raise ArgumentTypeError("value must be a positive finite number")
    return parsed


def _positive_int(value: str) -> int:
    """Parse a strictly positive integer."""
    parsed = int(value)
    if parsed <= 0:
        raise ArgumentTypeError("value must be a positive integer")
    return parsed


def build_parser() -> ArgumentParser:
    """Build the weather-station command-line parser."""
    parser = ArgumentParser(description="Run the Raspberry Pi weather station")
    parser.add_argument("--database", type=Path, default=Path("data/weather.db"))
    parser.add_argument("--interval", type=_positive_finite_float, default=60.0)
    parser.add_argument("--samples", type=_positive_int, default=1)
    parser.add_argument("--simulation", action="store_true")
    parser.add_argument("--pin", default="D4")
    parser.add_argument("--model", choices=("DHT11", "DHT22"), default="DHT22")
    return parser


def main() -> int:
    """Run the weather-station CLI."""
    args = build_parser().parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    sensor = (
        SimulatedTemperatureHumiditySensor()
        if args.simulation
        else DhtTemperatureHumiditySensor(args.pin, model=args.model)
    )
    store = SQLiteWeatherStore(args.database)
    station = WeatherStation(
        sensor,
        store,
        sample_interval_seconds=args.interval,
    )

    try:
        station.open()
        station.run(samples=args.samples)
    finally:
        station.close()

    return 0
