"""Append-only pain history log (JSONL) — records all processed events (IS-8.3)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from lambertian.contracts.pain_records import PainEvent

_log = logging.getLogger(__name__)


class PainHistory:
    """Appends processed PainEvent records to a JSONL history file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def append(self, event: PainEvent, dropped: bool = False) -> None:
        """Append one event as a JSONL line; includes the dropped flag."""
        record = {
            "event_id": event.event_id,
            "incident_type": event.incident_type,
            "severity": event.severity,
            "description": event.description,
            "turn_number": event.turn_number,
            "submitted_at": event.submitted_at,
            "context": event.context,
            "dropped": dropped,
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a") as fh:
                fh.write(json.dumps(record) + "\n")
        except OSError as exc:
            _log.error("Could not write pain history: %s", exc)
