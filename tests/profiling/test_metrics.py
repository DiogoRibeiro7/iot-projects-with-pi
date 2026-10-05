"""Tests for lightweight runtime profiling."""

import pytest

from iot_pi.profiling.metrics import BenchmarkResult, benchmark_weather_simulation


def test_benchmark_weather_simulation_reports_metrics() -> None:
    """A benchmark should report positive timing and throughput metrics."""
    result = benchmark_weather_simulation(100)

    assert isinstance(result, BenchmarkResult)
    assert result.samples == 100
    assert result.elapsed_seconds > 0
    assert result.cpu_seconds >= 0
    assert result.samples_per_second > 0
    assert result.rss_bytes is None or result.rss_bytes > 0
    assert result.platform


def test_benchmark_rejects_non_positive_sample_count() -> None:
    """Benchmark sample counts must be strictly positive."""
    with pytest.raises(ValueError, match="samples must be greater than zero"):
        benchmark_weather_simulation(0)


def test_benchmark_result_serializes_to_dict() -> None:
    """Benchmark metrics should be JSON-ready."""
    result = BenchmarkResult(
        samples=10,
        elapsed_seconds=1.0,
        cpu_seconds=0.5,
        samples_per_second=10.0,
        rss_bytes=1024,
        platform="test",
    )

    payload = result.to_dict()

    assert payload["samples"] == 10
    assert payload["rss_bytes"] == 1024
