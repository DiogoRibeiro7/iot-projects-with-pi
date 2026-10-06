# Durable telemetry outbox

The default `CloudTelemetryBridge` uses a lightweight in-memory buffer. Deployments
that need telemetry to survive network outages and process restarts can supply a
`SQLiteTelemetryOutbox`.

## Why an outbox

Without durable buffering, a message waiting in RAM disappears if:

- the process crashes;
- the Raspberry Pi reboots;
- the service is upgraded while the cloud endpoint is unavailable.

The SQLite outbox persists the typed `TelemetryMessage` envelope before delivery.

## Usage

```python
from pathlib import Path

from iot_pi.cloud import CloudTelemetryBridge, SQLiteTelemetryOutbox
from iot_pi.cloud.mqtt import MqttCloudTelemetrySink

sink = MqttCloudTelemetrySink(
    "mqtt.example.com",
    port=8883,
    tls_enabled=True,
)

outbox = SQLiteTelemetryOutbox(Path("/var/lib/iot-projects-with-pi/outbox.db"))

bridge = CloudTelemetryBridge(
    sink,
    batch_size=10,
    max_retries=3,
    backoff_seconds=1.0,
    outbox=outbox,
)
```

## Delivery semantics

The durable bridge provides **at-least-once delivery**.

After a successful sink delivery, the corresponding SQLite rows are acknowledged
and deleted in one transaction. If the process crashes after the remote service
accepts a batch but before the acknowledgement transaction commits, that batch may
be replayed after restart.

Consumers that require deduplication should use their own message identifiers or
idempotency logic at the cloud boundary.

## Retry counts

Each failed delivery attempt increments `retry_count` for the selected records.
This counter survives process restarts and can be used for diagnostics or future
dead-letter policies.

## Retention

`SQLiteTelemetryOutbox.prune_older_than()` removes old pending records explicitly.

Retention is intentionally not automatic: silently deleting undelivered telemetry
is a deployment policy decision. Operators should choose a retention window based
on:

- available storage;
- telemetry importance;
- expected outage duration;
- legal or operational retention requirements.

## Storage growth

A long cloud outage can grow the SQLite file continuously.

Recommended controls:

- monitor `pending_count`;
- expose backlog size through device health;
- configure retention where losing very old telemetry is acceptable;
- avoid storing high-rate expendable metrics in the durable outbox;
- keep the outbox database on persistent writable storage, not inside the code
  checkout.

## Restart recovery

On startup, the bridge reads the oldest pending rows first. Successful delivery
acknowledges only those record IDs, so newly enqueued rows cannot be accidentally
removed by an older batch acknowledgement.

The outbox stores transport-neutral telemetry envelopes. The same persisted rows
can therefore be replayed through any compatible `CloudTelemetrySink`, not only
MQTT.


## Runnable applications

Weather and smart agriculture can enable the durable outbox directly through
their shared runtime configuration.

Example weather configuration:

```toml
mqtt_host = "127.0.0.1"
mqtt_port = 1883
telemetry_outbox_database = "/var/lib/iot-projects-with-pi/weather-outbox.db"
telemetry_batch_size = 10
telemetry_max_retries = 3
telemetry_backoff_seconds = 1.0
telemetry_tls_enabled = false
telemetry_topic_prefix = "iot"
```

The same fields are available under the `IOT_WEATHER_` and
`IOT_AGRICULTURE_` environment prefixes and as explicit CLI options.

## Offline startup

When a durable outbox is configured, the SQLite queue opens even if the MQTT
broker is unavailable. The application can therefore continue collecting local
observations and enqueueing telemetry while offline.

Each normal runtime cycle:

1. persists the typed telemetry envelope to SQLite;
2. updates `HealthTracker.backlog_size`;
3. makes one best-effort delivery attempt;
4. leaves the row pending if the broker is still unavailable.

Network errors from that best-effort attempt are not propagated into the
weather or irrigation control flow.

## Reconnect and restart

At startup, if the broker is reachable, the runtime drains the oldest persisted
outbox rows using the configured batch/retry policy before normal acquisition.

If the process restarts while offline, pending rows remain in SQLite. A later
restart with the broker available replays and acknowledges them.

For smart agriculture, durable delivery is separate from actuator safety:
broker failure cannot trigger a pump safety stop. Local persistence failures
remain visible because the telemetry record could not be made durable.
