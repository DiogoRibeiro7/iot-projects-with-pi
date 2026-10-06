"""CLI for inspecting persistent device deployment metadata."""

from argparse import ArgumentParser
from pathlib import Path

from iot_pi.device import load_device_metadata


def build_parser() -> ArgumentParser:
    """Build the device metadata CLI parser."""
    parser = ArgumentParser(description="Inspect persistent device deployment metadata")
    parser.add_argument("path", type=Path, help="path to the device metadata TOML file")
    return parser


def main() -> int:
    """Load, validate, and print device metadata."""
    args = build_parser().parse_args()
    metadata = load_device_metadata(args.path)
    print(metadata.to_json())
    return 0
