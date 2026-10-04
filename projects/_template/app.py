"""Minimal entry point for a new IoT project."""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Minimal project configuration used by the template."""

    device_id: str = "pi-example"
    simulation: bool = True


def build_parser() -> ArgumentParser:
    """Build the project command-line parser."""
    parser = ArgumentParser(description="Reusable Raspberry Pi project template")
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run with simulated hardware.",
    )
    return parser


def run(config: ProjectConfig) -> int:
    """Run one template application cycle."""
    mode = "simulation" if config.simulation else "hardware"
    print(f"{config.device_id}: running in {mode} mode")
    return 0


def main() -> int:
    """Run the template command-line application."""
    args = build_parser().parse_args()
    return run(ProjectConfig(simulation=args.simulation))


if __name__ == "__main__":
    raise SystemExit(main())
