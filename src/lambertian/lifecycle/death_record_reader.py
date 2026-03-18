"""Agent-side death record reader — checked at the start of each turn (IS-6.3 step 1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from lambertian.contracts.pain_records import DeathRecord


class DeathRecordParseError(Exception):
    """Raised when death.json exists but cannot be parsed."""


class DeathRecordReader:
    """Reads the death record file written by DeathGuard."""

    def __init__(self, death_record_path: Path) -> None:
        self._path = death_record_path

    def is_dead(self) -> bool:
        """Return True if death.json exists."""
        return self._path.exists()

    def read(self) -> Optional[DeathRecord]:
        """Return the DeathRecord if the file exists, None if absent.

        Raises DeathRecordParseError if the file exists but is malformed.
        """
        if not self._path.exists():
            return None
        try:
            raw = json.loads(self._path.read_text())
            return DeathRecord(
                instance_id=str(raw["instance_id"]),
                trigger=str(raw["trigger"]),
                trigger_value=float(raw["trigger_value"]),
                threshold_used=float(raw["threshold_used"]),
                turn_number=int(raw["turn_number"]),
                timestamp=str(raw["timestamp"]),
            )
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
            raise DeathRecordParseError(
                f"Failed to parse death record at {self._path}: {exc}"
            ) from exc
