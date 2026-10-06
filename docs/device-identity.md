# Device identity and deployment metadata

Each deployed Raspberry Pi can have a small persistent metadata file describing
the identity of the physical deployment independently of transient application
configuration.

## Metadata model

The metadata contains:

- `device_id`: stable device identity used by application configuration and telemetry;
- `hardware_class`: hardware family, for example `raspberry-pi-zero-2-w`;
- `environment`: deployment environment such as `production` or `staging`;
- `site`: physical or logical site label;
- `software_version`: deployed repository/package version;
- `deployed_at`: timezone-aware deployment timestamp.

A provisioning example is available at:

```text
deployment/config/device-metadata.toml.example
```

## Provisioning

Copy the example to a host-managed location such as:

```text
/etc/iot-projects-with-pi/device.toml
```

Then edit it during provisioning. The file should be managed by the deployment
process rather than application runtime code.

Inspect and validate it without opening any hardware:

```bash
poetry run iot-device /etc/iot-projects-with-pi/device.toml
```

The command prints normalized JSON and exits non-zero when the TOML is incomplete
or invalid.

## Runtime identity consistency

Application configuration still owns runtime settings. The reusable
`validate_device_id()` helper can assert that a runtime `device_id` matches the
persistent metadata before telemetry or health state is emitted.

This keeps deployment identity reusable by observability and messaging layers
without coupling the metadata model to GPIO, SPI, sensors, MQTT, or a specific
reference application.
