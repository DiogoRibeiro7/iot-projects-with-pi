"""CLI for hardware-free fleet manifest validation."""

from argparse import ArgumentParser
from pathlib import Path

from iot_pi.fleet import validate_fleet


def build_parser() -> ArgumentParser:
    """Build the fleet validation CLI parser."""
    parser = ArgumentParser(description="Validate a Raspberry Pi fleet manifest")
    parser.add_argument("manifest", type=Path)
    return parser


def main() -> int:
    """Validate and print the normalized fleet manifest."""
    args = build_parser().parse_args()
    manifest = validate_fleet(args.manifest)
    print(manifest.to_json())
    return 0
