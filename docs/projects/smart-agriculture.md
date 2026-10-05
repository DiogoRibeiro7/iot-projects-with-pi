# Smart agriculture

The smart-agriculture project is the most complete actuator reference in the repository.

## What it demonstrates

- analogue soil-moisture sensing through MCP3008;
- deterministic fixture and randomized simulation modes;
- dry/wet hysteresis;
- maximum pump runtime and cooldown safety guardrails;
- SQLite persistence;
- runtime health and operational events;
- optional climate context;
- optional MQTT telemetry.

## Run in deterministic simulation

```bash
poetry run iot-agriculture --simulation --simulation-fixture projects/smart_agriculture/simulation.json --samples 6 --interval 1
```

## Physical hardware

```bash
poetry install -E hardware
poetry run iot-agriculture --adc-channel 0 --relay-pin 27 --dry-raw 0.80 --wet-raw 0.30 --max-run-seconds 300 --cooldown-seconds 60
```

Read [Irrigation safety](../irrigation-safety.md) for the actuator safety model.

For complete BOM, SPI wiring, calibration, troubleshooting, and electrical safety notes, see the [canonical project README](https://github.com/DiogoRibeiro7/iot-projects-with-pi/blob/main/projects/smart_agriculture/README.md).
