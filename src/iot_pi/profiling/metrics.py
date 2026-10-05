"""Lightweight runtime profiling using only the Python standard library."""

from __future__ import annotations

import ctypes
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from iot_pi.weather.sensors import SimulatedTemperatureHumiditySensor


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Summary metrics for one benchmark run."""

    samples: int
    elapsed_seconds: float
    cpu_seconds: float
    samples_per_second: float
    rss_bytes: int | None
    platform: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable mapping."""
        return asdict(self)


def _linux_rss_bytes() -> int | None:
    """Read current RSS from Linux procfs when available."""
    status = Path("/proc/self/status")
    if not status.exists():
        return None

    for line in status.read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            if len(parts) >= 2:
                return int(parts[1]) * 1024

    return None


def _windows_rss_bytes() -> int | None:
    """Read the current working set size on Windows."""
    if os.name != "nt":
        return None

    class ProcessMemoryCounters(ctypes.Structure):
        """Subset of PROCESS_MEMORY_COUNTERS required for working-set size."""

        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(ProcessMemoryCounters)

    get_current_process = kernel32.GetCurrentProcess
    get_current_process.restype = ctypes.c_void_p

    get_process_memory_info = psapi.GetProcessMemoryInfo
    get_process_memory_info.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ProcessMemoryCounters),
        ctypes.c_ulong,
    ]
    get_process_memory_info.restype = ctypes.c_int

    process = get_current_process()
    ok = get_process_memory_info(
        process,
        ctypes.byref(counters),
        counters.cb,
    )
    if not ok:
        return None

    return int(counters.WorkingSetSize)


def current_rss_bytes() -> int | None:
    """Return current resident memory where the platform exposes it."""
    if sys.platform.startswith("linux"):
        return _linux_rss_bytes()
    if os.name == "nt":
        return _windows_rss_bytes()
    return None


def benchmark_weather_simulation(samples: int) -> BenchmarkResult:
    """Benchmark deterministic weather sampling without hardware or persistence."""
    if samples <= 0:
        raise ValueError("samples must be greater than zero")

    sensor = SimulatedTemperatureHumiditySensor(seed=42)

    wall_start = time.perf_counter()
    cpu_start = time.process_time()

    sensor.open()
    try:
        for _ in range(samples):
            sensor.read()
    finally:
        sensor.close()

    cpu_seconds = time.process_time() - cpu_start
    elapsed_seconds = time.perf_counter() - wall_start

    return BenchmarkResult(
        samples=samples,
        elapsed_seconds=elapsed_seconds,
        cpu_seconds=cpu_seconds,
        samples_per_second=samples / elapsed_seconds,
        rss_bytes=current_rss_bytes(),
        platform=sys.platform,
    )
