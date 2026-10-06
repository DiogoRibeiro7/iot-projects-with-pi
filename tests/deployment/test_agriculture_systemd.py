"""Tests for the smart-agriculture systemd deployment profile."""

from pathlib import Path

from iot_pi.config import AgricultureConfig, load_config

ROOT = Path(__file__).parents[2]
UNIT_PATH = ROOT / "deployment/systemd/iot-agriculture.service"
CONFIG_PATH = ROOT / "deployment/config/agriculture.toml.example"


def test_agriculture_deployment_config_is_valid() -> None:
    """The committed agriculture TOML example should pass runtime validation."""
    config = load_config(
        AgricultureConfig,
        path=CONFIG_PATH,
        env_prefix="IOT_AGRICULTURE_",
        environ={},
    )

    assert config.simulation is False
    assert config.database == "/var/lib/iot-projects-with-pi/agriculture.db"
    assert config.max_run_seconds == 300.0
    assert config.cooldown_seconds == 60.0
    assert config.relay_pin == 27
    assert config.adc_channel == 0
    assert config.health_file == (
        "/var/lib/iot-projects-with-pi/agriculture-health.json"
    )


def test_agriculture_systemd_unit_preserves_safety_and_permissions() -> None:
    """The service unit should encode the expected deployment safety contract."""
    unit = UNIT_PATH.read_text(encoding="utf-8")

    assert "User=iot" in unit
    assert "Group=iot" in unit
    assert "SupplementaryGroups=gpio spi" in unit
    assert "--config /etc/iot-projects-with-pi/agriculture.toml" in unit
    assert "KillSignal=SIGINT" in unit
    assert "Restart=always" in unit
    assert "NoNewPrivileges=true" in unit
    assert "ProtectSystem=strict" in unit
    assert "ReadWritePaths=/var/lib/iot-projects-with-pi" in unit
