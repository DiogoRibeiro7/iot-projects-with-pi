# MQTT messaging

The repository uses MQTT as an infrastructure boundary, not as application
business logic.

## Topics

The stable convention is:

```text
iot/<device-id>/telemetry/<stream>
iot/<device-id>/state/<component>
iot/<device-id>/command/<component>
```

Examples:

```text
iot/pi-01/telemetry/weather
iot/pi-01/state/relay
iot/pi-01/command/relay
```

## QoS

- QoS 0: expendable high-rate telemetry.
- QoS 1: default for measurements and commands.
- QoS 2: only when duplicate delivery is unacceptable and the extra overhead is
  justified.

## Retained messages

Retain durable **state** messages when a new subscriber needs the latest known
state immediately. Do not retain event streams or one-shot commands.

## Message schema

Telemetry includes `device_id`, `event`, timezone-aware `timestamp`, and a
`data` object. Commands include `device_id`, `command`, and a timezone-aware
`timestamp`.

## Installation

```bash
poetry install -E mqtt
```

The unit tests use the in-memory publisher and require no running broker.
