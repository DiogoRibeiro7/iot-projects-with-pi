# Project Name

## Purpose

Describe the concrete IoT problem this project demonstrates.

## Architecture

```text
input -> hardware adapter -> application logic -> output/storage/telemetry
```

Describe which components are reused from `src/iot_pi`.

## Bill of materials

| Component | Quantity | Notes |
| --- | ---: | --- |
| Raspberry Pi | 1 | Specify model |
| Sensor/actuator | 1 | Specify part |

## Supported Raspberry Pi models

| Model | Status | Notes |
| --- | --- | --- |
| Raspberry Pi 4 | Expected | Not yet physically validated |

## Wiring and pin mapping

| Peripheral pin | Raspberry Pi pin | Purpose |
| --- | --- | --- |
| TODO | TODO | TODO |

State whether pin numbers use BCM/GPIO or physical-header numbering.

## Software dependencies

- Python 3.12
- Poetry
- Required extras: TODO
- External services: none / TODO

## Installation

Simulation:

```bash
poetry install
```

Hardware:

```bash
poetry install -E TODO
```

## Configuration

Copy the example configuration:

```bash
cp projects/_template/config.example.toml config.toml
```

The template entrypoint loads this TOML file with `tomllib`. Document every option here.

## Execution

Simulation:

```bash
python projects/_template/app.py --simulation
```

Hardware:

```bash
python projects/_template/app.py
```

## Expected telemetry or output

```json
{"event":"example","device_id":"pi-example","value":1.0}
```

## Testing without hardware

```bash
poetry run pytest --no-cov projects/_template/tests
```

The template uses simulation/fake components so tests do not require GPIO. The default simulation fixture is loaded from `simulation.json`.

## Troubleshooting

- **Hardware backend unavailable:** install the required optional dependency.
- **Invalid pin:** verify BCM versus physical pin numbering.
- **Permission denied:** check device-group membership and deployment guidance.

## Safety

Describe actuator fail-safe behavior and any electrical constraints.

## Limitations and next steps

- TODO
