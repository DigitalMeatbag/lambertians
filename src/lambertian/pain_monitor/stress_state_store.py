"""Atomic read/write of stress_state.json (IS-8.2.4)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from lambertian.contracts.pain_records import StressState

_log = logging.getLogger(__name__)


class StressStateStore:
    """Persists StressState to a JSON file with atomic writes."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def write(self, state: StressState) -> None:
        """Atomically write the current StressState."""
        data = json.dumps(
            {
                "scalar": state.scalar,
                "raw_last": state.raw_last,
                "cpu_pressure_last": state.cpu_pressure_last,
                "memory_pressure_last": state.memory_pressure_last,
                "consecutive_above_death_threshold": state.consecutive_above_death_threshold,
                "last_sampled_at": state.last_sampled_at,
            }
        )
        self._atomic_write(self._path, data)

    def read(self) -> Optional[StressState]:
        """Return StressState from file, or None if file is absent."""
        if not self._path.exists():
            return None
        try:
            raw = json.loads(self._path.read_text())
            return StressState(
                scalar=float(raw["scalar"]),
                raw_last=float(raw["raw_last"]),
                cpu_pressure_last=float(raw["cpu_pressure_last"]),
                memory_pressure_last=float(raw["memory_pressure_last"]),
                consecutive_above_death_threshold=int(
                    raw["consecutive_above_death_threshold"]
                ),
                last_sampled_at=str(raw["last_sampled_at"]),
            )
        except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            _log.warning("Could not read stress_state.json: %s", exc)
            return None

    def _atomic_write(self, path: Path, data: str) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(data)
        os.replace(tmp, path)  # atomic on both POSIX and Windows
