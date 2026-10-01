"""Messaging interfaces used by application services."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MessagePublisher(Protocol):
    """Minimal publisher contract used by domain services."""

    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        """Publish one serialized message."""
