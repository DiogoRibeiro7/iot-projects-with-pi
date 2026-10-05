"""Command-line interface for lightweight runtime profiling."""

from __future__ import annotations

import json
from argparse import ArgumentParser, ArgumentTypeError

from iot_pi.profiling.metrics import benchmark_weather_simulation


def _positive_int(value: str) -> int:
    """Parse a strictly positive integer."""
    parsed = int(value)
    if parsed <= 0:
        raise ArgumentTypeError("value must be a positive integer")
    return parsed


def build_parser() -> ArgumentParser:
    """Build the profiling command-line parser."""
    parser = ArgumentParser(description="Benchmark Raspberry Pi IoT runtime paths")
    parser.add_argument(
        "--samples",
        type=_positive_int,
        default=100_000,
        help="Number of simulated weather samples to process.",
    )
    return parser


def main() -> int:
    """Run the simulation benchmark and print JSON metrics."""
    args = build_parser().parse_args()
    result = benchmark_weather_simulation(args.samples)
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0
