# Observability and local persistence

Long-running Raspberry Pi services need diagnostics that remain useful after
restarts while limiting unnecessary writes to SD cards.

## Structured logging

Use `configure_json_logging()` to create a bounded rotating JSON log.

Example:

```python
from pathlib import Path

from iot_pi.observability import configure_json_logging

logger = configure_json_logging(
    Path("data/logs/iot.log"),
    max_bytes=1_048_576,
    backup_count=3,
)
```

The default strategy keeps one active file plus three backups and avoids
unbounded local growth.

## Runtime health

`HealthTracker` records:

- process uptime;
- sensor failure count;
- last successful sample time;
- current queue/backlog size.

`HealthSnapshot` has a stable JSON schema:

```json
{
  "backlog_size": 4,
  "last_successful_sample": "2026-10-05T20:00:00+00:00",
  "sensor_failures": 1,
  "uptime_seconds": 123.4
}
```

A missing successful sample is represented as `null`.

### Persisting live health

The weather, home-automation, and smart-agriculture CLIs accept
`--health-file`. When configured, health mutations are written atomically to
that JSON file.

Example:

```bash
poetry run iot-weather \
  --simulation \
  --samples 5 \
  --health-file data/weather-health.json
```

The state file is intentionally opt-in so existing deployments do not gain a new
write path unexpectedly.

### Inspecting health locally

Print the same stable JSON schema with:

```bash
poetry run iot-health --file data/weather-health.json
```

The command reads persisted state. It does not create a second health tracker or
infer state by parsing logs.

### Publishing retained MQTT health state

Install the MQTT extra:

```bash
poetry install -E mqtt
```

Then publish the persisted snapshot:

```bash
poetry run iot-health \
  --file data/weather-health.json \
  --mqtt-host 127.0.0.1 \
  --device-id weather-pi-01
```

The command publishes the snapshot with `retain=true` to:

```text
iot/<device-id>/state/health
```

A newly connected subscriber can therefore receive the latest known health
state immediately.

MQTT publishing is deliberately separated from the service's synchronous health
tracking path. A broker outage cannot stop sensor sampling or actuator control.

## Generic event persistence

`SQLiteEventRepository` stores timestamped JSON events and supports retention
cleanup.

Example:

```python
from datetime import timedelta

repository.prune_older_than(timedelta(days=30))
```

Use retention windows that match the operational value of the data and the
storage limits of the target Raspberry Pi.
