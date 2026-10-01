"""Tests for Raspberry Pi adapters that do not require GPIO hardware."""

import builtins
from typing import Any

import pytest

from iot_pi.hardware.errors import HardwareUnavailableError
from iot_pi.hardware.gpiozero import GpioZeroDigitalInput, GpioZeroRelay


class FakeButton:
    """Minimal gpiozero Button test double."""

    def __init__(self, pin: int, *, pull_up: bool) -> None:
        self.pin = pin
        self.pull_up = pull_up
        self.is_pressed = True
        self.closed = False

    def close(self) -> None:
        """Record resource cleanup."""
        self.closed = True


class FakeOutputDevice:
    """Minimal gpiozero OutputDevice test double."""

    def __init__(
        self,
        pin: int,
        *,
        active_high: bool,
        initial_value: bool,
    ) -> None:
        self.pin = pin
        self.active_high = active_high
        self.value = initial_value
        self.closed = False

    def on(self) -> None:
        """Switch the fake output on."""
        self.value = True

    def off(self) -> None:
        """Switch the fake output off."""
        self.value = False

    def close(self) -> None:
        """Record resource cleanup."""
        self.closed = True


def test_gpiozero_is_loaded_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    """Creating an adapter should not import gpiozero until it is opened."""
    adapter = GpioZeroDigitalInput(pin=17)
    real_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "gpiozero":
            raise ImportError("gpiozero intentionally unavailable")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    with pytest.raises(HardwareUnavailableError, match="gpiozero is unavailable"):
        adapter.open()


def test_digital_input_adapter_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The digital input adapter should expose and release device state."""
    monkeypatch.setattr(
        "iot_pi.hardware.gpiozero._load_gpiozero",
        lambda: (FakeButton, FakeOutputDevice),
    )
    adapter = GpioZeroDigitalInput(pin=17, pull_up=False)

    with pytest.raises(HardwareUnavailableError, match="not open"):
        adapter.read()

    adapter.open()
    adapter.open()

    assert adapter.read() is True

    adapter.close()
    adapter.close()

    with pytest.raises(HardwareUnavailableError, match="not open"):
        adapter.read()


def test_relay_adapter_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """The relay adapter should control state and fail safe on close."""
    monkeypatch.setattr(
        "iot_pi.hardware.gpiozero._load_gpiozero",
        lambda: (FakeButton, FakeOutputDevice),
    )
    relay = GpioZeroRelay(pin=27, active_high=False, initial_state=False)

    with pytest.raises(HardwareUnavailableError, match="not open"):
        relay.read()
    with pytest.raises(HardwareUnavailableError, match="not open"):
        relay.write(True)

    relay.open()
    relay.open()

    assert relay.read() is False

    relay.write(True)
    assert relay.read() is True

    relay.write(False)
    assert relay.read() is False

    relay.close()
    relay.close()

    with pytest.raises(HardwareUnavailableError, match="not open"):
        relay.read()
