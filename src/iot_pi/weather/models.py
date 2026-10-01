"""Domain models for weather observations."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class WeatherObservation:
    """Validated environmental observation."""

    timestamp: datetime
    temperature_c: float
    relative_humidity_percent: float
    pressure_hpa: float | None = None

    def __post_init__(self) -> None:
        """Validate physically plausible observation values."""
        if not -80.0 <= self.temperature_c <= 80.0:
            raise ValueError("temperature_c is outside the supported range")
        if not 0.0 <= self.relative_humidity_percent <= 100.0:
            raise ValueError("relative_humidity_percent must be between 0 and 100")
        if self.pressure_hpa is not None and not 300.0 <= self.pressure_hpa <= 1200.0:
            raise ValueError("pressure_hpa is outside the supported range")
