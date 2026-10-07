"""Generate machine-readable release provenance."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from iot_pi.release import validate_release, write_release_provenance


def build_parser() -> argparse.ArgumentParser:
    """Build the provenance-generation CLI parser."""
    parser = argparse.ArgumentParser(description="Generate release provenance metadata")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--build-timestamp", required=True)
    parser.add_argument("--output", type=Path, default=Path("dist/provenance.json"))
    parser.add_argument("--project", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    return parser


def main() -> int:
    """Validate artifacts and write provenance metadata."""
    args = build_parser().parse_args()
    wheel, sdist = validate_release(
        project_path=args.project,
        dist_dir=args.dist,
        tag=args.tag,
    )
    write_release_provenance(
        output_path=args.output,
        tag=args.tag,
        commit_sha=args.commit_sha,
        workflow=args.workflow,
        build_timestamp=datetime.fromisoformat(args.build_timestamp),
        wheel=wheel,
        sdist=sdist,
        project_path=args.project,
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
