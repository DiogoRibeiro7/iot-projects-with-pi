"""Tests for SQLite backup, restore, and integrity helpers."""

import sqlite3
from pathlib import Path

import pytest

from iot_pi.sqlite_tools import backup_database, check_integrity, restore_database


def _create_database(path: Path) -> None:
    """Create a small deterministic SQLite database."""
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE readings (id INTEGER PRIMARY KEY, value TEXT)")
        connection.executemany(
            "INSERT INTO readings(value) VALUES (?)",
            [("alpha",), ("beta",)],
        )
        connection.commit()
    finally:
        connection.close()


def _read_values(path: Path) -> list[str]:
    """Read the deterministic rows from a test database."""
    connection = sqlite3.connect(path)
    try:
        rows = connection.execute("SELECT value FROM readings ORDER BY id").fetchall()
    finally:
        connection.close()
    return [str(row[0]) for row in rows]


def test_backup_and_restore_preserve_records(tmp_path: Path) -> None:
    """A verified backup should restore the original records."""
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    restored = tmp_path / "restored.db"
    _create_database(source)

    backup_database(source, backup)
    restore_database(backup, restored)

    assert _read_values(backup) == ["alpha", "beta"]
    assert _read_values(restored) == ["alpha", "beta"]


def test_backup_refuses_existing_destination(tmp_path: Path) -> None:
    """Backup must never overwrite an existing file implicitly."""
    source = tmp_path / "source.db"
    destination = tmp_path / "existing.db"
    _create_database(source)
    destination.write_text("do not overwrite", encoding="utf-8")

    with pytest.raises(FileExistsError):
        backup_database(source, destination)

    assert destination.read_text(encoding="utf-8") == "do not overwrite"


def test_restore_refuses_existing_destination(tmp_path: Path) -> None:
    """Restore must never overwrite an existing database implicitly."""
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    destination = tmp_path / "existing.db"
    _create_database(source)
    backup_database(source, backup)
    destination.write_text("preserve me", encoding="utf-8")

    with pytest.raises(FileExistsError):
        restore_database(backup, destination)

    assert destination.read_text(encoding="utf-8") == "preserve me"


def test_integrity_check_rejects_non_database_file(tmp_path: Path) -> None:
    """Corrupt or non-SQLite input must not be accepted as a backup."""
    path = tmp_path / "not-a-database.db"
    path.write_text("not sqlite", encoding="utf-8")

    with pytest.raises((sqlite3.DatabaseError, ValueError)):
        check_integrity(path)


def test_check_integrity_accepts_valid_database(tmp_path: Path) -> None:
    """A healthy SQLite database should pass integrity validation."""
    path = tmp_path / "healthy.db"
    _create_database(path)

    check_integrity(path)


def test_backup_rejects_missing_source(tmp_path: Path) -> None:
    """Backup should fail clearly when the source database does not exist."""
    with pytest.raises(FileNotFoundError):
        backup_database(tmp_path / "missing.db", tmp_path / "backup.db")


def test_check_integrity_rejects_missing_file(tmp_path: Path) -> None:
    """Integrity checks should fail clearly for missing database paths."""
    with pytest.raises(FileNotFoundError):
        check_integrity(tmp_path / "missing.db")


def test_backup_removes_destination_when_post_check_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed post-backup verification must not leave an invalid backup."""
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"
    _create_database(source)

    from iot_pi import sqlite_tools

    monkeypatch.setattr(
        sqlite_tools,
        "check_integrity",
        lambda path: (_ for _ in ()).throw(ValueError("forced failure")),
    )

    with pytest.raises(ValueError, match="forced failure"):
        backup_database(source, destination)

    assert not destination.exists()


def test_restore_removes_destination_when_post_check_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed post-restore verification must not leave an invalid restore."""
    backup = tmp_path / "backup.db"
    destination = tmp_path / "restored.db"
    _create_database(backup)

    from iot_pi import sqlite_tools

    calls = 0

    def fail_second_check(path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("forced failure")

    monkeypatch.setattr(sqlite_tools, "check_integrity", fail_second_check)

    with pytest.raises(ValueError, match="forced failure"):
        restore_database(backup, destination)

    assert not destination.exists()
