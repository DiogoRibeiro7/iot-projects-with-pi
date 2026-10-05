# IoT Projects with Raspberry Pi

A collection of reproducible IoT projects and reusable Python components for
Raspberry Pi systems.

The repository is being developed as an engineering lab rather than a set of
isolated scripts. Shared concerns such as configuration, hardware access,
messaging, persistence, and observability live in the `iot_pi` package, while
complete applications live under `projects/`.

## Repository layout

```text
iot-projects-with-pi/
├── src/iot_pi/       # Reusable typed Python components
├── projects/         # Complete reference IoT applications
├── examples/         # Focused runnable examples
├── tests/            # Hardware-independent automated tests
├── docs/             # Architecture and development documentation
└── pyproject.toml    # Poetry and quality-tool configuration
```

## Requirements

- Python 3.12
- Poetry
- Raspberry Pi hardware only when running hardware-specific adapters

The core package and automated tests are designed to work without GPIO hardware.

## Development setup

Clone the repository:

```bash
git clone https://github.com/DiogoRibeiro7/iot-projects-with-pi.git
cd iot-projects-with-pi
```

Install dependencies:

```bash
poetry install
```

Run the quality checks:

```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy src
poetry run pytest
```

Install the local pre-commit hooks:

```bash
poetry run pre-commit install
```

## Projects

The roadmap starts with two complete reference applications:

1. **Weather station** — periodic environmental measurements, validation,
   persistence, telemetry, and simulation support.
2. **Home automation** — sensor-driven rules, actuator control, manual override,
   and safe failure behaviour.

Additional projects should reuse the common package rather than duplicate
infrastructure code.

New projects should start from [projects/_template](projects/_template/README.md)
and follow the [project documentation standard](docs/project-standard.md).

## Architecture

See [docs/architecture.md](docs/architecture.md) for the repository boundaries
and design principles.

## Raspberry Pi Zero 2 W

For constrained-device profiling and low-resource settings, see
[docs/pi-zero-2w.md](docs/pi-zero-2w.md).

## Deployment

For Raspberry Pi deployment, use the native `systemd` path by default. An
optional Docker/Compose setup is also provided for simulation and controlled
container deployments.

See [docs/deployment.md](docs/deployment.md) for the complete installation,
service, container, GPIO-permission, and update procedures.

## Roadmap

Development is tracked through GitHub issues. The roadmap covers repository
foundations, hardware abstractions, reference projects, MQTT, persistence,
observability, testing, deployment, and documentation.

## Contributing

Contributions should be developed on a branch and submitted through a pull
request. New code should be typed, documented, and covered by tests where
appropriate.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
