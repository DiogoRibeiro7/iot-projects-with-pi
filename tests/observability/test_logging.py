"""Tests for structured rotating logging."""

import json
from pathlib import Path

from iot_pi.observability.logging import configure_json_logging


def test_json_logger_writes_structured_record(tmp_path: Path) -> None:
    """Configured logging should emit parseable JSON."""
    path = tmp_path / "iot.log"
    logger = configure_json_logging(path, logger_name="iot_pi.test")

    logger.info("sensor online")

    raw = json.loads(path.read_text(encoding="utf-8").strip())

    assert raw["level"] == "INFO"
    assert raw["logger"] == "iot_pi.test"
    assert raw["message"] == "sensor online"
    assert "timestamp" in raw
