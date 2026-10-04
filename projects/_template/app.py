"""Minimal entry point for a new IoT project."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Minimal project configuration used by the template."""

    device_id: str = "pi-example"
    simulation: bool = True


def run(config: ProjectConfig) -> int:
    """Run one template application cycle."""
    mode = "simulation" if config.simulation else "hardware"
    print(f"{config.device_id}: running in {mode} mode")
    return 0


def main() -> int:
    """Run the template with safe defaults."""
    return run(ProjectConfig())


if __name__ == "__main__":
    raise SystemExit(main())
