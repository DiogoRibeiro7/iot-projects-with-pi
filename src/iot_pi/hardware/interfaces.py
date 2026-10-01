"""Typed interfaces shared by hardware adapters."""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class Lifecycle(Protocol):
    """Lifecycle contract for hardware resources."""

    @abstractmethod
    def open(self) -> None:
        """Initialize the resource."""

    @abstractmethod
    def close(self) -> None:
        """Release the resource."""


@runtime_checkable
class DigitalInput(Lifecycle, Protocol):
    """Digital input abstraction."""

    @abstractmethod
    def read(self) -> bool:
        """Return the current logical input state."""


@runtime_checkable
class DigitalOutput(Lifecycle, Protocol):
    """Digital output abstraction."""

    @abstractmethod
    def write(self, state: bool) -> None:
        """Set the logical output state."""

    @abstractmethod
    def read(self) -> bool:
        """Return the current logical output state."""


@runtime_checkable
class AnalogSensor(Lifecycle, Protocol):
    """Analogue sensor abstraction for ADC-backed devices."""

    @abstractmethod
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

    @abstractmethod
    def read(self) -> TemperatureHumidityReading:
        """Return one environmental observation."""


@runtime_checkable
class MotionSensor(DigitalInput, Protocol):
    """Motion or occupancy sensor abstraction."""


@runtime_checkable
class Relay(DigitalOutput, Protocol):
    """Relay actuator abstraction."""
