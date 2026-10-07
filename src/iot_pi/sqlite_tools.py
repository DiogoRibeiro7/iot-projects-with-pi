"""Safe SQLite backup, integrity-check, and restore helpers."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path


def check_integrity(path: Path) -> None:
    """Raise ValueError when SQLite integrity_check does not return ok."""
    if not path.is_file():
        raise FileNotFoundError(path)

    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
    finally:
        connection.close()

    messages = [str(row[0]) for row in rows]
    if messages != ["ok"]:
        raise ValueError("SQLite integrity check failed: " + "; ".join(messages))


def backup_database(source: Path, destination: Path) -> None:
    """Create a consistent online SQLite backup and verify the result."""
    if not source.is_file():
        raise FileNotFoundError(source)
    if destination.exists():
        raise FileExistsError(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)

    source_connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()

    try:
        check_integrity(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def restore_database(backup: Path, destination: Path) -> None:
    """Restore a verified backup into a new destination path."""
    if destination.exists():
        raise FileExistsError(destination)

    check_integrity(backup)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, destination)

    try:
        check_integrity(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
