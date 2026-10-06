"""Command-line interface for the home-automation reference project."""

import logging
import time
from argparse import ArgumentParser, BooleanOptionalAction
from pathlib import Path

from iot_pi.config import HomeConfig, load_config
from iot_pi.hardware.fake import FakeDigitalInput, FakeDigitalOutput
from iot_pi.hardware.gpiozero import GpioZeroDigitalInput, GpioZeroRelay
from iot_pi.hardware.interfaces import DigitalInput, Relay, TemperatureHumiditySensor
from iot_pi.home.rules import AutomationPolicy
from iot_pi.home.service import HomeAutomationController, OverrideMode
from iot_pi.observability.health import HealthTracker
from iot_pi.observability.state import HealthStateFile
from iot_pi.weather.sensors import (
    DhtTemperatureHumiditySensor,
    SimulatedTemperatureHumiditySensor,
)


def build_parser() -> ArgumentParser:
    """Build the CLI parser."""
    parser = ArgumentParser(description="Run the Raspberry Pi home automation demo")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--device-id")
    parser.add_argument(
        "--simulation",
        action=BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--motion-pin", type=int)
    parser.add_argument("--relay-pin", type=int)
    parser.add_argument("--dht-pin")
    parser.add_argument("--dht-model", choices=("DHT11", "DHT22"))
    parser.add_argument("--temperature-on", type=float)
    parser.add_argument("--temperature-off", type=float)
    parser.add_argument("--override", choices=("auto", "on", "off"))
    parser.add_argument(
        "--continuous",
        action=BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--interval", type=float)
    parser.add_argument("--health-file")
    return parser


def main() -> int:
    """Run one home-automation evaluation cycle."""
    args = build_parser().parse_args()
    config = load_config(
        HomeConfig,
        path=args.config,
        env_prefix="IOT_HOME_",
        cli_overrides={
            "device_id": args.device_id,
            "simulation": args.simulation,
            "motion_pin": args.motion_pin,
            "relay_pin": args.relay_pin,
            "dht_pin": args.dht_pin,
            "dht_model": args.dht_model,
            "temperature_on_c": args.temperature_on,
            "temperature_off_c": args.temperature_off,
            "override": args.override,
            "continuous": args.continuous,
            "sample_interval_seconds": args.interval,
            "health_file": args.health_file,
        },
    )
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    climate: TemperatureHumiditySensor
    motion: DigitalInput
    relay: Relay

    if config.simulation:
        climate = SimulatedTemperatureHumiditySensor(base_temperature_c=29.0)
        motion = FakeDigitalInput(state=True)
        relay = FakeDigitalOutput()
    else:
        climate = DhtTemperatureHumiditySensor(
            config.dht_pin,
            model=config.dht_model,
        )
        motion = GpioZeroDigitalInput(config.motion_pin)
        relay = GpioZeroRelay(config.relay_pin)

    health = (
        None
        if config.health_file is None
        else HealthTracker(observer=HealthStateFile(Path(config.health_file)))
    )
    controller = HomeAutomationController(
        climate,
        motion,
        relay,
        policy=AutomationPolicy(
            temperature_on_c=config.temperature_on_c,
            temperature_off_c=config.temperature_off_c,
        ),
        health=health,
    )
    controller.set_override(OverrideMode(config.override))

    try:
        controller.open()
        if config.continuous:
            while True:
                controller.evaluate_once()
                time.sleep(config.sample_interval_seconds)
        else:
            controller.evaluate_once()
    except KeyboardInterrupt:
        return 0
    finally:
        controller.close()

    return 0
