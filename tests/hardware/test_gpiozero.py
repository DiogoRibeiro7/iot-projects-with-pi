"""Tests for Raspberry Pi adapters that do not require GPIO hardware."""

import builtins
from typing import Any

import pytest

from iot_pi.hardware.errors import HardwareUnavailableError
from iot_pi.hardware.gpiozero import GpioZeroDigitalInput, GpioZeroRelay


class FakeBadPinFactory(Exception):
    """Test double for gpiozero's BadPinFactory."""


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


class BrokenButton:
    """Button test double that simulates an unusable pin factory."""

    def __init__(self, pin: int, *, pull_up: bool) -> None:
        raise FakeBadPinFactory(f"no pin factory for pin {pin}")


class BrokenOutputDevice:
    """Output test double that simulates an unusable pin factory."""

    def __init__(
        self,
        pin: int,
        *,
        active_high: bool,
        initial_value: bool,
    ) -> None:
        raise FakeBadPinFactory(f"no pin factory for pin {pin}")


def test_gpiozero_is_loaded_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    """Creating an adapter should not import gpiozero until it is opened."""
    real_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "gpiozero" or name.startswith("gpiozero."):
            raise ImportError("gpiozero intentionally unavailable")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    adapter = GpioZeroDigitalInput(pin=17)

    with pytest.raises(HardwareUnavailableError, match="gpiozero is unavailable"):
        adapter.open()


def test_digital_input_adapter_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The digital input adapter should expose and release device state."""
    monkeypatch.setattr(
        "iot_pi.hardware.gpiozero._load_gpiozero",
        lambda: (FakeButton, FakeOutputDevice, FakeBadPinFactory),
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


def test_digital_input_wraps_bad_pin_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unusable gpiozero backend should map to the public error type."""
    monkeypatch.setattr(
        "iot_pi.hardware.gpiozero._load_gpiozero",
        lambda: (BrokenButton, FakeOutputDevice, FakeBadPinFactory),
    )
    adapter = GpioZeroDigitalInput(pin=17)

    with pytest.raises(HardwareUnavailableError, match="no usable Raspberry Pi"):
        adapter.open()


def test_relay_adapter_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """The relay adapter should control state and fail safe on close."""
    monkeypatch.setattr(
        "iot_pi.hardware.gpiozero._load_gpiozero",
        lambda: (FakeButton, FakeOutputDevice, FakeBadPinFactory),
    )
    relay = GpioZeroRelay(pin=27, active_high=False, initial_state=False)

    with pytest.raises(HardwareUnavailableError, match="not open"):
        relay.read()
    with pytest.raises(HardwareUnavailableError, match="not open"):
        relay.write(True)

    relay.open()
    relay.open()

    device = relay._device
    assert isinstance(device, FakeOutputDevice)
    assert relay.read() is False

    relay.write(True)
    assert relay.read() is True

    relay.close()
    relay.close()

    assert device.value is False
    assert device.closed is True

    with pytest.raises(HardwareUnavailableError, match="not open"):
        relay.read()


def test_relay_wraps_bad_pin_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Relay initialization should normalize pin-factory failures."""
    monkeypatch.setattr(
        "iot_pi.hardware.gpiozero._load_gpiozero",
        lambda: (FakeButton, BrokenOutputDevice, FakeBadPinFactory),
    )
    relay = GpioZeroRelay(pin=27)

    with pytest.raises(HardwareUnavailableError, match="no usable Raspberry Pi"):
        relay.open()
