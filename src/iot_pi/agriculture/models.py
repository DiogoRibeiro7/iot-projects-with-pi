"""Domain models for smart-agriculture observations."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AgricultureObservation:
    """Validated irrigation observation."""

    timestamp: datetime
    soil_moisture_percent: float
    pump_on: bool
    reason: str
    temperature_c: float | None = None
    relative_humidity_percent: float | None = None

    def __post_init__(self) -> None:
        """Validate observation ranges and paired climate values."""
        if not 0.0 <= self.soil_moisture_percent <= 100.0:
            raise ValueError("soil_moisture_percent must be between 0 and 100")
        if not self.reason.strip():
            raise ValueError("reason must not be empty")

        climate_values = (
            self.temperature_c is not None,
            self.relative_humidity_percent is not None,
        )
        if climate_values[0] != climate_values[1]:
            raise ValueError(
                "temperature_c and relative_humidity_percent must be set together"
            )

        if self.temperature_c is not None and not -80.0 <= self.temperature_c <= 80.0:
            raise ValueError("temperature_c is outside the supported range")

        if (
            self.relative_humidity_percent is not None
            and not 0.0 <= self.relative_humidity_percent <= 100.0
        ):
            raise ValueError("relative_humidity_percent must be between 0 and 100")
