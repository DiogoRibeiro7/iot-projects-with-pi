"""Tests for release tag and artifact validation."""

from pathlib import Path

import pytest

from scripts.validate_release import (
    normalize_distribution_name,
    read_project_metadata,
    validate_artifact_metadata,
)


def test_distribution_name_normalization() -> None:
    """Python distribution separators should compare consistently."""
    assert normalize_distribution_name("iot_projects.with-pi") == "iot-projects-with-pi"


def test_project_metadata_reads_name_and_version() -> None:
    """Release validation should read the canonical PEP 621 metadata."""
    name, version = read_project_metadata(Path("pyproject.toml"))

    assert name == "iot-projects-with-pi"
    assert version == "0.1.0"


def test_artifact_metadata_accepts_matching_name_and_version() -> None:
    """Matching package metadata should pass without error."""
    validate_artifact_metadata(
        expected_name="iot-projects-with-pi",
        expected_version="0.1.0",
        artifact_name="example.whl",
        actual_name="iot_projects_with_pi",
        actual_version="0.1.0",
    )


@pytest.mark.parametrize(
    ("actual_name", "actual_version", "message"),
    [
        ("other-package", "0.1.0", "package name"),
        ("iot-projects-with-pi", "0.2.0", "version"),
    ],
)
def test_artifact_metadata_rejects_mismatch(
    actual_name: str,
    actual_version: str,
    message: str,
) -> None:
    """Package metadata must match the project release metadata."""
    with pytest.raises(ValueError, match=message):
        validate_artifact_metadata(
            expected_name="iot-projects-with-pi",
            expected_version="0.1.0",
            artifact_name="artifact",
            actual_name=actual_name,
            actual_version=actual_version,
        )
