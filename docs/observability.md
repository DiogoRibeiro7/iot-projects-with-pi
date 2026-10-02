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

The tracker has no HTTP, MQTT, or dashboard dependency. A later transport can
publish the resulting snapshot without changing application services.

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
