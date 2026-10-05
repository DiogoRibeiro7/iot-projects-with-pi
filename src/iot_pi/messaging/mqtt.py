"""Paho MQTT adapter with bounded reconnect backoff."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from iot_pi.hardware.errors import HardwareUnavailableError


class PahoMqttPublisher:
    """MQTT publisher backed by paho-mqtt."""

    def __init__(
        self,
        host: str,
        *,
        port: int = 1883,
        client_id: str = "",
        connect_retries: int = 3,
        backoff_seconds: float = 1.0,
        username: str | None = None,
        password: str | None = None,
        tls_enabled: bool = False,
        ca_cert: str | None = None,
        client_cert: str | None = None,
        client_key: str | None = None,
    ) -> None:
        """Create an unopened MQTT publisher."""
        if connect_retries <= 0:
            raise ValueError("connect_retries must be greater than zero")
        if backoff_seconds <= 0:
            raise ValueError("backoff_seconds must be greater than zero")

        self._host = host
        self._port = port
        self._client_id = client_id
        self._connect_retries = connect_retries
        self._backoff_seconds = backoff_seconds
        self._username = username
        self._password = password
        self._tls_enabled = tls_enabled
        self._ca_cert = ca_cert
        self._client_cert = client_cert
        self._client_key = client_key
        self._client: Any | None = None

    def open(self) -> None:
        """Connect to the broker with bounded exponential backoff."""
        if self._client is not None:
            return

        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise HardwareUnavailableError(
                "paho-mqtt is unavailable; install the 'mqtt' extra"
            ) from exc

        last_error: Exception | None = None
        for attempt in range(self._connect_retries):
            callback_api = mqtt.CallbackAPIVersion.VERSION2  # type: ignore[attr-defined]
            client = mqtt.Client(
                callback_api,
                client_id=self._client_id,
            )
            if self._username is not None:
                client.username_pw_set(self._username, self._password)
            if self._tls_enabled:
                client.tls_set(
                    ca_certs=self._ca_cert,
                    certfile=self._client_cert,
                    keyfile=self._client_key,
                )
            try:
                client.connect(self._host, self._port)
                client.loop_start()
            except OSError as exc:
                last_error = exc
                if attempt < self._connect_retries - 1:
                    time.sleep(self._backoff_seconds * (2**attempt))
                continue

            self._client = client
            return

        raise HardwareUnavailableError(
            f"unable to connect to MQTT broker after {self._connect_retries} attempts"
        ) from last_error

    def close(self) -> None:
        """Stop network processing and disconnect."""
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None

    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        """Publish one MQTT message."""
        if self._client is None:
            raise HardwareUnavailableError("MQTT publisher is not open")
        if qos not in {0, 1, 2}:
            raise ValueError("qos must be 0, 1, or 2")

        result = self._client.publish(topic, payload, qos=qos, retain=retain)
        if getattr(result, "rc", 0) != 0:
            raise HardwareUnavailableError("MQTT publish failed")


class PahoCommandSubscriber:
    """Small command subscriber that forwards UTF-8 payloads to a handler."""

    def __init__(
        self,
        host: str,
        topic: str,
        handler: Callable[[str], None],
        *,
        port: int = 1883,
        qos: int = 1,
    ) -> None:
        """Create an unopened command subscriber."""
        self._host = host
        self._port = port
        self._topic = topic
        self._handler = handler
        self._qos = qos
        self._client: Any | None = None

    def open(self) -> None:
        """Connect and subscribe."""
        if self._client is not None:
            return

        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise HardwareUnavailableError(
                "paho-mqtt is unavailable; install the 'mqtt' extra"
            ) from exc

        callback_api = mqtt.CallbackAPIVersion.VERSION2  # type: ignore[attr-defined]
        client = mqtt.Client(callback_api)

        def on_message(
            _client: Any,
            _userdata: Any,
            message: Any,
        ) -> None:
            self._handler(message.payload.decode("utf-8"))

        client.on_message = on_message
        try:
            client.connect(self._host, self._port)
            client.subscribe(self._topic, qos=self._qos)
            client.loop_start()
        except OSError as exc:
            client.disconnect()
            raise HardwareUnavailableError("unable to connect MQTT subscriber") from exc

        self._client = client

    def close(self) -> None:
        """Stop network processing and disconnect."""
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None



class PahoOneShotSubscriber:
    """Receive one UTF-8 MQTT payload with a bounded timeout."""

    def __init__(
        self,
        host: str,
        topic: str,
        *,
        port: int = 1883,
        qos: int = 1,
        timeout_seconds: float = 5.0,
    ) -> None:
        """Create an unopened one-shot subscriber."""
        if qos not in {0, 1, 2}:
            raise ValueError("qos must be 0, 1, or 2")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self._host = host
        self._port = port
        self._topic = topic
        self._qos = qos
        self._timeout_seconds = timeout_seconds

    def receive(self) -> str:
        """Connect, subscribe, receive one payload, and disconnect."""
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise HardwareUnavailableError(
                "paho-mqtt is unavailable; install the 'mqtt' extra"
            ) from exc

        from threading import Event

        received = Event()
        payload: list[str] = []

        callback_api = mqtt.CallbackAPIVersion.VERSION2  # type: ignore[attr-defined]
        client = mqtt.Client(callback_api)

        def on_message(
            _client: Any,
            _userdata: Any,
            message: Any,
        ) -> None:
            payload.append(message.payload.decode("utf-8"))
            received.set()

        client.on_message = on_message
        try:
            client.connect(self._host, self._port)
            client.subscribe(self._topic, qos=self._qos)
            client.loop_start()

            if not received.wait(self._timeout_seconds):
                raise TimeoutError(
                    f"no MQTT message received within {self._timeout_seconds:g} seconds"
                )

            return payload[0]
        except OSError as exc:
            raise HardwareUnavailableError(
                "unable to connect MQTT one-shot subscriber"
            ) from exc
        finally:
            client.loop_stop()
            client.disconnect()
