"""Safe remote command envelopes and replay protection."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

CommandAction = Literal["auto", "on", "off"]


@dataclass(frozen=True, slots=True)
class RemoteCommand:
    """Typed remote command envelope."""

    command_id: str
    device_id: str
    issued_at: datetime
    expires_at: datetime
    action: CommandAction

    def __post_init__(self) -> None:
        """Validate command envelope invariants."""
        if not self.command_id.strip():
            raise ValueError("command_id must not be empty")
        if not self.device_id.strip():
            raise ValueError("device_id must not be empty")
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("issued_at and expires_at must include a timezone")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be later than issued_at")
        if self.action not in {"auto", "on", "off"}:
            raise ValueError("action must be one of: auto, on, off")

    @classmethod
    def from_json(cls, payload: str) -> RemoteCommand:
        """Parse and validate a JSON remote command."""
        raw = json.loads(payload)
        if not isinstance(raw, dict):
            raise ValueError("remote command payload must be a JSON object")

        command_id = raw.get("command_id")
        device_id = raw.get("device_id")
        issued_at = raw.get("issued_at")
        expires_at = raw.get("expires_at")
        action = raw.get("action")

        if not isinstance(command_id, str):
            raise ValueError("command_id must be a string")
        if not isinstance(device_id, str):
            raise ValueError("device_id must be a string")
        if not isinstance(issued_at, str):
            raise ValueError("issued_at must be an ISO-8601 string")
        if not isinstance(expires_at, str):
            raise ValueError("expires_at must be an ISO-8601 string")
        if action not in {"auto", "on", "off"}:
            raise ValueError("action must be one of: auto, on, off")

        return cls(
            command_id=command_id,
            device_id=device_id,
            issued_at=datetime.fromisoformat(issued_at),
            expires_at=datetime.fromisoformat(expires_at),
            action=action,
        )


class SQLiteCommandReplayStore:
    """Persist processed command IDs to reject replays across restarts."""

    def __init__(self, path: Path) -> None:
        """Create a replay store for one SQLite database path."""
        self._path = path
        self._connection: sqlite3.Connection | None = None

    def open(self) -> None:
        """Open the replay database and initialize schema."""
        if self._connection is not None:
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._path)
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_commands (
                    command_id TEXT PRIMARY KEY,
                    processed_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
        except Exception:
            connection.close()
            raise

        self._connection = connection

    def close(self) -> None:
        """Close the replay database."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def contains(self, command_id: str) -> bool:
        """Return whether a command ID was already processed."""
        if self._connection is None:
            raise RuntimeError("command replay store is not open")

        row = self._connection.execute(
            "SELECT 1 FROM processed_commands WHERE command_id = ?",
            (command_id,),
        ).fetchone()
        return row is not None

    def record(self, command_id: str, *, processed_at: datetime) -> None:
        """Persist one processed command ID atomically."""
        if self._connection is None:
            raise RuntimeError("command replay store is not open")
        if processed_at.tzinfo is None:
            raise ValueError("processed_at must include a timezone")

        self._connection.execute(
            """
            INSERT INTO processed_commands (command_id, processed_at)
            VALUES (?, ?)
            """,
            (command_id, processed_at.astimezone(UTC).isoformat()),
        )
        self._connection.commit()


def validate_remote_command(
    command: RemoteCommand,
    *,
    device_id: str,
    replay_store: SQLiteCommandReplayStore,
    now: datetime | None = None,
) -> RemoteCommand:
    """Reject wrong-device, expired, future-issued, or replayed commands."""
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        raise ValueError("now must include a timezone")

    if command.device_id != device_id:
        raise ValueError("remote command is addressed to another device")
    if command.issued_at > reference:
        raise ValueError("remote command issued_at is in the future")
    if command.expires_at <= reference:
        raise ValueError("remote command has expired")
    if replay_store.contains(command.command_id):
        raise ValueError("remote command has already been processed")

    return command


def accept_remote_command(
    command: RemoteCommand,
    *,
    device_id: str,
    replay_store: SQLiteCommandReplayStore,
    now: datetime | None = None,
) -> RemoteCommand:
    """Validate a command and atomically mark it processed before execution."""
    reference = now or datetime.now(UTC)
    validated = validate_remote_command(
        command,
        device_id=device_id,
        replay_store=replay_store,
        now=reference,
    )
    replay_store.record(validated.command_id, processed_at=reference)
    return validated
