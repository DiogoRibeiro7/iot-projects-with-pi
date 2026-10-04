# Weather Station

## Purpose

Collect environmental observations on a Raspberry Pi using the shared
`iot_pi` abstractions, with the same application flow available in simulation
and on physical DHT hardware.

## Architecture

```text
DHT11/DHT22 or simulator
        |
        v
WeatherStation service
        |
        +--> validation
        +--> SQLite persistence
        +--> structured logging
        +--> optional telemetry integration
```

## Features

- temperature and relative-humidity acquisition;
- DHT11 and DHT22 support;
- deterministic simulation mode;
- timestamped and validated observations;
- SQLite persistence;
- structured JSON log output;
- configurable sampling interval;
- bounded DHT retry behavior;
- command-line execution.

## Bill of materials

| Component | Quantity | Notes |
| --- | ---: | --- |
| Raspberry Pi | 1 | GPIO-capable model |
| DHT11 or DHT22 | 1 | Temperature/humidity sensor |
| Jumper wires | 3+ | Depends on breakout |
| Pull-up resistor | 1 | If not included on the sensor board |

## Supported Raspberry Pi models

The software is designed for Raspberry Pi models supported by Adafruit Blinka
and CircuitPython's board pin aliases. GPIO-capable Raspberry Pi 3, 4, and 5
class devices are the intended targets.

## Wiring and pin mapping

The default example uses CircuitPython board alias `D4` (GPIO4).

| DHT pin | Raspberry Pi connection | Notes |
| --- | --- | --- |
| VCC | 3.3 V | Follow sensor voltage specification |
| DATA | GPIO4 / D4 | Configurable |
| GND | GND | Common ground |

A pull-up resistor may be required depending on the sensor breakout board.

## Software dependencies

Simulation uses the core package only.

Physical DHT support uses the Poetry `dht` extra:

- `adafruit-circuitpython-dht`;
- `adafruit-blinka`.

## Installation

Simulation:

```bash
poetry install
```

Raspberry Pi DHT hardware:

```bash
poetry install -E dht
```

## Configuration

Important CLI settings:

| Option | Meaning | Default |
| --- | --- | --- |
| `--database` | SQLite database path | `data/weather.db` |
| `--interval` | Sampling interval in seconds | `60` |
| `--samples` | Number of samples | `1` |
| `--pin` | CircuitPython board pin | `D4` |
| `--model` | `DHT11` or `DHT22` | `DHT22` |
| `--simulation` | Use simulated hardware | disabled |

## Run

### Simulation

```bash
poetry run iot-weather --simulation --samples 5 --interval 2
```

### Raspberry Pi hardware

```bash
poetry run iot-weather --model DHT22 --pin D4 --samples 10 --interval 60
```

## Telemetry and output

Observations are persisted in SQLite and logged as structured JSON.

Example:

```json
{"event":"weather_observation","pressure_hpa":null,"relative_humidity_percent":54.73,"temperature_c":21.28,"timestamp":"2026-10-01T10:00:00+00:00"}
```

The shared MQTT layer can map weather observations to:

```text
iot/<device-id>/telemetry/weather
```

## Testing without hardware

The deterministic simulator is the default hardware-free test path.

Run the weather tests with:

```bash
poetry run pytest tests/weather
```

## Troubleshooting

- **DHT library unavailable:** install the `dht` extra on the Raspberry Pi.
- **Unknown board pin:** use a valid CircuitPython alias such as `D4`.
- **Intermittent DHT failure:** each read is retried with bounded delay.
- **Permission error:** verify the process can access the required GPIO device.
- **No persisted data:** verify the database directory is writable.

## Safety

This project reads a low-voltage environmental sensor. Follow the sensor
manufacturer's voltage, wiring, and pull-up requirements.

## Deployment

See [../../docs/deployment.md](../../docs/deployment.md) for native `systemd`
and optional container deployment.
