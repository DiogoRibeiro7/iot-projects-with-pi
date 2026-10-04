# Project documentation standard

Every project under `projects/` should be understandable, runnable, and testable
without requiring the reader to reverse-engineer repository internals.

## Required sections

Each project README should use the following order unless there is a strong
project-specific reason to deviate:

1. **Purpose**
2. **Architecture**
3. **Bill of materials**
4. **Supported Raspberry Pi models**
5. **Wiring and pin mapping**
6. **Software dependencies**
7. **Installation**
8. **Configuration**
9. **Execution**
10. **Expected telemetry or output**
11. **Testing without hardware**
12. **Troubleshooting**
13. **Safety**
14. **Limitations and next steps**

## Project directory structure

A new project should begin from the reusable skeleton:

```text
projects/_template/
├── README.md
├── config.example.toml
├── app.py
├── hardware.py
├── simulation.json
└── tests/
    └── test_app.py
```

The skeleton is intentionally small. Reusable infrastructure belongs in
`src/iot_pi`, not inside each project.

## Purpose

State what the project does, the problem it demonstrates, and why it exists in
the repository.

Avoid generic descriptions such as "an IoT example." Describe the concrete
sensor, actuator, data flow, or operational behavior.

## Architecture

Explain the runtime components and their responsibilities.

Prefer a short data-flow description, for example:

```text
DHT22 -> sensor adapter -> application service -> SQLite
                                      \
                                       -> MQTT telemetry
```

Identify which components come from `src/iot_pi` and which are project-specific.

## Bill of materials

List hardware explicitly.

| Component | Quantity | Notes |
| --- | ---: | --- |
| Raspberry Pi | 1 | State tested models |
| Sensor | 1 | Exact family or supported variants |

Do not imply hardware has been physically validated unless it has.

## Supported Raspberry Pi models

State known-compatible models and distinguish:

- tested;
- expected to work;
- unsupported or unverified.

## Wiring and pin mapping

Use a table containing the peripheral pin, Raspberry Pi pin, and purpose.

Pin naming must distinguish GPIO/BCM numbering from physical header numbering.

## Software dependencies

Document:

- Python version;
- Poetry extras;
- external services such as MQTT;
- system packages where applicable.

## Installation

Provide commands that can be copied directly.

Keep simulation-only installation separate from hardware installation where
hardware libraries are optional.

## Configuration

Document every user-facing option.

For projects with several settings, provide a committed
`config.example.toml`, `.env.example`, or equivalent safe template.

Never commit credentials or device secrets.

## Execution

Show at least:

- simulation mode;
- physical-hardware mode when supported.

For long-running applications, document clean shutdown behavior.

## Expected telemetry or output

Show a representative log, MQTT message, database row, or terminal output.

Examples should use synthetic values and non-sensitive identifiers.

## Testing without hardware

Every project should describe how it can be exercised on a laptop or CI runner.

Prefer fake or simulation adapters over conditional test skips.

## Troubleshooting

Include common operational failures such as:

- missing hardware libraries;
- invalid pins;
- permissions;
- sensor timeouts;
- unavailable broker;
- invalid configuration.

## Safety

Actuator projects must state their safe startup/shutdown behavior.

If relays or external power are involved, clearly distinguish low-voltage logic
testing from mains-voltage installation. Do not present mains wiring as a casual
software step.

## Limitations and next steps

Be explicit about what the project does not yet support. Link roadmap issues when
appropriate.

## Code expectations

Project code should:

- use Python 3.12;
- include type annotations;
- keep business logic independent from hardware adapters;
- reuse `iot_pi` interfaces;
- support simulation where practical;
- include tests;
- pass Ruff, mypy, and pytest.

## Creating a new project

Copy the skeleton:

```bash
cp -R projects/_template projects/my_project
```

Then:

1. rename placeholders in the README and modules;
2. define the concrete hardware contract;
3. move reusable code into `src/iot_pi`;
4. add project-specific tests;
5. document simulation and physical-hardware paths;
6. add the project to `projects/README.md`.
