"""Tests for safe remote command validation and replay protection."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from iot_pi.messaging.remote_commands import (
    RemoteCommand,
    SQLiteCommandReplayStore,
    accept_remote_command,
    validate_remote_command,
)


def _command(
    *,
    command_id: str = "cmd-001",
    device_id: str = "home-pi-01",
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> RemoteCommand:
    """Create one deterministic remote command."""
    issued = issued_at or datetime(2026, 10, 7, 9, 0, tzinfo=UTC)
    expires = expires_at or issued + timedelta(minutes=5)
    return RemoteCommand(
        command_id=command_id,
        device_id=device_id,
        issued_at=issued,
        expires_at=expires,
        action="off",
    )


def test_remote_command_rejects_expired_command(tmp_path: Path) -> None:
    """Expired commands must be rejected before execution."""
    store = SQLiteCommandReplayStore(tmp_path / "commands.db")
    store.open()
    try:
        command = _command(
            expires_at=datetime(2026, 10, 7, 9, 1, tzinfo=UTC),
        )
        with pytest.raises(ValueError, match="expired"):
            validate_remote_command(
                command,
                device_id="home-pi-01",
                replay_store=store,
                now=datetime(2026, 10, 7, 9, 2, tzinfo=UTC),
            )
    finally:
        store.close()


def test_remote_command_rejects_wrong_device(tmp_path: Path) -> None:
    """Commands addressed to another device must be rejected."""
    store = SQLiteCommandReplayStore(tmp_path / "commands.db")
    store.open()
    try:
        with pytest.raises(ValueError, match="another device"):
            validate_remote_command(
                _command(device_id="home-pi-02"),
                device_id="home-pi-01",
                replay_store=store,
                now=datetime(2026, 10, 7, 9, 1, tzinfo=UTC),
            )
    finally:
        store.close()


def test_remote_command_rejects_future_issued_command(tmp_path: Path) -> None:
    """A command claiming to be issued in the future must not be accepted."""
    store = SQLiteCommandReplayStore(tmp_path / "commands.db")
    store.open()
    try:
        with pytest.raises(ValueError, match="future"):
            validate_remote_command(
                _command(
                    issued_at=datetime(2026, 10, 7, 9, 5, tzinfo=UTC),
                    expires_at=datetime(2026, 10, 7, 9, 10, tzinfo=UTC),
                ),
                device_id="home-pi-01",
                replay_store=store,
                now=datetime(2026, 10, 7, 9, 1, tzinfo=UTC),
            )
    finally:
        store.close()


def test_accept_remote_command_persists_replay_across_restart(
    tmp_path: Path,
) -> None:
    """Accepted command IDs must remain rejected after reopening the store."""
    path = tmp_path / "commands.db"
    command = _command()
    now = datetime(2026, 10, 7, 9, 1, tzinfo=UTC)

    store = SQLiteCommandReplayStore(path)
    store.open()
    try:
        accepted = accept_remote_command(
            command,
            device_id="home-pi-01",
            replay_store=store,
            now=now,
        )
        assert accepted.command_id == "cmd-001"
    finally:
        store.close()

    reopened = SQLiteCommandReplayStore(path)
    reopened.open()
    try:
        with pytest.raises(ValueError, match="already been processed"):
            validate_remote_command(
                command,
                device_id="home-pi-01",
                replay_store=reopened,
                now=now,
            )
    finally:
        reopened.close()


def test_remote_command_from_json_validates_envelope() -> None:
    """A complete JSON envelope should parse into the typed command."""
    command = RemoteCommand.from_json(
        '{"command_id":"cmd-001","device_id":"home-pi-01",'
        '"issued_at":"2026-10-07T09:00:00+00:00",'
        '"expires_at":"2026-10-07T09:05:00+00:00","action":"off"}'
    )

    assert command.command_id == "cmd-001"
    assert command.action == "off"


@pytest.mark.parametrize(
    "payload",
    [
        "[]",
        '{"command_id":"","device_id":"home-pi-01","issued_at":"2026-10-07T09:00:00+00:00","expires_at":"2026-10-07T09:05:00+00:00","action":"off"}',
        '{"command_id":"cmd-001","device_id":"home-pi-01","issued_at":"2026-10-07T09:05:00+00:00","expires_at":"2026-10-07T09:00:00+00:00","action":"off"}',
    ],
)
def test_remote_command_rejects_invalid_payload(payload: str) -> None:
    """Malformed remote command envelopes must fail validation."""
    with pytest.raises(ValueError):
        RemoteCommand.from_json(payload)


def test_replay_store_requires_open_connection(tmp_path: Path) -> None:
    """Replay queries and writes should fail when the store is closed."""
    store = SQLiteCommandReplayStore(tmp_path / "commands.db")

    with pytest.raises(RuntimeError, match="not open"):
        store.contains("cmd-001")

    with pytest.raises(RuntimeError, match="not open"):
        store.record(
            "cmd-001",
            processed_at=datetime(2026, 10, 7, 9, 1, tzinfo=UTC),
        )


def test_replay_store_rejects_naive_processed_timestamp(tmp_path: Path) -> None:
    """Persisted replay timestamps must be timezone aware."""
    store = SQLiteCommandReplayStore(tmp_path / "commands.db")
    store.open()
    try:
        with pytest.raises(ValueError, match="timezone"):
            store.record(
                "cmd-001",
                processed_at=datetime(2026, 10, 7, 9, 1),
            )
    finally:
        store.close()


def test_remote_command_requires_timezone_aware_dates() -> None:
    """Command validity windows must be timezone aware."""
    with pytest.raises(ValueError, match="timezone"):
        RemoteCommand(
            command_id="cmd-001",
            device_id="home-pi-01",
            issued_at=datetime(2026, 10, 7, 9, 0),
            expires_at=datetime(2026, 10, 7, 9, 5),
            action="off",
        )


def test_validate_remote_command_rejects_naive_now(tmp_path: Path) -> None:
    """Validation reference time must include timezone information."""
    store = SQLiteCommandReplayStore(tmp_path / "commands.db")
    store.open()
    try:
        with pytest.raises(ValueError, match="timezone"):
            validate_remote_command(
                _command(),
                device_id="home-pi-01",
                replay_store=store,
                now=datetime(2026, 10, 7, 9, 1),
            )
    finally:
        store.close()
