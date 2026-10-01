"""Typed application configuration shared by IoT projects."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Base configuration for an IoT application.

    Attributes:
        device_id: Stable identifier for the Raspberry Pi or simulated device.
        sample_interval_seconds: Delay between consecutive sensor samples.
        simulation: Whether hardware access should be replaced by simulated adapters.
    """

    device_id: str
    sample_interval_seconds: float = 60.0
    simulation: bool = False

    def __post_init__(self) -> None:
        """Validate configuration invariants."""
        if not self.device_id.strip():
            raise ValueError("device_id must not be empty")

        if self.sample_interval_seconds <= 0:
            raise ValueError("sample_interval_seconds must be greater than zero")
