# Weather station

The weather station is the simplest end-to-end sensing reference project.

## What it demonstrates

- DHT11/DHT22 temperature and humidity acquisition;
- deterministic simulation without Raspberry Pi hardware;
- validated domain observations;
- SQLite persistence;
- structured JSON logging;
- configurable sampling;
- optional health-state persistence and telemetry.

## Run in simulation

```bash
poetry run iot-weather --simulation --samples 5 --interval 2
```

## Physical hardware

```bash
poetry install -E dht
poetry run iot-weather --model DHT22 --pin D4 --samples 10 --interval 60
```

For the complete bill of materials, wiring table, troubleshooting, and safety notes, see the [canonical project README](https://github.com/DiogoRibeiro7/iot-projects-with-pi/blob/main/projects/weather_station/README.md).
