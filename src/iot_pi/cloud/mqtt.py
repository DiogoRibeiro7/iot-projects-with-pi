"""MQTT-backed reference cloud telemetry sink."""

from __future__ import annotations

from collections.abc import Sequence

from iot_pi.messaging.models import TelemetryMessage
from iot_pi.messaging.mqtt import PahoMqttPublisher


class MqttCloudTelemetrySink:
    """Forward telemetry through an authenticated/TLS-capable MQTT publisher."""

    def __init__(
        self,
        host: str,
        *,
        port: int = 8883,
        client_id: str = "",
        topic_prefix: str = "devices",
        qos: int = 1,
        username: str | None = None,
        password: str | None = None,
        tls_enabled: bool = True,
        ca_cert: str | None = None,
        client_cert: str | None = None,
        client_key: str | None = None,
    ) -> None:
        """Create a cloud sink without opening a network connection."""
        if not host.strip():
            raise ValueError("host must not be empty")
        if not topic_prefix.strip("/"):
            raise ValueError("topic_prefix must not be empty")
        if qos not in {0, 1, 2}:
            raise ValueError("qos must be 0, 1, or 2")

        self._topic_prefix = topic_prefix.strip("/")
        self._qos = qos
        self._publisher = PahoMqttPublisher(
            host,
            port=port,
            client_id=client_id,
            username=username,
            password=password,
            tls_enabled=tls_enabled,
            ca_cert=ca_cert,
            client_cert=client_cert,
            client_key=client_key,
        )

    def open(self) -> None:
        """Connect the MQTT publisher."""
        self._publisher.open()

    def close(self) -> None:
        """Disconnect the MQTT publisher."""
        self._publisher.close()

    def send_batch(self, messages: Sequence[TelemetryMessage]) -> None:
        """Publish each telemetry envelope in order."""
        for message in messages:
            topic = (
                f"{self._topic_prefix}/{message.device_id}/telemetry/{message.event}"
            )
            self._publisher.publish(
                topic,
                message.to_json(),
                qos=self._qos,
                retain=False,
            )
