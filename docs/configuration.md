# Runtime configuration

The weather, home-automation, and smart-agriculture CLIs use one shared
configuration model.

## Precedence

Configuration is resolved in this order:

1. built-in typed defaults;
2. TOML configuration file;
3. environment variables;
4. explicit CLI options.

Later sources override earlier ones.

## TOML

Each CLI accepts `--config`:

```bash
poetry run iot-weather --config deployment/config/weather.toml.example
poetry run iot-home --config deployment/config/home.toml.example
poetry run iot-agriculture --config deployment/config/agriculture.toml.example
```

The example files are intended as deployment templates. Copy them to a writable
configuration location before editing them for a device.

## Environment variables

Environment keys use these prefixes:

- weather: `IOT_WEATHER_`;
- home automation: `IOT_HOME_`;
- smart agriculture: `IOT_AGRICULTURE_`.

Field names are uppercased. For example:

```bash
export IOT_WEATHER_SAMPLE_INTERVAL_SECONDS=300
export IOT_WEATHER_SIMULATION=true
```

Boolean environment values accept:

```text
true / false
1 / 0
yes / no
on / off
```

## CLI overrides

Existing command-line options remain supported. An option only overrides file or
environment configuration when it is supplied explicitly.

Example:

```bash
poetry run iot-weather \
  --config deployment/config/weather.toml.example \
  --interval 30 \
  --simulation
```

That command keeps the file's database, device ID, pin, and model while
overriding the interval and simulation mode.

Boolean flags also support explicit negation through argparse's boolean optional
form, for example `--no-simulation` or `--no-continuous`.

## Secrets

Do not store passwords, private keys, or cloud tokens in repository TOML
examples.

Use environment variables or deployment-specific secret handling for sensitive
values.

## Validation

Configuration is converted into typed dataclasses before hardware is opened.
Invalid device IDs, intervals, thresholds, ports, channel numbers, and enum-like
values fail before the application service starts.

Hardware-free normalized configuration inspection is tracked separately in the
configuration validation workstream.
