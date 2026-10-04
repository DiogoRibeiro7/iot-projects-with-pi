"""Tests for the reusable project skeleton."""

from projects._template.app import ProjectConfig, run
from projects._template.hardware import SimulatedProjectSensor


def test_template_application_runs_in_simulation() -> None:
    """The template entry point should be executable without hardware."""
    assert run(ProjectConfig(simulation=True)) == 0


def test_simulated_sensor_is_deterministic() -> None:
    """The project simulator should return its configured value."""
    sensor = SimulatedProjectSensor(value=2.5)

    assert sensor.read() == 2.5
