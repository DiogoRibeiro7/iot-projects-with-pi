"""Typed interfaces shared by hardware adapters."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class Lifecycle(Protocol):
    """Lifecycle contract for hardware resources."""

    def open(self) -> None:
        """Initialize the resource."""

    def close(self) -> None:
        """Release the resource."""


@runtime_checkable
class DigitalInput(Lifecycle, Protocol):
    """Digital input abstraction."""

    def read(self) -> bool:
        """Return the current logical input state."""


@runtime_checkable
class DigitalOutput(Lifecycle, Protocol):
    """Digital output abstraction."""

    def write(self, state: bool) -> None:
        """Set the logical output state."""

    def read(self) -> bool:
        """Return the current logical output state."""


@runtime_checkable
class AnalogSensor(Lifecycle, Protocol):
    """Analogue sensor abstraction for ADC-backed devices."""

    def read(self) -> float:
        """Return the current sensor value."""


@dataclass(frozen=True, slots=True)
class TemperatureHumidityReading:
    """Environmental reading returned by a combined sensor."""

    temperature_c: float
    relative_humidity_percent: float


@runtime_checkable
class TemperatureHumiditySensor(Lifecycle, Protocol):
    """Combined temperature and humidity sensor abstraction."""

    def read(self) -> TemperatureHumidityReading:
        """Return one environmental observation."""


@runtime_checkable
class MotionSensor(DigitalInput, Protocol):
    """Motion or occupancy sensor abstraction."""


@runtime_checkable
class Relay(DigitalOutput, Protocol):
    """Relay actuator abstraction."""
