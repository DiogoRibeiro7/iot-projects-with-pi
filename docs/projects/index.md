# Project catalogue

The repository contains three complete reference projects plus a reusable project template.

| Project | Main concern | Hardware-free path |
| --- | --- | --- |
| [Weather station](weather-station.md) | Environmental sensing | Deterministic sensor simulator |
| [Home automation](home-automation.md) | Rules + relay actuation | Fake digital I/O + simulated climate |
| [Smart agriculture](smart-agriculture.md) | Irrigation + actuator safety | Sequence/simulated soil sensors |
| Reusable template | New project structure | Template simulator |

All projects share infrastructure from `src/iot_pi` rather than duplicating hardware, persistence, messaging, or observability logic.

For the required structure of a new project, see [Project documentation standard](../project-standard.md).
