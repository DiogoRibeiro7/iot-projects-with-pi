# SQLite backup and restore

The repository provides a small maintenance CLI for local SQLite state used by
weather observations, agriculture observations, telemetry outboxes, and event
storage.

## Integrity check

Run SQLite's built-in integrity check without opening any application service:

```bash
poetry run iot-sqlite check data/weather.db
```

The command exits successfully only when SQLite reports `ok`.

## Backup

Create a consistent online backup:

```bash
poetry run iot-sqlite backup \
  data/weather.db \
  backups/weather-2026-10-07.db
```

The implementation uses SQLite's backup API rather than a raw file copy, then
runs an integrity check on the generated backup.

Existing destination files are never overwritten implicitly.

## Restore

Restore a verified backup into a new destination:

```bash
poetry run iot-sqlite restore \
  backups/weather-2026-10-07.db \
  data/weather-restored.db
```

The backup is integrity-checked before the copy and the restored destination is
checked again afterwards.

Restore refuses an existing destination. If replacing a live database is
required, stop the corresponding service first, move the existing database out
of the way explicitly, then restore into the intended path.

## Service considerations

SQLite's online backup API allows a consistent backup while a database may be in
use, but operationally it is still preferable to avoid maintenance during high
write activity.

Restore should be treated as an offline maintenance operation. Stop the weather,
home, or agriculture service before replacing a live database path.

The CLI is storage-agnostic, so the same commands work for:

- weather databases;
- agriculture databases;
- telemetry outbox databases;
- structured event databases.
