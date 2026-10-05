"""Run one real MQTT publish/subscribe round trip."""

from __future__ import annotations

import argparse
import threading
import time

from iot_pi.messaging.mqtt import PahoMqttPublisher, PahoOneShotSubscriber


def run_round_trip(
    host: str,
    *,
    port: int,
    topic: str,
    payload: str,
    timeout_seconds: float,
) -> None:
    """Publish one payload and require the repository subscriber to receive it."""
    subscriber = PahoOneShotSubscriber(
        host,
        topic,
        port=port,
        timeout_seconds=timeout_seconds,
    )

    received: list[str] = []
    failures: list[BaseException] = []

    def receive() -> None:
        try:
            received.append(subscriber.receive())
        except BaseException as exc:
            failures.append(exc)

    thread = threading.Thread(target=receive, daemon=True)
    thread.start()

    # Give the broker time to process the subscription before publishing.
    time.sleep(0.5)

    publisher = PahoMqttPublisher(
        host,
        port=port,
        client_id="iot-projects-smoke-publisher",
    )
    publisher.open()
    try:
        publisher.publish(topic, payload, qos=1)
    finally:
        publisher.close()

    thread.join(timeout_seconds + 1.0)

    if thread.is_alive():
        raise TimeoutError("MQTT smoke subscriber did not finish")
    if failures:
        raise RuntimeError("MQTT smoke subscriber failed") from failures[0]
    if received != [payload]:
        raise AssertionError(f"expected {payload!r}, received {received!r}")


def build_parser() -> argparse.ArgumentParser:
    """Build the smoke-test CLI."""
    parser = argparse.ArgumentParser(description="Run an MQTT round-trip smoke test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic", default="iot/smoke/telemetry/roundtrip")
    parser.add_argument("--payload", default='{"status":"ok"}')
    parser.add_argument("--timeout", type=float, default=5.0)
    return parser


def main() -> int:
    """Run the MQTT smoke test."""
    args = build_parser().parse_args()
    run_round_trip(
        args.host,
        port=args.port,
        topic=args.topic,
        payload=args.payload,
        timeout_seconds=args.timeout,
    )
    print("MQTT round trip succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
