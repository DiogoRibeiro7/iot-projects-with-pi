"""Tests for persistent device identity and deployment metadata."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from iot_pi.device import DeviceMetadata, load_device_metadata, validate_device_id


def test_device_metadata_serializes_deterministically() -> None:
    """Metadata JSON should expose stable deployment identity fields."""
    metadata = DeviceMetadata(
        device_id="weather-pi-01",
        hardware_class="raspberry-pi-zero-2-w",
        environment="production",
        site="greenhouse-west",
        software_version="0.1.0",
        deployed_at=datetime(2026, 10, 6, 21, 0, tzinfo=UTC),
    )

    rendered = metadata.to_json()

    assert '"device_id": "weather-pi-01"' in rendered
    assert '"software_version": "0.1.0"' in rendered
    assert '"deployed_at": "2026-10-06T21:00:00+00:00"' in rendered


def test_load_device_metadata_from_toml(tmp_path: Path) -> None:
    """A complete metadata TOML file should load into the typed model."""
    path = tmp_path / "device.toml"
    path.write_text(
        (
            'device_id = "farm-01"\n'
            'hardware_class = "raspberry-pi-4"\n'
            'environment = "production"\n'
            'site = "field-a"\n'
            'software_version = "0.1.0"\n'
            "deployed_at = 2026-10-06T20:30:00+00:00\n"
        ),
        encoding="utf-8",
    )

    metadata = load_device_metadata(path)

    assert metadata.device_id == "farm-01"
    assert metadata.hardware_class == "raspberry-pi-4"
    assert metadata.deployed_at.tzinfo is not None


@pytest.mark.parametrize(
    "content",
    [
        (
            'device_id = ""\n'
            'hardware_class = "raspberry-pi-4"\n'
            'environment = "production"\n'
            'site = "field-a"\n'
            'software_version = "0.1.0"\n'
            "deployed_at = 2026-10-06T20:30:00+00:00\n"
        ),
        (
            'device_id = "farm-01"\n'
            'hardware_class = "raspberry-pi-4"\n'
            'environment = "production"\n'
            'site = "field-a"\n'
            'software_version = "0.1.0"\n'
            'deployed_at = "2026-10-06T20:30:00"\n'
        ),
    ],
)
def test_load_device_metadata_rejects_invalid_values(
    tmp_path: Path,
    content: str,
) -> None:
    """Malformed metadata must fail before it can identify a deployment."""
    path = tmp_path / "device.toml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        load_device_metadata(path)


def test_validate_device_id_requires_runtime_identity_match() -> None:
    """Runtime config and persistent device identity must not silently diverge."""
    metadata = DeviceMetadata(
        device_id="weather-pi-01",
        hardware_class="raspberry-pi-zero-2-w",
        environment="production",
        site="greenhouse-west",
        software_version="0.1.0",
        deployed_at=datetime(2026, 10, 6, 21, 0, tzinfo=UTC),
    )

    validate_device_id("weather-pi-01", metadata)

    with pytest.raises(ValueError, match="does not match"):
        validate_device_id("weather-pi-02", metadata)
