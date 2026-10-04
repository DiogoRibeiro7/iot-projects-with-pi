"""Tests for the reusable project skeleton."""

from pathlib import Path

from iot_pi.config import AppConfig
from projects._template.app import (
    load_config,
    load_simulation_readings,
    run,
)
from projects._template.hardware import SimulatedProjectSensor


def test_template_application_runs_in_simulation() -> None:
    """The template entry point should be executable without hardware."""
    config = AppConfig(
        device_id="pi-template",
        sample_interval_seconds=5.0,
        simulation=True,
    )

    assert run(config, readings=[1.0]) == 0


def test_template_configuration_is_loaded_from_toml(tmp_path: Path) -> None:
    """TOML configuration should populate the shared AppConfig."""
    path = tmp_path / "config.toml"
    path.write_text(
        'device_id = "pi-test"\nsimulation = true\nsample_interval_seconds = 2.5\n',
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.device_id == "pi-test"
    assert config.simulation is True
    assert config.sample_interval_seconds == 2.5


def test_template_simulation_fixture_is_loaded(tmp_path: Path) -> None:
    """Simulation JSON should provide deterministic readings."""
    path = tmp_path / "simulation.json"
    path.write_text('{"readings":[1.0,1.5]}', encoding="utf-8")

    assert load_simulation_readings(path) == [1.0, 1.5]


def test_simulated_sensor_is_deterministic() -> None:
    """The project simulator should return its configured value."""
    sensor = SimulatedProjectSensor(value=2.5)

    assert sensor.read() == 2.5
