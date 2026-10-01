# Weather Station

A reference Raspberry Pi weather station built on the shared `iot_pi` package.

## Features

- temperature and relative-humidity acquisition;
- DHT11 and DHT22 support;
- deterministic simulation mode;
- timestamped and validated observations;
- SQLite persistence;
- structured JSON log output;
- configurable sample interval;
- command-line execution.

## Hardware

Supported initial sensor models:

- DHT11
- DHT22

The default example pin is `D4` (GPIO4). Use the corresponding board pin name
for your wiring.

### Typical DHT wiring

| DHT pin | Raspberry Pi |
| --- | --- |
| VCC | 3.3 V |
| DATA | GPIO4 / D4 |
| GND | GND |

A pull-up resistor may be required depending on the sensor breakout board.

## Installation

For simulation-only development:

```bash
poetry install
```

For Raspberry Pi DHT hardware support:

```bash
poetry install -E dht
```

## Simulation

```bash
poetry run iot-weather --simulation --samples 5 --interval 2
```

## Raspberry Pi

```bash
poetry run iot-weather --model DHT22 --pin D4 --samples 10 --interval 60
```

Observations are stored in `data/weather.db` by default.

## Example log record

```json
{"event":"weather_observation","pressure_hpa":null,"relative_humidity_percent":54.73,"temperature_c":21.28,"timestamp":"2026-10-01T10:00:00+00:00"}
```

## Troubleshooting

- **gpio/DHT library unavailable:** install the `dht` extra on the Raspberry Pi.
- **unknown board pin:** use a valid CircuitPython board pin such as `D4`.
- **intermittent DHT read failures:** DHT devices can transiently fail; each sample is retried up to three times with a two-second delay before the run stops.
- **permission errors:** verify the process has access to the required GPIO devices.

## Safety

This project only reads a low-voltage environmental sensor. Follow the sensor
manufacturer's voltage and wiring specifications.
