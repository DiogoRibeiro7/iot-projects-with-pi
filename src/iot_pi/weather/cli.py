"""Command-line interface for the weather station."""

from argparse import ArgumentParser
import logging
from pathlib import Path

from iot_pi.weather.sensors import (
    DhtTemperatureHumiditySensor,
    SimulatedTemperatureHumiditySensor,
)
from iot_pi.weather.service import WeatherStation
from iot_pi.weather.storage import SQLiteWeatherStore


def build_parser() -> ArgumentParser:
    """Build the weather-station command-line parser."""
    parser = ArgumentParser(description="Run the Raspberry Pi weather station")
    parser.add_argument("--database", type=Path, default=Path("data/weather.db"))
    parser.add_argument("--interval", type=float, default=60.0)
    parser.add_argument("--samples", type=int, default=1)
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

    station.open()
    try:
        station.run(samples=args.samples)
    finally:
        station.close()

    return 0
