"""CLI for side-effect-free fleet deployment planning."""

from argparse import ArgumentParser
from pathlib import Path

from iot_pi.deployment_plan import build_deployment_plan


def build_parser() -> ArgumentParser:
    """Build the deployment-plan CLI parser."""
    parser = ArgumentParser(description="Generate a fleet deployment plan")
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--device-id",
        action="append",
        default=[],
        help="limit the plan to one or more device IDs",
    )
    parser.add_argument(
        "--label",
        action="append",
        default=[],
        help="require one or more fleet labels",
    )
    return parser


def main() -> int:
    """Build and print a deterministic deployment plan."""
    args = build_parser().parse_args()
    plan = build_deployment_plan(
        args.manifest,
        device_ids=set(args.device_id),
        labels=set(args.label),
    )
    print(plan.to_json())
    return 0
