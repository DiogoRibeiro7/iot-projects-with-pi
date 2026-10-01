"""Pure business rules for home automation."""

from dataclasses import dataclass
from enum import Enum


class AutomationState(str, Enum):
    """Logical actuator state."""

    OFF = "off"
    ON = "on"


@dataclass(frozen=True, slots=True)
class AutomationDecision:
    """Result of evaluating one automation cycle."""

    desired_state: AutomationState
    reason: str


@dataclass(frozen=True, slots=True)
class AutomationPolicy:
    """Configurable rule set independent from GPIO or sensor libraries."""

    temperature_on_c: float = 28.0
    temperature_off_c: float = 26.0
    require_motion: bool = True

    def __post_init__(self) -> None:
        """Validate hysteresis configuration."""
        if self.temperature_off_c >= self.temperature_on_c:
            raise ValueError("temperature_off_c must be lower than temperature_on_c")

    def evaluate(
        self,
        *,
        temperature_c: float,
        motion_detected: bool,
        current_state: AutomationState,
    ) -> AutomationDecision:
        """Evaluate the next desired actuator state."""
        if self.require_motion and not motion_detected:
            return AutomationDecision(AutomationState.OFF, "no_motion")

        if current_state is AutomationState.OFF:
            if temperature_c >= self.temperature_on_c:
                return AutomationDecision(AutomationState.ON, "temperature_high")
            return AutomationDecision(AutomationState.OFF, "below_on_threshold")

        if temperature_c <= self.temperature_off_c:
            return AutomationDecision(AutomationState.OFF, "temperature_recovered")

        return AutomationDecision(AutomationState.ON, "hysteresis_hold")
