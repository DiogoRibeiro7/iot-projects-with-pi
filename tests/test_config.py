"""Tests for shared IoT application configuration."""

from pathlib import Path

import pytest

from iot_pi.config import (
    AgricultureConfig,
    AppConfig,
    HomeConfig,
    WeatherConfig,
    format_config,
    load_config,
    with_overrides,
)


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


@pytest.mark.parametrize(
    "sample_interval_seconds",
    [0.0, -1.0, float("nan"), float("inf")],
)
def test_app_config_rejects_invalid_interval(
    sample_interval_seconds: float,
) -> None:
    """Sampling intervals must be positive finite values."""
    with pytest.raises(ValueError, match="sample_interval_seconds"):
        AppConfig(
            device_id="pi-lab-01",
            sample_interval_seconds=sample_interval_seconds,
        )


def test_weather_config_precedence(tmp_path: Path) -> None:
    """CLI overrides env, env overrides TOML, and TOML overrides defaults."""
    path = tmp_path / "weather.toml"
    path.write_text(
        (
            'device_id = "toml-device"\n'
            "sample_interval_seconds = 30.0\n"
            "samples = 2\n"
            'model = "DHT11"\n'
        ),
        encoding="utf-8",
    )

    config = load_config(
        WeatherConfig,
        path=path,
        env_prefix="IOT_WEATHER_",
        environ={
            "IOT_WEATHER_DEVICE_ID": "env-device",
            "IOT_WEATHER_SAMPLE_INTERVAL_SECONDS": "15",
            "IOT_WEATHER_SIMULATION": "true",
        },
        cli_overrides={
            "device_id": "cli-device",
            "samples": 5,
        },
    )

    assert config.device_id == "cli-device"
    assert config.sample_interval_seconds == 15.0
    assert config.simulation is True
    assert config.samples == 5
    assert config.model == "DHT11"


def test_home_config_uses_defaults_without_sources() -> None:
    """No file, env, or CLI values should preserve typed defaults."""
    config = load_config(
        HomeConfig,
        env_prefix="IOT_HOME_",
        environ={},
    )

    assert config.device_id == "home-pi"
    assert config.sample_interval_seconds == 5.0
    assert config.motion_pin == 17
    assert config.override == "auto"


def test_agriculture_environment_coercion() -> None:
    """Environment values should coerce to bool, int, and float types."""
    config = load_config(
        AgricultureConfig,
        env_prefix="IOT_AGRICULTURE_",
        environ={
            "IOT_AGRICULTURE_SIMULATION": "yes",
            "IOT_AGRICULTURE_SAMPLES": "7",
            "IOT_AGRICULTURE_DRY_ON_PERCENT": "25.5",
            "IOT_AGRICULTURE_MQTT_PORT": "1884",
        },
    )

    assert config.simulation is True
    assert config.samples == 7
    assert config.dry_on_percent == 25.5
    assert config.mqtt_port == 1884


def test_invalid_environment_boolean_fails() -> None:
    """Invalid boolean strings should not be guessed."""
    with pytest.raises(ValueError, match="invalid boolean"):
        load_config(
            WeatherConfig,
            env_prefix="IOT_WEATHER_",
            environ={"IOT_WEATHER_SIMULATION": "sometimes"},
        )


def test_unknown_toml_key_fails(tmp_path: Path) -> None:
    """Configuration typos should fail instead of being silently ignored."""
    path = tmp_path / "weather.toml"
    path.write_text("unknown_key = 3\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unknown configuration keys"):
        load_config(
            WeatherConfig,
            path=path,
            env_prefix="IOT_WEATHER_",
            environ={},
        )


def test_with_overrides_ignores_none_values() -> None:
    """None should represent an unspecified CLI option."""
    original = WeatherConfig()
    updated = with_overrides(
        original,
        samples=3,
        model=None,
    )

    assert updated.samples == 3
    assert updated.model == original.model


def test_weather_outbox_requires_mqtt_host() -> None:
    """Durable telemetry cannot be enabled without a delivery endpoint."""
    with pytest.raises(ValueError, match="mqtt_host"):
        WeatherConfig(telemetry_outbox_database="data/outbox.db")


@pytest.mark.parametrize(
    ("batch_size", "max_retries", "backoff_seconds"),
    [(0, 3, 1.0), (10, 0, 1.0), (10, 3, 0.0)],
)
def test_agriculture_rejects_invalid_telemetry_retry_settings(
    batch_size: int,
    max_retries: int,
    backoff_seconds: float,
) -> None:
    """Durable telemetry retry controls must remain strictly positive."""
    with pytest.raises(ValueError):
        AgricultureConfig(
            mqtt_host="127.0.0.1",
            telemetry_outbox_database="data/outbox.db",
            telemetry_batch_size=batch_size,
            telemetry_max_retries=max_retries,
            telemetry_backoff_seconds=backoff_seconds,
        )


def test_format_config_returns_normalized_json() -> None:
    """Validated configuration should serialize deterministically for inspection."""
    rendered = format_config(WeatherConfig(device_id="weather-lab", samples=2))

    assert '"device_id": "weather-lab"' in rendered
    assert '"samples": 2' in rendered
    assert rendered.index('"device_id"') < rendered.index('"samples"')


@pytest.mark.parametrize(
    ("dry_raw", "wet_raw"),
    [(-0.1, 0.3), (0.8, 1.1), (0.5, 0.5)],
)
def test_agriculture_config_rejects_invalid_adc_calibration(
    dry_raw: float,
    wet_raw: float,
) -> None:
    """Calibration mistakes must fail before MCP3008 hardware is opened."""
    with pytest.raises(ValueError, match="dry_raw|wet_raw"):
        AgricultureConfig(dry_raw=dry_raw, wet_raw=wet_raw)
