# Fleet inventory

A fleet manifest represents multiple Raspberry Pi deployments in one
declarative file and validates every referenced application configuration
without opening hardware.

## Manifest format

The manifest uses TOML `[[devices]]` entries:

```toml
[[devices]]
device_id = "weather-pi-01"
application = "weather"
config = "config/weather.toml.example"
labels = ["site:lab", "role:weather"]
```

Supported applications are:

- `weather`;
- `home`;
- `agriculture`.

Configuration paths are resolved relative to the manifest file.

## Validation

Run:

```bash
poetry run iot-fleet deployment/fleet.toml.example
```

Validation checks:

- the manifest contains at least one device;
- device IDs are unique;
- every referenced config file exists;
- every referenced config passes the existing typed application validation;
- the config `device_id` matches the fleet inventory `device_id`;
- application names and labels are valid.

The command prints a normalized JSON inventory on success.

No GPIO, SPI, sensor, MQTT, or SQLite runtime resource is opened, so the same
validation can run on a laptop or in CI before deployment.

## Example inventory

A three-device example is committed at:

```text
deployment/fleet.toml.example
```

It references the repository weather, home-automation, and agriculture
configuration examples and demonstrates deployment labels.
