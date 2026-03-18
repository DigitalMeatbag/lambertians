"""Frozen dataclasses for the host_state.json snapshot written by the env monitor."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class CpuState:
    load_percent_per_core: list[float]
    load_percent_total: float
    temp_celsius_per_core: Optional[list[float]]
    temp_celsius_max: Optional[float]


@dataclass(frozen=True)
class MemoryState:
    total_gb: float
    available_gb: float
    used_percent: float


@dataclass(frozen=True)
class GpuState:
    load_percent: Optional[float]
    memory_used_mb: Optional[int]
    memory_total_mb: Optional[int]
    temp_celsius: Optional[float]


@dataclass(frozen=True)
class MediaState:
    playing: bool
    title: Optional[str]
    artist: Optional[str]
    source_app: Optional[str]


@dataclass(frozen=True)
class HostStateSnapshot:
    collected_at: str  # ISO 8601 UTC
    cpu: Optional[CpuState]
    memory: Optional[MemoryState]
    gpu: Optional[GpuState]
    media: Optional[MediaState]

    def to_dict(self) -> dict[object, object]:
        """Serialize to a JSON-compatible dict, preserving None values as null."""
        return asdict(self)
