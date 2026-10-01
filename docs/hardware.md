# Hardware abstraction

Application code should depend on interfaces from `iot_pi.hardware.interfaces`
rather than importing GPIO libraries directly.

## Design

The hardware layer has three parts:

1. **Protocols** define what application code needs.
2. **Fake adapters** provide deterministic implementations for development and
   tests without Raspberry Pi hardware.
3. **Raspberry Pi adapters** wrap hardware libraries and are loaded lazily.

This design keeps `import iot_pi` safe on laptops, CI runners, and other
machines without GPIO support.

## Lifecycle

Every hardware resource follows an explicit lifecycle:

```python
device.open()
try:
    value = device.read()
finally:
    device.close()
```

Actuators must return to a safe state during `close()` whenever possible.

## GPIO adapters

The first concrete Raspberry Pi adapters use `gpiozero`:

- `GpioZeroDigitalInput` for motion switches or digital sensors;
- `GpioZeroRelay` for relay-controlled actuators.

Install the optional hardware dependency group on the Raspberry Pi before using
these adapters.
