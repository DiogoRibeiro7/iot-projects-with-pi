"""Tests for shared IoT application configuration."""

import pytest

from iot_pi.config import AppConfig


def test_app_config_accepts_valid_values() -> None:
    """Valid configuration values should be preserved."""
    config = AppConfig(
        device_id="pi-lab-01",
        sample_interval_seconds=30.0,
        simulation=True,
    )

    assert config.device_id == "pi-lab-01"
    assert config.sample_interval_seconds == 30.0
    assert config.simulation is True


@pytest.mark.parametrize("device_id", ["", "   "])
def test_app_config_rejects_empty_device_id(device_id: str) -> None:
    """A device identifier must contain non-whitespace characters."""
    with pytest.raises(ValueError, match="device_id must not be empty"):
        AppConfig(device_id=device_id)


@pytest.mark.parametrize("sample_interval_seconds", [0.0, -1.0])
def test_app_config_rejects_non_positive_interval(
    sample_interval_seconds: float,
) -> None:
    """Sampling intervals must be strictly positive."""
    with pytest.raises(
        ValueError,
        match="sample_interval_seconds must be greater than zero",
    ):
        AppConfig(
            device_id="pi-lab-01",
            sample_interval_seconds=sample_interval_seconds,
        )
