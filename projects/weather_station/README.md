# Weather Station

## Purpose

Provide a complete Raspberry Pi environmental-monitoring reference project using
the shared `iot_pi` hardware, persistence, and observability abstractions.

The project collects temperature and relative humidity, validates observations,
stores them locally, and supports deterministic simulation for development
without physical hardware.

## Architecture

```text
DHT11/DHT22 -> temperature/humidity adapter -> WeatherStation service
                                                |-> SQLite observations
                                                |-> structured logs
                                                `-> observability hooks
```

Reusable application logic lives under `src/iot_pi/weather`.

## Bill of materials

| Component | Quantity | Notes |
| --- | ---: | --- |
| Raspberry Pi | 1 | Model with GPIO support |
| DHT11 or DHT22 | 1 | Environmental sensor |
| Pull-up resistor | 1 | May already be present on breakout boards |
| Jumper wires | As needed | 3.3 V logic |

## Supported Raspberry Pi models

The project uses CircuitPython/Blika-compatible GPIO access and is expected to
work on current Raspberry Pi models supported by those libraries. Physical
validation should be recorded per device before claiming tested status.

## Wiring and pin mapping

Default example:

| DHT pin | Raspberry Pi connection | Purpose |
| --- | --- | --- |
| VCC | 3.3 V | Sensor power |
| DATA | GPIO4 / D4 | Digital sensor data |
| GND | GND | Ground |

The CLI uses CircuitPython board names such as `D4`, not physical header
numbers.

## Software dependencies

- Python 3.12
- Poetry
- `dht` optional dependency extra for physical hardware
- SQLite from the Python standard library

## Installation

Simulation-only development:

```bash
poetry install
```

Raspberry Pi hardware:

```bash
poetry install -E dht
```

## Configuration

Important CLI options:

| Option | Purpose | Default |
| --- | --- | --- |
| `--database` | SQLite database path | `data/weather.db` |
| `--interval` | Seconds between samples | `60` |
| `--samples` | Number of samples | `1` |
| `--simulation` | Use deterministic simulator | disabled |
| `--model` | DHT11 or DHT22 | DHT22 |
| `--pin` | CircuitPython board pin | D4 |

For managed Raspberry Pi deployment, see
[../../docs/deployment.md](../../docs/deployment.md).

## Execution

Simulation:

```bash
poetry run iot-weather --simulation --samples 5 --interval 2
```

Physical hardware:

```bash
poetry run iot-weather --model DHT22 --pin D4 --samples 10 --interval 60
```

## Expected telemetry or output

Observations are persisted to SQLite and emitted as structured log records.

Example:

```json
{"event":"weather_observation","pressure_hpa":null,"relative_humidity_percent":54.73,"temperature_c":21.28,"timestamp":"2026-10-01T10:00:00+00:00"}
```

The repository also provides MQTT message builders for weather telemetry.

## Testing without hardware

The deterministic simulator exercises the same `WeatherStation` application
service used by real sensors.

Run the weather tests:

```bash
poetry run pytest tests/weather
```

No Raspberry Pi hardware is required by the unit test suite.

## Troubleshooting

- **DHT library unavailable:** install the `dht` extra.
- **Unknown board pin:** use a valid CircuitPython board pin such as `D4`.
- **Intermittent reads:** DHT reads are retried up to three times by default.
- **Permission errors:** verify the process has access to the required GPIO
  devices and groups.
- **Database path failure:** ensure the target directory is writable.

## Safety

The project reads a low-voltage environmental sensor and does not control mains
power.

Follow the sensor manufacturer's voltage and wiring specifications and power
down the Pi before changing wiring.

## Limitations and next steps

- pressure is represented in the domain model but no pressure adapter is included
  yet;
- physical compatibility should be recorded explicitly for tested Pi/sensor
  combinations;
- MQTT publishing is available as shared infrastructure but is not yet wired into
  the CLI runtime.
