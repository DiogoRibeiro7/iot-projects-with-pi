# Home Automation

## Purpose

Demonstrate a Raspberry Pi automation controller that combines environmental
input, occupancy state, configurable rules, and a relay actuator behind the
shared `iot_pi` hardware abstractions.

## Architecture

```text
temperature/humidity ----+
                         |
motion/occupancy --------+--> HomeAutomationController --> relay
                         |
manual override ---------+
```

The automation policy is independent from GPIO libraries and can be tested
without physical hardware.

## Features

- DHT11/DHT22 climate input;
- PIR/digital occupancy input;
- relay-controlled actuator;
- temperature thresholds with hysteresis;
- optional occupancy requirement;
- manual `auto`, `on`, and `off` override modes;
- deterministic simulation;
- structured decision logs;
- continuous execution mode;
- safe relay shutdown.

## Bill of materials

| Component | Quantity | Notes |
| --- | ---: | --- |
| Raspberry Pi | 1 | GPIO-capable model |
| DHT11 or DHT22 | 1 | Climate sensor |
| PIR/digital motion sensor | 1 | Occupancy input |
| Relay module | 1 | Use an appropriately rated isolated module |
| Jumper wires | As needed | Low-voltage side only |

## Supported Raspberry Pi models

The project targets GPIO-capable Raspberry Pi models supported by `gpiozero`
and Adafruit Blinka. Raspberry Pi 3, 4, and 5 class devices are the intended
targets.

## Wiring and pin mapping

Default example:

| Component | Raspberry Pi connection | Default |
| --- | --- | --- |
| DHT data | CircuitPython `D4` | GPIO4 |
| Motion input | BCM GPIO | 17 |
| Relay output | BCM GPIO | 27 |
| Sensor/relay ground | GND | Common ground |

The DHT pin uses a CircuitPython board alias. Motion and relay values use BCM
GPIO numbering.

## Software dependencies

Physical hardware support requires both Poetry extras:

```bash
poetry install -E dht -E hardware
```

This installs the DHT/Blika and `gpiozero` backends.

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

Important CLI settings:

| Option | Meaning | Default |
| --- | --- | --- |
| `--dht-model` | `DHT11` or `DHT22` | `DHT22` |
| `--dht-pin` | CircuitPython DHT pin | `D4` |
| `--motion-pin` | BCM motion GPIO | `17` |
| `--relay-pin` | BCM relay GPIO | `27` |
| `--temperature-on` | Relay-on threshold °C | `28` |
| `--temperature-off` | Relay-off threshold °C | `26` |
| `--override` | `auto`, `on`, or `off` | `auto` |
| `--continuous` | Repeat controller evaluation | disabled |
| `--interval` | Continuous interval in seconds | `5` |

The off threshold must be strictly lower than the on threshold.

## Run

### Simulation

One cycle:

```bash
poetry run iot-home --simulation
```

Continuous simulation:

```bash
poetry run iot-home --simulation --continuous --interval 5
```

Manual override:

```bash
poetry run iot-home --simulation --override off
```

### Raspberry Pi hardware

```bash
poetry run iot-home \
  --dht-model DHT22 \
  --dht-pin D4 \
  --motion-pin 17 \
  --relay-pin 27 \
  --continuous
```

## Telemetry and output

Each controller evaluation emits structured state including:

- temperature;
- relative humidity;
- motion state;
- desired relay state;
- decision reason;
- active override mode.

Typed MQTT override commands use:

```text
iot/<device-id>/command/relay
```

## Testing without hardware

The project uses:

- `SimulatedTemperatureHumiditySensor`;
- `FakeDigitalInput`;
- `FakeDigitalOutput`.

Run:

```bash
poetry run pytest tests/home
```

## Troubleshooting

- **Relay does not change:** verify BCM pin numbering and active-high wiring.
- **DHT unavailable:** install the `dht` extra and verify the board alias.
- **Motion always active/inactive:** check PIR wiring and pull-up behavior.
- **Threshold error:** ensure the off threshold is lower than the on threshold.
- **Continuous mode exits:** use a positive finite interval.

## Safety

The controller writes the relay to **off** during startup and shutdown and
releases already-opened resources if initialization fails.

Do not switch mains voltage unless the relay module, enclosure, wiring,
clearances, fusing, and installation are appropriate for the load. Prefer
qualified electrical installation for mains-powered equipment.

## Deployment

See [../../docs/deployment.md](../../docs/deployment.md). The provided
`iot-home.service` uses continuous mode and a safe shutdown signal.
