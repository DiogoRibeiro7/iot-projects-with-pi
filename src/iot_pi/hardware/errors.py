"""Hardware-specific exception hierarchy."""


class HardwareError(RuntimeError):
    """Base exception for hardware access failures."""


class HardwareUnavailableError(HardwareError):
    """Raised when a requested hardware backend is unavailable."""
