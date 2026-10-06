"""Validate release tags and built Python artifacts."""

from __future__ import annotations

import argparse
import re
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path


def normalize_distribution_name(name: str) -> str:
    """Normalize a Python distribution name for comparison."""
    return re.sub(r"[-_.]+", "-", name).lower()


def read_project_metadata(path: Path) -> tuple[str, str]:
    """Read project name and version from pyproject.toml."""
    import tomllib

    with path.open("rb") as stream:
        project = tomllib.load(stream)["project"]

    name = project["name"]
    version = project["version"]
    if not isinstance(name, str) or not isinstance(version, str):
        raise ValueError("project name and version must be strings")
    return name, version


def _parse_package_metadata(payload: str) -> tuple[str, str]:
    """Extract Name and Version fields from Python package metadata."""
    metadata = Parser().parsestr(payload)
    name = metadata.get("Name")
    version = metadata.get("Version")
    if not name or not version:
        raise ValueError("package metadata must contain Name and Version")
    return name, version


def read_wheel_metadata(path: Path) -> tuple[str, str]:
    """Read package metadata from a wheel archive."""
    with zipfile.ZipFile(path) as archive:
        candidates = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(candidates) != 1:
            raise ValueError(
                f"{path.name} must contain exactly one .dist-info/METADATA file"
            )
        payload = archive.read(candidates[0]).decode("utf-8")
    return _parse_package_metadata(payload)


def read_sdist_metadata(path: Path) -> tuple[str, str]:
    """Read package metadata from a gzip-compressed source distribution."""
    with tarfile.open(path, mode="r:gz") as archive:
        candidates = [
            member
            for member in archive.getmembers()
            if member.isfile() and member.name.endswith("/PKG-INFO")
        ]
        if len(candidates) != 1:
            raise ValueError(
                f"{path.name} must contain exactly one top-level PKG-INFO file"
            )
        stream = archive.extractfile(candidates[0])
        if stream is None:
            raise ValueError(f"unable to read PKG-INFO from {path.name}")
        payload = stream.read().decode("utf-8")
    return _parse_package_metadata(payload)


def validate_artifact_metadata(
    *,
    expected_name: str,
    expected_version: str,
    artifact_name: str,
    actual_name: str,
    actual_version: str,
) -> None:
    """Validate one built artifact against project metadata."""
    if normalize_distribution_name(actual_name) != normalize_distribution_name(
        expected_name
    ):
        raise ValueError(
            f"{artifact_name} has package name {actual_name!r}, "
            f"expected {expected_name!r}"
        )
    if actual_version != expected_version:
        raise ValueError(
            f"{artifact_name} has version {actual_version!r}, "
            f"expected {expected_version!r}"
        )


def validate_release(
    *,
    project_path: Path,
    dist_dir: Path,
    tag: str,
) -> tuple[Path, Path]:
    """Validate tag, wheel, and source distribution for a release."""
    project_name, project_version = read_project_metadata(project_path)
    expected_tag = f"v{project_version}"
    if tag != expected_tag:
        raise ValueError(f"tag {tag!r} does not match project version {expected_tag!r}")

    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1:
        raise ValueError("dist must contain exactly one wheel")
    if len(sdists) != 1:
        raise ValueError("dist must contain exactly one .tar.gz source distribution")

    wheel_name, wheel_version = read_wheel_metadata(wheels[0])
    validate_artifact_metadata(
        expected_name=project_name,
        expected_version=project_version,
        artifact_name=wheels[0].name,
        actual_name=wheel_name,
        actual_version=wheel_version,
    )

    sdist_name, sdist_version = read_sdist_metadata(sdists[0])
    validate_artifact_metadata(
        expected_name=project_name,
        expected_version=project_version,
        artifact_name=sdists[0].name,
        actual_name=sdist_name,
        actual_version=sdist_version,
    )

    return wheels[0], sdists[0]


def build_parser() -> argparse.ArgumentParser:
    """Build the release-validation command-line parser."""
    parser = argparse.ArgumentParser(
        description="Validate a version tag and built Python release artifacts"
    )
    parser.add_argument("--tag", required=True)
    parser.add_argument(
        "--project",
        type=Path,
        default=Path("pyproject.toml"),
    )
    parser.add_argument(
        "--dist",
        type=Path,
        default=Path("dist"),
    )
    return parser


def main() -> int:
    """Validate the requested release and print the validated artifacts."""
    args = build_parser().parse_args()
    wheel, sdist = validate_release(
        project_path=args.project,
        dist_dir=args.dist,
        tag=args.tag,
    )
    print(f"validated {wheel.name}")
    print(f"validated {sdist.name}")
    return 0


