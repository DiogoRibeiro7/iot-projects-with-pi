"""Pure irrigation rules for smart agriculture."""

from dataclasses import dataclass
from enum import Enum


class IrrigationState(str, Enum):
    """Logical irrigation actuator state."""

    OFF = "off"
    ON = "on"


@dataclass(frozen=True, slots=True)
class IrrigationDecision:
    """Result of evaluating one irrigation cycle."""

    desired_state: IrrigationState
    reason: str


@dataclass(frozen=True, slots=True)
class IrrigationPolicy:
    """Moisture-driven irrigation policy with hysteresis."""

    dry_on_percent: float = 30.0
    wet_off_percent: float = 45.0

    def __post_init__(self) -> None:
        """Validate moisture thresholds."""
        if not 0.0 <= self.dry_on_percent <= 100.0:
            raise ValueError("dry_on_percent must be between 0 and 100")
        if not 0.0 <= self.wet_off_percent <= 100.0:
            raise ValueError("wet_off_percent must be between 0 and 100")
        if self.dry_on_percent >= self.wet_off_percent:
            raise ValueError("dry_on_percent must be lower than wet_off_percent")

    def evaluate(
        self,
        *,
        soil_moisture_percent: float,
        current_state: IrrigationState,
    ) -> IrrigationDecision:
        """Return the desired pump state for the current moisture level."""
        if not 0.0 <= soil_moisture_percent <= 100.0:
            raise ValueError("soil_moisture_percent must be between 0 and 100")

        if current_state is IrrigationState.OFF:
            if soil_moisture_percent <= self.dry_on_percent:
                return IrrigationDecision(IrrigationState.ON, "soil_dry")
            return IrrigationDecision(IrrigationState.OFF, "moisture_sufficient")

        if soil_moisture_percent >= self.wet_off_percent:
            return IrrigationDecision(IrrigationState.OFF, "soil_rehydrated")

        return IrrigationDecision(IrrigationState.ON, "hysteresis_hold")
