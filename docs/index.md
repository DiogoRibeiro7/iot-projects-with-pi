# IoT Projects with Raspberry Pi

A reusable Raspberry Pi IoT engineering lab built around typed hardware abstractions, hardware-free simulation, local persistence, messaging, observability, and deployment patterns.

The repository is designed around one rule: **business logic should not depend directly on Raspberry Pi libraries**. Hardware adapters sit behind typed interfaces so the same services can run against simulation in CI or physical devices on a Pi.

## Reference projects

- **Weather station** — environmental sensing with deterministic simulation, validation, SQLite persistence, structured logs, and optional telemetry.
- **Home automation** — climate and occupancy-driven relay control with hysteresis, override modes, and safe shutdown.
- **Smart agriculture** — soil-moisture-driven irrigation with actuator safety, persistence, observability, and optional MQTT telemetry.

See the [project catalogue](projects/index.md) for runnable examples.

## Engineering layers

```text
projects / CLIs
      |
      v
application services + domain rules
      |
      +--> hardware abstractions and simulation
      +--> SQLite persistence and observability
      +--> local MQTT and optional cloud bridge
      +--> deployment / systemd / containers
```

Start with [Architecture](architecture.md) for repository boundaries, or jump to [Deployment](deployment.md) for Raspberry Pi operation.

## Quality baseline

Every pull request validates Ruff, formatting, strict mypy, pytest with a 90% core coverage threshold, project-local tests, package build, and the documentation site build.

The runtime package does not require MkDocs. Documentation dependencies are kept in `requirements-docs.txt`.
