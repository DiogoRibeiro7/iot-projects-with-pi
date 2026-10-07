"""Fleet inventory manifest loading and validation."""

from __future__ import annotations

import json
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

from iot_pi.config import (
    AgricultureConfig,
    HomeConfig,
    WeatherConfig,
    load_config,
)

ApplicationName = Literal["weather", "home", "agriculture"]


@dataclass(frozen=True, slots=True)
class FleetDevice:
    """One declared device deployment in a fleet manifest."""

    device_id: str
    application: ApplicationName
    config: str
    labels: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate one manifest entry."""
        if not self.device_id.strip():
            raise ValueError("fleet device_id must not be empty")
        if self.application not in {"weather", "home", "agriculture"}:
            raise ValueError("application must be one of: weather, home, agriculture")
        if not self.config.strip():
            raise ValueError("fleet config path must not be empty")
        if any(not label.strip() for label in self.labels):
            raise ValueError("fleet labels must not contain empty values")


@dataclass(frozen=True, slots=True)
class FleetManifest:
    """Validated fleet inventory."""

    devices: tuple[FleetDevice, ...]

    def __post_init__(self) -> None:
        """Validate fleet-wide invariants."""
        if not self.devices:
            raise ValueError("fleet manifest must contain at least one device")
        device_ids = [device.device_id for device in self.devices]
        duplicates = sorted(
            device_id
            for device_id in set(device_ids)
            if device_ids.count(device_id) > 1
        )
        if duplicates:
            raise ValueError("duplicate fleet device_id values: " + ", ".join(duplicates))

    def to_json(self) -> str:
        """Serialize the normalized fleet inventory."""
        return json.dumps(
            {"devices": [asdict(device) for device in self.devices]},
            indent=2,
            sort_keys=True,
        )


def load_fleet_manifest(path: Path) -> FleetManifest:
    """Load and validate a fleet manifest from TOML."""
    with path.open("rb") as stream:
        raw = tomllib.load(stream)

    allowed_top_level = {"devices"}
    unknown_top_level = sorted(set(raw) - allowed_top_level)
    if unknown_top_level:
        raise ValueError("unknown fleet manifest keys: " + ", ".join(unknown_top_level))

    raw_devices = raw.get("devices")
    if not isinstance(raw_devices, list):
        raise ValueError("fleet manifest must define [[devices]] entries")

    devices: list[FleetDevice] = []
    allowed_device_keys = {"device_id", "application", "config", "labels"}

    for index, raw_device in enumerate(raw_devices):
        if not isinstance(raw_device, dict):
            raise ValueError(f"devices[{index}] must be a TOML table")

        unknown = sorted(set(raw_device) - allowed_device_keys)
        if unknown:
            raise ValueError(f"unknown devices[{index}] keys: " + ", ".join(unknown))

        required = {"device_id", "application", "config"}
        missing = sorted(required - set(raw_device))
        if missing:
            raise ValueError(f"missing devices[{index}] keys: " + ", ".join(missing))

        labels = raw_device.get("labels", [])
        if not isinstance(labels, list) or not all(
            isinstance(label, str) for label in labels
        ):
            raise ValueError(f"devices[{index}].labels must be a string list")

        device_id = raw_device["device_id"]
        application = raw_device["application"]
        config = raw_device["config"]
        if not isinstance(device_id, str):
            raise ValueError(f"devices[{index}].device_id must be a string")
        if not isinstance(application, str):
            raise ValueError(f"devices[{index}].application must be a string")
        if not isinstance(config, str):
            raise ValueError(f"devices[{index}].config must be a string")

        devices.append(
            FleetDevice(
                device_id=device_id,
                application=cast(ApplicationName, application),
                config=config,
                labels=tuple(labels),
            )
        )

    return FleetManifest(tuple(devices))


def validate_fleet(path: Path) -> FleetManifest:
    """Validate a fleet manifest and every referenced application config."""
    manifest = load_fleet_manifest(path)
    base_directory = path.parent

    for device in manifest.devices:
        config_path = (base_directory / device.config).resolve()
        if not config_path.is_file():
            raise FileNotFoundError(f"missing config for {device.device_id}: {config_path}")

        if device.application == "weather":
            config = load_config(
                WeatherConfig,
                path=config_path,
                env_prefix="IOT_WEATHER_",
                environ={},
            )
        elif device.application == "home":
            config = load_config(
                HomeConfig,
                path=config_path,
                env_prefix="IOT_HOME_",
                environ={},
            )
        else:
            config = load_config(
                AgricultureConfig,
                path=config_path,
                env_prefix="IOT_AGRICULTURE_",
                environ={},
            )

        if config.device_id != device.device_id:
            raise ValueError(
                f"fleet device_id {device.device_id!r} does not match "
                f"{device.application} config device_id {config.device_id!r}"
            )

    return manifest
