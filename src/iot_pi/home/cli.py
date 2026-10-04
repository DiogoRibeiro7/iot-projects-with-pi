"""Command-line interface for the home-automation reference project."""

import logging
import time
from argparse import ArgumentParser
from math import isfinite

from iot_pi.hardware.fake import FakeDigitalInput, FakeDigitalOutput
from iot_pi.hardware.gpiozero import GpioZeroDigitalInput, GpioZeroRelay
from iot_pi.hardware.interfaces import DigitalInput, Relay, TemperatureHumiditySensor
from iot_pi.home.rules import AutomationPolicy
from iot_pi.home.service import HomeAutomationController, OverrideMode
from iot_pi.weather.sensors import (
    DhtTemperatureHumiditySensor,
    SimulatedTemperatureHumiditySensor,
)


def build_parser() -> ArgumentParser:
    """Build the CLI parser."""
    parser = ArgumentParser(description="Run the Raspberry Pi home automation demo")
    parser.add_argument("--simulation", action="store_true")
    parser.add_argument("--motion-pin", type=int, default=17)
    parser.add_argument("--relay-pin", type=int, default=27)
    parser.add_argument("--dht-pin", default="D4")
    parser.add_argument("--dht-model", choices=("DHT11", "DHT22"), default="DHT22")
    parser.add_argument("--temperature-on", type=float, default=28.0)
    parser.add_argument("--temperature-off", type=float, default=26.0)
    parser.add_argument(
        "--override",
        choices=("auto", "on", "off"),
        default="auto",
    )
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--interval", type=float, default=5.0)
    return parser


def main() -> int:
    """Run one home-automation evaluation cycle."""
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    climate: TemperatureHumiditySensor
    motion: DigitalInput
    relay: Relay

    if args.simulation:
        climate = SimulatedTemperatureHumiditySensor(base_temperature_c=29.0)
        motion = FakeDigitalInput(state=True)
        relay = FakeDigitalOutput()
    else:
        climate = DhtTemperatureHumiditySensor(args.dht_pin, model=args.dht_model)
        motion = GpioZeroDigitalInput(args.motion_pin)
        relay = GpioZeroRelay(args.relay_pin)

    controller = HomeAutomationController(
        climate,
        motion,
        relay,
        policy=AutomationPolicy(
            temperature_on_c=args.temperature_on,
            temperature_off_c=args.temperature_off,
        ),
    )
    controller.set_override(OverrideMode(args.override))

    if not isfinite(args.interval) or args.interval <= 0:
        raise ValueError("interval must be a positive finite number")

    try:
        controller.open()
        if args.continuous:
            while True:
                controller.evaluate_once()
                time.sleep(args.interval)
        else:
            controller.evaluate_once()
    except KeyboardInterrupt:
        return 0
    finally:
        controller.close()

    return 0
