# Projects

This directory contains runnable Raspberry Pi IoT reference projects.

Every project should reuse components from `src/iot_pi` rather than duplicate
hardware, configuration, messaging, persistence, or observability
infrastructure.

## Reference projects

| Project | Purpose |
| --- | --- |
| [Weather station](weather_station/README.md) | Environmental sensing, validation, SQLite persistence, and simulation |
| [Home automation](home_automation/README.md) | Occupancy-aware rules, relay control, override behavior, and safe shutdown |

## New projects

Start from [`_template/`](_template/README.md).

The repository-wide documentation requirements are defined in
[`docs/project-standard.md`](../docs/project-standard.md).

A new project should include:

- a complete README following the standard;
- configuration example;
- application entry point;
- tests that run without physical hardware;
- project-specific hardware placeholders only when shared abstractions are not
  appropriate;
- simulation data or deterministic fixtures.

Reusable code should be promoted into `src/iot_pi`.
