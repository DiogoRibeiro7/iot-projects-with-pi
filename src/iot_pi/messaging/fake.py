"""In-memory messaging adapters for tests."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PublishedMessage:
    """Captured published message."""

    topic: str
    payload: str
    qos: int
    retain: bool


@dataclass(slots=True)
class InMemoryPublisher:
    """Capture published messages without a broker."""

    messages: list[PublishedMessage] = field(default_factory=list)

    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        """Capture one publication."""
        self.messages.append(
            PublishedMessage(
                topic=topic,
                payload=payload,
                qos=qos,
                retain=retain,
            )
        )
