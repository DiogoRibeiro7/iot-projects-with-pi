"""Tests for MQTT adapter argument validation."""

import pytest

from iot_pi.messaging.mqtt import PahoOneShotSubscriber


@pytest.mark.parametrize(
    ("qos", "timeout_seconds"),
    [(-1, 1.0), (3, 1.0), (1, 0.0), (1, -1.0)],
)
def test_one_shot_subscriber_rejects_invalid_configuration(
    qos: int,
    timeout_seconds: float,
) -> None:
    """One-shot subscriber bounds should fail before network access."""
    with pytest.raises(ValueError):
        PahoOneShotSubscriber(
            "127.0.0.1",
            "iot/test",
            qos=qos,
            timeout_seconds=timeout_seconds,
        )
