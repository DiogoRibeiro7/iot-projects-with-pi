# Projects

This directory contains runnable Raspberry Pi IoT reference projects.

Every project should reuse components from `src/iot_pi` instead of duplicating
hardware, configuration, messaging, persistence, or observability infrastructure.

## Documentation standard

All projects must follow
[the project documentation standard](../docs/project-standard.md).

A project README should cover:

- purpose and architecture;
- bill of materials;
- supported Raspberry Pi models;
- wiring and pin mapping;
- software dependencies;
- installation and configuration;
- execution;
- telemetry/output;
- testing without hardware;
- troubleshooting;
- safety;
- limitations and next steps.

## Start a new project

Copy the reusable skeleton:

```bash
cp -R projects/_template projects/my_new_project
```

Then replace the placeholders, connect the project to shared `iot_pi`
abstractions, implement simulation first, and add tests before physical hardware
integration.

## Reference projects

- [Weather station](weather_station/README.md)
- [Home automation](home_automation/README.md)
- [Smart agriculture](smart_agriculture/README.md)
- [Reusable project template](_template/README.md)
