# Raspberry Pi deployment

Native deployment is the recommended mode for hardware projects. Containers are
provided as an optional path for simulation and controlled deployments where
device access is understood explicitly.

## Native installation

The examples assume Raspberry Pi OS or another Debian-family distribution.

Create a dedicated service account:

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin iot
sudo mkdir -p /opt/iot-projects-with-pi /var/lib/iot-projects-with-pi
sudo chown -R iot:iot /opt/iot-projects-with-pi /var/lib/iot-projects-with-pi
```

Clone or copy the repository into `/opt/iot-projects-with-pi`, then install
Python 3.12, Poetry, and the required project extras.

For the weather station:

```bash
cd /opt/iot-projects-with-pi
poetry config virtualenvs.in-project true
poetry install -E dht
```

For home automation:

```bash
poetry install -E dht -E hardware
```

The committed `poetry.lock` keeps the installed dependency set reproducible.

## Configuration

Copy the environment template:

```bash
sudo mkdir -p /etc/iot-projects-with-pi
sudo cp deployment/env/weather.env.example \
  /etc/iot-projects-with-pi/weather.env
sudo chmod 0640 /etc/iot-projects-with-pi/weather.env
```

Edit the file for the connected sensor and pin mapping.

## systemd

Install the service unit:

```bash
sudo cp deployment/systemd/iot-weather.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now iot-weather.service
```

Inspect the service:

```bash
systemctl status iot-weather.service
journalctl -u iot-weather.service -f
```

The unit runs as the dedicated `iot` account, uses `NoNewPrivileges`, and
limits filesystem writes to the application data directory.

### GPIO permissions

Do not run the application as root merely to access GPIO. Add the service user
to the appropriate Raspberry Pi device group for the operating system and
hardware stack in use, then verify the minimum required permissions.

## Container deployment

Build the multi-stage image:

```bash
docker build -t iot-projects-with-pi .
```

Run the default simulation:

```bash
docker run --rm iot-projects-with-pi
```

Or start the example stack:

```bash
docker compose up --build
```

The Compose file starts:

- a Mosquitto broker on port 1883;
- a simulated weather station with persistent SQLite storage.

The current weather CLI does not require MQTT to operate; the broker is included
as the local messaging service used by the repository's MQTT layer and future
runtime wiring.

## GPIO inside containers

GPIO access is host-specific. A container does not automatically gain access to
Raspberry Pi GPIO devices.

When real hardware is required:

1. identify the exact device nodes and groups used by the selected Raspberry Pi
   GPIO backend;
2. pass only those devices and group permissions to the container;
3. avoid `--privileged` unless there is no narrower option;
4. keep the application process non-root where possible.

Native `systemd` deployment remains the preferred choice when direct GPIO
access is the primary requirement.

## Updating a deployed Pi

A safe update flow is:

```bash
sudo systemctl stop iot-weather.service
cd /opt/iot-projects-with-pi
git pull --ff-only
poetry install -E dht
sudo systemctl start iot-weather.service
```

Validate `poetry.lock` before deployment if `pyproject.toml` changed:

```bash
poetry check --lock
```

## Logging and storage

Use `journalctl` for service-level logs and the repository's rotating JSON
logger for structured application logs when configured. Keep SQLite databases
and mutable runtime state under `/var/lib/iot-projects-with-pi`, not inside the
repository checkout.

## Security notes

- run services under a dedicated non-login user;
- grant only required hardware-device groups;
- avoid storing credentials in the repository;
- restrict environment-file permissions;
- do not expose an unauthenticated MQTT broker outside a trusted local network;
- avoid privileged containers for GPIO access.
