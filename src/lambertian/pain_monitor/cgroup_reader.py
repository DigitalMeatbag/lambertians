"""Cgroup signal reader — detects v1/v2, PSI availability, produces ResourceSample."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

# Cgroup v2 paths
_CGROUP_V2_CPU_STAT = Path("/sys/fs/cgroup/cpu.stat")
_CGROUP_V2_MEMORY_CURRENT = Path("/sys/fs/cgroup/memory.current")
_CGROUP_V2_MEMORY_MAX = Path("/sys/fs/cgroup/memory.max")

# Cgroup v1 paths
_CGROUP_V1_CPU_USAGE = Path("/sys/fs/cgroup/cpuacct/cpuacct.usage")
_CGROUP_V1_MEMORY_USAGE = Path("/sys/fs/cgroup/memory/memory.usage_in_bytes")
_CGROUP_V1_MEMORY_LIMIT = Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")

# PSI path
_PSI_CPU = Path("/proc/pressure/cpu")
_PROC_MEMINFO = Path("/proc/meminfo")


class CgroupMode(Enum):
    V2 = auto()
    V1 = auto()


class PsiAvailability(Enum):
    AVAILABLE = auto()
    UNAVAILABLE = auto()


@dataclass(frozen=True)
class ResourceSample:
    cpu_usage_fraction: float
    memory_usage_fraction: float
    cpu_psi_some: Optional[float]
    memory_psi_some: Optional[float]


def _read_host_memory_bytes() -> int:
    """Read MemTotal from /proc/meminfo; return 0 on failure."""
    try:
        text = _PROC_MEMINFO.read_text()
        for line in text.splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                kb = int(parts[1])
                return kb * 1024
    except OSError as exc:
        _log.warning("Could not read /proc/meminfo: %s", exc)
    return 0


def _parse_psi_some(path: Path) -> Optional[float]:
    """Parse 'some avg10=<val>' from a PSI file; return None on failure."""
    try:
        text = path.read_text()
        for line in text.splitlines():
            if line.startswith("some"):
                for token in line.split():
                    if token.startswith("avg10="):
                        return float(token[len("avg10="):]) / 100.0
    except OSError:
        pass
    return None


class CgroupReader:
    """Reads CPU and memory pressure signals from cgroups.

    Detects cgroup mode (v1/v2) and PSI availability at construction time.
    Maintains delta state for CPU usage fraction computation.
    """

    def __init__(self) -> None:
        self._mode: CgroupMode = (
            CgroupMode.V2 if _CGROUP_V2_CPU_STAT.exists() else CgroupMode.V1
        )
        self._psi: PsiAvailability = (
            PsiAvailability.AVAILABLE if _PSI_CPU.exists() else PsiAvailability.UNAVAILABLE
        )
        _log.info("CgroupReader: mode=%s psi=%s", self._mode.name, self._psi.name)

        # CPU delta state
        self._last_cpu_usec: Optional[int] = None
        self._last_sample_time: Optional[float] = None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def sample(self) -> ResourceSample:
        """Read cgroup signals and return a ResourceSample."""
        cpu_fraction = self._read_cpu_fraction()
        memory_fraction = self._read_memory_fraction()

        cpu_psi: Optional[float] = None
        memory_psi: Optional[float] = None
        if self._psi is PsiAvailability.AVAILABLE:
            cpu_psi = _parse_psi_some(_PSI_CPU)
            memory_psi = _parse_psi_some(Path("/proc/pressure/memory"))

        return ResourceSample(
            cpu_usage_fraction=cpu_fraction,
            memory_usage_fraction=memory_fraction,
            cpu_psi_some=cpu_psi,
            memory_psi_some=memory_psi,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _read_cpu_fraction(self) -> float:
        now = time.monotonic()
        if self._mode is CgroupMode.V2:
            current_usec = self._read_v2_cpu_usec()
        else:
            current_usec = self._read_v1_cpu_usec()

        if current_usec is None:
            self._last_cpu_usec = None
            self._last_sample_time = now
            return 0.0

        if self._last_cpu_usec is None or self._last_sample_time is None:
            self._last_cpu_usec = current_usec
            self._last_sample_time = now
            return 0.0

        elapsed_usec = (now - self._last_sample_time) * 1_000_000
        if elapsed_usec <= 0:
            return 0.0

        delta_usec = current_usec - self._last_cpu_usec
        self._last_cpu_usec = current_usec
        self._last_sample_time = now

        fraction = delta_usec / elapsed_usec
        return max(0.0, min(1.0, fraction))

    def _read_v2_cpu_usec(self) -> Optional[int]:
        try:
            text = _CGROUP_V2_CPU_STAT.read_text()
            for line in text.splitlines():
                if line.startswith("usage_usec"):
                    return int(line.split()[1])
        except (OSError, ValueError, IndexError) as exc:
            _log.warning("Could not read cgroup v2 cpu.stat: %s", exc)
        return None

    def _read_v1_cpu_usec(self) -> Optional[int]:
        try:
            val = int(_CGROUP_V1_CPU_USAGE.read_text().strip())
            # v1 reports nanoseconds; convert to microseconds
            return val // 1000
        except (OSError, ValueError) as exc:
            _log.warning("Could not read cgroup v1 cpuacct.usage: %s", exc)
        return None

    def _read_memory_fraction(self) -> float:
        if self._mode is CgroupMode.V2:
            return self._read_v2_memory_fraction()
        return self._read_v1_memory_fraction()

    def _read_v2_memory_fraction(self) -> float:
        try:
            usage = int(_CGROUP_V2_MEMORY_CURRENT.read_text().strip())
        except (OSError, ValueError) as exc:
            _log.warning("Could not read memory.current: %s", exc)
            return 0.0

        try:
            limit_text = _CGROUP_V2_MEMORY_MAX.read_text().strip()
            if limit_text == "max":
                limit = _read_host_memory_bytes()
            else:
                limit = int(limit_text)
        except (OSError, ValueError) as exc:
            _log.warning("Could not read memory.max: %s", exc)
            return 0.0

        if limit <= 0:
            return 0.0
        return max(0.0, min(1.0, usage / limit))

    def _read_v1_memory_fraction(self) -> float:
        try:
            usage = int(_CGROUP_V1_MEMORY_USAGE.read_text().strip())
        except (OSError, ValueError) as exc:
            _log.warning("Could not read v1 memory usage: %s", exc)
            return 0.0

        try:
            limit = int(_CGROUP_V1_MEMORY_LIMIT.read_text().strip())
        except (OSError, ValueError) as exc:
            _log.warning("Could not read v1 memory limit: %s", exc)
            return 0.0

        if limit <= 0:
            return 0.0
        return max(0.0, min(1.0, usage / limit))
