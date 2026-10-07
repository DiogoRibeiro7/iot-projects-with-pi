# Safe remote commands

Remote control is treated as a separate control-plane contract rather than a
direct MQTT-to-actuator path.

## Command envelope

A remote command contains:

```json
{
  "command_id": "cmd-001",
  "device_id": "home-pi-01",
  "issued_at": "2026-10-07T09:00:00+00:00",
  "expires_at": "2026-10-07T09:05:00+00:00",
  "action": "off"
}
```

Supported actions are `auto`, `on`, and `off`.

## Validation order

Before application logic is allowed to act on a command, the control-plane gate
checks that:

1. the command is addressed to the current device;
2. `issued_at` is not in the future;
3. `expires_at` has not passed;
4. the command ID has not already been processed.

An accepted command ID is persisted to SQLite before actuator-facing code is
called. The replay store therefore survives process restart.

## Replay database

`SQLiteCommandReplayStore` stores processed command IDs and timestamps in a
small local SQLite database. The caller controls the database path so it can use
the same backup and restore workflow as the repository's other SQLite state.

## Home automation integration

The safe adapter is:

```python
apply_safe_remote_override_command(...)
```

It parses the envelope, validates it, records the command ID, and only then calls
the home controller's override API. Rejected commands do not mutate controller
state.

The existing local `CommandMessage` path remains available for backward
compatibility. New remote-control integrations should use the safe remote
command path.

## Transport security

Replay protection and expiry validation do not authenticate the sender or
encrypt transport. Production MQTT or other transports still need appropriate
TLS, broker authentication, authorization, and secret management.
