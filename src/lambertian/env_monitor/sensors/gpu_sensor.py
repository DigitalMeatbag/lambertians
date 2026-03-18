"""GPU sensor — load, memory, and temperature via pynvml (NVIDIA)."""

from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)


class GpuSensor:
    """Returns gpu dict using pynvml. Targets first NVIDIA device (index 0)."""

    def collect(self) -> dict[str, Any]:
        try:
            import pynvml  # type: ignore[import-untyped]
        except ImportError:
            _log.warning("pynvml not available — gpu sensor returning empty")
            return {}

        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)

            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

            return {
                "gpu": {
                    "load_percent": float(util.gpu),
                    "memory_used_mb": mem.used // (1024 * 1024),
                    "memory_total_mb": mem.total // (1024 * 1024),
                    "temp_celsius": float(temp),
                }
            }
        except Exception as exc:
            _log.warning("GpuSensor.collect failed: %s", exc)
            return {"gpu": {"load_percent": None, "memory_used_mb": None,
                            "memory_total_mb": None, "temp_celsius": None}}
