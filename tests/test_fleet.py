"""Tests for fleet manifest validation."""

from pathlib import Path

import pytest

from iot_pi.fleet import FleetDevice, FleetManifest, load_fleet_manifest, validate_fleet


def _write_config(path: Path, device_id: str) -> None:
    """Write a minimal weather config for fleet validation tests."""
    path.write_text(
        f'device_id = "{device_id}"\nsimulation = true\n',
        encoding="utf-8",
    )


def test_fleet_manifest_rejects_duplicate_device_ids() -> None:
    """Fleet inventory must keep device identities unique."""
    with pytest.raises(ValueError, match="duplicate fleet device_id"):
        FleetManifest(
            (
                FleetDevice("pi-01", "weather", "weather.toml"),
                FleetDevice("pi-01", "home", "home.toml"),
            )
        )


def test_validate_fleet_loads_referenced_config(tmp_path: Path) -> None:
    """Fleet validation should reuse the typed application config loader."""
    config = tmp_path / "weather.toml"
    _write_config(config, "weather-pi-01")
    manifest = tmp_path / "fleet.toml"
    manifest.write_text(
        (
            "[[devices]]\n"
            'device_id = "weather-pi-01"\n'
            'application = "weather"\n'
            'config = "weather.toml"\n'
            'labels = ["site:lab"]\n'
        ),
        encoding="utf-8",
    )

    validated = validate_fleet(manifest)

    assert validated.devices[0].device_id == "weather-pi-01"
    assert validated.devices[0].labels == ("site:lab",)


def test_validate_fleet_rejects_missing_config(tmp_path: Path) -> None:
    """Missing referenced configuration files must fail before deployment."""
    manifest = tmp_path / "fleet.toml"
    manifest.write_text(
        (
            "[[devices]]\n"
            'device_id = "weather-pi-01"\n'
            'application = "weather"\n'
            'config = "missing.toml"\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="missing config"):
        validate_fleet(manifest)


def test_validate_fleet_rejects_device_id_mismatch(tmp_path: Path) -> None:
    """Inventory identity and runtime configuration must agree."""
    config = tmp_path / "weather.toml"
    _write_config(config, "weather-pi-02")
    manifest = tmp_path / "fleet.toml"
    manifest.write_text(
        (
            "[[devices]]\n"
            'device_id = "weather-pi-01"\n'
            'application = "weather"\n'
            'config = "weather.toml"\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not match"):
        validate_fleet(manifest)


def test_load_fleet_manifest_rejects_unknown_application(tmp_path: Path) -> None:
    """Unsupported application names must not enter the inventory."""
    manifest = tmp_path / "fleet.toml"
    manifest.write_text(
        (
            "[[devices]]\n"
            'device_id = "pi-01"\n'
            'application = "unsupported"\n'
            'config = "config.toml"\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="application must be one of"):
        load_fleet_manifest(manifest)
