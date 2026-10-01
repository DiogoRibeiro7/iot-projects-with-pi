"""Home-automation command handling helpers."""

from iot_pi.home.service import HomeAutomationController, OverrideMode
from iot_pi.messaging.models import CommandMessage


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
