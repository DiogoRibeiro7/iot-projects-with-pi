"""Tests for fleet deployment planning."""

from pathlib import Path

import pytest

from iot_pi.deployment_plan import build_deployment_plan


def _write_weather_config(path: Path, device_id: str) -> None:
    """Write a minimal valid weather configuration."""
    path.write_text(
        f'device_id = "{device_id}"\nsimulation = true\n',
        encoding="utf-8",
    )


def _write_home_config(path: Path, device_id: str) -> None:
    """Write a minimal valid home configuration."""
    path.write_text(
        f'device_id = "{device_id}"\nsimulation = true\n',
        encoding="utf-8",
    )


def _write_manifest(tmp_path: Path) -> Path:
    """Create a deterministic two-device fleet manifest."""
    _write_weather_config(tmp_path / "weather.toml", "weather-01")
    _write_home_config(tmp_path / "home.toml", "home-01")
    manifest = tmp_path / "fleet.toml"
    manifest.write_text(
        (
            "[[devices]]\n"
            'device_id = "weather-01"\n'
            'application = "weather"\n'
            'config = "weather.toml"\n'
            'labels = ["site:lab", "tier:canary"]\n'
            "\n"
            "[[devices]]\n"
            'device_id = "home-01"\n'
            'application = "home"\n'
            'config = "home.toml"\n'
            'labels = ["site:office"]\n'
        ),
        encoding="utf-8",
    )
    return manifest


def test_build_deployment_plan_preserves_manifest_order(tmp_path: Path) -> None:
    """Deployment plans should preserve declared fleet order."""
    manifest = _write_manifest(tmp_path)

    plan = build_deployment_plan(manifest)

    assert [item.device_id for item in plan.items] == ["weather-01", "home-01"]
    assert plan.items[0].service == "iot-weather.service"
    assert plan.items[1].service == "iot-home.service"
    assert plan.items[0].config_path == str((tmp_path / "weather.toml").resolve())


def test_build_deployment_plan_filters_by_device_id(tmp_path: Path) -> None:
    """Device filtering should select only requested inventory entries."""
    manifest = _write_manifest(tmp_path)

    plan = build_deployment_plan(manifest, device_ids={"home-01"})

    assert [item.device_id for item in plan.items] == ["home-01"]


def test_build_deployment_plan_filters_by_all_labels(tmp_path: Path) -> None:
    """Label filters should require every requested label."""
    manifest = _write_manifest(tmp_path)

    plan = build_deployment_plan(
        manifest,
        labels={"site:lab", "tier:canary"},
    )

    assert [item.device_id for item in plan.items] == ["weather-01"]


def test_build_deployment_plan_rejects_unknown_device_id(tmp_path: Path) -> None:
    """Unknown explicit device IDs should fail instead of producing an empty plan."""
    manifest = _write_manifest(tmp_path)

    with pytest.raises(ValueError, match="unknown fleet device_id"):
        build_deployment_plan(manifest, device_ids={"missing-01"})


def test_deployment_plan_json_is_deterministic(tmp_path: Path) -> None:
    """Plan JSON should expose stable deployment fields."""
    manifest = _write_manifest(tmp_path)

    rendered = build_deployment_plan(manifest).to_json()

    assert '"device_id": "weather-01"' in rendered
    assert '"service": "iot-weather.service"' in rendered
    assert '"application": "weather"' in rendered
