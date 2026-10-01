# Architecture

The repository separates reusable infrastructure from runnable IoT projects.

## Layers

- `src/iot_pi`: reusable configuration, hardware abstractions, messaging,
  storage, and observability components.
- `projects`: complete reference applications.
- `examples`: focused demonstrations of individual capabilities.
- `tests`: hardware-independent automated tests.

Hardware-specific libraries must not be imported from the package root. This
keeps the core importable on development machines and CI runners without GPIO
hardware.

Application code should depend on typed interfaces. Raspberry Pi adapters and
simulation adapters will implement those interfaces in later roadmap work.
