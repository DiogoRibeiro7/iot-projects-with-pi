"""Command-line interface for local device health inspection."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from iot_pi.messaging.mqtt import PahoMqttPublisher
from iot_pi.observability.state import HealthStateFile, MqttHealthStatePublisher


def build_parser() -> ArgumentParser:
    """Build the health-status command-line parser."""
    parser = ArgumentParser(description="Print or publish the latest health snapshot")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("data/health.json"),
        help="Path to the persisted health JSON state.",
    )
    parser.add_argument("--mqtt-host")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--device-id")
    return parser


def main() -> int:
    """Print the latest health snapshot and optionally publish retained state."""
    args = build_parser().parse_args()
    snapshot = HealthStateFile(args.file).read()
    print(snapshot.to_json())

    if args.mqtt_host:
        if not args.device_id:
            raise ValueError("--device-id is required when --mqtt-host is used")

        publisher = PahoMqttPublisher(
            args.mqtt_host,
            port=args.mqtt_port,
            client_id=f"{args.device_id}-health",
        )
        publisher.open()
        try:
            MqttHealthStatePublisher(
                publisher,
                device_id=args.device_id,
            )(snapshot)
        finally:
            publisher.close()

    return 0
