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

For home automation, copy its environment template too:

```bash
sudo cp deployment/env/home.env.example \
  /etc/iot-projects-with-pi/home.env
sudo chmod 0640 /etc/iot-projects-with-pi/home.env
```

Edit `home.env` for the DHT sensor, motion input, relay pin, thresholds, and
evaluation interval.

## systemd

Install the weather service:

```bash
sudo cp deployment/systemd/iot-weather.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now iot-weather.service
```

Install the home-automation service:

```bash
sudo cp deployment/systemd/iot-home.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now iot-home.service
```

Inspect the weather service:

```bash
systemctl status iot-weather.service
journalctl -u iot-weather.service -f
```

Inspect the home-automation service separately:

```bash
systemctl status iot-home.service
journalctl -u iot-home.service -f
```

The units run as the dedicated `iot` account and use `NoNewPrivileges`.
The weather unit limits filesystem writes to the application data directory.
The home unit runs its controller continuously at the configured interval and
uses `SIGINT` on shutdown so the CLI cleanup path explicitly de-energizes the
relay before exiting.

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

- a Mosquitto broker bound to host loopback on port 1883;
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

A safe update flow for a device running both reference services is:

```bash
sudo systemctl stop iot-weather.service iot-home.service
cd /opt/iot-projects-with-pi
git pull --ff-only
poetry install -E dht -E hardware
sudo systemctl start iot-weather.service iot-home.service
```

If only one reference service is deployed, stop, update dependencies for, and
restart only that service.

Validate `poetry.lock` before deployment if `pyproject.toml` changed:

```bash
poetry check --lock
```

## Low-resource deployment

For Raspberry Pi Zero 2 W profiling and conservative sampling defaults, see
[pi-zero-2w.md](pi-zero-2w.md) and
`deployment/env/low-resource.env.example`.

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
- the example anonymous MQTT broker is bound to `127.0.0.1`; require
  authentication before exposing a broker to other hosts;
- avoid privileged containers for GPIO access.
