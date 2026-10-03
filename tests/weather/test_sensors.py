"""Tests for weather-station sensor adapters."""

import pytest

from iot_pi.hardware.errors import HardwareUnavailableError
from iot_pi.weather.sensors import SimulatedTemperatureHumiditySensor


def test_simulated_sensor_is_deterministic() -> None:
    """A fixed seed should reproduce the complete generated stream."""
    first = SimulatedTemperatureHumiditySensor(seed=7)
    second = SimulatedTemperatureHumiditySensor(seed=7)

    first.open()
    second.open()
    try:
        first_readings = [first.read() for _ in range(5)]
        second_readings = [second.read() for _ in range(5)]
        assert first_readings == second_readings
    finally:
        first.close()
        second.close()


def test_simulated_sensor_seed_affects_generated_stream() -> None:
    """Different seeds should produce different simulated observations."""
    first = SimulatedTemperatureHumiditySensor(seed=7)
    second = SimulatedTemperatureHumiditySensor(seed=8)

    first.open()
    second.open()
    try:
        assert [first.read() for _ in range(3)] != [second.read() for _ in range(3)]
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize(
    ("temperature", "humidity"),
    [(-80.0, 55.0), (80.0, 55.0), (21.0, 0.0), (21.0, 100.0)],
)
def test_simulated_sensor_rejects_unsafe_baselines(
    temperature: float,
    humidity: float,
) -> None:
    """Simulator baselines must leave room for random variation."""
    with pytest.raises(ValueError):
        SimulatedTemperatureHumiditySensor(
            base_temperature_c=temperature,
            base_humidity_percent=humidity,
        )


def test_simulated_sensor_requires_open_lifecycle() -> None:
    """Reading before opening should fail consistently."""
    sensor = SimulatedTemperatureHumiditySensor()

    with pytest.raises(HardwareUnavailableError, match="not open"):
        sensor.read()


class FakeDhtDevice:
    """Small DHT device double with configurable readings."""

    def __init__(self, readings: list[object]) -> None:
        self._readings = iter(readings)
        self.exited = False

    @property
    def temperature(self) -> object:
        """Return the next configured temperature value."""
        value = next(self._readings)
        if isinstance(value, Exception):
            raise value
        return value

    @property
    def humidity(self) -> object:
        """Return the next configured humidity value."""
        value = next(self._readings)
        if isinstance(value, Exception):
            raise value
        return value

    def exit(self) -> None:
        """Record cleanup."""
        self.exited = True


def test_dht_constructor_validates_configuration() -> None:
    """DHT configuration should reject unsupported values."""
    from iot_pi.weather.sensors import DhtTemperatureHumiditySensor

    with pytest.raises(ValueError, match="model"):
        DhtTemperatureHumiditySensor("D4", model="DHT99")
    with pytest.raises(ValueError, match="retries"):
        DhtTemperatureHumiditySensor("D4", retries=0)
    with pytest.raises(ValueError, match="retry_delay_seconds"):
        DhtTemperatureHumiditySensor("D4", retry_delay_seconds=0)


def test_dht_read_retries_transient_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transient DHT errors should be retried before succeeding."""
    from iot_pi.weather.sensors import DhtTemperatureHumiditySensor

    sensor = DhtTemperatureHumiditySensor(
        "D4",
        retries=2,
        retry_delay_seconds=0.01,
    )
    device = FakeDhtDevice([RuntimeError("transient"), 21.5, 55.0])
    sensor._device = device
    sleeps: list[float] = []
    monkeypatch.setattr("iot_pi.weather.sensors.time.sleep", sleeps.append)

    reading = sensor.read()

    assert reading.temperature_c == 21.5
    assert reading.relative_humidity_percent == 55.0
    assert sleeps == [0.01]


def test_dht_read_fails_after_retry_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exhausted retries should raise the public hardware error."""
    from iot_pi.weather.sensors import DhtTemperatureHumiditySensor

    sensor = DhtTemperatureHumiditySensor(
        "D4",
        retries=2,
        retry_delay_seconds=0.01,
    )
    sensor._device = FakeDhtDevice(
        [RuntimeError("first"), RuntimeError("second")]
    )
    monkeypatch.setattr("iot_pi.weather.sensors.time.sleep", lambda _: None)

    with pytest.raises(HardwareUnavailableError, match="after 2 attempts"):
        sensor.read()


def test_dht_read_retries_missing_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing DHT values should consume retry budget too."""
    from iot_pi.weather.sensors import DhtTemperatureHumiditySensor

    sensor = DhtTemperatureHumiditySensor(
        "D4",
        retries=1,
        retry_delay_seconds=0.01,
    )
    sensor._device = FakeDhtDevice([None, None])
    monkeypatch.setattr("iot_pi.weather.sensors.time.sleep", lambda _: None)

    with pytest.raises(HardwareUnavailableError, match="after 1 attempts"):
        sensor.read()


def test_dht_read_requires_open_device() -> None:
    """A DHT read before initialization should fail."""
    from iot_pi.weather.sensors import DhtTemperatureHumiditySensor

    sensor = DhtTemperatureHumiditySensor("D4")

    with pytest.raises(HardwareUnavailableError, match="not open"):
        sensor.read()


def test_dht_close_releases_device() -> None:
    """Closing should call the underlying device exit hook."""
    from iot_pi.weather.sensors import DhtTemperatureHumiditySensor

    sensor = DhtTemperatureHumiditySensor("D4")
    device = FakeDhtDevice([])
    sensor._device = device

    sensor.close()
    sensor.close()

    assert device.exited is True
    assert sensor._device is None
