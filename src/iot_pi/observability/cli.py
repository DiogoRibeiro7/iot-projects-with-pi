"""Command-line interface for local device health inspection."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from iot_pi.observability.state import HealthStateFile


def build_parser() -> ArgumentParser:
    """Build the health-status command-line parser."""
    parser = ArgumentParser(description="Print the latest IoT device health snapshot")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("data/health.json"),
        help="Path to the persisted health JSON state.",
    )
    return parser


def main() -> int:
    """Print the latest persisted health snapshot."""
    args = build_parser().parse_args()
    snapshot = HealthStateFile(args.file).read()
    print(snapshot.to_json())
    return 0
