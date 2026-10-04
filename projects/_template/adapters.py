"""Project-specific hardware adapter placeholders."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SimulatedInput:
    """Deterministic simulated input used for development and tests."""

    value: float = 0.0

    def read(self) -> float:
        """Return the configured simulated reading."""
        return self.value


class RaspberryPiInput:
    """Placeholder for a Raspberry Pi-specific hardware adapter."""

    def read(self) -> float:
        """Read one value from physical hardware."""
        raise NotImplementedError("implement the physical hardware adapter")
