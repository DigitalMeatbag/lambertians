"""Writes HostStateSnapshot to disk atomically."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from lambertian.env_monitor.models import HostStateSnapshot

_log = logging.getLogger(__name__)


class HostStateWriter:
    """Atomically writes a HostStateSnapshot as JSON to the configured output path."""

    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path

    def write(self, snapshot: HostStateSnapshot) -> None:
        """Serialize snapshot and write atomically (tmp → rename)."""
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._output_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(snapshot.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
        tmp.replace(self._output_path)
        _log.debug("host_state.json written at %s", snapshot.collected_at)
