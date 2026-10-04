# Home Automation

## Purpose

Demonstrate a Raspberry Pi automation controller that combines environmental
sensing, occupancy input, rule-based decisions, and a relay actuator while
keeping business rules independent from GPIO libraries.

## Architecture

```text
DHT sensor ----\
                -> HomeAutomationController -> automation policy -> relay
PIR/motion ----/                               |
                                                -> logs/events/health
```

Hardware access is provided through shared `iot_pi.hardware` interfaces.
Automation decisions live in pure application code and can be tested without
GPIO.

## Bill of materials

| Component | Quantity | Notes |
| --- | ---: | --- |
| Raspberry Pi | 1 | GPIO-capable model |
| DHT11 or DHT22 | 1 | Temperature/humidity |
| PIR motion sensor | 1 | Digital occupancy input |
| Relay module | 1 | Must match logic and load requirements |
| Jumper wires | As needed | Low-voltage GPIO wiring |

## Supported Raspberry Pi models

The project is designed around GPIOZero and CircuitPython-compatible Raspberry
Pi GPIO access. Record physical validation for specific Pi and relay combinations
before marking them tested.

## Wiring and pin mapping

Default CLI example:

| Component | Default | Numbering |
| --- | --- | --- |
| DHT data | D4 | CircuitPython board name |
| Motion input | GPIO17 | BCM |
| Relay output | GPIO27 | BCM |

Actual wiring depends on the sensor and relay board. Verify voltage levels and
active-high/active-low behavior before connecting an actuator.

## Software dependencies

- Python 3.12
- Poetry
- `dht` extra for DHT sensor support
- `hardware` extra for GPIOZero relay and digital input support

## Installation

Simulation:

```bash
poetry install
```

Raspberry Pi hardware:

```bash
poetry install -E dht -E hardware
```

## Configuration

Key CLI options:

| Option | Purpose | Default |
| --- | --- | --- |
| `--motion-pin` | BCM motion input | 17 |
| `--relay-pin` | BCM relay output | 27 |
| `--dht-pin` | DHT board pin | D4 |
| `--dht-model` | DHT11 or DHT22 | DHT22 |
| `--temperature-on` | Relay-on threshold | 28 |
| `--temperature-off` | Relay-off threshold | 26 |
| `--override` | auto/on/off | auto |
| `--continuous` | Repeated evaluation mode | disabled |
| `--interval` | Continuous-cycle delay | 5 seconds |

The off threshold must be lower than the on threshold.

For managed deployment, use the environment and systemd examples in
[../../docs/deployment.md](../../docs/deployment.md).

## Execution

Simulation:

```bash
poetry run iot-home --simulation
```

Continuous simulation:

```bash
poetry run iot-home --simulation --continuous --interval 5
```

Physical hardware:

```bash
poetry run iot-home \
  --dht-model DHT22 \
  --dht-pin D4 \
  --motion-pin 17 \
  --relay-pin 27 \
  --continuous
```

## Expected telemetry or output

Each evaluation produces a structured automation-decision log containing
temperature, humidity, occupancy, relay state, override mode, and decision
reason.

Typical reasons include:

- `temperature_high`
- `temperature_recovered`
- `hysteresis_hold`
- `no_motion`
- `manual_override_on`
- `manual_override_off`

## Testing without hardware

Fake digital inputs/outputs and the simulated climate sensor allow the controller
and rules to run without a Raspberry Pi.

```bash
poetry run pytest tests/home
```

## Troubleshooting

- **GPIO backend unavailable:** install the `hardware` extra on the Pi.
- **DHT backend unavailable:** install the `dht` extra.
- **Relay behaves inversely:** verify relay active-high/active-low behavior.
- **No automation response:** verify motion state and temperature thresholds.
- **Continuous mode exits:** ensure `--interval` is positive and finite.
- **Permission denied:** verify GPIO device-group membership.

## Safety

The controller writes the relay to **off** during startup and shutdown. Managed
systemd deployment sends SIGINT so the CLI cleanup path can explicitly
de-energize the relay.

Do not connect mains-voltage loads unless the relay, enclosure, wiring,
protection, and installation are appropriate and performed by someone qualified
for that electrical work.

## Limitations and next steps

- the reference policy is intentionally simple and rule-based;
- manual override is process-local rather than persistent;
- MQTT command helpers exist, but the CLI does not yet subscribe to commands;
- physical relay fail-safe behavior also depends on the selected relay board.
