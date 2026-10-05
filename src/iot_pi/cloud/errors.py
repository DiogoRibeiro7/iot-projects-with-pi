"""Cloud telemetry exception types."""


class CloudDeliveryError(RuntimeError):
    """Raised when a telemetry batch cannot be delivered after retries."""
