"""Minimal entry point for a new IoT project."""

from __future__ import annotations

import json
import tomllib
from argparse import ArgumentParser
from dataclasses import replace
from pathlib import Path
from typing import Any

from iot_pi.config import AppConfig


def build_parser() -> ArgumentParser:
    """Build the project command-line parser."""
    project_dir = Path(__file__).resolve().parent

    parser = ArgumentParser(description="Reusable Raspberry Pi project template")
    parser.add_argument(
        "--config",
        type=Path,
        default=project_dir / "config.example.toml",
        help="Path to the project TOML configuration.",
    )
    parser.add_argument(
        "--simulation-fixture",
        type=Path,
        default=project_dir / "simulation.json",
        help="Path to deterministic simulation data.",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--simulation",
        dest="simulation",
        action="store_true",
        default=None,
        help="Override configuration and use simulated hardware.",
    )
    mode.add_argument(
        "--hardware",
        dest="simulation",
        action="store_false",
        help="Override configuration and use physical hardware.",
    )
    return parser


def load_config(path: Path) -> AppConfig:
    """Load and validate project configuration from TOML."""
    with path.open("rb") as stream:
        raw: dict[str, Any] = tomllib.load(stream)

    return AppConfig(
        device_id=str(raw["device_id"]),
        sample_interval_seconds=float(raw["sample_interval_seconds"]),
        simulation=bool(raw["simulation"]),
    )


def load_simulation_readings(path: Path) -> list[float]:
    """Load deterministic simulation readings from JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    readings = raw.get("readings")
    if not isinstance(readings, list) or not readings:
        raise ValueError("simulation fixture must contain a non-empty readings list")

    return [float(value) for value in readings]


def run(config: AppConfig, *, readings: list[float] | None = None) -> int:
    """Run one template application cycle."""
    mode = "simulation" if config.simulation else "hardware"
    print(
        f"{config.device_id}: running in {mode} mode "
        f"every {config.sample_interval_seconds:g}s"
    )

    if config.simulation:
        if not readings:
            raise ValueError("simulation mode requires deterministic readings")
        print(f"simulated reading: {readings[0]:g}")

    return 0


def main() -> int:
    """Run the template command-line application."""
    args = build_parser().parse_args()
    config = load_config(args.config)

    if args.simulation is not None:
        config = replace(config, simulation=args.simulation)

    readings = (
        load_simulation_readings(args.simulation_fixture)
        if config.simulation
        else None
    )
    return run(config, readings=readings)


if __name__ == "__main__":
    raise SystemExit(main())
