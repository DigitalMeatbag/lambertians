"""Reads the current turn number from turn_state.json (IS-6 interface)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

_log = logging.getLogger(__name__)


class TurnStateReader:
    """Reads the agent's current turn number from the shared turn_state.json file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read_turn_number(self) -> int:
        """Return the current turn number; returns 0 if the file is absent."""
        if not self._path.exists():
            return 0
        try:
            raw = json.loads(self._path.read_text())
            return int(raw["turn_number"])
        except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            _log.warning("Could not read turn_state.json: %s", exc)
            return 0
