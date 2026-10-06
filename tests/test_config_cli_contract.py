"""Contract tests for hardware-free configuration inspection."""

from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "path",
    [
        Path("src/iot_pi/weather/cli.py"),
        Path("src/iot_pi/home/cli.py"),
        Path("src/iot_pi/agriculture/cli.py"),
    ],
)
def test_reference_clis_expose_check_config_before_hardware(path: Path) -> None:
    """Reference CLIs must return from config inspection before runtime setup."""
    source = path.read_text(encoding="utf-8")

    assert '"--check-config"' in source
    assert "print(format_config(config))" in source
    assert "if args.check_config:" in source

    check_position = source.index("if args.check_config:")
    logging_position = source.index("logging.basicConfig")
    assert check_position < logging_position
