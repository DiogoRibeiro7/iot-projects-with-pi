"""Tests for smart-agriculture project fixtures."""

import json
from pathlib import Path


def test_simulation_fixture_contains_valid_moisture_readings() -> None:
    """Fixture values should remain valid soil-moisture percentages."""
    path = Path(__file__).parents[1] / "simulation.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    readings = payload["soil_moisture_percent"]

    assert readings
    assert all(0.0 <= float(value) <= 100.0 for value in readings)
