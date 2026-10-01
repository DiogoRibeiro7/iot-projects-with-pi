"""Tests for hardware-independent fake adapters."""

import pytest

from iot_pi.hardware.errors import HardwareUnavailableError
from iot_pi.hardware.fake import FakeDigitalInput, FakeDigitalOutput
from iot_pi.hardware.interfaces import DigitalInput, Relay


def test_fake_input_implements_protocol() -> None:
    """The fake input should satisfy the public digital-input protocol."""
    sensor = FakeDigitalInput(state=True)

    assert isinstance(sensor, DigitalInput)


def test_fake_input_requires_open_lifecycle() -> None:
    """Reading a closed input should fail deterministically."""
    sensor = FakeDigitalInput(state=True)

    with pytest.raises(HardwareUnavailableError, match="not open"):
        sensor.read()

    sensor.open()
    sensor.open()
    assert sensor.read() is True

    sensor.close()
    with pytest.raises(HardwareUnavailableError, match="not open"):
        sensor.read()


def test_fake_output_open_is_idempotent() -> None:
    """Opening an already-open output should preserve its current state."""
    relay = FakeDigitalOutput(initial_state=False)
    relay.open()
    relay.write(True)

    relay.open()

    assert relay.read() is True


def test_fake_output_resets_to_safe_state_on_close() -> None:
    """Closing an output should leave it de-energized."""
    relay = FakeDigitalOutput(initial_state=True)
    relay.open()

    assert relay.read() is True
    relay.write(True)
    relay.close()

    assert relay.is_open is False
    assert relay._state is False

    with pytest.raises(HardwareUnavailableError, match="not open"):
        relay.read()


def test_fake_output_satisfies_relay_protocol() -> None:
    """The fake output can stand in for relay-driven application logic."""
    relay = FakeDigitalOutput()

    assert isinstance(relay, Relay)
