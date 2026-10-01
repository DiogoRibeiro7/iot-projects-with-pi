"""Stable topic conventions for IoT devices."""


def telemetry_topic(device_id: str, stream: str) -> str:
    """Return the telemetry topic for one device stream."""
    return f"iot/{device_id}/telemetry/{stream}"


def state_topic(device_id: str, component: str) -> str:
    """Return the retained state topic for one component."""
    return f"iot/{device_id}/state/{component}"


def command_topic(device_id: str, component: str) -> str:
    """Return the command topic for one component."""
    return f"iot/{device_id}/command/{component}"
