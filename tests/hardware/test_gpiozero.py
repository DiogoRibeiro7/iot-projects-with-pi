"""Tests for Raspberry Pi adapters that do not require GPIO hardware."""

import builtins

import pytest

from iot_pi.hardware.errors import HardwareUnavailableError
from iot_pi.hardware.gpiozero import GpioZeroDigitalInput


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
    ) -> object:
        if name == "gpiozero":
            raise ImportError("gpiozero intentionally unavailable")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    with pytest.raises(HardwareUnavailableError, match="gpiozero is unavailable"):
        adapter.open()
