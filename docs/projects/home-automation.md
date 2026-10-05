# Home automation

The home-automation project demonstrates typed input/output abstractions and stateful actuator rules without coupling domain logic to GPIO.

## What it demonstrates

- temperature/humidity input;
- motion/occupancy input;
- relay actuation;
- hysteresis;
- manual `auto`, `on`, and `off` overrides;
- deterministic simulation;
- structured operational events;
- health tracking;
- safe startup and shutdown.

## Run in simulation

```bash
poetry run iot-home --simulation --continuous --interval 5
```

## Physical hardware

```bash
poetry install -E dht -E hardware
poetry run iot-home --dht-pin D4 --motion-pin 17 --relay-pin 27 --continuous
```

For complete wiring, configuration, and safety guidance, see the [canonical project README](https://github.com/DiogoRibeiro7/iot-projects-with-pi/blob/main/projects/home_automation/README.md).
