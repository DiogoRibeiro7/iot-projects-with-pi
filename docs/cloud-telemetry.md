# Optional cloud telemetry

Cloud delivery is an optional infrastructure layer. Weather and home-automation
business logic do not import AWS, Azure, or other vendor SDKs.

## Architecture

```text
application/domain telemetry
          |
          v
TelemetryMessage
          |
          v
CloudTelemetryBridge
          |
          v
CloudTelemetrySink protocol
          |
          +--> MQTT cloud sink
          +--> future AWS/Azure-specific adapters
```

The bridge owns batching and retry behavior. A sink owns vendor/network-specific
delivery.

## Batching and retries

`CloudTelemetryBridge` buffers messages until the configured batch size is
reached or `flush()` is called.

Failed batches use bounded exponential backoff. A batch remains pending when all
retry attempts fail; it is not silently discarded.

Example:

```python
from iot_pi.cloud import CloudTelemetryBridge
from iot_pi.cloud.mqtt import MqttCloudTelemetrySink
from iot_pi.messaging.weather import weather_telemetry

sink = MqttCloudTelemetrySink(
    "mqtt.example.com",
    port=8883,
    client_id="pi-01",
    topic_prefix="devices",
    tls_enabled=True,
)

bridge = CloudTelemetryBridge(
    sink,
    batch_size=10,
    max_retries=3,
    backoff_seconds=1.0,
)

bridge.open()
try:
    bridge.enqueue(weather_telemetry("pi-01", observation))
    bridge.flush()
finally:
    bridge.close()
```

## MQTT reference sink

The reference cloud sink uses the existing optional `mqtt` extra:

```bash
poetry install -E mqtt
```

It supports:

- TLS;
- CA certificate path;
- client certificate and key paths;
- username/password authentication;
- configurable QoS;
- configurable topic prefix.

No credentials are stored in source code by the repository.

## AWS IoT Core

AWS IoT Core supports MQTT over TLS. A deployment can use the reference MQTT
sink with the assigned endpoint and certificate material.

Treat these as deployment secrets/configuration:

- AWS IoT endpoint;
- device certificate;
- private key;
- CA certificate.

Do not commit certificate private keys or credentials to this repository.

If AWS-specific features such as custom authorizers, shadow APIs, or SDK-managed
credential providers are required, implement a separate
`CloudTelemetrySink` adapter behind an optional dependency.

## Azure IoT Hub

Azure IoT Hub also supports MQTT-compatible device telemetry, but its topic,
username, authentication, and token conventions are service-specific.

For simple deployments, configure an MQTT-based adapter with the required Azure
endpoint/authentication values. For richer Azure SDK behavior, implement a
separate `CloudTelemetrySink` adapter rather than importing Azure SDKs into
application services.

## Failure semantics

A cloud outage should not change local application behavior.

Recommended deployment behavior:

- keep local SQLite/logging/MQTT paths independent;
- record cloud delivery failures operationally;
- retain or persist important unsent telemetry when delivery guarantees matter;
- use bounded queues rather than unlimited in-memory growth;
- do not block safety-critical actuator logic on cloud availability.

The bridge can also use a durable SQLite outbox for at-least-once delivery across
process restarts. See [telemetry-outbox.md](telemetry-outbox.md) for restart,
acknowledgement, retry-count, and retention semantics.
