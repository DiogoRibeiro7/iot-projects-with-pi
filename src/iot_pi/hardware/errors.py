"""Hardware-specific exception hierarchy."""


class HardwareError(RuntimeError):
    """Base exception for hardware access failures."""


class HardwareUnavailableError(HardwareError):
    """Raised when a requested hardware backend is unavailable."""


class HardwareReadError(HardwareError):
    """Raised when a hardware reading cannot be obtained."""


class HardwareWriteError(HardwareError):
    """Raised when a hardware state change cannot be applied."""
