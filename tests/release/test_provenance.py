"""Tests for release provenance metadata."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from iot_pi.release import sha256_file, write_release_provenance


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    """Artifact digests should match the standard SHA-256 implementation."""
    path = tmp_path / "artifact.bin"
    payload = b"release-artifact"
    path.write_bytes(payload)

    assert sha256_file(path) == hashlib.sha256(payload).hexdigest()


def test_write_release_provenance_records_artifact_identity(tmp_path: Path) -> None:
    """Provenance should bind tag, commit, workflow, and artifact digests."""
    project = tmp_path / "pyproject.toml"
    project.write_text(
        '[project]\nname = "iot-projects-with-pi"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    wheel = tmp_path / "package.whl"
    sdist = tmp_path / "package.tar.gz"
    wheel.write_bytes(b"wheel-bytes")
    sdist.write_bytes(b"sdist-bytes")
    output = tmp_path / "provenance.json"

    write_release_provenance(
        output_path=output,
        tag="v0.1.0",
        commit_sha="abc123",
        workflow="Release",
        build_timestamp=datetime(2026, 10, 7, 11, 0, tzinfo=UTC),
        wheel=wheel,
        sdist=sdist,
        project_path=project,
    )

    raw = json.loads(output.read_text(encoding="utf-8"))

    assert raw["version"] == "0.1.0"
    assert raw["tag"] == "v0.1.0"
    assert raw["commit_sha"] == "abc123"
    assert raw["workflow"] == "Release"
    assert raw["artifacts"]["package.whl"]["type"] == "wheel"
    assert raw["artifacts"]["package.tar.gz"]["type"] == "sdist"
    assert (
        raw["artifacts"]["package.whl"]["sha256"]
        == hashlib.sha256(b"wheel-bytes").hexdigest()
    )
    assert raw["security_evidence"]["artifact_name"] == "security-evidence-abc123"


def test_write_release_provenance_rejects_invalid_metadata(tmp_path: Path) -> None:
    """Provenance generation should reject ambiguous build identity."""
    project = tmp_path / "pyproject.toml"
    project.write_text(
        '[project]\nname = "iot-projects-with-pi"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"x")

    with pytest.raises(ValueError, match="timezone"):
        write_release_provenance(
            output_path=tmp_path / "provenance.json",
            tag="v0.1.0",
            commit_sha="abc123",
            workflow="Release",
            build_timestamp=datetime(2026, 10, 7, 11, 0),
            wheel=artifact,
            sdist=artifact,
            project_path=project,
        )

    with pytest.raises(ValueError, match="project version"):
        write_release_provenance(
            output_path=tmp_path / "provenance.json",
            tag="v9.9.9",
            commit_sha="abc123",
            workflow="Release",
            build_timestamp=datetime(2026, 10, 7, 11, 0, tzinfo=UTC),
            wheel=artifact,
            sdist=artifact,
            project_path=project,
        )
