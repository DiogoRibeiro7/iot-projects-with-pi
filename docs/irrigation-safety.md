# Irrigation actuator safety

The smart-agriculture controller uses an application-level safety guard in
addition to moisture hysteresis.

## Independent controls

The moisture policy answers whether irrigation is useful.

The safety guard separately answers whether the actuator is allowed to remain
energized.

Default limits:

- maximum continuous run: 300 seconds;
- minimum cooldown after stopping: 60 seconds.

Both are configurable through `iot-agriculture`.

## Maximum run time

If the pump remains on for the configured maximum duration, the next evaluation
forces it off with:

```text
safety_max_run_reached
```

That observation follows the same persistence, event, logging, and telemetry
paths as an ordinary irrigation decision.

## Cooldown

After a normal policy stop, maximum-run stop, or error-driven emergency stop,
the guard records the stop time.

A dry-soil request received before the cooldown expires remains off with:

```text
safety_cooldown_active
```

## Error-driven shutdown

Any exception during an irrigation evaluation triggers a best-effort relay OFF
write before the exception is re-raised.

The controller also records an operational event with:

```text
safety_error_stop
```

This includes downstream failures such as storage, event, or telemetry errors
that occur after the pump has already been energized.

## Timing model

Safety timing uses an injectable monotonic clock rather than wall-clock
timestamps. Clock changes, timezone changes, or NTP corrections therefore do
not alter runtime/cooldown measurements.

## Electrical safety boundary

Software timing limits are an additional protection layer, not a substitute for
hardware safety.

Use:

- a correctly rated relay or MOSFET driver;
- an external pump/valve power supply;
- appropriate fusing;
- flyback/transient suppression for inductive loads;
- pump dry-run or flow protection where the installation requires it.

The reference project assumes isolated low-voltage actuation. Mains-voltage
installation should be handled by a qualified person.
