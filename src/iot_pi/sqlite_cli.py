"""CLI for SQLite backup, restore, and integrity checks."""

from argparse import ArgumentParser
from pathlib import Path

from iot_pi.sqlite_tools import backup_database, check_integrity, restore_database


def build_parser() -> ArgumentParser:
    """Build the SQLite operations CLI."""
    parser = ArgumentParser(description="Manage local SQLite state safely")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="run SQLite integrity_check")
    check.add_argument("path", type=Path)

    backup = subparsers.add_parser("backup", help="create a verified SQLite backup")
    backup.add_argument("source", type=Path)
    backup.add_argument("destination", type=Path)

    restore = subparsers.add_parser("restore", help="restore into a new destination")
    restore.add_argument("backup", type=Path)
    restore.add_argument("destination", type=Path)

    return parser


def main() -> int:
    """Run one SQLite maintenance operation."""
    args = build_parser().parse_args()

    if args.command == "check":
        check_integrity(args.path)
    elif args.command == "backup":
        backup_database(args.source, args.destination)
    elif args.command == "restore":
        restore_database(args.backup, args.destination)

    return 0
