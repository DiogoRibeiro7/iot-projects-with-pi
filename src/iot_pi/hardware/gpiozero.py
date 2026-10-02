"""Raspberry Pi GPIO adapters backed by gpiozero.

The dependency is imported lazily so importing :mod:`iot_pi` remains safe on
machines without Raspberry Pi GPIO support.
"""

from typing import Any

from iot_pi.hardware.errors import HardwareUnavailableError


def _load_gpiozero() -> tuple[type[Any], type[Any], type[Exception]]:
    """Load gpiozero classes only when real hardware is requested."""
    try:
        from gpiozero import Button, OutputDevice
        from gpiozero.exc import BadPinFactory
    except (ImportError, OSError) as exc:
        raise HardwareUnavailableError(
            "gpiozero is unavailable; install the 'hardware' extra on a Raspberry Pi"
        ) from exc

    return Button, OutputDevice, BadPinFactory


class GpioZeroDigitalInput:
    """Digital input adapter using :class:`gpiozero.Button`."""

    def __init__(self, pin: int, *, pull_up: bool = True) -> None:
        """Create an unopened GPIO input adapter."""
        self._pin = pin
        self._pull_up = pull_up
        self._device: Any | None = None

    def open(self) -> None:
        """Allocate the GPIO input device."""
        if self._device is not None:
            return

        button_type, _, bad_pin_factory = _load_gpiozero()
        try:
            self._device = button_type(self._pin, pull_up=self._pull_up)
        except bad_pin_factory as exc:
            raise HardwareUnavailableError(
                "gpiozero is installed but no usable Raspberry Pi "
                "pin factory is available"
            ) from exc

    def close(self) -> None:
        """Release the GPIO input device."""
        if self._device is not None:
            self._device.close()
            self._device = None

    def read(self) -> bool:
        """Return the logical GPIO input state."""
        if self._device is None:
            raise HardwareUnavailableError("digital input is not open")
        return bool(self._device.is_pressed)


class GpioZeroRelay:
    """Relay-style digital output backed by :class:`gpiozero.OutputDevice`."""

    def __init__(
        self,
        pin: int,
        *,
        active_high: bool = True,
        initial_state: bool = False,
    ) -> None:
        """Create an unopened relay adapter."""
        self._pin = pin
        self._active_high = active_high
        self._initial_state = initial_state
        self._device: Any | None = None

    def open(self) -> None:
        """Allocate the GPIO output device."""
        if self._device is not None:
            return

        _, output_type, bad_pin_factory = _load_gpiozero()
        try:
            self._device = output_type(
                self._pin,
                active_high=self._active_high,
                initial_value=self._initial_state,
            )
        except bad_pin_factory as exc:
            raise HardwareUnavailableError(
                "gpiozero is installed but no usable Raspberry Pi "
                "pin factory is available"
            ) from exc

    def close(self) -> None:
        """Switch the relay off and release GPIO resources."""
        if self._device is not None:
            self._device.off()
            self._device.close()
            self._device = None

    def write(self, state: bool) -> None:
        """Set the relay logical state."""
        if self._device is None:
            raise HardwareUnavailableError("relay is not open")
        if state:
            self._device.on()
        else:
            self._device.off()

    def read(self) -> bool:
        """Return the current logical relay state."""
        if self._device is None:
            raise HardwareUnavailableError("relay is not open")
        return bool(self._device.value)
