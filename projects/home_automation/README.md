# Home Automation

A Raspberry Pi reference project demonstrating sensors, occupancy input, and a
relay-controlled actuator behind the shared `iot_pi` abstractions.

## Behavior

The initial rule models a simple temperature-driven appliance:

- motion/occupancy must be detected;
- when temperature reaches the configured **on** threshold, the relay turns on;
- once active, it remains on until temperature falls to the lower **off**
  threshold;
- without motion, the relay is forced off;
- manual override can force the relay on or off.

The two thresholds provide hysteresis and avoid relay chatter near one boundary.

## Simulation

No Raspberry Pi hardware is required:

```bash
poetry run iot-home --simulation
```

Manual override:

```bash
poetry run iot-home --simulation --override off
```

## Raspberry Pi hardware

The initial hardware configuration uses:

- DHT11 or DHT22 for temperature/humidity;
- a digital PIR/motion input;
- a relay output.

Example:

```bash
poetry install -E hardware -E dht
poetry run iot-home \
  --dht-model DHT22 \
  --dht-pin D4 \
  --motion-pin 17 \
  --relay-pin 27
```

## Configuration

Thresholds can be changed without modifying application code:

```bash
poetry run iot-home --simulation \
  --temperature-on 27 \
  --temperature-off 25
```

The off threshold must be strictly below the on threshold.

## Safety

The controller writes the relay to **off** during startup and shutdown. If
initialization fails part-way through, already-opened resources are released.

Do not connect mains-voltage loads directly unless the relay hardware, enclosure,
wiring, and installation are appropriate for the voltage and current involved.
