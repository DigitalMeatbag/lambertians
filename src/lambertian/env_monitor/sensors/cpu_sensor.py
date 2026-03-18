"""CPU sensor — load via psutil, temperatures via WMI (Windows)."""

from __future__ import annotations

import logging
from typing import Any, Optional

_log = logging.getLogger(__name__)


class CpuSensor:
    """Returns cpu dict: load_percent_per_core, load_percent_total, temps (best-effort)."""

    def collect(self) -> dict[str, Any]:
        try:
            import psutil  # type: ignore[import-untyped]
        except ImportError:
            _log.warning("psutil not available — cpu sensor returning empty")
            return {}

        try:
            per_core: list[float] = psutil.cpu_percent(interval=None, percpu=True)  # type: ignore[assignment]
            total: float = psutil.cpu_percent(interval=None)
            temps = self._read_temps()
            return {
                "cpu": {
                    "load_percent_per_core": per_core,
                    "load_percent_total": total,
                    "temp_celsius_per_core": temps,
                    "temp_celsius_max": max(temps) if temps else None,
                }
            }
        except Exception as exc:
            _log.warning("CpuSensor.collect failed: %s", exc)
            return {}

    def _read_temps(self) -> Optional[list[float]]:
        """Read per-core temps via WMI. Returns None if unavailable."""
        try:
            import wmi as _wmi  # type: ignore[import-untyped]
            c = _wmi.WMI(namespace=r"root\OpenHardwareMonitor")
            sensors = c.Sensor()
            core_temps = [
                float(s.Value)
                for s in sensors
                if s.SensorType == "Temperature" and "CPU Core" in s.Name
            ]
            return core_temps if core_temps else None
        except Exception as exc:
            _log.debug("WMI CPU temps unavailable: %s", exc)
            return None
