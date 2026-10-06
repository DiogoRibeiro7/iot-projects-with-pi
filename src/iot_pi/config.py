"""Typed configuration loading shared by runnable IoT applications."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from math import isfinite
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Common device/runtime configuration."""

    device_id: str
    sample_interval_seconds: float = 60.0
    simulation: bool = False

    def __post_init__(self) -> None:
        """Validate common configuration invariants."""
        if not self.device_id.strip():
            raise ValueError("device_id must not be empty")
        if (
            not isfinite(self.sample_interval_seconds)
            or self.sample_interval_seconds <= 0
        ):
            raise ValueError("sample_interval_seconds must be a positive finite number")


@dataclass(frozen=True, slots=True)
class WeatherConfig:
    """Weather-station runtime configuration."""

    device_id: str = "weather-pi"
    sample_interval_seconds: float = 60.0
    simulation: bool = False
    database: str = "data/weather.db"
    samples: int = 1
    pin: str = "D4"
    model: str = "DHT22"
    health_file: str | None = None
    mqtt_host: str | None = None
    mqtt_port: int = 1883
    telemetry_outbox_database: str | None = None
    telemetry_batch_size: int = 10
    telemetry_max_retries: int = 3
    telemetry_backoff_seconds: float = 1.0
    telemetry_tls_enabled: bool = False
    telemetry_topic_prefix: str = "iot"

    def __post_init__(self) -> None:
        """Validate weather configuration."""
        AppConfig(
            device_id=self.device_id,
            sample_interval_seconds=self.sample_interval_seconds,
            simulation=self.simulation,
        )
        if self.samples <= 0:
            raise ValueError("samples must be greater than zero")
        if self.model not in {"DHT11", "DHT22"}:
            raise ValueError("model must be DHT11 or DHT22")
        if not self.database.strip():
            raise ValueError("database must not be empty")
        if not self.pin.strip():
            raise ValueError("pin must not be empty")
        _validate_telemetry_settings(
            mqtt_host=self.mqtt_host,
            mqtt_port=self.mqtt_port,
            outbox_database=self.telemetry_outbox_database,
            batch_size=self.telemetry_batch_size,
            max_retries=self.telemetry_max_retries,
            backoff_seconds=self.telemetry_backoff_seconds,
            topic_prefix=self.telemetry_topic_prefix,
        )


@dataclass(frozen=True, slots=True)
class HomeConfig:
    """Home-automation runtime configuration."""

    device_id: str = "home-pi"
    sample_interval_seconds: float = 5.0
    simulation: bool = False
    motion_pin: int = 17
    relay_pin: int = 27
    dht_pin: str = "D4"
    dht_model: str = "DHT22"
    temperature_on_c: float = 28.0
    temperature_off_c: float = 26.0
    override: str = "auto"
    continuous: bool = False
    health_file: str | None = None

    def __post_init__(self) -> None:
        """Validate home-automation configuration."""
        AppConfig(
            device_id=self.device_id,
            sample_interval_seconds=self.sample_interval_seconds,
            simulation=self.simulation,
        )
        if self.dht_model not in {"DHT11", "DHT22"}:
            raise ValueError("dht_model must be DHT11 or DHT22")
        if self.temperature_off_c >= self.temperature_on_c:
            raise ValueError("temperature_off_c must be lower than temperature_on_c")
        if self.override not in {"auto", "on", "off"}:
            raise ValueError("override must be auto, on, or off")


@dataclass(frozen=True, slots=True)
class AgricultureConfig:
    """Smart-agriculture runtime configuration."""

    device_id: str = "agriculture-pi"
    sample_interval_seconds: float = 60.0
    simulation: bool = False
    database: str = "data/agriculture.db"
    events_database: str | None = None
    simulation_fixture: str | None = None
    samples: int = 1
    dry_on_percent: float = 30.0
    wet_off_percent: float = 45.0
    max_run_seconds: float = 300.0
    cooldown_seconds: float = 60.0
    relay_pin: int = 27
    adc_channel: int = 0
    dry_raw: float = 0.8
    wet_raw: float = 0.3
    climate: bool = False
    dht_pin: str = "D4"
    dht_model: str = "DHT22"
    mqtt_host: str | None = None
    mqtt_port: int = 1883
    health_file: str | None = None
    telemetry_outbox_database: str | None = None
    telemetry_batch_size: int = 10
    telemetry_max_retries: int = 3
    telemetry_backoff_seconds: float = 1.0
    telemetry_tls_enabled: bool = False
    telemetry_topic_prefix: str = "iot"

    def __post_init__(self) -> None:
        """Validate agriculture configuration."""
        AppConfig(
            device_id=self.device_id,
            sample_interval_seconds=self.sample_interval_seconds,
            simulation=self.simulation,
        )
        if self.samples <= 0:
            raise ValueError("samples must be greater than zero")
        if not 0.0 <= self.dry_on_percent < self.wet_off_percent <= 100.0:
            raise ValueError(
                "dry_on_percent must be lower than wet_off_percent within 0..100"
            )
        if not isfinite(self.max_run_seconds) or self.max_run_seconds <= 0:
            raise ValueError("max_run_seconds must be a positive finite number")
        if not isfinite(self.cooldown_seconds) or self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be a non-negative finite number")
        if self.adc_channel not in range(8):
            raise ValueError("adc_channel must be between 0 and 7")
        if self.dht_model not in {"DHT11", "DHT22"}:
            raise ValueError("dht_model must be DHT11 or DHT22")
        _validate_telemetry_settings(
            mqtt_host=self.mqtt_host,
            mqtt_port=self.mqtt_port,
            outbox_database=self.telemetry_outbox_database,
            batch_size=self.telemetry_batch_size,
            max_retries=self.telemetry_max_retries,
            backoff_seconds=self.telemetry_backoff_seconds,
            topic_prefix=self.telemetry_topic_prefix,
        )



def _validate_telemetry_settings(
    *,
    mqtt_host: str | None,
    mqtt_port: int,
    outbox_database: str | None,
    batch_size: int,
    max_retries: int,
    backoff_seconds: float,
    topic_prefix: str,
) -> None:
    """Validate shared optional durable telemetry settings."""
    if mqtt_port <= 0 or mqtt_port > 65535:
        raise ValueError("mqtt_port must be between 1 and 65535")
    if outbox_database is not None and not mqtt_host:
        raise ValueError("mqtt_host is required when telemetry outbox is enabled")
    if batch_size <= 0:
        raise ValueError("telemetry_batch_size must be greater than zero")
    if max_retries <= 0:
        raise ValueError("telemetry_max_retries must be greater than zero")
    if not isfinite(backoff_seconds) or backoff_seconds <= 0:
        raise ValueError(
            "telemetry_backoff_seconds must be a positive finite number"
        )
    if not topic_prefix.strip("/"):
        raise ValueError("telemetry_topic_prefix must not be empty")

def load_config[TConfig](
    config_type: type[TConfig],
    *,
    path: Path | None = None,
    env_prefix: str,
    cli_overrides: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> TConfig:
    """Load defaults, TOML, environment, then explicit CLI overrides."""
    default_instance: Any = config_type()
    defaults = {
        field.name: getattr(default_instance, field.name)
        for field in fields(default_instance)
    }
    file_values = _load_toml(path)
    environment = environ if environ is not None else os.environ
    env_values = _load_environment(config_type, env_prefix, environment)
    overrides = {
        key: value for key, value in (cli_overrides or {}).items() if value is not None
    }

    merged = {**defaults, **file_values, **env_values, **overrides}
    allowed = {field.name for field in fields(default_instance)}
    unknown = sorted(set(merged) - allowed)
    if unknown:
        raise ValueError(f"unknown configuration keys: {', '.join(unknown)}")

    return config_type(**merged)


def _load_toml(path: Path | None) -> dict[str, Any]:
    """Load a flat TOML mapping when a configuration path is supplied."""
    if path is None:
        return {}

    with path.open("rb") as stream:
        data = tomllib.load(stream)

    if not isinstance(data, dict):
        raise ValueError("configuration file must contain a TOML table")
    return dict(data)


def _load_environment[TConfig](
    config_type: type[TConfig],
    prefix: str,
    environ: Mapping[str, str],
) -> dict[str, Any]:
    """Load prefixed environment values using dataclass field types."""
    values: dict[str, Any] = {}
    defaults: Any = config_type()

    for field in fields(defaults):
        key = f"{prefix}{field.name}".upper()
        if key not in environ:
            continue
        current = getattr(defaults, field.name)
        values[field.name] = _coerce_environment_value(environ[key], current)

    return values


def _coerce_environment_value(raw: str, current: Any) -> Any:
    """Coerce an environment string using the default value's runtime type."""
    if isinstance(current, bool):
        normalized = raw.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError(f"invalid boolean environment value: {raw!r}")

    if isinstance(current, int) and not isinstance(current, bool):
        return int(raw)
    if isinstance(current, float):
        return float(raw)
    return raw


def with_overrides[TConfig](config: TConfig, **values: Any) -> TConfig:
    """Return a validated configuration with non-None overrides applied."""
    filtered = {key: value for key, value in values.items() if value is not None}
    return cast(TConfig, replace(cast(Any, config), **filtered))
