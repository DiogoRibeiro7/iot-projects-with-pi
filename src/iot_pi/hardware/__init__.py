"""Hardware interfaces and adapters for Raspberry Pi IoT projects."""

from iot_pi.hardware.errors import HardwareError, HardwareUnavailableError
from iot_pi.hardware.fake import FakeDigitalInput, FakeDigitalOutput
from iot_pi.hardware.interfaces import (
    AnalogSensor,
    DigitalInput,
    DigitalOutput,
    Lifecycle,
    MotionSensor,
    Relay,
    TemperatureHumidityReading,
    TemperatureHumiditySensor,
)

__all__ = [
    "AnalogSensor",
    "DigitalInput",
    "DigitalOutput",
    "FakeDigitalInput",
    "FakeDigitalOutput",
    "HardwareError",
    "HardwareUnavailableError",
    "Lifecycle",
    "MotionSensor",
    "Relay",
    "TemperatureHumidityReading",
    "TemperatureHumiditySensor",
]
