"""Hardware-free deployment planning from fleet manifests."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from iot_pi.fleet import FleetDevice, validate_fleet

_SERVICE_NAMES = {
    "weather": "iot-weather.service",
    "home": "iot-home.service",
    "agriculture": "iot-agriculture.service",
}


@dataclass(frozen=True, slots=True)
class DeploymentPlanItem:
    """One planned device deployment action."""

    device_id: str
    application: str
    service: str
    config_path: str
    labels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeploymentPlan:
    """Deterministic, side-effect-free deployment plan."""

    items: tuple[DeploymentPlanItem, ...]

    def to_json(self) -> str:
        """Serialize the deployment plan deterministically."""
        return json.dumps(
            {"items": [asdict(item) for item in self.items]},
            indent=2,
            sort_keys=True,
        )


def _matches(
    device: FleetDevice,
    *,
    device_ids: set[str],
    labels: set[str],
) -> bool:
    """Return whether one device satisfies the requested filters."""
    if device_ids and device.device_id not in device_ids:
        return False
    return not labels or labels.issubset(set(device.labels))


def build_deployment_plan(
    manifest_path: Path,
    *,
    device_ids: set[str] | None = None,
    labels: set[str] | None = None,
) -> DeploymentPlan:
    """Validate a fleet manifest and derive a deterministic deployment plan."""
    manifest = validate_fleet(manifest_path)
    selected_device_ids = device_ids or set()
    selected_labels = labels or set()

    known_ids = {device.device_id for device in manifest.devices}
    unknown_ids = sorted(selected_device_ids - known_ids)
    if unknown_ids:
        raise ValueError("unknown fleet device_id values: " + ", ".join(unknown_ids))

    items: list[DeploymentPlanItem] = []
    for device in manifest.devices:
        if not _matches(
            device,
            device_ids=selected_device_ids,
            labels=selected_labels,
        ):
            continue

        items.append(
            DeploymentPlanItem(
                device_id=device.device_id,
                application=device.application,
                service=_SERVICE_NAMES[device.application],
                config_path=str((manifest_path.parent / device.config).resolve()),
                labels=device.labels,
            )
        )

    return DeploymentPlan(tuple(items))
