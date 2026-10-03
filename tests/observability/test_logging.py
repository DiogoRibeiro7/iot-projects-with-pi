"""Tests for structured rotating logging."""

import json
import logging
from pathlib import Path

import pytest

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


@pytest.mark.parametrize(
    ("max_bytes", "backup_count"),
    [(0, 3), (1024, -1)],
)
def test_json_logger_rejects_invalid_rotation_config(
    tmp_path: Path,
    max_bytes: int,
    backup_count: int,
) -> None:
    """Rotation settings should reject invalid bounds."""
    with pytest.raises(ValueError):
        configure_json_logging(
            tmp_path / "iot.log",
            logger_name="iot_pi.invalid",
            max_bytes=max_bytes,
            backup_count=backup_count,
        )

def test_json_logger_reconfiguration_replaces_existing_handler(
    tmp_path: Path,
) -> None:
    """Reconfiguring a logger should not accumulate duplicate handlers."""
    path = tmp_path / "iot.log"
    logger = configure_json_logging(path, logger_name="iot_pi.reconfigure")
    first_handler = logger.handlers[0]

    logger = configure_json_logging(path, logger_name="iot_pi.reconfigure")

    assert len(logger.handlers) == 1
    assert logger.handlers[0] is not first_handler

def test_json_logger_serializes_exception_information(tmp_path: Path) -> None:
    """Exception logging should include a rendered traceback."""
    path = tmp_path / "iot.log"
    logger = configure_json_logging(
        path,
        logger_name="iot_pi.exception",
        level=logging.ERROR,
    )

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        logger.exception("sensor failed")

    raw = json.loads(path.read_text(encoding="utf-8").strip())

    assert raw["message"] == "sensor failed"
    assert "RuntimeError: boom" in raw["exception"]
