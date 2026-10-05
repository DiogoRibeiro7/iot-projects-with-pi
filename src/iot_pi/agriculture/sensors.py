"""Soil-moisture sensor adapters."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from random import Random
from typing import Any, cast

from iot_pi.hardware.errors import HardwareUnavailableError


@dataclass(slots=True)
class SimulatedSoilMoistureSensor:
    """Deterministic soil-moisture simulator."""

    seed: int = 42
    base_moisture_percent: float = 35.0
    variation_percent: float = 5.0
    _random: Random | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Validate simulator bounds."""
        if not 0.0 <= self.base_moisture_percent <= 100.0:
            raise ValueError("base_moisture_percent must be between 0 and 100")
        if self.variation_percent < 0:
            raise ValueError("variation_percent must not be negative")
        if self.variation_percent > 100.0:
            raise ValueError("variation_percent must not exceed 100")

    def open(self) -> None:
        """Initialize deterministic simulator state."""
        if self._random is None:
            self._random = Random(self.seed)

    def close(self) -> None:
        """Release simulator state."""
        self._random = None

    def read(self) -> float:
        """Return one bounded simulated soil-moisture percentage."""
        if self._random is None:
            raise HardwareUnavailableError("simulated soil sensor is not open")

        value = self.base_moisture_percent + self._random.uniform(
            -self.variation_percent,
            self.variation_percent,
        )
        return round(min(100.0, max(0.0, value)), 2)


@dataclass(slots=True)
class SequenceSoilMoistureSensor:
    """Repeat a deterministic sequence of soil-moisture readings."""

    readings: Sequence[float]
    _index: int = field(default=0, init=False)
    _is_open: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Validate fixture readings."""
        if not self.readings:
            raise ValueError("readings must not be empty")
        if any(not 0.0 <= float(value) <= 100.0 for value in self.readings):
            raise ValueError("all readings must be between 0 and 100")

    def open(self) -> None:
        """Initialize sequence playback."""
        self._index = 0
        self._is_open = True

    def close(self) -> None:
        """Release sequence playback."""
        self._is_open = False

    def read(self) -> float:
        """Return the next reading and wrap at the end of the fixture."""
        if not self._is_open:
            raise HardwareUnavailableError("sequence soil sensor is not open")

        value = float(self.readings[self._index])
        self._index = (self._index + 1) % len(self.readings)
        return value


def _load_mcp3008() -> type[Any]:
    """Load gpiozero MCP3008 only when physical hardware is requested."""
    try:
        from gpiozero import MCP3008  # type: ignore[import-untyped]
    except (ImportError, OSError) as exc:
        raise HardwareUnavailableError(
            "gpiozero MCP3008 support is unavailable; install the 'hardware' extra"
        ) from exc

    return cast(type[Any], MCP3008)


class Mcp3008SoilMoistureSensor:
    """Calibrated soil-moisture sensor using an MCP3008 ADC channel."""

    def __init__(
        self,
        channel: int = 0,
        *,
        dry_raw: float = 0.8,
        wet_raw: float = 0.3,
    ) -> None:
        """Create an unopened MCP3008 soil-moisture adapter."""
        if channel not in range(8):
            raise ValueError("channel must be between 0 and 7")
        if not 0.0 <= dry_raw <= 1.0 or not 0.0 <= wet_raw <= 1.0:
            raise ValueError("dry_raw and wet_raw must be between 0 and 1")
        if dry_raw == wet_raw:
            raise ValueError("dry_raw and wet_raw must be different")

        self._channel = channel
        self._dry_raw = dry_raw
        self._wet_raw = wet_raw
        self._device: Any | None = None

    def open(self) -> None:
        """Allocate the MCP3008 channel."""
        if self._device is not None:
            return

        device_type = _load_mcp3008()
        try:
            self._device = device_type(channel=self._channel)
        except (RuntimeError, ValueError, OSError) as exc:
            raise HardwareUnavailableError("unable to initialize MCP3008") from exc

    def close(self) -> None:
        """Release the MCP3008 device."""
        if self._device is not None:
            self._device.close()
            self._device = None

    def read(self) -> float:
        """Return calibrated soil moisture as a percentage."""
        if self._device is None:
            raise HardwareUnavailableError("MCP3008 soil sensor is not open")

        raw = float(self._device.value)
        moisture = 100.0 * (raw - self._dry_raw) / (self._wet_raw - self._dry_raw)
        return round(min(100.0, max(0.0, moisture)), 2)
