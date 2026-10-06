# Telemetry contracts

Telemetry published by the repository uses a versioned JSON envelope.

## Envelope

Every newly encoded telemetry message contains:

```json
{
  "schema_version": "1.0",
  "device_id": "weather-pi",
  "event": "weather_observation",
  "timestamp": "2026-10-06T12:00:00+00:00",
  "data": {}
}
```

The MQTT topic layout is unchanged. Schema versioning lives in the payload so
consumers can evaluate compatibility independently of transport routing.

Committed JSON Schema documents live under `schemas/`:

- `telemetry-envelope.schema.json`;
- `weather-observation.schema.json`;
- `irrigation-observation.schema.json`.

## Compatibility policy

Version `1.x` follows these rules:

- adding an optional field is backward compatible;
- widening an accepted numeric range is backward compatible;
- adding a new event type does not change existing event contracts;
- removing or renaming a required field is breaking;
- changing a field type is breaking;
- changing the meaning or unit of an existing field is breaking.

Breaking changes require a new major schema version.

The current implementation emits `1.0`. The decoder treats legacy envelopes
without `schema_version` as `1.0` so telemetry persisted before versioning can
still be replayed from the durable outbox.

## CI contract checks

CI verifies that the committed schemas retain the common required envelope
fields and the expected event discriminators. Application tests separately
exercise the typed builders for weather and irrigation payloads.

Schema validation tooling is intentionally kept out of Raspberry Pi runtime
dependencies.
