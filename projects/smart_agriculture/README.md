# Smart Agriculture

## Purpose

Demonstrate a Raspberry Pi irrigation controller that uses soil moisture to
drive a low-voltage pump or valve relay safely, while reusing the repository's
hardware, observability, persistence, messaging, and optional cloud layers.

## Architecture

```text
capacitive soil sensor
        |
        v
MCP3008 ADC or simulator
        |
        v
IrrigationController
        |
        +--> IrrigationPolicy with hysteresis
        +--> IrrigationSafetyGuard
        +--> relay / low-voltage pump
        +--> SQLite observations
        +--> health + operational events
        +--> optional MQTT telemetry
        +--> optional climate context
```

## Bill of materials

| Component | Quantity | Notes |
| --- | ---: | --- |
| Raspberry Pi | 1 | GPIO-capable model |
| Capacitive soil-moisture sensor | 1 | Analogue output |
| MCP3008 ADC | 1 | Converts analogue sensor output for the Pi |
| Relay module | 1 | Appropriately rated, isolated, low-voltage control |
| Low-voltage pump or valve | 1 | Match relay and power-supply ratings |
| External power supply | 1 | Sized for the pump/valve |
| Jumper wires | As needed | Keep logic and load wiring separated |

## Supported Raspberry Pi models

The project targets Raspberry Pi models supported by `gpiozero` and SPI.
Raspberry Pi 3, 4, 5, and Zero 2 W class devices are expected targets.

Physical hardware compatibility depends on the operating system, SPI
configuration, and selected relay/pump hardware.

## Wiring and pin mapping

The default example uses MCP3008 channel 0 and BCM GPIO27 for the relay.

### MCP3008

| MCP3008 pin/function | Raspberry Pi connection | Purpose |
| --- | --- | --- |
| VDD / VREF | 3.3 V | ADC supply/reference |
| AGND / DGND | GND | Common ground |
| CLK | SPI SCLK | ADC clock |
| DOUT | SPI MISO | ADC to Pi |
| DIN | SPI MOSI | Pi to ADC |
| CS/SHDN | SPI CE0 | Chip select |
| CH0 | Soil sensor analogue output | Moisture input |

Enable SPI on Raspberry Pi OS before using the physical path.

### Relay

| Relay input | Raspberry Pi connection | Default |
| --- | --- | --- |
| Signal | BCM GPIO27 | Configurable with `--relay-pin` |
| Logic power | Per module specification | Usually 3.3 V/5 V logic |
| Ground | GND | Common logic ground |

Do not power a pump directly from a Raspberry Pi GPIO pin.

## Software dependencies

Simulation requires only the core project dependencies.

Physical soil-moisture and relay control use the `hardware` extra:

```bash
poetry install -E hardware
```

Optional DHT climate context additionally uses:

```bash
poetry install -E hardware -E dht
```

Optional MQTT telemetry uses:

```bash
poetry install -E hardware -E mqtt
```

## Installation

Simulation:

```bash
poetry install
```

Physical hardware:

```bash
poetry install -E hardware
```

## Configuration

Important CLI options:

| Option | Meaning | Default |
| --- | --- | --- |
| `--dry-on` | Moisture % at/below which irrigation starts | `30` |
| `--wet-off` | Moisture % at/above which irrigation stops | `45` |
| `--max-run-seconds` | Maximum continuous pump-on duration | `300` |
| `--cooldown-seconds` | Minimum off time before restart | `60` |
| `--relay-pin` | BCM GPIO controlling the relay | `27` |
| `--adc-channel` | MCP3008 channel | `0` |
| `--dry-raw` | ADC value measured in dry calibration | `0.8` |
| `--wet-raw` | ADC value measured in wet calibration | `0.3` |
| `--database` | SQLite observation database | `data/agriculture.db` |
| `--samples` | Number of evaluations | `1` |
| `--interval` | Seconds between evaluations | `60` |
| `--climate` | Add temperature/humidity context | disabled |
| `--mqtt-host` | Publish telemetry to an MQTT broker | unset |
| `--device-id` | Telemetry device identifier | `agriculture-pi` |

The dry threshold must remain below the wet threshold. This hysteresis prevents
rapid relay switching around one moisture boundary.

The actuator safety guard independently limits continuous runtime and enforces a
minimum cooldown before the pump can restart. These limits apply even when soil
remains dry.

### Soil sensor calibration

Record the normalized MCP3008 value with the sensor in representative dry soil
and representative wet soil. Use those readings for `--dry-raw` and
`--wet-raw`.

The adapter maps that calibrated range to 0–100% and clips out-of-range values.

## Execution

### Deterministic simulation

```bash
poetry run iot-agriculture \
  --simulation \
  --simulation-fixture projects/smart_agriculture/simulation.json \
  --samples 6 \
  --interval 1
```

### Randomized simulation

```bash
poetry run iot-agriculture --simulation --samples 5
```

### Raspberry Pi hardware

```bash
poetry run iot-agriculture \
  --adc-channel 0 \
  --relay-pin 27 \
  --dry-raw 0.80 \
  --wet-raw 0.30 \
  --max-run-seconds 300 \
  --cooldown-seconds 60 \
  --samples 1000 \
  --interval 60
```

### Optional climate context

```bash
poetry run iot-agriculture \
  --simulation \
  --climate \
  --samples 5
```

### Optional MQTT telemetry

```bash
poetry run iot-agriculture \
  --simulation \
  --mqtt-host 127.0.0.1 \
  --device-id greenhouse-01
```

Telemetry uses:

```text
iot/<device-id>/telemetry/agriculture
```

## Expected telemetry or output

A persisted/logged irrigation observation contains:

- timestamp;
- calibrated soil-moisture percentage;
- pump state;
- irrigation decision reason;
- optional temperature;
- optional relative humidity.

MQTT payloads use the shared typed `TelemetryMessage` schema.

## Testing without hardware

Run the focused agriculture suite without the repository-wide coverage gate:

```bash
poetry run pytest --no-cov tests/agriculture
```

The tests use deterministic sequence sensors, fake relays, in-memory MQTT
publishers, temporary SQLite databases, and simulated climate sensors.

The full CI suite still enforces the repository's 90% core coverage threshold.

## Troubleshooting

- **MCP3008 cannot initialize:** enable SPI and install the `hardware` extra.
- **Moisture moves in the wrong direction:** verify dry/wet calibration values.
- **Pump chatters:** increase the separation between dry-on and wet-off values.
- **Relay does not switch:** verify BCM numbering, active-high behavior, and relay wiring.
- **Pump remains off:** verify calibrated moisture is at or below the dry threshold.
- **MQTT publish fails:** verify broker address, network access, and optional MQTT installation.
- **DHT unavailable:** install the `dht` extra and verify its board pin.

## Safety

The default design assumes an isolated **low-voltage** pump or valve circuit.

The controller forces the relay off during startup and shutdown. It also rolls
back already-opened resources when initialization fails.

By default, the pump may run continuously for at most **300 seconds**, followed
by at least **60 seconds** off before it may restart. A maximum-run stop is
persisted/logged with reason `safety_max_run_reached`; a blocked restart uses
`safety_cooldown_active`.

If an evaluation fails after or during actuation, the controller immediately
attempts to de-energize the relay, records `safety_error_stop` as an
operational event, and starts the cooldown interval.

Do not:

- drive a pump directly from a GPIO pin;
- route pump current through Raspberry Pi power rails;
- use mains-voltage loads as a casual breadboard experiment;
- omit flyback/protection appropriate to the selected inductive load and driver.

Use an appropriately rated relay or MOSFET driver, external power supply, fuse,
and enclosure. Mains-voltage installation should be performed by a qualified
person.

## Limitations and next steps

- physical MCP3008 calibration is installation-specific;
- durable offline MQTT/cloud spooling is available through the repository cloud
  outbox and can be enabled through shared runtime configuration;
- the safety guard limits continuous runtime but does not replace electrical
  over-current, dry-run, or flow protection;
- rainfall forecasts and evapotranspiration models are outside the current scope.

## Deployment

The repository includes
[`deployment/systemd/iot-agriculture.service`](../../deployment/systemd/iot-agriculture.service)
and a typed
[`agriculture.toml.example`](../../deployment/config/agriculture.toml.example).

The native service runs as the non-root `iot` user with `gpio` and `spi`
supplementary groups, writes mutable state only under
`/var/lib/iot-projects-with-pi`, and uses `SIGINT` for safe relay shutdown.

See [../../docs/deployment.md](../../docs/deployment.md) for installation,
permissions, configuration, service inspection, and update commands.

For long-running deployments, choose an evaluation interval appropriate to soil
dynamics and the pump hardware rather than high-frequency polling.
