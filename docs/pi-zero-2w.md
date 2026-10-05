# Raspberry Pi Zero 2 W runtime profile

The Raspberry Pi Zero 2 W is the primary constrained-device target for this
repository.

The original Pi Zero and Zero W use ARMv6 and are not guaranteed targets because
modern Python and optional dependency wheels may not be available consistently.

## Benchmark command

The repository includes a hardware-independent benchmark for the weather
simulation path:

```bash
poetry run iot-profile --samples 100000
```

The command reports JSON containing:

- `samples`;
- wall-clock elapsed seconds;
- CPU seconds;
- samples per second;
- current RSS memory in bytes when supported;
- runtime platform.

Example shape:

```json
{
  "cpu_seconds": 0.42,
  "elapsed_seconds": 0.43,
  "platform": "linux",
  "rss_bytes": 42000000,
  "samples": 100000,
  "samples_per_second": 232558.1
}
```

The exact values are machine-dependent and should be compared only under a
repeatable environment.

## Repeatable Pi Zero 2 W procedure

1. Use a 64-bit Raspberry Pi OS image where practical.
2. Disable unrelated user workloads during benchmarking.
3. Record the Python and Poetry versions.
4. Install the repository without optional extras unless the benchmark needs
   them:

   ```bash
   poetry install
   ```

5. Run the benchmark three times:

   ```bash
   poetry run iot-profile --samples 100000
   ```

6. Record median elapsed time, CPU time, throughput, and RSS.
7. Repeat after any optimization that claims a resource improvement.

## Low-resource operating profile

A conservative weather sampling interval for low-power environmental monitoring
is 300 seconds. Home-automation polling should normally remain in the 5–10
second range unless the application requires faster response.

The example file
`deployment/env/low-resource.env.example` captures these defaults.

## SQLite and SD-card pressure

The current weather store commits every observation. For slow environmental
sampling this is acceptable, but high-frequency projects should avoid turning
SQLite into a high-write-rate event stream.

For constrained deployments:

- prefer slower environmental sampling where the physical process allows it;
- keep structured logs rotating and bounded;
- avoid debug logging during normal operation;
- keep high-rate transient telemetry out of SQLite unless it has operational
  value;
- use the generic event-retention policy to prune old operational records.

## Optional dependencies

Hardware and MQTT libraries are optional and should only be installed when the
deployment requires them.

Simulation and profiling paths use the core package and do not need:

- `gpiozero`;
- Adafruit Blinka/DHT packages;
- `paho-mqtt`.

This keeps development and low-resource test environments smaller.

## What to compare

For performance work, compare:

- RSS memory;
- CPU seconds per fixed sample count;
- samples per second;
- startup time where relevant;
- write frequency for SQLite/logging workloads.

Do not optimize the business logic by bypassing the typed hardware interfaces or
removing validation solely to improve synthetic benchmark numbers.
