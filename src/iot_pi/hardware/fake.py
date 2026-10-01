"""In-memory hardware adapters for development and tests."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class FakeDigitalInput:
    """Controllable in-memory digital input."""

    state: bool = False
    is_open: bool = field(default=False, init=False)

    def open(self) -> None:
        """Mark the fake input as initialized."""
        self.is_open = True

    def close(self) -> None:
        """Mark the fake input as released."""
        self.is_open = False

    def read(self) -> bool:
        """Return the configured logical state."""
        if not self.is_open:
            raise RuntimeError("digital input is not open")
        return self.state


@dataclass(slots=True)
class FakeDigitalOutput:
    """In-memory digital output with deterministic lifecycle semantics."""

    initial_state: bool = False
    is_open: bool = field(default=False, init=False)
    _state: bool = field(default=False, init=False)

    def open(self) -> None:
        """Initialize the fake output to its configured state."""
        self._state = self.initial_state
        self.is_open = True

    def close(self) -> None:
        """Reset to a safe off state and release the fake output."""
        self._state = False
        self.is_open = False

    def write(self, state: bool) -> None:
        """Set the logical output state."""
        if not self.is_open:
            raise RuntimeError("digital output is not open")
        self._state = state

    def read(self) -> bool:
        """Return the current logical output state."""
        if not self.is_open:
            raise RuntimeError("digital output is not open")
        return self._state
