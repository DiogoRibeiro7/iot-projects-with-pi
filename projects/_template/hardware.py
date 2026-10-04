"""Hardware placeholders for a new project.

Replace project-specific adapters here only when they are not reusable enough to
belong in :mod:`iot_pi.hardware`.
"""

from typing import Protocol


class ProjectSensor(Protocol):
    """Example sensor contract for project-specific application logic."""

    def read(self) -> float:
        """Return one sensor value."""


class SimulatedProjectSensor:
    """Deterministic sensor implementation for local development."""

    def __init__(self, value: float = 1.0) -> None:
        self._value = value

    def read(self) -> float:
        """Return the configured deterministic value."""
        return self._value
