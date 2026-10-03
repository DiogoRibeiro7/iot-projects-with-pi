"""Tests for MQTT topic conventions."""

from iot_pi.messaging.topics import command_topic, state_topic, telemetry_topic


def test_topic_helpers_follow_stable_convention() -> None:
    """Topic helpers should produce predictable device-scoped paths."""
    assert telemetry_topic("pi-01", "weather") == "iot/pi-01/telemetry/weather"
    assert state_topic("pi-01", "relay") == "iot/pi-01/state/relay"
    assert command_topic("pi-01", "relay") == "iot/pi-01/command/relay"
