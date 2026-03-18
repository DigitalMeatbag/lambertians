"""Aggregates all sensor outputs into a single HostStateSnapshot."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from lambertian.env_monitor.models import (
    CpuState,
    GpuState,
    HostStateSnapshot,
    MediaState,
    MemoryState,
)
from lambertian.env_monitor.sensor import SensorProvider

_log = logging.getLogger(__name__)


class EnvStateAggregator:
    """Calls each registered sensor and merges results into a HostStateSnapshot."""

    def __init__(self, sensors: list[SensorProvider]) -> None:
        self._sensors = sensors

    def collect_all(self) -> HostStateSnapshot:
        merged: dict[str, Any] = {}
        for sensor in self._sensors:
            try:
                result = sensor.collect()
                merged.update(result)
            except Exception as exc:
                _log.warning("Sensor %s raised unexpectedly: %s", type(sensor).__name__, exc)

        return HostStateSnapshot(
            collected_at=datetime.now(timezone.utc).isoformat(),
            cpu=_build_cpu(merged.get("cpu")),
            memory=_build_memory(merged.get("memory")),
            gpu=_build_gpu(merged.get("gpu")),
            media=_build_media(merged.get("media")),
        )


def _build_cpu(d: Any) -> CpuState | None:
    if not isinstance(d, dict):
        return None
    try:
        return CpuState(
            load_percent_per_core=d.get("load_percent_per_core") or [],
            load_percent_total=float(d.get("load_percent_total") or 0.0),
            temp_celsius_per_core=d.get("temp_celsius_per_core"),
            temp_celsius_max=d.get("temp_celsius_max"),
        )
    except Exception as exc:
        _log.warning("Failed to build CpuState: %s", exc)
        return None


def _build_memory(d: Any) -> MemoryState | None:
    if not isinstance(d, dict):
        return None
    try:
        return MemoryState(
            total_gb=float(d.get("total_gb") or 0.0),
            available_gb=float(d.get("available_gb") or 0.0),
            used_percent=float(d.get("used_percent") or 0.0),
        )
    except Exception as exc:
        _log.warning("Failed to build MemoryState: %s", exc)
        return None


def _build_gpu(d: Any) -> GpuState | None:
    if not isinstance(d, dict):
        return None
    try:
        return GpuState(
            load_percent=d.get("load_percent"),
            memory_used_mb=d.get("memory_used_mb"),
            memory_total_mb=d.get("memory_total_mb"),
            temp_celsius=d.get("temp_celsius"),
        )
    except Exception as exc:
        _log.warning("Failed to build GpuState: %s", exc)
        return None


def _build_media(d: Any) -> MediaState | None:
    if not isinstance(d, dict):
        return None
    try:
        return MediaState(
            playing=bool(d.get("playing", False)),
            title=d.get("title"),
            artist=d.get("artist"),
            source_app=d.get("source_app"),
        )
    except Exception as exc:
        _log.warning("Failed to build MediaState: %s", exc)
        return None
