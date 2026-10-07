"""Home-automation command handling helpers."""

from datetime import datetime

from iot_pi.home.service import HomeAutomationController, OverrideMode
from iot_pi.messaging.models import CommandMessage
from iot_pi.messaging.remote_commands import (
    RemoteCommand,
    SQLiteCommandReplayStore,
    accept_remote_command,
)


def apply_override_command(
    controller: HomeAutomationController,
    payload: str,
    *,
    device_id: str,
) -> CommandMessage:
    """Parse and apply a typed home-automation override command."""
    command = CommandMessage.from_json(payload)
    if command.device_id != device_id:
        raise ValueError("command device_id does not match this controller")

    controller.set_override(OverrideMode(command.command))
    return command


def apply_safe_remote_override_command(
    controller: HomeAutomationController,
    payload: str,
    *,
    device_id: str,
    replay_store: SQLiteCommandReplayStore,
    now: datetime | None = None,
) -> RemoteCommand:
    """Validate, persist, and only then apply a remote override command."""
    command = RemoteCommand.from_json(payload)
    accepted = accept_remote_command(
        command,
        device_id=device_id,
        replay_store=replay_store,
        now=now,
    )
    controller.set_override(OverrideMode(accepted.action))
    return accepted
